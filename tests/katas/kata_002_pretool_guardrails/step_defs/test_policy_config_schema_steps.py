"""Step defs binding TS-019 — PolicyConfig validates against its JSON Schema."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
from pytest_bdd import given, parsers, scenario, then, when

from katas.kata_002_pretool_guardrails.policy import load_policy

from ..conftest import REPO_ROOT

CONTRACTS_DIR = REPO_ROOT / "specs" / "002-pretool-guardrails" / "contracts"
FEATURE_FILE = REPO_ROOT / "specs" / "002-pretool-guardrails" / "tests" / "features" / "contracts.feature"


@scenario(
    str(FEATURE_FILE),
    "PolicyConfig instances validate against the policy-config schema",
)
def test_ts_019_policy_config_validates() -> None:
    """Bind only TS-019 here."""


@given(
    parsers.parse("a PolicyConfig loaded from config/policy.json"),
    target_fixture="policy_object",
)
def _given_policy_object(policy_snapshotter: Path):
    return load_policy(policy_snapshotter)


@when(
    parsers.parse("the object is validated against contracts/policy-config.schema.json"),
    target_fixture="schema_validation_result",
)
def _when_validate_policy(policy_object) -> dict:
    schema = json.loads((CONTRACTS_DIR / "policy-config.schema.json").read_text())
    serialized = policy_object.model_dump(mode="json")
    serialized["max_refund"] = str(policy_object.max_refund)
    jsonschema.Draft202012Validator(schema).validate(serialized)
    return {"object": serialized, "kind": "policy_config"}


@then(parsers.parse("the object passes schema validation"))
def _then_passes(schema_validation_result: dict) -> None:
    assert schema_validation_result["object"]


@then(parsers.parse('the comparison_stance equals "{value}"'))
def _then_stance(schema_validation_result: dict, value: str) -> None:
    assert schema_validation_result["object"]["comparison_stance"] == value


@then(parsers.parse("the max_refund is a decimal-safe numeric string"))
def _then_decimal_safe(schema_validation_result: dict) -> None:
    raw = schema_validation_result["object"]["max_refund"]
    assert isinstance(raw, str)
    assert re.fullmatch(r"[0-9]+(\.[0-9]+)?", raw), f"not decimal-safe: {raw!r}"
