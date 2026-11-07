# Phase 0: data note and Gate 1 decision

## Source

RCA Insurance Library 2-pack preview (`RootCauseAnalytics/Insurance-Library-Sample`, Hugging Face),
CC-BY-NC-4.0, fully synthetic Australian commercial P&C submission packs. Downloaded with
`scripts/download_data.py` into `data/raw/`. Only the clean PDFs are used; the `pdfs_scanned/`
variants (rotation + JPEG noise) are left for a future OCR robustness test.

## Inventory (`scripts/phase0_inspect.py`, `runs/phase0/inventory.csv`)

| | |
|---|---|
| Packs | 2 (`PACK000001` = Greenleaf Property Services, `PACK000002` = Tide Gym) |
| Documents / pages | 14 / 18 (11 one-page, 3 two-page) |
| Document types | broker submission email, loss run, statement of values (SOV), policy schedule, insurance application, FNOL form (2 each); claim report, certificate of currency (1 each) |
| Text layer | Present on every clean PDF: no OCR needed |
| Tokens | ~6.1K in total, 270–710 per document (~4 chars/token estimate) |

Every document fits in a single extraction request (well under Groq's ~4–5K token budget per
request), so the extractor sends whole documents with page markers. Section chunking
(`src/ingest.py:chunk_document`) is used for RAG: 35 chunks over the 14 documents.

## Text extraction: pymupdf4llm vs plain PyMuPDF

Probe strings that must survive intact (SOV address and USD total, loss-run claim number and
totals, schedule limits):

| Document | PyMuPDF | pymupdf4llm |
|---|---|---|
| Statement of values | 3/3 | 2/3 (address split across two table columns: `83` / `Crossing Way, Canberra`) |
| Loss run | 3/3 | 2/3 (totals row cells split: `A` / `UD $165,`) |
| Policy schedule | 3/3 | 3/3 |

pymupdf4llm's table detection mis-segments the dense spreadsheet-style grids and also calls
Tesseract on pages that already have text. **Decision: plain PyMuPDF text.** Both methods
inherit the PDF's own mid-word wrapping inside narrow table cells (`Greenleaf Property Se` /
`rvices Pty Ltd`, `AUD $21,1` / `87`), which the extractor has to repair; this is a realistic
error source and shows up in the error analysis.

## Ground-truth format

`ground_truth.jsonl` has one row per PDF. Each row repeats the pack-level facts (insured, ABN,
broker, insurer, policy number, period) and adds document-type-specific fields
(`limits_json`, `deductibles_json`, `location_rows_json`, `claim_rows_json`, `fnol_*`,
`report_*`, `coc_limits_json`, ...). Engineered inconsistencies are in `red_flags_json`
(`flag_type`, `target_doc_type`, `overrides`); the `displayed_*` fields hold the value actually
printed when an override applies (e.g. `displayed_abn = "21275287720"`).

Important: pack-level fields are repeated on **every** row even when the document does not show
them (the Tide Gym email never names the insurer or the coverages). The gold set is therefore
built per document type from the fields that each template actually prints, checked against the
PDF text (`src/gold.py`, `data/gold/hand_labels.json`).

Engineered inconsistencies (4): `currency_mismatch` and `loss_date_outside_policy_period`
(Pack 1), `sov_total_mismatch` and `abn_formatting_inconsistency` (Pack 2).

Reading the PDFs also shows **unlabelled** conflicts that a cross-document detector should find:
the Tide Gym certificate of currency prints Public Liability AUD 20M and Property AUD 1M while
the schedule prints 10M and 2M; the broker emails' "years trading" disagree with the
applications (25 vs 17, 15 vs 29). These are reported separately, never counted as false flags
without comment.

## Label-to-schema mapping

| Schema | Dataset fields |
|---|---|
| `Party(insured)` | `insured_business_name`, `insured_abn` / `displayed_abn`, `displayed_insured_name` |
| `Party(insurer / broker)` | `insurer_name`, `broker_company` |
| `Party(prior_insurer / interested_party / loss_adjuster)` | `prior_insurer`, `interested_party_name`, `report_adjuster_firm` |
| `Policy` | `policy_number`, `premium` |
| `Coverage` | `limits_json`, `deductibles_json`, `coc_limits_json`, `requested_coverage` |
| `Location` | `location_rows_json`, `displayed_locations_json`, `insured_address`, `fnol_incident_location` |
| `Claim` | `claim_rows_json` (+ overrides), `fnol_*`, `report_*` |
| `KeyDate` | `policy_period_*`, `target_inception_date`, `valuation_date`, `certificate_date`, `report_date` |
| `Relationship` | not labelled in the dataset: hand-labelled |

## Gate 1 decision

* **Can the labels be mapped to the schema?** Yes: every schema field has a dataset source,
  except relationships and the application's declared-claims table, which are hand-labelled.
* **Variety check (fallback trigger).** Pack B (test) yields fewer than ~10 gold items for
  several entity types (claims, locations, dates, policies), and the insurance application, FNOL
  form and SOV use the *same* template in both packs. The fallback trigger is met.
* **Action:** keep the real dataset as the primary benchmark (Pack A dev, Pack B test) and add
  the plan's fallback: synthetic packs generated *from fact records* with code templates
  (`src/synth.py`), ground truth correct by construction, programmatically seeded
  inconsistencies, and disjoint templates and random seeds for synthetic dev vs synthetic test.
  Final test results are reported as separate rows (Pack B, synthetic test), with item counts
  and confidence intervals.
