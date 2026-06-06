# ADR-01: Data Mesh Paradigm

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** Nothing — this is the root architectural decision
**Blocks:** ADR-02, ADR-03, and all downstream decisions

---

## Knowledge Required

Dehghani, Data Mesh (O'Reilly, 2022) — chapters 1–3: the four principles and the problems they solve
FDA Data Integrity Guidance (2018) — the failure modes in regulated contexts a mesh must resolve
Wilkinson et al., FAIR Data Principles (2016) — the scientific data sharing failures that motivate mesh in research
Understanding of alternative paradigms: centralised lakehouse, federated databases, per-study databases

---

## References

**Books**
- Dehghani, *Data Mesh* (O'Reilly, 2022) — ch1–3: the four principles and the problems they solve
- DDA ch2–3: data architecture patterns and the forces driving decentralisation

**Databricks documentation**
None directly — this is a paradigm decision, not a platform decision.

**Primary sources**
- FDA Data Integrity Guidance (2018) — failure modes in regulated contexts a mesh must resolve
- Wilkinson et al., FAIR Data Principles (2016, *Scientific Data*) — scientific data sharing failures that motivate mesh in research

---

## Decision

### Context

The DMD data problem is inherently multi-domain. Mutation data lives in variant registries (LOVD, ClinVar, TREAT-NMD) maintained by the bioinformatics community. Clinical trial data lives in ClinicalTrials.gov and national trial registries maintained by regulators and sponsors. Reference ontologies (HPO, HGNC, Ensembl) are maintained by independent international consortia. These sources have different update cadences, different schemas, and are consumed by different analytical questions.

This project is built by a single person but is deliberately designed as a model for a multi-team, multi-institutional clinical research platform. The architectural decisions are made as they would be made in that multi-team context, not as they would be optimised for a single-person workflow. The goal is a demonstrable architecture that a research organisation or consulting engagement could adopt directly.

### Decision

Adopt data mesh as the architectural paradigm, implementing all four principles:

1. **Domain ownership**: data is owned by the domain closest to its source and analytical use. Genomic data is owned by the Discovery domain; trial eligibility data is owned by the Clinical domain; shared ontologies are owned by the Reference domain.
2. **Data as a product**: each domain publishes Gold-layer data products with defined contracts, quality guarantees, and semantic versioning. Internal tables are not products.
3. **Self-serve infrastructure**: the platform (Databricks + Unity Catalog) provides the governance, compute, and storage primitives that domains depend on without requiring domain teams to manage infrastructure.
4. **Federated computational governance**: global standards (Bitol contract format, SemVer, conflict resolution rules) are defined centrally and applied locally by each domain.

### Alternatives considered

**Centralised lakehouse**: all data in one domain, one team responsible for all pipelines. Technically simpler for a single person. Does not model the multi-team, multi-institutional reality of clinical research data. Produces a single point of governance failure and no domain accountability for data quality. Does not satisfy the FAIR interoperability requirement: a centralised schema is not inherently portable across institutions.

**Per-study databases**: the pre-existing anti-pattern in clinical research. Each study produces a separate database; cross-study questions require bespoke integration. Cannot answer the primary analytical question (which patients across the mutation registry match which open trials). Violates FAIR and FDA data integrity requirements — data silos with no lineage, no shared semantics, no defined ownership outside the study team.

**Federated query layer** (e.g., Trino): query source systems directly without ingestion. Avoids storage and pipeline costs. Does not produce governed, quality-assured, versioned data products. Source systems do not guarantee schema stability, access continuity, or response time — none of which are acceptable for a clinical data product. Audit trail and lineage are not available across federated heterogeneous sources.

### Rationale

- Domain ownership matches the actual responsibility structure of DMD data: variant registries are a genomics concern, trial eligibility is a clinical concern, shared ontologies are a platform infrastructure concern. Ownership follows the domain that understands the data and is accountable for its quality.
- Data as a product enforces a quality contract between producer and consumer that neither ad-hoc sharing nor a centralised pipeline enforces. In a clinical context, a downstream consumer must be able to trust a data product without inspecting the pipeline that produced it.
- The FAIR data principles are structurally satisfied by data mesh: Findable through Unity Catalog discoverability, Accessible through SQL endpoints, Interoperable through open standards (HGVS, HPO, OMOP), Reusable through versioned contracts.
- FDA Data Integrity Guidance failure modes — data without clear provenance, data modified without an audit trail, data without a defined responsible party — are addressed by the ownership and product principles.

### Consequences

- Three domains are defined: Discovery, Clinical, and Reference (ADR-03)
- Cross-domain data sharing happens only through published Gold-layer data products with Bitol contracts — never through direct table reads across domain catalog boundaries
- Every cross-domain Gold product requires a schema contract, semantic versioning, and a quality SLA (ADR-04, ADR-08)
- The single-person implementation simulates multi-team boundaries through Unity Catalog catalog-level isolation, identical to what a multi-team deployment would use

### Compliance implications

- The ownership principle aligns with FDA data integrity requirements: every data element has a named owner, a defined pipeline, and an audit trail
- ALCOA+ data integrity principles are structurally enforced: Attributable through domain ownership declarations, Enduring through Delta Lake time travel, Original through Bronze immutability (ADR-09)
- FAIR principles are enforced structurally rather than aspirationally

### Assumptions

- The project is built by a single person but designed as a model for a multi-team organisation. Domain boundaries are drawn as they would be in a multi-team context.
- Unity Catalog is available and provides the physical implementation of domain isolation (confirmed in ADR-02)
- Exploration notebooks are intentionally outside this governance framework and are not subject to data mesh production standards

### Review trigger

If the project is adopted by a second person or team, validate that the domain boundaries and ownership model hold under real multi-team conditions before extending the architecture.
