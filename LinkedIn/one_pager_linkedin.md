# The bottleneck is not the science

A child with Duchenne Muscular Dystrophy receives a confirmed genetic diagnosis on average 2.2 years after first symptoms appear.

By that point, something remarkable is already true: a single formula predicts a large part of their clinical future. Take the deleted exons. Sum their nucleotide lengths. Divide by three.

If the remainder is zero, the reading frame is preserved. The patient likely has the Becker variant — milder symptoms, ambulatory into their 40s, near-normal life expectancy.

If the remainder is one or two, the reading frame breaks. No functional dystrophin is produced. That is DMD: loss of independent walking by 10–12, ventilator dependence through the teens, life expectancy of 20–30 years.

The formula holds for 91% of patients at the DNA level. The biology is not the hard part.

---

Four FDA-approved exon-skipping therapies exist for DMD. Together they cover roughly 27% of patients by mutation type. The remaining 73% have options — investigational oligonucleotides, gene therapy, stop-codon readthrough — but identifying which one a specific patient qualifies for requires manually cross-referencing their confirmed mutation against trial eligibility criteria written in free text, across registries that do not interoperate.

In oncology, MatchMiner solved the equivalent problem computationally: linking tumour genomic profiles to targeted trials, reducing time to consent by 22% — 55 days. DMD is structurally simpler than cancer. The eligibility rule is arithmetic. The exon sizes are published.

What is missing is not scientific inference. It is governed infrastructure.

---

So why hasn't it been built?

The matching logic is not the barrier. The barrier is a specific combination: reading a clinical genetics paper and knowing which exception cases invalidate the formula; understanding that GDPR's right to erasure conflicts directly with the ICH requirement to retain trial records for 15 years, and resolving that conflict in the data model rather than in a legal memo; then writing the governed pipeline that enforces the result — without losing context at any of those handoffs.

The pharma industry understands the challenge. Novartis has invested heavily in embedding AI specialists directly with bench scientists — the instinct is right, and at sufficient scale it demonstrably works. But "it works" describes a sustained organisational investment: years of ramp-up, coordination overhead across large teams, justified by blockbuster-drug economics. For rare diseases, where a condition may affect thousands of patients globally and commercial returns are uncertain, that investment calculus rarely holds.

Here is the part that gets less attention: even where the resources exist, the coordination overhead between specialists who do not share a language is a tax on every project, not a problem that disappears once you can afford to hire all three. A handoff between the clinical expert, the regulatory expert, and the data engineer still happens. Errors still fall into the gaps. Someone who does not need the translation step is not a budget workaround — they are a structural advantage, including inside a well-resourced team. That combination is rare. It may be the actual reason this infrastructure does not exist for rare monogenic diseases, despite the matching logic being simpler than oncology.

---

I am building an open-source reference implementation: a governed data mesh on Databricks that integrates LOVD, ClinVar, and ClinicalTrials.gov, applies the reading frame rule at scale, flags classification conflicts across databases, and surfaces patient-trial matches automatically. Built to the standards a regulated environment requires — OMOP CDM, data contracts, declared quality expectations, GDPR-compliant pseudonymisation — and open so others can extend it.

The project will be on GitHub. The architecture decisions, including how the GDPR–GCP retention conflict was resolved, will be documented as ADRs.

---

Three questions I am genuinely curious about — and where I expect to be corrected:

**1.** If you work in rare disease research or clinical operations: how does mutation-to-eligibility matching actually happen at your organisation today? Is there a governed system, or is it a researcher with a spreadsheet and a database tab open?

**2.** For those who've worked in or alongside embedded AI or data science teams in life sciences: how long before the specialist became genuinely productive for the domain scientist? And what was the actual translation bottleneck — the biology, the regulatory constraints, or the data model?

**3.** MatchMiner reduced time-to-consent by 22% in oncology. Has anyone built the equivalent for a monogenic rare disease — where the eligibility rule is simpler but the registries more fragmented and the patient populations smaller? I have not found a published example and would genuinely like to know if I am wrong.

If this resonates — or if any of it deserves pushing back — send me a DM. I'll share the full technical one-pager: the data model, the regulatory conflict resolutions, and the architecture decisions behind it at present.

---

#RareDisease #DataEngineering #PrecisionMedicine
