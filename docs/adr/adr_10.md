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

## Decision (to be filled in)

*Context, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed before extraction pipeline build.*