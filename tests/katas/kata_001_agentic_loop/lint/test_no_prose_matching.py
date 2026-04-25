"""AST lint: forbid prose-matching primitives in loop.py.

Why an AST test (not a grep) is the right shape:
- grep produces false positives on comments/strings.
- AST visits real call expressions, so the test fails ONLY on actual misuse.

Constitution Principle I (NN) and FR-004 forbid termination decisions derived
from response prose. This test is the structural guardrail: even if a future
contributor "just adds a quick `re.search`" to loop.py, this test fails the
build before the regression can land.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

LOOP_PATH = (
    Path(__file__).resolve().parents[4]
    / "katas"
    / "kata_001_agentic_loop"
    / "loop.py"
)

FORBIDDEN_IMPORTS = {"re"}
FORBIDDEN_METHOD_NAMES = {"find", "rfind", "index", "search", "match", "fullmatch"}


def _parse_loop_module() -> ast.Module:
    if not LOOP_PATH.exists():
        pytest.fail(f"loop.py not found at {LOOP_PATH}")
    return ast.parse(LOOP_PATH.read_text(encoding="utf-8"))


def test_loop_does_not_import_re() -> None:
    """`re` import in loop.py is the most direct prose-matching anti-pattern."""
    module = _parse_loop_module()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in FORBIDDEN_IMPORTS, (
                    f"loop.py imports forbidden module {alias.name!r}"
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in FORBIDDEN_IMPORTS, (
                f"loop.py does `from {node.module} import ...`"
            )


def test_loop_does_not_call_string_search_methods() -> None:
    """No .find / .search / .match / .index / .startswith / .endswith.

    The test is intentionally broad — plan.md Constraints calls for an
    'AST lint that fails loudly on regressions' covering these primitives.
    """
    module = _parse_loop_module()
    forbidden = FORBIDDEN_METHOD_NAMES | {"startswith", "endswith"}
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in forbidden, (
                f"loop.py calls forbidden string-search method "
                f"{node.func.attr!r} at line {node.lineno}"
            )


def test_loop_does_not_use_in_against_string_literal() -> None:
    """`"task complete" in <something>` is the canonical decoy-phrase check."""
    module = _parse_loop_module()
    for node in ast.walk(module):
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                if isinstance(op, (ast.In, ast.NotIn)) and isinstance(
                    node.left, ast.Constant
                ) and isinstance(node.left.value, str):
                    pytest.fail(
                        f"loop.py uses string-literal `in` membership at line "
                        f"{node.lineno}: {ast.unparse(node)}"
                    )
                # Also catch the reverse: `something in "literal"`.
                if isinstance(op, (ast.In, ast.NotIn)) and isinstance(
                    comparator, ast.Constant
                ) and isinstance(comparator.value, str):
                    pytest.fail(
                        f"loop.py uses string-literal `in` membership at line "
                        f"{node.lineno}: {ast.unparse(node)}"
                    )
