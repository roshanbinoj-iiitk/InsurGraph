"""PDF ingestion and chunking.

Phase 0 compared ``pymupdf4llm`` against plain PyMuPDF text on the statement of values
and loss run (see docs/phase0_data_note.md). pymupdf4llm's table detection split addresses
and money values across columns on the SOV grid, so plain PyMuPDF text is the default.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from src.config import RAW_PDF_DIR, SYNTH_DIR, pack_of

_DOC_TYPE_RE = re.compile(r"^[A-Z]+\d+_\d+_(?P<type>[a-z_]+)$")


@dataclass
class Page:
    number: int  # 1-based
    text: str


@dataclass
class Document:
    doc_id: str
    path: Path
    pages: list[Page] = field(default_factory=list)

    @property
    def pack_id(self) -> str:
        return pack_of(self.doc_id)

    @property
    def doc_type(self) -> str:
        m = _DOC_TYPE_RE.match(self.doc_id)
        return m.group("type") if m else "unknown"

    def render(self) -> str:
        """Full text with page markers, as sent to the extractor."""
        return "\n\n".join(f"=== Page {p.number} ===\n{p.text.strip()}" for p in self.pages)

    @property
    def n_tokens(self) -> int:
        return estimate_tokens(self.render())


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 characters per token) used for budgeting and throttling."""
    return max(1, len(text) // 4)


def load_pdf(path: str | Path, method: str = "pymupdf") -> Document:
    path = Path(path)
    doc_id = path.stem
    if method == "pymupdf":
        with pymupdf.open(path) as pdf:
            pages = [Page(i + 1, _clean(pg.get_text())) for i, pg in enumerate(pdf)]
    elif method == "pymupdf4llm":
        import pymupdf4llm

        chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True)
        pages = [Page(i + 1, c["text"]) for i, c in enumerate(chunks)]
    else:
        raise ValueError(method)
    return Document(doc_id=doc_id, path=path, pages=pages)


def _clean(text: str) -> str:
    """NFKC folds typographic ligatures (U+FB01 'fi') that PyMuPDF emits for some fonts."""
    return unicodedata.normalize("NFKC", text)


def has_text_layer(path: str | Path, min_chars: int = 50) -> bool:
    with pymupdf.open(path) as pdf:
        return all(len(pg.get_text().strip()) >= min_chars for pg in pdf)


def list_pdfs(source: str = "real") -> list[Path]:
    """``real`` = dataset PDFs, ``synthetic`` = generated fallback PDFs, ``all`` = both."""
    paths: list[Path] = []
    if source in ("real", "all"):
        paths += sorted(RAW_PDF_DIR.glob("*.pdf"))
    if source in ("synthetic", "all"):
        paths += sorted((SYNTH_DIR / "pdfs").glob("*.pdf"))
    return paths


def load_corpus(source: str = "real") -> list[Document]:
    return [load_pdf(p) for p in list_pdfs(source)]


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    page: int
    text: str


_SECTION_RE = re.compile(r"^(?:\d+\.\s+)?[A-Z][A-Z0-9 /&()\-]{3,}$")


def chunk_document(doc: Document, max_chars: int = 1200) -> list[Chunk]:
    """Split by section headings (ALL-CAPS lines), then pack sections up to ``max_chars``.

    Chunks never cross page boundaries so each keeps a single page number. Each chunk is
    prefixed with the document id and type so retrieval can use them.
    """
    chunks: list[Chunk] = []
    header = f"[{doc.doc_id} | {doc.doc_type.replace('_', ' ')}]"
    for page in doc.pages:
        sections: list[list[str]] = [[]]
        for line in page.text.splitlines():
            line = line.rstrip()
            if not line:
                continue
            if _SECTION_RE.match(line.strip()) and sections[-1]:
                sections.append([])
            sections[-1].append(line)
        buf = ""
        for sec in sections:
            sec_text = "\n".join(sec)
            if buf and len(buf) + len(sec_text) > max_chars:
                chunks.append(_mk_chunk(doc, page.number, len(chunks), header, buf))
                buf = ""
            while len(sec_text) > max_chars:  # very long section: hard split on lines
                cut = sec_text.rfind("\n", 0, max_chars)
                cut = cut if cut > 0 else max_chars
                chunks.append(_mk_chunk(doc, page.number, len(chunks), header, sec_text[:cut]))
                sec_text = sec_text[cut:].lstrip("\n")
            buf = f"{buf}\n{sec_text}" if buf else sec_text
        if buf.strip():
            chunks.append(_mk_chunk(doc, page.number, len(chunks), header, buf))
    return chunks


def _mk_chunk(doc: Document, page: int, idx: int, header: str, body: str) -> Chunk:
    return Chunk(
        chunk_id=f"{doc.doc_id}#c{idx:02d}",
        doc_id=doc.doc_id,
        page=page,
        text=f"{header} (page {page})\n{body.strip()}",
    )
