# Architecture

```mermaid
flowchart LR
    subgraph Data
        RAW[RCA 2-pack PDFs<br/>+ ground truth] --> GOLD[gold.py<br/>dataset + hand labels]
        FACTS[synth.py<br/>fact records] --> SPDF[synthetic PDFs<br/>+ gold by construction]
    end
    RAW --> ING[ingest.py<br/>PyMuPDF text, page markers]
    SPDF --> ING
    ING --> EXT[extract.py<br/>prompt v1 zero/few-shot<br/>compact JSON + Pydantic + 1 retry]
    EXT <--> LLM[llm.py<br/>Gemini / Groq / local<br/>diskcache + token limiter + tenacity]
    EXT --> PRED[predictions/*.json]
    PRED --> EVAL[eval/<br/>strict + lenient P/R/F1<br/>bootstrap CIs]
    GOLD --> EVAL
    PRED --> RES[resolve.py<br/>normalise -> fuzzy -> LLM]
    RES --> G[graph.py<br/>NetworkX MultiDiGraph<br/>page provenance]
    G --> DET[inconsistency detector]
    DET --> DEVAL[eval/detector.py<br/>found / missed / extra]
    ING --> CH[chunk_document] --> CHROMA[(Chroma<br/>MiniLM embeddings)]
    CHROMA --> RAG[rag.py plain / graph-routed]
    G --> RAG
    RAG --> REVAL[eval/rag_eval.py<br/>hit@k, exact/numeric,<br/>LLM judge for free text]
```

* **Provenance.** Every extracted item carries `source_doc` and `page`; graph edges keep both, so
  any flag or graph answer can be traced to a page.
* **Leakage control.** Pack A (and synthetic dev, templates D1/D2, seed 1101) is used for prompt
  writing, threshold tuning and model selection. Pack B (and synthetic test, templates T1/T2,
  seed 2202) is run once for the reported test numbers. The few-shot example is an invented
  document, not taken from any pack.
* **Budget control.** Compact row-array output (≈3× fewer output tokens than verbose JSON),
  whole-document requests (every document is < 1K tokens), a persistent call cache, and a
  proactive tokens-per-minute limiter so Groq's 8K TPM is rarely hit.
