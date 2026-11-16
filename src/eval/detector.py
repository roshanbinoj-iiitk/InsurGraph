"""Evaluate the inconsistency detector against labelled (dataset + seeded synthetic) flags.

Raw counts only (found / missed / extra), with every extra flag classified as corroborating,
true-but-unlabelled (hand-verified list) or false. With a handful of labelled flags a
percentage would overclaim.
"""

from __future__ import annotations

import json

from src.config import GOLD_DIR, RAW_DIR, SYNTH_DIR


def labelled_flags() -> dict[str, set[str]]:
    """pack -> set of labelled flag types (dataset red flags + synthetic seeded flags)."""
    out: dict[str, set[str]] = {}
    for line in open(RAW_DIR / "ground_truth.jsonl"):
        row = json.loads(line)
        out.setdefault(row["submission_pack_id"], set()).update(
            f["flag_type"] for f in json.loads(row["red_flags_json"])
        )
    synth = SYNTH_DIR / "red_flags.json"
    if synth.exists():
        for pack, flags in json.loads(synth.read_text()).items():
            out.setdefault(pack, set()).update(f["flag_type"] for f in flags)
    return out


def evaluate_flags(flags: list[dict], packs: list[str]) -> dict:
    labels = labelled_flags()
    extra_info = json.loads((GOLD_DIR / "unlabelled_inconsistencies.json").read_text())
    cases, found, missed, extra_true, corroborating, false = [], 0, 0, 0, 0, 0
    for pack in packs:
        pf = [f for f in flags if f["pack"] == pack]
        types = {f["flag_type"] for f in pf}
        for lab in sorted(labels.get(pack, ())):
            hit = lab in types
            found += hit
            missed += not hit
            ex = next((f for f in pf if f["flag_type"] == lab), None)
            cases.append(
                {
                    "pack": pack,
                    "flag_type": lab,
                    "outcome": "found" if hit else "missed",
                    "detail": ex["detail"] if ex else "",
                }
            )
        for f in pf:
            if f["flag_type"] in labels.get(pack, ()):
                continue
            if any(
                c["flag_type"] == f["flag_type"]
                and c["attribute"] == f["attribute"]
                and c["labelled"] in labels.get(pack, ())
                for c in extra_info["corroborating"]
            ):
                outcome = "corroborating"
                corroborating += 1
            elif any(
                u["pack"] == pack and u["flag_type"] == f["flag_type"] and u["node_contains"] in f["node"]
                for u in extra_info["unlabelled"]
            ):
                outcome = "true (unlabelled)"
                extra_true += 1
            else:
                outcome = "false flag"
                false += 1
            cases.append({"pack": pack, "flag_type": f["flag_type"], "outcome": outcome, "detail": f["detail"]})
    return {
        "labelled": found + missed,
        "found": found,
        "missed": missed,
        "corroborating": corroborating,
        "true_unlabelled": extra_true,
        "false_flags": false,
        "cases": cases,
    }


def flags_markdown(title: str, res: dict) -> str:
    lines = [
        f"### {title}",
        "",
        f"Labelled flags: **{res['found']} found / {res['missed']} missed** of {res['labelled']}; extra flags: "
        f"{res['corroborating']} corroborating, {res['true_unlabelled']} true but unlabelled, "
        f"**{res['false_flags']} false**.",
        "",
        "| Pack | Flag | Outcome | Detail |",
        "|---|---|---|---|",
    ]
    lines += [f"| {c['pack']} | {c['flag_type']} | {c['outcome']} | {c['detail']} |" for c in res["cases"]]
    return "\n".join(lines) + "\n"
