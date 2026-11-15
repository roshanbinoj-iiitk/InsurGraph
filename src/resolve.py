"""Layered entity resolution for party names.

1. Deterministic normalisation (lower-case, punctuation and legal suffixes stripped); names
   equal after removing all spaces also merge, which repairs PDF wraps like "Se rvices".
2. Fuzzy match (rapidfuzz scorer + threshold tuned on the dev pairs in
   ``data/gold/entity_pairs.json``).
3. Only for still-unresolved pairs in a grey zone: a cached ``is_same_entity`` LLM call
   (Gemini Flash Lite). Candidate pairs are restricted to the same entity type so the request
   count stays small.

Every decision is logged with the layer that made it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from src import llm
from src.config import GOLD_DIR
from src.extract import parse_json
from src.normalize import norm_name

SCORERS = {
    "ratio": fuzz.ratio,
    "token_sort_ratio": fuzz.token_sort_ratio,
    "token_set_ratio": fuzz.token_set_ratio,
    "WRatio": fuzz.WRatio,
}

# Tuned on the dev pairs by scripts/tune_resolution.py (see runs/resolution/).
DEFAULT_SCORER = "token_set_ratio"
DEFAULT_THRESHOLD = 100.0
GREY_ZONE_LOW = 50.0

SAME_ENTITY_SYSTEM = (
    "You decide whether two organisation names refer to the same real-world organisation, as they "
    "might appear in different insurance documents (abbreviations, missing legal suffixes, regional "
    'subsidiaries of one group count as the same). Answer with JSON: {"same": true|false}.'
)


def score(a: str, b: str, scorer: str = DEFAULT_SCORER) -> float:
    na, nb = norm_name(a) or "", norm_name(b) or ""
    return float(SCORERS[scorer](na, nb))


@dataclass
class Decision:
    a: str
    b: str
    same: bool
    layer: str
    score: float


@dataclass
class Resolver:
    scorer: str = DEFAULT_SCORER
    threshold: float = DEFAULT_THRESHOLD
    llm_model: str | None = "gemini-flash-lite"
    grey_low: float = GREY_ZONE_LOW
    log: list[Decision] = field(default_factory=list)

    def same(self, a: str, b: str, etype: str = "organisation") -> Decision:
        na, nb = norm_name(a) or "", norm_name(b) or ""
        s = score(a, b, self.scorer)
        if na == nb or na.replace(" ", "") == nb.replace(" ", ""):
            d = Decision(a, b, True, "normalise", s)
        elif s >= self.threshold:
            d = Decision(a, b, True, "fuzzy", s)
        elif self.llm_model and s >= self.grey_low:
            d = Decision(a, b, self._ask_llm(a, b, etype), "llm", s)
        else:
            d = Decision(a, b, False, "fuzzy", s)
        self.log.append(d)
        return d

    def _ask_llm(self, a: str, b: str, etype: str) -> bool:
        x, y = sorted([a, b])  # order-independent cache key
        user = f"Entity type: {etype}\nName A: {x}\nName B: {y}"
        res = llm.complete(self.llm_model, SAME_ENTITY_SYSTEM, user, json_mode=True, max_tokens=200)
        try:
            return bool(parse_json(res.text).get("same"))
        except ValueError:
            return False

    def cluster(self, names: list[str], etype: str = "organisation") -> dict[str, str]:
        """Map each name to a canonical representative (union-find over pairwise decisions).

        The canonical name is the longest variant (usually the full legal name).
        """
        uniq = sorted(set(n for n in names if n))
        parent = {n: n for n in uniq}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, a in enumerate(uniq):
            for b in uniq[i + 1 :]:
                if find(a) != find(b) and self.same(a, b, etype).same:
                    parent[find(a)] = find(b)
        groups: dict[str, list[str]] = {}
        for n in uniq:
            groups.setdefault(find(n), []).append(n)
        canon = {}
        for members in groups.values():
            rep = max(members, key=lambda m: (len(m), m))
            for m in members:
                canon[m] = rep
        return canon


def load_pairs(split: str | None = None) -> list[dict]:
    pairs = json.loads((GOLD_DIR / "entity_pairs.json").read_text())["pairs"]
    return [p for p in pairs if split is None or p["split"] == split]


def evaluate_pairs(resolver: Resolver, pairs: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    rows = []
    for p in pairs:
        d = resolver.same(p["a"], p["b"])
        gold = bool(p["same"])
        tp += d.same and gold
        fp += d.same and not gold
        fn += (not d.same) and gold
        tn += (not d.same) and (not gold)
        rows.append({**p, "pred": d.same, "layer": d.layer, "score": round(d.score, 1)})
    acc = (tp + tn) / len(pairs) if pairs else 0.0
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    return {
        "n": len(pairs),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "rows": rows,
    }
