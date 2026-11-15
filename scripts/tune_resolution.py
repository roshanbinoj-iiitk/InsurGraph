"""Tune the fuzzy layer of entity resolution on dev pairs, then check the full resolver on test pairs.

Writes runs/resolution/{tuning.csv, results.md, decisions.jsonl}.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RUNS_DIR  # noqa: E402
from src.resolve import SCORERS, Resolver, evaluate_pairs, load_pairs  # noqa: E402


def main() -> None:
    out = RUNS_DIR / "resolution"
    out.mkdir(parents=True, exist_ok=True)
    dev, test = load_pairs("dev"), load_pairs("test")

    # Grid search string matching only (no LLM) on dev; tie-break on precision, then higher threshold.
    grid = []
    for scorer in SCORERS:
        for thr in range(70, 101, 5):
            r = evaluate_pairs(Resolver(scorer=scorer, threshold=thr, llm_model=None), dev)
            grid.append({"scorer": scorer, "threshold": thr, **{k: r[k] for k in ("accuracy", "precision", "recall")}})
    with open(out / "tuning.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(grid[0]))
        w.writeheader()
        w.writerows(grid)
    best = max(grid, key=lambda g: (g["accuracy"], g["precision"], g["threshold"]))
    print("best on dev:", best)

    lines = [
        "# Entity resolution",
        "",
        f"Fuzzy layer tuned on {len(dev)} dev pairs: **{best['scorer']} >= "
        f"{best['threshold']}** (dev accuracy {best['accuracy']:.2f}).",
        "",
        "| Split | Resolver | n | Accuracy | Precision | Recall | FP | FN |",
        "|---|---|---|---|---|---|---|---|",
    ]
    decisions = []
    for split, pairs in (("dev", dev), ("test", test)):
        for label, llm_model in (("normalise + fuzzy", None), ("normalise + fuzzy + LLM", "gemini-flash-lite")):
            res = Resolver(scorer=best["scorer"], threshold=best["threshold"], llm_model=llm_model)
            r = evaluate_pairs(res, pairs)
            lines.append(
                f"| {split} | {label} | {r['n']} | {r['accuracy']:.2f} | {r['precision']:.2f} | "
                f"{r['recall']:.2f} | {r['fp']} | {r['fn']} |"
            )
            decisions += [{"split": split, "resolver": label, **row} for row in r["rows"]]
    lines += ["", "Per-pair decisions (layer that decided, fuzzy score) are in `decisions.jsonl`.", ""]
    errs = [d for d in decisions if d["pred"] != d["same"]]
    if errs:
        lines += ["Errors:", ""] + [
            f"- {d['split']} / {d['resolver']}: `{d['a']}` vs `{d['b']}` "
            f"(gold {d['same']}, layer {d['layer']}, score {d['score']})"
            for d in errs
        ]
    (out / "results.md").write_text("\n".join(lines) + "\n")
    with open(out / "decisions.jsonl", "w") as f:
        for d in decisions:
            f.write(json.dumps(d) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
