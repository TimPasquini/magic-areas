"""Tests for core config helpers."""

from enum import Enum

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.core.config import (
    get_feature_config,
    has_configured_state,
    has_feature,
    normalize_feature_config,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


class FeatureEnum(Enum):
    """Example enum for feature normalization."""

    TEST = "test_feature"


def test_normalize_feature_config_list() -> None:
    """Normalize list-based feature config."""
    config = {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain"]}

    enabled, feature_configs = normalize_feature_config(config)

    assert enabled == {"test_feature", "plain"}
    assert feature_configs == {"test_feature": {}, "plain": {}}


def test_normalize_feature_config_dict() -> None:
    """Normalize dict-based feature config."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True},
            "plain": {"value": 10},
        }
    }

    enabled, feature_configs = normalize_feature_config(config)

    assert enabled == {"test_feature", "plain"}
    assert feature_configs == {
        "test_feature": {"flag": True},
        "plain": {"value": 10},
    }


def test_has_configured_state() -> None:
    """Report configured secondary states from config."""
    config = {
        CONF_SECONDARY_STATES: {
            CONF_SLEEP_ENTITY: "light.bedroom",
        }
    }

    assert has_configured_state(config, AreaStates.SLEEP) is True
    assert has_configured_state(config, AreaStates.CLEAR) is False


def test_has_feature_with_list_config() -> None:
    """Check if feature is enabled with list-based config."""
    config = {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain_feature"]}

    assert has_feature(config, "test_feature") is True
    assert has_feature(config, "plain_feature") is True
    assert has_feature(config, "unknown_feature") is False


def test_has_feature_with_dict_config() -> None:
    """Check if feature is enabled with dict-based config."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True},
            "plain": {},
        }
    }

    assert has_feature(config, "test_feature") is True
    assert has_feature(config, "plain") is True
    assert has_feature(config, "unknown") is False


def test_has_feature_with_empty_config() -> None:
    """Check that has_feature returns False for empty config."""
    config: dict = {}

    assert has_feature(config, "any_feature") is False


def test_get_feature_config_returns_config() -> None:
    """Get feature config returns configured options."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True, "value": 42},
            "plain": {"setting": "enabled"},
        }
    }

    assert get_feature_config(config, "test_feature") == {"flag": True, "value": 42}
    assert get_feature_config(config, "plain") == {"setting": "enabled"}


def test_get_feature_config_returns_empty_for_disabled() -> None:
    """Get feature config returns empty dict for disabled feature."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True},
        }
    }

    assert get_feature_config(config, "unknown_feature") == {}
    assert get_feature_config(config, "plain") == {}


def test_get_feature_config_from_list_config() -> None:
    """Get feature config works with list-based config."""
    config = {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain"]}

    assert get_feature_config(config, "test_feature") == {}
    assert get_feature_config(config, "plain") == {}
    assert get_feature_config(config, "unknown") == {}


# Integration tests from test_magic.py


async def test_has_configured_state_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test has_configured_state logic with real config entry."""

    from tests.const import DEFAULT_MOCK_AREA

    # Configure secondary state
    data = dict(mock_config_entry.data)
    data[CONF_SECONDARY_STATES] = {"dark_entity": "sensor.light_sensor"}
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    # AreaStates.DARK maps to "dark_entity" in CONFIGURABLE_AREA_STATE_MAP
    assert has_configured_state(area_config.config, AreaStates.DARK) is True

    # Sleep is not configured
    assert has_configured_state(area_config.config, AreaStates.SLEEP) is False

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_legacy_features(hass: HomeAssistant) -> None:
    """Test legacy feature configuration (list)."""
    from tests.const import DEFAULT_MOCK_AREA

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = [MagicAreasFeatures.LIGHT_GROUPS]

    config_entry = MockConfigEntry(
        domain="magic_areas", data=data
    )
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    assert has_feature(area_config.config, MagicAreasFeatures.LIGHT_GROUPS) is True

    await shutdown_integration(hass, [config_entry])


async def test_magic_area_invalid_features(hass: HomeAssistant) -> None:
    """Test invalid feature configuration."""
    from tests.const import DEFAULT_MOCK_AREA

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = "invalid_string"

    config_entry = MockConfigEntry(
        domain="magic_areas", data=data
    )
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify has_feature returns False for invalid feature config
    assert (
        has_feature(
            coordinator.data.config, MagicAreasFeatures.LIGHT_GROUPS
        )
        is False
    )

    await shutdown_integration(hass, [config_entry])
