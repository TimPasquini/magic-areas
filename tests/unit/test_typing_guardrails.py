"""Typing guardrails for production code."""

from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "custom_components" / "magic_areas"
ALLOWED_SOURCE_TYPE_IGNORES = {
    SOURCE_ROOT / "schemas" / "selectors.py",
}
CRITICAL_TYPED_FILES = (
    SOURCE_ROOT / "config_flow.py",
    SOURCE_ROOT / "core" / "config" / "area.py",
    SOURCE_ROOT / "core" / "config" / "feature.py",
    SOURCE_ROOT / "core" / "runtime_model" / "area.py",
    SOURCE_ROOT / "features" / "modules" / "ble_trackers.py",
    SOURCE_ROOT / "features" / "modules" / "health.py",
    SOURCE_ROOT / "features" / "modules" / "light_groups.py",
    SOURCE_ROOT / "features" / "modules" / "wasp_in_a_box.py",
    SOURCE_ROOT / "features" / "registry.py",
    SOURCE_ROOT / "schemas" / "selectors.py",
)


def _python_sources() -> list[Path]:
    return sorted(path for path in SOURCE_ROOT.rglob("*.py"))


def test_production_code_does_not_use_type_ignore() -> None:
    """Keep production typing fixes explicit instead of silenced."""
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in _python_sources()
        if "type: ignore" in path.read_text()
        and path not in ALLOWED_SOURCE_TYPE_IGNORES
    ]
    assert offenders == []


def test_production_code_does_not_use_typing_cast() -> None:
    """Keep production typing fixes structural instead of assertion-based."""
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in _python_sources()
        if "cast(" in path.read_text()
    ]
    assert offenders == []


def test_critical_runtime_boundaries_do_not_fall_back_to_any() -> None:
    """Shared typed surfaces should not regress to broad Any annotations."""
    any_pattern = re.compile(r"\bAny\b")
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in CRITICAL_TYPED_FILES
        if any_pattern.search(path.read_text())
    ]
    assert offenders == []
