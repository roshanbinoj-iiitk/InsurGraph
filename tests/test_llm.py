import groq
import httpx
import pytest
from tenacity import wait_none

from src import llm


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(llm, "_active_key", {})
    monkeypatch.setattr(llm, "_clients", {})
    monkeypatch.setattr(llm._call.retry, "wait", wait_none())


def test_key_names_order_and_dedupe(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "primary")
    monkeypatch.setenv("GROQ_API_KEY_FALLBACK", "backup")
    assert llm.api_key_names("groq") == ["GROQ_API_KEY", "GROQ_API_KEY_FALLBACK"]
    monkeypatch.setenv("GROQ_API_KEY_FALLBACK", "primary")  # same value is not a real fallback
    assert llm.api_key_names("groq") == ["GROQ_API_KEY"]
    monkeypatch.setenv("GROQ_API_KEY_FALLBACK", " ")
    assert llm.api_key_names("groq") == ["GROQ_API_KEY"]


def test_rotate_key_is_sticky_and_bounded(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "a")
    monkeypatch.setenv("GEMINI_API_KEY_FALLBACK", "b")
    assert llm._current_key("gemini") == ("GEMINI_API_KEY", "a")
    assert llm.rotate_key("gemini") is True
    assert llm._current_key("gemini") == ("GEMINI_API_KEY_FALLBACK", "b")
    assert llm.rotate_key("gemini") is False  # no third key


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_FALLBACK", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        llm._current_key("gemini")


class _FakeGroq:
    calls: list[str] = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        _FakeGroq.calls.append(self.api_key)
        if self.api_key == "primary":
            resp = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
            raise groq.RateLimitError("rate limited", response=resp, body=None)
        msg = type("M", (), {"content": '{"ok": true}'})()
        choice = type("C", (), {"message": msg})()
        usage = type("U", (), {"prompt_tokens": 5, "completion_tokens": 3})()
        return type("R", (), {"choices": [choice], "usage": usage})()


def test_groq_429_switches_to_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "primary")
    monkeypatch.setenv("GROQ_API_KEY_FALLBACK", "backup")
    monkeypatch.setattr(groq, "Groq", _FakeGroq)
    _FakeGroq.calls = []
    res = llm.complete("qwen-judge", "sys", "user", use_cache=False)
    assert res.text == '{"ok": true}'
    assert _FakeGroq.calls == ["primary", "backup"]
    # subsequent calls stay on the fallback
    llm.complete("qwen-judge", "sys", "user again", use_cache=False)
    assert _FakeGroq.calls[-1] == "backup"
