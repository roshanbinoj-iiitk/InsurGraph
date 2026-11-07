---
license: cc-by-nc-4.0
language:
- en
tags:
- synthetic-data
- document-ai
- ocr
- insurance
- commercial-pc
- evaluation
- regression-testing
pretty_name: RCA Insurance Library - 2-Pack Preview
size_categories:
- n<1K
---

# RCA Insurance Library - 2-Pack Preview

Public sample from the RCA Insurance Library. Two complete synthetic commercial P&C submission packs (14 documents) with ground truth and engineered cross-document inconsistencies.

Fully synthetic. No real policyholder, claimant, broker, insurer or customer data. SYNTHETIC TRAINING DOCUMENT disclaimer on every page.

## What is in the preview

- 14 PDFs across 8 commercial P&C document types: broker submission emails, loss run reports, statements of values, policy schedules, certificates of currency, insurance applications, FNOL forms, claim reports
- Clean and scanned variants for each (rotation + JPEG noise)
- Ground truth CSV and JSONL with labelled fields
- Per-claim and per-location row-level bounding boxes
- 4 engineered cross-document inconsistencies labelled in ground truth (currency mismatch, loss date outside policy period, SOV total mismatch, ABN formatting inconsistency)

## What is in the full library

25 submission packs, 160 documents, 14 engineered red flag types covering loss run mismatches, missing attachments, policy number mismatches, location address mismatches, claim after policy end, outdated valuations, missing broker signatures, industry code mismatches, certificate expiry inconsistencies, and others.

## What it is for

- Document AI QA and regression testing
- Loss run, SOV, FNOL, and submission intake extraction testing
- Pack-level consistency testing (cross-document validation)
- Demo data for prospect POCs (no PII risk)

## What it is not for

Real underwriting, claims adjudication, policy issuance, or regulatory submission.

## License

Creative Commons Attribution-NonCommercial 4.0. For commercial use or the full library, see [rootcauseanalytics.com.au](https://rootcauseanalytics.com.au).

## Citation

```bibtex
@misc{rca-insurance-2pack-preview,
  author = {Webb, Jack},
  title = {RCA Insurance Library - 2-Pack Preview},
  year = {2026},
  publisher = {Root Cause Analytics},
  url = {https://rootcauseanalytics.com.au/libraries/insurance}
}
```
