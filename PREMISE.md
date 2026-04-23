# ia-claude Premise

## What

`ia-claude` is a training and reference repository that implements 20 hands-on katas (exercises) covering the full Claude Certified Architect competency set: deterministic agentic loops, guardrail hooks (PreToolUse/PostToolUse), subagent isolation, defensive structured extraction, MCP integration, Plan Mode, hierarchical CLAUDE.md memory, prefix caching, context-rot mitigation, prompt chaining, headless CI/CD reviews, few-shot calibration, self-correction, human handoff, Batch API processing, scratchpad persistence, adaptive investigation, and provenance preservation. Each kata is a self-contained, runnable module with documented objective, steps, and anti-patterns.

## Who

- Engineers preparing for the **Claude Certified Architect** credential.
- AI/Platform engineers building production agentic systems with the Claude API and Claude Agent SDK.
- Tech leads defining agent governance (hooks, MCP policies, context-engineering standards) across teams.
- Students of the maestría program using this repo as practical coursework.

## Why

LLM agents fail in production when teams rely on probabilistic text signals instead of deterministic API contracts, share context indiscriminately across subagents, or ignore context-window economics. This repo closes that gap by turning the architect-level playbook into executable katas: every exercise forces the practitioner to wire `stop_reason`-driven loops, schema-validated tool use, structured error payloads, prefix-cache-friendly prompts, and human-in-the-loop escalation patterns. Outcome: reproducible, auditable agent behavior instead of prompt-engineering folklore.

## Domain

**Domain:** Agentic AI systems engineering on the Anthropic / Claude stack.
**Methodology:** **FDD (Feature-Driven Development)** — each of the 20 katas is
modeled as one independent feature, built end-to-end (spec → plan → testify →
tasks → implement) before the next kata begins. Features are the unit of
planning, tracking, commit grouping, and documentation.
**Key terms:**
- **FDD (Feature-Driven Development)** — iterative, feature-by-feature delivery
  where each kata = one vertical feature with its own specs, tests, code, and
  docs; no horizontal layering or shared batched work across katas.
- **Agentic Loop** — `stop_reason`-driven control flow (`tool_use` → execute → append → loop; `end_turn` → stop).
- **Hooks** — `PreToolUse` / `PostToolUse` interceptors in the Claude Agent SDK for deterministic guardrails and payload normalization.
- **MCP (Model Context Protocol)** — standard for tool/server integration; surfaces `isError`, `errorCategory`, `isRetryable`.
- **Subagent Isolation** — hub-and-spoke coordinator pattern; no shared memory, only typed JSON payloads.
- **Plan Mode** — read-only Claude Code mode for safe exploration before direct execution.
- **Prefix Caching** — KV-cache reuse requiring static-prefix-first, dynamic-suffix-last prompt layout.
- **Context Rot / Softmax Dilution** — attention degradation at mid-context; mitigated by edge placement + `/compact`.
- **Prompt Chaining** — multi-pass decomposition for large audits.
- **Scratchpad** — externalized persistent memory file (`investigation-scratchpad.md`) surviving `/compact`.
- **Provenance** — claim↔source mapping preserved via typed JSON fields (`claim`, `source_url`, `source_name`, `publication_date`).

## Scope

**In scope:**
- 20 katas as individual features/modules under `specs/` (one spec per kata).
  FDD cadence: lightweight specs for all 20 are produced upfront (Build Feature
  List phase); plan/testify/tasks/implement/docs happen strictly sequentially
  per kata (Build-by-Feature phase).
- Per-kata documentation deliverables: in-code comments explaining the
  *why* of each decision, plus a physical `README.md` (or equivalent) per
  kata narrating objective, steps, anti-pattern, and observed outcomes.
- Reference implementations in Python using the Claude API and Claude Agent SDK.
- Hook scripts (`PreToolUse`, `PostToolUse`), MCP server stubs, JSON-schema tool definitions.
- Headless CI/CD review workflow example (GitHub Actions + `claude -p`).
- `CLAUDE.md` / `.claude/rules/` governance examples demonstrating hierarchical memory.
- Evaluation harness to verify each kata's success criteria (e.g. schema adherence, loop termination on `stop_reason`, cache-hit rate sanity checks).

**Out of scope:**
- Production-grade UI or customer-facing applications.
- Fine-tuning or training of base models.
- Non-Anthropic LLM providers (OpenAI, Gemini, local models) — illustrative only if referenced.
- Enterprise secrets management, multi-tenant auth, or SRE/observability beyond minimal logging needed to demonstrate a kata.
