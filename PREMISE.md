# ia-claude Premise

## What

`ia-claude` is a concept-study workshop for the **Claude Certified
Architect** credential. It covers 20 katas spanning the architect-level
syllabus: deterministic agentic loops, PreToolUse / PostToolUse hooks,
subagent isolation, defensive structured extraction, MCP error contracts,
Plan Mode, hierarchical `CLAUDE.md` memory, prefix caching, softmax
dilution mitigation, prompt chaining, headless CI/CD review, few-shot
calibration, self-correction, human handoff, Batch API, scratchpad
persistence, adaptive investigation, and provenance preservation.

Each kata ships **two artifacts**:

- `specs/<NNN-slug>/spec.md` — one-page concept brief.
- `katas/kata_NNN_<slug>/notebook.ipynb` — runnable Jupyter notebook with
  the worked example, the anti-pattern, and the certification argument.

Nothing else.

## Who

- Engineers preparing for the Claude Certified Architect credential.
- AI/Platform engineers who want to internalize the agent-engineering
  patterns without first wading through a multi-stage TDD pipeline.
- Tech leads who need a self-contained reference of the deterministic
  patterns to share with their teams.
- Maestría students using this repo as practical coursework.

## Why

LLM agents fail in production when teams rely on probabilistic text
signals instead of deterministic API contracts, share context
indiscriminately across subagents, or ignore context-window economics.
This repo closes that gap by turning the architect playbook into a
sequence of focused notebooks: each one teaches one principle, names the
anti-pattern, and arms the practitioner with the argument they would make
in a certification interview.

The previous revision of this repo wrapped the same content in a
test-first FDD ladder (specs, plans, tasks, .feature files,
assertion-integrity hashes). That scaffolding obscured the learning
objective. The current revision keeps the spec as a one-pager and the
notebook as the only deliverable.

## Domain

- **Domain:** Agentic AI systems engineering on the Anthropic / Claude
  stack.
- **Methodology:** concept-first study; one notebook per kata.
- **Key terms:** Agentic Loop, Hooks (PreToolUse / PostToolUse), MCP,
  Subagent Isolation, Plan Mode, Prefix Caching, Context Rot / Softmax
  Dilution, Prompt Chaining, Scratchpad, Provenance.

## Scope

**In scope:**

- 20 one-page specs in `specs/`.
- 20 runnable Jupyter notebooks in `katas/`, each demonstrating both the
  correct pattern and the anti-pattern.
- Reference Python snippets using the Claude API and Claude Agent SDK.
- A short top-level `specs/README.md` orienting the reader.

**Out of scope:**

- Test-first delivery, BDD scenarios, assertion-integrity hashes.
- Production-grade UI, customer applications, fine-tuning.
- Non-Anthropic LLM providers (illustrative references only).
- Multi-tenant auth, secrets management, SRE tooling.
