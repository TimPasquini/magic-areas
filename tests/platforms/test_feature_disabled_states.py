"""Test platform behavior when features are disabled."""

import pytest
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_COVER_GROUPS,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def test_sensor_aggregates_skipped_when_feature_disabled(
    hass: HomeAssistant,
) -> None:
    """Test aggregate sensors not created when aggregation feature disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Explicitly disable aggregation feature
    data[CONF_ENABLED_FEATURES] = {}  # No features enabled

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Check that no aggregate sensors were created
    # (they would have entity IDs like sensor.magic_areas_aggregates_*)
    aggregate_sensor_ids = [
        entity_id
        for entity_id in hass.states.async_entity_ids(SENSOR_DOMAIN)
        if "aggregates" in entity_id
    ]
    assert len(aggregate_sensor_ids) == 0, "No aggregate sensors should exist"

    await shutdown_integration(hass, [config_entry])


async def test_fan_groups_skipped_when_feature_disabled(
    hass: HomeAssistant,
) -> None:
    """Test fan groups not created when feature disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Explicitly disable fan groups feature
    data[CONF_ENABLED_FEATURES] = {}  # No features enabled

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Check that no fan group entities were created
    fan_group_ids = [
        entity_id
        for entity_id in hass.states.async_entity_ids(FAN_DOMAIN)
        if "magic_areas" in entity_id
    ]
    assert len(fan_group_ids) == 0, "No fan groups should exist"

    await shutdown_integration(hass, [config_entry])


async def test_light_groups_skipped_when_feature_disabled(
    hass: HomeAssistant,
) -> None:
    """Test light groups not created when feature disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Explicitly disable light groups feature
    data[CONF_ENABLED_FEATURES] = {}  # No features enabled

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Check that no light group entities were created
    light_group_ids = [
        entity_id
        for entity_id in hass.states.async_entity_ids(LIGHT_DOMAIN)
        if "magic_areas" in entity_id and "group" in entity_id
    ]
    assert len(light_group_ids) == 0, "No light groups should exist"

    await shutdown_integration(hass, [config_entry])


async def test_cover_groups_skipped_when_feature_disabled(
    hass: HomeAssistant,
) -> None:
    """Test cover groups not created when feature disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Explicitly disable cover groups feature
    data[CONF_ENABLED_FEATURES] = {}  # No features enabled

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Check that no cover group entities were created
    cover_group_ids = [
        entity_id
        for entity_id in hass.states.async_entity_ids(COVER_DOMAIN)
        if "magic_areas" in entity_id
    ]
    assert len(cover_group_ids) == 0, "No cover groups should exist"

    await shutdown_integration(hass, [config_entry])


async def test_media_player_groups_skipped_when_feature_disabled(
    hass: HomeAssistant,
) -> None:
    """Test media player groups not created when feature disabled."""
    from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Explicitly disable media player features
    data[CONF_ENABLED_FEATURES] = {}  # No features enabled

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Check that no media player group entities were created
    mp_group_ids = [
        entity_id
        for entity_id in hass.states.async_entity_ids(MEDIA_PLAYER_DOMAIN)
        if "magic_areas" in entity_id
    ]
    assert len(mp_group_ids) == 0, "No media player groups should exist"

    await shutdown_integration(hass, [config_entry])
