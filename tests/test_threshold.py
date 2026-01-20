"""Test for aggregate (group) sensor behavior."""

import asyncio

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.components.threshold.const import ATTR_HYSTERESIS, ATTR_UPPER
from homeassistant.const import LIGHT_LUX, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    init_integration as init_integration_helper,
)
from tests.helpers import (
    setup_mock_entities,
)
from tests.mocks import MockSensor


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = {
        "name": "kitchen",
        "id": "kitchen",
        "type": "interior",
        CONF_ENABLED_FEATURES: {
            CONF_FEATURE_AGGREGATION: {
                CONF_AGGREGATES_MIN_ENTITIES: 1,
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 600,
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS: 10,
            }
        },
    }
    entry = MockConfigEntry(domain=DOMAIN, data=data, entry_id="test_threshold")
    return entry


@pytest.fixture(name="entities_sensor_illuminance_multiple")
async def setup_entities_sensor_illuminance_multiple(
    hass: HomeAssistant,
) -> list[SensorEntity]:
    """Create multiple mock sensor and set up the system with it."""
    entities = [
        MockSensor(
            name=f"illuminance_sensor_{i}",
            unique_id=f"illuminance_sensor_{i}",
            device_class=SensorDeviceClass.ILLUMINANCE,
            native_unit_of_measurement=LIGHT_LUX,
            unit_of_measurement=LIGHT_LUX,
            native_value=0.0,
        )
        for i in range(3)
    ]

    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: entities})

    return entities


async def test_threshold_sensor_light(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entities_sensor_illuminance_multiple: list[SensorEntity],
) -> None:
    """Test the light from illuminance threshold sensor."""

    threshold_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_threshold_kitchen_threshold_light"
    )

    aggregate_sensor_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_illuminance"
    )

    # Setup integration after entities are ready to avoid reload race condition
    await init_integration_helper(hass, [mock_config_entry])

    await hass.async_block_till_done()

    # Ensure aggregate sensor was created
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert float(aggregate_sensor_state.state) == 0.0

    # Ensure threhsold sensor was created
    threshold_sensor_state = hass.states.get(threshold_sensor_id)
    assert threshold_sensor_state is not None
    assert threshold_sensor_state.state == STATE_OFF
    assert hasattr(threshold_sensor_state, "attributes")
    assert ATTR_UPPER in threshold_sensor_state.attributes
    assert ATTR_HYSTERESIS in threshold_sensor_state.attributes

    sensor_threshold_upper = int(threshold_sensor_state.attributes[ATTR_UPPER])
    sensor_hysteresis = int(threshold_sensor_state.attributes[ATTR_HYSTERESIS])

    assert sensor_threshold_upper == 600
    assert sensor_hysteresis == 60.0

    # Set illuminance sensor values to over the threhsold upper value (incl. hysteresis)
    for mock_entity in entities_sensor_illuminance_multiple:
        old_state = hass.states.get(mock_entity.entity_id)
        attributes = old_state.attributes if old_state else {}
        hass.states.async_set(
            mock_entity.entity_id,
            str(sensor_threshold_upper + sensor_hysteresis + 10),
            attributes=attributes,
        )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()

    # Ensure aggregate sensor updated
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert float(aggregate_sensor_state.state) == float(
        sensor_threshold_upper + sensor_hysteresis + 10
    )

    # Ensure threhsold sensor is triggered
    threshold_sensor_state = hass.states.get(threshold_sensor_id)
    assert (
        threshold_sensor_state.state == STATE_ON
    ), f"Threshold sensor is {threshold_sensor_state.state}, expected {STATE_ON}. Aggregate state: {aggregate_sensor_state.state}"

    # Reset illuminance sensor values to 0
    for mock_entity in entities_sensor_illuminance_multiple:
        old_state = hass.states.get(mock_entity.entity_id)
        attributes = old_state.attributes if old_state else {}
        hass.states.async_set(
            mock_entity.entity_id,
            "0.0",
            attributes=attributes,
        )
    await hass.async_block_till_done()
    await asyncio.sleep(0.1)
    await hass.async_block_till_done()

    # Ensure aggregate sensor updated
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert float(aggregate_sensor_state.state) == 0.0

    # Ensure threhsold sensor is cleared
    threshold_sensor_state = hass.states.get(threshold_sensor_id)
    assert threshold_sensor_state.state == STATE_OFF
