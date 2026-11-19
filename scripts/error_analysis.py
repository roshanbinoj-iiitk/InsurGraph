"""Count and categorise extraction errors (strict mode) for one or more runs.

Usage: python scripts/error_analysis.py runs/extraction/dev/<config> [...]
Writes runs/error_analysis/<split>__<config>.md with category counts and examples.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RUNS_DIR  # noqa: E402


def categorise(e: dict, spurious_by_doc: dict) -> str:
    t, kind = e["type"], e["kind"]
    if kind == "field_error":
        f = e["fields"]
        if t == "party" and f == ["abn"]:
            return "ABN missing/reformatted"
        if t == "claim" and set(f) <= {"loss_date", "reported_date"}:
            return "claim date wrong"
        if t == "claim" and set(f) <= {"category", "status"}:
            return "claim label wording"
        if t == "location" and "currency" in f:
            return "row currency wrong (symbol not normalised)"
        if t == "location" and set(f) <= {"address"}:
            return "address wording / wrap"
        if t in ("coverage",) and set(f) & {"limit", "deductible"}:
            return "limit/deductible value wrong"
        return f"{t}: field {'+'.join(f)} wrong"
    if kind == "missed":
        g = e["gold"]
        if t == "party":
            same_name = [
                s for s in spurious_by_doc[e["doc"]] if s["type"] == "party" and s["pred"].get("name") == g.get("name")
            ]
            if same_name:
                return "party role confusion"
            return f"party missed ({g.get('role')})"
        if t.startswith("rel") or t == "relationship":
            return "relationship missed"
        return f"{t} missed"
    # spurious
    p = e["pred"]
    if t == "coverage" and p.get("coverage_type") == "other":
        return "sub-limit / endorsement extracted as coverage"
    if t == "party":
        return f"spurious party ({p.get('role')})"
    if t == "relationship":
        return "spurious relationship"
    return f"spurious {t}"


def analyse(run_dir: Path) -> str:
    errors = [json.loads(line) for line in open(run_dir / "errors.jsonl")]
    errors = [e for e in errors if e["subset"].endswith("strict")]
    spurious = defaultdict(list)
    for e in errors:
        if e["kind"] == "spurious":
            spurious[e["doc"]].append(e)
    cats: Counter = Counter()
    examples: dict[str, list] = defaultdict(list)
    for e in errors:
        c = f"{e['subset'].split('/')[0]}: {categorise(e, spurious)}"
        cats[c] += 1
        if len(examples[c]) < 2:
            examples[c].append(e)
    lines = [
        f"# Error analysis: {run_dir.parent.name} / {run_dir.name}",
        "",
        f"{len(errors)} strict-mode errors (a field error counts once; it costs one FP and one FN).",
        "",
        "| Category | Count |",
        "|---|---|",
    ]
    lines += [f"| {c} | {n} |" for c, n in cats.most_common()]
    lines += ["", "## Examples", ""]
    for c, _ in cats.most_common(8):
        lines.append(f"**{c}**")
        for e in examples[c]:
            lines.append(f"- `{e['doc']}`: gold={json.dumps(e.get('gold'))} pred={json.dumps(e.get('pred'))}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    out = RUNS_DIR / "error_analysis"
    out.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[1:]:
        d = Path(arg)
        md = analyse(d)
        (out / f"{d.parent.name}__{d.name}.md").write_text(md)
        print(md)


if __name__ == "__main__":
    main()
