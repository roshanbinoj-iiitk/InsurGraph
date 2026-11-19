"""One-command reproducible run.

  python scripts/run_all.py            # full pipeline (needs GEMINI_API_KEY and GROQ_API_KEY)
  python scripts/run_all.py --offline  # rebuild every table from the committed runs/ outputs, no API calls

Steps: data -> gold -> synthetic packs -> extraction (2 models x 2 prompts, dev) -> pick best on dev
-> the same 4 configs on test (run once) -> entity resolution check -> graph + inconsistency detector
-> RAG (plain + graph-assisted) -> runs/summary.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DIR, RUNS_DIR, SYNTH_DIR  # noqa: E402
from src.eval.detector import evaluate_flags, flags_markdown  # noqa: E402
from src.eval.metrics import score  # noqa: E402
from src.extract import evaluate_run, load_predictions, run, run_dir_for  # noqa: E402
from src.gold import load_gold  # noqa: E402
from src.graph import build_graph, detect_inconsistencies, to_json_safe  # noqa: E402
from src.resolve import Resolver  # noqa: E402

MODELS = ("gemini-flash-lite", "gpt-oss-120b")
PROMPTS = ("zero_shot_v1", "few_shot_v1")
SELECTION_METRIC = "real/strict"  # dev selection: mean of entity and relationship macro-F1 on Pack A + synthetic


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def ensure_data(offline: bool) -> None:
    if not (RAW_DIR / "ground_truth.jsonl").exists():
        if offline:
            raise SystemExit("data/raw missing; run without --offline or scripts/download_data.py")
        import subprocess

        subprocess.run([sys.executable, "scripts/download_data.py"], check=True)
    from src import gold, synth

    gold.main()
    if not (SYNTH_DIR / "gold.jsonl").exists():
        print(synth.generate())


def dev_score(run_dir: Path) -> float:
    """Selection score on dev: average of entity and relationship macro-F1 over real and synthetic (strict)."""
    s = json.loads((run_dir / "meta.json").read_text())["summary"]
    vals = [
        v
        for k in ("real/strict", "synthetic/strict")
        if k in s
        for v in (s[k]["entity_macro_f1"], s[k]["relation_macro_f1"])
        if v is not None
    ]
    return sum(vals) / len(vals)


def extraction(split: str, offline: bool) -> dict[str, Path]:
    dirs = {}
    for m in MODELS:
        for p in PROMPTS:
            d = run_dir_for(m, p, split)
            if offline:
                evaluate_run(d, m, p, split)
            else:
                run(m, p, split, "all")
            dirs[f"{m}__{p}"] = d
    return dirs


def detector_section(best: dict[str, Path], resolver: Resolver) -> str:
    out = RUNS_DIR / "detector"
    out.mkdir(parents=True, exist_ok=True)
    gold = load_gold("all")
    md = ["# Inconsistency detector", ""]
    results = {}
    for label, exts in (
        ("gold extractions (detector logic only)", gold),
        ("best model's extractions (end to end)", {**load_predictions(best["dev"]), **load_predictions(best["test"])}),
    ):
        G = build_graph(exts, resolver)
        flags = detect_inconsistencies(G)
        for split, packs in (
            ("dev", ["PACK000001", "SYNDEV001", "SYNDEV002", "SYNDEV003"]),
            ("test", ["PACK000002", "SYNTEST001", "SYNTEST002", "SYNTEST003"]),
        ):
            res = evaluate_flags(flags, packs)
            results[f"{label} / {split}"] = res
            md.append(flags_markdown(f"{label}, {split}", res))
        if label.startswith("best"):
            (out / "graph_best.json").write_text(json.dumps(to_json_safe(G), default=str))
            (out / "flags_best.json").write_text(json.dumps(flags, indent=1, default=str))
            log = [d.__dict__ for d in G.graph["resolution_log"] if d.a != d.b]
            (out / "resolution_log_best.json").write_text(json.dumps(log, indent=1))
    (out / "results.md").write_text("\n".join(md))
    summary = {
        k: {kk: v[kk] for kk in ("labelled", "found", "missed", "corroborating", "true_unlabelled", "false_flags")}
        for k, v in results.items()
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return "\n".join(md)


def extraction_table(dirs_by_split: dict[str, dict[str, Path]]) -> str:
    lines = [
        "| Split | Subset | Model | Prompt | Entity macro-F1 strict [95% CI] | lenient | "
        "Relationship macro-F1 strict [95% CI] | Valid JSON 1st try (whole split) | Tokens (whole split) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    gold = load_gold("all")
    for split, dirs in dirs_by_split.items():
        for subset in ("real", "synthetic"):
            for d in dirs.values():
                meta = json.loads((d / "meta.json").read_text())
                preds = load_predictions(d)
                g = {
                    k: v for k, v in gold.items() if k in preds and k.startswith("PACK" if subset == "real" else "SYN")
                }
                st, le = score(g, preds, "strict"), score(g, preds, "lenient", n_boot=0)
                ci_e, ci_r = st.ci.get("entity_macro_f1"), st.ci.get("relation_macro_f1")
                lines.append(
                    f"| {split} | {'Pack ' + ('A' if split == 'dev' else 'B') if subset == 'real' else 'synthetic ' + split}"  # noqa: E501
                    f" ({len(g)} docs) | {meta['model']} | {meta['prompt']} | {st.entity_macro_f1:.3f} "
                    f"[{ci_e[0]:.2f}, {ci_e[1]:.2f}] | {le.entity_macro_f1:.3f} | {st.relation_macro_f1:.3f} "
                    f"[{ci_r[0]:.2f}, {ci_r[1]:.2f}] | {meta['valid_first_try']}/{meta['n_docs']} | "
                    f"{meta['prompt_tokens'] + meta['completion_tokens']:,} |"
                )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="re-score committed outputs; no LLM calls")
    args = ap.parse_args()

    step("data and gold")
    ensure_data(args.offline)

    step("extraction: dev (2 models x 2 prompts)")
    dev_dirs = extraction("dev", args.offline)
    ranking = sorted(dev_dirs, key=lambda k: dev_score(dev_dirs[k]), reverse=True)
    best_key = ranking[0]
    (RUNS_DIR / "extraction" / "best_config.json").write_text(
        json.dumps(
            {"best": best_key, "selected_on": "dev", "ranking": {k: round(dev_score(dev_dirs[k]), 4) for k in ranking}},
            indent=2,
        )
    )
    print("best on dev:", best_key)

    step("extraction: test (run once, all configs)")
    test_dirs = extraction("test", args.offline)
    best = {"dev": dev_dirs[best_key], "test": test_dirs[best_key]}

    step("entity resolution")
    if not args.offline:
        import subprocess

        subprocess.run([sys.executable, "scripts/tune_resolution.py"], check=True)
    # LLM layer whenever a key is available (calls are cached); string layers only otherwise.
    resolver = Resolver(llm_model="gemini-flash-lite" if os.getenv("GEMINI_API_KEY") else None)

    step("graph and inconsistency detector")
    detector_md = detector_section(best, resolver)

    step("RAG")
    rag_md = []
    for split in ("dev", "test"):
        path = RUNS_DIR / "rag" / split / "metrics.md"
        if not args.offline:
            from src.eval.rag_eval import run as rag_run

            rag_run(split)
        rag_md.append(path.read_text() if path.exists() else f"(no RAG results for {split})")

    step("summary")
    summary = [
        "# Results summary",
        "",
        f"Best configuration on dev: **{best_key}** (selected on dev only; test run once afterwards).",
        "",
        "## Extraction",
        "",
        extraction_table({"dev": dev_dirs, "test": test_dirs}),
        "",
        "## Entity resolution",
        "",
        (RUNS_DIR / "resolution" / "results.md").read_text(),
        "",
        detector_md.replace("# Inconsistency detector", "## Inconsistency detector"),
        "",
        "## RAG",
        "",
        *[m.replace("# RAG", "### RAG") for m in rag_md],
    ]
    (RUNS_DIR / "summary.md").write_text("\n".join(summary))
    print(f"wrote {RUNS_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
