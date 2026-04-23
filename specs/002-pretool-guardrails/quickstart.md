# Kata 2 — Quickstart

## What you'll build

A Python module that makes the refund policy physically unbypassable at the
tool-dispatch boundary: a `PreToolUseHook` inspects every `process_refund`
invocation, validates the payload against a pydantic schema, compares the
amount against an externally-configured limit, and returns a **structured
error** into the model's next context window on reject — never free-text.
Zero external API calls escape on a reject; the refund API stub's call log
stays empty. The policy limit lives in `config/policy.json`, never in the
system prompt, and that absence is enforced by an AST lint.

## Prerequisites

- Python 3.11+
- `uv` or `pip` for dependency install
- An Anthropic API key in `ANTHROPIC_API_KEY` — **only** needed when running
  against the live SDK; the default test run uses recorded fixtures.

## Install

```bash
# From repo root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # pyproject.toml declares anthropic, pydantic, pytest, pytest-bdd
```

## Seed the policy file

```bash
mkdir -p config
cat > config/policy.json <<'JSON'
{
  "policy_id": "refund-policy",
  "policy_snapshot_version": "v1",
  "max_refund": "500.00",
  "comparison_stance": "strict_less_than",
  "escalation_pathway": "refund-review-queue",
  "effective_from": "2026-04-23T00:00:00Z"
}
JSON
```

## Run the kata against recorded fixtures (default — no API key needed)

```bash
pytest tests/katas/002_pretool_guardrails -v
```

You should see:
- the Gherkin `pretool_guardrails.feature` scenarios pass,
- the AST lint `tests/katas/002_pretool_guardrails/lint/test_prompt_has_no_limit.py`
  pass (proving `katas/002_pretool_guardrails/prompts.py` contains no
  numeric literal equal to the current `PolicyConfig.max_refund`),
- the AST lint `test_no_float_in_amount_path.py` pass (proving the amount
  path uses `decimal.Decimal`),
- all unit tests pass.

## Run the kata against the live API

```bash
LIVE_API=1 python -m katas.002_pretool_guardrails.runner \
  --model claude-opus-4-7 \
  --prompt "Process a refund of \$750 for customer C-42." \
  --policy config/policy.json
```

Expected with `max_refund="500.00"`:
- no line appears in `runs/<session-id>/refund_api_calls.jsonl`,
- `runs/<session-id>/events.jsonl` contains one `verdict` record with
  `verdict="reject"`, `reason_code="policy_breach"`, plus one `escalation`
  record with `escalation_reason="policy_breach"`,
- the model's next turn (visible in the transcript) acknowledges the
  structured error and routes the user to the escalation pathway.

## Verify zero-call & structured-error properties from the logs

```bash
# SC-002: zero API calls on rejected invocations
test ! -s runs/<session-id>/refund_api_calls.jsonl && echo "OK: SC-002 holds"

# SC-003: every reject has a corresponding structured_error in context
jq -c 'select(.kind=="verdict" and .verdict=="reject")' \
  runs/<session-id>/events.jsonl

# FR-009: correlation_id joins invocation → verdict → (escalation)
jq -c 'group_by(.correlation_id) | map({cid: .[0].correlation_id, kinds: map(.kind)})' \
  runs/<session-id>/events.jsonl
```

## Scenario → spec mapping (every P1/P2/P3 scenario and every edge case)

| Scenario | Priority / Spec ID | Fixture | Expected verdict |
|----------|--------------------|---------|------------------|
| Refund amount strictly below limit reaches the API | P1 — US1-AS1 | `within_limit.json` | `allow`; one line in `refund_api_calls.jsonl`; FR-001, FR-006, SC-001 |
| Success outcome is derived from the API response, not a hook stub | P1 — US1-AS2 | `within_limit.json` | success message has `source="refund_api_stub"` |
| Amount strictly above limit blocks pre-API | P2 — US2-AS1 | `over_limit.json` | `reject/policy_breach`; zero API calls; FR-004, FR-006, SC-001, SC-002 |
| Reject surfaces a structured error into the model's context | P2 — US2-AS2 | `over_limit.json` | `StructuredError` validates `structured-error.schema.json`; FR-003, FR-005, SC-003 |
| Same over-limit retry yields identical verdict | P2 — US2-AS3 | `retry_same_over_limit.json` | byte-equal `HookVerdict` (minus `evaluated_at`); FR-010 |
| Over-limit blocked even when prompt contains no dollar limit | P2 — US2-AS4 | `over_limit.json` + AST lint | AST lint passes (no numeric literal matching `max_refund` in `prompts.py`); FR-008 |
| Policy change from L1 to L2 takes effect on next call | P3 — US3-AS1..AS3 | `policy_change_before.json` + `policy_change_after.json` | amount A: allow under L1, reject under L2; SC-004 |
| Policy change requires no prompt edit, schema edit, or redeploy | P3 — US3-AS3 | diff of git tree between before/after | no changes outside `config/policy.json`; FR-011 |
| Missing amount field | Edge #1 | `missing_amount.json` | `reject/schema_violation`, `field="amount"`, `rule_violated="required"` |
| Non-numeric amount ("five hundred") | Edge #2 | `non_numeric_amount.json` | `reject/schema_violation`, `rule_violated="decimal_type"` |
| Negative amount (e.g. -100) | Edge #3 | `negative_amount.json` | `reject/schema_violation`, `rule_violated="positive_decimal"` |
| Amount exactly at the limit | Edge #4 | `at_limit.json` | `reject/policy_breach` (strict_less_than stance, D-008) |
| Hook itself raises (corrupt policy file) | Edge #5 | `hook_failure_corrupt_policy.json` | `reject/hook_failure`, fail-closed, zero API calls; FR-012 |
| Payload with extra fields | Edge #6 | `extra_fields.json` | `reject/schema_violation` (pydantic `extra="forbid"`) |
| Concurrent policy update mid-invocation | Edge #7 | `concurrent_policy_update.json` | verdict and escalation record the snapshot version that was pinned at entry |

## What "done" looks like (per Constitution §Kata Completion Standards)

- [ ] `spec.md`, `plan.md`, `tasks.md`, `.feature` file all exist — plan done; testify + tasks next.
- [ ] Acceptance scenarios cover both the stated objective AND the stated anti-pattern — US1 (objective), US2-AS4 + AST lint (anti-pattern).
- [ ] Automated evaluation harness uses signal-level assertions — `HookVerdict` schema conformance, `refund_api_calls.jsonl` line count, `StructuredError` schema validation, escalation record presence — not string matching over model output.
- [ ] Anti-pattern test fails closed when the behavior is reintroduced — `test_prompt_has_no_limit.py` fails if the limit migrates into the prompt; removing the hook causes `test_hook_verdict_over_limit.py` + SC-002 stub-call assertion to fail.
- [ ] Assertion-integrity hashes in `.specify/context.json` match the locked test set — generated by `/iikit-04-testify`.
- [ ] Per-kata `README.md` with objective / walkthrough / anti-pattern defense / run instructions / reflection — written during `/iikit-07-implement`.
- [ ] Every non-trivial hook, schema, and control-flow branch carries a *why* comment tied to this kata's anti-pattern — enforced at implement review.
- [ ] Reflection note records the observed failure mode: "the model agreed not to refund >\$500 five times; the sixth time it paraphrased and refunded anyway — that was the prompt-only anti-pattern the hook now prevents."

## Reflection prompts (answered at implement time)

- Where in the source tree is the number `500` allowed to appear, and where is
  it forbidden? How does the AST lint police that boundary?
- When the hook fails internally (corrupt policy file), why does the system
  fail *closed* rather than *open*, and which principle dictates the choice?
- If Compliance needs to tighten the limit to \$250 tomorrow at 09:00, which
  exact file do they edit and what happens at 09:01 with zero redeploys?
