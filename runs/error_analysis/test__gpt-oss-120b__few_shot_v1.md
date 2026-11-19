# Error analysis: test / gpt-oss-120b__few_shot_v1

18 strict-mode errors (a field error counts once; it costs one FP and one FN).

| Category | Count |
|---|---|
| synthetic: relationship missed | 4 |
| synthetic: claim label wording | 4 |
| real: claim label wording | 3 |
| synthetic: party missed (insurer) | 3 |
| real: date: field date wrong | 1 |
| synthetic: location missed | 1 |
| synthetic: spurious location | 1 |
| synthetic: location: field total_declared_value wrong | 1 |

## Examples

**synthetic: relationship missed**
- `SYNTEST001_01_policy_schedule`: gold={"subject": "HM-2026-695998", "predicate": "COVERS_LOCATION", "object": "1"} pred=null
- `SYNTEST001_03_loss_run_report`: gold={"subject": "HM-2026-695998", "predicate": "ISSUED_BY", "object": "harbourline mutual"} pred=null

**synthetic: claim label wording**
- `SYNTEST001_03_loss_run_report`: gold={"claim_no": "CL-2022-23144", "loss_date": "2022-06-21", "reported_date": "2022-07-15", "category": "property damage", "status": "open", "incurred": 48552.0} pred={"claim_no": "CL-2022-23144", "loss_date": "2022-06-21", "reported_date": "2022-07-15", "category": null, "status": null, "incurred": 48552.0}
- `SYNTEST001_03_loss_run_report`: gold={"claim_no": "CL-2023-65427", "loss_date": "2028-10-06", "reported_date": "2023-04-23", "category": "liability notification", "status": "open", "incurred": 19765.0} pred={"claim_no": "CL-2023-65427", "loss_date": "2028-10-06", "reported_date": "2023-04-23", "category": null, "status": null, "incurred": 19765.0}

**real: claim label wording**
- `PACK000002_02_loss_run_report`: gold={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor collision", "status": "closed", "incurred": 9106.0} pred={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor", "status": "closed", "incurred": 9106.0}
- `PACK000002_02_loss_run_report`: gold={"claim_no": "CLM-2024-94098", "loss_date": "2024-09-12", "reported_date": "2024-10-03", "category": "water damage", "status": "closed", "incurred": 61365.0} pred={"claim_no": "CLM-2024-94098", "loss_date": "2024-09-12", "reported_date": "2024-10-03", "category": "water", "status": "closed", "incurred": 61365.0}

**synthetic: party missed (insurer)**
- `SYNTEST001_03_loss_run_report`: gold={"role": "insurer", "name": "harbourline mutual", "abn": null} pred=null
- `SYNTEST002_03_loss_run_report`: gold={"role": "insurer", "name": "blackwood assurance", "abn": null} pred=null

**real: date: field date wrong**
- `PACK000002_03_statement_of_values`: gold={"kind": "policy_end", "date": "2026-12-01"} pred={"kind": "policy_end", "date": "2020-12-01"}

**synthetic: location missed**
- `SYNTEST001_01_policy_schedule`: gold={"location_no": 1, "address": "199 quarry pde devonport tas 7310", "total_declared_value": null, "currency": null} pred=null

**synthetic: spurious location**
- `SYNTEST001_01_policy_schedule`: gold=null pred={"location_no": null, "address": "199 quarry pde devonport tas 7310", "total_declared_value": null, "currency": null}

**synthetic: location: field total_declared_value wrong**
- `SYNTEST002_02_statement_of_values`: gold={"location_no": 1, "address": "70 foundry rd mount gambier sa 5290", "total_declared_value": 4319000.0, "currency": "AUD"} pred={"location_no": 1, "address": "70 foundry rd mount gambier sa 5290", "total_declared_value": 3715000.0, "currency": "AUD"}
