# Thin slice (Milestone 1)

Model `gemini-flash-lite`, prompt `zero_shot_v1`, documents: PACK000001_02_loss_run_report, PACK000001_04_policy_schedule

* Extraction (strict): entity macro-F1 1.000, relationship macro-F1 1.000
* Graph: 18 nodes, 36 edges
* Coverages of PI-2025-981268: ['business_interruption', 'cyber', 'professional_indemnity', 'property', 'public_liability']
* Parties of PI-2025-981268: {"HAS_INSURED: Greenleaf Property Services Pty Ltd": ["PACK000001_02_loss_run_report", "PACK000001_04_policy_schedule"], "ISSUED_BY: Pinewood Insurance Underwriting Agency": ["PACK000001_02_loss_run_report", "PACK000001_04_policy_schedule"], "PLACED_BY: Ridgeline Insurance Brokers Pty Ltd": ["PACK000001_04_policy_schedule"]}
* RAG: Q: What is the public liability limit on policy PI-2025-981268?  A: **20000000** (top doc PACK000001_01_broker_submission_email)
