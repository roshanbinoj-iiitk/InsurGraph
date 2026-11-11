"""LLM extraction: document -> validated ``DocumentExtraction``.

Baseline: whole-document request (every document is < 1K tokens; see Phase 0 note), JSON
output, Pydantic validation, one retry with the validation error on failure. If the retry is
still invalid, invalid *items* are dropped and the document is marked ``salvaged`` so the
failure rate is reported rather than hidden.

CLI:
  python -m src.extract --model gemma-4-e4b --prompt zero_shot_v1 --split dev [--source all]
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from src import llm
from src.config import MODELS, PROMPTS_DIR, RUNS_DIR, split_of
from src.eval.metrics import score
from src.eval.report import write_report
from src.gold import load_gold
from src.ingest import Document, load_corpus
from src.schema import (
    Claim,
    Coverage,
    DocumentExtraction,
    KeyDate,
    Location,
    Party,
    Policy,
    Relationship,
)

ITEM_MODELS = {
    "parties": Party,
    "policies": Policy,
    "coverages": Coverage,
    "locations": Location,
    "claims": Claim,
    "dates": KeyDate,
    "relationships": Relationship,
}


def load_prompt(version: str) -> tuple[str, str]:
    text = (PROMPTS_DIR / f"extract_{version}.md").read_text()
    system, user = text.split("===USER===")
    return system.strip(), user.strip()


def parse_json(text: str) -> dict:
    """Parse the first JSON object in a model response (tolerates ``` fences and chatter)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(t[start : end + 1])


# Column order of the compact row format the prompts ask for (keeps output tokens ~3x lower
# than verbose JSON objects, which matters for Groq's 8K TPM and slow local models).
COLUMNS = {
    "parties": ("role", "name", "abn", "page"),
    "policies": ("policy_number", "premium", "page"),
    "coverages": ("coverage_type", "limit", "deductible", "page"),
    "locations": ("location_no", "address", "total_declared_value", "currency", "page"),
    "claims": ("claim_no", "loss_date", "reported_date", "category", "status", "incurred", "page"),
    "dates": ("kind", "date", "page"),
    "relationships": ("predicate", "object", "page"),
}


def from_compact(data: dict) -> dict:
    """Convert row arrays to the schema's dict shape (dict rows are passed through)."""
    out = {"declared_total": data.get("declared_total")}
    subject = data.get("relationship_subject")
    for key, cols in COLUMNS.items():
        rows = data.get(key) or []
        if not isinstance(rows, list):
            out[key] = rows  # let validation report it
            continue
        items = []
        for row in rows:
            if isinstance(row, list):
                row = dict(zip(cols, row, strict=False))
            if key == "relationships" and isinstance(row, dict):
                row.setdefault("subject", subject)
            items.append(row)
        out[key] = items
    return out


def salvage(data: dict) -> tuple[DocumentExtraction, int]:
    """Keep only the items that validate; return the extraction and number of dropped items."""
    kept: dict = {}
    dropped = 0
    for key, model in ITEM_MODELS.items():
        items = data.get(key) or []
        if not isinstance(items, list):
            dropped += 1
            continue
        kept[key] = []
        for it in items:
            try:
                kept[key].append(model.model_validate(it))
            except (ValidationError, TypeError, ValueError):
                dropped += 1
    try:
        kept["declared_total"] = DocumentExtraction.model_validate(
            {"declared_total": data.get("declared_total")}
        ).declared_total
    except ValidationError:
        dropped += 1
    return DocumentExtraction(**kept), dropped


def extract_document(doc: Document, model: str, prompt: str, use_cache: bool = True) -> tuple[DocumentExtraction, dict]:
    system, user_tpl = load_prompt(prompt)
    user = user_tpl.replace("{doc_id}", doc.doc_id).replace("{document}", doc.render())
    meta = {"doc_id": doc.doc_id, "model": model, "prompt": prompt, "attempts": 0, "status": None,
            "errors": [], "prompt_tokens": 0, "completion_tokens": 0, "latency_s": 0.0, "cached": True}
    data = None
    for attempt in range(2):
        meta["attempts"] = attempt + 1
        res = llm.complete(model, system, user, temperature=0.0, json_mode=True, use_cache=use_cache)
        meta["prompt_tokens"] += res.prompt_tokens or 0
        meta["completion_tokens"] += res.completion_tokens or 0
        meta["latency_s"] += res.latency_s
        meta["cached"] = meta["cached"] and res.cached
        try:
            data = from_compact(parse_json(res.text))
            ext = DocumentExtraction.model_validate(data)
            meta["status"] = "valid" if attempt == 0 else "valid_after_retry"
            return ext.stamp_source(doc.doc_id), meta
        except (ValueError, ValidationError) as e:
            err = str(e)[:600]
            meta["errors"].append(err)
            user = (
                user_tpl.replace("{doc_id}", doc.doc_id).replace("{document}", doc.render())
                + f"\n\nYour previous answer was invalid:\n{err}\nReturn the corrected JSON object only."
            )
    if isinstance(data, dict):
        ext, dropped = salvage(data)
        meta["status"] = f"salvaged({dropped} items dropped)"
        return ext.stamp_source(doc.doc_id), meta
    meta["status"] = "failed"
    return DocumentExtraction().stamp_source(doc.doc_id), meta


def run_dir_for(model: str, prompt: str, split: str) -> Path:
    return RUNS_DIR / "extraction" / split / f"{model}__{prompt}"


def load_predictions(run_dir: Path) -> dict[str, DocumentExtraction]:
    out = {}
    for f in sorted((run_dir / "predictions").glob("*.json")):
        out[f.stem] = DocumentExtraction.model_validate_json(f.read_text()).stamp_source(f.stem)
    return out


def run(model: str, prompt: str, split: str, source: str = "all", doc_filter: list[str] | None = None,
        use_cache: bool = True) -> Path:
    docs = [d for d in load_corpus(source) if split_of(d.doc_id) == split]
    if doc_filter:
        docs = [d for d in docs if any(f in d.doc_id for f in doc_filter)]
    run_dir = run_dir_for(model, prompt, split)
    (run_dir / "predictions").mkdir(parents=True, exist_ok=True)
    log = []
    t0 = time.time()
    for i, doc in enumerate(docs, 1):
        ext, meta = extract_document(doc, model, prompt, use_cache)
        (run_dir / "predictions" / f"{doc.doc_id}.json").write_text(ext.model_dump_json(indent=1))
        log.append(meta)
        print(f"[{i}/{len(docs)}] {doc.doc_id}: {meta['status']} ({meta['latency_s']:.0f}s"
              f"{', cached' if meta['cached'] else ''})", flush=True)
    with open(run_dir / "extraction_log.jsonl", "w") as f:
        for m in log:
            f.write(json.dumps(m) + "\n")
    evaluate_run(run_dir, model, prompt, split, log, wall_s=time.time() - t0)
    return run_dir


def evaluate_run(run_dir: Path, model: str, prompt: str, split: str, log: list[dict] | None = None,
                 wall_s: float | None = None) -> dict:
    if log is None:
        log = [json.loads(line) for line in open(run_dir / "extraction_log.jsonl")]
    preds = load_predictions(run_dir)
    gold_all = load_gold("all")
    subsets = {
        "real": {d: g for d, g in gold_all.items() if d.startswith("PACK") and d in preds},
        "synthetic": {d: g for d, g in gold_all.items() if d.startswith("SYN") and d in preds},
    }
    cards = {}
    for label, gold in subsets.items():
        if not gold:
            continue
        for mode in ("strict", "lenient"):
            cards[f"{label}/{mode}"] = score(gold, preds, mode)
    n = len(log)
    statuses = [m["status"] for m in log]
    tags = {
        "model": model,
        "model_id": MODELS[model].model_id,
        "provider": MODELS[model].provider,
        "prompt": prompt,
        "split": split,
        "n_docs": n,
        "valid_first_try": sum(s == "valid" for s in statuses),
        "valid_after_retry": sum(s == "valid_after_retry" for s in statuses),
        "salvaged_or_failed": sum(s.startswith(("salvaged", "failed")) for s in statuses),
        "prompt_tokens": sum(m["prompt_tokens"] for m in log),
        "completion_tokens": sum(m["completion_tokens"] for m in log),
        "llm_latency_s": round(sum(m["latency_s"] for m in log), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if wall_s is not None:
        tags["wall_s"] = round(wall_s, 1)
    write_report(run_dir, cards, tags)
    summary = {k: {"entity_macro_f1": c.entity_macro_f1, "relation_macro_f1": c.relation_macro_f1}
               for k, c in cards.items()}
    (run_dir / "meta.json").write_text(json.dumps({**tags, "summary": summary}, indent=2))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(MODELS))
    ap.add_argument("--prompt", default="zero_shot_v1")
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--source", default="all", choices=["real", "synthetic", "all"])
    ap.add_argument("--docs", nargs="*", help="substring filter on doc ids")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()
    run_dir = run(args.model, args.prompt, args.split, args.source, args.docs, not args.no_cache)
    print((run_dir / "metrics.md").read_text())


if __name__ == "__main__":
    main()
