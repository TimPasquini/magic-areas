"""Scenario tests for cover automation behavior."""

from collections.abc import AsyncGenerator
from typing import Protocol, cast

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockBinarySensor, MockCover, MockLight

LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE = "occupancy"
LIGHT_GROUP_ACT_ON_STATE_CHANGE = "state"


class _ScenarioLightGroup(Protocol):
    """Runtime surface used to emit light area-state transitions."""

    category: str

    def area_state_changed(
        self,
        area_id: str,
        states_tuple: tuple[list[str], list[str], list[str]],
    ) -> object:
        """Handle a room-level area-state transition."""


@pytest.fixture(name="cover_light_scenario_entry")
def cover_light_scenario_entry_fixture() -> MockConfigEntry:
    """Return a Magic Areas entry with cover automation and adaptive lights enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.COVER_GROUPS: {},
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE: "adaptive",
                    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: (
                        "binary_sensor.scenario_inside_bright"
                    ),
                    "overhead_lights": ["light.scenario_overhead_light"],
                    "overhead_lights_states": [AreaStates.OCCUPIED.value],
                    "overhead_lights_act_on": [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                    "sleep_lights": [],
                    "sleep_lights_states": [],
                    "sleep_lights_act_on": [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                    "accent_lights": [],
                    "accent_lights_states": [],
                    "accent_lights_act_on": [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                    "task_lights": [],
                    "task_lights_states": [],
                    "task_lights_act_on": [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="cover_light_scenario")
async def cover_light_scenario_fixture(
    hass: HomeAssistant,
    cover_light_scenario_entry: MockConfigEntry,
) -> AsyncGenerator[dict[str, object]]:
    """Set up one room with cover automation and adaptive light control."""
    overhead = MockLight(
        name="scenario_overhead_light",
        state=STATE_OFF,
        unique_id="scenario_overhead_light",
    )
    occupancy = MockBinarySensor(
        name="scenario_occupancy",
        unique_id="scenario_occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    )
    inside_bright = MockBinarySensor(
        name="scenario_inside_bright",
        unique_id="scenario_inside_bright",
        device_class=BinarySensorDeviceClass.LIGHT,
    )
    blind = MockCover(
        name="scenario_blind",
        unique_id="scenario_blind",
        device_class=CoverDeviceClass.BLIND,
        state=STATE_OPEN,
    )
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: [overhead]})
    await setup_mock_entities(
        hass,
        BINARY_SENSOR_DOMAIN,
        {DEFAULT_MOCK_AREA: [occupancy, inside_bright]},
    )
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: [blind]})
    await init_integration(hass, [cover_light_scenario_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield {
        "entry": cover_light_scenario_entry,
        "overhead": overhead,
        "occupancy": occupancy,
        "inside_bright": inside_bright,
        "blind": blind,
    }
    await shutdown_integration(hass, [cover_light_scenario_entry])


@pytest.fixture(name="cover_scenario_entry")
def cover_scenario_entry_fixture() -> MockConfigEntry:
    """Return a Magic Areas entry with cover automation enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_ENABLED_FEATURES: {MagicAreasFeatures.COVER_GROUPS: {}}})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="cover_scenario")
async def cover_scenario_fixture(
    hass: HomeAssistant,
    cover_scenario_entry: MockConfigEntry,
) -> AsyncGenerator[MockCover]:
    """Set up one room with one blind cover."""
    blind = MockCover(
        name="scenario_blind",
        unique_id="scenario_blind",
        device_class=CoverDeviceClass.BLIND,
        state=STATE_OPEN,
    )
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: [blind]})
    await init_integration(hass, [cover_scenario_entry])
    yield blind
    await shutdown_integration(hass, [cover_scenario_entry])


def _cover_group_entity_id() -> str:
    """Return the scenario blind helper entity id."""
    return (
        f"{COVER_DOMAIN}.magic_areas_cover_groups_"
        f"{DEFAULT_MOCK_AREA}_cover_group_blind"
    )


def _cover_control_entity_id() -> str:
    """Return the scenario cover control switch entity id."""
    return (
        f"{SWITCH_DOMAIN}.magic_areas_cover_groups_"
        f"{DEFAULT_MOCK_AREA}_cover_control"
    )


def _light_control_entity_id() -> str:
    """Return the scenario light control switch entity id."""
    return (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_"
        f"{DEFAULT_MOCK_AREA}_light_control"
    )


def _overhead_light_entity_id() -> str:
    """Return the scenario overhead light entity id."""
    return f"{LIGHT_DOMAIN}.scenario_overhead_light"


def _light_group_runtime(config_entry: MockConfigEntry) -> _ScenarioLightGroup:
    """Return the loaded overhead light-group runtime."""
    controllers = config_entry.runtime_data.runtime_controllers or []
    for controller in controllers:
        if getattr(controller, "category", None) == "overhead_lights":
            return cast(_ScenarioLightGroup, controller)
    raise AssertionError("overhead_lights runtime controller not found")


async def _enable_cover_control(hass: HomeAssistant) -> None:
    """Enable cover automation for the scenario room."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: _cover_control_entity_id()},
        blocking=True,
    )
    await hass.async_block_till_done()


async def _enable_light_control(hass: HomeAssistant) -> None:
    """Enable light automation for the scenario room."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: _light_control_entity_id()},
        blocking=True,
    )
    await hass.async_block_till_done()


async def _emit_area_state_transition(
    hass: HomeAssistant,
    *,
    new_states: list[AreaStates],
    lost_states: list[AreaStates] | None = None,
    current_states: list[AreaStates] | None = None,
) -> None:
    """Emit a Magic Areas area-state transition."""
    dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        (
            [state.value for state in new_states],
            [state.value for state in (lost_states or [])],
            [state.value for state in (current_states or new_states)],
        ),
    )
    await hass.async_block_till_done()


async def _emit_light_area_state_transition(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    *,
    new_states: list[AreaStates],
    lost_states: list[AreaStates] | None = None,
    current_states: list[AreaStates] | None = None,
) -> None:
    """Emit an area-state transition through the light runtime."""
    _light_group_runtime(config_entry).area_state_changed(
        DEFAULT_MOCK_AREA.value,
        (
            [state.value for state in new_states],
            [state.value for state in (lost_states or [])],
            [state.value for state in (current_states or new_states)],
        ),
    )
    await hass.async_block_till_done()


async def test_cover_privacy_closes_and_daylight_release_reopens(
    hass: HomeAssistant,
    cover_scenario: MockCover,
) -> None:
    """Sleep/privacy should close covers and release back to daylight when cleared."""
    await _enable_cover_control(hass)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
    )
    await wait_for_state(hass, _cover_group_entity_id(), STATE_CLOSED)

    await _emit_area_state_transition(
        hass,
        new_states=[],
        lost_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED],
    )
    await wait_for_state(hass, _cover_group_entity_id(), STATE_OPEN)


async def test_manual_cover_movement_is_not_immediately_reversed(
    hass: HomeAssistant,
    cover_scenario: MockCover,
) -> None:
    """Manual cover movement should hold automation instead of reopening immediately."""
    await _enable_cover_control(hass)

    cover_scenario.close_cover()
    await wait_for_state(hass, _cover_group_entity_id(), STATE_CLOSED)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )
    await hass.async_block_till_done()

    cover_group_state = hass.states.get(_cover_group_entity_id())
    assert cover_group_state is not None
    assert cover_group_state.state == STATE_CLOSED


async def test_dark_context_blocks_daylight_cover_open(
    hass: HomeAssistant,
    cover_scenario: MockCover,
) -> None:
    """Occupied dark/night context should not open covers through Daylight."""
    _ = cover_scenario
    await _enable_cover_control(hass)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
    )
    await wait_for_state(hass, _cover_group_entity_id(), STATE_CLOSED)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.DARK],
        lost_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
    )
    await hass.async_block_till_done()

    cover_group_state = hass.states.get(_cover_group_entity_id())
    assert cover_group_state is not None
    assert cover_group_state.state == STATE_CLOSED


async def test_cover_opening_can_support_adaptive_light_off(
    hass: HomeAssistant,
    cover_light_scenario: dict[str, object],
) -> None:
    """Opening covers should feed brightness context that light policy can consume."""
    config_entry = cast(MockConfigEntry, cover_light_scenario["entry"])
    occupancy = cast(MockBinarySensor, cover_light_scenario["occupancy"])
    inside_bright = cast(MockBinarySensor, cover_light_scenario["inside_bright"])

    hass.states.async_set("sun.sun", "above_horizon")
    inside_bright.turn_off()
    occupancy.turn_on()
    await hass.async_block_till_done()
    await _enable_light_control(hass)
    await _enable_cover_control(hass)

    await _emit_light_area_state_transition(
        hass,
        config_entry,
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )
    await wait_for_state(hass, _overhead_light_entity_id(), STATE_ON)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )
    await wait_for_state(hass, _cover_group_entity_id(), STATE_OPEN)

    inside_bright.turn_on()
    await hass.async_block_till_done()
    await _emit_light_area_state_transition(
        hass,
        config_entry,
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
    )

    await wait_for_state(hass, _overhead_light_entity_id(), STATE_OFF)


async def test_cover_closing_can_support_occupied_dark_light_on(
    hass: HomeAssistant,
    cover_light_scenario: dict[str, object],
) -> None:
    """Closing covers should feed dark context that light policy can consume."""
    config_entry = cast(MockConfigEntry, cover_light_scenario["entry"])
    occupancy = cast(MockBinarySensor, cover_light_scenario["occupancy"])
    inside_bright = cast(MockBinarySensor, cover_light_scenario["inside_bright"])
    blind = cast(MockCover, cover_light_scenario["blind"])

    hass.states.async_set("sun.sun", "above_horizon")
    inside_bright.turn_on()
    occupancy.turn_on()
    await hass.async_block_till_done()
    await _enable_light_control(hass)

    await _emit_light_area_state_transition(
        hass,
        config_entry,
        new_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
    )
    overhead_state = hass.states.get(_overhead_light_entity_id())
    assert overhead_state is not None
    assert overhead_state.state == STATE_OFF

    blind.close_cover()
    await wait_for_state(hass, _cover_group_entity_id(), STATE_CLOSED)
    inside_bright.turn_off()
    await hass.async_block_till_done()
    await _emit_light_area_state_transition(
        hass,
        config_entry,
        new_states=[AreaStates.DARK],
        lost_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
    )

    await wait_for_state(hass, _overhead_light_entity_id(), STATE_ON)
