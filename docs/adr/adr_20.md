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

## Decision (to be filled in before extraction pipeline build)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before the extraction pipeline goes to production.*