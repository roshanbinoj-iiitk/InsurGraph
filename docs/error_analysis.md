# Error analysis

Source: strict-mode errors in `runs/extraction/*/*/errors.jsonl`, categorised by
`scripts/error_analysis.py` (per-run tables in `runs/error_analysis/`). Counts below are for the
test split unless stated; dev showed the same patterns.

## Top 3 failure types

### 1. Relationships invented for documents without a policy number (Gemini, both prompts)

The insurance application prints no policy number, only a document reference
(`APP-PACK000002-5125`) and the pack id. Gemini still fills `relationship_subject` with one of those
and links the insured, every requested coverage and every declared claim to it: **8 of the 8
spurious relationships** on Pack B (10 of 10 on Pack A) come from the application. Few-shot also
emits the reference as a `policy`. Downstream this creates a second "policy" node, which the
detector reports as a false `policy_number_mismatch` in both packs.

*Fix to try next (not applied: would be tuning after seeing test):* state in the prompt that
document/export references are not policy numbers, or validate subjects against the extracted
`policies` list in code.

### 2. PDF line-wrap damage inside table cells

The source PDFs wrap text inside narrow cells mid-token. Models usually repair it, but not always:

* `CLM-2024` / `-74176` → gpt-oss-120b zero-shot kept only `CLM-2024` for all three Pack B
  claims (3 claims missed + 3 spurious), which also broke the `HAS_CLAIM` relationships.
* `Motor` / `Collision`, `Water` / `Damage`, `Liability N` / `otification` → gpt-oss-120b few-shot
  kept the first word only (3 Pack B claims with wrong category).
* `PERIOD 02/12/2025 - 01/12/20` / `26` → Gemini read the SOV policy end as 2026-12-26, which
  produced a false `policy_period_mismatch` flag.

Lenient matching does not rescue these (they are identifiers, labels and dates, not names).

### 3. Date and amount semantics confused across document types

* The claim report's own **Report Date** (2022-04-08) is taken as the claim's `reported_date`
  (gold: reported 2022-03-12 on the loss run; the report does not print it). Seen with every
  configuration on Pack A; it causes a false `claim_attribute_mismatch` flag.
* FNOL "Date Reported" emitted as a `report_date` key date as well as on the claim.
* Synthetic test template T1 writes amounts as `A$5,621,000`; Gemini copied `A$` as the row
  currency instead of `AUD` on all 4 rows of one SOV. This is a normalisation gap found only on
  test: `A$` should map to `AUD`. It was **not** patched in the scorer after the fact, so the test
  numbers include it.

## Other observations

* gpt-oss-120b misses insurers named only in a loss-run heading ("Blackwood Assurance - Claims
  Department") on the synthetic test template (3 docs), and leaves category/status empty on the
  prose-style loss run (T1).
* Strict and lenient scores are identical on the real packs: name variants were already repaired by
  the models; lenient matching mainly helps gpt-oss on synthetic address wrapping.
* Few-shot costs ~50% more tokens than zero-shot. It helped Gemini on test (Pack B entity
  macro-F1 0.918 → 0.933) but hurt gpt-oss on synthetic test (0.978 → 0.891). All differences are
  inside the bootstrap intervals; with 7 real documents per split no prompt or model difference
  here is statistically meaningful.
