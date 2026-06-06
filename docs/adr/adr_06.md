# ADR-06: Canonical Data Sources

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Depends on:** ADR-03 (domain boundaries determine which domain owns which sources)
**Blocks:** ADR-09 (Bronze layer invariants), Bronze ingestion pipeline design for all domains

---

## Knowledge Required

ClinicalTrials.gov API documentation — available fields, data structure, update frequency
TREAT-NMD registry — what it adds that ClinicalTrials.gov lacks (deeper phenotypic data, patient-level registry data)
EudraCT — European trial coverage gaps in ClinicalTrials.gov
Limitations documentation: what ClinicalTrials.gov does not contain that a production system would need

---

## References

**Books**
- FDE ch5: source system evaluation and ingestion patterns
- DDIA ch4: data encoding and schema evolution — relevant to how ClinicalTrials.gov data structure changes propagate downstream

**Databricks documentation**
- [Auto Loader for incremental ingestion](https://docs.databricks.com/en/ingestion/auto-loader/index.html) — relevant to how ClinicalTrials.gov data arrives and is ingested into Bronze
- [Connecting to external systems and APIs](https://docs.databricks.com/en/connect/external-systems/index.html) — the technical basis for the ClinicalTrials.gov ingestion pipeline design

---

## Decision

### Context

Each domain's Bronze layer must declare its canonical sources before any ingestion pipeline is built. Canonical means: this source is ingested; in case of disagreement between sources covering the same entity, the conflict resolution rule below applies. Without canonical source declarations, conflicting data from multiple sources can silently produce inconsistent Silver and Gold records.

The principle for this project is maximum coverage: pull from all publicly accessible sources. Data access requirements (TREAT-NMD, HGMD) keep those sources as options rather than active canonical sources until access is confirmed.

### Decision

**Clinical domain sources**

| Source | Canonical for | Access |
|--------|--------------|--------|
| ClinicalTrials.gov REST API | Trial eligibility criteria, NCT IDs, trial status, intervention type, phase | Public |
| EU Clinical Trials Register | European EMA-registered trials not covered or incompletely covered by ClinicalTrials.gov | Public |
| FDA DailyMed drug labels | Approved therapy mutation eligibility criteria, prescribing conditions | Public |
| EMA product information | EU-approved equivalent of FDA labels | Public |

**Discovery domain sources**

| Source | Canonical for | Access |
|--------|--------------|--------|
| LOVD DMD-specific | Curated DMD/BMD variant catalogue, exon-level annotation | Public |
| ClinVar (NCBI FTP) | Variant pathogenicity classifications (Pathogenic / VUS / Benign) | Public |
| Ensembl REST API | DMD transcript structure, exon coordinates, variant annotation (VEP) | Public |
| TREAT-NMD Global Database | Patient-level mutation registry data with phenotype linkage | Data access agreement required — pipeline stub created, not activated |
| HGMD | Comprehensive disease mutation catalogue | Subscription required — deferred until access confirmed |

**Reference domain sources**

| Source | Canonical for | Access |
|--------|--------------|--------|
| HPO (JAX OBO release) | Phenotype ontology terms and hierarchy | Public |
| HGNC | Authoritative gene symbols and IDs (DMD: HGNC:2928) | Public |
| OMIM | Disease definitions, genotype-phenotype correlations | Public (API key required) |
| Orphanet | Rare disease classification, ORPHA codes | Public |
| dmd.nl Leiden MD pages | DMD exon sizes, reading frame table for all standard deletion patterns | Public |

---

### Conflict resolution rules

**ClinicalTrials.gov vs EU Clinical Trials Register — same trial (matched on NCT ID or EUDRACT number)**

Merge on the common identifier where possible. Where eligibility criteria text differs materially between the two sources for the same trial, do not silently prefer either source. Set `source_conflict = true` and `action_required = 'expert_review'` on the Silver record. The record is included in Gold as a lower-confidence entry with `conflict_flagged = true`; it is not quarantined, because the trial's existence is not in doubt.

**LOVD vs ClinVar — same variant (matched on HGVS normalised representation), disagreeing pathogenicity**

Flag the variant in `silver.dmd_variants` with `classification_conflict = true` and `action_required = 'expert_review'`. Quarantine from Gold publication: the variant is not promoted to `gold.dmd_mutation_catalogue` until the conflict is resolved by an expert or a resolution rule is applied (e.g., ClinVar has higher evidence level). A variant with unresolved conflicting pathogenicity classifications is not safe to use in an eligibility decision.

**Multiple LOVD submissions — same variant, different submitters, different clinical significance**

Apply the same flagging as LOVD vs ClinVar disagreement. If clinical significance differs between LOVD submitters, treat it as a conflict requiring review.

**LOVD and ClinVar covering different variants (no overlap)**

No conflict. Each source is additive. A variant present in LOVD but not ClinVar is still eligible for Gold promotion. A variant in ClinVar but not LOVD is also eligible. The two sources are not mutually exclusive.

---

### Alternatives considered

**ClinicalTrials.gov only for trial data**: simpler ingestion. The EU Clinical Trials Register covers European EMA-registered studies that may not appear or may be incompletely represented in ClinicalTrials.gov. Excluding it reduces coverage for European trials and European patients. Rejected.

**TREAT-NMD as primary patient mutation source from the start**: TREAT-NMD has >7,000 curated patient mutations with phenotype linkage — more than LOVD alone. However, access requires a formal Data Access Agreement. Making TREAT-NMD canonical before access is confirmed would block the Discovery domain pipeline on a bureaucratic process. Kept as an option with a pipeline stub; not activated until access is confirmed.

**Single canonical source per entity type**: simpler conflict resolution. Insufficient coverage — LOVD and ClinVar each carry variants the other does not, and both are needed for maximum mutation catalogue completeness.

**Silent winner rule for conflicts** (e.g., ClinVar always wins): eliminates the need for expert review flags. Unacceptable in a clinical context. A variant whose pathogenicity is disputed between two authoritative sources requires human judgment; automated resolution would produce eligibility decisions based on silently overridden data.

### Rationale

The maximum coverage principle reflects the clinical importance of the mutation catalogue: a patient whose variant is not in the catalogue cannot be matched. Coverage completeness is more important than ingestion simplicity at this stage. Conflict flagging rather than silent resolution ensures that downstream consumers know when they are relying on a disputed classification.

### Consequences

- The Bronze layer ingests from all confirmed public sources simultaneously; TREAT-NMD and HGMD ingestion pipelines are stubbed (schema and job defined) but not activated
- Silver deduplication and conflict-flagging logic is established before Gold promotion; the `classification_conflict` and `source_conflict` flag schema is defined in Silver tables
- The Reference domain runs its own ingestion independently; Discovery and Clinical consume from `reference.curated.*` rather than each querying HPO and HGNC directly

**Note added 2026-06-06 — EudraCT investigation**: EudraCT's informal REST endpoint (`/ctr-search/rest/search`) is decommissioned — HTTP 404 on all variants. The source is frozen (no new records since January 2023; CTIS became mandatory for new EU trials from that date). No automated ingestion pipeline is viable. The 108 DMD records visible in the EudraCT web UI are the final count; a manual one-time extraction is documented in `exploratory/notes.md` as a fallback if historical completeness is required. CTIS (the "EU Clinical Trials Register" entry in this ADR) is confirmed as the correct canonical source for all ongoing EU trial coverage.

### Compliance implications

- Conflict flagging rather than silent resolution satisfies the ALCOA+ Accurate requirement: data with unresolved quality questions is not published as authoritative to downstream consumers
- All Bronze records include provenance metadata: `source_system`, `ingestion_timestamp`, and `source_version` (API version, FTP release date, or download date). This satisfies the ALCOA+ Attributable and Original requirements
- Quarantined records are retained in Silver with their conflict flags; they are not deleted. This satisfies the Enduring requirement — the original conflicting records remain in the audit trail

### Assumptions

- ClinicalTrials.gov API rate limits do not require a formal data access agreement for research-scale ingestion; standard public API access is sufficient
- OMIM API access requires registration; this is a minor administrative step, not a blocking dependency
- TREAT-NMD data access, if confirmed, goes into `discovery.bronze` as an additional source alongside LOVD; it does not require a new domain

### Review trigger

When TREAT-NMD data access is confirmed, activate the ingestion pipeline stub, define the TREAT-NMD vs LOVD priority rule for patient-level mutation data, and update this ADR. When HGMD subscription access is confirmed, evaluate whether HGMD adds coverage beyond LOVD + ClinVar for DMD-specific variants.
