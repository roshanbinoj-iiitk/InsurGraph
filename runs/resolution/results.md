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
