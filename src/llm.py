"""Provider-agnostic LLM calls with a persistent cache, proactive throttling and retries.

* Cache: ``diskcache`` keyed by a hash of provider, model, temperature, system prompt, user
  prompt, extra params and schema version, so reruns cost nothing and survive restarts.
* Throttle: a sliding 60-second window per model that estimates tokens *before* each call and
  waits when the request would exceed the free-tier RPM/TPM (Groq binds on 8K TPM).
* Retries: ``tenacity`` exponential backoff on rate-limit / transient errors, honouring a
  ``retry-after`` header when the API sends one.

Structured output uses native JSON mode where available plus Pydantic validation in the
caller (``src.extract``); ``instructor`` was not needed for this path.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass

import diskcache
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import CACHE_DIR, LOCAL_LLM_BASE_URL, MODELS, SCHEMA_VERSION, ModelSpec
from src.ingest import estimate_tokens

_cache: diskcache.Cache | None = None


def get_cache() -> diskcache.Cache:
    global _cache
    if _cache is None:
        _cache = diskcache.Cache(str(CACHE_DIR / "llm"))
    return _cache


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cached: bool = False
    latency_s: float = 0.0


class RateLimiter:
    """Sliding-window limiter on requests and (estimated) tokens per minute."""

    def __init__(self, rpm: int | None, tpm: int | None):
        self.rpm, self.tpm = rpm, tpm
        self.events: deque[tuple[float, int]] = deque()
        self.lock = threading.Lock()

    def wait(self, tokens: int) -> float:
        if not self.rpm and not self.tpm:
            return 0.0
        waited = 0.0
        while True:
            with self.lock:
                now = time.monotonic()
                while self.events and now - self.events[0][0] >= 60:
                    self.events.popleft()
                n_req = len(self.events)
                n_tok = sum(t for _, t in self.events)
                ok_r = not self.rpm or n_req + 1 <= self.rpm
                ok_t = not self.tpm or n_tok + tokens <= self.tpm or not self.events
                if ok_r and ok_t:
                    self.events.append((now, tokens))
                    return waited
                sleep = 60 - (now - self.events[0][0]) + 0.05
            time.sleep(sleep)
            waited += sleep


_limiters: dict[str, RateLimiter] = {}


def _limiter(spec: ModelSpec) -> RateLimiter:
    if spec.name not in _limiters:
        _limiters[spec.name] = RateLimiter(spec.rpm, spec.tpm)
    return _limiters[spec.name]


class RateLimitError(RuntimeError):
    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        if exc.retry_after:
            time.sleep(min(exc.retry_after, 120))
        return True
    name = type(exc).__name__.lower()
    if any(k in name for k in ("ratelimit", "timeout", "connection", "unavailable", "internalserver", "servererror")):
        return True
    return getattr(exc, "code", None) in (429, 500, 502, 503, 504) or getattr(exc, "status_code", None) in (
        429,
        500,
        502,
        503,
        504,
    )


def _retry_after(exc: Exception) -> float | None:
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None) or {}
    val = headers.get("retry-after") if hasattr(headers, "get") else None
    try:
        return float(val) if val else None
    except ValueError:
        return None


# ------------------------------------------------------------------------------------------
# API keys: primary plus optional fallback per provider. On a 429 (rate limit / quota) the
# client switches to the next key and stays there; key values are never logged.

KEY_ENV = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
_active_key: dict[str, int] = {}


def api_key_names(provider: str) -> list[str]:
    """Env var names that hold a non-empty, distinct key for ``provider``, in priority order."""
    base = KEY_ENV[provider]
    names, seen = [], set()
    for name in (base, f"{base}_FALLBACK"):
        val = (os.getenv(name) or "").strip()
        if val and val not in seen:
            names.append(name)
            seen.add(val)
    return names


def _current_key(provider: str) -> tuple[str, str]:
    names = api_key_names(provider)
    if not names:
        raise RuntimeError(f"{KEY_ENV[provider]} is not set (see .env.example)")
    name = names[min(_active_key.get(provider, 0), len(names) - 1)]
    return name, os.environ[name].strip()


def rotate_key(provider: str) -> bool:
    """Switch ``provider`` to its next configured key. Returns False if there is none left."""
    names = api_key_names(provider)
    i = _active_key.get(provider, 0)
    if i + 1 >= len(names):
        return False
    _active_key[provider] = i + 1
    print(f"[llm] {names[i]} rate-limited; switching to {names[i + 1]}", file=sys.stderr, flush=True)
    return True


def _rate_limited(provider: str, exc: Exception) -> RateLimitError:
    """Wrap a provider 429: rotate to the fallback key (retry at once) or back off as told."""
    if rotate_key(provider):
        return RateLimitError(str(exc), retry_after=0)
    return RateLimitError(str(exc), _retry_after(exc))


def cache_key(spec: ModelSpec, system: str, user: str, temperature: float, json_mode: bool, max_tokens: int) -> str:
    payload = json.dumps(
        {
            "provider": spec.provider,
            "model": spec.model_id,
            "temperature": temperature,
            "system": system,
            "user": user,
            "json_mode": json_mode,
            "max_tokens": max_tokens,
            "extra": spec.extra,
            "schema_version": SCHEMA_VERSION,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def complete(
    model: str,
    system: str,
    user: str,
    temperature: float = 0.0,
    json_mode: bool = False,
    max_tokens: int | None = None,
    use_cache: bool = True,
) -> LLMResult:
    """One chat completion. ``model`` is a key of ``src.config.MODELS``."""
    spec = MODELS[model]
    max_tokens = max_tokens or spec.max_output_tokens
    key = cache_key(spec, system, user, temperature, json_mode, max_tokens)
    cache = get_cache()
    if use_cache and key in cache:
        hit = dict(cache[key])
        return LLMResult(**{**hit, "cached": True})
    # Budget input + expected output tokens (output counts against Groq TPM too).
    est = estimate_tokens(system + user) + min(max_tokens, 1500)
    _limiter(spec).wait(est)
    t0 = time.time()
    res = _call(spec, system, user, temperature, json_mode, max_tokens)
    res.latency_s = round(time.time() - t0, 2)
    cache[key] = {k: v for k, v in res.__dict__.items() if k != "cached"}
    return res


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(8),
    reraise=True,
)
def _call(spec: ModelSpec, system: str, user: str, temperature: float, json_mode: bool, max_tokens: int) -> LLMResult:
    if spec.provider in ("local", "groq"):
        return _call_openai_compatible(spec, system, user, temperature, json_mode, max_tokens)
    if spec.provider == "gemini":
        return _call_gemini(spec, system, user, temperature, json_mode, max_tokens)
    raise ValueError(spec.provider)


_clients: dict[str, object] = {}


def _call_openai_compatible(spec, system, user, temperature, json_mode, max_tokens) -> LLMResult:
    if spec.provider == "groq":
        from groq import Groq
        from groq import RateLimitError as ProviderRateLimit

        key_name, key = _current_key("groq")
        if key_name not in _clients:
            _clients[key_name] = Groq(api_key=key)
        client = _clients[key_name]
    else:
        from openai import OpenAI
        from openai import RateLimitError as ProviderRateLimit

        client = _clients.setdefault("local", OpenAI(base_url=LOCAL_LLM_BASE_URL, api_key="lm-studio", timeout=900))
    kwargs = dict(
        model=spec.model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    if json_mode and spec.provider == "groq":
        kwargs["response_format"] = {"type": "json_object"}
    kwargs.update(spec.extra)
    try:
        r = client.chat.completions.create(**kwargs)
    except ProviderRateLimit as e:  # type: ignore[misc]
        if spec.provider == "groq":
            raise _rate_limited("groq", e) from e
        raise RateLimitError(str(e), _retry_after(e)) from e
    usage = getattr(r, "usage", None)
    return LLMResult(
        text=r.choices[0].message.content or "",
        model=spec.model_id,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
    )


def _call_gemini(spec, system, user, temperature, json_mode, max_tokens) -> LLMResult:
    from google import genai
    from google.genai import errors, types

    key_name, key = _current_key("gemini")
    if key_name not in _clients:
        _clients[key_name] = genai.Client(api_key=key)
    client = _clients[key_name]
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        max_output_tokens=max_tokens,
        response_mime_type="application/json" if json_mode else None,
    )
    try:
        r = client.models.generate_content(model=spec.model_id, contents=user, config=cfg)
    except errors.APIError as e:
        if getattr(e, "code", None) == 429:
            raise _rate_limited("gemini", e) from e
        raise
    um = getattr(r, "usage_metadata", None)
    return LLMResult(
        text=r.text or "",
        model=spec.model_id,
        prompt_tokens=getattr(um, "prompt_token_count", None),
        completion_tokens=getattr(um, "candidates_token_count", None),
    )
