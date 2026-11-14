# Error analysis: dev / gemini-flash-lite__few_shot_v1

13 strict-mode errors (a field error counts once; it costs one FP and one FN).

| Category | Count |
|---|---|
| real: spurious relationship | 10 |
| real: spurious policy | 1 |
| real: spurious date | 1 |
| real: claim date wrong | 1 |

## Examples

**real: spurious relationship**
- `PACK000001_06_insurance_application`: gold=null pred={"subject": "APP-PACK000001-5326", "predicate": "HAS_INSURED", "object": "greenleaf property services"}
- `PACK000001_06_insurance_application`: gold=null pred={"subject": "APP-PACK000001-5326", "predicate": "HAS_COVERAGE", "object": "public_liability"}

**real: spurious policy**
- `PACK000001_06_insurance_application`: gold=null pred={"policy_number": "APP-PACK000001-5326", "premium": null}

**real: spurious date**
- `PACK000001_06_insurance_application`: gold=null pred={"kind": "policy_end", "date": "2026-06-08"}

**real: claim date wrong**
- `PACK000001_08_claim_report`: gold={"claim_no": "CLM-2022-56562", "loss_date": "2022-03-05", "reported_date": null, "category": "liability notification", "status": "closed", "incurred": 72781.0} pred={"claim_no": "CLM-2022-56562", "loss_date": "2022-03-05", "reported_date": "2022-04-08", "category": "liability notification", "status": "closed", "incurred": 72781.0}
