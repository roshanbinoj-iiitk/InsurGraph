# Error analysis: test / gpt-oss-120b__zero_shot_v1

29 strict-mode errors (a field error counts once; it costs one FP and one FN).

| Category | Count |
|---|---|
| real: date missed | 4 |
| synthetic: relationship missed | 4 |
| real: claim missed | 3 |
| real: spurious claim | 3 |
| real: relationship missed | 3 |
| synthetic: party missed (insurer) | 3 |
| real: spurious relationship | 2 |
| synthetic: location missed | 2 |
| real: party missed (broker) | 1 |
| real: party missed (insured) | 1 |
| real: location missed | 1 |
| real: spurious date | 1 |
| synthetic: spurious location | 1 |

## Examples

**real: date missed**
- `PACK000002_03_statement_of_values`: gold={"kind": "policy_start", "date": "2025-12-02"} pred=null
- `PACK000002_03_statement_of_values`: gold={"kind": "policy_end", "date": "2026-12-01"} pred=null

**synthetic: relationship missed**
- `SYNTEST001_01_policy_schedule`: gold={"subject": "HM-2026-695998", "predicate": "COVERS_LOCATION", "object": "1"} pred=null
- `SYNTEST001_03_loss_run_report`: gold={"subject": "HM-2026-695998", "predicate": "ISSUED_BY", "object": "harbourline mutual"} pred=null

**real: claim missed**
- `PACK000002_02_loss_run_report`: gold={"claim_no": "CLM-2024-74176", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor collision", "status": "closed", "incurred": 9106.0} pred=null
- `PACK000002_02_loss_run_report`: gold={"claim_no": "CLM-2024-94098", "loss_date": "2024-09-12", "reported_date": "2024-10-03", "category": "water damage", "status": "closed", "incurred": 61365.0} pred=null

**real: spurious claim**
- `PACK000002_02_loss_run_report`: gold=null pred={"claim_no": "CLM-2024", "loss_date": "2024-05-29", "reported_date": "2024-06-15", "category": "motor", "status": "closed", "incurred": 9106.0}
- `PACK000002_02_loss_run_report`: gold=null pred={"claim_no": "CLM-2024", "loss_date": "2024-09-12", "reported_date": "2024-10-03", "category": "water", "status": "closed", "incurred": 61365.0}

**real: relationship missed**
- `PACK000002_02_loss_run_report`: gold={"subject": "SC-2025-372491", "predicate": "HAS_CLAIM", "object": "CLM-2024-74176"} pred=null
- `PACK000002_02_loss_run_report`: gold={"subject": "SC-2025-372491", "predicate": "HAS_CLAIM", "object": "CLM-2024-94098"} pred=null

**synthetic: party missed (insurer)**
- `SYNTEST001_03_loss_run_report`: gold={"role": "insurer", "name": "harbourline mutual", "abn": null} pred=null
- `SYNTEST002_03_loss_run_report`: gold={"role": "insurer", "name": "blackwood assurance", "abn": null} pred=null

**real: spurious relationship**
- `PACK000002_02_loss_run_report`: gold=null pred={"subject": "SC-2025-372491", "predicate": "HAS_CLAIM", "object": "CLM-2024"}
- `PACK000002_02_loss_run_report`: gold=null pred={"subject": "SC-2025-372491", "predicate": "HAS_CLAIM", "object": "CLM-2025"}

**synthetic: location missed**
- `SYNTEST001_01_policy_schedule`: gold={"location_no": 1, "address": "199 quarry pde devonport tas 7310", "total_declared_value": null, "currency": null} pred=null
- `SYNTEST001_04_certificate_of_currency`: gold={"location_no": null, "address": "199 quarry pde devonport tas 7310", "total_declared_value": null, "currency": null} pred=null
