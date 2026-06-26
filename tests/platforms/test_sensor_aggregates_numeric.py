"""Numeric aggregate sensor behavior tests."""

from __future__ import annotations

from random import randint
from statistics import mean

from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    UnitOfElectricCurrent,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from tests.mocks import MockSensor

pytest_plugins = ("tests.platforms.sensor_aggregates_testkit",)


async def test_aggregates_sensor_avg(
    hass: HomeAssistant,
    entities_sensor_temperature_multiple: list[MockSensor],
    _setup_integration_aggregates: object,
) -> None:
    """Temperature aggregate should track average value."""
    aggregate_sensor_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_temperature"
    )

    entity_values = []
    for mock_entity in entities_sensor_temperature_multiple:
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state is not None
        entity_values.append(int(mock_state.state))

    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(
        mean(entity_values), 2
    )

    changed_values = []
    for mock_entity in entities_sensor_temperature_multiple:
        random_value = randint(0, 100)
        changed_values.append(random_value)
        hass.states.async_set(
            mock_entity.entity_id,
            str(random_value),
            attributes={
                ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                "unit_of_measurement": UnitOfTemperature.CELSIUS,
            },
        )
        await hass.async_block_till_done()
        changed_state = hass.states.get(mock_entity.entity_id)
        assert changed_state is not None
        assert int(changed_state.state) == random_value

    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(
        mean(changed_values), 2
    )


async def test_aggregates_sensor_sum(
    hass: HomeAssistant,
    entities_sensor_current_multiple: list[MockSensor],
    _setup_integration_aggregates: object,
) -> None:
    """Current aggregate should track sum value."""
    aggregate_sensor_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_current"
    )

    entity_values = []
    for mock_entity in entities_sensor_current_multiple:
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state is not None
        entity_values.append(int(mock_state.state))

    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(sum(entity_values), 2)

    changed_values = []
    for mock_entity in entities_sensor_current_multiple:
        random_value = randint(0, 100)
        changed_values.append(random_value)
        hass.states.async_set(
            mock_entity.entity_id,
            str(random_value),
            attributes={
                ATTR_DEVICE_CLASS: SensorDeviceClass.CURRENT,
                "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
            },
        )
        await hass.async_block_till_done()
        changed_state = hass.states.get(mock_entity.entity_id)
        assert changed_state is not None
        assert int(changed_state.state) == random_value

    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(
        sum(changed_values), 2
    )
