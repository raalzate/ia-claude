"""AST lint: hook.py / models.py / runner.py never use ``float()`` on amounts.

Why machine-enforced:
    ``float("0.1") + float("0.2") != Decimal("0.3")``. A single ``float(amount)``
    in the amount path silently turns the policy threshold check into a
    non-deterministic comparison. The lint catches it at the structural
    level — even before the test suite runs.
"""

from __future__ import annotations

import ast
from pathlib import Path

KATA_ROOT = (
    Path(__file__).resolve().parents[4] / "katas" / "kata_002_pretool_guardrails"
)
TARGET_FILES = ("hook.py", "models.py", "runner.py")


def _has_float_call_or_annotation(tree: ast.AST) -> list[str]:
    """Return human-readable descriptions of every offending node."""
    offenders: list[str] = []
    for node in ast.walk(tree):
        # ``float(...)`` call.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
            offenders.append(f"float() call at line {node.lineno}")
        # ``: float`` annotation on a function arg or assignment.
        if isinstance(node, ast.AnnAssign) and isinstance(node.annotation, ast.Name):
            if node.annotation.id == "float":
                offenders.append(f"float annotation at line {node.lineno}")
        if isinstance(node, ast.arg) and isinstance(node.annotation, ast.Name):
            if node.annotation.id == "float":
                offenders.append(f"float arg annotation at line {node.lineno}")
    return offenders


def test_amount_path_modules_have_no_float() -> None:
    """No ``float`` call or annotation in any of the three amount-path files."""
    for filename in TARGET_FILES:
        path = KATA_ROOT / filename
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        offenders = _has_float_call_or_annotation(tree)
        assert not offenders, f"float in amount path: {path.name}: {offenders}"
