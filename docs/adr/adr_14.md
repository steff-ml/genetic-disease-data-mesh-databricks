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

## References

**Books**
- DDIA ch4: schema evolution and the costs of incompatible changes — directly applicable to variant representation format changes across HGVS specification versions
- FDE ch5: source system integration patterns and handling schemas with known complexity — Bronze ingestion from LOVD and VCF sources

**Databricks documentation**
- [Auto Loader](https://docs.databricks.com/en/ingestion/auto-loader/index.html) — incremental file ingestion for VCF or LOVD exports into Bronze; handles schema inference and evolution automatically
- [Delta Lake data types](https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html) — STRUCT and STRING type choices for storing HGVS strings and parsed variant components in Silver

**Domain-specific resources**
- [HGVS Nomenclature specification](https://hgvs-nomenclature.org) — the authoritative standard for variant representation; required reading before schema design
- [biocommons/hgvs Python library](https://github.com/biocommons/hgvs) — the primary Python library for HGVS parsing, normalisation, and validation; tool choice affects the Bronze-to-Silver transformation design
- [Ensembl Variant Effect Predictor (VEP)](https://www.ensembl.org/info/docs/tools/vep/index.html) — VCF-to-HGVS conversion; relevant if the source data is in VCF format rather than pre-annotated HGVS
- [VCF format specification v4.3](https://samtools.github.io/hts-specs/VCFv4.3.pdf) — the standard source format from sequencing pipelines; required to design the Bronze schema and the Bronze-to-Silver parsing step
- [LOVD DMD variant database](https://databases.lovd.nl/shared/genes/DMD) — the Leiden Open Variation Database for DMD; the most comprehensive public resource for DMD variants; the source schema that determines what normalisation is needed at Bronze ingestion
- [GA4GH Phenopackets schema](https://phenopacket-schema.readthedocs.io) — the standard for representing patient phenotype plus genetic data as a structured record; relevant if phenotypic data accompanies variant records in the patient-side data model

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when patient variant data is added to the genomic domain.*