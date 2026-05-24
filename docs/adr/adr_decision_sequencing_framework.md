# Architecture Decision Sequencing Framework
Duchenne Rare Disease Data Mesh — Open Source

Back to [README.md](../../README.md)

## Purpose
This document governs when architectural decisions are made, what information is required to make them well, and what triggers deferred decisions. It sits above individual ADRs and answers a question they do not: in what order should decisions be made, and why.
Every decision in this framework is classified on three axes before it is made:
- **Reversibility** : How costly is it to change this decision later? (Structural, Costly, Adjustable, Throwaway)
- **Dependency direction**: what does this decision block, and what must precede it?  (Blocking, Dependent, Independent)
- **Information Readiness**: when do you have enough information to decide well? (Decidable now, Decidable at milestone, Decidable on trigger, Undecidable yet)
- **Status** (Done, Draft, Not started)

Decisions are made following the last responsible moment principle: Defer decisions until the moment when further deferral becomes costly. A decision made early is made with less information. The cost of early decisions is not just the risk of being wrong; it is the foreclosure of options not yet visible.

## ADR Decision Inventory

**Audience legend:** `Architect` — cross-cutting structure and paradigm choices; `Domain` — scientific and data source decisions owned by domain scientists; `Engineer` — storage, pipeline, and serving decisions; `Governance` — compliance, regulatory, and access control decisions.

---

### AI Governance

How artificial intelligence is used — both in building this project and in governing its production behaviour.

| Decision | Description | Reversibility | Dependency | Information Readiness | Decision trigger | Revisit trigger | Status | Audience |
|----------|-------------|---------------|------------|-----------------------|------------------|-----------------|--------|----------|
| [ADR-00](adr_00.md) | Use of AI in project development | Adjustable | Independent | Decidable now | Before any building | Changes in AI services (quality competitor, throttling) or in the regulatory framework | Done | Governance |
| [ADR-20](adr_20.md) | GenAI extraction model governance | Costly. Prompt and model changes affect extraction quality and must be validated before deployment; audit trail obligations make ad-hoc changes costly. | Blocks: Production extraction pipeline deployment. Depends on: ADR-10 (scope defines what the model must do; governance defines how it does it safely). | Decidable before the extraction pipeline goes to production. | Before extraction pipeline build. | Model deprecation by provider, significant change in extraction quality, or new regulatory requirement for AI in clinical data pipelines. | Draft | Governance |

---

### Architecture

Paradigm, platform, and structural decisions that shape everything downstream. Made once; changed only under extreme pressure.

| Decision | Description | Reversibility | Dependency | Information Readiness | Decision trigger | Revisit trigger | Status | Audience |
|----------|-------------|---------------|------------|-----------------------|------------------|-----------------|--------|----------|
| [ADR-01](adr_01.md) | Adopt data mesh as architectural paradigm | Structural | Blocks all other decisions | Decidable with published evidence | Before any building | Fundamental change in organisational structure that makes domain ownership unworkable, or emergence of a paradigm that resolves the same forces more effectively. | Draft | Architect |
| [ADR-02](adr_02.md) | Adopt Databricks as the platform | Structural | Blocks: Platform topology, governance model, all layer design decisions. Depends on: ADR-01. | Decidable with published evidence and platform documentation. | Before any building | Unity Catalog governance gaps identified for a specific compliance requirement, or a consumer organisation mandating a different platform. | Draft | Architect |
| [ADR-03](adr_03.md) | Domain boundary principle: what defines a domain | Structural | Blocks: ADR-04, ADR-05, ADR-06, ADR-19. Depends on: ADR-01, ADR-02. | Decidable now. For this project the domain structure is derivable from the data sources and the consumer question. | Before any building | Expansion beyond Duchenne to a second disease area, or addition of a genuinely independent data consumer requiring a separate domain. | Draft | Architect |
| [ADR-05](adr_05.md) | Domain ownership of the cross-domain products | Structural. Ownership determines write access, pipeline authorisation, and consumer contract accountability. | Blocks: All pipeline design. Depends on: ADR-03, ADR-04. | Decidable now. | Before any building | Expansion to multiple disease areas, a second independent trial domain consumer, or matching logic becoming an ML model requiring its own validation lifecycle. | Draft | Architect |
| [ADR-15](adr_15.md) | Separate matching domain | Structural. | Blocks: Domain topology. Depends on: ADR-03. | Decidable when trigger conditions are met. | Expansion to second disease area, second independent trial domain consumer, or matching logic becoming an ML model requiring its own validation lifecycle. | — | Deferred | Architect |

---

### Data Product Design

What a data product is, how it is versioned, how its contracts are enforced, and how consumers access it.

| Decision | Description | Reversibility | Dependency | Information Readiness | Decision trigger | Revisit trigger | Status | Audience |
|----------|-------------|---------------|------------|-----------------------|------------------|-----------------|--------|----------|
| [ADR-04](adr_04.md) | Definition of a data product | Structural once external consumers exist. Adjustable before that. | Blocks: ADR-08 (versioning), ADR-12 (cross-domain contracts), ADR-13 (interface design). Depends on: ADR-03. | Decidable now at minimum viable level. Full elaboration deferred until a second product exists to compare against. | Before any building | A second data product with meaningfully different characteristics exposes gaps in the definition. | Draft | Architect |
| [ADR-08](adr_08.md) | Versioning and lifecycle strategy | Structural once external consumers exist. Adjustable before that. | Blocks: External publication of any Gold product. Depends on: ADR-04. | Decidable now in principle. Specific breaking-change rules decidable after the first schema is designed. | Before first Gold product is published externally. | A consumer breaks silently on a non-breaking change, indicating the breaking-change definition is wrong. | Draft | Engineer |
| [ADR-12](adr_12.md) | Cross-domain contract enforcement mechanism | Adjustable. The mechanism can change without changing the contract terms, provided the terms remain stable. | Blocks: External publication of genomic domain products. Depends on: ADR-03, ADR-08. | Decidable before the first cross-domain product is published. Not blocking current build. | Before first cross-domain product is published. | A consumer organisation mandates a different enforcement mechanism, or Unity Catalog introduces native contract enforcement. | Draft | Engineer |
| [ADR-13](adr_13.md) | Match product interface type | Adjustable. Interfaces can be added without removing existing ones. | Blocks: Nothing in the build sequence. Depends on: Gold layer being built. | SQL endpoint decidable now as prototype interface. REST API design deferred until a specific external consumer is identified. | Before first external consumer accesses a data product. | A specific external consumer is identified with a tool requirement that cannot be met by the SQL endpoint. | Draft | Engineer |
| [ADR-17](adr_17.md) | External sharing model | Adjustable. | Depends on: Gold products built. | Decidable when an external consumer is identified. Requires: Delta Sharing protocol, data clean room patterns, GDPR Article 46, GA4GH Data Access Framework. | An external organisation wants to consume products without direct platform access. | — | Deferred | Governance |

---

### Logical Data Design

How data is modelled across Silver and Gold, which sources are canonical, how eligibility criteria are represented and classified, and how genetic variants are encoded.

| Decision | Description | Reversibility | Dependency | Information Readiness | Decision trigger | Revisit trigger | Status | Audience |
|----------|-------------|---------------|------------|-----------------------|------------------|-----------------|--------|----------|
| [ADR-19](adr_19.md) | Silver and Gold layer data modelling approach | Costly. The Silver schema is the foundation all downstream Gold products build on; changing it requires reprocessing and consumer migration. | Blocks: ADR-07, ADR-09 (Silver), ADR-10, ADR-11. Depends on: ADR-02 (Databricks), ADR-03 (domain boundaries). | Decidable now in principle. Specific table design choices decidable before Silver build. | Before Silver layer build. | Addition of a second disease domain with substantially different data characteristics, or persistent Gold query performance issues that require structural change. | Draft | Architect |
| [ADR-06](adr_06.md) | Canonical data sources | Costly. Switching sources requires Bronze reprocessing and potentially Silver schema changes. | Blocks: Bronze ingestion design. Depends on: ADR-03. | Decidable now for the prototype. | Bronze ingestion build. | Need for European trial coverage (adds EudraCT), patient-level registry data (adds TREAT-NMD), or genomic variant sources. | Draft | Domain |
| [ADR-07](adr_07.md) | Eligibility criteria representation standard | Costly. Changing the representation requires reprocessing all Silver records and updating all downstream matching logic. | Blocks: Silver schema design, ADR-10, ADR-11. Depends on: ADR-06, ADR-19. | Decidable after reading 20–30 actual DMD trial eligibility texts from ClinicalTrials.gov. | Silver layer build. | Addition of patient variant data to the genomic domain (triggers HGVS representation decision). | Draft | Domain |
| [ADR-10](adr_10.md) | GenAI extraction scope | Adjustable. Expanding or contracting LLM scope affects the pipeline but not the output schema contract. | Blocks: Extraction pipeline design, ADR-20 (model governance). Depends on: ADR-06, ADR-07, ADR-09 Silver. | Principle decidable now. Boundary cases decidable after reading 20–30 DMD eligibility texts. | Before extraction pipeline build. | Approved therapy reference tables change, or LLM accuracy demonstrably exceeds deterministic approach for currently-deterministic criteria. | Draft | Domain |
| [ADR-11](adr_11.md) | Computability classification schema | Partially reversible. Adding classes is safe. Removing or merging classes breaks downstream matching logic. | Blocks: Gold matching logic design. Depends on: ADR-07, ADR-10. | Three-class schema decidable now. Population of criterion types into classes decidable after reading DMD eligibility texts. | Before Silver layer build. | A criterion type is encountered that cannot be represented by the three-class schema. | Draft | Domain |
| [ADR-14](adr_14.md) | HGVS representation for patient variants | Costly. Switching representation requires Bronze reprocessing and potentially Silver schema changes. | Blocks: Patient variant ingestion design. | Decidable when patient variant data is added. Requires: HGVS spec, GA4GH Phenopackets, LOVD schema, VCF format, hgvs Python library. | When patient variant data is added to the genomic domain. | — | Deferred | Domain |

---

### Physical Design

How pipelines are implemented, how data quality is enforced and monitored, how the system is tested, and how storage is optimised.

| Decision | Description | Reversibility | Dependency | Information Readiness | Decision trigger | Revisit trigger | Status | Audience |
|----------|-------------|---------------|------------|-----------------------|------------------|-----------------|--------|----------|
| [ADR-09](adr_09.md) | Medallion layer invariants | Adjustable for tightening. Loosening Bronze invariants is harder because it undermines the audit story. | Blocks: ADR-21 (pipeline framework), ADR-22 (quality monitoring). Depends on: ADR-01, ADR-02. Silver invariants also depend on ADR-06. | Bronze invariants decidable now. Silver invariants decidable after first Bronze ingestion. | Before Bronze build (Bronze); before Silver build (Silver). | Silver invariants loosened in a way that undermines the audit story. | Draft | Engineer |
| [ADR-21](adr_21.md) | Pipeline framework: DLT vs Spark Jobs | Adjustable. Pipelines can be rewritten without changing the data contract. | Blocks: Pipeline implementation, ADR-22 (quality monitoring), ADR-23 (test strategy). Depends on: ADR-02, ADR-09. | Decidable now. | Before Bronze build. | DLT limitations block a specific pipeline requirement, or a significant cost difference is observed in production. | Draft | Engineer |
| [ADR-22](adr_22.md) | Data quality monitoring framework | Adjustable. The monitoring surface can change without changing the underlying quality rules. | Blocks: Quality SLA enforcement. Depends on: ADR-09 (invariants define the rules), ADR-21 (framework shapes how rules are expressed). | Decidable before Silver build. | Before Silver layer build. | Quality SLA breach rate exceeds acceptable threshold, or a consumer requires a quality certification the current monitoring cannot produce. | Draft | Engineer |
| [ADR-23](adr_23.md) | Test strategy | Adjustable. Coverage can be extended without changing the system under test. | Blocks: CI/CD pipeline design. Depends on: ADR-21 (framework determines testability). | Decidable before first pipeline is built. | Before Bronze build. | Pipeline framework changes in a way that invalidates the existing test approach. | Draft | Engineer |
| [ADR-16](adr_16.md) | Partitioning and Z-order optimisation | Throwaway. | Independent. | Requires real query logs and data volume actuals — not decidable on hypothetical usage. | Match query latency on full trial catalogue exceeds 30 seconds. | — | Deferred | Engineer |

---

### Compliance & Regulatory

Platform-level regulatory obligations and validation frameworks.

| Decision | Description | Reversibility | Dependency | Information Readiness | Decision trigger | Revisit trigger | Status | Audience |
|----------|-------------|---------------|------------|-----------------------|------------------|-----------------|--------|----------|
| [ADR-18](adr_18.md) | Full GxP validation framework | Costly. | Depends on: Platform build complete. | Decidable when a regulated entity adopts the platform. Requires: ICH E6(R3), FDA 21 CFR Part 11, GAMP 5. | A regulated entity adopts the platform for use in a regulated context. | — | Deferred | Governance |



## ADR Dependency Graph

ADR-00 is independent and runs before any building.

The critical path for the first data product is:

```
ADR-00 (AI in development — independent)
ADR-01 → ADR-02 → ADR-03 → ADR-04 → ADR-05 → all pipeline design
                           │
                           ├── ADR-06 ──────────────────── Bronze ingestion build
                           │
                           ├── ADR-19 (data modelling approach)
                           │     ├── ADR-07 (eligibility representation) → read 20–30 DMD eligibility texts
                           │     │         ├── ADR-10 (GenAI scope) → ADR-20 (model governance) → extraction pipeline build
                           │     │         └── ADR-11 (computability classification) → Silver layer build
                           │     │                                                           └── Gold layer build
                           │     │                                                                 └── ADR-13 → expose interface
                           │     ├── ADR-09 (Bronze invariants) → ADR-21 (pipeline framework)
                           │     │         │                             ├── ADR-22 (quality monitoring) → Silver layer build
                           │     │         │                             └── ADR-23 (test strategy) → CI/CD build
                           │     │         └── ADR-09 (Silver invariants) → Silver layer build
                           │     └── ADR-08 ─────────────────────────── publish first Gold product externally
                           │
                           └── ADR-12 ─────────────────────────────── publish first cross-domain product
```

Deferred decisions (not on the critical path — named triggers only):

- ADR-14 — patient variant data added to the genomic domain
- ADR-15 — expansion to a second disease area or matching logic becomes an ML model
- ADR-16 — match query latency exceeds 30 seconds
- ADR-17 — external organisation requests access without direct platform access
- ADR-18 — regulated entity adopts the platform

Everything not on the critical path either runs in parallel or is explicitly deferred with a named trigger.



