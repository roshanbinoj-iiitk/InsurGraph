# RCA Insurance Library - Free 2-Pack Preview

Welcome. This is the free 2-pack preview of the RCA Insurance Library, a synthetic commercial P&C training document library for document AI evaluation.

Everything in this folder is fully synthetic. No real policyholder, claimant, broker, insurer or customer data was used in generation. Disclaimer banners are embedded in every PDF.

If anything is unclear or you want this weighted differently (more loss runs, more SOVs, more FNOL forms, larger claim history), reply to my email and I will adjust before delivery of the paid sprint.

Jack Webb, Root Cause Analytics
rootcauseanalytics.com.au

---

## 5-minute recommended review path

Allocate 5 minutes. The goal is to evaluate whether the structural complexity, ground truth, bounding boxes, and engineered cross-document red flags fit your QA workflow.

### Minute 1 - Open one full pack end to end

Open the PDFs for Pack 1 in this order:

1. `pdfs/PACK000001_01_broker_submission_email.pdf`
2. `pdfs/PACK000001_02_loss_run_report.pdf`
3. `pdfs/PACK000001_03_statement_of_values.pdf`
4. `pdfs/PACK000001_04_policy_schedule.pdf`
5. `pdfs/PACK000001_06_insurance_application.pdf`
6. `pdfs/PACK000001_07_fnol_form.pdf`
7. `pdfs/PACK000001_08_claim_report.pdf`

This is one complete commercial P&C submission. Note the cross-document references: the same insured business name, ABN, policy number, and location numbers appear across docs.

### Minute 2 - Open the scanned variants

Open `pdfs_scanned/PACK000001_02_loss_run_report_scanned.pdf` next to its clean counterpart. The scanned variant has light rotation, JPEG compression and printer-style noise. This is your OCR robustness test material.

Each clean PDF has a matching scanned variant in `pdfs_scanned/`.

### Minute 3 - Inspect the engineered red flags

This is where the library earns its place in your regression suite. Open `ground_truth.jsonl` and search for `"red_flags_json"`. The 2-pack preview ships with 4 engineered cross-document inconsistencies:

| Pack | Flag | What broke |
|------|------|------------|
| PACK000001 | `currency_mismatch` | Statement of values declares one location's total in a currency other than AUD |
| PACK000001 | `loss_date_outside_policy_period` | A claim's loss date in the loss run falls outside any covered policy period |
| PACK000002 | `sov_total_mismatch` | Statement of values displayed total does not equal the sum of location rows |
| PACK000002 | `abn_formatting_inconsistency` | ABN formatting differs between documents (e.g. spaced vs unspaced) |

These are the regression cases your production data does not have by definition. If your extraction pipeline does not flag them on the matching PDFs, that is the gap.

The full library has 14 engineered red flag types covering loss run total mismatch, missing attachments, policy number mismatch, location address mismatch, claim after policy end, outdated loss runs, missing broker signature, industry code mismatch, certificate expiry before inception, and insured name mismatch.

### Minute 4 - Inspect the ground truth and bounding boxes

Open `ground_truth.csv` and `ground_truth.jsonl`. Each row corresponds to one PDF and includes structured fields for:

- Pack identity: `submission_pack_id`, `document_type`, `pdf_filename`
- Insured entity: `insured_business_name`, `abn`, `industry`, `industry_anzsic`
- Policy: `policy_number`, `inception_date`, `expiry_date`, `currency`
- Per-doc fields: applicable schema per document type
- Style metadata: `style_profile`, `template_family`, `document_origin`, `synthetic_disclaimer_variant`, `density`
- Red flags: `generated_red_flags` (label), `red_flags_json` (full structure)

Open `bboxes.jsonl`. Each row has per-field bounding boxes with `page`, `x`, `y`, `width`, `height` in PDF coordinate space. Use these for layout extraction QA and to compare your extractor's coordinates against ground truth.

### Minute 5 - Decide

Three useful questions:

1. Does the structural complexity match what you see in real broker submissions?
2. Are the engineered red flags the regression cases you want to add to your eval suite?
3. Would a 10-pack version (50 to 80 documents, all 8 doc types, full red flag coverage, same-day delivery, AUD $2,500 fixed) close a gap in your QA workflow?

If yes to 3, the Insurance QA Sprint Pack is at https://rootcauseanalytics.com.au/libraries/benchmark-packs and I can send a Stripe link directly.

If no, I would still like 60 seconds of feedback on what was missing. Reply to my email or LinkedIn DM.

---

## What is in this folder

```
/
  pdfs/                          # clean PDFs (one per document, 13-14 files)
  pdfs_scanned/                  # scanned variants with rotation + JPEG noise
  ground_truth.csv               # one row per document, all labelled fields
  ground_truth.jsonl             # same as CSV, JSONL for line-stream consumers
  bboxes.jsonl                   # per-field bounding boxes, PDF coordinates
  manifest.json                  # generation metadata (seed, counts)
  splits.json                    # train / val / test stratified splits
  README.md                      # auto-generated library card (HF-style)
  README_START_HERE.md           # this file
```

## What is not in this folder (but is in the paid sprint)

- 10 complete submission packs instead of 2 (50 to 80 PDFs)
- Full coverage of all 8 document types per pack
- Full coverage of all 14 engineered red flag types
- Engineered red flag summary CSV (one row per flag, ready to import as test cases)
- 30-minute handover call to walk through it and weight the next batch
- Same-day delivery from payment confirmation
- AUD $2,500, fixed, public price

## Trust and licensing

- Fully synthetic. No real policyholder, claimant, broker, insurer or customer data.
- "SYNTHETIC TRAINING DOCUMENT" disclaimer embedded on every page.
- Use for: document AI QA, regression testing, demo data, model evaluation.
- Do not use for: actual underwriting, claims adjudication, policy issuance, regulatory submission, or any real insurance workflow.

## Contact

Jack Webb, founder
Root Cause Analytics, Sydney
rootcauseanalytics.com.au
