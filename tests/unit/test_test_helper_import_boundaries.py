"""Import boundaries for responsibility-focused test helpers."""

from __future__ import annotations

import ast
from pathlib import Path

TESTS_ROOT = Path(__file__).parents[1]
HELPER_FACADE = TESTS_ROOT / "helpers" / "__init__.py"


def test_test_helpers_aggregate_facade_is_not_reintroduced() -> None:
    """Tests must import concrete helper modules, never an aggregate facade."""
    violations: list[str] = []

    for path in TESTS_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "tests.helpers":
                violations.append(f"{path.relative_to(TESTS_ROOT)}:{node.lineno}")
            elif isinstance(node, ast.Import) and any(
                alias.name == "tests.helpers" for alias in node.names
            ):
                violations.append(f"{path.relative_to(TESTS_ROOT)}:{node.lineno}")

    assert not violations, (
        "Import responsibility modules under tests.helpers directly: "
        + ", ".join(violations)
    )
    assert not HELPER_FACADE.exists(), (
        "tests/helpers/__init__.py must not recreate an aggregate helper facade"
    )
