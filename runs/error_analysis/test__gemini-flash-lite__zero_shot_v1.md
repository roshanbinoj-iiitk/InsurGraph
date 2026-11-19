# Error analysis: test / gemini-flash-lite__zero_shot_v1

27 strict-mode errors (a field error counts once; it costs one FP and one FN).

| Category | Count |
|---|---|
| real: spurious relationship | 8 |
| synthetic: policy missed | 4 |
| synthetic: row currency wrong (symbol not normalised) | 4 |
| real: policy missed | 2 |
| synthetic: party missed (insurer) | 2 |
| synthetic: relationship missed | 2 |
| real: spurious party (insurer) | 1 |
| real: claim label wording | 1 |
| real: location missed | 1 |
| synthetic: spurious party (insurer) | 1 |
| synthetic: spurious relationship | 1 |

## Examples

**real: spurious relationship**
- `PACK000002_06_insurance_application`: gold=null pred={"subject": "PACK000002", "predicate": "HAS_INSURED", "object": "tide gym"}
- `PACK000002_06_insurance_application`: gold=null pred={"subject": "PACK000002", "predicate": "HAS_COVERAGE", "object": "public_liability"}

**synthetic: policy missed**
- `SYNTEST001_03_loss_run_report`: gold={"policy_number": "HM-2026-695998", "premium": null} pred=null
- `SYNTEST002_02_statement_of_values`: gold={"policy_number": "BA-2026-151831", "premium": null} pred=null

**synthetic: row currency wrong (symbol not normalised)**
- `SYNTEST002_02_statement_of_values`: gold={"location_no": 1, "address": "70 foundry rd mount gambier sa 5290", "total_declared_value": 4319000.0, "currency": "AUD"} pred={"location_no": 1, "address": "70 foundry rd mount gambier sa 5290", "total_declared_value": 4319000.0, "currency": "A$"}
- `SYNTEST002_02_statement_of_values`: gold={"location_no": 2, "address": "30 bridge ct devonport tas 7310", "total_declared_value": 5621000.0, "currency": "AUD"} pred={"location_no": 2, "address": "30 bridge ct devonport tas 7310", "total_declared_value": 5621000.0, "currency": "A$"}

**real: policy missed**
- `PACK000002_03_statement_of_values`: gold={"policy_number": "SC-2025-372491", "premium": null} pred=null
- `PACK000002_07_fnol_form`: gold={"policy_number": "SC-2025-372491", "premium": null} pred=null

**synthetic: party missed (insurer)**
- `SYNTEST001_03_loss_run_report`: gold={"role": "insurer", "name": "harbourline mutual", "abn": null} pred=null
- `SYNTEST003_03_loss_run_report`: gold={"role": "insurer", "name": "harbourline mutual", "abn": null} pred=null

**synthetic: relationship missed**
- `SYNTEST001_03_loss_run_report`: gold={"subject": "HM-2026-695998", "predicate": "ISSUED_BY", "object": "harbourline mutual"} pred=null
- `SYNTEST003_03_loss_run_report`: gold={"subject": "HM-2025-545314", "predicate": "ISSUED_BY", "object": "harbourline mutual"} pred=null

**real: spurious party (insurer)**
- `PACK000002_01_broker_submission_email`: gold=null pred={"role": "insurer", "name": "southern underwriting", "abn": null}

**real: claim label wording**
- `PACK000002_02_loss_run_report`: gold={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor collision", "status": "closed", "incurred": 9106.0} pred={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor", "status": "closed", "incurred": 9106.0}
