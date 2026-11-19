# Inconsistency detector

### gold extractions (detector logic only), dev

Labelled flags: **7 found / 0 missed** of 7; extra flags: 1 corroborating, 0 true but unlabelled, **0 false**.

| Pack | Flag | Outcome | Detail |
|---|---|---|---|
| PACK000001 | currency_mismatch | found | Unit 15, 433 Pioneer Bvd, Townsville QLD 4810: value declared in USD, pack currency AUD |
| PACK000001 | loss_date_outside_policy_period | found | CLM-2020-27293: loss 2027-10-13 after reported 2020-10-02 / valuation 2025-05-13 |
| PACK000001 | claim_attribute_mismatch | corroborating | CLM-2020-27293: loss_date differs across documents |
| SYNDEV001 | abn_formatting_inconsistency | found | ABN 77220074584 printed in 2 formats |
| SYNDEV002 | abn_formatting_inconsistency | found | ABN 92762501283 printed in 2 formats |
| SYNDEV002 | loss_date_outside_policy_period | found | CL-2022-67031: loss 2027-07-12 after reported 2022-12-12 / valuation 2025-11-23 |
| SYNDEV003 | policy_number_mismatch | found | 2 different policy numbers in one submission |
| SYNDEV003 | sov_total_mismatch | found | displayed total 5,591,000 != sum of rows 4,757,000 |

### gold extractions (detector logic only), test

Labelled flags: **7 found / 0 missed** of 7; extra flags: 0 corroborating, 2 true but unlabelled, **0 false**.

| Pack | Flag | Outcome | Detail |
|---|---|---|---|
| PACK000002 | abn_formatting_inconsistency | found | ABN 21275287720 printed in 2 formats |
| PACK000002 | sov_total_mismatch | found | displayed total 15,383,103 != sum of rows 14,635,928 |
| PACK000002 | limit_mismatch | true (unlabelled) | public_liability: limit differs across documents |
| PACK000002 | limit_mismatch | true (unlabelled) | property: limit differs across documents |
| SYNTEST001 | loss_date_outside_policy_period | found | CL-2023-65427: loss 2028-10-06 after reported 2023-04-23 / valuation 2026-05-07 |
| SYNTEST002 | limit_mismatch | found | public_liability: limit differs across documents |
| SYNTEST002 | loss_date_outside_policy_period | found | CL-2025-99029: loss 2028-02-18 after reported 2025-08-29 / valuation 2026-02-17 |
| SYNTEST003 | currency_mismatch | found | Unit 17, 111 Wattle Pde, Bendigo VIC 3550: value declared in USD, pack currency AUD |
| SYNTEST003 | loss_date_outside_policy_period | found | CL-2021-21003: loss 2027-11-22 after reported 2022-01-10 / valuation 2025-10-29 |

### best model's extractions (end to end), dev

Labelled flags: **7 found / 0 missed** of 7; extra flags: 1 corroborating, 0 true but unlabelled, **2 false**.

| Pack | Flag | Outcome | Detail |
|---|---|---|---|
| PACK000001 | currency_mismatch | found | Unit 15, 433 Pioneer Bvd, Townsville QLD 4810: value declared in USD, pack currency AUD |
| PACK000001 | loss_date_outside_policy_period | found | CLM-2020-27293: loss 2027-10-13 after reported 2020-10-02 / valuation 2025-05-13 |
| PACK000001 | claim_attribute_mismatch | corroborating | CLM-2020-27293: loss_date differs across documents |
| PACK000001 | claim_attribute_mismatch | false flag | CLM-2022-56562: reported_date differs across documents |
| PACK000001 | policy_number_mismatch | false flag | 2 different policy numbers in one submission |
| SYNDEV001 | abn_formatting_inconsistency | found | ABN 77220074584 printed in 2 formats |
| SYNDEV002 | abn_formatting_inconsistency | found | ABN 92762501283 printed in 2 formats |
| SYNDEV002 | loss_date_outside_policy_period | found | CL-2022-67031: loss 2027-07-12 after reported 2022-12-12 / valuation 2025-11-23 |
| SYNDEV003 | policy_number_mismatch | found | 2 different policy numbers in one submission |
| SYNDEV003 | sov_total_mismatch | found | displayed total 5,591,000 != sum of rows 4,757,000 |

### best model's extractions (end to end), test

Labelled flags: **7 found / 0 missed** of 7; extra flags: 0 corroborating, 2 true but unlabelled, **2 false**.

| Pack | Flag | Outcome | Detail |
|---|---|---|---|
| PACK000002 | abn_formatting_inconsistency | found | ABN 21275287720 printed in 2 formats |
| PACK000002 | sov_total_mismatch | found | displayed total 15,383,103 != sum of rows 14,635,928 |
| PACK000002 | policy_period_mismatch | false flag | SC-2025-372491: policy_end differs across documents |
| PACK000002 | limit_mismatch | true (unlabelled) | public_liability: limit differs across documents |
| PACK000002 | limit_mismatch | true (unlabelled) | property: limit differs across documents |
| PACK000002 | policy_number_mismatch | false flag | 2 different policy numbers in one submission |
| SYNTEST001 | loss_date_outside_policy_period | found | CL-2023-65427: loss 2028-10-06 after reported 2023-04-23 / valuation 2026-05-07 |
| SYNTEST002 | limit_mismatch | found | public_liability: limit differs across documents |
| SYNTEST002 | loss_date_outside_policy_period | found | CL-2025-99029: loss 2028-02-18 after reported 2025-08-29 / valuation 2026-02-17 |
| SYNTEST003 | currency_mismatch | found | Unit 17, 111 Wattle Pde, Bendigo VIC 3550: value declared in USD, pack currency AUD |
| SYNTEST003 | loss_date_outside_policy_period | found | CL-2021-21003: loss 2027-11-22 after reported 2022-01-10 / valuation 2025-10-29 |
