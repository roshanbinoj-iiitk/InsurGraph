"""Phase 0: document inventory, text-layer check, extractor comparison and token counts.

Writes runs/phase0/inventory.csv and prints a summary used in docs/phase0_data_note.md.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DIR, RUNS_DIR  # noqa: E402
from src.ingest import chunk_document, has_text_layer, list_pdfs, load_pdf  # noqa: E402

# Strings that must survive intact for a table to be usable (from the SOV and loss run).
PROBES = {
    "PACK000001_03_statement_of_values": ["83 Crossing Way, Canberra", "USD $3,413,719", "AUD $8,376,361"],
    "PACK000001_02_loss_run_report": ["CLM-2021-", "AUD $165,982", "Theft"],
    "PACK000001_04_policy_schedule": ["AUD $20,000,000", "Professional Indemnity", "PI-2025-981268"],
}


def main() -> None:
    out_dir = RUNS_DIR / "phase0"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in list_pdfs("real"):
        doc = load_pdf(path)
        rows.append(
            {
                "doc_id": doc.doc_id,
                "pack": doc.pack_id,
                "doc_type": doc.doc_type,
                "pages": len(doc.pages),
                "chars": len(doc.render()),
                "est_tokens": doc.n_tokens,
                "chunks": len(chunk_document(doc)),
                "text_layer": has_text_layer(path),
            }
        )
    with open(out_dir / "inventory.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"documents: {len(rows)}  pages: {sum(r['pages'] for r in rows)}")
    print(f"est. tokens total: {sum(r['est_tokens'] for r in rows)}  max/doc: {max(r['est_tokens'] for r in rows)}")
    print("doc types:", dict(Counter(r["doc_type"] for r in rows)))
    print("all have text layer:", all(r["text_layer"] for r in rows))

    print("\nExtractor comparison (probe strings found intact):")
    comparison = {}
    for doc_id, probes in PROBES.items():
        for method in ("pymupdf", "pymupdf4llm"):
            text = load_pdf(RAW_DIR / "pdfs" / f"{doc_id}.pdf", method=method).render()
            flat = text.replace("`", "").replace("**", "")
            hits = sum(p in flat for p in probes)
            comparison[f"{doc_id}:{method}"] = f"{hits}/{len(probes)}"
            print(f"  {doc_id:40s} {method:12s} {hits}/{len(probes)}")
    (out_dir / "extractor_comparison.json").write_text(json.dumps(comparison, indent=2))

    gt = [json.loads(line) for line in open(RAW_DIR / "ground_truth.jsonl")]
    print("\nGround-truth rows:", len(gt))
    print("red flags:", [(r["submission_pack_id"], f["flag_type"]) for r in gt[:1] + gt[7:8] for f in json.loads(r["red_flags_json"])])


if __name__ == "__main__":
    main()
