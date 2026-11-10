"""Normalisation used by gold building, evaluation, entity resolution and the graph.

Rules: dates to ISO, currency to numbers, names lower-cased and stripped of punctuation
and company suffixes, coverage names mapped to a small canonical list.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}


def _clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def norm_date(value: str | date | None) -> str | None:
    """Parse a date in the formats seen in Australian P&C documents into ISO ``YYYY-MM-DD``.

    Day-first is assumed for numeric dates (``09/06/2025`` is 9 June 2025).
    Returns None when the value cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = re.sub(r"\s+", "", str(value))  # PDF wrapping can split dates: "13/10/\n2027"
    if not s:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:T.*)?", s)
    if m:
        y, mo, d = map(int, m.groups())
        return _safe_date(y, mo, d)
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", s)
    if m:
        d, mo, y = map(int, m.groups())
        y = y + 2000 if y < 100 else y
        return _safe_date(y, mo, d)
    # "30April2025", "9-Jun-2025", "09Jun2025"
    m = re.fullmatch(r"(\d{1,2})[\-]?([A-Za-z]+)[\-,]?(\d{4})", s)
    if m:
        d, mon, y = m.groups()
        mo = _MONTHS.get(mon.lower())
        return _safe_date(int(y), mo, int(d)) if mo else None
    # "June9,2025"
    m = re.fullmatch(r"([A-Za-z]+)(\d{1,2}),?(\d{4})", s)
    if m:
        mon, d, y = m.groups()
        mo = _MONTHS.get(mon.lower())
        return _safe_date(int(y), mo, int(d)) if mo else None
    return None


def _safe_date(y: int, mo: int, d: int) -> str | None:
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def norm_money(value: str | float | int | None) -> float | None:
    """``"AUD $21,1 87"`` -> 21187.0; ``"$2.5m"`` -> 2500000.0. None if no number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).lower().replace("\n", "")
    mult = 1.0
    m = re.search(r"(\d[\d,\s]*(?:\.\d+)?)\s*(m|mil|million|k|thousand)\b", s)
    if m:
        mult = 1_000_000.0 if m.group(2).startswith("m") else 1_000.0
        s = m.group(1)
    digits = re.sub(r"[^\d.]", "", s)
    if not digits or digits == ".":
        return None
    try:
        return float(digits) * mult
    except ValueError:
        return None


def detect_currency(value: str | None) -> str | None:
    """Currency code mentioned in a money string (``"USD $3,413,719"`` -> ``"USD"``)."""
    if not value:
        return None
    m = re.search(r"\b(AUD|USD|NZD|GBP|EUR|SGD|CAD)\b", str(value).upper())
    if m:
        return m.group(1)
    if "A$" in str(value).upper():
        return "AUD"
    return None


_SUFFIXES = (
    "proprietary limited",
    "pty ltd",
    "pty limited",
    "pty",
    "limited",
    "ltd",
    "incorporated",
    "inc",
    "llc",
    "corporation",
    "corp",
    "company",
    "co",
    "plc",
)


def norm_name(value: str | None) -> str | None:
    """Lower-case, strip punctuation and legal suffixes (Pty Ltd, Inc, LLC, ...)."""
    if not value:
        return None
    s = value.lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = _clean_ws(s)
    changed = True
    while changed:
        changed = False
        for suf in _SUFFIXES:
            if s.endswith(" " + suf):
                s = s[: -len(suf) - 1].rstrip()
                changed = True
    return s or None


def norm_abn(value: str | None) -> str | None:
    """Australian Business Number as 11 digits (formatting removed)."""
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits or None


def abn_format(value: str | None) -> str | None:
    """Formatting pattern of a displayed ABN, e.g. ``'NN NNN NNN NNN'`` or ``'NNNNNNNNNNN'``."""
    if not value:
        return None
    return re.sub(r"\d", "N", str(value).strip())


_ADDR_ABBREV = {
    "street": "st",
    "road": "rd",
    "avenue": "ave",
    "parade": "pde",
    "boulevard": "bvd",
    "drive": "dr",
    "court": "ct",
    "place": "pl",
    "highway": "hwy",
    "lane": "ln",
    "terrace": "tce",
    "crescent": "cres",
}


def norm_address(value: str | None) -> str | None:
    if not value:
        return None
    s = re.sub(r"[^\w\s]", " ", value.lower())
    words = [_ADDR_ABBREV.get(w, w) for w in s.split()]
    return " ".join(words) or None


def norm_id(value: str | None) -> str | None:
    """Policy / claim numbers: upper-case, whitespace removed (handles PDF line breaks)."""
    if not value:
        return None
    s = re.sub(r"\s+", "", str(value)).upper()
    return s or None


def norm_text(value: str | None) -> str | None:
    if not value:
        return None
    s = re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", str(value)).lower())
    return _clean_ws(s) or None


CANONICAL_COVERAGES = (
    "public_liability",
    "property",
    "professional_indemnity",
    "business_interruption",
    "cyber",
    "management_liability",
    "motor",
    "workers_compensation",
    "product_liability",
    "other",
)

_COVERAGE_SYNONYMS = {
    "public_liability": (
        "public liability",
        "general liability",
        "public and products liability",
        "broadform liability",
        "pl",
        "cgl",
        "liability",
    ),
    "product_liability": ("products liability", "product liability"),
    "property": (
        "property",
        "material damage",
        "industrial special risks",
        "isr",
        "property damage",
        "buildings and contents",
        "fire and perils",
    ),
    "professional_indemnity": (
        "professional indemnity",
        "professional liability",
        "errors and omissions",
        "e and o",
        "pi",
    ),
    "business_interruption": (
        "business interruption",
        "loss of profits",
        "consequential loss",
        "bi",
        "business income",
    ),
    "cyber": ("cyber", "cyber liability", "cyber risk", "cyber and privacy"),
    "management_liability": (
        "management liability",
        "directors and officers",
        "d and o",
        "do",
        "statutory liability",
    ),
    "motor": ("motor", "motor vehicle", "commercial motor", "fleet"),
    "workers_compensation": ("workers compensation", "workers comp"),
}


def norm_coverage(value: str | None) -> str | None:
    """Map a coverage/section label to the canonical list (unknown labels -> ``'other'``)."""
    if not value:
        return None
    s = norm_text(value.replace("&", " and ").replace("_", " "))
    if not s:
        return None
    s = re.sub(r"\b(section|cover|coverage|insurance|policy)\b", " ", s)
    s = _clean_ws(s)
    if s.replace(" ", "_") in CANONICAL_COVERAGES:
        return s.replace(" ", "_")
    for canon, syns in _COVERAGE_SYNONYMS.items():
        if s in syns:
            return canon
    # Longest synonym first, so "management liability xyz" beats bare "liability".
    for syn, canon in _SYNONYMS_BY_LENGTH:
        if len(syn) > 3 and re.search(rf"\b{re.escape(syn)}\b", s):
            return canon
    return "other"


_SYNONYMS_BY_LENGTH = sorted(
    ((syn, canon) for canon, syns in _COVERAGE_SYNONYMS.items() for syn in syns),
    key=lambda pair: -len(pair[0]),
)
