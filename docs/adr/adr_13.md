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

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the first external consumer accesses a data product.*