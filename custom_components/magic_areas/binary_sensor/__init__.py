"""Binary sensor control for magic areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.base.magic import MagicArea, MagicMetaArea
from custom_components.magic_areas.binary_sensor.base import AreaSensorGroupBinarySensor
from custom_components.magic_areas.binary_sensor.ble_tracker import (
    AreaBLETrackerBinarySensor,
)
from custom_components.magic_areas.binary_sensor.presence import (
    AreaStateBinarySensor,
    MetaAreaStateBinarySensor,
)
from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    AreaWaspInABoxBinarySensor,
)
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
)

from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_WASP_IN_A_BOX,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoAggregates,
    MagicAreasFeatureInfoHealth,
)
from custom_components.magic_areas.threshold import create_illuminance_threshold
from custom_components.magic_areas.util import cleanup_removed_entries

if TYPE_CHECKING:
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)

# Classes


class AreaAggregateBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoAggregates()


class AreaHealthBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoHealth()


# Setup


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area binary sensor config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping binary sensor setup; coordinator data unavailable")
        return
    area: MagicArea | MagicMetaArea = data.area
    entities_by_domain = data.entities
    magic_entities = data.magic_entities

    entities: list[Entity] = []

    # Create main presence sensor
    if area.is_meta() and isinstance(area, MagicMetaArea):
        entities.append(MetaAreaStateBinarySensor(area))
    else:
        entities.append(AreaStateBinarySensor(area))

    # Create extra sensors
    if CONF_FEATURE_AGGREGATION in data.enabled_features:
        entities.extend(create_aggregate_sensors(data, entities_by_domain))
        illuminance_threshold_sensor = create_illuminance_threshold(hass, data)
        if illuminance_threshold_sensor:
            entities.append(illuminance_threshold_sensor)

        # Wasp in a box
        if (
            CONF_FEATURE_WASP_IN_A_BOX in data.enabled_features
            and not area.is_meta()
        ):
            entities.extend(create_wasp_in_a_box_sensor(data))

    if CONF_FEATURE_HEALTH in data.enabled_features:
        entities.extend(create_health_sensors(data, entities_by_domain))

    if CONF_FEATURE_BLE_TRACKERS in data.enabled_features:
        entities.extend(create_ble_tracker_sensor(data))

    # Add all entities
    async_add_entities(entities)

    # Cleanup
    if BINARY_SENSOR_DOMAIN in magic_entities:
        cleanup_removed_entries(
            area.hass, entities, magic_entities[BINARY_SENSOR_DOMAIN]
        )


def create_wasp_in_a_box_sensor(
    data: MagicAreasData,
) -> list[AreaWaspInABoxBinarySensor]:
    """Add the Wasp in a box sensor for the area."""

    area = data.area
    if (
        CONF_FEATURE_WASP_IN_A_BOX not in data.enabled_features
        or CONF_FEATURE_AGGREGATION not in data.enabled_features
    ):
        return []

    try:
        return [AreaWaspInABoxBinarySensor(area)]
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating wasp in a box sensor: %s",
            area.slug,
            str(e),
        )
        return []


def create_ble_tracker_sensor(
    data: MagicAreasData,
) -> list[AreaBLETrackerBinarySensor]:
    """Add the BLE tracker sensor for the area."""
    area = data.area
    if CONF_FEATURE_BLE_TRACKERS not in data.enabled_features:
        return []

    if not data.feature_configs.get(CONF_FEATURE_BLE_TRACKERS, {}).get(
        CONF_BLE_TRACKER_ENTITIES, []
    ):
        return []

    try:
        return [
            AreaBLETrackerBinarySensor(
                area,
            )
        ]
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating BLE tracker sensor: %s",
            area.slug,
            str(e),
        )
        return []


def create_health_sensors(
    data: MagicAreasData, entities_by_domain: dict[str, list[dict[str, str]]]
) -> list[AreaHealthBinarySensor]:
    """Add the health sensors for the area."""
    area = data.area
    if CONF_FEATURE_HEALTH not in data.enabled_features:
        return []

    if BINARY_SENSOR_DOMAIN not in entities_by_domain:
        return []

    distress_entities: list[str] = []

    health_sensor_device_classes = data.feature_configs.get(
        CONF_FEATURE_HEALTH, {}
    ).get(CONF_HEALTH_SENSOR_DEVICE_CLASSES, DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES)

    for entity in entities_by_domain[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in health_sensor_device_classes:
            continue

        distress_entities.append(entity[ATTR_ENTITY_ID])

    if not distress_entities:
        _LOGGER.debug(
            "%s: No binary sensor found for configured device classes: %s.",
            area.name,
            str(health_sensor_device_classes),
        )
        return []

    _LOGGER.debug(
        "%s: Creating health sensor with the following entities: %s",
        area.slug,
        str(distress_entities),
    )

    try:
        return [
            AreaHealthBinarySensor(
                area,
                device_class=BinarySensorDeviceClass.PROBLEM,
                entity_ids=distress_entities,
            )
        ]
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating area health sensor: %s",
            area.slug,
            str(e),
        )
        return []


def create_aggregate_sensors(
    data: MagicAreasData, entities_by_domain: dict[str, list[dict[str, str]]]
) -> list[Entity]:
    """Create the aggregate sensors for the area."""
    # Create aggregates
    area = data.area
    if CONF_FEATURE_AGGREGATION not in data.enabled_features:
        return []

    aggregates: list[Entity] = []

    # Check BINARY_SENSOR_DOMAIN entities, count by device_class
    if BINARY_SENSOR_DOMAIN not in entities_by_domain:
        return []

    device_class_entities: dict[str, list[str]] = {}

    for entity in entities_by_domain[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in device_class_entities:
            device_class_entities[entity[ATTR_DEVICE_CLASS]] = []

        device_class_entities[entity[ATTR_DEVICE_CLASS]].append(entity["entity_id"])

    for device_class, entity_list in device_class_entities.items():
        if len(entity_list) < data.feature_configs.get(CONF_FEATURE_AGGREGATION, {}).get(
            CONF_AGGREGATES_MIN_ENTITIES, 0
        ):
            continue

        if device_class not in data.feature_configs.get(
            CONF_FEATURE_AGGREGATION, {}
        ).get(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
            DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            len(entity_list),
            area.slug,
        )
        try:
            aggregates.append(
                AreaAggregateBinarySensor(area, device_class, entity_list)
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error creating '%s' aggregate sensor: %s",
                area.slug,
                device_class,
                str(e),
            )

    return aggregates
