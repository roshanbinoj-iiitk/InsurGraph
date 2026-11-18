# RAG results (test)

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
