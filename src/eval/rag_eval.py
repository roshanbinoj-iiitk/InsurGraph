"""RAG evaluation: retrieval hit rate, exact/numeric scoring, LLM-as-judge for free text.

Usage: python -m src.eval.rag_eval --split dev [--variants plain graph] [--k 5]
Writes runs/rag/<split>/{answers.jsonl, metrics.md}.
"""

from __future__ import annotations

import argparse
import json
import re

from src import llm
from src.config import DEV_PACKS, GOLD_DIR, RUNS_DIR, TEST_PACKS
from src.extract import load_predictions, parse_json
from src.gold import load_gold
from src.graph import build_graph
from src.normalize import norm_address, norm_date, norm_money, norm_name, norm_text
from src.rag import answer

JUDGE_MODEL = "qwen-judge"
JUDGE_SYSTEM = (
    "You grade answers to questions about insurance documents. Compare the CANDIDATE answer with the "
    "REFERENCE answer. The candidate is correct if it states the same facts as the reference (numbers, "
    "dates, names and yes/no conclusion must agree; extra correct detail is fine; wording may differ). "
    'Reply with JSON only: {"correct": true|false, "reason": "<one short sentence>"}'
)


def extracted_graph_inputs() -> dict:
    """Real-document extractions of the dev-selected configuration (falls back to gold if not run yet)."""
    best_file = RUNS_DIR / "extraction" / "best_config.json"
    if best_file.exists():
        best = json.loads(best_file.read_text())["best"]
        preds = {}
        for split in ("dev", "test"):
            d = RUNS_DIR / "extraction" / split / best
            if d.exists():
                preds.update({k: v for k, v in load_predictions(d).items() if k.startswith("PACK")})
        if preds:
            return preds
    return load_gold("real")


def load_questions(split: str) -> list[dict]:
    packs = DEV_PACKS if split == "dev" else TEST_PACKS
    qs = json.loads((GOLD_DIR / "rag_questions.json").read_text())["questions"]
    return [q for q in qs if q["pack"] in packs]


def score_answer(q: dict, ans: str) -> bool | None:
    """Deterministic scoring for numeric/date/exact questions; None for free text."""
    t = q["answer_type"]
    if t == "numeric":
        gold = float(q["answer"])
        nums = [norm_money(m) for m in re.findall(r"\d[\d,]*(?:\.\d+)?\s*(?:m|million|k)?\b", ans.lower())]
        return any(n is not None and abs(n - gold) <= max(0.5, 0.005 * gold) for n in nums)
    if t == "date":
        cands = re.findall(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}", ans)
        return any(norm_date(c) == q["answer"] for c in cands)
    if t == "exact":
        g_name, a_name = norm_name(q["answer"]) or "", norm_text(ans) or ""
        if g_name and g_name in a_name:
            return True
        return bool(norm_address(q["answer"]) and norm_address(q["answer"]) in (norm_address(ans) or ""))
    return None


def judge(q: dict, ans: str) -> dict:
    user = f"QUESTION: {q['question']}\nREFERENCE: {q['answer']}\nCANDIDATE: {ans}"
    res = llm.complete(JUDGE_MODEL, JUDGE_SYSTEM, user, json_mode=True, max_tokens=300)
    try:
        out = parse_json(res.text)
        return {"correct": bool(out.get("correct")), "reason": str(out.get("reason", ""))}
    except ValueError:
        return {"correct": False, "reason": f"unparseable judge output: {res.text[:100]}"}


def run(split: str, variants=("plain", "graph"), k: int = 5, model: str = "gemini-flash-lite") -> dict:
    qs = load_questions(split)
    G = build_graph(extracted_graph_inputs()) if "graph" in variants else None
    out_dir = RUNS_DIR / "rag" / split
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for variant in variants:
        for q in qs:
            r = answer(q["question"], model=model, k=k, variant=variant, G=G)
            hit = any(h["doc_id"] in q["source_docs"] for h in r["retrieved"])
            correct = score_answer(q, r["answer"])
            jd = None
            if correct is None:
                jd = judge(q, r["answer"])
                correct = jd["correct"]
            rows.append(
                {
                    "id": q["id"],
                    "variant": variant,
                    "answer_type": q["answer_type"],
                    "question": q["question"],
                    "reference": q["answer"],
                    "answer": r["answer"],
                    "hit": hit,
                    "correct": correct,
                    "judge": jd,
                    "routed_pack": r["routed_pack"],
                    "retrieved": [h["doc_id"] for h in r["retrieved"]],
                }
            )
            print(f"{variant:5s} {q['id']} hit={hit!s:5s} correct={correct!s:5s} | {r['answer'][:70]}", flush=True)
    with open(out_dir / "answers.jsonl", "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    summary = summarise(rows, split, k, model)
    (out_dir / "metrics.md").write_text(summary["markdown"])
    return summary


def summarise(rows: list[dict], split: str, k: int, model: str) -> dict:
    lines = [
        f"# RAG results ({split})",
        "",
        f"Answer model `{model}`, top-k = {k}, judge `{JUDGE_MODEL}` "
        "(free-text answers only), embeddings: local sentence-transformers.",
        "",
        "| Variant | n | Retrieval hit@k | Exact/numeric acc. (n) | Judged free-text acc. (n) | Overall acc. |",
        "|---|---|---|---|---|---|",
    ]
    table = {}
    for variant in sorted({r["variant"] for r in rows}, key=lambda v: v != "plain"):
        rs = [r for r in rows if r["variant"] == variant]
        det = [r for r in rs if r["answer_type"] != "free_text"]
        ft = [r for r in rs if r["answer_type"] == "free_text"]
        hit = sum(r["hit"] for r in rs) / len(rs)
        da = sum(r["correct"] for r in det) / len(det) if det else 0
        fa = sum(r["correct"] for r in ft) / len(ft) if ft else 0
        acc = sum(r["correct"] for r in rs) / len(rs)
        table[variant] = {"n": len(rs), "hit": hit, "det_acc": da, "ft_acc": fa, "acc": acc}
        lines.append(
            f"| {variant} | {len(rs)} | {hit:.2f} | {da:.2f} ({len(det)}) | {fa:.2f} ({len(ft)}) | {acc:.2f} |"
        )
    lines += ["", "Wrong answers:", ""]
    lines += [
        f"- {r['variant']} {r['id']}: Q: {r['question']} | ref: {r['reference']} | got: {r['answer']} (hit={r['hit']})"
        for r in rows
        if not r["correct"]
    ]
    return {"table": table, "markdown": "\n".join(lines) + "\n"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--variants", nargs="+", default=["plain", "graph"])
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()
    print(run(args.split, tuple(args.variants), args.k)["markdown"])


if __name__ == "__main__":
    main()
