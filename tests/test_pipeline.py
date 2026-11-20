"""Offline smoke test: one real document through ingest -> extract (stubbed LLM) -> score -> graph -> chunks."""

import json

import pytest

from src import extract, llm
from src.config import RAW_PDF_DIR
from src.eval.metrics import score
from src.gold import load_gold
from src.graph import build_graph, coverage_limit_across_documents
from src.ingest import chunk_document, load_pdf
from src.resolve import Resolver

DOC = "PACK000002_04_policy_schedule"

CANNED = {
    "parties": [
        ["insurer", "Southern Cross Commercial Underwriters Pty Ltd", None, 1],
        ["insured", "Tide Gym Pty Ltd", "21 275 287 720", 1],
        ["broker", "Summit Risk Brokers Pty Ltd", None, 1],
    ],
    "policies": [["SC-2025-372491", 13020, 1]],
    "coverages": [
        ["public_liability", 10000000, 10000, 1],
        ["property", 2000000, 1000, 1],
        ["business_interruption", 500000, 10000, 1],
        ["management_liability", 5000000, 10000, 1],
    ],
    "locations": [],
    "claims": [],
    "dates": [["policy_start", "2025-12-02", 1], ["policy_end", "2026-12-01", 1]],
    "declared_total": None,
    "relationship_subject": "SC-2025-372491",
    "relationships": [
        ["HAS_INSURED", "Tide Gym Pty Ltd", 1],
        ["ISSUED_BY", "Southern Cross Commercial Underwriters Pty Ltd", 1],
        ["PLACED_BY", "Summit Risk Brokers Pty Ltd", 1],
        ["HAS_COVERAGE", "public_liability", 1],
        ["HAS_COVERAGE", "property", 1],
        ["HAS_COVERAGE", "business_interruption", 1],
        ["HAS_COVERAGE", "management_liability", 1],
    ],
}


@pytest.fixture
def stub_llm(monkeypatch):
    calls = []

    def fake_complete(model, system, user, **kw):
        calls.append(user)
        # first answer is invalid JSON-in-fences with a bad role, to exercise the retry path
        if len(calls) == 1:
            bad = dict(CANNED, parties=[["ceo", "Someone", None, 1]])
            return llm.LLMResult(text="```json\n" + json.dumps(bad) + "\n```", model=model)
        return llm.LLMResult(text=json.dumps(CANNED), model=model)

    monkeypatch.setattr(llm, "complete", fake_complete)
    return calls


def test_one_document_end_to_end(stub_llm):
    doc = load_pdf(RAW_PDF_DIR / f"{DOC}.pdf")
    assert "=== Page 1 ===" in doc.render() and doc.n_tokens < 1000

    ext, meta = extract.extract_document(doc, "gemini-flash-lite", "zero_shot_v1")
    assert meta["status"] == "valid_after_retry" and meta["attempts"] == 2
    assert "previous answer was invalid" in stub_llm[1]
    assert all(c.source_doc == DOC for c in ext.coverages)

    gold = {DOC: load_gold("real")[DOC]}
    sc = score(gold, {DOC: ext}, "strict", n_boot=0)
    assert sc.entity_macro_f1 == 1.0 and sc.relation_macro_f1 == 1.0

    G = build_graph({DOC: ext}, Resolver(llm_model=None))
    assert coverage_limit_across_documents(G, "SC-2025-372491", "Public Liability") == {DOC: 10_000_000}

    chunks = chunk_document(doc)
    assert chunks and all(c.doc_id == DOC and c.page == 1 for c in chunks)
    assert any("Public Liability" in c.text for c in chunks)


def test_salvage_drops_only_invalid_items():
    data = extract.from_compact(dict(CANNED, parties=[["ceo", "X", None, 1], ["insured", "Tide Gym", None, 1]]))
    ext, dropped = extract.salvage(data)
    assert dropped == 1 and [p.name for p in ext.parties] == ["Tide Gym"]


def test_parse_json_tolerates_chatter():
    assert extract.parse_json('Sure! ```json\n{"a": 1}\n``` done') == {"a": 1}
    with pytest.raises(ValueError):
        extract.parse_json("no json here")
