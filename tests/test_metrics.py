import copy

import pytest

from src.eval.matching import match_items
from src.eval.metrics import prf, score
from src.gold import load_gold
from src.schema import Claim, DocumentExtraction, Party


@pytest.fixture(scope="module")
def gold():
    return load_gold("real")


def test_empty_extractor_scores_zero(gold):
    sc = score(gold, {}, "strict", n_boot=50)
    assert sc.entity_macro_f1 == 0.0
    assert sc.relation_macro_f1 == 0.0
    assert sc.entity_micro_f1 == 0.0


@pytest.mark.parametrize("mode", ["strict", "lenient"])
def test_gold_copy_scores_one(gold, mode):
    sc = score(gold, copy.deepcopy(gold), mode, n_boot=50)
    assert sc.entity_macro_f1 == 1.0
    assert sc.relation_macro_f1 == 1.0
    assert all(ts.prf[2] == 1.0 for ts in sc.types.values() if ts.n_gold)
    assert sc.ci["entity_macro_f1"] == (1.0, 1.0)


def test_prf_values():
    assert prf(0, 0, 0) == (1.0, 1.0, 1.0)
    assert prf(1, 1, 0) == (0.5, 1.0, pytest.approx(2 / 3))
    assert prf(0, 3, 2) == (0.0, 0.0, 0.0)


def test_strict_vs_lenient_names():
    g = [Party(role="insured", name="Greenleaf Property Services Pty Ltd")]
    p = [Party(role="insured", name="Greenleaf Property Se rvices Pty Ltd")]
    assert match_items("party", g, p, "strict").tp == 0
    assert match_items("party", g, p, "lenient").tp == 1
    # roles are never fuzzy
    p2 = [Party(role="insurer", name="Greenleaf Property Services Pty Ltd")]
    assert match_items("party", g, p2, "lenient").tp == 0


def test_field_error_counts_as_fp_and_fn():
    g = [Claim(claim_no="CLM-1", loss_date="2020-09-24", incurred=100)]
    p = [Claim(claim_no="CLM-1", loss_date="2027-10-13", incurred=100)]
    m = match_items("claim", g, p, "strict")
    assert (m.tp, m.fp, m.fn) == (0, 1, 1)
    assert m.errors[0]["kind"] == "field_error" and m.errors[0]["fields"] == ["loss_date"]
    assert m.fields_correct == m.fields_total - 1


def test_one_to_one_matching():
    g = [Claim(claim_no="C1")]
    p = [Claim(claim_no="C1"), Claim(claim_no="C1")]
    m = match_items("claim", g, p, "strict")
    assert (m.tp, m.fp, m.fn) == (1, 1, 0)


def test_partial_prediction_between_bounds(gold):
    half = {}
    for d, g in gold.items():
        h = copy.deepcopy(g)
        h.claims = h.claims[: len(h.claims) // 2]
        h.relationships = []
        half[d] = h
    sc = score(gold, half, "strict", n_boot=0)
    assert 0 < sc.entity_macro_f1 < 1
    assert sc.types["party"].prf[2] == 1.0
    assert sc.types["claim"].prf[1] < 1.0


def test_missing_doc_counts_as_empty(gold):
    one = {k: v for k, v in list(gold.items())[:1]}
    sc = score(gold, one, "strict", n_boot=0)
    assert 0 < sc.entity_micro_f1 < 1
    assert DocumentExtraction() is not None
