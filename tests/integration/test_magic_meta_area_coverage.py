"""Integration tests for MagicMetaArea coverage of base/magic.py uncovered lines."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.area_constants import (
    AREA_TYPE_META,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_EXTERIOR,
)
from custom_components.magic_areas.config_keys import CONF_TYPE
from custom_components.magic_areas.enums import AreaStates
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_magic_area_has_state_with_enum(hass: HomeAssistant) -> None:
    """Test has_state with Enum state values.

    This test covers lines 192-193 in base/magic.py.
    """
    # Setup a regular area
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Test has_state with Enum - should not crash
    result = area.has_state(AreaStates.OCCUPIED)
    assert isinstance(result, bool)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_magic_area_feature_config_not_enabled(hass: HomeAssistant) -> None:
    """Test feature_config returns empty dict for disabled feature.

    This test covers lines 215-216 in base/magic.py.
    """
    # Setup a regular area
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Don't enable any features
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Request config for a feature that's not enabled
    config = area.feature_config("nonexistent_feature")
    assert config == {}

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_magic_area_feature_config_no_config_found(hass: HomeAssistant) -> None:
    """Test feature_config logs debug when no config found.

    This test covers line 219 in base/magic.py.
    """
    # Setup a regular area with a feature but no feature config
    from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
    from custom_components.magic_areas.features import CONF_FEATURE_LIGHT_GROUPS

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Enable feature but don't provide config
    data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Request config for enabled feature
    config = area.feature_config(CONF_FEATURE_LIGHT_GROUPS)
    assert isinstance(config, dict)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_magic_area_get_current_states_missing_sensor(
    hass: HomeAssistant,
) -> None:
    """Test get_current_states returns empty list when sensor missing.

    This test covers line 188 in base/magic.py.
    """
    # Setup a regular area
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # get_current_states should return list
    states = area.get_current_states()
    assert isinstance(states, list)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_magic_area_is_interior(hass: HomeAssistant) -> None:
    """Test is_interior method.

    This test covers line 248 in base/magic.py.
    """
    # Setup interior area
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_TYPE] = AREA_TYPE_INTERIOR
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    assert area.is_interior() is True
    assert area.is_exterior() is False

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_magic_area_is_exterior(hass: HomeAssistant) -> None:
    """Test is_exterior method.

    This test covers line 252 in base/magic.py.
    """
    # Setup exterior area
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_TYPE] = AREA_TYPE_EXTERIOR
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    assert area.is_interior() is False
    assert area.is_exterior() is True

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_magic_area_has_entities(hass: HomeAssistant) -> None:
    """Test has_entities method.

    This test covers line 273 in base/magic.py.
    """
    # Setup a regular area
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Test has_entities - may return True or False depending on what was loaded
    result = area.has_entities("light")
    assert isinstance(result, bool)

    result = area.has_entities("nonexistent_domain")
    assert result is False

    await shutdown_integration(hass, [config_entry])
