"""Test harness for Kata 1.

Why this file exists:
    pytest-bdd needs to know where to discover ``.feature`` files for this
    kata, and the BDD steps need a couple of small loaders (recorded fixture
    sessions, JSON Schema contracts, a clean event-log path). Centralising
    those here keeps every step file thin and forces the same conventions on
    unit + step_defs + lint suites — Constitution Principle V (TDD) demands
    that the test harness itself stay deterministic.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

# Repo root resolves up from tests/katas/kata_001_agentic_loop/conftest.py
REPO_ROOT = Path(__file__).resolve().parents[3]

KATA_DIR = REPO_ROOT / "tests" / "katas" / "kata_001_agentic_loop"
FEATURES_DIR = KATA_DIR / "features"
FIXTURES_DIR = KATA_DIR / "fixtures"
CONTRACTS_DIR = REPO_ROOT / "specs" / "001-agentic-loop" / "contracts"


def load_fixture_session(name: str) -> dict:
    """Load a recorded Anthropic Messages API fixture session by short name.

    Why: tests must be byte-deterministic across runs (SC-007), so they pull
    pre-recorded responses rather than hitting the real API.
    """
    path = FIXTURES_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract_schema(name: str) -> dict:
    """Load a JSON Schema document from ``specs/001-agentic-loop/contracts/``.

    Why: schemas are the single source of truth for tool / event-log shape
    (Principle II). Tests resolve them by name to avoid path drift.
    """
    path = CONTRACTS_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def fixture_loader():
    """Expose ``load_fixture_session`` to step_defs / unit tests."""
    return load_fixture_session


@pytest.fixture
def schema_loader():
    """Expose ``load_contract_schema`` to step_defs / unit tests."""
    return load_contract_schema


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """A clean per-test ``runs/`` directory so event-log assertions are isolated."""
    target = tmp_path / "runs"
    target.mkdir()
    return target


@pytest.fixture
def session_id() -> str:
    """A stable, unique session id for the current test."""
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def _no_real_anthropic_calls(monkeypatch):
    """Block accidental real API hits during tests.

    Why: Constitution V (TDD) requires deterministic tests; an inadvertent
    network call would make the suite non-reproducible. We unset the API key
    so a misconfigured ``LiveClient`` raises instead of silently calling out.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LIVE_API", raising=False)
    yield


def pytest_configure(config) -> None:
    """Register dynamic markers used by feature-file tags.

    Why: ``--strict-markers`` is on globally; the BDD feature files carry
    tags like ``@TS-001``, ``@FR-004`` that pytest-bdd surfaces as markers.
    We register the prefixes once so the kata test suite stays strict-mode
    compatible without polluting the workshop-wide ``pyproject.toml``.
    """
    for prefix in ("US", "TS", "FR", "SC", "P"):
        for n in range(0, 100):
            config.addinivalue_line("markers", f"{prefix}-{n:03d}: feature tag")
            config.addinivalue_line("markers", f"{prefix}{n}: feature tag")
    for static in ("acceptance", "contract", "P1", "P2", "P3"):
        config.addinivalue_line("markers", f"{static}: feature tag")


def pytest_collection_modifyitems(config, items):
    """Tag scenarios so we can later filter by acceptance vs unit (SC-007)."""
    _ = config, items


def pytest_bdd_apply_tag(tag, function):
    """Allow ``@P1``/``@P2``/``@P3``/``@acceptance`` tags through unmodified."""
    _ = tag, function


# Helpers used in unit tests to build a throwaway run dir.
def make_run_dir(parent: Path) -> Path:
    """Create a fresh ``runs/<uuid>/`` under ``parent`` and return its path."""
    rid = str(uuid.uuid4())
    target = parent / rid
    target.mkdir(parents=True, exist_ok=True)
    return target


def reset_run_dir(path: Path) -> None:
    """Remove and recreate ``path`` — used between two reproducibility runs."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
