"""Snapshot test fixtures for Magic Areas."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import LIGHT_LUX
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_ID,
    CONF_TYPE,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.area_state import AreaType
from tests.const import DEFAULT_MOCK_AREA, MOCK_AREAS, MockAreaIds
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor, MockLight, MockSensor


@pytest.fixture(name="snapshot_integration")
async def snapshot_integration_fixture(
    hass: HomeAssistant,
) -> AsyncGenerator[MockConfigEntry]:
    """Set up integration with realistic entities and enabled features."""
    motion_sensor = MockBinarySensor(
        name="motion_sensor",
        unique_id="motion_sensor",
        device_class=BinarySensorDeviceClass.MOTION,
    )
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [motion_sensor]}
    )

    light = MockLight(
        name="mock_light",
        state="off",
        unique_id="mock_light",
    )
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: [light]})

    illuminance_sensor = MockSensor(
        name="illuminance_sensor",
        unique_id="illuminance_sensor",
        native_value=250,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        unit_of_measurement=LIGHT_LUX,
    )
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [illuminance_sensor]}
    )

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {},
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 100,
        },
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=data.get(CONF_ID, DEFAULT_MOCK_AREA.value),
    )

    await init_integration_helper(hass, [entry])
    yield entry
    await shutdown_integration(hass, [entry])


@pytest.fixture(name="snapshot_integration_all_areas")
async def snapshot_integration_all_areas_fixture(
    hass: HomeAssistant,
    all_areas_with_meta_config_entry: list[MockConfigEntry],
) -> AsyncGenerator[list[MockConfigEntry]]:
    """Set up integration with multiple areas and meta areas plus entities."""
    mock_binary_sensor_entities: dict[MockAreaIds, list[MockBinarySensor]] = {}
    regular_areas: list[MockAreaIds] = []

    for area in MockAreaIds:
        area_object = MOCK_AREAS[area]
        if area_object[CONF_TYPE] == AreaType.META:
            continue
        regular_areas.append(area)

        mock_binary_sensor_entities[area] = [
            MockBinarySensor(
                name=f"motion_sensor_{area.value}",
                unique_id=f"motion_sensor_{area.value}",
                device_class=BinarySensorDeviceClass.MOTION,
            )
        ]

    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)

    await init_integration_helper(
        hass, all_areas_with_meta_config_entry, areas=regular_areas
    )
    yield all_areas_with_meta_config_entry
    await shutdown_integration(hass, all_areas_with_meta_config_entry)
