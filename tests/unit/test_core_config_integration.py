"""Integration-oriented config helper tests."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.core.config import (
    has_configured_state,
    normalize_feature_config,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def test_has_configured_state_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test has_configured_state logic with real config entry."""
    data = dict(mock_config_entry.data)
    data[CONF_SECONDARY_STATES] = {"dark_entity": "sensor.light_sensor"}
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config
    assert has_configured_state(area_config.config, AreaStates.DARK) is True
    assert has_configured_state(area_config.config, AreaStates.SLEEP) is False

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_legacy_features(hass: HomeAssistant) -> None:
    """Test legacy feature configuration (list)."""
    from tests.const import DEFAULT_MOCK_AREA

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = [MagicAreasFeatures.LIGHT_GROUPS]
    config_entry = MockConfigEntry(domain="magic_areas", data=data)
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config
    enabled, _ = normalize_feature_config(area_config.config)
    assert str(MagicAreasFeatures.LIGHT_GROUPS) in enabled

    await shutdown_integration(hass, [config_entry])


async def test_magic_area_invalid_features(hass: HomeAssistant) -> None:
    """Test invalid feature configuration."""
    from tests.const import DEFAULT_MOCK_AREA

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = "invalid_string"
    config_entry = MockConfigEntry(domain="magic_areas", data=data)
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    enabled, _ = normalize_feature_config(entry.runtime_data.coordinator.data.config)
    assert str(MagicAreasFeatures.LIGHT_GROUPS) not in enabled

    await shutdown_integration(hass, [config_entry])
