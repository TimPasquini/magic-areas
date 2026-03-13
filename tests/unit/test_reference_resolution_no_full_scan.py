"""Regression guardrails for reference resolution complexity."""

from __future__ import annotations

import inspect

from custom_components.magic_areas.core.runtime_model.references import build_entity_references


def test_build_entity_references_avoids_full_registry_scan() -> None:
    """Reference build path should not iterate every entity registry entry."""
    source = inspect.getsource(build_entity_references)
    assert "entity_registry.entities.values()" not in source
