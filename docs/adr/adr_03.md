# ADR-03: Domain Boundary Principle

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** ADR-01 (paradigm defines what a domain is), ADR-02 (Unity Catalog defines the physical boundary mechanism)
**Blocks:** ADR-04, ADR-05, ADR-06, ADR-07, ADR-09, and all layer design decisions

---

## Knowledge Required

Dehghani chapters 3–4 — domain-oriented ownership and what constitutes a domain boundary
Understanding of the specific data sources: ClinicalTrials.gov (trial domain), variant databases (genomic domain)
Understanding of the consumer question: who asks "which patients match which trials" — this identifies the owning domain
Anti-pattern knowledge: study-per-database silo, distributed monolith

---

## References

**Books**
- Dehghani, *Data Mesh* ch4, ch8: domain-oriented ownership and what constitutes a domain boundary
- FDE ch2–3: data domains and ownership in practice

**Databricks documentation**
- [Unity Catalog overview](https://docs.databricks.com/en/data-governance/unity-catalog/index.html) — the catalog–schema–table hierarchy is what domain boundaries map onto physically; understanding this before drawing boundaries prevents a topology you cannot implement

---

## Decision

### Context

Data mesh requires domain boundaries to be drawn before any pipeline is built. A domain boundary is correct when there is an independent analytical question, an identifiable owning team, and an independent data lifecycle on each side of the boundary. In this project, domains are drawn as they would be in a multi-team deployment (not as they would be optimised for a single person) because the architecture is intended as a reusable model.

### Decision

**Three domains** are established.

---

**Discovery domain** — genetic and variant data

*Analytical question*: "What mutations exist in the DMD gene and what are their biological properties?"

Owns: LOVD variant records, ClinVar pathogenicity classifications, HGMD entries, Ensembl exon structure, reading frame computation outputs. Ingests from public variant databases and genomic reference APIs.

Published Gold products (cross-domain interfaces): `gold.patient_mutation_profile`, `gold.dmd_mutation_catalogue`, `gold.exon_skipping_eligibility`

Unity Catalog: `discovery.bronze`, `discovery.silver`, `discovery.gold`

---

**Clinical domain** — trial eligibility and patient-therapy matching

*Analytical question*: "Which trials is this patient eligible for?"

Owns: ClinicalTrials.gov trial records, EU Clinical Trials Register records, FDA drug labels (including their mutation eligibility criteria), EMA product information. The mutation eligibility criteria within a drug label are clinical eligibility rules, not variant data — they are consumed by the eligibility rule engine and belong here.

Published Gold products: `gold.trial_eligibility_catalogue`, `gold.patient_trial_eligibility`, `gold.therapy_addressable_population`, `gold.mutation_coverage_gaps`, `gold.patient_trial_eligibility_delta`

Unity Catalog: `clinical.bronze`, `clinical.silver`, `clinical.gold`

---

**Reference domain** — shared ontologies and controlled vocabularies

*Analytical question*: "What does this code, term, or identifier mean?"

Owns: HPO, HGNC, OMIM, Orphanet, dmd.nl exon reference tables, Ensembl gene structure reference (the static reference copy; the Discovery domain also queries Ensembl directly for variant data, but the canonical exon reference table is owned here).

Owner in the multi-team model: the data platform team (the hub). In the single-person implementation: the project maintainer. Reference data is not patient-level and has no direct clinical accountability; it is infrastructure.

Unity Catalog: `reference.raw`, `reference.curated` (static reference data does not require Bronze/Silver/Gold separation)

---

### Why FDA/EMA drug labels belong in the Clinical domain

Drug labels define approved therapy mutation eligibility criteria (e.g., "indicated for patients with a confirmed out-of-frame deletion amenable to exon 51 skipping"). These are eligibility rules consumed by the Clinical domain's matching engine — not variant records consumed by the Discovery domain. The Discovery domain does not read drug labels; the Clinical domain does.

### Why reference data is a separate domain

HPO, HGNC, and dmd.nl exon tables are consumed by both Discovery and Clinical with identical semantics. If each domain ingested its own copy, two independent curation pipelines would exist for the same source with no governance mechanism to detect divergence. A Reference domain with a single owner eliminates the duplication and makes ontology version updates a single operation.

### Alternatives considered

**Two domains (Discovery + Clinical, no Reference)**: simpler. Creates duplication of HPO, HGNC, and exon reference data across both domains. Two independent curation points for the same controlled vocabularies, with no guarantee they remain consistent. Rejected.

**Four or more domains (separate Matching domain)**: premature. A Matching domain is warranted only when matching logic becomes an ML model with its own versioning and validation lifecycle, or when a second disease area with genuinely different matching logic is added. Deferred in ADR-15.

**Study-level domains**: anti-pattern. Produces silos that cannot answer cross-study questions. Violates the fundamental mesh principle of domain-oriented (not study-oriented) ownership.

### Rationale

The three-domain topology matches the actual professional ownership structure in a clinical research organisation: a bioinformatics team owns variant data (Discovery), a clinical data management team owns trial data (Clinical), and a data platform team owns shared reference infrastructure (Reference). Building to this topology ensures the architecture is adoptable by a real organisation without restructuring.

### Consequences

- Cross-domain access goes through published Gold products with Bitol contracts (ADR-04); no direct cross-catalog table reads in production pipelines
- TREAT-NMD patient-level data, if access is confirmed, is ingested into the Discovery domain as a Bronze source — it does not require a new domain
- The Reference domain's curated tables are readable by both Discovery and Clinical pipeline service principals; they are the only tables with multi-domain read grants

### Compliance implications

- Unity Catalog catalog-level isolation ensures that clinical data (which may become patient-identifiable as the project matures) is isolated at the catalog level; pipelines without explicit grants cannot read it
- Reference domain tables carry no patient data and have a lower governance burden; they may be queried more openly

### Assumptions

- The Reference domain does not publish patient-level data; it contains only public ontologies and reference tables
- Ensembl is used by both the Reference domain (static exon reference table) and the Discovery domain (live variant annotation queries); this is acceptable because the uses are distinct

### Review trigger

If a second disease area (e.g., SMA) is added, evaluate whether the Discovery and Clinical domains remain appropriate as disease-agnostic boundaries or whether disease-specific sub-domains are needed.
