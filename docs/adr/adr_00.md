# ADR-00: Use of AI in This Project

Back to [ADR Decision Sequencing Framework](adr_decision_sequencing_framework.md)

**Status:** Working Decision
**Author:** Steff Horemans
**Date:** 2026-04-11
**Depends on:** Nothing — this is an independent governance decision
**Blocks:** Development workflow, PR process, documentation strategy

---

## Knowledge Required

**Productivity research**

The empirical evidence on AI coding assistance is mixed and context-dependent. Productivity gains are most consistent for less experienced developers and developers under high workload. Experienced developers may be slower when using AI assistance while perceiving themselves as faster — a gap that increases the risk of overconfidence. The most comprehensive field study (Cui et al., MIT 2025) shows a 10–30% increase in developer effectiveness in production settings. The rate of model improvement makes these figures unstable over time; re-evaluation is warranted at major model releases.

**Cognitive and skill effects**

AI assistance can degrade the development of coding skills, particularly when used for task delegation rather than explanation. Research shows that higher confidence in AI relative to one's own judgment correlates with reduced critical thinking — developers are less likely to verify AI output, less prepared to handle exceptions, and prone to overestimating their own ability. Automation and offloading of reasoning are identified as the primary mechanisms of skill erosion.

**Burnout and employment effects**

Time saved by AI is frequently absorbed by organisational inefficiency rather than relieved workload. Developer frustration with "almost right" AI code is a documented stressor distinct from traditional debugging. High-volume agentic AI use has been associated with severe exhaustion. Entry-level tech employment has begun to decline, raising questions about the sustainability of skipping foundational coding experience.

**Security risks**

AI-generated code introduces security vulnerabilities at a measurable rate. Fu et al. (ACM TOSEM 2025) found that 29.5% of Copilot-generated Python snippets in real GitHub repositories contained security weaknesses across 38 CWE categories. Spracklen et al. (arXiv 2024) found that 5–21% of AI-suggested package names are hallucinated and exploitable for supply chain attacks. These findings directly inform the decision not to delegate security-critical logic to AI generation.

**AI provider economics**

Provider pricing models are unstable. Billing shifts (per-request to token-based), API throttling for commercial reasons, undisclosed model quality changes, and competitive entry into adjacent markets have all been documented at major providers. Long-term dependency on a single provider carries reliability risk that must be managed through architecture rather than trust.

---

## References

**Empirical research**
- Peng et al. (2023), *GitHub Copilot's Effect on Developer Productivity* — [arXiv:2302.06590](https://arxiv.org/pdf/2302.06590) — significant productivity gains for less experienced and high-workload developers
- Weidinger et al. (2025), *Experienced developers slower with AI* — [arXiv:2507.09089](https://arxiv.org/pdf/2507.09089) — experienced developers slower but perceiving themselves as faster
- Cui et al. (2025, MIT), *Generative AI and Developer Effectiveness* — [MIT Economics working paper](https://economics.mit.edu/sites/default/files/inline-files/draft_copilot_experiments.pdf) — 10–30% increase in developer effectiveness in production
- Al-Kaswan et al. (2025), *AI and coding skill development* — [arXiv:2601.20245](https://arxiv.org/html/2601.20245v1) — skill degradation when AI is used for delegation; interaction patterns that preserve learning
- Lee et al. (2025, Microsoft Research), *AI and critical thinking* — [Microsoft Research](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/01/lee_2025_ai_critical_thinking_survey.pdf) — overconfidence in AI reduces critical thinking
- Kosmyna et al. (2025), *Cognitive offloading and AI* — [PMC11239631](https://pmc.ncbi.nlm.nih.gov/articles/PMC11239631/) — skill erosion and overconfidence as mechanisms of cognitive atrophy
- Atlassian Developer Experience Report (2025) — [Atlassian blog](https://www.atlassian.com/blog/developer/developer-experience-report-2025) — AI time savings lost to organisational overhead; empathy gap with management
- Stack Overflow Developer Survey (2025) — [survey.stackoverflow.co/2025/ai](https://survey.stackoverflow.co/2025/ai) — developer frustration with "almost right" AI code
- Stanford Digital Economy Lab (2025), *Canaries in the Coal Mine* — [report](https://digitaleconomy.stanford.edu/app/uploads/2025/11/CanariesintheCoalMine_Nov25.pdf) — entry-level tech employment decline
- Yegge, S. (2026), *The AI Vampire* — [Medium](https://steve-yegge.medium.com/the-ai-vampire-eda6e4f07163) — exhaustion from high-volume agentic AI use
- Fu et al. (ACM TOSEM 2025) — 29.5% of Copilot-generated Python snippets in production contain security weaknesses across 38 CWE categories
- Spracklen et al. (arXiv 2024) — 5–21% of AI-suggested packages are hallucinated and exploitable for supply chain attacks
- GitHub Octoverse (2025), *The new identity of a developer* — [GitHub blog](https://github.blog/news-insights/octoverse/the-new-identity-of-a-developer-what-changes-and-what-doesnt-in-the-ai-era/) — developer identity evolution from user to strategist

**Framework**
- Anthropic AI Fluency Framework — [aifluencyframework.org](https://aifluencyframework.org) — the four-D framework (Delegate, Description, Discernment, Diligence) used to structure this decision

**Claude Code tooling**
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code)
- [Claude Code security review action](https://github.com/anthropics/claude-code-security-review)

**Model routing and local models**
- [LiteLLM model routing guide](https://medium.com/@michael.hannecke/implementing-llm-model-routing-a-practical-guide-with-ollama-and-litellm-b62c1562f50f)
- [OpenCode documentation](https://opencode.ai/docs/agents/)
- [Qwen 3.5 9B local agentic coding](https://aiproductivity.ai/news/qwen35-9b-local-agentic-coding/)

**AI git hooks and PR automation**
- [AI git hooks](https://www.deployhq.com/git/ai-git-hooks)
- [Claude Code hooks for commit automation](https://www.morphllm.com/claude-code-hooks)
- [Free AI code review on every commit](https://dev.to/shrsv/we-built-a-free-ai-code-review-that-runs-on-every-commit-ij1)

**AI-assisted documentation**
- [AI documentation from code comments](https://www.kinde.com/learn/ai-for-software-engineering/best-practice/building-ai-enhanced-documentation-from-code-comments-to-living-architecture-docs/)

---

## Decision

### Context

AI coding assistance is now ubiquitous and unavoidable in software development. The question is not whether to use it but how to use it in a way that preserves skill development, maintains clinical-grade code quality, and avoids unsustainable dependency on a single provider or model.

The primary risk of the dominant approach — AI generates, human reviews — is skill atrophy. For a project whose explicit goal is to develop and demonstrate biomedical data engineering skills, handing code generation to an AI defeats the primary purpose. A secondary risk is quality: the security vulnerability and hallucination rates documented in the literature are unacceptable for a clinical data platform.

This ADR is structured using the Anthropic AI Fluency Framework's four-D model.

### Decision

**Delegate** — reversed delegation: human codes, AI reviews

The standard approach (AI generates code, human reviews the output) is rejected for this project. The reversal is deliberate: I write the code and AI reviews it. AI assistance is permitted and encouraged for boilerplate, documentation, and code review — not for logic that I do not fully understand before it is committed.

Two AI tools are used with distinct and non-overlapping roles:

- **Qwen 3.5 9B (local, via OpenCode)**: boilerplate scaffolding and documentation generation. This model runs locally and sets the "intelligence floor" — anything it can produce reliably is fully automatable and not a skill worth optimising for.
- **Claude Code (subscription)**: architectural code review, ADR drafting, documentation updates, and PR review feedback. Used as a senior reviewer and a teaching resource, not as a coder. The goal is to extract knowledge from its feedback, not to use it as a productivity shortcut.

Everything between these two — logic, pipeline design, data modelling, eligibility rule implementation — is written by the human author.

*Exploration exemption*: exploratory notebooks in the `personal.exploration` schema are exempt from the human-codes rule. AI may generate code freely in exploration notebooks — full notebook drafts, API call patterns, data structure inspection. The hard constraint is: **exploratory notebooks are never imported, called, or referenced from production pipelines**. If logic developed in exploration belongs in production, it is rewritten by the human author using the exploration notebook as a reference. Exploratory code is a disposable learning artifact; responsibility transfers to production only when the human author rewrites and owns the logic.

---

**Description** — implementation of the review and documentation system

A `CLAUDE.md` file defines coding standards and routes Claude Code to the relevant documentation for each task type. It is versioned alongside the code.

The tooling system uses agents for documentation maintenance and boilerplate generation. Agent definitions live in `.claude/agents/`. Agents run on demand rather than interrupting the coding session.

*Documentation maintenance cluster* (`doc-sync`): invoked at the end of a session or after a significant change. Reads the git diff, identifies what changed, and routes to sub-agents: `adr-updater` (ADR status and consequence notes), `data-product-doc` (Bitol YAML contract updates when Gold schemas change), `readme-updater` (README milestone updates), `scientific-background-sync` (data model section in `scientific_background.md`).

*Ingestion stub agent* (`api-stub`): given an API documentation URL and target domain/layer/table name, generates an exploration notebook scaffolding the API calls needed to understand the data structure and quality. Run by the local Qwen 3.5 9B model via OpenCode.

*Contract drafter agent* (`contract-drafter`): given a DLT table definition, produces a Bitol YAML contract skeleton for a Gold data product.

*ADR drafter agent* (`adr-drafter`): given a topic and answers to structured questions, produces an ADR draft in the project's format.

*Supporting agents* (stubs, for later implementation): `schema-validator` checks a Delta table's actual schema against its declared Bitol contract; `quality-report` formats DLT event log expectation failures into a structured review document.

*Layer 2 — PR review (planned)*: target architecture is a GitHub Actions workflow triggered on every pull request to main, calling Qwen3.5 30B Coder via the OVH API, posting the review as a comment from a named bot account. Not yet active; Claude Code is used for ad hoc PR review in the interim.

In all cases, AI output is treated as a suggestion. The human author is the sole decision-maker on what is committed.

---

**Discernment** — knowing when AI output is wrong

Discernment is handled structurally rather than heuristically: because AI is the reviewer and not the coder, the failure mode is missed issues rather than hallucinated logic. Two failure modes are explicitly managed:

- *False confidence*: AI reviewer approves bad code. Mitigated by the human-owns-logic rule — I read every suggestion and am the sole decision-maker on what is committed. AI feedback is a second opinion, not a gate.
- *Missed vulnerabilities*: AI reviewer misses a security issue. Mitigated by the Layer 2 hook running on every PR without exception, and by never delegating security-critical logic (authentication, data access control, encryption key management) to AI generation in the first place.

The system does not attempt to detect every AI error. It assumes AI will be wrong some of the time and keeps a human accountable for the outcome.

---

**Diligence** — transparency about AI use

- This ADR and `CLAUDE.md` are committed to the repository and versioned alongside the code.
- PR descriptions note when AI review feedback was incorporated and what was accepted or rejected.
- Layer 2 review comments are posted by a named bot account so they are distinguishable from human review.
- No AI-generated code is committed without the human author having read and understood it.

### Alternatives considered

**Standard delegation** (AI generates, human reviews): faster in the short term. Rejected because it produces skill atrophy, generates security vulnerabilities at a documented rate, and defeats the project's primary goal of skill development.

**No AI use**: eliminates vendor dependency and cognitive atrophy risk. Rejected because AI review genuinely reduces the probability of quality issues reaching the main branch, and documentation assistance reduces the cost of maintaining accurate architecture documentation as the project evolves.

**Full agentic mode**: maximum velocity. Rejected. The research on burnout from high-volume agentic use (Yegge 2026) and the productivity ceiling for experienced developers (arXiv 2507.09089) do not support this approach for a long-duration project with quality requirements.

### Rationale

The reversed delegation model preserves the primary goal (skill development) while capturing the genuine value of AI assistance (review coverage, documentation quality). It accepts a speed penalty in exchange for maintained skill, reduced security risk, and sustainable pace. The security vulnerability data (Fu et al., Spracklen et al.) provides direct empirical justification for not delegating code generation in a clinical data platform context.

### Consequences

- **Speed cost**: production code is written by the human author; development velocity for the production layer is lower than a full-delegation approach. Exploratory notebooks in the personal schema are exempt — AI may generate freely there. This is accepted as the cost of maintaining skill development and production code quality.
- **Quality benefit**: every production PR receives at least one AI review and one human review before merging. No production code reaches main without the human author having read and understood it.
- **Vendor lock-in**: Claude Code is used for session-time assistance and documentation agents. The Layer 2 target architecture (Qwen3.5 30B Coder via OVH) is independent of Anthropic — when implemented, Anthropic dependency is limited to the Claude Code subscription used during development sessions. The agent cluster can be rerouted via LiteLLM to a local or alternative model if needed. This migration should be completed before the platform serves more than one active contributor.

**Evaluation criteria** — to be reviewed after three months of active development:
- Layer 2 PR review is catching issues the author missed (tracked by reviewing accepted suggestions quarterly)
- Documentation remains current with the codebase (spot-checked on each ADR review)
- No security vulnerabilities introduced by AI-generated code reach the main branch
- Personal assessment: coding skill and systems thinking feel maintained, not atrophied

If the speed cost proves prohibitive, the first adjustment is to permit AI generation for well-tested utility functions only, expanding scope incrementally as trust is established. If review quality proves insufficient, the Layer 2 model is upgraded before expanding the delegation scope.

### Compliance implications

- Transparency about AI involvement is a requirement under EU AI Act Article 13 for systems used in healthcare contexts. This ADR, the named bot account, and the PR disclosure practice satisfy that requirement for the development process.
- No AI-generated code is committed without human review — this satisfies the human oversight requirement for high-risk AI system development under EU AI Act Article 14.

### Assumptions

- Claude Code subscription remains available and the Anthropic API remains accessible for Layer 2 PR review
- The Qwen 3.5 9B model running locally via OpenCode is sufficient for boilerplate and documentation tasks without requiring API access
- GitHub Actions is available for the Layer 2 PR workflow

### Review trigger

After three months of active development, evaluate against the criteria above. Also revisit if: Anthropic changes pricing or API access materially, a second contributor joins the project, or a security vulnerability reaches the main branch despite the two-layer review system.
