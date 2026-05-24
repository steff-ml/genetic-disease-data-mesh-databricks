# ADR-13: Match Product Interface Type

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** Gold layer being built
**Blocks:** Nothing in the build sequence — Gold layer can be built before this is decided

---

## Knowledge Required

Databricks SQL endpoint documentation — setup, authentication (personal access token, OAuth), query patterns. The SQL endpoint is the minimum viable interface: any SQL-capable tool can query it.

Databricks Model Serving documentation — for exposing match logic as a REST API. Relevant when a clinical application needs to query eligibility for a single patient in real time rather than running batch queries.

Delta Sharing documentation — the open protocol for sharing Delta tables with external organisations without data copying. Relevant when a patient registry or research consortium needs access without being a Databricks customer.

Consumer tool landscape: biostatisticians use SAS or R; data scientists use Python; clinical coordinators use web applications that call REST APIs; external registries need Delta Sharing or API. The interface decision is driven by the first external consumer's tooling, not by internal preference.

---

## Partial Decision

SQL endpoint for prototype demonstration. REST API documented as the target for clinical integration, to be designed when a specific external consumer is identified with a defined tool requirement.

---

## References

**Books**
- FDE ch9: data product interface patterns and consumer-facing API design
- Dehghani, *Data Mesh* ch5: interface as part of the data product contract

**Databricks documentation**
- [Databricks SQL endpoint](https://docs.databricks.com/en/sql/get-started/index.html) — setup, authentication, query patterns; the primary interface for the prototype match product
- [Delta Sharing](https://docs.databricks.com/en/delta-sharing/index.html) — the external sharing interface for ADR-17; worth reading now to understand the upgrade path from SQL endpoint to external sharing
- [Model Serving REST API](https://docs.databricks.com/en/machine-learning/model-serving/index.html) — the target interface for clinical application integration requiring real-time single-patient queries

---

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the first external consumer accesses a data product.*