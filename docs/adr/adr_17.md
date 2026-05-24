# ADR-17: External Sharing Model

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Deferred
**Trigger:** An external organisation (patient registry, hospital system, research consortium) wants to consume data products without direct Databricks platform access.
**Depends on:** Gold products built
**Blocks:** External data distribution

---

## Knowledge Required When Triggered

Delta Sharing protocol documentation — the open protocol for sharing Delta tables across organisational boundaries without data copying. No Databricks subscription required on the consumer side. Includes audit logs of what was accessed and when.

Data clean room patterns — for sharing derived or aggregated data without exposing raw patient-level records. Relevant if the consumer is a registry that should receive eligibility verdicts but not the underlying variant data.

GDPR Article 46 adequacy requirements — for cross-border data sharing when the external organisation is in a jurisdiction without an EU adequacy decision. Determines whether a Data Transfer Agreement or Standard Contractual Clauses are required.

GA4GH Data Access Framework — the standard for controlled access to genomic data in research settings. Relevant if a genomic product is shared with a research consortium that requires GA4GH-compliant access control.

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when an external consumer is identified.*