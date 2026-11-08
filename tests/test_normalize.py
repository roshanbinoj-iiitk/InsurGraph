import pytest

from src.normalize import (
    abn_format,
    detect_currency,
    norm_abn,
    norm_address,
    norm_coverage,
    norm_date,
    norm_id,
    norm_money,
    norm_name,
)


@pytest.mark.parametrize(
    "raw,iso",
    [
        ("09/06/2025", "2025-06-09"),
        ("13/10/\n2027", "2027-10-13"),
        ("2025-06-09", "2025-06-09"),
        ("30 April 2025", "2025-04-30"),
        ("9-Jun-2025", "2025-06-09"),
        ("June 9, 2025", "2025-06-09"),
        ("31/02/2025", None),
        ("not a date", None),
        (None, None),
    ],
)
def test_norm_date(raw, iso):
    assert norm_date(raw) == iso


@pytest.mark.parametrize(
    "raw,value",
    [
        ("AUD $21,1 87", 21187.0),
        ("USD $3,413,719", 3413719.0),
        ("$2.5m", 2_500_000.0),
        ("A$750k", 750_000.0),
        ("1,000,000.00 AUD", 1_000_000.0),
        (5000, 5000.0),
        ("-", None),
        (None, None),
    ],
)
def test_norm_money(raw, value):
    assert norm_money(raw) == value


def test_currency_detection():
    assert detect_currency("USD $3,413,719") == "USD"
    assert detect_currency("A$1,000") == "AUD"
    assert detect_currency("$1,000") is None


@pytest.mark.parametrize(
    "a,b",
    [
        ("Greenleaf Property Services Pty Ltd", "greenleaf property services"),
        ("Acme, Inc.", "acme"),
        ("Zurich American Insurance Company", "zurich american insurance"),
        ("Smith & Sons LLC", "smith and sons"),
    ],
)
def test_norm_name(a, b):
    assert norm_name(a) == b


def test_abn():
    assert norm_abn("21 275 287 720") == norm_abn("21275287720") == "21275287720"
    assert abn_format("21 275 287 720") == "NN NNN NNN NNN"
    assert abn_format("21275287720") == "NNNNNNNNNNN"


@pytest.mark.parametrize(
    "label,canon",
    [
        ("Public Liability", "public_liability"),
        ("General Liability", "public_liability"),
        ("Management Liability Section", "management_liability"),
        ("Directors & Officers", "management_liability"),
        ("Material Damage", "property"),
        ("Loss of Profits", "business_interruption"),
        ("Cyber Liability", "cyber"),
        ("Professional Indemnity", "professional_indemnity"),
        ("Loss of Documents Sub-limit", "other"),
    ],
)
def test_norm_coverage(label, canon):
    assert norm_coverage(label) == canon


def test_address_and_ids():
    assert norm_address("336 Riverside Parade, Launceston TAS") == norm_address("336 Riverside Pde Launceston TAS")
    assert norm_id("CLM-2020-\n27293") == "CLM-2020-27293"
