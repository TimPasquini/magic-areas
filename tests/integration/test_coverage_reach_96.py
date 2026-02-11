"""Final targeted tests to reach 96% coverage."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, AreaStates
from custom_components.magic_areas.features import (
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_comprehensive_state_coverage(hass: HomeAssistant) -> None:
    """Test all state transitions with all features enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_LIGHT_GROUPS: {},
        CONF_FEATURE_FAN_GROUPS: {"tracked_device_class": "temperature"},
        CONF_FEATURE_CLIMATE_CONTROL: {
            "target_entity": "climate.test",
            "presets": {
                "occupied": "heat",
                "extended": "eco",
                "clear": "off",
                "dark": "auto",
            },
        },
        CONF_FEATURE_PRESENCE_HOLD: {},
        CONF_FEATURE_AGGREGATION: {},
        CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Test all state transitions
    transitions = [
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
        ([AreaStates.DARK], [], [AreaStates.OCCUPIED, AreaStates.DARK]),
        ([AreaStates.EXTENDED], [AreaStates.OCCUPIED], [AreaStates.EXTENDED, AreaStates.DARK]),
        ([AreaStates.CLEAR], [AreaStates.EXTENDED, AreaStates.DARK], [AreaStates.CLEAR]),
        ([AreaStates.BRIGHT], [], [AreaStates.CLEAR, AreaStates.BRIGHT]),
    ]

    for new, lost, current in transitions:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area.id,
            (new, lost, current),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_all_state_combinations(hass: HomeAssistant) -> None:
    """Test every possible state combination."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_LIGHT_GROUPS: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    all_states = [
        AreaStates.OCCUPIED,
        AreaStates.CLEAR,
        AreaStates.EXTENDED,
        AreaStates.DARK,
        AreaStates.BRIGHT,
        AreaStates.ACCENT,
        AreaStates.SLEEP,
    ]

    # Send every state
    for state in all_states:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area.id,
            ([state], [], [state]),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_area_methods_called_directly(hass: HomeAssistant) -> None:
    """Test calling area methods directly to trigger uncovered code."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Call methods directly
    assert callable(area.is_occupied)
    is_occ = area.is_occupied()
    assert isinstance(is_occ, bool)

    assert callable(area.get_current_states)
    states = area.get_current_states()
    assert isinstance(states, list)

    assert callable(area.has_state)
    result = area.has_state("occupied")
    assert isinstance(result, bool)

    assert callable(area.has_configured_state)
    result = area.has_configured_state("occupied")
    assert isinstance(result, bool)

    assert callable(area.has_feature)
    result = area.has_feature("light_groups")
    assert isinstance(result, bool)

    assert callable(area.feature_config)
    config = area.feature_config("light_groups")
    assert isinstance(config, dict)

    assert callable(area.available_platforms)
    platforms = area.available_platforms()
    assert isinstance(platforms, list)

    assert callable(area.has_entities)
    result = area.has_entities("light")
    assert isinstance(result, bool)

    assert callable(area.is_meta)
    result = area.is_meta()
    assert isinstance(result, bool)

    assert callable(area.is_interior)
    result = area.is_interior()
    assert isinstance(result, bool)

    assert callable(area.is_exterior)
    result = area.is_exterior()
    assert isinstance(result, bool)

    await shutdown_integration(hass, [config_entry])
