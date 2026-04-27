"""pytest configuration + shared fixtures for kata 2.

Why this file exists:
    pytest-bdd needs a deterministic location to discover ``.feature`` files.
    Per Constitution Principle V (Test-First Kata Delivery, NN), the
    ``.feature`` files are produced by ``/iikit-04-testify`` and live under
    ``specs/002-pretool-guardrails/tests/features/``. They MUST NOT be copied
    into the test tree (they are hash-locked by ``context.json``); instead,
    the step-definition modules below resolve their feature paths via the
    ``FEATURES_DIR`` constant exported from this module.

Real shared fixtures (``session_tmpdir``, ``policy_snapshotter``,
``stub_api_inspector``, ``audit_log_reader``) are added in T018 once the
production modules they depend on (``policy``, ``events``,
``refund_api_stub``) exist. This file is the T006 stub: it pins the feature
directory so step-definition modules authored ahead of those fixtures still
import.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
"""Absolute repo root, computed once. Step modules use this to find features."""

FEATURES_DIR = REPO_ROOT / "specs" / "002-pretool-guardrails" / "tests" / "features"
"""Canonical .feature directory — owned by /iikit-04-testify, NOT this tree."""

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
"""Recorded payload fixtures (per plan.md §Storage)."""


@pytest.fixture
def session_tmpdir(tmp_path: Path) -> Path:
    """Per-test ``runs/<session-id>/`` root.

    Why pytest's ``tmp_path``: each test gets an isolated directory so
    ``events.jsonl`` / ``refund_api_calls.jsonl`` writes from one test cannot
    leak into another, and SC-002 (zero-call assertions) stays bisectable.
    """
    return tmp_path


@pytest.fixture
def policy_snapshotter(session_tmpdir: Path) -> Path:
    """Copy the seed ``config/policy.json`` into the per-test tmpdir.

    Why a copy: tests for US3 (policy hot reload) MUST mutate the policy
    file. Mutating the repo-tracked seed would corrupt subsequent tests; the
    snapshot pattern keeps the seed read-only.
    """
    src = REPO_ROOT / "config" / "policy.json"
    dst_dir = session_tmpdir / "config"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "policy.json"
    shutil.copy2(src, dst)
    return dst


@pytest.fixture
def stub_api_inspector(session_tmpdir: Path) -> Iterator[Path]:
    """Path to ``refund_api_calls.jsonl`` for the current test session.

    Yields the path even when the file does not yet exist — SC-002 asserts
    *absence* of records on reject verdicts, so the inspector must work
    on an empty / missing file.
    """
    path = session_tmpdir / "refund_api_calls.jsonl"
    yield path


@pytest.fixture
def audit_log_reader(session_tmpdir: Path) -> Iterator[Path]:
    """Path to ``events.jsonl`` for the current test session."""
    path = session_tmpdir / "events.jsonl"
    yield path


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts; missing file → empty list."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture
def read_jsonl():
    """Expose the JSONL reader to tests as a callable fixture."""
    return _read_jsonl
