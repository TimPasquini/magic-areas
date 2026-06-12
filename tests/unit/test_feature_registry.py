"""Tests for FeatureRegistry behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import voluptuous as vol
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.area_state import AreaType, META_AREA_GLOBAL
from custom_components.magic_areas.components import MagicAreasConfigEntry
from custom_components.magic_areas.config_keys.area import CONF_TYPE
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.runtime_model import (
    AreaConfig,
    AreaRuntime,
    EntityReferences,
    ManagedSurface,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import FeatureConfigStep
from custom_components.magic_areas.features.registry import FeatureRegistry


@dataclass(slots=True)
class DummyModule:
    """Simple FeatureModule test double."""

    id: MagicAreasFeatures
    domains: set[str]
    enabled: bool = True
    deps: set[MagicAreasFeatures] = field(default_factory=set)
    supports_regular_area: bool = True
    supports_meta_area: bool = True
    supports_global_meta_area: bool = True
    configurable_on_meta: bool = True
    configurable_on_global_meta: bool = True
    schema: vol.Schema | None = None

    def config_schema(self) -> vol.Schema | None:  # pragma: no cover - not used
        """Return the config schema for this feature."""
        return self.schema

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

    def desired_managed_surfaces(  # pragma: no cover
        self, *_args: object, **_kwargs: object
    ) -> list[ManagedSurface]:
        """Return managed surfaces for this feature."""
        return []

    def attach_listeners(  # pragma: no cover
        self, *_args: object, **_kwargs: object
    ) -> None:
        """Attach listeners for this feature."""
        return None

    def config_flow_steps(self) -> list[FeatureConfigStep]:  # pragma: no cover - not used
        """Return config flow steps for this feature."""
        return []


def _build_magic_areas_data() -> MagicAreasData:
    """Create a minimal typed snapshot for registry tests."""
    area_config = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=MagicMock(spec=MagicAreasConfigEntry),
    )
    return MagicAreasData(
        entities={},
        magic_entities={},
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features=set(),
        feature_configs={},
        group_registry=GroupRegistry(),
        entity_references=EntityReferences(),
        area_config=area_config,
        area_runtime=AreaRuntime(),
        updated_at=datetime.now(),
    )


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

    assert registry.enabled_modules(_build_magic_areas_data()) == [enabled_module]


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
        registry.validate_dependencies(_build_magic_areas_data())

    assert "missing dependencies" in caplog.text
    assert MagicAreasFeatures.AGGREGATES.value in caplog.text


def test_available_features_for_area_respects_support_flags() -> None:
    """Available feature list should respect regular/meta/global support flags."""
    regular_only = DummyModule(
        id=MagicAreasFeatures.PRESENCE_HOLD,
        domains={"switch"},
        supports_meta_area=False,
        supports_global_meta_area=False,
    )
    meta_only = DummyModule(
        id=MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
        domains={"media_player"},
        supports_regular_area=False,
    )
    all_areas = DummyModule(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"sensor"},
    )
    registry = FeatureRegistry([regular_only, meta_only, all_areas])

    regular_area = SimpleNamespace(config={CONF_TYPE: AreaType.INTERIOR}, id="kitchen")
    meta_area = SimpleNamespace(config={CONF_TYPE: AreaType.META}, id="interior")
    global_meta = SimpleNamespace(
        config={CONF_TYPE: AreaType.META}, id=META_AREA_GLOBAL.lower()
    )

    assert registry.available_features_for_area(regular_area) == [
        MagicAreasFeatures.PRESENCE_HOLD,
        MagicAreasFeatures.AGGREGATES,
    ]
    assert registry.available_features_for_area(meta_area) == [
        MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
        MagicAreasFeatures.AGGREGATES,
    ]
    assert registry.available_features_for_area(global_meta) == [
        MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
        MagicAreasFeatures.AGGREGATES,
    ]


def test_configurable_features_for_area_respects_meta_configurability() -> None:
    """Configurable features should drop non-configurable meta features."""
    regular_and_meta = DummyModule(
        id=MagicAreasFeatures.CLIMATE_CONTROL,
        domains={"switch"},
        supports_meta_area=True,
        configurable_on_meta=True,
        schema=vol.Schema({}),
    )
    meta_not_configurable = DummyModule(
        id=MagicAreasFeatures.LIGHT_GROUPS,
        domains={"light"},
        supports_meta_area=True,
        configurable_on_meta=False,
        schema=vol.Schema({}),
    )
    no_schema = DummyModule(
        id=MagicAreasFeatures.HEALTH,
        domains={"binary_sensor"},
    )
    registry = FeatureRegistry([regular_and_meta, meta_not_configurable, no_schema])

    regular_area = SimpleNamespace(config={CONF_TYPE: AreaType.INTERIOR}, id="kitchen")
    meta_area = SimpleNamespace(config={CONF_TYPE: AreaType.META}, id="interior")

    assert registry.configurable_features_for_area(regular_area) == [
        MagicAreasFeatures.CLIMATE_CONTROL,
        MagicAreasFeatures.LIGHT_GROUPS,
    ]
    assert registry.configurable_features_for_area(meta_area) == [
        MagicAreasFeatures.CLIMATE_CONTROL,
    ]
