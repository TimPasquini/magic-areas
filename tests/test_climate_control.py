"""Tests for the BLE Tracker feature."""

import asyncio
from collections.abc import AsyncGenerator
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_NONE,
    SERVICE_SET_PRESET_MODE,
    HVACMode,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.config_keys import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.enums import (
    MagicAreasFeatures,
    MagicAreasEvents,
)

from tests.const import DEFAULT_MOCK_AREA
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from tests.helpers import (
    assert_attribute,
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockBinarySensor, MockClimate

_LOGGER = logging.getLogger(__name__)


# Constants

MOCK_CLIMATE_ENTITY_ID = f"{CLIMATE_DOMAIN}.mock_climate"
CLIMATE_CONTROL_SWITCH_ENTITY_ID = (
    f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
)
AREA_SENSOR_ENTITY_ID = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"

def _assert_attribute_with_context(
    hass: HomeAssistant,
    entity_id: str,
    attribute_key: str,
    expected_value: str,
    *,
    context: str,
    area_events: list[tuple[str, list[str], list[str], list[str]]] | None = None,
    preset_calls: list[str] | None = None,
) -> None:
    """Assert entity attribute with context dump for debugging failures."""
    entity_state = hass.states.get(entity_id)
    if not entity_state:
        raise AssertionError(
            f"{context}: missing state for {entity_id}"
        )

    actual_value = str(entity_state.attributes.get(attribute_key))
    if actual_value != expected_value:
        motion_state = hass.states.get("binary_sensor.motion_sensor")
        area_state = hass.states.get(AREA_SENSOR_ENTITY_ID)
        switch_state = hass.states.get(CLIMATE_CONTROL_SWITCH_ENTITY_ID)
        debug_details = (
            f"{context}: {entity_id}.{attribute_key} expected={expected_value} "
            f"actual={actual_value}; "
            f"climate_state={entity_state.state}; "
            f"motion_state={getattr(motion_state, 'state', None)}; "
            f"area_state={getattr(area_state, 'state', None)}; "
            f"switch_state={getattr(switch_state, 'state', None)}; "
            f"area_attrs={getattr(area_state, 'attributes', None)}"
        )
        if area_events is not None:
            debug_details = f"{debug_details}; area_events={area_events}"
        if preset_calls is not None:
            debug_details = f"{debug_details}; preset_calls={preset_calls}"
        raise AssertionError(debug_details)


async def _wait_for_attribute(
    hass: HomeAssistant,
    entity_id: str,
    attribute_key: str,
    expected_value: str,
    *,
    context: str | None = None,
    area_events: list[tuple[str, list[str], list[str], list[str]]] | None = None,
    preset_calls: list[str] | None = None,
    attempts: int = 20,
    delay: float = 0.1,
) -> None:
    """Wait for an entity attribute to reach a specific value."""
    for _ in range(attempts):
        state = hass.states.get(entity_id)
        if state and str(state.attributes.get(attribute_key)) == expected_value:
            return
        await asyncio.sleep(delay)
        await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    actual = None if not state else str(state.attributes.get(attribute_key))
    details = f"{entity_id}.{attribute_key} expected={expected_value} actual={actual}"
    if context:
        details = f"{context}: {details}"
    if area_events is not None:
        details = f"{details}; area_events={area_events}"
    if preset_calls is not None:
        details = f"{details}; preset_calls={preset_calls}"
    raise AssertionError(details)


# Fixtures


@pytest.fixture(name="climate_control_config_entry")
def mock_config_entry_climate_control() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.CLIMATE_CONTROL: {
                    CONF_CLIMATE_CONTROL_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID,
                    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: PRESET_NONE,
                    CONF_CLIMATE_CONTROL_PRESET_CLEAR: PRESET_AWAY,
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_climate_control")
async def setup_integration_climate_control(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with BLE tracker config."""

    await init_integration_helper(hass, [climate_control_config_entry])
    yield
    await shutdown_integration(hass, [climate_control_config_entry])


# Entities


@pytest.fixture(name="entities_climate_one")
async def setup_entities_climate_one(
    hass: HomeAssistant,
) -> list[MockClimate]:
    """Create one mock climate and set up the system with it."""
    mock_climate_entities = [
        MockClimate(
            name="mock_climate",
            unique_id="unique_mock_climate",
        )
    ]
    await setup_mock_entities(
        hass, CLIMATE_DOMAIN, {DEFAULT_MOCK_AREA: mock_climate_entities}
    )
    return mock_climate_entities


# Tests


async def test_climate_control_init(
    hass: HomeAssistant,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control,
) -> None:
    """Test climate control."""

    area_sensor_state = hass.states.get(AREA_SENSOR_ENTITY_ID)
    assert_state(area_sensor_state, STATE_OFF)

    climate_control_switch_state = hass.states.get(CLIMATE_CONTROL_SWITCH_ENTITY_ID)
    assert_state(climate_control_switch_state, STATE_OFF)

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert_state(climate_state, STATE_OFF)

    # Turn on the climate device
    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID}
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert_state(climate_state, HVACMode.AUTO)

    # Reset preset mode
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE: PRESET_ECO},
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert_attribute(climate_state, ATTR_PRESET_MODE, PRESET_ECO)


async def test_climate_control_logic(
    hass: HomeAssistant,
    entities_climate_one: list[MockClimate],
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_climate_control,
) -> None:
    """Test climate control logic."""

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    motion_sensor_state = hass.states.get(motion_sensor_entity_id)
    assert_state(motion_sensor_state, STATE_OFF)

    # Turn on the climate device
    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID}
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert_state(climate_state, HVACMode.AUTO)

    # Set initial preset to something we don't use, so we know we changed from it
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE: PRESET_ECO},
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert_attribute(climate_state, ATTR_PRESET_MODE, PRESET_ECO)

    # @TODO test control off, ensure nothing happens

    # Capture area state change events for debug context
    area_events: list[tuple[str, list[str], list[str], list[str]]] = []

    def _record_area_event(
        area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        new_states, lost_states, current_states = states_tuple
        area_events.append((area_id, new_states, lost_states, current_states))

    remove_event_listener = async_dispatcher_connect(
        hass, MagicAreasEvents.AREA_STATE_CHANGED, _record_area_event
    )
    preset_calls: list[str] = []
    switch_entity = hass.data["entity_components"]["switch"].get_entity(
        CLIMATE_CONTROL_SWITCH_ENTITY_ID
    )
    if switch_entity is None:
        raise AssertionError("climate control switch entity not found")
    original_apply_preset = switch_entity.apply_preset

    async def _wrapped_apply_preset(state_name: str) -> None:
        preset_calls.append(state_name)
        await original_apply_preset(state_name)

    switch_entity.apply_preset = _wrapped_apply_preset

    try:
        # Turn on climate control
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: CLIMATE_CONTROL_SWITCH_ENTITY_ID},
        )
        await hass.async_block_till_done()
        await wait_for_state(hass, CLIMATE_CONTROL_SWITCH_ENTITY_ID, STATE_ON)

        # Area occupied, preset should be PRESET_NONE
        hass.states.async_set(motion_sensor_entity_id, STATE_ON)
        await hass.async_block_till_done()

        motion_sensor_state = hass.states.get(motion_sensor_entity_id)
        assert_state(motion_sensor_state, STATE_ON)

        area_sensor_state = hass.states.get(AREA_SENSOR_ENTITY_ID)
        assert_state(area_sensor_state, STATE_ON)

        await _wait_for_attribute(
            hass,
            MOCK_CLIMATE_ENTITY_ID,
            ATTR_PRESET_MODE,
            PRESET_NONE,
            context="occupied transition",
            area_events=area_events,
            preset_calls=preset_calls,
        )
        _assert_attribute_with_context(
            hass,
            MOCK_CLIMATE_ENTITY_ID,
            ATTR_PRESET_MODE,
            PRESET_NONE,
            context="occupied transition",
            area_events=area_events,
            preset_calls=preset_calls,
        )

        # Area clear, preset should be PRESET_AWAY
        hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
        await hass.async_block_till_done()

        motion_sensor_state = hass.states.get(motion_sensor_entity_id)
        assert_state(motion_sensor_state, STATE_OFF)

        area_sensor_state = hass.states.get(AREA_SENSOR_ENTITY_ID)
        assert_state(area_sensor_state, STATE_OFF)

        await _wait_for_attribute(
            hass,
            MOCK_CLIMATE_ENTITY_ID,
            ATTR_PRESET_MODE,
            PRESET_AWAY,
            context="clear transition",
            area_events=area_events,
            preset_calls=preset_calls,
        )
        _assert_attribute_with_context(
            hass,
            MOCK_CLIMATE_ENTITY_ID,
            ATTR_PRESET_MODE,
            PRESET_AWAY,
            context="clear transition",
            area_events=area_events,
            preset_calls=preset_calls,
        )
    finally:
        switch_entity.apply_preset = original_apply_preset
        remove_event_listener()
