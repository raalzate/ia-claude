"""Pytest config + fixtures for Kata 1 (Agentic Loop & Deterministic Control).

Why this lives here, not at repo root:
- Each kata is delivered vertically (Constitution §Development Workflow / FDD).
  Sharing a root conftest would leak fixtures across katas and erode isolation
  (Principle IV — Subagent Isolation, applied by analogy to test scopes).
- pytest-bdd resolves `.feature` files relative to the test file's directory,
  so we declare `features_base_dir` here once and let every step-def module
  inherit it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import scenarios as _bdd_scenarios  # re-exported for clarity

# Where the .feature files live for this kata. pytest-bdd reads `bdd_features_base_dir`
# from a config option; we expose it as a fixture too for tests that resolve paths
# explicitly.
FEATURES_DIR = Path(__file__).parent / "features"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_bdd_apply_tag(tag: str, function):  # noqa: D401, ARG001
    """Allow scenario tags through unchanged.

    Why: the .feature files carry traceability tags like @TS-001, @FR-001. The
    default pytest-bdd handler treats unknown tags as pytest markers, which
    raises under `--strict-markers`. We register them as no-op markers via the
    pytest config below.
    """
    return None


def pytest_configure(config):
    """Register scenario tags as pytest markers.

    Why: tasks.md mandates traceability tags on every scenario; without
    registering them as markers, pytest with `--strict-markers` fails to
    collect.
    """
    for tag in ("US-001", "US-002", "US-003"):
        config.addinivalue_line("markers", f"{tag}: user-story scope tag")
    for prefix in ("TS", "FR", "SC"):
        for n in range(1, 100):
            config.addinivalue_line(
                "markers", f"{prefix}-{n:03d}: traceability tag from spec"
            )
    for tag in ("P1", "P2", "P3", "acceptance", "contract"):
        config.addinivalue_line("markers", f"{tag}: scenario classification")


@pytest.fixture(scope="session")
def features_base_dir() -> Path:
    """Directory pytest-bdd loads `.feature` files from for this kata."""
    return FEATURES_DIR


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Directory of recorded API session fixtures consumed by RecordedClient."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def load_session_fixture():
    """Return a loader that reads a recorded session fixture by short name.

    Why a fixture and not a top-level helper: keeping the path resolution under
    a fixture makes test isolation explicit — every test acquires a fresh
    handle, no module-level mutable state.
    """

    def _loader(name: str) -> dict:
        path = FIXTURES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"recorded fixture missing: {path}")
        return json.loads(path.read_text())

    return _loader


@pytest.fixture(scope="session")
def load_contract_schema():
    """Return a loader that reads a JSON Schema from `specs/.../contracts/`.

    Why this lives in conftest, not in the kata source: schemas are an external
    contract used in tests for validation; production code has its own pydantic
    models. Tests load the JSON Schema to assert shape compliance independently.
    """
    contracts_dir = (
        Path(__file__).resolve().parents[3]
        / "specs"
        / "001-agentic-loop"
        / "contracts"
    )

    def _loader(name: str) -> dict:
        path = contracts_dir / name
        if not path.exists():
            raise FileNotFoundError(f"contract schema missing: {path}")
        return json.loads(path.read_text())

    return _loader


__all__ = ["_bdd_scenarios", "FEATURES_DIR", "FIXTURES_DIR"]
