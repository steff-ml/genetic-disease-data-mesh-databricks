# ADR-20: GenAI Extraction Model Governance

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Draft
**Depends on:** ADR-10 (GenAI extraction scope — scope defines what the model must do; governance defines how it does it safely)
**Blocks:** Production extraction pipeline deployment

---

## The Problem

ADR-10 decides what the extraction model does. This ADR decides how it is governed in production: how model versions are pinned, how prompt changes are controlled, how output quality is validated, and what the audit trail looks like. These are distinct questions. A well-scoped model with no governance is not deployable in a clinical data pipeline.

---

## Knowledge Required

**Model version pinning**: Anthropic deprecates model versions on a published schedule. A production pipeline must pin to a specific model version (e.g., `claude-sonnet-4-6`) and define a validation protocol for upgrading — because a model upgrade is a change to the system that can alter extraction outputs for identical inputs.

**Prompt versioning and change control**: Prompts are code. They must be version-controlled (Git), reviewed before deployment, and linked to the extraction outputs they produced. A prompt change without a version bump makes outputs non-reproducible. The `extracted_by` field in the Silver schema (from ADR-11) must record prompt version alongside model version.

**Confidence threshold calibration**: The threshold that separates "extract and flag as probabilistic" from "flag for human review" requires calibration against labelled examples. The calibration method and the resulting threshold must be documented and justified, not set arbitrarily.

**Output validation**: Schema compliance (does the extracted JSON conform to the Silver schema?), range checks (is the confidence score between 0 and 1?), and cross-referencing (does an extracted mutation class match the known DMD mutation taxonomy?) — these must run as pipeline expectations, not as post-hoc checks.

**Fallback behaviour**: What happens when the model is unavailable, returns a malformed response, or returns a confidence score below the actionable threshold? The pipeline must degrade gracefully — quarantine the record, log the failure, alert — not silently skip or corrupt.

**EU AI Act compliance**: Clinical data extraction pipelines using generative AI are likely to be classified as high-risk AI systems under the EU AI Act (Annex III, healthcare context). Requirements include: transparency of AI involvement in the output, human oversight capability, technical documentation, conformity assessment, and post-market monitoring. These must be designed in from the start.

**Anthropic usage policies and data handling**: Inputs to the extraction model may contain clinical trial text that is publicly available, but the pipeline design must confirm that API usage complies with Anthropic's data processing terms, particularly if the pipeline is ever used with non-public patient data.

---

## References

**Books — AI Engineering (Huyen, 2025)**
- AIE ch3–4 (Evaluation Methodology and Metrics) — precision/recall for extracted entities, confidence calibration methods; required to define what the confidence threshold means and how to justify it
- AIE ch10 (AI Engineering Architecture) — the overall architecture for integrating an LLM into a data pipeline; how to version the extraction component and interface it with downstream consumers

**Books — Designing ML Systems (Huyen, 2022)**
- DMLS ch8 (Data Distribution Shifts and Monitoring) — detecting when an extraction model degrades due to changes in source data language; maps directly to the post-deployment monitoring requirement and EU AI Act post-market monitoring obligation

**Databricks documentation**
- [MLflow](https://docs.databricks.com/en/mlflow/index.html) — prompt versioning, model version tracking, extraction accuracy logging; the `extracted_by` field in the Silver schema (ADR-11) should reference an MLflow run ID to make outputs traceable to the exact prompt and model that produced them
- [External model endpoints](https://docs.databricks.com/en/generative-ai/external-models/index.html) — how to call and audit external API calls (Claude) within a Databricks pipeline; provides the audit log mechanism for external model calls required under the governance framework

**Anthropic resources**
- [Anthropic model deprecation policy](https://docs.anthropic.com/en/api/versioning) — the published model lifecycle and deprecation schedule; defines the minimum notice period before a pinned model version is retired; required reading before committing a version string to a production pipeline
- [Anthropic usage policy](https://www.anthropic.com/legal/usage-policy) — confirms whether processing clinical trial eligibility text is within permitted use; must be reviewed before production deployment, and again if the pipeline is extended to non-public patient data
- [Anthropic privacy policy and data handling](https://www.anthropic.com/legal/privacy) — the data processing terms covering what Anthropic retains from API calls; critical for confirming compliance when any patient-adjacent data enters the extraction pipeline

**Regulatory references**
- [EU AI Act (Regulation 2024/1689)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) — the full regulation text; Annex III defines high-risk AI system categories (healthcare context); Article 10 covers data governance requirements; Article 13 covers transparency obligations; required reading before production deployment of the extraction pipeline

---

## Decision (to be filled in before extraction pipeline build)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the extraction pipeline goes to production.*