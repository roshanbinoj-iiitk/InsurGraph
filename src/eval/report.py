"""Markdown and CSV result tables, tagged with model, prompt version and split."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.eval.metrics import REL_NAMES, SMALL_N, Scorecard
from src.schema import ENTITY_TYPES


def _f(x: float | None) -> str:
    return "–" if x is None else f"{x:.3f}"


def _ci(ci: tuple[float, float] | None) -> str:
    return "" if ci is None else f"[{ci[0]:.2f}, {ci[1]:.2f}]"


def scorecard_rows(sc: Scorecard, tags: dict) -> list[dict]:
    rows = []
    for name in (*ENTITY_TYPES, *REL_NAMES):
        ts = sc.types.get(name)
        if ts is None:
            continue
        p, r, f = ts.prf
        rows.append(
            {
                **tags,
                "mode": sc.mode,
                "type": name,
                "n_gold": ts.n_gold,
                "n_pred": ts.n_pred,
                "tp": ts.tp,
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f, 4),
                "f1_ci_low": ts.f1_ci and round(ts.f1_ci[0], 4),
                "f1_ci_high": ts.f1_ci and round(ts.f1_ci[1], 4),
                "field_acc": None if ts.field_acc is None else round(ts.field_acc, 4),
            }
        )
    for key in ("entity_macro_f1", "entity_micro_f1", "relation_macro_f1", "relation_micro_f1"):
        val = getattr(sc, key)
        ci = sc.ci.get(key)
        rows.append(
            {
                **tags,
                "mode": sc.mode,
                "type": key,
                "f1": None if val is None else round(val, 4),
                "f1_ci_low": ci and round(ci[0], 4),
                "f1_ci_high": ci and round(ci[1], 4),
            }
        )
    return rows


def scorecard_markdown(sc: Scorecard, title: str) -> str:
    lines = [
        f"### {title} ({sc.mode}, {sc.n_docs} docs)",
        "",
        "| Type | n gold | n pred | P | R | F1 | 95% CI | Field acc. |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in (*ENTITY_TYPES, *REL_NAMES):
        ts = sc.types.get(name)
        if ts is None or ts.n_gold + ts.n_pred == 0:
            continue
        p, r, f = ts.prf
        flag = " †" if ts.n_gold < SMALL_N else ""
        lines.append(
            f"| {name}{flag} | {ts.n_gold} | {ts.n_pred} | {_f(p)} | {_f(r)} | {_f(f)} | {_ci(ts.f1_ci)} "
            f"| {_f(ts.field_acc)} |"
        )
    lines += [
        "",
        f"Entity macro-F1 **{_f(sc.entity_macro_f1)}** {_ci(sc.ci.get('entity_macro_f1'))} · "
        f"micro-F1 {_f(sc.entity_micro_f1)} {_ci(sc.ci.get('entity_micro_f1'))}  ",
        f"Relationship macro-F1 **{_f(sc.relation_macro_f1)}** {_ci(sc.ci.get('relation_macro_f1'))} · "
        f"micro-F1 {_f(sc.relation_micro_f1)} {_ci(sc.ci.get('relation_micro_f1'))}",
        "",
        f"† fewer than {SMALL_N} gold items: per-type F1 is unreliable.",
        "",
    ]
    return "\n".join(lines)


def write_report(run_dir: Path, cards: dict[str, Scorecard], tags: dict) -> None:
    """Write metrics.md, metrics.csv and errors.jsonl for a run. ``cards`` maps a label to a scorecard."""
    run_dir.mkdir(parents=True, exist_ok=True)
    md = [f"# Run {run_dir.name}", "", "```", json.dumps(tags, indent=2), "```", ""]
    rows = []
    for label, sc in cards.items():
        md.append(scorecard_markdown(sc, label))
        rows += scorecard_rows(sc, {**tags, "subset": label})
    (run_dir / "metrics.md").write_text("\n".join(md))
    fields: list[str] = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(run_dir / "metrics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(run_dir / "errors.jsonl", "w") as f:
        for label, sc in cards.items():
            if sc.mode != "strict":
                continue
            for e in sc.errors:
                f.write(json.dumps({"subset": label, **e}) + "\n")
