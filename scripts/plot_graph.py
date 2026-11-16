"""Demo figure: one submission's knowledge graph with detector flags highlighted.

Usage: python scripts/plot_graph.py [--pack PACK000002] [--source best|gold]
Writes docs/graph_<pack>.png.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import ROOT, RUNS_DIR  # noqa: E402
from src.extract import load_predictions  # noqa: E402
from src.gold import load_gold  # noqa: E402
from src.graph import build_graph, detect_inconsistencies  # noqa: E402
from src.resolve import Resolver  # noqa: E402

COLORS = {
    "policy": "#2b6cb0",
    "party": "#2f855a",
    "coverage": "#b7791f",
    "location": "#805ad5",
    "claim": "#319795",
    "document": "#a0aec0",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="PACK000002")
    ap.add_argument("--source", default="best", choices=["best", "gold"])
    args = ap.parse_args()
    if args.source == "best":
        best = json.loads((RUNS_DIR / "extraction" / "best_config.json").read_text())["best"]
        exts = {
            **load_predictions(RUNS_DIR / "extraction" / "dev" / best),
            **load_predictions(RUNS_DIR / "extraction" / "test" / best),
        }
    else:
        exts = load_gold("real")
    exts = {k: v for k, v in exts.items() if k.startswith(args.pack)}
    G = build_graph(exts, Resolver(llm_model=None))
    flagged = {f["node"] for f in detect_inconsistencies(G)}

    H = nx.DiGraph()
    for u, v, d in G.edges(data=True):
        if d["predicate"] == "PART_OF":
            continue
        if d["predicate"] == "MENTIONED_IN":
            if G.nodes[u]["type"] in ("coverage", "party"):
                H.add_edge(u, v, kind="mention")
        else:
            H.add_edge(u, v, kind=d["predicate"])
    for n in H.nodes:
        H.nodes[n].update(G.nodes[n])

    pos = nx.spring_layout(H, seed=7, k=1.1)
    fig, ax = plt.subplots(figsize=(15, 10))
    mention = [(u, v) for u, v, d in H.edges(data=True) if d["kind"] == "mention"]
    rels = [(u, v) for u, v, d in H.edges(data=True) if d["kind"] != "mention"]
    nx.draw_networkx_edges(H, pos, edgelist=mention, style="dotted", edge_color="#cbd5e0", ax=ax, arrows=False)
    nx.draw_networkx_edges(H, pos, edgelist=rels, edge_color="#4a5568", ax=ax, arrowsize=10)
    for t, c in COLORS.items():
        nodes = [n for n in H if H.nodes[n].get("type") == t]
        nx.draw_networkx_nodes(
            H,
            pos,
            nodelist=nodes,
            node_color=c,
            node_size=420 if t != "document" else 260,
            edgecolors=["#e53e3e" if n in flagged else "white" for n in nodes],
            linewidths=[3.5 if n in flagged else 1 for n in nodes],
            ax=ax,
        )
    labels = {}
    for n in H:
        lab = str(H.nodes[n].get("label", n))
        if H.nodes[n].get("type") == "document":
            lab = lab.split("_", 2)[-1].replace("_", " ")
        labels[n] = lab if len(lab) < 34 else lab[:31] + "..."
    nx.draw_networkx_labels(H, pos, labels, font_size=7, ax=ax)
    edge_labels = {
        (u, v): d["kind"] for u, v, d in H.edges(data=True) if d["kind"] in ("HAS_INSURED", "ISSUED_BY", "PLACED_BY")
    }
    nx.draw_networkx_edge_labels(H, pos, edge_labels, font_size=6, ax=ax)
    from matplotlib.lines import Line2D

    handles = [Line2D([], [], marker="o", ls="", color=c, markersize=9, label=t) for t, c in COLORS.items()]
    handles.append(
        Line2D(
            [],
            [],
            marker="o",
            ls="",
            markerfacecolor="white",
            markeredgecolor="#e53e3e",
            markeredgewidth=2.5,
            markersize=9,
            label="flagged",
        )
    )
    ax.legend(handles=handles, loc="lower left", fontsize=8)
    ax.set_title(
        f"{args.pack} knowledge graph ({args.source} extractions). Red outline = inconsistency flag; "
        "dotted = mentioned in document",
        fontsize=10,
    )
    ax.axis("off")
    out = ROOT / "docs" / f"graph_{args.pack}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"wrote {out} ({H.number_of_nodes()} nodes, flagged: {sorted(flagged)})")


if __name__ == "__main__":
    main()
