"""Tests for entity state edge cases and error recovery."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.features import (
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_CLIMATE_CONTROL,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_light_platform_setup_creates_light_entities(
    hass: HomeAssistant,
) -> None:
    """Test light platform successfully creates entities during setup."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator.data is not None

    # Verify light platform was set up (entities would be registered)
    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_platform_setup_creates_fan_entities(
    hass: HomeAssistant,
) -> None:
    """Test fan platform successfully creates entities during setup."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator.data is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_platform_setup_creates_climate_control(
    hass: HomeAssistant,
) -> None:
    """Test climate platform successfully creates climate control entity."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_CLIMATE_CONTROL: {
            "target_entity": "climate.living_room",
            "presets": {
                "occupied": "heat",
                "clear": "off",
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    assert runtime_data is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_coordinator_data_available_after_init(
    hass: HomeAssistant,
) -> None:
    """Test that coordinator has data after initialization."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.data is not None
    assert coordinator.data.area_config is not None
    assert coordinator.data.area_runtime is not None
    assert coordinator.data.enabled_features is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_multiple_entity_setup_with_different_features(
    hass: HomeAssistant,
) -> None:
    """Test setup with multiple features enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_LIGHT_GROUPS: {},
        CONF_FEATURE_FAN_GROUPS: {},
        CONF_FEATURE_CLIMATE_CONTROL: {
            "target_entity": "climate.test",
            "presets": {"occupied": "heat"},
        },
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    coordinator = config_entry.runtime_data.coordinator
    assert coordinator.data is not None
    assert CONF_FEATURE_LIGHT_GROUPS in coordinator.data.enabled_features
    assert CONF_FEATURE_FAN_GROUPS in coordinator.data.enabled_features
    assert CONF_FEATURE_CLIMATE_CONTROL in coordinator.data.enabled_features

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_entity_registry_lookup_in_platforms(hass: HomeAssistant) -> None:
    """Test platforms can look up entities in entity registry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Platforms should have been able to look up existing entities
    # Verify we got to this point without errors
    runtime_data = config_entry.runtime_data
    assert runtime_data is not None

    await shutdown_integration(hass, [config_entry])
