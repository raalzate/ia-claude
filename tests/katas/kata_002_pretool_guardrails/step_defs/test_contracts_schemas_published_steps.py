"""Step defs for ``contracts.feature`` TS-021 (all five schemas published).

Why narrow: TS-016/17/18/19/20/22 (per-object validation) live in
``test_contracts_payloads_steps.py`` and ``test_policy_config_schema_steps.py``.
TS-021 is the directory-presence + Draft-2020-12 validity check; keeping it
in a dedicated file lets the directory listing fail loudly and early
without dragging the per-object validation harness into scope.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from pytest_bdd import given, parsers, scenario, then, when

from ..conftest import FEATURES_DIR, REPO_ROOT

CONTRACTS_DIR = REPO_ROOT / "specs" / "002-pretool-guardrails" / "contracts"


@scenario(
    str(FEATURES_DIR / "contracts.feature"),
    "All five hook boundary schemas are published under contracts/",
)
def test_ts_021_all_schemas_published() -> None:
    """Bind only TS-021 — the other contracts.feature scenarios live in T040/T050."""


@given("the feature contracts directory", target_fixture="contracts_dir")
def _given_contracts_dir() -> Path:
    return CONTRACTS_DIR


@when("the directory is inspected", target_fixture="contracts_listing")
def _when_inspect(contracts_dir: Path) -> dict[str, Path]:
    return {p.name: p for p in contracts_dir.glob("*.schema.json")}


@then(parsers.parse("it contains {filename}"))
def _then_contains_file(contracts_listing: dict[str, Path], filename: str) -> None:
    assert filename in contracts_listing, f"missing schema file: {filename}"
    schema = json.loads(contracts_listing[filename].read_text())
    # FR-013 / TS-021: every schema MUST be a valid Draft 2020-12 JSON Schema.
    Draft202012Validator.check_schema(schema)
