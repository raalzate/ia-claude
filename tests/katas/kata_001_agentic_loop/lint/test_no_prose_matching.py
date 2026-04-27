"""Static guard: ``loop.py`` MUST NOT do prose matching.

Why an AST lint test exists:
    The kata's whole point (Principle I) is that the loop is signal-driven.
    Without an automated guard, a future maintainer "just cleaning up" might
    re-introduce ``if "done" in text`` or ``re.search(r"complete", ...)`` and
    silently regress determinism (FR-004). This test parses the file and
    fails the build on any of those operators applied to assistant text.
"""

from __future__ import annotations

import ast
from pathlib import Path

LOOP_PATH = Path(__file__).resolve().parents[4] / "katas" / "kata_001_agentic_loop" / "loop.py"

# Method names disallowed when called on a *string* in loop.py. Empty-set
# membership against a frozenset (``in`` operator on a set) is fine; the
# lint targets ``in`` against a *string literal* and method calls on text.
_BANNED_METHODS = frozenset(
    {"find", "rfind", "index", "rindex", "search", "match", "startswith", "endswith"}
)


def _parse_loop_module() -> ast.AST:
    return ast.parse(LOOP_PATH.read_text(encoding="utf-8"), filename=str(LOOP_PATH))


def test_loop_does_not_import_re() -> None:
    """``re`` and ``regex`` are banned at module top-level."""
    tree = _parse_loop_module()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in {"re", "regex"}, (
                    f"loop.py imports forbidden module: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in {"re", "regex"}, (
                f"loop.py imports forbidden module: {node.module}"
            )


def test_loop_calls_no_banned_text_methods() -> None:
    """``.find / .index / .search / .match / .startswith / .endswith`` banned."""
    tree = _parse_loop_module()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _BANNED_METHODS:
                raise AssertionError(
                    f"loop.py calls banned text method: .{node.func.attr}() at line {node.lineno}"
                )


def test_loop_does_not_use_in_against_string_literal() -> None:
    """Forbid ``"some_substring" in some_variable`` and inverse forms."""
    tree = _parse_loop_module()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                if not isinstance(op, (ast.In, ast.NotIn)):
                    continue
                # ``"foo" in bar`` — left side is a string literal.
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    raise AssertionError(
                        f"loop.py uses 'in' against a string literal at line {node.lineno}"
                    )
                # ``bar in "foo"`` — right comparator is a string literal.
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                    raise AssertionError(
                        f"loop.py compares 'in' to a string literal at line {node.lineno}"
                    )


def test_loop_does_not_iterate_assistant_text_blocks() -> None:
    """Branching off ``Turn.assistant_text_blocks`` is forbidden.

    Why: that field is for the audit log only. Reading it inside the loop
    would resurrect the prose-matching anti-pattern even without an explicit
    string operator.
    """
    tree = _parse_loop_module()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "assistant_text_blocks":
            # ``build_turn`` populates it as a write-only field; the lint
            # rejects any *Load* context (read access).
            if isinstance(node.ctx, ast.Load):
                raise AssertionError(
                    f"loop.py reads Turn.assistant_text_blocks at line {node.lineno}"
                )
