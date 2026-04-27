"""Notebook bootstrap. See ARCHITECTURE.md.

Contract: the first code cell of every kata notebook is

    from katas._shared.bootstrap import bootstrap
    client, settings = bootstrap()

The function prompts for ANTHROPIC_API_KEY if missing, returns a wrapped
Anthropic client that enforces a per-notebook call budget, and returns
mutable Settings for the kata to override before issuing requests.
"""

from __future__ import annotations

import getpass
import os
from dataclasses import dataclass, field

from anthropic import Anthropic


DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_BUDGET_CALLS = 20


class BudgetExceeded(RuntimeError):
    """Raised when a notebook exceeds its per-session call budget."""


@dataclass
class Settings:
    """Mutable per-notebook configuration. Override before calling the API."""

    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    budget_calls: int = DEFAULT_BUDGET_CALLS
    calls_made: int = field(default=0, init=False)


class _BudgetedMessages:
    """Wrapper around `client.messages` that counts every `.create` call."""

    def __init__(self, real_messages, settings: Settings) -> None:
        self._real = real_messages
        self._settings = settings

    def create(self, **kwargs):
        if self._settings.calls_made >= self._settings.budget_calls:
            raise BudgetExceeded(
                f"budget_calls={self._settings.budget_calls} exhausted; "
                "raise settings.budget_calls if intentional"
            )
        self._settings.calls_made += 1
        kwargs.setdefault("model", self._settings.model)
        kwargs.setdefault("max_tokens", self._settings.max_tokens)
        return self._real.create(**kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)


class _BudgetedClient:
    """Anthropic client wrapper that exposes a budgeted `.messages.create`."""

    def __init__(self, real_client: Anthropic, settings: Settings) -> None:
        self._real = real_client
        self.messages = _BudgetedMessages(real_client.messages, settings)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _ensure_api_key() -> None:
    """Prompt for ANTHROPIC_API_KEY if not in env. Sets it in os.environ."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    key = getpass.getpass("ANTHROPIC_API_KEY (no se mostrará): ").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY vacía; aborto.")
    os.environ["ANTHROPIC_API_KEY"] = key


def bootstrap(
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    budget_calls: int | None = None,
) -> tuple[_BudgetedClient, Settings]:
    """Configure key + client + settings for a kata notebook.

    Args:
        model: override default model (e.g. for Sonnet/Opus katas).
        max_tokens: override default max output tokens.
        budget_calls: override default per-notebook call budget.

    Returns:
        (client, settings) — `client.messages.create(...)` is budget-guarded;
        `settings` is mutable so the notebook can adjust mid-run if needed.
    """
    _ensure_api_key()
    settings = Settings(
        model=model or DEFAULT_MODEL,
        max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
        budget_calls=budget_calls or DEFAULT_BUDGET_CALLS,
    )
    real = Anthropic()
    return _BudgetedClient(real, settings), settings
