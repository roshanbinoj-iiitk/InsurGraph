# RAG results (dev)

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
