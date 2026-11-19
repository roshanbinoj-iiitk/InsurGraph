# Error analysis: test / gemini-flash-lite__few_shot_v1

17 strict-mode errors (a field error counts once; it costs one FP and one FN).

| Category | Count |
|---|---|
| real: spurious relationship | 8 |
| synthetic: row currency wrong (symbol not normalised) | 4 |
| real: spurious location | 1 |
| real: claim label wording | 1 |
| real: date: field date wrong | 1 |
| real: spurious policy | 1 |
| real: spurious date | 1 |

## Examples

**real: spurious relationship**
- `PACK000002_06_insurance_application`: gold=null pred={"subject": "APP-PACK000002-5125", "predicate": "HAS_INSURED", "object": "tide gym"}
- `PACK000002_06_insurance_application`: gold=null pred={"subject": "APP-PACK000002-5125", "predicate": "HAS_COVERAGE", "object": "public_liability"}

**synthetic: row currency wrong (symbol not normalised)**
- `SYNTEST002_02_statement_of_values`: gold={"location_no": 1, "address": "70 foundry rd mount gambier sa 5290", "total_declared_value": 4319000.0, "currency": "AUD"} pred={"location_no": 1, "address": "70 foundry rd mount gambier sa 5290", "total_declared_value": 4319000.0, "currency": "A$"}
- `SYNTEST002_02_statement_of_values`: gold={"location_no": 2, "address": "30 bridge ct devonport tas 7310", "total_declared_value": 5621000.0, "currency": "AUD"} pred={"location_no": 2, "address": "30 bridge ct devonport tas 7310", "total_declared_value": 5621000.0, "currency": "A$"}

**real: spurious location**
- `PACK000002_01_broker_submission_email`: gold=null pred={"location_no": null, "address": "launceston tas", "total_declared_value": null, "currency": null}

**real: claim label wording**
- `PACK000002_02_loss_run_report`: gold={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor collision", "status": "closed", "incurred": 9106.0} pred={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor", "status": "closed", "incurred": 9106.0}

**real: date: field date wrong**
- `PACK000002_03_statement_of_values`: gold={"kind": "policy_end", "date": "2026-12-01"} pred={"kind": "policy_end", "date": "2026-12-26"}

**real: spurious policy**
- `PACK000002_06_insurance_application`: gold=null pred={"policy_number": "APP-PACK000002-5125", "premium": null}

**real: spurious date**
- `PACK000002_07_fnol_form`: gold=null pred={"kind": "report_date", "date": "2025-04-01"}
