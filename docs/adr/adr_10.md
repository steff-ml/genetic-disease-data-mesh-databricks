# ADR-10: GenAI Extraction Scope

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-06 (eligibility representation standard — must know the structure being extracted into), ADR-09 Silver (Silver invariants constrain the quality guarantees extraction must meet)
**Blocks:** Extraction pipeline design

---

## Knowledge Required

Aartsma-Rus reading frame calculator and exon skipping amenability tables — confirms that genetic eligibility for the four FDA-approved AONs is fully deterministic. Exon 51 skip amenability, for example, is a lookup against a known table. This is not an LLM problem.

FDA approved drug labels for eteplirsen (exon 51), golodirsen (exon 53), viltolarsen (exon 53), casimersen (exon 45) — the authoritative source of the amenability reference tables. These labels define the exact deletion patterns that qualify.

Anthropic structured output / tool use documentation — how to enforce JSON schema compliance on LLM extraction outputs so extracted criteria conform to the Silver schema contract.

Understanding of LLM confidence calibration — how to produce reliable confidence scores for probabilistic extractions. Confidence scores are part of the computability classification schema (ADR-11) and must be interpretable downstream.

20-30 DMD trial eligibility texts from ClinicalTrials.gov — the empirical basis for boundary case decisions. Some criterion types will be obviously deterministic (exon deletion pattern), some obviously non-computable (physician discretion), and the boundary cases (age thresholds, ambulation status) require explicit classification decisions.

---

## Partial Decision

Deterministic genetic criteria use a reference table, not an LLM. LLM scope is limited to non-genetic clinical criteria and exclusion criteria classification. LLM is never used where a deterministic rule exists.

---

## References

**Books — AI Engineering (Huyen, 2025)**
- AIE ch5, Information Extraction section (p.521–536) — **primary reference** for this ADR. The only source in the reading list that directly addresses how to build a structured extraction pipeline using an LLM: structured output enforcement, JSON schema compliance, prompt patterns for extraction tasks
- AIE ch3–4 (Evaluation Methodology and Metrics) — how to evaluate extraction quality, precision/recall on extracted entities, confidence calibration; needed to write the evaluation criteria for the confidence score design
- AIE ch6 (RAG and Agents) — if eligibility criteria extraction needs to reference external knowledge (HPO ontology, drug labels), RAG architecture patterns apply
- AIE ch10 (AI Engineering Architecture) — the overall architecture for integrating an LLM extraction component into a data pipeline; covers the interface between extraction and downstream consumers

**Books — Designing ML Systems (Huyen, 2022)**
- DMLS ch3 (Data Engineering Fundamentals) — the data pipeline context for ML components; where extraction sits in the Bronze→Silver pipeline
- DMLS ch8 (Data Distribution Shifts and Monitoring) — how ClinicalTrials.gov eligibility criteria language changes over time and how to detect when the extraction model degrades due to distribution shift; the monitoring dimension of this decision

**Databricks documentation**
- [Model Serving](https://docs.databricks.com/en/machine-learning/model-serving/index.html) — how to deploy the LLM extraction component as a Databricks endpoint; relevant to latency, cost, and audit trail for the extraction step
- [MLflow](https://docs.databricks.com/en/mlflow/index.html) — tracking extraction model experiments, versioning prompts and models, logging extraction accuracy metrics; the `extracted_by` field in the Silver schema should reference an MLflow run ID
- [External model endpoints](https://docs.databricks.com/en/generative-ai/external-models/index.html) — how to integrate and audit external API calls (Claude) within Databricks if not using a self-hosted model

**Domain-specific primary sources**
- Aartsma-Rus reading frame calculator and exon skipping amenability tables
- FDA approved drug labels: eteplirsen, golodirsen, viltolarsen, casimersen

---

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before extraction pipeline build.*