"""Build the gold set: dataset ground truth converted to the schema, plus hand labels.

Each document type prints a known subset of the pack-level facts; ``_from_row`` encodes which
fields each template displays (verified against the PDF text) and applies the engineered
overrides so the gold holds the value actually printed. ``data/gold/hand_labels.json`` adds
what the dataset does not label (relationships, the application's declared-claims table, SOV
"declared as at" dates) and removes repeated row fields a specific document does not print.

Every item carries ``provenance`` ("dataset" or "hand") in the written gold file.

Usage: python -m src.gold   -> writes data/gold/gold.jsonl and prints item counts.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.config import GOLD_DIR, RAW_DIR, SYNTH_DIR, split_of
from src.normalize import norm_coverage
from src.schema import ENTITY_TYPES, DocumentExtraction

LIST_KEY = {
    "party": "parties",
    "policy": "policies",
    "coverage": "coverages",
    "location": "locations",
    "claim": "claims",
    "date": "dates",
}


def _jl(row: dict, key: str):
    raw = row.get(key)
    if raw in (None, ""):
        return None
    return json.loads(raw) if isinstance(raw, str) else raw


def _coverages_from_list(text: str) -> list[dict]:
    return [{"coverage_type": norm_coverage(c), "page": 1} for c in text.split(",") if c.strip()]


def _from_row(row: dict) -> dict:
    """Dataset-derived gold for one document (dict in the DocumentExtraction shape)."""
    t = row["document_type"]
    flags = _jl(row, "red_flags_json") or []
    overrides: dict = {}
    for f in flags:
        if f["target_doc_type"] == t:
            overrides.update(f["overrides"])

    insured = row["insured_business_name"]
    abn = row.get("displayed_abn") or row["insured_abn"]
    pol = row["policy_number"]
    start, end = row["policy_period_start"], row["policy_period_end"]
    out: dict = {k: [] for k in LIST_KEY.values()}

    def party(role, name, abn_=None, page=1):
        out["parties"].append({"role": role, "name": name, "abn": abn_, "page": page})

    def date(kind, value, page=1):
        out["dates"].append({"kind": kind, "date": value, "page": page})

    if t == "broker_submission_email":
        party("broker", row["broker_company"])
        party("insurer", row["insurer_name"])
        party("insured", insured)
        out["coverages"] = _coverages_from_list(row.get("requested_coverage", ""))
        date("policy_start", row["target_inception_date"])

    elif t == "loss_run_report":
        party("insured", insured, abn)
        party("insurer", row["insurer_name"])
        out["policies"].append({"policy_number": pol, "page": 1})
        date("valuation_date", row["valuation_date"])
        for i, c in enumerate(_jl(row, "claim_rows_json")):
            loss_date = c["loss_date"]
            if overrides.get("claim_index") == i and "displayed_loss_date" in overrides:
                loss_date = overrides["displayed_loss_date"]
            out["claims"].append(
                {
                    "claim_no": c["claim_no"],
                    "loss_date": loss_date,
                    "reported_date": c["reported_date"],
                    "category": c["category"],
                    "status": c["status"],
                    "incurred": c["incurred"],
                    "page": 1,
                }
            )

    elif t == "statement_of_values":
        party("broker", row["broker_company"])
        party("insured", insured, abn)
        out["policies"].append({"policy_number": pol, "page": 1})
        date("policy_start", start)
        date("policy_end", end)
        cur_idx = overrides.get("currency_mismatch_loc_index")
        for i, loc in enumerate(_jl(row, "location_rows_json")):
            out["locations"].append(
                {
                    "location_no": loc["location_no"],
                    "address": loc["address"],
                    "total_declared_value": loc["total_declared_value"],
                    "currency": overrides.get("currency_mismatch_currency", "AUD") if i == cur_idx else "AUD",
                    "page": 1,
                }
            )
        out["declared_total"] = row.get("displayed_total_declared_value")

    elif t == "policy_schedule":
        party("insurer", row["insurer_name"])
        party("insured", insured, abn)
        party("broker", row["broker_company"])
        out["policies"].append({"policy_number": pol, "premium": row.get("premium"), "page": 1})
        date("policy_start", start)
        date("policy_end", end)
        limits = _jl(row, "limits_json") or {}
        deds = _jl(row, "deductibles_json") or {}
        for cov, lim in limits.items():
            out["coverages"].append(
                {"coverage_type": norm_coverage(cov), "limit": lim, "deductible": deds.get(cov), "page": 1}
            )
        for loc in _jl(row, "displayed_locations_json") or []:
            out["locations"].append(
                {"location_no": loc["location_no"], "address": loc["displayed_address"], "page": 1}
            )

    elif t == "certificate_of_currency":
        party("insurer", row["insurer_name"])
        party("insured", row.get("displayed_insured_name") or insured, abn)
        party("interested_party", row["interested_party_name"])
        out["policies"].append({"policy_number": row.get("displayed_policy_number") or pol, "page": 1})
        date("certificate_date", row["certificate_date"])
        date("policy_start", start)
        date("policy_end", row.get("displayed_period_end") or end)
        for cov, lim in (_jl(row, "coc_limits_json") or {}).items():
            out["coverages"].append({"coverage_type": norm_coverage(cov), "limit": lim, "page": 1})
        out["locations"].append({"address": row["insured_address"], "page": 1})

    elif t == "insurance_application":
        party("insured", insured, abn)
        party("prior_insurer", row["prior_insurer"])
        out["coverages"] = _coverages_from_list(row.get("application_requested_coverage", ""))
        out["locations"].append({"address": row["insured_address"], "page": 1})
        date("policy_start", start)

    elif t == "fnol_form":
        party("insured", insured, abn)
        party("insurer", row["insurer_name"])
        out["policies"].append({"policy_number": pol, "page": 1})
        date("policy_start", start)
        date("policy_end", end)
        out["claims"].append(
            {
                "claim_no": row["fnol_claim_no"],
                "loss_date": row["fnol_loss_date"],
                "reported_date": row["fnol_reported_date"],
                "category": row["fnol_category"],
                "status": row["fnol_status"],
                "incurred": row["fnol_estimated_loss"],
                "page": 1,
            }
        )
        out["locations"].append({"address": row["fnol_incident_location"], "page": 1})

    elif t == "claim_report":
        party("insured", insured)
        party("insurer", row["insurer_name"])
        party("loss_adjuster", row["report_adjuster_firm"])
        out["policies"].append({"policy_number": pol, "page": 1})
        date("report_date", row["report_date"])
        out["claims"].append(
            {
                "claim_no": row["report_claim_no"],
                "loss_date": row["report_loss_date"],
                "category": row["report_category"],
                "status": row["report_status"],
                "incurred": row["report_incurred"],
                "page": 1,
            }
        )
    else:
        raise ValueError(f"unknown document type {t}")
    return out


_KEY_FIELD = {"party": "role", "coverage": "coverage_type", "location": "location_no", "claim": "claim_no",
              "date": "kind", "policy": "policy_number"}


def _apply_hand(doc: dict, hand: dict) -> dict:
    for etype, key in hand.get("remove", []):
        lk = LIST_KEY[etype]
        doc[lk] = [] if key == "*" else [it for it in doc[lk] if str(it.get(_KEY_FIELD[etype])) != key]
    for lk, items in hand.get("add", {}).items():
        doc[lk] += [{**it, "provenance": "hand"} for it in items]
    doc["relationships"] = [
        {"subject": s, "predicate": p, "object": o, "page": pg, "provenance": "hand"}
        for s, p, o, pg in hand.get("relationships", [])
    ]
    return doc


def build_real_gold() -> dict[str, dict]:
    rows = [json.loads(line) for line in open(RAW_DIR / "ground_truth.jsonl")]
    hand_all = json.loads((GOLD_DIR / "hand_labels.json").read_text())
    gold = {}
    for row in rows:
        doc_id = Path(row["pdf_filename"]).stem
        doc = _from_row(row)
        for lk in LIST_KEY.values():
            doc[lk] = [{**it, "provenance": "dataset"} for it in doc[lk]]
        doc = _apply_hand(doc, hand_all.get(doc_id, {}))
        doc["doc_id"] = doc_id
        gold[doc_id] = doc
    return gold


def load_gold(source: str = "real") -> dict[str, DocumentExtraction]:
    """Validated gold extractions keyed by doc id (``real``, ``synthetic`` or ``all``)."""
    files = []
    if source in ("real", "all"):
        files.append(GOLD_DIR / "gold.jsonl")
    if source in ("synthetic", "all"):
        files.append(SYNTH_DIR / "gold.jsonl")
    out = {}
    for f in files:
        if not f.exists():
            continue
        for line in open(f):
            d = json.loads(line)
            out[d["doc_id"]] = DocumentExtraction.model_validate(d).stamp_source(d["doc_id"])
    return out


def count_items(gold: dict[str, DocumentExtraction], provenance_src: dict | None = None) -> dict:
    counts: Counter = Counter()
    for doc_id, g in gold.items():
        split = split_of(doc_id)
        for etype, items in g.entity_lists().items():
            counts[(split, etype)] += len(items)
        counts[(split, "relationship")] += len(g.relationships)
    return counts


def main() -> None:
    gold = build_real_gold()
    out = GOLD_DIR / "gold.jsonl"
    with open(out, "w") as f:
        for doc_id in sorted(gold):
            DocumentExtraction.model_validate(gold[doc_id])  # validates
            f.write(json.dumps(gold[doc_id]) + "\n")
    validated = load_gold("real")
    prov = Counter()
    for d in gold.values():
        for lk in list(LIST_KEY.values()) + ["relationships"]:
            for it in d[lk]:
                prov[it["provenance"]] += 1
    counts = count_items(validated)
    print(f"wrote {out} ({len(validated)} documents, all validate)")
    print("provenance:", dict(prov))
    for split in ("dev", "test"):
        print(split, {t: counts[(split, t)] for t in (*ENTITY_TYPES, "relationship")})


if __name__ == "__main__":
    main()
