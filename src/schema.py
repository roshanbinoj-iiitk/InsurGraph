"""Pydantic extraction schema.

Six entity types (party, policy, coverage, location, claim, date) and six relationship
predicates. Every item carries the page it was found on; ``source_doc`` is attached by the
pipeline after extraction so the graph has page-level provenance.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.normalize import norm_date, norm_money


class PartyRole(StrEnum):
    insured = "insured"
    insurer = "insurer"
    broker = "broker"
    interested_party = "interested_party"
    prior_insurer = "prior_insurer"
    loss_adjuster = "loss_adjuster"


class DateKind(StrEnum):
    policy_start = "policy_start"
    policy_end = "policy_end"
    valuation_date = "valuation_date"
    certificate_date = "certificate_date"
    report_date = "report_date"


class Predicate(StrEnum):
    HAS_INSURED = "HAS_INSURED"
    ISSUED_BY = "ISSUED_BY"
    PLACED_BY = "PLACED_BY"
    HAS_COVERAGE = "HAS_COVERAGE"
    COVERS_LOCATION = "COVERS_LOCATION"
    HAS_CLAIM = "HAS_CLAIM"


# Object entity type for each predicate (the subject is always a policy).
PREDICATE_OBJECT_TYPE = {
    Predicate.HAS_INSURED: "party",
    Predicate.ISSUED_BY: "party",
    Predicate.PLACED_BY: "party",
    Predicate.HAS_COVERAGE: "coverage",
    Predicate.COVERS_LOCATION: "location",
    Predicate.HAS_CLAIM: "claim",
}


class _Item(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    page: int | None = Field(default=None, description="1-based page number")
    source_doc: str | None = None


def _money(v):
    if v is None or v == "":
        return None
    return norm_money(v)


def _date(v):
    if v is None or v == "":
        return None
    return norm_date(v) or v  # keep unparseable text so evaluation counts it as wrong


class Party(_Item):
    role: PartyRole
    name: str
    abn: str | None = Field(default=None, description="ABN exactly as displayed")


class Policy(_Item):
    policy_number: str
    premium: float | None = None

    money_fields = field_validator("premium", mode="before")(_money)


class Coverage(_Item):
    coverage_type: str
    limit: float | None = None
    deductible: float | None = None

    money_fields = field_validator("limit", "deductible", mode="before")(_money)


class Location(_Item):
    location_no: int | None = None
    address: str
    total_declared_value: float | None = None
    currency: str | None = None

    money_fields = field_validator("total_declared_value", mode="before")(_money)

    @field_validator("location_no", mode="before")
    @classmethod
    def _loc_no(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            digits = "".join(ch for ch in v if ch.isdigit())
            return int(digits) if digits else None
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def _cur(cls, v):
        return v.strip().upper() if isinstance(v, str) and v.strip() else None


class Claim(_Item):
    claim_no: str
    loss_date: str | None = None
    reported_date: str | None = None
    category: str | None = None
    status: str | None = None
    incurred: float | None = None

    date_fields = field_validator("loss_date", "reported_date", mode="before")(_date)
    money_fields = field_validator("incurred", mode="before")(_money)


class KeyDate(_Item):
    kind: DateKind
    date: str

    date_fields = field_validator("date", mode="before")(_date)


class Relationship(_Item):
    subject: str = Field(description="policy number")
    predicate: Predicate
    object: str = Field(description="party name, coverage type, location no/address or claim no")


class DocumentExtraction(BaseModel):
    """Everything extracted from one document."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    doc_id: str | None = None
    parties: list[Party] = Field(default_factory=list)
    policies: list[Policy] = Field(default_factory=list)
    coverages: list[Coverage] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    dates: list[KeyDate] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    declared_total: float | None = Field(
        default=None, description="Statement of values displayed grand total"
    )

    money_fields = field_validator("declared_total", mode="before")(_money)

    def stamp_source(self, doc_id: str) -> DocumentExtraction:
        """Attach ``doc_id`` as ``source_doc`` on every item."""
        self.doc_id = doc_id
        for items in self.entity_lists().values():
            for it in items:
                it.source_doc = doc_id
        for rel in self.relationships:
            rel.source_doc = doc_id
        return self

    def entity_lists(self) -> dict[str, list[_Item]]:
        return {
            "party": self.parties,
            "policy": self.policies,
            "coverage": self.coverages,
            "location": self.locations,
            "claim": self.claims,
            "date": self.dates,
        }


ENTITY_TYPES = ("party", "policy", "coverage", "location", "claim", "date")
RELATIONSHIP_TYPES = tuple(p.value for p in Predicate)
