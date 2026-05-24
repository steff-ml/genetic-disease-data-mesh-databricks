# ADR-18: Full GxP Validation Framework

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Deferred
**Trigger:** A regulated entity (pharmaceutical company, CRO, or hospital conducting regulated clinical trials) adopts the platform for use in a regulated context.
**Depends on:** Platform build complete
**Blocks:** Use of the platform in a GxP-regulated context

---

## Current position

The platform is built with 21 CFR Part 11 compatible audit trail and ALCOA+ data integrity principles from the start. Full GxP validation (IQ/OQ/PQ) is not required until a regulated entity adopts it. Building validation evidence before a regulated consumer exists is premature and expensive.

---

## Knowledge Required When Triggered

ICH E6(R3) full text — Good Clinical Practice requirements for data management systems used in clinical trial contexts. Defines the obligations a computerised system must satisfy to be used in a regulated trial.

FDA 21 CFR Part 11 — electronic records and electronic signatures. Defines the technical controls (audit trail, access control, system validation) required for records that are created, modified, maintained, or transmitted electronically in a regulated context.

GAMP 5 guidance (ISPE) — the industry-standard validation framework for computerised systems in regulated environments. Defines the validation lifecycle: user requirements specification, functional specification, design specification, installation qualification (IQ), operational qualification (OQ), performance qualification (PQ).

Validation evidence requirements for the specific regulated use case: which records are GxP-relevant, which system functions require validation, and what level of validation evidence the regulated consumer's quality system requires.

---

## References

**Books**
- No general-purpose data engineering or ML books cover GxP validation directly. This decision is governed entirely by regulatory and industry-standard guidance.

**Regulatory references**
- ICH E6(R3) — Good Clinical Practice guidance; sections 4–5 cover computerised systems and data integrity obligations in regulated clinical trials; defines the obligations the platform must satisfy to be used in a trial context
- FDA 21 CFR Part 11 — electronic records and electronic signatures; the technical requirements (audit trail, access control, system validation) for systems used in FDA-regulated contexts
- GAMP 5 (ISPE) — the industry-standard validation lifecycle framework: User Requirements Specification, Functional Specification, Design Specification, Installation Qualification (IQ), Operational Qualification (OQ), Performance Qualification (PQ)

**Additional regulatory resources**
- EMA Annex 11 — the EU equivalent of FDA 21 CFR Part 11 for computerised systems in GMP/GCP contexts; required if the regulated consumer operates under EMA oversight
- EMA Guidelines on Computerised Systems — practical implementation guidance that complements the legal text of Annex 11; covers data integrity, audit trails, and validation in clinical trial data management

---

## Decision (to be filled in when triggered)

*Context, decision, alternatives considered, rationale, consequences, compliance implications, assumptions, and review trigger to be completed when a regulated entity adopts the platform.*