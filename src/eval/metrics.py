"""Precision / recall / F1 per entity and relationship type, macro averages and bootstrap CIs."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from src.eval.matching import MatchResult, match_document
from src.schema import ENTITY_TYPES, RELATIONSHIP_TYPES, DocumentExtraction

SMALL_N = 10  # below this many gold items a per-type F1 is flagged as unreliable


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """P, R, F1. Conventions: no predictions and no gold -> 1.0 (nothing to find, nothing wrong)."""
    if tp + fp + fn == 0:
        return 1.0, 1.0, 1.0
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


@dataclass
class TypeScore:
    name: str
    tp: int
    fp: int
    fn: int
    fields_total: int
    fields_correct: int
    f1_ci: tuple[float, float] | None = None

    @property
    def n_gold(self) -> int:
        return self.tp + self.fn

    @property
    def n_pred(self) -> int:
        return self.tp + self.fp

    @property
    def prf(self):
        return prf(self.tp, self.fp, self.fn)

    @property
    def field_acc(self) -> float | None:
        return self.fields_correct / self.fields_total if self.fields_total else None


def _aggregate(per_doc: dict[str, dict[str, MatchResult]], doc_ids) -> dict[str, TypeScore]:
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    for d in doc_ids:
        for t, m in per_doc[d].items():
            a = acc[t]
            a[0] += m.tp
            a[1] += m.fp
            a[2] += m.fn
            a[3] += m.fields_total
            a[4] += m.fields_correct
    return {t: TypeScore(t, *v) for t, v in acc.items()}


def _macro(scores: dict[str, TypeScore], names) -> float | None:
    vals = [scores[n].prf[2] for n in names if n in scores and scores[n].n_gold > 0]
    return sum(vals) / len(vals) if vals else None


def _micro(scores: dict[str, TypeScore], names) -> float:
    tp = sum(scores[n].tp for n in names if n in scores)
    fp = sum(scores[n].fp for n in names if n in scores)
    fn = sum(scores[n].fn for n in names if n in scores)
    return prf(tp, fp, fn)[2]


REL_NAMES = tuple(f"rel:{r}" for r in RELATIONSHIP_TYPES)


@dataclass
class Scorecard:
    mode: str
    n_docs: int
    types: dict[str, TypeScore]
    entity_macro_f1: float | None
    entity_micro_f1: float
    relation_macro_f1: float | None
    relation_micro_f1: float
    ci: dict[str, tuple[float, float]]
    errors: list[dict]


def score(
    gold: dict[str, DocumentExtraction],
    pred: dict[str, DocumentExtraction],
    mode: str = "strict",
    n_boot: int = 1000,
    seed: int = 13,
) -> Scorecard:
    """Score predictions against gold over the documents in ``gold``.

    Missing predictions count as empty extractions. Confidence intervals are 95% percentile
    bootstrap intervals from resampling documents with replacement.
    """
    doc_ids = sorted(gold)
    per_doc = {}
    errors: list[dict] = []
    for d in doc_ids:
        p = pred.get(d) or DocumentExtraction(doc_id=d)
        g = gold[d]
        if g.doc_id is None:
            g.doc_id = d
        per_doc[d] = match_document(g, p, mode)
        for m in per_doc[d].values():
            errors += m.errors
    types = _aggregate(per_doc, doc_ids)

    def summary(sc):
        return {
            "entity_macro_f1": _macro(sc, ENTITY_TYPES),
            "entity_micro_f1": _micro(sc, ENTITY_TYPES),
            "relation_macro_f1": _macro(sc, REL_NAMES),
            "relation_micro_f1": _micro(sc, REL_NAMES),
            **{t: sc[t].prf[2] if t in sc and sc[t].n_gold + sc[t].n_pred else None for t in sc},
        }

    point = summary(types)
    ci: dict[str, tuple[float, float]] = {}
    if n_boot and len(doc_ids) > 1:
        rng = random.Random(seed)
        samples: dict[str, list[float]] = defaultdict(list)
        for _ in range(n_boot):
            res = [rng.choice(doc_ids) for _ in doc_ids]
            s = summary(_aggregate(per_doc, res))
            for k, v in s.items():
                if v is not None:
                    samples[k].append(v)
        for k, vals in samples.items():
            vals.sort()
            ci[k] = (vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))])
    for t, ts in types.items():
        ts.f1_ci = ci.get(t)
    return Scorecard(
        mode=mode,
        n_docs=len(doc_ids),
        types=types,
        entity_macro_f1=point["entity_macro_f1"],
        entity_micro_f1=point["entity_micro_f1"],
        relation_macro_f1=point["relation_macro_f1"],
        relation_micro_f1=point["relation_micro_f1"],
        ci=ci,
        errors=errors,
    )
