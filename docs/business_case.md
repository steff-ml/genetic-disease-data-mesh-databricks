# Business Case: Genetic Disease Data Mesh AI GENERATED SUBJECT TO HUMAN REVIEW
*(AI generated — subject to review)*

This document makes the case for building a governed, continuously updated data platform that links genetic mutation profiles to therapeutic eligibility for Duchenne Muscular Dystrophy (DMD) — and demonstrates the value of extending this architecture to other rare genetic diseases.

---

## The Value of Integrated Data Sources for Genetic Diseases

### Trial Recruitment Failure Costs

Clinical trial recruitment is the single most cited cause of trial delay and failure in drug development. For rare diseases, the problem is structural: patient populations are small, genetic eligibility criteria are highly specific, and the tools for identifying eligible patients are fragmented.

For DMD specifically, the bottleneck is mutation-specific eligibility. Each approved exon-skipping therapy targets a specific subset of deletion patterns. Four FDA-approved antisense oligonucleotides (targeting exons 51, 53, 45, and 44) together cover only approximately **27% of DMD patients** — meaning the majority of patients are screened out based on mutation alone, before any clinical criteria are applied ([Leckie, Zia & Yokota, 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11593839/)). In this context, identifying eligible patients ahead of trial opening — rather than screening them reactively — has direct commercial and scientific value.

Beyond DMD, the broader costs of poor data infrastructure in clinical research are well-documented. An estimated **$28 billion per year** is lost to preclinical biomedical research that cannot be reproduced, partly due to data analysis and reporting failures ([Freedman, Cockburn & Simcoe, 2015, *PLOS Biology*](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1002165)). Data integrity violations appear in **60–80% of FDA GMP warning letters**, the single most cited compliance failure category ([Astrix, FDA enforcement data](https://www.astrixinc.com/blog/trends-in-fda-data-integrity-483s-and-warning-letters-for-pharmaceutical-companies/)). These are the direct consequences of building registries and pipelines without the governance infrastructure to keep eligibility data current, accurate, and linkable.

---

### Diagnostic Odysseys

Before any mutation-specific therapy can be prescribed or a trial enrolment can be initiated, a patient requires a confirmed molecular diagnosis — a precise identification of which exons are affected and what the reading frame consequence is. Without this, no eligibility determination is possible.

Rare disease patients face significant delays in reaching this point. Surveys consistently report average diagnostic delays of **4–8 years**, with a meaningful proportion of patients initially misdiagnosed ([EURORDIS Rare Barometer, 2017](https://www.eurordis.org/rare-barometer/); [NORD, 2020](https://rarediseases.org/)). For DMD, molecular diagnosis has improved with wider access to next-generation sequencing, but structured linkage between a confirmed molecular diagnosis and therapy eligibility remains a manual process.

The `patient_mutation_profile` data product this project produces makes that linkage immediate and computational. A confirmed HGVS-annotated variant maps directly to Layer 1 mutation classification and from there to therapy eligibility flags — reducing the time between molecular diagnosis and an eligibility assessment from days of expert cross-referencing to a query.

---

### Therapy Eligibility Gaps

The most direct quantification of the problem this project addresses:

[Leckie et al. (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11593839/) applied every approved and experimental exon-skipping strategy to the full UMD-DMD mutation database. The result: the four currently FDA-approved AONs reach only **27% of patients**. The remaining 73% are not without options — the trial landscape includes CRISPR-based exon deletion (~60% of deletion patients), stop codon readthrough for the ~10–15% with nonsense mutations, mutation-agnostic microdystrophin gene therapy, and emerging base and prime editing approaches for point mutations and small frameshifts. But identifying which of these a specific patient qualifies for requires manually cross-referencing mutation data, the reading frame rule, and free-text trial eligibility criteria across multiple disconnected systems.

That process does not scale. This project makes it queryable.

The [TREAT-NMD Global Database (Bladen et al., 2015)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4405042/) has catalogued more than 7,000 DMD mutations. The [data silos that fragment this knowledge](https://pmc.ncbi.nlm.nih.gov/articles/PMC8025897/) — across registries, trial databases, and published literature — are the primary obstacle between a patient and the therapy options available to them.

---

### Translation to Other Diseases

The data architecture built for DMD is not DMD-specific. The three-layer eligibility model, the medallion architecture across Discovery and Clinical domains, and the cross-domain data product design apply directly to any rare genetic disease where mutation type determines therapy eligibility, multiple therapeutic approaches with different genetic prerequisites exist in parallel, and the patient population is too small for reactive recruitment to function reliably.

Immediate candidates for extension include Spinal Muscular Atrophy (SMN1/SMN2 copy number-dependent eligibility for nusinersen and risdiplam), Huntington's disease (CAG repeat length-dependent trial eligibility), and the lysosomal storage disorders. The [RDCA-DAP platform (Barrett et al., 2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10673974/) is pursuing this generalisation at the regulatory level via CDISC SDTM; this project provides the open-access, research-grade equivalent.

Building to [FAIR data principles (Wilkinson et al., 2016, *Scientific Data*)](https://www.nature.com/articles/sdata201618) — now endorsed by NIH, EMA, and FDA as a framework expectation in drug development submissions — means the DMD implementation functions simultaneously as a working product and a reusable template for subsequent rare disease domains. Each new disease domain added to the mesh reduces the marginal cost of the next.

---

## Product Use Cases

### Patient-Trial Matching

**Who uses it**: clinical research coordinators, trial sponsors, patient advocacy organisations, clinicians referring patients to trials.

**The query**: given a patient's confirmed mutation profile, which currently open or recruiting trials do they meet the genetic eligibility criteria for?

**How it works**: `discovery.gold.patient_mutation_profile` is joined against `clinical.gold.trial_eligibility_catalogue` to produce `clinical.gold.patient_trial_eligibility` — a per-patient, per-trial eligibility verdict with a mutation-eligible flag, an evidence level (approved / active trial / completed / experimental), and a list of exclusion reasons where applicable. Patient-level criteria (age, ambulatory status, AAV antibody titres) are flagged as fields requiring clinical input.

**Value delivered**: replaces a manual, multi-system, expert-dependent process with a structured, auditable query. Scales across an entire patient registry rather than one patient at a time. Updates automatically as trials open, close, or revise eligibility criteria.

---

### Patient-Therapy Matching

**Who uses it**: clinicians making prescribing decisions, patients and families seeking clarity on approved options, payers assessing coverage eligibility.

**The query**: given a patient's confirmed mutation profile, which currently approved therapies are they eligible for, and which are they explicitly excluded from?

**How it works**: a constrained version of patient-trial matching, filtered to `evidence_level = approved`. The output is a short list of approved therapies with eligibility flags and the specific mutation-level reasoning — for example: *"eligible for exon 51 skipping: deletion of exons 49–50 is out-of-frame and restored to in-frame by skipping exon 51."*

**Value delivered**: provides an auditable, reproducible eligibility determination grounded in the published reading frame rule ([Aartsma-Rus et al., 2009](https://pubmed.ncbi.nlm.nih.gov/19156838/)) and current FDA/EMA approval criteria — replacing informal expert judgement with a documented, versioned data product output.

---

### Therapeutic Cohort Sizing

**Who uses it**: biotech and pharma companies designing new therapeutic programs; academic groups planning clinical studies; trial sponsors estimating recruitment feasibility before committing to a protocol.

**The query**: given a proposed therapeutic approach with defined mutation eligibility criteria, how many patients in the known DMD population would qualify? What is the overlap with patients already enrolled in other trials?

**How it works**: the reverse direction of patient-trial matching. Rather than querying from a patient outward, this queries from a therapy inward — applying candidate eligibility rules against `gold.dmd_mutation_catalogue` to count and characterise the addressable population before a trial is designed. This is the analysis [Leckie et al. (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11593839/) performed statically for approved AONs; this product makes it available as a live query against the current mutation landscape.

**Value delivered**: de-risks trial design decisions. A company considering a new exon-skipping combination can answer "how many patients exist for this approach" before investing in protocol development. This is particularly valuable for the ~73% of patients not covered by approved therapies, where the addressable population for any new approach is small and must be estimated precisely.

---

### Mutation Gap Analysis

**Who uses it**: patient advocacy organisations prioritising research funding; drug developers identifying underserved mutation classes; regulators and payers assessing equity of therapeutic coverage.

**The query**: which mutation classes have no approved therapy and no active trial? How many patients fall into each gap, and what therapeutic mechanism would be required to address them?

**How it works**: an aggregation across `gold.dmd_mutation_catalogue`, `gold.exon_skipping_eligibility`, and `gold.trial_eligibility_catalogue` — grouping patients by mutation class and flagging those with zero approved and zero active trial options. The output characterises each gap by patient count, mutation type, and the Layer 2 eligibility logic that would need to be satisfied by a new approach.

**Value delivered**: makes the unmet need visible and specific rather than approximate. Advocacy organisations such as Parent Project Muscular Dystrophy or TREAT-NMD can use this to direct research funding toward the mutation classes with the largest underserved populations. Drug developers can identify white space. The [Denton et al. (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8025897/) finding — that data silos cause redundant studies rather than coordinated coverage — is exactly the failure this use case prevents.

---

### Proactive Trial Alerts for Patient Registries

**Who uses it**: patient registries (TREAT-NMD, national DMD registries, patient advocacy-run databases); clinicians managing cohorts of DMD patients; patients and families who have opted into a registry.

**The query**: as new trials open or eligibility criteria change, which registered patients have become newly eligible?

**How it works**: a triggered, event-driven version of patient-trial matching. When `gold.trial_eligibility_catalogue` is updated with a new or modified trial record, the eligibility join is re-run for the affected trial and the delta — patients who are newly eligible relative to the previous version — is surfaced as a notification or report. This requires patient mutation profiles to be maintained in the system, which is a data governance decision each registry must make.

**Value delivered**: converts the mutation-to-trial matching system from a query tool into an active recruitment support system. For rare diseases where eligible patients are geographically dispersed and no single site has enough of them, proactive identification is the difference between a trial recruiting on schedule and one that fails to reach statistical power.
