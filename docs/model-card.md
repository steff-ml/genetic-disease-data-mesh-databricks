# Model Card

A model card documents the purpose, behaviour, limitations, and responsible use of an AI model. This card follows the structure proposed by Mitchell et al. (2019) and is adapted for the EU AI Act context.

**Reference:** Mitchell, M. et al. (2019). Model Cards for Model Reporting. *FAccT*. [doi:10.1145/3287560.3287596](https://doi.org/10.1145/3287560.3287596)

---

## Model Details

| Field | Value |
|-------|-------|
| Model name | _(e.g. GPT-4o / Claude 3.5 Sonnet / Llama 3)_ |
| Model version | _(e.g. gpt-4o-2024-08-06)_ |
| Model type | _(e.g. Large Language Model — text in, structured data out)_ |
| Provider | _(e.g. OpenAI / Anthropic / Meta)_ |
| Access method | _(e.g. API / self-hosted)_ |
| Maintained by | _(team or person responsible for this deployment)_ |
| Last reviewed | _(date)_ |

### Prompt

The system prompt and any few-shot examples used to condition the model's behaviour are maintained in _(e.g. `src/prompts/` / a linked config file)_. Changes to the prompt constitute a new model configuration and should be versioned accordingly.

---

## Intended Use

**Primary use case:** _(e.g. Extracting structured genetic disease information — such as gene–disease associations, variant classifications, and phenotype descriptions — from unstructured text sources such as scientific literature and clinical reports.)_

**Intended users:** _(e.g. Data engineers and curators working on the genetic disease data mesh.)_

**Deployment context:** _(e.g. Runs as part of an automated ingestion pipeline on Databricks. All outputs are reviewed by a human curator before being promoted to a validated data product.)_

---

## Out-of-Scope Use

This model should **not** be used for:

- **Clinical decision support** — outputs are not validated for diagnostic or treatment decisions.
- **Direct patient-facing applications** — the model has not been evaluated in a clinical setting.
- **Legal or regulatory determinations** — variant classifications produced by the model require expert review before any regulatory use.
- _(Add any domain-specific exclusions here.)_

---

## Inputs and Outputs

| | Description | Example |
|-|-------------|---------|
| **Input** | _(e.g. Free-text paragraph from a scientific paper or clinical record)_ | _"Mutations in BRCA1 are associated with hereditary breast and ovarian cancer..."_ |
| **Output** | _(e.g. JSON object with extracted gene, disease, variant, and evidence fields)_ | `{ "gene": "BRCA1", "disease": "Hereditary breast cancer", ... }` |

---

## Training Data

This model uses a pre-trained foundation model and has **not been fine-tuned** on project-specific data. Its behaviour is shaped exclusively through prompting and few-shot examples.

If fine-tuning is introduced in future, this section will document:
- The dataset used for fine-tuning
- Its size, sources, and date range
- Any filtering or curation steps applied

---

## Evaluation Results

Performance is assessed against a human-curated gold standard dataset of _(N)_ examples.

| Metric | Value | Notes |
|--------|-------|-------|
| Precision | _(e.g. 0.91)_ | _(field or task scope)_ |
| Recall | _(e.g. 0.87)_ | _(field or task scope)_ |
| F1 score | _(e.g. 0.89)_ | — |
| Hallucination rate | _(e.g. 3.2%)_ | _(cases where model fabricated a value not in the source text)_ |

Evaluations are re-run whenever the model version or prompt changes. Results are stored in _(e.g. `eval/results/`)_.

---

## Limitations

- **Knowledge cutoff:** The foundation model has a training cutoff date. Newly described genes, variants, or diseases may not be recognised correctly.
- **Rare entities:** Performance degrades for very rare diseases or genes with limited representation in the training data.
- **Ambiguity:** When source text is ambiguous, the model may resolve ambiguity incorrectly and with apparent confidence.
- **Language:** Evaluated on English-language sources only. Performance on other languages is unknown.
- _(Add any observed failure modes specific to this deployment.)_

---

## Bias and Fairness Considerations

Genetic databases and scientific literature are known to underrepresent certain populations, particularly non-European ancestries. The model's outputs will reflect these biases in the source material. Specifically:

- Variant frequency estimates may not generalise across all populations.
- Disease associations derived predominantly from WEIRD (Western, Educated, Industrialised, Rich, Democratic) cohorts may not apply universally.

Users should interpret outputs with awareness of these limitations.

---

## Human Oversight

Given the sensitivity of genetic health data, this model operates under the following oversight requirements:

| Stage | Human Review Required? |
|-------|----------------------|
| Ingestion pipeline output | Yes — curator spot-check |
| Promotion to validated data product | Yes — mandatory sign-off |
| Direct use in research publication | Yes — independent expert review |

The model is classified as a **human-in-the-loop** system. No output is treated as ground truth without human review.

---

## EU AI Act Classification

| Field | Assessment |
|-------|-----------|
| Risk category | _(e.g. High-risk / Limited-risk — to be confirmed with legal)_ |
| Rationale | _(e.g. Used in a health-related data pipeline; outputs may inform downstream medical research)_ |
| Obligations triggered | _(e.g. Transparency, human oversight, logging, conformity assessment — pending legal review)_ |
| Compliance status | _(e.g. Under assessment)_ |

**Note:** EU AI Act classification should be confirmed with a legal or compliance team before deployment in a production context.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 0.1 | _(date)_ | Initial model card draft |
