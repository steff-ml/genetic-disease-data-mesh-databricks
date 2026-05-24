Knowledge required:

ClinicalTrials.gov API documentation — available fields, data structure, update frequency
TREAT-NMD registry — what it adds that ClinicalTrials.gov lacks (deeper phenotypic data, patient-level registry data)
EudraCT — European trial coverage gaps in ClinicalTrials.gov
Limitations documentation: what ClinicalTrials.gov does not contain that a production system would need

## References

**Books**
- FDE ch5: source system evaluation and ingestion patterns
- DDIA ch4: data encoding and schema evolution — relevant to how ClinicalTrials.gov data structure changes propagate downstream

**Databricks documentation**
- [Auto Loader for incremental ingestion](https://docs.databricks.com/en/ingestion/auto-loader/index.html) — relevant to how ClinicalTrials.gov data arrives and is ingested into Bronze
- [Connecting to external systems and APIs](https://docs.databricks.com/en/connect/external-systems/index.html) — the technical basis for the ClinicalTrials.gov ingestion pipeline design