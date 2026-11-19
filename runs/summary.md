# Results summary

Best configuration on dev: **gemini-flash-lite__few_shot_v1** (selected on dev only; test run once afterwards).

## Extraction

| Split | Subset | Model | Prompt | Entity macro-F1 strict [95% CI] | lenient | Relationship macro-F1 strict [95% CI] | Valid JSON 1st try (whole split) | Tokens (whole split) |
|---|---|---|---|---|---|---|---|---|
| dev | Pack A (7 docs) | gemini-flash-lite | zero_shot_v1 | 0.971 [0.83, 1.00] | 0.971 | 0.888 [0.73, 1.00] | 19/19 | 30,348 |
| dev | Pack A (7 docs) | gemini-flash-lite | few_shot_v1 | 0.961 [0.87, 1.00] | 0.961 | 0.888 [0.73, 1.00] | 16/19 | 48,472 |
| dev | Pack A (7 docs) | gpt-oss-120b | zero_shot_v1 | 0.918 [0.83, 0.98] | 0.918 | 0.958 [0.88, 1.00] | 18/19 | 36,093 |
| dev | Pack A (7 docs) | gpt-oss-120b | few_shot_v1 | 0.894 [0.79, 0.96] | 0.894 | 0.958 [0.88, 1.00] | 19/19 | 43,140 |
| dev | synthetic dev (12 docs) | gemini-flash-lite | zero_shot_v1 | 0.967 [0.92, 0.99] | 0.967 | 1.000 [1.00, 1.00] | 19/19 | 30,348 |
| dev | synthetic dev (12 docs) | gemini-flash-lite | few_shot_v1 | 1.000 [1.00, 1.00] | 1.000 | 1.000 [1.00, 1.00] | 16/19 | 48,472 |
| dev | synthetic dev (12 docs) | gpt-oss-120b | zero_shot_v1 | 0.957 [0.91, 0.99] | 0.990 | 0.967 [0.92, 1.00] | 18/19 | 36,093 |
| dev | synthetic dev (12 docs) | gpt-oss-120b | few_shot_v1 | 0.935 [0.88, 0.98] | 0.979 | 0.952 [0.87, 0.98] | 19/19 | 43,140 |
| test | Pack B (7 docs) | gemini-flash-lite | zero_shot_v1 | 0.918 [0.81, 0.96] | 0.918 | 0.906 [0.73, 1.00] | 18/19 | 32,163 |
| test | Pack B (7 docs) | gemini-flash-lite | few_shot_v1 | 0.933 [0.87, 0.97] | 0.933 | 0.906 [0.73, 1.00] | 16/19 | 48,851 |
| test | Pack B (7 docs) | gpt-oss-120b | zero_shot_v1 | 0.870 [0.73, 0.96] | 0.870 | 0.881 [0.75, 1.00] | 17/19 | 37,790 |
| test | Pack B (7 docs) | gpt-oss-120b | few_shot_v1 | 0.916 [0.81, 1.00] | 0.916 | 1.000 [1.00, 1.00] | 18/19 | 45,281 |
| test | synthetic test (12 docs) | gemini-flash-lite | zero_shot_v1 | 0.925 [0.83, 0.99] | 0.925 | 0.971 [0.92, 1.00] | 18/19 | 32,163 |
| test | synthetic test (12 docs) | gemini-flash-lite | few_shot_v1 | 0.968 [0.90, 1.00] | 0.968 | 1.000 [1.00, 1.00] | 16/19 | 48,851 |
| test | synthetic test (12 docs) | gpt-oss-120b | zero_shot_v1 | 0.978 [0.94, 0.99] | 0.978 | 0.962 [0.91, 0.99] | 17/19 | 37,790 |
| test | synthetic test (12 docs) | gpt-oss-120b | few_shot_v1 | 0.891 [0.80, 0.99] | 0.891 | 0.962 [0.91, 0.99] | 18/19 | 45,281 |

## Entity resolution

# Entity resolution

Fuzzy layer tuned on 14 dev pairs: **token_set_ratio >= 100** (dev accuracy 1.00).

| Split | Resolver | n | Accuracy | Precision | Recall | FP | FN |
|---|---|---|---|---|---|---|---|
| dev | normalise + fuzzy | 14 | 1.00 | 1.00 | 1.00 | 0 | 0 |
| dev | normalise + fuzzy + LLM | 14 | 1.00 | 1.00 | 1.00 | 0 | 0 |
| test | normalise + fuzzy | 14 | 0.86 | 1.00 | 0.78 | 0 | 2 |
| test | normalise + fuzzy + LLM | 14 | 1.00 | 1.00 | 1.00 | 0 | 0 |

Per-pair decisions (layer that decided, fuzzy score) are in `decisions.jsonl`.

Errors:

- test / normalise + fuzzy: `Southern Cross Commercial Underwriters Pty Ltd` vs `Southern Cross Commercial Underwriting` (gold True, layer fuzzy, score 92.1)
- test / normalise + fuzzy: `Zurich North America` vs `Zurich American Insurance Company` (gold True, layer fuzzy, score 75.6)


## Inconsistency detector

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


## RAG

### RAG results (dev)

Answer model `gemini-flash-lite`, top-k = 5, judge `qwen-judge` (free-text answers only), embeddings: local sentence-transformers.

| Variant | n | Retrieval hit@k | Exact/numeric acc. (n) | Judged free-text acc. (n) | Overall acc. |
|---|---|---|---|---|---|
| plain | 14 | 0.93 | 0.91 (11) | 0.67 (3) | 0.86 |
| graph | 14 | 0.93 | 0.91 (11) | 0.33 (3) | 0.79 |

Wrong answers:

- plain A10: Q: What loss date does the loss run show for claim CLM-2020-27293, and does it agree with the insurance application? | ref: The loss run shows 13/10/2027 but the application declares 24/09/2020, so they disagree (the loss run date is after the claim was reported). | got: not found (hit=True)
- plain A11: Q: Who was Greenleaf Property Services' current or most recent insurer before this submission? | ref: Verity Insurance Underwriting Agency | got: not found (hit=False)
- graph A10: Q: What loss date does the loss run show for claim CLM-2020-27293, and does it agree with the insurance application? | ref: The loss run shows 13/10/2027 but the application declares 24/09/2020, so they disagree (the loss run date is after the claim was reported). | got: not found (hit=True)
- graph A11: Q: Who was Greenleaf Property Services' current or most recent insurer before this submission? | ref: Verity Insurance Underwriting Agency | got: not found (hit=False)
- graph A12: Q: What happened in claim CLM-2023-10762 and were the police notified? | ref: Tools were stolen from the premises (theft), and yes, the police were notified. | got: not found (hit=True)

### RAG results (test)

Answer model `gemini-flash-lite`, top-k = 5, judge `qwen-judge` (free-text answers only), embeddings: local sentence-transformers.

| Variant | n | Retrieval hit@k | Exact/numeric acc. (n) | Judged free-text acc. (n) | Overall acc. |
|---|---|---|---|---|---|
| plain | 14 | 1.00 | 0.91 (11) | 0.33 (3) | 0.79 |
| graph | 14 | 1.00 | 0.91 (11) | 0.67 (3) | 0.86 |

Wrong answers:

- plain B07: Q: Who reported claim CLM-2025-13385 and what is their role? | ref: Zara Williams, the Operations Manager. | got: not found (hit=True)
- plain B08: Q: What grand total is displayed on the Tide Gym statement of values? | ref: 15383103 | got: not found (hit=True)
- plain B09: Q: Does the displayed total on the Tide Gym statement of values equal the sum of its location totals? | ref: No. The five location totals sum to 14,635,928 but the displayed total is 15,383,103, a difference of 747,175. | got: not found (hit=True)
- graph B08: Q: What grand total is displayed on the Tide Gym statement of values? | ref: 15383103 | got: not found (hit=True)
- graph B09: Q: Does the displayed total on the Tide Gym statement of values equal the sum of its location totals? | ref: No. The five location totals sum to 14,635,928 but the displayed total is 15,383,103, a difference of 747,175. | got: not found (hit=True)
