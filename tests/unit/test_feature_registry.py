"""Tests for FeatureRegistry behavior."""

from __future__ import annotations

from dataclasses import dataclass
import logging

import pytest
import voluptuous as vol
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.registry import FeatureRegistry
from custom_components.magic_areas.features.base import FeatureConfigStep


@dataclass(slots=True)
class DummyModule:
    """Simple FeatureModule test double."""

    id: MagicAreasFeatures
    domains: set[str]
    enabled: bool = True
    deps: set[MagicAreasFeatures] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Normalize optional defaults after init."""
        if self.deps is None:
            self.deps = set()

    def config_schema(self) -> vol.Schema | None:  # pragma: no cover - not used
        """Return the config schema for this feature."""
        return None

    def option_steps(self) -> list[str]:  # pragma: no cover - not used
        """Return option step identifiers for this feature."""
        return []

    def validate_config(self, config: dict) -> dict:  # pragma: no cover - not used
        """Validate and normalize config for this feature."""
        return config

    def is_enabled(self, data: object) -> bool:
        """Return whether this feature is enabled for the area."""
        return self.enabled

    def depends_on(self) -> set[MagicAreasFeatures]:
        """Return feature dependencies required for this module."""
        return set(self.deps)

    def build_entities(  # pragma: no cover
        self, *_args: object, **_kwargs: object
    ) -> list[Entity]:
        """Build entities for this feature."""
        return []

    def attach_listeners(  # pragma: no cover
        self, *_args: object, **_kwargs: object
    ) -> None:
        """Attach listeners for this feature."""
        return None

    def config_flow_steps(self) -> list[FeatureConfigStep]:  # pragma: no cover - not used
        """Return config flow steps for this feature."""
        return []


def test_modules_for_domain_filters() -> None:
    """Registry returns only modules that match a domain."""
    aggregates = DummyModule(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"sensor", "binary_sensor"},
    )
    wasp = DummyModule(
        id=MagicAreasFeatures.WASP_IN_A_BOX,
        domains={"binary_sensor"},
    )
    registry = FeatureRegistry([aggregates, wasp])

    assert registry.modules_for_domain("sensor") == [aggregates]
    assert registry.modules_for_domain("binary_sensor") == [aggregates, wasp]
    assert registry.modules_for_domain("light") == []


def test_module_for_feature_lookup() -> None:
    """Registry resolves modules by feature id."""
    aggregates = DummyModule(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"sensor"},
    )
    registry = FeatureRegistry([aggregates])

    assert registry.module_for_feature(MagicAreasFeatures.AGGREGATES) is aggregates
    assert registry.module_for_feature(MagicAreasFeatures.WASP_IN_A_BOX) is None


def test_enabled_modules_uses_module_gate() -> None:
    """Enabled modules are filtered by module.is_enabled()."""
    enabled_module = DummyModule(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"sensor"},
        enabled=True,
    )
    disabled_module = DummyModule(
        id=MagicAreasFeatures.WASP_IN_A_BOX,
        domains={"binary_sensor"},
        enabled=False,
    )
    registry = FeatureRegistry([enabled_module, disabled_module])

    assert registry.enabled_modules(object()) == [enabled_module]


def test_validate_dependencies_logs_missing(caplog: pytest.LogCaptureFixture) -> None:
    """Missing dependencies are logged for enabled modules."""
    aggregates = DummyModule(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"sensor"},
        enabled=False,
    )
    wasp = DummyModule(
        id=MagicAreasFeatures.WASP_IN_A_BOX,
        domains={"binary_sensor"},
        enabled=True,
        deps={MagicAreasFeatures.AGGREGATES},
    )
    registry = FeatureRegistry([aggregates, wasp])

    with caplog.at_level(logging.WARNING):
        registry.validate_dependencies(object())

    assert "missing dependencies" in caplog.text
    assert MagicAreasFeatures.AGGREGATES.value in caplog.text
