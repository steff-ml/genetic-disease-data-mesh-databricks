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

## References

**Books**
- Dehghani, *Data Mesh* ch7: federated computational governance — how cross-domain and cross-organisational data sharing is governed without centralised control; the conceptual basis for the external sharing model choice
- FDE ch9: data product interface patterns — external-facing interface design for data products shared across organisational boundaries

**Databricks documentation**
- [Delta Sharing](https://docs.databricks.com/en/delta-sharing/index.html) — the open protocol for sharing Delta tables across organisational boundaries without data copying; audit logs, recipient management, and the consumer-side experience without requiring a Databricks subscription
- [Unity Catalog external sharing](https://docs.databricks.com/en/data-governance/unity-catalog/index.html) — how Unity Catalog manages access grants to external recipients; the governance layer above the Delta Sharing protocol
- [Databricks Clean Rooms](https://docs.databricks.com/en/clean-rooms/index.html) — the mechanism for sharing derived analytics without exposing raw underlying records; relevant when a registry consumer should receive eligibility verdicts but not the patient-level variant data

**Regulatory and standards references**
- GDPR Article 46 — adequacy requirements for cross-border personal data transfers; determines whether Standard Contractual Clauses or a Data Transfer Agreement are needed when sharing with non-EEA organisations
- [GA4GH Framework for Responsible Sharing of Genomic and Health-Related Data](https://www.ga4gh.org/genomic-data-toolkit/data-security-toolkit/framework-for-responsible-sharing-of-genomic-and-health-related-data/) — the standard for controlled access to genomic research data; relevant if a research consortium is the external consumer and requires GA4GH-compliant access control

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when an external consumer is identified.*