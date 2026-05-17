# Positioning Synapse Data

## The Problem

The pharma and biotech industry is investing heavily in AI, yet [68% of technology executives say weak data quality and governance is the primary reason those investments fail](https://www.zs.com/insights/scaling-ai-in-pharma-cdio-2026), not the algorithms. The bottleneck is upstream: data that is fragmented, poorly governed, and modelled without scientific literacy that no AI system can reliably consume.

The root cause is structural. Biomedical data spans clinical notes, electronic health records, genetic sequencing, imaging, and regulatory submissions.  A technically correct pipeline built without deep scientific understanding produces biologically meaningless results. The regulatory exposure is real: data integrity violations appear in [79% of FDA GMP warning letters](https://www.astrixinc.com/blog/trends-in-fda-data-integrity-483s-and-warning-letters-for-pharmaceutical-companies/). 

This plays out differently depending on organization size, but the underlying gap is the same: people who understand both the biology and the engineering are genuinely scarce. [49% of pharma professionals identify the skills gap as the single biggest barrier to digital transformation and people that have deep pharmaceutical knowledge and AI skills are in particularly short supply.](https://intuitionlabs.ai/articles/pharma-ai-skills-gap) Large pharma accumulates deep expertise in siloed departments (Discovery, Translational Science, Clinical, RWE), but [integrating data across those silos is where value is created and where it is currently lost.](https://pmc.ncbi.nlm.nih.gov/articles/PMC8025897/) Smaller biotech cannot staff all of those competencies at once  and [startups in particular are challenged to compete with the salary and benefit packages of tech giants, because of the high demand of AI and data skills across the industry.](https://intuitionlabs.ai/articles/pharma-ai-skills-gap). [The skills gap is also indirectly exacerbated by regulatory complexity, which puts additional demands on practitioners to properly document and audit their ML models in a GMP environment.](https://intuitionlabs.ai/articles/pharma-ai-skills-gap)


## Vision

A life science industry where biomedical data connects as fluently as synapses in the nervous system.

## Mission

Biomedical data pipelines fail not because the engineering is wrong, but because the science is. Synapse Data's mission is to close that gap: building AI-ready biomedical data infrastructure where scientific reasoning is present at every level: in the data models, the pipelines, the clinical standards, and the governance and not just as advisory input handed to engineers, but as the capability doing the work. Executed on Databricks, a [data platform widely adopted in pharma](https://intuitionlabs.ai/articles/pharma-data-lakehouse-databricks-snowflake-iceberg/) for complex, high-volume analytical workloads.

## Why Synapse Data

The rarest thing in biomedical data is not tooling or budget. It is a person who can reason through a clinical data modelling decision with a biostatistician, implement the resulting pipeline correctly, and defend its regulatory traceability to a compliance team. That combination almost never exists in a single role. The result is what the problem statement describes: technically correct pipelines that encode wrong domain assumptions, AI systems trained on data that answers the wrong questions.

Synapse Data is built around making that capability available. A founder with a PhD in Life Sciences (Paris-Saclay), a master's in Biophysics (KU Leuven), and a postgraduate in Applied AI (EhB), combined with hands-on data engineering and product ownership in industry, means scientific reasoning is present at implementation level and not in an advisory layer above the engineers. Concretely: this is the difference between a data model that happens to store OMOP fields and one designed by someone who understands why a given clinical concept maps the way it does. Or between a federated pipeline spec and one that will actually hold under the data governance constraints of a multi-site research consortium.

As a reference implementation, Synapse Data is building an open-access genetic disease data mesh for Duchenne Muscular Dystrophy:  linking mutation profiles from public variant registries to clinical trial eligibility criteria via a governed, versioned data product architecture on Databricks. This serves as both a working proof of the methodology and a conceptual foundation for the open data product line.

## Competitive Landscape: How Synapse Data fits into the overall landscape

| | Who | The gap they leave |
|---|---|---|
| **Enterprise platforms** | [Palantir Foundry](https://www.palantir.com/offerings/life-sciences/), IQVIA | Enterprise-only pricing and implementation burden; out of reach for most biotechs and mid-size pharma |
| **Large consultancies** | [Thoughtworks](https://www.thoughtworks.com/en-us/what-we-do) *(ran the [Roche data mesh](https://datameshlearning.com/blog/recap-data-mesh-days-for-life-sciences/)(https://www.thoughtworks.com/en-us/insights/blog/data-strategy/the-state-of-data-mesh-in-2026-from-hype-to-hard-won-maturity) — the reference implementation for pharma)* | Sound methodology, but large-consultancy overhead and cost; unreachable for smaller clients |
| **Mid-market life sciences IT** | [Agilisium](https://www.agilisium.com/about) | mid-market life sciences IT firms bring genuine domain knowledge but typically concentrate scientific expertise at the advisory level, with delivery done by certified engineers rather than domain scientists; model requires large embedded enterprise engagements |
| **Data platforms** | [Lifebit](https://lifebit.ai), DNAnexus, Snowflake Health Data Cloud | Purpose-built platforms — strong at what they do, but require data handover into their ecosystem; not consulting partners who build on your infrastructure and leave you owning the result |

**The position Synapse Data occupies**: None of the above solve the core problem the problem statement names, scientifically mismodelled data built by teams where the domain knowledge and the engineering capability are in different people. Mid-market life sciences IT comes closest but keeps science advisory and cannot right-size for smaller clients. Synapse Data is the answer when the bottleneck is not capacity or methodology, but the specific combination of scientific depth and engineering execution in one engagement.


## Services

Synapse Data focuses on providing excellence in the following things:
- **Data products** with quality enforcement, refresh patterns, and lineage — built to modern engineering best practices
- **Clinical standards integration** (OMOP, CDM) so data products speak the language of clinical data teams from day one
- **GenAI pipelines** for structured data extraction, designed for regulated environments
- **Data governance**: audit trails, lineage tracking, and access control designed for clinical research contexts
- **Data models** that reflect biological and clinical reality, not just storage convenience

Engagements are delivered as embedded consulting at a fixed day rate, with scope defined per project.

Synapse Data partners with established intermediary consulting agencies that hold master service agreements with large pharma clients. This positions Synapse Data as a scientific domain specialist within larger engagements, without requiring the firm to navigate enterprise procurement directly. Synapse Data offers embedded consulting engagements designing and building data products for large pharma companies, Series A/B rare disease biotechs, Mid-size pharma data teams (50–500 person companies) and Academic spin-outs and university hospitals building research data platforms. 


**European focus**: Synapse Data operates from Belgium, at the centre of European pharma and biotech: Roche (Basel), Novartis (Basel), UCB (Brussels), Janssen (Beerse), and a dense cluster of rare disease biotechs across Belgium, the Netherlands, and Switzerland are within direct reach. This is a structural advantage over US-based competitors. It also means operating natively within the EU regulatory environment: GDPR is an architectural constraint the firm designs around from the start, not a compliance checkbox applied after the fact. The EU AI Act, which introduces mandatory transparency, human oversight, and conformity requirements for AI systems used in high-risk contexts including healthcare, is a domain Synapse Data is positioned to navigate as a practitioner, meaning clients receive pipelines that are designed to pass conformity review from the start, not retrofitted after deployment.

## Data Products

Beyond consulting, Synapse Data is building a line of open-source data products distributed via the [Databricks Marketplace](https://www.databricks.com/product/marketplace) and API access,  reference implementations of the data infrastructure problems pharma faces most often: OMOP-standardized disease and genetic datasets, FAIR-compliant data product templates, and quality-enforced reference data for common biomedical entities.


