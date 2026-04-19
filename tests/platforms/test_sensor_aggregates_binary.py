"""Binary-sensor aggregate behavior tests."""

from __future__ import annotations

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests.helpers import assert_state
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.platforms.sensor_aggregates_testkit",)


async def test_aggregates_binary_sensor_regular(
    hass: HomeAssistant,
    entities_binary_sensor_motion_multiple: list[MockBinarySensor],
    _setup_integration_aggregates: None,
) -> None:
    """Binary sensor aggregate should behave in any-on mode."""
    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_motion"
    )

    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert aggregate_sensor_state.state == STATE_OFF
    assert hasattr(aggregate_sensor_state, "attributes")
    assert ATTR_ENTITY_ID in aggregate_sensor_state.attributes

    group_members: list[str] = aggregate_sensor_state.attributes[ATTR_ENTITY_ID]

    for mock_entity in entities_binary_sensor_motion_multiple:
        assert mock_entity.entity_id in group_members

        mock_state = hass.states.get(mock_entity.entity_id)
        assert_state(mock_state, STATE_OFF)

        hass.states.async_set(mock_entity.entity_id, STATE_ON)
        await hass.async_block_till_done()
        assert_state(hass.states.get(mock_entity.entity_id), STATE_ON)
        assert_state(hass.states.get(aggregate_sensor_id), STATE_ON)

        hass.states.async_set(mock_entity.entity_id, STATE_OFF)
        await hass.async_block_till_done()
        assert_state(hass.states.get(mock_entity.entity_id), STATE_OFF)
        assert_state(hass.states.get(aggregate_sensor_id), STATE_OFF)

    for mock_entity in entities_binary_sensor_motion_multiple:
        hass.states.async_set(mock_entity.entity_id, STATE_ON)
    await hass.async_block_till_done()

    for entity_index, mock_entity in enumerate(entities_binary_sensor_motion_multiple):
        last_sensor = entity_index == (len(entities_binary_sensor_motion_multiple) - 1)
        hass.states.async_set(mock_entity.entity_id, STATE_OFF)
        await hass.async_block_till_done()
        assert_state(hass.states.get(aggregate_sensor_id), STATE_OFF if last_sensor else STATE_ON)


async def test_aggregates_binary_sensor_all(
    hass: HomeAssistant,
    entities_binary_sensor_connectivity_multiple: list[MockBinarySensor],
    _setup_integration_aggregates: None,
) -> None:
    """Connectivity aggregate should behave in all-on mode."""
    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_connectivity"
    )

    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert aggregate_sensor_state.state == STATE_OFF
    assert hasattr(aggregate_sensor_state, "attributes")
    assert ATTR_ENTITY_ID in aggregate_sensor_state.attributes

    group_members: list[str] = aggregate_sensor_state.attributes[ATTR_ENTITY_ID]

    for entity_index, mock_entity in enumerate(entities_binary_sensor_connectivity_multiple):
        last_sensor = entity_index == (len(entities_binary_sensor_connectivity_multiple) - 1)

        assert mock_entity.entity_id in group_members
        assert_state(hass.states.get(mock_entity.entity_id), STATE_OFF)

        hass.states.async_set(mock_entity.entity_id, STATE_ON)
        await hass.async_block_till_done()
        assert_state(hass.states.get(mock_entity.entity_id), STATE_ON)
        assert_state(hass.states.get(aggregate_sensor_id), STATE_ON if last_sensor else STATE_OFF)

    for mock_entity in entities_binary_sensor_connectivity_multiple:
        hass.states.async_set(mock_entity.entity_id, STATE_OFF)
        await hass.async_block_till_done()
        assert_state(hass.states.get(mock_entity.entity_id), STATE_OFF)
        assert_state(hass.states.get(aggregate_sensor_id), STATE_OFF)
