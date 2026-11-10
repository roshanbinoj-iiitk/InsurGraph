"""Synthetic submission packs generated from fact records (Gate 1 fallback).

Facts first, documents second: each pack is a structured fact record (insured, insurer,
broker, policy, coverages, locations, claims) rendered into four documents (policy schedule,
statement of values, loss run, certificate of currency) with code templates. The gold labels
are written from the same values the templates print, so they are correct by construction.
No LLM is involved, so the synthetic data cannot leak an extractor's own biases.

Leakage control: dev and test use **disjoint template styles** and **different random seeds**.
Inconsistencies are seeded programmatically (one value changed in one document) and recorded
in ``data/synthetic/red_flags.json``.

Usage: python -m src.synth   -> data/synthetic/{pdfs/, gold.jsonl, facts.jsonl, red_flags.json}
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

import pymupdf

from src.config import SYNTH_DIR
from src.schema import DocumentExtraction

# --------------------------------------------------------------------------------------------
# Fact vocabularies (all fictional)

INSURED_FIRST = ["Bluewater", "Ironbark", "Saltbush", "Coral Bay", "Redgum", "Kestrel", "Wattle Grove",
                 "Southerly", "Granite Peak", "Magpie", "Lighthouse", "Banksia", "Copperleaf", "Tallowwood"]
INDUSTRIES = [
    ("Bakery", "Commercial Bakery"), ("Logistics", "Warehouse / Distribution"), ("Dental", "Dental Clinic"),
    ("Joinery", "Timber Joinery Workshop"), ("Cafe", "Cafe / Restaurant"), ("Engineering", "Light Engineering"),
    ("Printing", "Print Shop"), ("Veterinary", "Veterinary Clinic"), ("Brewing", "Craft Brewery"),
]
INSURERS = [
    ("Harbourline Mutual Insurance Ltd", "Harbourline Mutual"),
    ("Eastgate General Insurance Limited", "Eastgate General"),
    ("Tasman Ridge Underwriting Agency Pty Ltd", "Tasman Ridge Underwriting"),
    ("Kookaburra Commercial Insurance Co", "Kookaburra Commercial"),
    ("Meridian Specialty Underwriters Pty Ltd", "Meridian Specialty"),
    ("Blackwood Assurance Limited", "Blackwood Assurance"),
]
BROKERS = ["Northshore Risk Partners Pty Ltd", "Clearwater Insurance Brokers Pty Ltd",
           "Pacific Crest Brokers Pty Ltd", "Anchor Point Risk Services Pty Ltd", "Highline Brokers Pty Ltd"]
STREETS = ["Wattle", "Harbour", "Station", "Mill", "Quarry", "Ocean", "Bridge", "Foundry", "Orchard", "Railway"]
STREET_TYPES = ["St", "Rd", "Ave", "Pde", "Dr", "Ct"]
SUBURBS = [("Geelong", "VIC", "3220"), ("Bendigo", "VIC", "3550"), ("Toowoomba", "QLD", "4350"),
           ("Cairns", "QLD", "4870"), ("Newcastle", "NSW", "2300"), ("Wagga Wagga", "NSW", "2650"),
           ("Bunbury", "WA", "6230"), ("Darwin", "NT", "0800"), ("Mount Gambier", "SA", "5290"),
           ("Devonport", "TAS", "7310")]
COVERAGES = {
    "public_liability": ("Public Liability", [5_000_000, 10_000_000, 20_000_000], [1_000, 2_500, 5_000, 10_000]),
    "property": ("Property", [1_000_000, 2_000_000, 5_000_000, 7_500_000], [500, 1_000, 2_500]),
    "business_interruption": ("Business Interruption", [250_000, 500_000, 1_000_000], [5_000, 10_000]),
    "professional_indemnity": ("Professional Indemnity", [1_000_000, 2_000_000, 5_000_000], [10_000, 25_000]),
    "cyber": ("Cyber", [500_000, 1_000_000, 2_000_000], [10_000, 25_000]),
    "management_liability": ("Management Liability", [1_000_000, 2_000_000, 5_000_000], [5_000, 10_000]),
    "motor": ("Commercial Motor", [500_000, 1_000_000], [1_000, 2_000]),
}
CLAIM_TYPES = [("Water Damage", "Burst pipe damaged stock and fit-out."),
               ("Theft", "Break-in overnight; equipment stolen."),
               ("Property Damage", "Vehicle reversed into the loading dock door."),
               ("Liability Notification", "Customer slip-and-fall notification, no demand received."),
               ("Storm Damage", "Roof sheeting lifted during storm."),
               ("Motor Collision", "Delivery van rear-ended at intersection.")]
FLAG_TYPES = ["limit_mismatch", "sov_total_mismatch", "currency_mismatch", "abn_formatting_inconsistency",
              "loss_date_outside_policy_period", "policy_number_mismatch"]


@dataclass
class Facts:
    pack_id: str
    insured: str
    abn: str
    industry: str
    occupancy: str
    insurer_full: str
    insurer_alias: str
    broker: str
    policy_number: str
    start: str
    end: str
    premium: int
    coverages: list[dict]
    locations: list[dict]
    claims: list[dict]
    valuation_date: str
    certificate_date: str
    flags: list[dict] = field(default_factory=list)


def _abn(rng: random.Random) -> str:
    d = "".join(str(rng.randint(0, 9)) for _ in range(11))
    return f"{d[:2]} {d[2:5]} {d[5:8]} {d[8:]}"


def make_facts(pack_id: str, rng: random.Random) -> Facts:
    ind, occ = rng.choice(INDUSTRIES)
    insured = f"{rng.choice(INSURED_FIRST)} {ind} Pty Ltd"
    ins_full, ins_alias = rng.choice(INSURERS)
    start = date(2025, 1, 1) + timedelta(days=rng.randint(0, 540))
    end = date(start.year + 1, start.month, start.day) - timedelta(days=1)
    cov_keys = rng.sample(list(COVERAGES), rng.randint(3, 5))
    if "public_liability" not in cov_keys:
        cov_keys[0] = "public_liability"
    covs = [{"type": k, "limit": rng.choice(COVERAGES[k][1]), "deductible": rng.choice(COVERAGES[k][2])}
            for k in cov_keys]
    locs = []
    for i in range(rng.randint(1, 4)):
        sub, st, pc = rng.choice(SUBURBS)
        unit = f"Unit {rng.randint(1, 20)}, " if rng.random() < 0.3 else ""
        addr = f"{unit}{rng.randint(2, 400)} {rng.choice(STREETS)} {rng.choice(STREET_TYPES)}, {sub} {st} {pc}"
        b, c, bi = rng.randint(300, 5000) * 1000, rng.randint(50, 900) * 1000, rng.randint(100, 1500) * 1000
        locs.append({"no": i + 1, "address": addr, "building": b, "contents": c, "bi": bi,
                     "total": b + c + bi, "currency": "AUD"})
    valuation = start - timedelta(days=rng.randint(20, 60))
    claims = []
    years = sorted(rng.sample(range(valuation.year - 4, valuation.year), rng.randint(2, 4)))
    for y in years:
        loss = date(y, rng.randint(1, 12), rng.randint(1, 28))
        loss = min(loss, valuation - timedelta(days=30))
        cat, _ = rng.choice(CLAIM_TYPES)
        inc = rng.randint(2, 90) * 1000 + rng.randint(0, 999)
        claims.append({"claim_no": f"CL-{loss.year}-{rng.randint(10000, 99999)}", "loss_date": loss.isoformat(),
                       "reported_date": (loss + timedelta(days=rng.randint(2, 25))).isoformat(),
                       "category": cat, "status": rng.choice(["Closed", "Closed", "Open"]), "incurred": inc})
    prefix = "".join(w[0] for w in ins_alias.split()[:2]).upper()
    return Facts(
        pack_id=pack_id, insured=insured, abn=_abn(rng), industry=ind, occupancy=occ,
        insurer_full=ins_full, insurer_alias=ins_alias, broker=rng.choice(BROKERS),
        policy_number=f"{prefix}-{start.year}-{rng.randint(100000, 999999)}",
        start=start.isoformat(), end=end.isoformat(), premium=rng.randint(4, 40) * 1000 + rng.randint(0, 999),
        coverages=covs, locations=locs, claims=claims, valuation_date=valuation.isoformat(),
        certificate_date=(start - timedelta(days=rng.randint(1, 5))).isoformat(),
    )


def seed_flags(f: Facts, rng: random.Random, n: int) -> None:
    """Pick ``n`` flag types and record the displayed override for each."""
    choices = [t for t in FLAG_TYPES if not (t == "sov_total_mismatch" and False)]
    for t in rng.sample(choices, n):
        if t == "limit_mismatch":
            c = rng.choice(f.coverages)
            opts = [v for v in COVERAGES[c["type"]][1] if v != c["limit"]]
            f.flags.append({"flag_type": t, "target_doc_type": "certificate_of_currency",
                            "overrides": {"coverage": c["type"], "displayed_limit": rng.choice(opts)}})
        elif t == "sov_total_mismatch":
            f.flags.append({"flag_type": t, "target_doc_type": "statement_of_values",
                            "overrides": {"displayed_total_delta": rng.randint(50, 900) * 1000}})
        elif t == "currency_mismatch":
            f.flags.append({"flag_type": t, "target_doc_type": "statement_of_values",
                            "overrides": {"loc_index": rng.randrange(len(f.locations)),
                                          "currency": rng.choice(["USD", "NZD"])}})
        elif t == "abn_formatting_inconsistency":
            f.flags.append({"flag_type": t, "target_doc_type": "statement_of_values",
                            "overrides": {"displayed_abn": f.abn.replace(" ", "")}})
        elif t == "loss_date_outside_policy_period":
            i = rng.randrange(len(f.claims))
            bad = date.fromisoformat(f.valuation_date) + timedelta(days=rng.randint(400, 900))
            f.flags.append({"flag_type": t, "target_doc_type": "loss_run_report",
                            "overrides": {"claim_index": i, "displayed_loss_date": bad.isoformat()}})
        elif t == "policy_number_mismatch":
            pn = f.policy_number
            digits = list(pn[-6:])
            digits[-1], digits[-2] = digits[-2], digits[-1]
            if digits[-1] == digits[-2]:
                digits[-1] = str((int(digits[-1]) + 1) % 10)
            f.flags.append({"flag_type": t, "target_doc_type": "certificate_of_currency",
                            "overrides": {"displayed_policy_number": pn[:-6] + "".join(digits)}})


def _ov(f: Facts, doc_type: str) -> dict:
    out: dict = {}
    for fl in f.flags:
        if fl["target_doc_type"] == doc_type:
            out.update(fl["overrides"])
    return out


# --------------------------------------------------------------------------------------------
# Template styles. Dev and test use disjoint styles (labels, date/money formats and layout).

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

STYLES = {
    "D1": {"layout": "table", "limit": "Limit", "ded": "Deductible", "date": "dmy_slash", "money": "aud_dollar",
           "font": "sans-serif", "insured": "Insured", "period": "Policy Period"},
    "D2": {"layout": "kv", "limit": "Sum Insured", "ded": "Excess", "date": "long", "money": "dollar_aud",
           "font": "serif", "insured": "Name of Insured", "period": "Period of Insurance"},
    "T1": {"layout": "prose", "limit": "limit of indemnity", "ded": "excess", "date": "iso", "money": "a_dollar",
           "font": "serif", "insured": "Policyholder", "period": "Cover period"},
    "T2": {"layout": "boxed", "limit": "Limit of Liability", "ded": "Each & Every Claim Excess", "date": "dmy_mon",
           "money": "decimal_aud", "font": "monospace", "insured": "Insured Entity", "period": "Term"},
}
SPLIT_STYLES = {"dev": ("D1", "D2"), "test": ("T1", "T2")}


def fmt_date(iso: str, style: str) -> str:
    d = date.fromisoformat(iso)
    return {
        "dmy_slash": f"{d.day:02d}/{d.month:02d}/{d.year}",
        "long": f"{d.day} {MONTHS[d.month - 1]} {d.year}",
        "iso": iso,
        "dmy_mon": f"{d.day:02d}-{MONTHS[d.month - 1][:3]}-{d.year}",
    }[style]


def fmt_money(v: float, style: str, cur: str = "AUD") -> str:
    v = int(v)
    return {
        "aud_dollar": f"{cur} ${v:,}",
        "dollar_aud": f"${v:,} {cur}",
        "a_dollar": f"A${v:,}" if cur == "AUD" else f"{cur} ${v:,}",
        "decimal_aud": f"{v:,}.00 {cur}",
    }[style]


def _css(s: dict) -> str:
    return (f"* {{font-family: {s['font']}; font-size: 9.5px;}} h1 {{font-size: 15px;}} h2 {{font-size: 11px;}}"
            " table {border-collapse: collapse; width: 100%;} td, th {border: 1px solid #555; padding: 2px 4px;}"
            " .box {border: 1px solid #222; padding: 4px; margin: 4px 0;} .small {font-size: 7.5px; color: #555;}")


DISCLAIMER = "<p class='small'>SYNTHETIC TRAINING DOCUMENT - generated for document AI evaluation. All entities fictional.</p>"


def _kv_block(pairs: list[tuple[str, str]], s: dict) -> str:
    if s["layout"] in ("table", "boxed"):
        rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in pairs)
        return f"<table>{rows}</table>" if s["layout"] == "table" else f"<div class='box'><table>{rows}</table></div>"
    if s["layout"] == "kv":
        return "".join(f"<p><b>{k}:</b> {v}</p>" for k, v in pairs)
    return "<p>" + "; ".join(f"{k}: {v}" for k, v in pairs) + ".</p>"


def render_schedule(f: Facts, s: dict) -> str:
    d, m = s["date"], s["money"]
    head = (f"<h1>{f.insurer_full}</h1><h2>Policy Schedule</h2>{DISCLAIMER}"
            + _kv_block([(s["insured"], f.insured), ("ABN", f.abn), ("Policy Number", f.policy_number),
                         (s["period"], f"{fmt_date(f.start, d)} to {fmt_date(f.end, d)}"),
                         ("Broker", f.broker), ("Insurer", f.insurer_full)], s))
    if s["layout"] == "prose":
        cov = "".join(f"<p>The {COVERAGES[c['type']][0]} section is written to a {s['limit']} of "
                      f"{fmt_money(c['limit'], m)} with an {s['ded']} of {fmt_money(c['deductible'], m)}.</p>"
                      for c in f.coverages)
    else:
        rows = "".join(f"<tr><td>{COVERAGES[c['type']][0]}</td><td>{fmt_money(c['limit'], m)}</td>"
                       f"<td>{fmt_money(c['deductible'], m)}</td></tr>" for c in f.coverages)
        cov = f"<h2>Sections of Cover</h2><table><tr><th>Section</th><th>{s['limit']}</th><th>{s['ded']}</th></tr>{rows}</table>"
    locs = "".join(f"<p>Situation {loc['no']}: {loc['address']}</p>" for loc in f.locations)
    return (head + cov + f"<p><b>Total Annual Premium:</b> {fmt_money(f.premium, m)}</p>"
            + f"<h2>Insured Situations</h2>{locs}"
            + "<p>Endorsement: Flood Sub-limit " + fmt_money(250_000, m) + " any one event.</p>")


def render_sov(f: Facts, s: dict) -> str:
    d, m = s["date"], s["money"]
    ov = _ov(f, "statement_of_values")
    abn = ov.get("displayed_abn", f.abn)
    head = (f"<h1>Statement of Values</h1><p>Prepared by {f.broker}</p>{DISCLAIMER}"
            + _kv_block([(s["insured"], f.insured), ("ABN", abn), ("Policy Number", f.policy_number),
                         (s["period"], f"{fmt_date(f.start, d)} to {fmt_date(f.end, d)}"),
                         ("Values declared as at", fmt_date(f.valuation_date, d))], s))
    rows = ""
    for i, loc in enumerate(f.locations):
        cur = ov["currency"] if ov.get("loc_index") == i else "AUD"
        rows += (f"<tr><td>{loc['no']}</td><td>{loc['address']}</td><td>{fmt_money(loc['building'], m)}</td>"
                 f"<td>{fmt_money(loc['contents'], m)}</td><td>{fmt_money(loc['bi'], m)}</td>"
                 f"<td>{fmt_money(loc['total'], m, cur)}</td></tr>")
    total = sum(loc["total"] for loc in f.locations) + ov.get("displayed_total_delta", 0)
    return (head + "<table><tr><th>Loc</th><th>Address</th><th>Building</th><th>Contents</th>"
            f"<th>Business Interruption</th><th>Total Value</th></tr>{rows}"
            f"<tr><td></td><td><b>GRAND TOTAL</b></td><td></td><td></td><td></td><td><b>{fmt_money(total, m)}</b></td></tr>"
            "</table>")


def render_loss_run(f: Facts, s: dict) -> str:
    d, m = s["date"], s["money"]
    ov = _ov(f, "loss_run_report")
    head = (f"<h1>Loss Run Report</h1><p>{f.insurer_alias} - Claims Department</p>{DISCLAIMER}"
            + _kv_block([(s["insured"], f.insured), ("ABN", f.abn), ("Policy Number", f.policy_number),
                         ("Valuation Date", fmt_date(f.valuation_date, d))], s))
    rows = ""
    for i, c in enumerate(f.claims):
        loss = ov["displayed_loss_date"] if ov.get("claim_index") == i else c["loss_date"]
        if s["layout"] == "prose":
            rows += (f"<p>Claim {c['claim_no']}: loss on {fmt_date(loss, d)}, reported {fmt_date(c['reported_date'], d)}, "
                     f"{c['category']}, status {c['status']}, total incurred {fmt_money(c['incurred'], m)}.</p>")
        else:
            rows += (f"<tr><td>{c['claim_no']}</td><td>{fmt_date(loss, d)}</td><td>{fmt_date(c['reported_date'], d)}</td>"
                     f"<td>{c['category']}</td><td>{c['status']}</td><td>{fmt_money(c['incurred'], m)}</td></tr>")
    if s["layout"] != "prose":
        rows = ("<table><tr><th>Claim No</th><th>Date of Loss</th><th>Date Reported</th><th>Cause</th>"
                f"<th>Status</th><th>Incurred</th></tr>{rows}</table>")
    total = sum(c["incurred"] for c in f.claims)
    return head + rows + f"<p><b>Total incurred:</b> {fmt_money(total, m)}</p>"


def render_coc(f: Facts, s: dict) -> str:
    d, m = s["date"], s["money"]
    ov = _ov(f, "certificate_of_currency")
    pn = ov.get("displayed_policy_number", f.policy_number)
    limits = "".join(
        f"<p>{COVERAGES[c['type']][0]}: {fmt_money(ov['displayed_limit'] if ov.get('coverage') == c['type'] else c['limit'], m)}</p>"
        for c in f.coverages
    )
    return (f"<h1>Certificate of Currency</h1><p>Issued by {f.insurer_alias}</p>{DISCLAIMER}"
            + _kv_block([("Certificate Date", fmt_date(f.certificate_date, d)), (s["insured"], f.insured),
                         ("ABN", f.abn), ("Insured Address", f.locations[0]["address"]), ("Policy Number", pn),
                         (s["period"], f"{fmt_date(f.start, d)} to {fmt_date(f.end, d)}")], s)
            + f"<h2>Limits</h2>{limits}<p>This certificate is evidence of cover as at the certificate date only.</p>")


DOC_TYPES = [("01", "policy_schedule", render_schedule), ("02", "statement_of_values", render_sov),
             ("03", "loss_run_report", render_loss_run), ("04", "certificate_of_currency", render_coc)]


# --------------------------------------------------------------------------------------------
# Gold, built from the same values the templates print.

def gold_for(f: Facts, doc_type: str) -> dict:
    ov = _ov(f, doc_type)
    g: dict = {k: [] for k in ("parties", "policies", "coverages", "locations", "claims", "dates", "relationships")}
    pn = ov.get("displayed_policy_number", f.policy_number)

    def rel(pred, obj):
        g["relationships"].append({"subject": pn, "predicate": pred, "object": str(obj), "page": 1})

    if doc_type == "policy_schedule":
        g["parties"] = [{"role": "insurer", "name": f.insurer_full}, {"role": "insured", "name": f.insured, "abn": f.abn},
                        {"role": "broker", "name": f.broker}]
        g["policies"] = [{"policy_number": pn, "premium": f.premium}]
        g["coverages"] = [{"coverage_type": c["type"], "limit": c["limit"], "deductible": c["deductible"]}
                          for c in f.coverages]
        g["locations"] = [{"location_no": loc["no"], "address": loc["address"]} for loc in f.locations]
        g["dates"] = [{"kind": "policy_start", "date": f.start}, {"kind": "policy_end", "date": f.end}]
        rel("HAS_INSURED", f.insured)
        rel("ISSUED_BY", f.insurer_full)
        rel("PLACED_BY", f.broker)
        for c in f.coverages:
            rel("HAS_COVERAGE", c["type"])
        for loc in f.locations:
            rel("COVERS_LOCATION", loc["no"])
    elif doc_type == "statement_of_values":
        g["parties"] = [{"role": "broker", "name": f.broker},
                        {"role": "insured", "name": f.insured, "abn": ov.get("displayed_abn", f.abn)}]
        g["policies"] = [{"policy_number": pn}]
        g["locations"] = [{"location_no": loc["no"], "address": loc["address"], "total_declared_value": loc["total"],
                           "currency": ov["currency"] if ov.get("loc_index") == i else "AUD"}
                          for i, loc in enumerate(f.locations)]
        g["dates"] = [{"kind": "policy_start", "date": f.start}, {"kind": "policy_end", "date": f.end},
                      {"kind": "valuation_date", "date": f.valuation_date}]
        g["declared_total"] = sum(loc["total"] for loc in f.locations) + ov.get("displayed_total_delta", 0)
        rel("HAS_INSURED", f.insured)
        rel("PLACED_BY", f.broker)
        for loc in f.locations:
            rel("COVERS_LOCATION", loc["no"])
    elif doc_type == "loss_run_report":
        g["parties"] = [{"role": "insurer", "name": f.insurer_alias}, {"role": "insured", "name": f.insured, "abn": f.abn}]
        g["policies"] = [{"policy_number": pn}]
        g["claims"] = [{**{k: c[k] for k in ("claim_no", "reported_date", "category", "status", "incurred")},
                        "loss_date": ov["displayed_loss_date"] if ov.get("claim_index") == i else c["loss_date"]}
                       for i, c in enumerate(f.claims)]
        g["dates"] = [{"kind": "valuation_date", "date": f.valuation_date}]
        rel("HAS_INSURED", f.insured)
        rel("ISSUED_BY", f.insurer_alias)
        for c in f.claims:
            rel("HAS_CLAIM", c["claim_no"])
    elif doc_type == "certificate_of_currency":
        g["parties"] = [{"role": "insurer", "name": f.insurer_alias}, {"role": "insured", "name": f.insured, "abn": f.abn}]
        g["policies"] = [{"policy_number": pn}]
        g["coverages"] = [{"coverage_type": c["type"],
                           "limit": ov["displayed_limit"] if ov.get("coverage") == c["type"] else c["limit"]}
                          for c in f.coverages]
        g["locations"] = [{"address": f.locations[0]["address"]}]
        g["dates"] = [{"kind": "certificate_date", "date": f.certificate_date}, {"kind": "policy_start", "date": f.start},
                      {"kind": "policy_end", "date": f.end}]
        rel("HAS_INSURED", f.insured)
        rel("ISSUED_BY", f.insurer_alias)
        for c in f.coverages:
            rel("HAS_COVERAGE", c["type"])
    for key in ("parties", "policies", "coverages", "locations", "claims", "dates"):
        for it in g[key]:
            it["page"] = 1
            it["provenance"] = "synthetic"
    return g


# --------------------------------------------------------------------------------------------

SPLITS = {"dev": {"prefix": "SYNDEV", "seed": 1101, "n_packs": 3}, "test": {"prefix": "SYNTEST", "seed": 2202, "n_packs": 3}}


def render_pdf(html: str, css: str, path) -> int:
    doc = pymupdf.open()
    remaining = html
    pages = 0
    while remaining is not None and pages < 3:
        page = doc.new_page(width=595, height=842)
        spare, _ = page.insert_htmlbox(pymupdf.Rect(36, 36, 559, 806), remaining, css=css)
        pages += 1
        if spare >= 0:
            remaining = None
    doc.save(path)
    return pages


def generate() -> dict:
    pdf_dir = SYNTH_DIR / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for old in pdf_dir.glob("*.pdf"):
        old.unlink()
    gold_rows, fact_rows, flags = [], [], {}
    for split, cfg in SPLITS.items():
        rng = random.Random(cfg["seed"])
        styles = SPLIT_STYLES[split]
        for k in range(1, cfg["n_packs"] + 1):
            pack = f"{cfg['prefix']}{k:03d}"
            facts = make_facts(pack, rng)
            seed_flags(facts, rng, n=[1, 2, 2][(k - 1) % 3])
            flags[pack] = facts.flags
            fact_rows.append(asdict(facts))
            for num, dtype, render in DOC_TYPES:
                style = STYLES[rng.choice(styles)]
                doc_id = f"{pack}_{num}_{dtype}"
                render_pdf(render(facts, style), _css(style), pdf_dir / f"{doc_id}.pdf")
                g = gold_for(facts, dtype)
                DocumentExtraction.model_validate(g)
                gold_rows.append({"doc_id": doc_id, "style": [n for n, v in STYLES.items() if v is style][0], **g})
    with open(SYNTH_DIR / "gold.jsonl", "w") as fh:
        for row in gold_rows:
            fh.write(json.dumps(row) + "\n")
    with open(SYNTH_DIR / "facts.jsonl", "w") as fh:
        for row in fact_rows:
            fh.write(json.dumps(row) + "\n")
    (SYNTH_DIR / "red_flags.json").write_text(json.dumps(flags, indent=2))
    return {"docs": len(gold_rows), "packs": len(fact_rows), "flags": sum(len(v) for v in flags.values())}


if __name__ == "__main__":
    print(generate())
