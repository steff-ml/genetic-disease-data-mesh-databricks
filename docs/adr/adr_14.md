# ADR-14: HGVS Representation for Patient Variants

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Deferred
**Trigger:** When patient variant data is added to the genomic domain. Not eligibility criteria — actual patient genotypes.
**Depends on:** ADR-06 (canonical data sources), ADR-09 (medallion layer invariants)
**Blocks:** Patient variant ingestion design

---

## Knowledge Required

HGVS nomenclature specification (hgvs.org) — the standard for representing sequence variants at DNA, RNA, and protein level. Variants must be expressed in HGVS to be unambiguous across registries and tools.

GA4GH Phenopackets specification — the standard for representing patient phenotype plus genetic data. Relevant for the patient-side data model if phenotypic data is included alongside genotype.

Leiden DMD variant database (LOVD) schema — how DMD variants are represented in the most complete public resource for this disease. The source schema determines what normalisation is needed.

VCF format specification — the standard source format for genomic variant data from sequencing pipelines. Understanding VCF is required to design the Bronze-to-Silver transformation that produces HGVS-normalised records.

Translation tooling: hgvs Python library (biocommons) for HGVS parsing and normalisation; Ensembl Variant Effect Predictor (VEP) for VCF-to-HGVS conversion. Tool choice affects the Silver transformation design.

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when patient variant data is added to the genomic domain.*