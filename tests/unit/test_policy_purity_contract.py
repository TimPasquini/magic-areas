"""Purity contract tests for Layer 3 policy modules."""

from __future__ import annotations

import ast
from pathlib import Path


POLICY_MODULES = (
    Path("custom_components/magic_areas/core/controls/policies/fan.py"),
    Path("custom_components/magic_areas/core/controls/policies/climate.py"),
    Path("custom_components/magic_areas/core/controls/policies/media.py"),
    Path("custom_components/magic_areas/light_groups/policy.py"),
)


def _is_forbidden_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "execute_control_group_decision":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "async_call":
        return True
    return False


def test_policy_modules_do_not_call_services_or_executor() -> None:
    """Policy modules must not perform execution-layer side effects."""
    violations: list[str] = []

    for path in POLICY_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_forbidden_call(node):
                violations.append(f"{path}:{node.lineno}")

    assert violations == []
