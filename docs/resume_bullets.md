# Resume bullets (measured)

Title: **Insurance Document Intelligence: LLM Extraction, Knowledge Graph and RAG**

Duck Creek / insurance roles: lead with bullets 1 and 3. General AI/ML roles: lead with 2 and 4.

- Built an LLM pipeline that extracts policyholders, insurers, coverages, limits, claims and dates from
  14 synthetic commercial P&C submission documents into a validated Pydantic schema with page-level
  provenance, reaching 0.93 entity macro-F1 (0.91 relationship macro-F1) on a held-out pack and 0.97
  on held-out synthetic packs.
- Built an evaluation harness (strict and lenient precision, recall and F1 per entity and relationship
  type, bootstrap CIs) with a pack-level dev/test split, and compared 2 prompt strategies across 2 models
  from different providers (Gemini Flash Lite, gpt-oss-120b); all 152 extractions schema-valid
  (11 after one validation retry).
- Modelled results as a NetworkX knowledge graph with page-level provenance and layered entity resolution
  (14/14 held-out name pairs with an LLM fallback vs 12/14 string-only); built a cross-document
  inconsistency detector that found 14 of 14 labelled conflicts (limits, currencies, SOV totals, ABN
  formats, loss dates, policy numbers) end to end, plus 2 real conflicts the dataset did not label.
- Implemented Chroma RAG evaluated on 28 questions (hit@5 0.93–1.00, overall accuracy 0.79–0.86),
  with exact/numeric scoring and an LLM judge from a separate model family validated on 12 manual checks
  (12/12 agreement).
- Hand-labelled 63 gold items (54 relationships, declared-claims tables, valuation dates) plus 28 entity
  name pairs; generated 24 synthetic documents from fact records as a leakage-controlled extra test set;
  shipped with tests, cached and throttled LLM calls, and a one-command reproducible run.

Caveat to keep in mind when quoting these: 7 real documents per split, so CIs are wide
(test entity macro-F1 95% CI 0.87–0.97).
