import pytest
from pydantic import ValidationError

from src.gold import load_gold
from src.schema import Claim, Coverage, DocumentExtraction, KeyDate, Location, Relationship


def test_money_and_date_coercion():
    cov = Coverage(coverage_type="public_liability", limit="AUD $20,000,000", deductible="AUD $10,000")
    assert cov.limit == 20_000_000 and cov.deductible == 10_000
    claim = Claim(claim_no="CLM-1", loss_date="13/10/2027", incurred="AUD $21,187")
    assert claim.loss_date == "2027-10-13" and claim.incurred == 21187
    assert KeyDate(kind="policy_end", date="8 June 2026").date == "2026-06-08"


def test_location_number_and_currency():
    loc = Location(location_no="#2", address="83 Crossing Way", currency=" usd ")
    assert loc.location_no == 2 and loc.currency == "USD"


def test_invalid_enum_rejected():
    with pytest.raises(ValidationError):
        Relationship(subject="P1", predicate="OWNS", object="x")
    with pytest.raises(ValidationError):
        DocumentExtraction.model_validate({"parties": [{"role": "ceo", "name": "x"}]})


def test_stamp_source_sets_provenance():
    doc = DocumentExtraction.model_validate(
        {"claims": [{"claim_no": "C1"}], "relationships": [{"subject": "P", "predicate": "HAS_CLAIM", "object": "C1"}]}
    ).stamp_source("DOC1")
    assert doc.claims[0].source_doc == "DOC1"
    assert doc.relationships[0].source_doc == "DOC1"


def test_gold_set_loads_and_validates():
    gold = load_gold("real")
    assert len(gold) == 14
    total = sum(len(v) for g in gold.values() for v in g.entity_lists().values())
    assert total > 100
    assert sum(len(g.relationships) for g in gold.values()) >= 50
