"""Test for light groups edge cases."""

import logging
from unittest.mock import MagicMock

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.attrs import ATTR_STATES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    setup_mock_entities,
    shutdown_integration,
)
from tests.helpers import (
    init_integration as init_integration_helper,
)
from tests.mocks import MockBinarySensor, MockLight

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(name="light_edge_cases_config_entry")
def mock_config_entry_light_edge_cases() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.overhead_1", "light.overhead_2"],
                    CONF_OVERHEAD_LIGHTS_STATES: [
                        AreaStates.OCCUPIED,
                        AreaStates.BRIGHT,
                    ],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="light_edge_cases_config_entry_limited")
def mock_config_entry_light_edge_cases_limited() -> MockConfigEntry:
    """Fixture for mock configuration entry with limited features/states."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: ["light.overhead_1"],
                    CONF_OVERHEAD_LIGHTS_STATES: [AreaStates.OCCUPIED],
                    CONF_OVERHEAD_LIGHTS_ACT_ON: [],  # Empty for testing
                },
            },
            CONF_SECONDARY_STATES: {CONF_DARK_ENTITY: "binary_sensor.dark_sensor"},
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="entities_light_edge_cases")
async def setup_entities_light_edge_cases(hass: HomeAssistant) -> list[MockLight]:
    """Create mock lights."""
    lights = [
        MockLight("overhead_1", STATE_OFF, unique_id="overhead_1"),
        MockLight("overhead_2", STATE_OFF, unique_id="overhead_2"),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    return lights


@pytest.fixture(name="entities_binary_sensor_edge_cases")
async def setup_entities_binary_sensor_edge_cases(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create mock binary sensors."""
    sensors = [
        MockBinarySensor(name="dark_sensor", unique_id="dark_sensor"),
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: sensors})
    return sensors


async def test_get_active_lights_missing_entity(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Test _get_active_lights when an entity is missing from HA states."""

    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )

    # Remove one light from HA states
    hass.states.async_remove("light.overhead_2")

    # Trigger turn_on which calls _get_active_lights
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: light_group_id},
        blocking=True,
    )

    # If it doesn't crash, we are good.
    await shutdown_integration(hass, [light_edge_cases_config_entry])



async def test_is_child_controllable(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Test is_child_controllable."""

    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )

    # Get the entity instance from the entity component
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(
        light_group_id
    )
    assert target_group is not None

    # Test entity not found
    assert not target_group.is_child_controllable("light.non_existent")

    # Test entity found but no controlling attribute
    assert not target_group.is_child_controllable(
        entities_light_edge_cases[0].entity_id
    )

    # Test entity found AND has controlling attribute (True)
    hass.states.async_set(
        entities_light_edge_cases[0].entity_id, STATE_ON, {"controlling": True}
    )
    assert target_group.is_child_controllable(entities_light_edge_cases[0].entity_id)

    await shutdown_integration(hass, [light_edge_cases_config_entry])



async def test_group_state_changed_logic(
    hass: HomeAssistant,
    light_edge_cases_config_entry: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Test group_state_changed logic."""

    await init_integration_helper(hass, [light_edge_cases_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )

    # Get the entity instance from the entity component
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(
        light_group_id
    )
    assert target_group is not None

    # Area state sensor entity ID for setting occupancy via HA state machine
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )

    # Setup test scenario 1: area not occupied (clear state)
    hass.states.async_set(
        area_sensor_entity_id, STATE_OFF, {ATTR_STATES: [AreaStates.CLEAR]}
    )
    target_group.reset_control = MagicMock()

    # Test area not occupied
    event = MagicMock()
    target_group.group_state_changed(event)
    target_group.reset_control.assert_called_once()

    # Setup test scenario 2: area occupied
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )
    target_group.reset_control.reset_mock()

    # Test invalid event (no context)
    event.context = None
    assert not target_group.group_state_changed(event)

    # Test valid context but invalid origin event
    event.context = MagicMock()
    event.context.origin_event = None

    original_handle_secondary = target_group.handle_group_state_change_secondary
    target_group.handle_group_state_change_secondary = MagicMock()
    target_group.group_state_changed(event)
    target_group.handle_group_state_change_secondary.assert_called_once()

    # Test origin event state_changed but invalid states
    event.context.origin_event = MagicMock()
    event.context.origin_event.event_type = "state_changed"
    event.context.origin_event.data = {}

    target_group.handle_group_state_change_secondary.reset_mock()
    assert not target_group.group_state_changed(event)
    target_group.handle_group_state_change_secondary.assert_not_called()

    # Test restored event
    event.context.origin_event.data = {
        "old_state": MagicMock(state=STATE_ON, attributes={"restored": True}),
        "new_state": MagicMock(state=STATE_OFF),
    }
    assert not target_group.group_state_changed(event)
    target_group.handle_group_state_change_secondary.assert_not_called()

    # Restore original method
    target_group.handle_group_state_change_secondary = original_handle_secondary

    # Test controlled logic in handle_group_state_change_secondary
    target_group.controlled = True
    target_group.handle_group_state_change_secondary()
    assert not target_group.controlled

    await shutdown_integration(hass, [light_edge_cases_config_entry])




async def test_manual_control_detection(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Test manual control detection (539-540)."""

    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()

    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(
        light_group_id
    )

    # Setup: Set area to occupied via HA state machine
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )

    # Simulate state change event (manual turn on/off)
    event = MagicMock()
    event.context.origin_event.event_type = "state_changed"
    event.context.origin_event.data = {
        "old_state": State(light_group_id, STATE_OFF),
        "new_state": State(light_group_id, STATE_ON),
    }

    target_group.group_state_changed(event)

    # Should set controlling to False
    assert target_group.controlling is False

    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])


async def test_primary_change_no_children(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Test primary change with no children (521)."""

    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()

    # We need the ALL group.
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_all_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(
        light_group_id
    )

    # Force child_ids to empty
    target_group._child_ids = []

    # Let's set controlling to True first.
    target_group.controlling = True
    target_group.handle_group_state_change_primary()
    assert target_group.controlling is True

    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])


async def test_primary_change_controlling(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Test primary change controlling logic (525-526)."""

    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()

    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_all_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(
        light_group_id
    )

    # Mock is_child_controllable
    target_group.is_child_controllable = MagicMock(return_value=True)

    target_group.handle_group_state_change_primary()

    assert target_group.controlling is True

    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])
