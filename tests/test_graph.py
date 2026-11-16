import copy

import pytest

from src.eval.detector import evaluate_flags
from src.gold import load_gold
from src.graph import (
    build_graph,
    claims_for_policy,
    coverage_limit_across_documents,
    coverages_for_policy,
    detect_inconsistencies,
    documents_mentioning,
    parties_for_policy,
)
from src.resolve import Resolver


@pytest.fixture(scope="module")
def gold():
    return load_gold("real")


@pytest.fixture(scope="module")
def G(gold):
    return build_graph(gold, Resolver(llm_model=None))


def test_resolver_layers():
    r = Resolver(llm_model=None)
    assert r.same("Greenleaf Property Services Pty Ltd", "Greenleaf Property Se rvices Pty Ltd").layer == "normalise"
    d = r.same("Harbourline Mutual Insurance Ltd", "Harbourline Mutual")
    assert d.same and d.layer == "fuzzy"
    assert not r.same("Pinewood Insurance Underwriting Agency", "Verity Insurance Underwriting Agency").same


def test_resolver_cluster_picks_longest_name():
    canon = Resolver(llm_model=None).cluster(["Tide Gym", "Tide Gym Pty Ltd", "Summit Risk Brokers Pty Ltd"])
    assert canon["Tide Gym"] == "Tide Gym Pty Ltd"
    assert canon["Summit Risk Brokers Pty Ltd"] == "Summit Risk Brokers Pty Ltd"


def test_queries(G):
    assert set(coverages_for_policy(G, "PI-2025-981268")) >= {"public_liability", "cyber"}
    limits = coverage_limit_across_documents(G, "SC-2025-372491", "Public Liability")
    assert limits["PACK000002_04_policy_schedule"] == 10_000_000
    assert limits["PACK000002_05_certificate_of_currency"] == 20_000_000
    parties = parties_for_policy(G, "PI-2025-981268")
    assert len(parties["HAS_INSURED: Greenleaf Property Services Pty Ltd"]) == 5
    assert "PACK000001_08_claim_report" in documents_mentioning(G, "Pinewood Underwriting", Resolver(llm_model=None))
    assert len(claims_for_policy(G, "SC-2025-372491")) == 3


def test_every_edge_has_provenance(G):
    for _, _, d in G.edges(data=True):
        if d["predicate"] != "PART_OF":
            assert d.get("source_doc") and d.get("page")


def test_detector_finds_all_dataset_flags_on_gold(G):
    res = evaluate_flags(detect_inconsistencies(G), ["PACK000001", "PACK000002"])
    assert res["found"] == 4 and res["missed"] == 0 and res["false_flags"] == 0


def test_detector_flags_injected_limit_conflict(gold):
    g = copy.deepcopy(gold)
    g["PACK000001_04_policy_schedule"].coverages[0].limit = 1  # schedule vs nothing else -> no conflict yet
    email = g["PACK000001_01_broker_submission_email"]
    email.coverages[0].limit = 999  # requested public liability now has a conflicting limit
    flags = detect_inconsistencies(build_graph(g, Resolver(llm_model=None)))
    assert any(f["flag_type"] == "limit_mismatch" and f["pack"] == "PACK000001" for f in flags)
