"""Behavior tests for climate-control presence transitions."""


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
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from custom_components.magic_areas.enums import MagicAreasEvents
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_attribute,
    assert_state,
    wait_for_attribute,
    wait_for_state,
)
from tests.mocks import MockBinarySensor, MockClimate

pytest_plugins = ("tests.platforms.climate_control_testkit",)

MOCK_CLIMATE_ENTITY_ID = f"{CLIMATE_DOMAIN}.mock_climate"
CLIMATE_CONTROL_SWITCH_ENTITY_ID = (
    f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
)
AREA_SENSOR_ENTITY_ID = (
    f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
)


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
        raise AssertionError(f"{context}: missing state for {entity_id}")

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


async def test_climate_control_logic(
    hass: HomeAssistant,
    entities_climate_one: list[MockClimate],
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_climate_control: None,
) -> None:
    """Test climate control logic."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_OFF)

    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(MOCK_CLIMATE_ENTITY_ID), HVACMode.AUTO)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE: PRESET_ECO},
    )
    await hass.async_block_till_done()
    assert_attribute(hass.states.get(MOCK_CLIMATE_ENTITY_ID), ATTR_PRESET_MODE, PRESET_ECO)

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
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: CLIMATE_CONTROL_SWITCH_ENTITY_ID},
        )
        await hass.async_block_till_done()
        await wait_for_state(hass, CLIMATE_CONTROL_SWITCH_ENTITY_ID, STATE_ON)

        hass.states.async_set(motion_sensor_entity_id, STATE_ON)
        await hass.async_block_till_done()
        assert_state(hass.states.get(motion_sensor_entity_id), STATE_ON)
        assert_state(hass.states.get(AREA_SENSOR_ENTITY_ID), STATE_ON)
        await wait_for_attribute(
            hass,
            MOCK_CLIMATE_ENTITY_ID,
            ATTR_PRESET_MODE,
            PRESET_NONE,
            timeout=2.0,
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

        hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
        await hass.async_block_till_done()
        assert_state(hass.states.get(motion_sensor_entity_id), STATE_OFF)
        assert_state(hass.states.get(AREA_SENSOR_ENTITY_ID), STATE_OFF)
        await wait_for_attribute(
            hass,
            MOCK_CLIMATE_ENTITY_ID,
            ATTR_PRESET_MODE,
            PRESET_AWAY,
            timeout=2.0,
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
