# ADR-04: Data Product Definition

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** ADR-01 (data as a product is one of the four mesh principles), ADR-03 (domain boundaries define who owns each product)
**Blocks:** ADR-08 (versioning strategy), ADR-12 (contract enforcement mechanism), ADR-13 (interface type)

---

## Knowledge Required

Dehghani chapter 4 — data product as a first-class architectural concept
FAIR principles — findable, accessible, interoperable, reusable as minimum properties
DCAT vocabulary (W3C) — standard for data product metadata records
Consumer context: what does a match product consumer need to know before using the product?

Minimum viable definition for this project: A data product has an owner, a schema contract, a semantic version, a documented consumer, and a discoverability entry in Unity Catalog.

---

## References

**Books**
- Dehghani, *Data Mesh* ch5, ch9: data product as a first-class architectural concept and its minimum viable properties
- FDE ch9: data product delivery patterns

**Databricks documentation**
- [Unity Catalog tags and business metadata](https://docs.databricks.com/en/data-governance/unity-catalog/tags.html) — how discoverability is implemented; relevant to the findable and understandable qualities from DM ch5
- [Unity Catalog automated lineage](https://docs.databricks.com/en/data-governance/unity-catalog/data-lineage.html) — relevant to the trustworthy quality; traceability from source to product

**Standards**
- [Bitol Open Data Contract Standard](https://bitol.io) — the open, vendor-neutral YAML format for machine-readable data product contracts; covers schema, SLA, quality terms, consumer declarations, and data classification

---

## Decision

### Context

Data mesh requires data products to be first-class architectural concepts, not just tables. A data product is defined by its interface, its quality guarantees, and its discoverability, not by the pipeline that produces it. Without a shared definition of what a data product is, domains produce incompatible product structures that cannot be reliably consumed or validated.

This project demonstrates how to build a data mesh properly using open standards. The contract format must be portable outside Databricks, machine-readable, and version-controllable.

### Decision

A data product in this project must satisfy all six of the following criteria:

**1. Owner**: a named domain, declared in the contract. A product without an owner cannot have accountability for quality or breaking changes.

**2. Schema contract**: a [Bitol Open Data Contract Standard](https://bitol.io) YAML file committed to the repository under `docs/contracts/` alongside the pipeline code that produces the product. The contract declares:
- Schema: column names, types, nullability, descriptions
- Quality terms: minimum completeness, freshness SLA
- Semantic version (SemVer)
- Consumer declarations: named downstream consumers

**3. Semantic version**: SemVer applied to the contract. Adding a nullable column is a minor change. Removing a column, changing a type, or changing nullability on a non-null column is a breaking change that increments the major version. Consumers declare which major version they depend on in their pipeline code.

**4. Documented consumer**: at least one downstream consumer declared in the contract by name. A table with no declared consumer is an internal table, not a data product.

**5. Discoverability**: the Unity Catalog table has a populated description, an `owner` tag (domain name), and a `contract_version` tag matching the Bitol YAML file version. This makes the product findable without reading the pipeline code.

**6. Quality SLA**: at least one declared quality expectation in the Bitol contract — completeness (key fields are non-null above a declared threshold), freshness (table updated within a defined window), or validity (values drawn from a controlled vocabulary). The DLT pipeline enforces this expectation at write time via `@dlt.expect_or_quarantine`.

**Scope**: this definition applies to all Gold-layer tables consumed cross-domain or by an external consumer. Internal Silver and Bronze tables are governed by medallion layer invariants (ADR-09), not by this definition. They are not data products.

### Alternatives considered

**Unity Catalog schema + tags only**: simpler — the contract is platform metadata, not code. Cannot be version-controlled in Git, cannot be validated in CI, and is not portable outside Databricks. Insufficient for demonstrating open, production-grade data product design.

**DCAT (W3C vocabulary)**: the standard for catalogue-level dataset metadata. Too abstract for the operational quality and SLA terms this project needs. DCAT describes datasets as findable resources; Bitol describes data products with enforceable operational guarantees. The two standards are complementary, not substitutes.

**Informal README documentation**: cannot be validated programmatically. A contract that exists only in prose is not machine-readable and cannot enforce compliance. Schema drift between the declared contract and the actual table cannot be detected in CI.

**dbt contracts**: applicable only if dbt is the transformation layer. This project uses DLT; dbt contracts are not portable across the stack.

### Rationale

- Bitol is open and vendor-neutral: the contract YAML is readable outside Databricks by any system that can parse YAML. This is the open standard requirement.
- Bitol is version-controllable: YAML files committed to Git gain the full history, review, and diff capabilities of any code asset.
- Bitol is comprehensive: schema, SLA, quality terms, data classification, and consumer declarations are declared in one place — not split across Unity Catalog tags, README files, and pipeline comments.
- Schema contract validation in CI (ADR-23) requires a machine-readable contract format. Bitol provides this.

### Consequences

- A `docs/contracts/` directory holds one Bitol YAML file per published Gold data product
- CI validates that the Gold table schema matches its declared contract on every pipeline run (ADR-23)
- Consumer pipelines reference the contract version explicitly; a major version increment requires consumer pipelines to be updated before consuming the new version
- The Reference domain's curated ontology tables are also data products and require Bitol contracts, even though their consumers are internal to the project

### Compliance implications

- A machine-readable, version-controlled schema contract satisfies the requirement for documented data interfaces under ICH E6(R3) section 5.5 on data management documentation
- The owner declaration in the contract satisfies the ALCOA+ Attributable requirement for the data product layer
- Schema versioning in the contract provides the audit trail for breaking changes required before any cross-domain schema change is published

### Assumptions

- Bitol YAML is used at the file level; no additional tooling (a data contract server, a Bitol registry) is required for the prototype
- Contract validation in CI uses schema conformance checking; full Bitol toolchain deployment is deferred

### Review trigger

Before the first external consumer accesses a data product, validate that the Bitol contract format and SemVer scheme are sufficient for that consumer's integration requirements.
