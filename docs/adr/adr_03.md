Dehghani chapters 3–4 — domain-oriented ownership and what constitutes a domain boundary
Understanding of the specific data sources: ClinicalTrials.gov (trial domain), variant databases (genomic domain)
Understanding of the consumer question: who asks "which patients match which trials" — this identifies the owning domain
Anti-pattern knowledge: study-per-database silo, distributed monolith

## References

**Books**
- Dehghani, *Data Mesh* ch4, ch8: domain-oriented ownership and what constitutes a domain boundary
- FDE ch2–3: data domains and ownership in practice

**Databricks documentation**
- [Unity Catalog overview](https://docs.databricks.com/en/data-governance/unity-catalog/index.html) — the catalog–schema–table hierarchy is what domain boundaries map onto physically; understanding this before drawing boundaries prevents a topology you cannot implement