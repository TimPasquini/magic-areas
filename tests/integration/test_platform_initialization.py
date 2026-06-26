"""Tests for platform initialization edge cases."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_light_platform_skips_setup_when_no_lights(
    hass: HomeAssistant,
) -> None:
    """Test light platform setup returns early when no lights configured."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Even without lights, setup should complete without errors
    runtime_data = config_entry.runtime_data
    assert runtime_data is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_platform_setup_without_fan_entities(
    hass: HomeAssistant,
) -> None:
    """Test fan platform setup handles no fan entities gracefully."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    assert runtime_data is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_feature_disabled_platform_not_setup(hass: HomeAssistant) -> None:
    """Test platform setup skips when feature is disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Don't enable any features
    data[CONF_ENABLED_FEATURES] = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Setup should complete without errors even with no features
    runtime_data = config_entry.runtime_data
    assert runtime_data is not None
    assert len(runtime_data.coordinator.data.enabled_features) == 0

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_presence_hold_feature_setup(hass: HomeAssistant) -> None:
    """Test presence hold switch setup."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.PRESENCE_HOLD: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    assert (
        MagicAreasFeatures.PRESENCE_HOLD
        in runtime_data.coordinator.data.enabled_features
    )

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_all_platforms_skip_setup_with_disabled_features(
    hass: HomeAssistant,
) -> None:
    """Test all platforms skip setup when their features are disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # All platforms should skip setup gracefully
    runtime_data = config_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator.data is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_mixed_enabled_disabled_features(hass: HomeAssistant) -> None:
    """Test setup with some features enabled and others disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {},
        # FAN_GROUPS not enabled
        # CLIMATE_CONTROL not enabled
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    coordinator_data = config_entry.runtime_data.coordinator.data
    assert MagicAreasFeatures.LIGHT_GROUPS in coordinator_data.enabled_features
    assert MagicAreasFeatures.FAN_GROUPS not in coordinator_data.enabled_features

    await shutdown_integration(hass, [config_entry])
