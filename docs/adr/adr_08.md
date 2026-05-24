# ADR-08: Versioning and Lifecycle Strategy

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-03 (data product definition)
**Blocks:** External publication of any Gold product

---

## Knowledge Required

Semantic versioning specification (semver.org) — major/minor/patch rules; the vocabulary for communicating breaking versus non-breaking changes to consumers.

Understanding of what "breaking" means for specific consumers: schema column removal or rename, data type change, and computability class removal break downstream queries and matching logic. Column addition, constraint tightening, and new computability class additions do not.

Delta Lake table properties documentation — how to store version metadata as a table property so consumers can read it programmatically without inspecting the schema.

CDISC versioning patterns — how CDISC manages controlled terminology versions, as a domain-specific precedent for biomedical data products with downstream regulatory consumers.

---

## Partial Decision (to be completed before first Gold product is published externally)

Semantic versioning. Breaking change defined as: schema column removal or rename, data type change, computability class removal. Non-breaking: column addition, constraint tightening, new computability class.

---

## References

**Books**
- DDIA ch4: schema evolution and the costs of breaking changes for downstream consumers
- Dehghani, *Data Mesh* ch5: versioning as part of the data product contract
- FDE ch2: data lifecycle and retention patterns

**Databricks documentation**
- [Delta Lake table history and time travel](https://docs.databricks.com/en/delta/history.html) — the technical foundation for the version audit trail; how versions are recorded and how historical states are queried
- [Delta Lake table properties](https://docs.databricks.com/en/delta/table-properties.html) — how to store version metadata as a table property as part of the versioning implementation

---

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the first Gold product is published.*