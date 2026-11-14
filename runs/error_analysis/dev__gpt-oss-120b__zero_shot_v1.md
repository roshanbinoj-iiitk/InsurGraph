# Error analysis: dev / gpt-oss-120b__zero_shot_v1

18 strict-mode errors (a field error counts once; it costs one FP and one FN).

| Category | Count |
|---|---|
| real: claim label wording | 3 |
| synthetic: party missed (insurer) | 3 |
| synthetic: relationship missed | 3 |
| synthetic: address wording / wrap | 3 |
| real: party missed (insurer) | 1 |
| real: spurious party (insurer) | 1 |
| real: relationship missed | 1 |
| real: spurious relationship | 1 |
| real: party missed (prior_insurer) | 1 |
| real: claim date wrong | 1 |

## Examples

**real: claim label wording**
- `PACK000001_02_loss_run_report`: gold={"claim_no": "CLM-2020-27293", "loss_date": "2027-10-13", "reported_date": "2020-10-02", "category": "liability notification", "status": "closed", "incurred": 21187.0} pred={"claim_no": "CLM-2020-27293", "loss_date": "2027-10-13", "reported_date": "2020-10-02", "category": "liability", "status": "closed", "incurred": 21187.0}
- `PACK000001_02_loss_run_report`: gold={"claim_no": "CLM-2021-94769", "loss_date": "2021-12-02", "reported_date": "2021-12-15", "category": "property damage", "status": "closed", "incurred": 28494.0} pred={"claim_no": "CLM-2021-94769", "loss_date": "2021-12-02", "reported_date": "2021-12-15", "category": "property", "status": "closed", "incurred": 28494.0}

**synthetic: party missed (insurer)**
- `SYNDEV001_03_loss_run_report`: gold={"role": "insurer", "name": "kookaburra commercial", "abn": null} pred=null
- `SYNDEV002_03_loss_run_report`: gold={"role": "insurer", "name": "meridian specialty", "abn": null} pred=null

**synthetic: relationship missed**
- `SYNDEV001_03_loss_run_report`: gold={"subject": "KC-2026-385098", "predicate": "ISSUED_BY", "object": "kookaburra commercial"} pred=null
- `SYNDEV002_03_loss_run_report`: gold={"subject": "MS-2026-200818", "predicate": "ISSUED_BY", "object": "meridian specialty"} pred=null

**synthetic: address wording / wrap**
- `SYNDEV002_02_statement_of_values`: gold={"location_no": 2, "address": "unit 2 221 station ave bendigo vic 3550", "total_declared_value": 2295000.0, "currency": "AUD"} pred={"location_no": 2, "address": "unit 2 221 station ave bendigo vic", "total_declared_value": 2295000.0, "currency": "AUD"}
- `SYNDEV002_02_statement_of_values`: gold={"location_no": 3, "address": "163 foundry ct devonport tas 7310", "total_declared_value": 1960000.0, "currency": "AUD"} pred={"location_no": 3, "address": "163 foundry ct devonport tas", "total_declared_value": 1960000.0, "currency": "AUD"}

**real: party missed (insurer)**
- `PACK000001_04_policy_schedule`: gold={"role": "insurer", "name": "pinewood insurance underwriting agency", "abn": null} pred=null

**real: spurious party (insurer)**
- `PACK000001_04_policy_schedule`: gold=null pred={"role": "insurer", "name": "pinewood insurance", "abn": null}

**real: relationship missed**
- `PACK000001_04_policy_schedule`: gold={"subject": "PI-2025-981268", "predicate": "ISSUED_BY", "object": "pinewood insurance underwriting agency"} pred=null

**real: spurious relationship**
- `PACK000001_04_policy_schedule`: gold=null pred={"subject": "PI-2025-981268", "predicate": "ISSUED_BY", "object": "pinewood insurance"}
