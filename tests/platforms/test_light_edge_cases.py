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

    # Area occupied
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )

    # Invalid event (no context)
    event = MagicMock()
    event.context = None
    assert not target_group.group_state_changed(event)

    # state_changed event with missing data
    event.context = MagicMock()
    event.context.origin_event = MagicMock(event_type="state_changed", data={})
    assert not target_group.group_state_changed(event)

    # Restored event should be ignored
    event.context.origin_event.data = {
        "old_state": MagicMock(state=STATE_ON, attributes={"restored": True}),
        "new_state": MagicMock(state=STATE_OFF),
    }
    assert not target_group.group_state_changed(event)

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
    await hass.async_block_till_done()

    group_state = hass.states.get(light_group_id)
    assert group_state is not None
    assert group_state.attributes.get("controlling") is False

    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])

