"""Item normalisation and 1:1 matching of predicted vs gold items within a document.

Two modes:
* ``strict``: every field equal after normalisation.
* ``lenient``: names, addresses and free-text labels may differ up to a fuzzy-match threshold;
  numbers, dates, identifiers and roles still need to be equal.

An item counts as a true positive only when it is matched on its key *and* every field agrees
(under the mode). Pairs matched on the key but wrong in a field are reported as field errors,
which feed the error analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from src.normalize import (
    norm_abn,
    norm_address,
    norm_coverage,
    norm_date,
    norm_id,
    norm_money,
    norm_name,
    norm_text,
)
from src.schema import PREDICATE_OBJECT_TYPE, DocumentExtraction, Predicate

FUZZY_THRESHOLD = 90

# entity type -> (key fields, all compared fields, fuzzy-eligible fields)
SPEC: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "party": (("role", "name"), ("role", "name", "abn"), ("name",)),
    "policy": (("policy_number",), ("policy_number", "premium"), ()),
    "coverage": (("coverage_type",), ("coverage_type", "limit", "deductible"), ()),
    "location": (("location_no",), ("location_no", "address", "total_declared_value", "currency"), ("address",)),
    "claim": (
        ("claim_no",),
        ("claim_no", "loss_date", "reported_date", "category", "status", "incurred"),
        ("category", "status"),
    ),
    "date": (("kind",), ("kind", "date"), ()),
    "relationship": (("subject", "predicate", "object"), ("subject", "predicate", "object"), ("object",)),
}


def _num(v):
    n = norm_money(v)
    return None if n is None else round(n, 2)


def normalize_item(etype: str, item) -> dict:
    d = item.model_dump() if hasattr(item, "model_dump") else dict(item)
    if etype == "party":
        return {"role": d.get("role"), "name": norm_name(d.get("name")), "abn": norm_abn(d.get("abn"))}
    if etype == "policy":
        return {"policy_number": norm_id(d.get("policy_number")), "premium": _num(d.get("premium"))}
    if etype == "coverage":
        return {
            "coverage_type": norm_coverage(d.get("coverage_type")),
            "limit": _num(d.get("limit")),
            "deductible": _num(d.get("deductible")),
        }
    if etype == "location":
        return {
            "location_no": d.get("location_no"),
            "address": norm_address(d.get("address")),
            "total_declared_value": _num(d.get("total_declared_value")),
            "currency": (d.get("currency") or None) and d["currency"].upper(),
        }
    if etype == "claim":
        return {
            "claim_no": norm_id(d.get("claim_no")),
            "loss_date": norm_date(d.get("loss_date")) or d.get("loss_date"),
            "reported_date": norm_date(d.get("reported_date")) or d.get("reported_date"),
            "category": norm_text(d.get("category")),
            "status": norm_text(d.get("status")),
            "incurred": _num(d.get("incurred")),
        }
    if etype == "date":
        return {"kind": d.get("kind"), "date": norm_date(d.get("date")) or d.get("date")}
    if etype == "relationship":
        pred = d.get("predicate")
        return {"subject": norm_id(d.get("subject")), "predicate": pred, "object": norm_object(pred, d.get("object"))}
    raise ValueError(etype)


def norm_object(predicate: str, value) -> str | None:
    """Normalise a relationship object according to the predicate's object type."""
    if value is None:
        return None
    otype = PREDICATE_OBJECT_TYPE.get(Predicate(predicate)) if predicate in Predicate.__members__ else None
    s = str(value)
    if otype == "party":
        return norm_name(s)
    if otype == "coverage":
        return norm_coverage(s)
    if otype == "claim":
        return norm_id(s)
    if otype == "location":
        digits = "".join(ch for ch in s if ch.isdigit())
        return digits if digits and len(digits) <= 3 else norm_address(s)
    return norm_text(s)


def _fuzzy_eq(a, b) -> bool:
    if a is None or b is None:
        return a == b
    return fuzz.ratio(str(a).replace(" ", ""), str(b).replace(" ", "")) >= FUZZY_THRESHOLD


def field_eq(etype: str, fld: str, a, b, mode: str) -> bool:
    if a == b:
        return True
    if mode == "lenient" and fld in SPEC[etype][2]:
        return _fuzzy_eq(a, b)
    return False


def _key_eq(etype: str, g: dict, p: dict, mode: str) -> bool:
    keys = SPEC[etype][0]
    if etype == "location" and g.get("location_no") is None:
        keys = ("address",)  # unnumbered locations (trading address, incident location) key on address
        if mode == "strict":
            return g["address"] == p["address"]
        return _fuzzy_eq(g["address"], p["address"])
    return all(field_eq(etype, k, g.get(k), p.get(k), mode) for k in keys)


@dataclass
class MatchResult:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    fields_total: int = 0
    fields_correct: int = 0
    errors: list[dict] = field(default_factory=list)


def match_items(etype: str, gold: list, pred: list, mode: str = "strict", doc_id: str = "") -> MatchResult:
    g_norm = [normalize_item(etype, x) for x in gold]
    p_norm = [normalize_item(etype, x) for x in pred]
    fields = SPEC[etype][1]
    cands = []
    for gi, g in enumerate(g_norm):
        for pi, p in enumerate(p_norm):
            if _key_eq(etype, g, p, mode):
                score = sum(field_eq(etype, f, g.get(f), p.get(f), mode) for f in fields)
                cands.append((score, gi, pi))
    cands.sort(key=lambda c: (-c[0], c[1], c[2]))
    used_g, used_p = set(), set()
    res = MatchResult()
    for score, gi, pi in cands:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        res.fields_total += len(fields)
        res.fields_correct += score
        if score == len(fields):
            res.tp += 1
        else:
            bad = [f for f in fields if not field_eq(etype, f, g_norm[gi].get(f), p_norm[pi].get(f), mode)]
            res.errors.append(
                {"doc": doc_id, "type": etype, "kind": "field_error", "fields": bad,
                 "gold": g_norm[gi], "pred": p_norm[pi]}
            )
    for gi, g in enumerate(g_norm):
        if gi not in used_g:
            res.errors.append({"doc": doc_id, "type": etype, "kind": "missed", "gold": g})
    for pi, p in enumerate(p_norm):
        if pi not in used_p:
            res.errors.append({"doc": doc_id, "type": etype, "kind": "spurious", "pred": p})
    n_bad_pairs = len(used_g) - res.tp
    res.fn = len(g_norm) - res.tp
    res.fp = len(p_norm) - res.tp
    assert res.fn == (len(g_norm) - len(used_g)) + n_bad_pairs
    return res


def match_document(gold: DocumentExtraction, pred: DocumentExtraction, mode: str = "strict") -> dict[str, MatchResult]:
    """Per-type match results for one document; relationships are split by predicate."""
    out: dict[str, MatchResult] = {}
    g_lists, p_lists = gold.entity_lists(), pred.entity_lists()
    for etype in g_lists:
        out[etype] = match_items(etype, g_lists[etype], p_lists[etype], mode, gold.doc_id or "")
    for pred_type in Predicate:
        g_rel = [r for r in gold.relationships if r.predicate == pred_type.value]
        p_rel = [r for r in pred.relationships if r.predicate == pred_type.value]
        out[f"rel:{pred_type.value}"] = match_items("relationship", g_rel, p_rel, mode, gold.doc_id or "")
    return out
