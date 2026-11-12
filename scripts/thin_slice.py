"""Milestone 1 thin slice: 1-2 Pack A documents through extract -> score -> graph -> RAG.

Usage: python scripts/thin_slice.py [--model gemini-flash-lite]
Writes runs/thin_slice/summary.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RUNS_DIR  # noqa: E402
from src.eval.metrics import score  # noqa: E402
from src.extract import extract_document  # noqa: E402
from src.gold import load_gold  # noqa: E402
from src.graph import build_graph, coverages_for_policy, parties_for_policy  # noqa: E402
from src.ingest import load_corpus  # noqa: E402
from src.rag import answer  # noqa: E402

DOCS = ("PACK000001_02_loss_run_report", "PACK000001_04_policy_schedule")
QUESTION = "What is the public liability limit on policy PI-2025-981268?"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-flash-lite")
    args = ap.parse_args()
    out = RUNS_DIR / "thin_slice"
    out.mkdir(parents=True, exist_ok=True)

    docs = [d for d in load_corpus("real") if d.doc_id in DOCS]
    preds = {}
    for d in docs:
        preds[d.doc_id], meta = extract_document(d, args.model, "zero_shot_v1")
        print(d.doc_id, meta["status"])
    gold = {k: v for k, v in load_gold("real").items() if k in DOCS}
    sc = score(gold, preds, "strict", n_boot=0)
    G = build_graph(preds)
    rag = answer(QUESTION, model=args.model, G=G)
    lines = [
        "# Thin slice (Milestone 1)", "",
        f"Model `{args.model}`, prompt `zero_shot_v1`, documents: {', '.join(DOCS)}", "",
        f"* Extraction (strict): entity macro-F1 {sc.entity_macro_f1:.3f}, relationship macro-F1 "
        f"{sc.relation_macro_f1:.3f}",
        f"* Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges",
        f"* Coverages of PI-2025-981268: {sorted(coverages_for_policy(G, 'PI-2025-981268'))}",
        f"* Parties of PI-2025-981268: {json.dumps(parties_for_policy(G, 'PI-2025-981268'))}",
        f"* RAG: Q: {QUESTION}  A: **{rag['answer']}** (top doc {rag['retrieved'][0]['doc_id']})", "",
    ]
    (out / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
