Knowledge required:

HPO (Human Phenotype Ontology) documentation — what phenotypic concepts it covers, how terms are structured
20–30 DMD trial eligibility criteria texts — what categories of criteria actually appear in practice
Understanding of the Duchenne mutation landscape: exon deletions, duplications, point mutations, reading frame rule — needed to design the mutation class enum
GA4GH Phenopackets specification — the standard for patient phenotype plus genetic data, relevant for the patient-side upgrade path

## References

**Books**
- DDIA ch2: data models and query languages — the trade-offs between relational, document, and graph representations apply directly to eligibility criteria
- FDE ch8: schema design for analytical pipelines

**Databricks documentation**
- [Delta Lake data types](https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html) — specifically STRUCT and ARRAY types; the eligibility criterion schema will use these for nested structured representation
- [Table constraints](https://docs.databricks.com/en/tables/constraints.html) — how to enforce NOT NULL and CHECK constraints at the Delta level for required schema fields