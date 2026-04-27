"""``PolicyConfig`` loader — fresh read from disk on every call.

Why per-invocation reload (FR-011, SC-004):
    US3's whole point is that *the limit is data, not code*. A change to
    ``config/policy.json`` must take effect on the next invocation with
    zero redeploy / zero prompt edit / zero schema edit. The simplest way
    to guarantee that is to reload the file on each call — no cache, no
    watch handle, no in-process mutable state. The ``test_policy_change_takes_effect``
    suite asserts the new limit is observed within one invocation.

Why a distinct exception class:
    FR-012 (fail closed) requires the hook to translate "I cannot read the
    policy file" into ``HookVerdict(reject, hook_failure)`` — distinct from
    ``policy_breach`` and ``schema_violation``. ``PolicyLoadError`` is the
    single exception the hook's ``try/except`` looks for; any other raise
    is unexpected and also routes to ``hook_failure``, but ``PolicyLoadError``
    is the documented contract for "the file is missing or malformed."
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from .models import PolicyConfig

DEFAULT_POLICY_PATH = Path("config") / "policy.json"
"""Default location relative to the repository root."""


class PolicyLoadError(Exception):
    """Raised when ``config/policy.json`` cannot be read or parsed.

    Why distinct: the hook fails closed by mapping this exception to
    ``ReasonCode.HOOK_FAILURE``. Any other exception during evaluation also
    fails closed, but this class makes the *expected* fail-closed path
    explicit and testable (see ``test_hook_failure_failsafe.py``).
    """


def load_policy(path: str | Path | None = None) -> PolicyConfig:
    """Read ``policy.json`` and return a frozen ``PolicyConfig`` instance.

    Args:
        path: Override the default ``config/policy.json`` path; the test
            suite passes a per-test snapshot here so it can mutate it
            without disturbing the repo seed.

    Returns:
        A new ``PolicyConfig`` instance — the caller MUST NOT cache it
        across invocations (FR-011).

    Raises:
        PolicyLoadError: when the file is missing, unreadable, malformed
            JSON, or fails the pydantic schema. Wrapping is intentional:
            the hook's ``except`` clause matches one type, not three.
    """
    target = Path(path) if path is not None else DEFAULT_POLICY_PATH
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyLoadError(f"policy file unreadable: {target}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"policy file is not valid JSON: {target}") from exc
    if not isinstance(data, dict):
        raise PolicyLoadError(f"policy root must be a JSON object: {target}")
    # Coerce Decimal-safe strings into Decimal *before* pydantic validation
    # — the JSON Schema mirrors require strings, but the pydantic model uses
    # Decimal natively. Any other shape (number, bool) falls through and is
    # rejected by the validators on PolicyConfig.
    if isinstance(data.get("max_refund"), str):
        try:
            data["max_refund"] = Decimal(data["max_refund"])
        except Exception as exc:  # pragma: no cover — caught below
            raw = data["max_refund"]
            raise PolicyLoadError(f"max_refund is not a valid decimal: {raw}") from exc
    try:
        return PolicyConfig.model_validate(data)
    except ValidationError as exc:
        raise PolicyLoadError(f"policy file failed schema validation: {exc}") from exc
