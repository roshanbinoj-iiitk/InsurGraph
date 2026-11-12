"""Knowledge graph over extractions, graph queries and the cross-document inconsistency detector.

Graph (NetworkX ``MultiDiGraph``):
* ``doc:<doc_id>`` document nodes (type, pack).
* Entity nodes: ``policy:<no>``, ``party:<canonical name>``, ``coverage:<policy>|<type>``,
  ``location:<pack>|<no or address>``, ``claim:<no>``.
* ``MENTIONED_IN`` edges entity -> document carry the attribute values *as observed in that
  document* plus the page, so every fact has page-level provenance and attribute conflicts
  across documents are visible.
* Relationship edges (``HAS_INSURED``, ``HAS_COVERAGE``, ...) policy -> entity, keyed by
  predicate, with ``source_doc`` and ``page``.

Party names are merged with ``src.resolve.Resolver`` before nodes are created.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import networkx as nx
from rapidfuzz import fuzz

from src.config import pack_of
from src.normalize import abn_format, norm_abn, norm_address, norm_coverage, norm_date, norm_id, norm_name
from src.resolve import Resolver
from src.schema import DocumentExtraction

ADDRESS_MATCH = 90  # fuzzy threshold for attaching an unnumbered address to a numbered location


def _primary_policy(exts: list[DocumentExtraction]) -> str | None:
    c = Counter(norm_id(p.policy_number) for e in exts for p in e.policies if p.policy_number)
    return c.most_common(1)[0][0] if c else None


def build_graph(extractions: dict[str, DocumentExtraction], resolver: Resolver | None = None) -> nx.MultiDiGraph:
    resolver = resolver or Resolver()
    G = nx.MultiDiGraph()
    by_pack: dict[str, list[DocumentExtraction]] = defaultdict(list)
    for doc_id, e in extractions.items():
        by_pack[pack_of(doc_id)].append(e)

    for pack, exts in sorted(by_pack.items()):
        G.add_node(f"pack:{pack}", type="pack", label=pack)
        names = [p.name for e in exts for p in e.parties] + [
            r.object for e in exts for r in e.relationships if r.predicate in ("HAS_INSURED", "ISSUED_BY", "PLACED_BY")
        ]
        canon = resolver.cluster(names, "organisation")
        primary = _primary_policy(exts)
        numbered: dict[int, str] = {}  # location_no -> node id
        for e in exts:
            for loc in e.locations:
                if loc.location_no is not None:
                    numbered.setdefault(loc.location_no, f"location:{pack}|{loc.location_no}")

        for e in sorted(exts, key=lambda x: x.doc_id or ""):
            doc = e.doc_id
            dnode = f"doc:{doc}"
            G.add_node(dnode, type="document", label=doc, pack=pack, doc_type=doc.split("_", 2)[-1])
            G.add_edge(dnode, f"pack:{pack}", key="PART_OF", predicate="PART_OF")
            doc_policy = norm_id(e.policies[0].policy_number) if e.policies else primary
            dates = {d.kind: norm_date(d.date) or d.date for d in e.dates}

            def mention(node, page, **attrs):
                G.add_edge(node, dnode, predicate="MENTIONED_IN", source_doc=doc, page=page,
                           attrs={k: v for k, v in attrs.items() if v is not None})

            for p in e.policies:
                n = f"policy:{norm_id(p.policy_number)}"
                G.add_node(n, type="policy", label=p.policy_number, pack=pack)
                mention(n, p.page, premium=p.premium, policy_start=dates.get("policy_start"),
                        policy_end=dates.get("policy_end"))
            for p in e.parties:
                cname = canon.get(p.name, p.name)
                n = f"party:{norm_name(cname)}"
                if n not in G:
                    G.add_node(n, type="party", label=cname, names=set(), roles=set(), pack=pack)
                G.nodes[n]["names"].add(p.name)
                G.nodes[n]["roles"].add(p.role)
                mention(n, p.page, role=p.role, name=p.name, abn=norm_abn(p.abn), abn_raw=p.abn,
                        abn_format=abn_format(p.abn))
            for c in e.coverages:
                ctype = norm_coverage(c.coverage_type)
                n = f"coverage:{doc_policy or pack}|{ctype}"
                G.add_node(n, type="coverage", label=ctype, policy=doc_policy, pack=pack)
                mention(n, c.page, limit=c.limit, deductible=c.deductible)
            for loc in e.locations:
                n = _location_node(pack, loc, numbered, G)
                G.add_node(n, type="location", label=loc.address, pack=pack)
                mention(n, loc.page, address=norm_address(loc.address), address_raw=loc.address,
                        total_declared_value=loc.total_declared_value, currency=loc.currency)
            for cl in e.claims:
                n = f"claim:{norm_id(cl.claim_no)}"
                G.add_node(n, type="claim", label=cl.claim_no, pack=pack)
                mention(n, cl.page, loss_date=norm_date(cl.loss_date) or cl.loss_date,
                        reported_date=norm_date(cl.reported_date) or cl.reported_date, incurred=cl.incurred,
                        status=cl.status, category=cl.category, valuation_date=dates.get("valuation_date"))
            if e.declared_total is not None:
                G.nodes[dnode]["declared_total"] = e.declared_total
                G.nodes[dnode]["row_totals"] = [loc.total_declared_value for loc in e.locations
                                                if loc.location_no is not None]
            for r in e.relationships:
                subj = f"policy:{norm_id(r.subject)}"
                if subj not in G:
                    G.add_node(subj, type="policy", label=r.subject, pack=pack)
                obj = _relationship_object(r.predicate, r.object, pack, canon, norm_id(r.subject), numbered)
                if obj is None:
                    continue
                if obj not in G:
                    G.add_node(obj, type=obj.split(":", 1)[0], label=r.object, pack=pack)
                G.add_edge(subj, obj, key=f"{r.predicate}|{doc}", predicate=r.predicate, source_doc=doc, page=r.page)
    G.graph["resolution_log"] = resolver.log
    return G


def _location_node(pack, loc, numbered, G) -> str:
    if loc.location_no is not None:
        return numbered[loc.location_no]
    addr = norm_address(loc.address) or ""
    for node in numbered.values():  # attach e.g. the insured's trading address to location #1
        for _, _, data in G.out_edges(node, data=True):
            other = data.get("attrs", {}).get("address")
            if other and fuzz.ratio(addr, other) >= ADDRESS_MATCH:
                return node
    return f"location:{pack}|{addr}"


def _relationship_object(predicate, obj, pack, canon, policy, numbered) -> str | None:
    if obj is None:
        return None
    if predicate in ("HAS_INSURED", "ISSUED_BY", "PLACED_BY"):
        return f"party:{norm_name(canon.get(obj, obj))}"
    if predicate == "HAS_COVERAGE":
        return f"coverage:{policy}|{norm_coverage(obj)}"
    if predicate == "HAS_CLAIM":
        return f"claim:{norm_id(obj)}"
    if predicate == "COVERS_LOCATION":
        digits = "".join(ch for ch in str(obj) if ch.isdigit())
        if digits and int(digits) in numbered:
            return numbered[int(digits)]
        return f"location:{pack}|{norm_address(str(obj))}"
    return None


# ------------------------------------------------------------------------------------------
# Queries


def observations(G: nx.MultiDiGraph, node: str) -> list[dict]:
    """Attribute observations of an entity, one per document mention."""
    return [{"doc": d.split(":", 1)[1], "page": data.get("page"), **data.get("attrs", {})}
            for _, d, data in G.out_edges(node, data=True) if data.get("predicate") == "MENTIONED_IN"]


def _policy_node(G, policy_number: str) -> str:
    return f"policy:{norm_id(policy_number)}"


def coverages_for_policy(G: nx.MultiDiGraph, policy_number: str) -> dict[str, list[dict]]:
    """Q1: all coverages of a policy, with limit/deductible as stated in each document."""
    pol = norm_id(policy_number)
    out = {}
    for n, data in G.nodes(data=True):
        if data.get("type") == "coverage" and data.get("policy") == pol:
            out[data["label"]] = observations(G, n)
    return out


def documents_mentioning(G: nx.MultiDiGraph, name: str, resolver: Resolver | None = None) -> list[str]:
    """Q2: all documents mentioning a party (resolved through entity resolution)."""
    resolver = resolver or Resolver()
    docs = set()
    for n, data in G.nodes(data=True):
        if data.get("type") == "party" and any(resolver.same(name, v).same for v in data["names"] | {data["label"]}):
            docs |= {o["doc"] for o in observations(G, n)}
    return sorted(docs)


def coverage_limit_across_documents(G: nx.MultiDiGraph, policy_number: str, coverage: str) -> dict[str, float | None]:
    """Q3: the limit for one coverage of a policy in every document that states it."""
    n = f"coverage:{norm_id(policy_number)}|{norm_coverage(coverage)}"
    return {o["doc"]: o.get("limit") for o in observations(G, n)} if n in G else {}


def parties_for_policy(G: nx.MultiDiGraph, policy_number: str) -> dict[str, list[str]]:
    """Q4: parties linked to a policy, by relationship, with the documents asserting the link."""
    out: dict[str, set] = defaultdict(set)
    pol = _policy_node(G, policy_number)
    if pol not in G:
        return {}
    for _, obj, data in G.out_edges(pol, data=True):
        if data["predicate"] in ("HAS_INSURED", "ISSUED_BY", "PLACED_BY"):
            out[f"{data['predicate']}: {G.nodes[obj]['label']}"].add(data["source_doc"])
    return {k: sorted(v) for k, v in out.items()}


def claims_for_policy(G: nx.MultiDiGraph, policy_number: str) -> dict[str, list[dict]]:
    """Q5: claims linked to a policy and how each document reports them."""
    pol = _policy_node(G, policy_number)
    if pol not in G:
        return {}
    claims = {obj for _, obj, d in G.out_edges(pol, data=True) if d["predicate"] == "HAS_CLAIM"}
    return {G.nodes[c]["label"]: observations(G, c) for c in sorted(claims)}


# ------------------------------------------------------------------------------------------
# Inconsistency detector

# (node type, attribute) -> flag type when the attribute takes different values across documents
CONFLICT_ATTRS = {
    ("party", "abn"): "abn_mismatch",
    ("policy", "premium"): "premium_mismatch",
    ("policy", "policy_start"): "policy_period_mismatch",
    ("policy", "policy_end"): "policy_period_mismatch",
    ("coverage", "limit"): "limit_mismatch",
    ("coverage", "deductible"): "deductible_mismatch",
    ("location", "total_declared_value"): "location_value_mismatch",
    ("claim", "loss_date"): "claim_attribute_mismatch",
    ("claim", "reported_date"): "claim_attribute_mismatch",
    ("claim", "incurred"): "claim_attribute_mismatch",
}


def detect_inconsistencies(G: nx.MultiDiGraph) -> list[dict]:
    flags: list[dict] = []

    def flag(pack, ftype, node, attribute, obs, detail):
        flags.append({"pack": pack, "flag_type": ftype, "node": node, "attribute": attribute,
                      "observations": obs, "detail": detail})

    for n, data in G.nodes(data=True):
        t = data.get("type")
        if t in (None, "document", "pack"):
            continue
        obs = observations(G, n)
        pack = data.get("pack")
        # 1. Same attribute, different values across documents.
        for (nt, attr), ftype in CONFLICT_ATTRS.items():
            if nt != t:
                continue
            vals = {o["doc"]: o[attr] for o in obs if o.get(attr) is not None}
            if len(set(vals.values())) > 1:
                flag(pack, ftype, n, attr, vals, f"{data['label']}: {attr} differs across documents")
        # 2. Same ABN digits printed in different formats.
        if t == "party":
            digits = {o.get("abn") for o in obs if o.get("abn")}
            fmts = {o["doc"]: o["abn_raw"] for o in obs if o.get("abn_raw")}
            if len(digits) == 1 and len({abn_format(v) for v in fmts.values()}) > 1:
                flag(pack, "abn_formatting_inconsistency", n, "abn", fmts,
                     f"ABN {next(iter(digits))} printed in {len(set(map(abn_format, fmts.values())))} formats")
        # 3. Claim loss date after the date it was reported or after the valuation date.
        if t == "claim":
            for o in obs:
                loss, rep, val = o.get("loss_date"), o.get("reported_date"), o.get("valuation_date")
                if loss and ((rep and loss > rep) or (val and loss > val)):
                    flag(pack, "loss_date_outside_policy_period", n, "loss_date",
                         {o["doc"]: loss}, f"{data['label']}: loss {loss} after reported {rep} / valuation {val}")

    # 4. Pack-level rules.
    packs = {d.get("pack") for _, d in G.nodes(data=True) if d.get("type") == "document"}
    for pack in sorted(p for p in packs if p):
        locs = [(n, o) for n, d in G.nodes(data=True) if d.get("type") == "location" and d.get("pack") == pack
                for o in observations(G, n) if o.get("currency")]
        cur = Counter(o["currency"] for _, o in locs)
        if cur:
            main = "AUD" if "AUD" in cur else cur.most_common(1)[0][0]
            for n, o in locs:
                if o["currency"] != main:
                    flag(pack, "currency_mismatch", n, "currency", {o["doc"]: o["currency"]},
                         f"{G.nodes[n]['label']}: value declared in {o['currency']}, pack currency {main}")
        policies = sorted(n for n, d in G.nodes(data=True) if d.get("type") == "policy" and d.get("pack") == pack)
        if len(policies) > 1:
            obs = {}
            for p in policies:
                docs = {o["doc"] for o in observations(G, p)} | {
                    d["source_doc"] for _, _, d in G.out_edges(p, data=True) if d.get("source_doc")}
                for doc in docs:
                    obs[doc] = G.nodes[p]["label"]
            flag(pack, "policy_number_mismatch", f"pack:{pack}", "policy_number", obs,
                 f"{len(policies)} different policy numbers in one submission")
        for n, d in G.nodes(data=True):
            if d.get("type") == "document" and d.get("pack") == pack and d.get("declared_total") is not None:
                rows = [v for v in d.get("row_totals", []) if v is not None]
                if rows and abs(sum(rows) - d["declared_total"]) > 1:
                    flag(pack, "sov_total_mismatch", n, "declared_total", {d["label"]: d["declared_total"]},
                         f"displayed total {d['declared_total']:,.0f} != sum of rows {sum(rows):,.0f}")
    return flags


def to_json_safe(G: nx.MultiDiGraph) -> dict:
    """Node-link dict with sets converted to sorted lists (for saving)."""
    H = G.copy()
    for _, d in H.nodes(data=True):
        for k, v in list(d.items()):
            if isinstance(v, set):
                d[k] = sorted(v)
    H.graph = {}
    return nx.node_link_data(H, edges="edges")
