"""Retrieval-augmented QA over the document chunks.

* Chunks (``src.ingest.chunk_document``) are embedded with a local sentence-transformers model
  and stored in a persistent Chroma collection with document, page, type and pack metadata.
* ``plain`` RAG: top-k chunks by similarity, answered by Gemini Flash Lite.
* ``graph`` RAG (stretch): first find the submission the question is about through the
  knowledge graph (policy numbers, claim numbers, resolved party names), then retrieve only
  from that pack's documents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import networkx as nx

from src import llm
from src.config import EMBEDDING_MODEL, INTERIM_DIR
from src.ingest import chunk_document, load_corpus
from src.normalize import norm_id, norm_name, norm_text

COLLECTION = "insurgraph_chunks"
ANSWER_SYSTEM = (
    "You answer questions about commercial insurance submission documents using ONLY the context "
    "excerpts provided. Each excerpt starts with [document id | type] (page). Give the shortest complete "
    "answer: a number for amounts (digits only, e.g. 1250000), an ISO date (YYYY-MM-DD) for dates, a name "
    "for names, or one sentence for explanations. If the context does not contain the answer, reply "
    "exactly: not found"
)

_model = None
_collection = None


def _embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    return _model


def get_collection(source: str = "real", rebuild: bool = False):
    """Persistent Chroma collection of chunk embeddings (built on first use)."""
    global _collection
    import chromadb

    client = chromadb.PersistentClient(path=str(INTERIM_DIR / "chroma"))
    name = f"{COLLECTION}_{source}"
    if rebuild:
        try:
            client.delete_collection(name)
        except Exception:  # noqa: BLE001 - collection may not exist
            pass
    col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    chunks = [c for d in load_corpus(source) for c in chunk_document(d)]
    if col.count() != len(chunks):
        if col.count():
            client.delete_collection(name)
            col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
        emb = _embedder().encode([c.text for c in chunks], normalize_embeddings=True).tolist()
        col.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=emb,
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "page": c.page,
                    "pack": c.doc_id.split("_", 1)[0],
                    "doc_type": c.doc_id.split("_", 2)[-1],
                }
                for c in chunks
            ],
        )
    _collection = col
    return col


@dataclass
class Retrieved:
    chunk_id: str
    doc_id: str
    page: int
    text: str
    distance: float


def retrieve(question: str, k: int = 5, pack: str | None = None, source: str = "real") -> list[Retrieved]:
    col = _collection or get_collection(source)
    q = _embedder().encode([question], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=q, n_results=k, where={"pack": pack} if pack else None)
    return [
        Retrieved(cid, meta["doc_id"], meta["page"], doc, dist)
        for cid, meta, doc, dist in zip(
            res["ids"][0], res["metadatas"][0], res["documents"][0], res["distances"][0], strict=True
        )
    ]


def route_to_pack(question: str, G: nx.MultiDiGraph) -> str | None:
    """Find the submission pack a question refers to via graph node labels."""
    q_ids = {norm_id(t) for t in re.findall(r"[A-Z]{2,}-\d{4}-\d+", question)}
    q_text = f" {norm_text(question) or ''} "
    votes: dict[str, int] = {}
    for _, d in G.nodes(data=True):
        pack = d.get("pack")
        if not pack or d.get("type") not in ("policy", "claim", "party"):
            continue
        label = str(d.get("label", ""))
        if d["type"] in ("policy", "claim") and norm_id(label) in q_ids:
            votes[pack] = votes.get(pack, 0) + 3
        if d["type"] == "party":
            for name in set(d.get("names", set())) | {label}:
                nn = norm_name(name)
                if nn and len(nn) > 3 and f" {nn} " in q_text:
                    votes[pack] = votes.get(pack, 0) + 2
    return max(votes, key=votes.get) if votes else None


def answer(
    question: str,
    model: str = "gemini-flash-lite",
    k: int = 5,
    variant: str = "plain",
    G: nx.MultiDiGraph | None = None,
) -> dict:
    pack = route_to_pack(question, G) if variant == "graph" and G is not None else None
    hits = retrieve(question, k=k, pack=pack)
    context = "\n\n---\n\n".join(h.text for h in hits)
    res = llm.complete(
        model, ANSWER_SYSTEM, f"Context:\n{context}\n\nQuestion: {question}\nAnswer:", temperature=0.0, max_tokens=300
    )
    return {
        "question": question,
        "answer": res.text.strip(),
        "variant": variant,
        "routed_pack": pack,
        "retrieved": [
            {"chunk_id": h.chunk_id, "doc_id": h.doc_id, "page": h.page, "distance": round(h.distance, 4)} for h in hits
        ],
    }
