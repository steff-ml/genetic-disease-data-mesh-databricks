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

| Decision | Description | Reversibility | Dependency | Information Readiness | Status |
|----------|-------------|---------------|------------|-----------------------|--------|
| [ADR-00](adr_00.md) | The use of AI inside this project | Adjustable | Independent | Decidable now| Done|



The Decision Inventory

Tier 0 — Paradigm and Platform
Structural decisions made once. They constrain everything that follows.

D-00: Adopt data mesh as the architectural paradigm
Reversibility: Structural. The entire downstream architecture assumes domain ownership, data products, and federated governance.
Blocks: All other decisions.
Depends on: Nothing architectural.
Information readiness: Decidable with published evidence.
Knowledge required:

Dehghani, Data Mesh (O'Reilly, 2022) — chapters 1–3: the four principles and the problems they solve
FDA Data Integrity Guidance (2018) — the failure modes in regulated contexts a mesh must resolve
Wilkinson et al., FAIR Data Principles (2016) — the scientific data sharing failures that motivate mesh in research
Understanding of alternative paradigms: centralised lakehouse, federated databases, per-study databases

Trigger for revisiting: Fundamental change in organisational structure that makes domain ownership unworkable, or emergence of a paradigm that resolves the same forces more effectively.
Write ADR before: Any build activity.

D-01: Adopt Databricks as the platform
Reversibility: Structural. Unity Catalog topology, Delta Lake properties, and DLT pipeline design are Databricks-specific. Migration requires rebuilding the infrastructure layer.
Blocks: Platform topology, governance model, all layer design decisions.
Depends on: D-00.
Information readiness: Decidable with published evidence and platform documentation.
Knowledge required:

Databricks Unity Catalog documentation — governance capabilities, fine-grained access control
Delta Lake documentation — ACID properties, time travel, deletion vectors, the GxP audit story
Databricks Life Sciences reference architecture
Comparative knowledge of alternatives: Snowflake governance model, AWS Lake Formation, Azure Synapse
Understanding of GxP audit trail requirements: what the platform must provide technically

Trigger for revisiting: Unity Catalog governance gaps identified for a specific compliance requirement, or a consumer organisation mandating a different platform.
Write ADR before: Any build activity.

Tier 1 — Structural Foundation
Structural or costly decisions that block all build activity. Decided before writing any code.

D-02: Domain boundary principle — what defines a domain
Reversibility: Structural. Domain boundaries determine Unity Catalog topology, ownership assignments, pipeline dependencies, and data product contracts. Redrawing boundaries invalidates all of these.
Blocks: D-03, D-04, D-05, D-06.
Depends on: D-00, D-01.
Information readiness: Decidable now. For this project the domain structure is derivable from the data sources and the consumer question.
Knowledge required:

Dehghani chapters 3–4 — domain-oriented ownership and what constitutes a domain boundary
Understanding of the specific data sources: ClinicalTrials.gov (trial domain), variant databases (genomic domain)
Understanding of the consumer question: who asks "which patients match which trials" — this identifies the owning domain
Anti-pattern knowledge: study-per-database silo, distributed monolith

Decision for this project: Two domains — genomic domain (patient variant profiles) and clinical trials domain (trial eligibility specifications and match products). Match product owned by clinical trials domain.
Trigger for revisiting: Expansion beyond Duchenne to a second disease area, or addition of a genuinely independent data consumer requiring a separate domain.
Write ADR before: Any build activity.

D-03: Definition of a data product
Reversibility: Structural once external consumers exist. Adjustable before that.
Blocks: D-07 (versioning), D-10 (interface design), D-11 (cross-domain contracts).
Depends on: D-02.
Information readiness: Decidable now at minimum viable level. Full elaboration deferred until a second product exists to compare against.
Knowledge required:

Dehghani chapter 4 — data product as a first-class architectural concept
FAIR principles — findable, accessible, interoperable, reusable as minimum properties
DCAT vocabulary (W3C) — standard for data product metadata records
Consumer context: what does a match product consumer need to know before using the product?

Minimum viable definition for this project: A data product has an owner, a schema contract, a semantic version, a documented consumer, and a discoverability entry in Unity Catalog.
Trigger for revisiting: A second data product with meaningfully different characteristics exposes gaps in the definition.
Write ADR before: Any build activity.

D-04: Domain ownership of the match product
Reversibility: Structural. Ownership determines write access, pipeline authorisation, and consumer contract accountability.
Blocks: All pipeline design.
Depends on: D-02, D-03.
Information readiness: Decidable now.
Knowledge required:

The consumer question test: whoever is accountable for answering the business question owns the product that answers it
Understanding of cross-domain product patterns: consuming domain produces a Gold product from upstream published products
Dehghani on domain ownership accountability

Decision for this project: Clinical trials domain owns the match product. It consumes the genomic domain's published patient variant product. No separate matching domain at current scope.
Trigger for revisiting: Expansion to multiple disease areas, a second independent trial domain consumer, or matching logic becoming an ML model requiring its own validation lifecycle.
Write ADR before: Any build activity.

D-05: Canonical trial data source
Reversibility: Costly. Switching sources requires Bronze reprocessing and potentially Silver schema changes if the new source has a different structure.
Blocks: Bronze ingestion design.
Depends on: D-02.
Information readiness: Decidable now for the prototype.
Knowledge required:

ClinicalTrials.gov API documentation — available fields, data structure, update frequency
TREAT-NMD registry — what it adds that ClinicalTrials.gov lacks (deeper phenotypic data, patient-level registry data)
EudraCT — European trial coverage gaps in ClinicalTrials.gov
Limitations documentation: what ClinicalTrials.gov does not contain that a production system would need

Decision for this project: ClinicalTrials.gov as sole source for the prototype.
Trigger for revisiting: Need for European trial coverage (adds EudraCT), need for patient-level registry data (adds TREAT-NMD).
Write ADR before: Bronze ingestion build.

D-06: Eligibility criteria representation standard
Reversibility: Costly. Changing the representation requires reprocessing all Silver records and updating all downstream matching logic.
Blocks: Silver schema design, D-08 (computability classification), D-09 (GenAI extraction scope).
Depends on: D-02, D-05.
Information readiness: Decidable after reading 20–30 actual DMD trial eligibility texts from ClinicalTrials.gov. This is a one-hour data exploration task, not a weeks-long reading programme.
Knowledge required:

HPO (Human Phenotype Ontology) documentation — what phenotypic concepts it covers, how terms are structured
20–30 DMD trial eligibility criteria texts — what categories of criteria actually appear in practice
Understanding of the Duchenne mutation landscape: exon deletions, duplications, point mutations, reading frame rule — needed to design the mutation class enum
GA4GH Phenopackets specification — the standard for patient phenotype plus genetic data, relevant for the patient-side upgrade path

Decision for this project: HPO for phenotypic criteria, mutation class enum (deletion, duplication, nonsense, other) plus exon amenability flag for genetic criteria. HGVS deferred until patient variant data is added.
Trigger for revisiting: Addition of patient variant data to the genomic domain (triggers D-13).
Write ADR before: Silver layer build.

Tier 2 — Layer Design
Costly to structural decisions. Decided before building each specific layer or component.

D-07: Versioning and lifecycle strategy
Reversibility: Structural once external consumers exist. Adjustable before that.
Blocks: External publication of any Gold product.
Depends on: D-03.
Information readiness: Principle decidable now. Specific breaking change rules decidable after the first schema is designed — a concrete schema is needed to reason about what constitutes a breaking change.
Knowledge required:

Semantic versioning specification (semver.org) — major/minor/patch rules
Understanding of what breaking means for specific consumers: schema change, controlled terminology update, population change
Delta Lake table properties documentation — how to store version metadata
CDISC versioning patterns — how CDISC manages controlled terminology versions, as a domain-specific precedent

Decision for this project: Semantic versioning. Breaking change defined as: schema column removal or rename, data type change, computability class removal. Non-breaking: column addition, constraint tightening, new computability class.
Write ADR before: First Gold product is published externally.

D-08: Medallion layer invariants
Reversibility: Adjustable for tightening. Loosening Bronze invariants is harder because it undermines the audit story.
Blocks: Quality constraint design, audit trail approach.
Depends on: D-01, D-02. Bronze invariants depend on nothing else. Silver invariants depend on D-06.
Information readiness: Bronze invariants decidable now. Silver invariants decidable after first Bronze ingestion — actual data quality must be seen before realistic conformance constraints can be written.
Knowledge required:

FDA Data Integrity Guidance — what immutability and audit trail mean in a regulated context, defines the Bronze invariant
ICH E6(R3) sections 4–5 — data governance obligations that translate to layer guarantees
Delta Lake documentation — time travel, transaction log, deletion vectors, the technical mechanisms that implement invariants
DLT expectations documentation — how to express quality constraints as pipeline-enforced rules
ClinicalTrials.gov data quality — what is actually found when ingesting it (missing fields, inconsistent formatting)

Bronze invariant decision: Immutable, raw as-received, full provenance metadata (source, ingestion timestamp, API version), no transformation permitted.
Silver invariant decision: Deferred until first Bronze ingestion.
Write Bronze invariant ADR before: Bronze build. Write Silver invariant ADR before: Silver build.

D-09: GenAI extraction scope
Reversibility: Adjustable. Expanding or contracting LLM scope affects the pipeline but not the output schema contract, provided the output structure remains stable.
Blocks: Extraction pipeline design.
Depends on: D-06 (must know what structure is being extracted into), D-08 Silver (Silver invariants constrain the quality guarantees extraction must meet).
Information readiness: Principle decidable now. Boundary cases decidable after reading 20–30 DMD eligibility texts — some criterion types will be obviously deterministic, some obviously non-computable, and the boundary cases require explicit classification decisions.
Knowledge required:

Aartsma-Rus reading frame calculator and exon skipping amenability tables — confirms that genetic eligibility for approved therapies is deterministic, not an LLM problem
FDA approved drug labels for eteplirsen, golodirsen, viltolarsen, casimersen — the source of the amenability reference table
Anthropic structured output / function calling documentation — how to enforce JSON schema compliance on LLM extraction outputs
Understanding of LLM confidence calibration — how to produce reliable confidence scores for extracted criteria
20–30 DMD trial eligibility texts from ClinicalTrials.gov — empirical basis for boundary case decisions

Principle decision: Deterministic genetic criteria use a reference table, not an LLM. LLM scope is limited to non-genetic clinical criteria and exclusion criteria classification. LLM is never used where a deterministic rule exists.
Write ADR before: Extraction pipeline build.

D-10: Computability classification schema
Reversibility: Partially reversible. Adding classes is safe. Removing or merging classes breaks downstream matching logic that depends on them.
Blocks: Gold matching logic design.
Depends on: D-06, D-09.
Information readiness: Three-class schema decidable now. Population of specific criterion types into classes decidable after reading DMD eligibility texts.
Knowledge required:

20–30 DMD eligibility texts — empirical basis for knowing which criterion types are computable
Understanding of the matching logic to be built: a criterion type is only worth classifying as deterministic if the matching rule for it can actually be implemented
HPO coverage for neuromuscular disease — some phenotypic criteria are only classifiable if HPO has a term for them

Schema decision: Three classes — deterministic, probabilistic, non-computable — plus a confidence score for probabilistic extractions, plus an extracted_by field recording model version and prompt version for auditability.
Write ADR before: Silver layer build.

Tier 3 — Cross-Domain and Governance
Adjustable to costly decisions. Decided before exposing products externally.

D-11: Cross-domain contract enforcement mechanism
Reversibility: Adjustable. The mechanism can change without changing the contract terms, provided the terms remain stable.
Blocks: External publication of genomic domain products.
Depends on: D-03, D-07.
Information readiness: Decidable before the first cross-domain product is published. Not blocking current build.
Knowledge required:

Unity Catalog table properties documentation — how to store and enforce version metadata
Delta Lake time travel documentation — how to pin a consumer to a specific table version
Schema evolution documentation — what Delta enforces automatically versus what requires explicit migration
Consumer tolerance for breaking changes: for a prototype with one consumer, this is simple; for an open source project with external consumers, a deprecation policy is needed

Decision for this project: Version stored as Unity Catalog table property. Consumer pipelines declare version dependency explicitly in code. Delta schema enforcement catches structural breaks at write time. Time travel used as safety net during breaking change absorption.
Write ADR before: First cross-domain product is published.

D-12: Match product interface type
Reversibility: Adjustable. Interfaces can be added without removing existing ones. Consumers depend on their specific interface, not the underlying storage.
Blocks: Nothing in the build sequence. Gold layer can be built before the interface is decided.
Depends on: Gold layer being built.
Information readiness: SQL endpoint decidable now as prototype interface. REST API design deferred until a specific external consumer is identified.
Knowledge required:

Databricks SQL endpoint documentation — setup, authentication, query patterns
Databricks Model Serving documentation — for REST API over the match logic
Delta Sharing documentation — for external organisation sharing without data copying
Consumer tool landscape: biostatisticians use SAS or R, data scientists use Python, clinical applications need REST APIs — consumer tool determines interface type

Decision for this project: SQL endpoint for prototype demonstration. REST API documented as target for clinical integration, designed when an external consumer is identified.
Write ADR before: First external consumer accesses a data product.

Tier 4 — Explicitly Deferred
Not absent decisions — decisions with named triggers. Each is documented here so deferral does not become forgetting.

D-13: HGVS representation for patient variants
Current status: Deferred.
Trigger: When patient variant data is added to the genomic domain. Not eligibility criteria — actual patient genotypes.
Knowledge required when triggered:

HGVS nomenclature specification — variant representation standard
GA4GH Phenopackets specification — patient phenotype plus genetic data standard
Leiden DMD variant database schema — how DMD variants are represented in the most complete public resource
VCF format specification — source format for genomic variant data
Translation tooling: hgvs Python library, Ensembl VEP for VCF-to-HGVS conversion


D-14: Separate matching domain
Current status: Deferred. Clinical trials domain owns match product per D-04.
Trigger: Expansion beyond Duchenne to a second disease area with independent matching logic, or a second independent trial domain consumer, or matching logic becoming an ML model requiring its own versioning and validation lifecycle.
Knowledge required when triggered:

Dehghani on domain proliferation anti-patterns — when splitting domains adds value versus overhead
Understanding of the new disease area's matching logic — does it share enough with Duchenne to stay in one domain, or is it genuinely independent?


D-15: Partitioning and Z-order optimisation
Current status: Deferred. Default Delta Lake settings apply.
Trigger: Query performance degrades measurably. Suggested threshold: match query latency on the full trial catalogue exceeds 30 seconds.
Knowledge required when triggered:

Delta Lake optimisation documentation: OPTIMIZE, ZORDER, Liquid Clustering
Actual query patterns from usage — partitioning decisions require real query logs, not hypothetical ones
Data volume actuals — partitioning strategy depends on row counts unknown until real data exists


D-16: External sharing model
Current status: Deferred.
Trigger: An external organisation (patient registry, hospital system, research consortium) wants to consume match products without direct platform access.
Knowledge required when triggered:

Delta Sharing protocol documentation — open protocol, no data copy, audit logs
Data clean room patterns — for sharing without exposing raw patient data
GDPR Article 46 adequacy requirements — for cross-border sharing if the external organisation is in a different jurisdiction
GA4GH Data Access Framework — the standard for controlled access to genomic data


D-17: Full GxP validation framework
Current status: Deferred.
Trigger: A regulated entity (pharmaceutical company, CRO, hospital conducting regulated trials) adopts the platform for use in a regulated context.
Knowledge required when triggered:

ICH E6(R3) full text — GCP requirements for data management systems
FDA 21 CFR Part 11 — electronic records and signatures
GAMP 5 guidance — validation framework for computerised systems in regulated environments
Validation evidence requirements: installation qualification, operational qualification, performance qualification


The Dependency Graph
Reading the dependency column across all decisions, the critical path is:
D-00 → D-01 → D-02 → D-05 → read 20–30 DMD eligibility texts
                           → D-06 → D-09 → build extraction pipeline
                                  → D-10 → build Silver layer
                                         → build Gold layer
                                                → D-12 → expose interface
                    → D-03 → D-07 → publish first Gold product
                           → D-11 → publish first cross-domain product
                    → D-04 → all pipeline design
                    → D-08 Bronze → Bronze build
                              → D-08 Silver → Silver build
Everything not on this path either runs in parallel or is explicitly deferred with a named trigger.

ADR Status Register
IDDecisionTierReversibilityStatusADRD-00Data mesh paradigm0StructuralPendingADR-000D-01Databricks platform0StructuralPendingADR-001D-02Domain boundary principle1StructuralPendingADR-002D-03Data product definition1StructuralPendingADR-003D-04Match product ownership1StructuralPendingADR-004D-05Canonical trial data source1CostlyPendingADR-005D-06Eligibility representation standard1CostlyPendingADR-006D-07Versioning and lifecycle strategy2StructuralPendingADR-007D-08Medallion layer invariants2AdjustablePendingADR-008D-09GenAI extraction scope2AdjustablePendingADR-009D-10Computability classification schema2PartialPendingADR-010D-11Cross-domain contract enforcement3AdjustablePendingADR-011D-12Match product interface type3AdjustablePendingADR-012D-13HGVS representation4CostlyDeferred — trigger: patient data added—D-14Separate matching domain4StructuralDeferred — trigger: second disease area—D-15Partitioning optimisation4ThrowawayDeferred — trigger: query performance threshold—D-16External sharing model4AdjustableDeferred — trigger: external consumer identified—D-17Full GxP validation framework4CostlyDeferred — trigger: regulated entity adoption—

