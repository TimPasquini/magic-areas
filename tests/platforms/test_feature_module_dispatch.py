"""Contract tests for feature module dispatch in platform setup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import FeatureConfigStep
from custom_components.magic_areas.features.registry import FeatureRegistry
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import get_basic_config_entry_data


@dataclass(slots=True)
class FeatureModuleDouble:
    """Test double for FeatureModule with observable lifecycle calls."""

    id: MagicAreasFeatures
    domains: set[str]
    entities: list[Entity]
    enabled: bool = True
    deps: set[MagicAreasFeatures] = field(default_factory=set)
    supports_regular_area: bool = True
    supports_meta_area: bool = True
    supports_global_meta_area: bool = True
    configurable_on_meta: bool = True
    configurable_on_global_meta: bool = True
    build_entities: MagicMock = field(init=False)
    attach_listeners: MagicMock = field(init=False)

    def __post_init__(self) -> None:
        """Attach callable mocks for module hooks."""
        self.build_entities = MagicMock(return_value=self.entities)
        self.attach_listeners = MagicMock()

    def config_schema(self) -> vol.Schema | None:  # pragma: no cover
        """Return the config schema for this feature."""
        return None

    def option_steps(self) -> list[str]:  # pragma: no cover - not used in dispatch tests
        """Return option step identifiers for this feature."""
        return []

    def validate_config(
        self, config: Mapping[str, object]
    ) -> dict[str, object]:  # pragma: no cover - not used
        """Validate and normalize config for this feature."""
        return dict(config)

    def is_enabled(self, data: object) -> bool:
        """Return whether this feature is enabled for the area."""
        return self.enabled

    def depends_on(self) -> set[MagicAreasFeatures]:
        """Return feature dependencies required for this module."""
        return set(self.deps)

    def config_flow_steps(self) -> list[FeatureConfigStep]:  # pragma: no cover - not used
        """Return config flow steps for this feature."""
        return []


@pytest.mark.asyncio
async def test_sensor_setup_dispatches_feature_modules(hass: HomeAssistant) -> None:
    """Sensor setup should dispatch to feature modules for the domain."""
    from custom_components.magic_areas.sensor import async_setup_entry

    data = MagicMock()
    data.area_config = MagicMock()
    data.entities = {}
    data.magic_entities = {}
    data.enabled_features = {MagicAreasFeatures.AGGREGATES}
    data.feature_configs = {}

    coordinator = AsyncMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()

    config_entry = MockConfigEntry(domain=DOMAIN, data=get_basic_config_entry_data(DEFAULT_MOCK_AREA))
    config_entry.runtime_data = MagicMock(coordinator=coordinator)

    module_entity = MagicMock(spec=Entity)
    module = FeatureModuleDouble(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"sensor"},
        entities=[module_entity],
    )
    registry = FeatureRegistry([module])

    async_add_entities = MagicMock()

    with patch(
        "custom_components.magic_areas.features.registry.FEATURE_REGISTRY",
        registry,
        create=True,
    ):
        await async_setup_entry(hass, config_entry, async_add_entities)

    module.build_entities.assert_called_once_with(data.area_config, coordinator, data)
    module.attach_listeners.assert_called_once_with([module_entity], data)
    async_add_entities.assert_called_once()
    added_entities = async_add_entities.call_args[0][0]
    assert module_entity in added_entities


@pytest.mark.asyncio
async def test_binary_sensor_setup_dispatches_feature_modules(hass: HomeAssistant) -> None:
    """Binary sensor setup should include feature module entities."""
    from custom_components.magic_areas.binary_sensor import async_setup_entry

    area_config = MagicMock()
    area_config.is_meta.return_value = False

    data = MagicMock()
    data.area_config = area_config
    data.entities = {}
    data.magic_entities = {}
    data.enabled_features = {MagicAreasFeatures.AGGREGATES}
    data.feature_configs = {}

    coordinator = AsyncMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()

    config_entry = MockConfigEntry(domain=DOMAIN, data=get_basic_config_entry_data(DEFAULT_MOCK_AREA))
    config_entry.runtime_data = MagicMock(coordinator=coordinator)

    presence_entity = MagicMock(spec=Entity)
    module_entity = MagicMock(spec=Entity)
    module = FeatureModuleDouble(
        id=MagicAreasFeatures.AGGREGATES,
        domains={"binary_sensor"},
        entities=[module_entity],
    )
    registry = FeatureRegistry([module])

    async_add_entities = MagicMock()

    with (
        patch(
            "custom_components.magic_areas.features.registry.FEATURE_REGISTRY",
            registry,
            create=True,
        ),
        patch(
            "custom_components.magic_areas.binary_sensor.AreaStateBinarySensor",
            return_value=presence_entity,
        ),
        patch(
            "custom_components.magic_areas.binary_sensor.MetaAreaStateBinarySensor",
            return_value=presence_entity,
        ),
    ):
        await async_setup_entry(hass, config_entry, async_add_entities)

    module.build_entities.assert_called_once_with(area_config, coordinator, data)
    module.attach_listeners.assert_called_once_with([module_entity], data)
    async_add_entities.assert_called_once()
    added_entities = async_add_entities.call_args[0][0]
    assert presence_entity in added_entities
    assert module_entity in added_entities


@pytest.mark.asyncio
async def test_dependency_missing_skips_module_entities(hass: HomeAssistant, caplog: pytest.LogCaptureFixture) -> None:
    """Modules with missing dependencies should not build entities."""
    from custom_components.magic_areas.sensor import async_setup_entry

    data = MagicMock()
    data.area_config = MagicMock()
    data.entities = {}
    data.magic_entities = {}
    data.enabled_features = {MagicAreasFeatures.WASP_IN_A_BOX}
    data.feature_configs = {}

    coordinator = AsyncMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()

    config_entry = MockConfigEntry(domain=DOMAIN, data=get_basic_config_entry_data(DEFAULT_MOCK_AREA))
    config_entry.runtime_data = MagicMock(coordinator=coordinator)

    module_entity = MagicMock(spec=Entity)
    module = FeatureModuleDouble(
        id=MagicAreasFeatures.WASP_IN_A_BOX,
        domains={"sensor"},
        entities=[module_entity],
        deps={MagicAreasFeatures.AGGREGATES},
    )
    registry = FeatureRegistry([module])

    async_add_entities = MagicMock()

    with (
        patch(
            "custom_components.magic_areas.features.registry.FEATURE_REGISTRY",
            registry,
            create=True,
        ),
        caplog.at_level("WARNING"),
    ):
        await async_setup_entry(hass, config_entry, async_add_entities)

    module.build_entities.assert_not_called()
    assert "missing dependencies" in caplog.text
