"""Binary sensor control for magic areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
from custom_components.magic_areas.core.aggregate_policy import (
    AggregateDefinition,
    AggregateKind,
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
from custom_components.magic_areas.config_keys import (
    CONF_BLE_TRACKER_ENTITIES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries
from custom_components.magic_areas.features.dispatch import collect_feature_entities

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.models import MagicAreasConfigEntry
    from custom_components.magic_areas.features.registry import FeatureRegistry

_LOGGER = logging.getLogger(__name__)
FEATURE_REGISTRY: "FeatureRegistry | None" = None


def _get_feature_registry() -> "FeatureRegistry":
    if FEATURE_REGISTRY is not None:
        return FEATURE_REGISTRY
    from custom_components.magic_areas.features.registry import FEATURE_REGISTRY as registry

    return registry

# Classes


class AreaAggregateBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.AGGREGATES


class AreaHealthBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.HEALTH


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
    area_config = data.area_config
    coordinator = runtime_data.coordinator
    magic_entities = data.magic_entities

    entities: list[Entity] = []

    # Create main presence sensor
    if area_config.is_meta():
        entities.append(MetaAreaStateBinarySensor(area_config, coordinator))
    else:
        entities.append(AreaStateBinarySensor(area_config, coordinator))

    registry = _get_feature_registry()
    entities.extend(
        collect_feature_entities(
            domain=BINARY_SENSOR_DOMAIN,
            registry=registry,
            data=data,
            area_config=area_config,
            coordinator=coordinator,
            logger=_LOGGER,
        )
    )

    # Add all entities
    async_add_entities(entities)

    # Cleanup
    if BINARY_SENSOR_DOMAIN in magic_entities:
        cleanup_removed_entries(
            hass, entities, magic_entities[BINARY_SENSOR_DOMAIN]
        )


def create_wasp_in_a_box_sensor(
    data: MagicAreasData,
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
) -> list[AreaWaspInABoxBinarySensor]:
    """Add the Wasp in a box sensor for the area."""

    if (
        MagicAreasFeatures.WASP_IN_A_BOX not in data.enabled_features
        or MagicAreasFeatures.AGGREGATES not in data.enabled_features
    ):
        return []

    try:
        return [AreaWaspInABoxBinarySensor(area_config, coordinator)]
    except Exception as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating wasp in a box sensor: %s",
            area_config.slug,
            str(e),
        )
        return []


def create_ble_tracker_sensor(
    data: MagicAreasData,
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
) -> list[AreaBLETrackerBinarySensor]:
    """Add the BLE tracker sensor for the area."""
    if MagicAreasFeatures.BLE_TRACKER not in data.enabled_features:
        return []

    if not data.feature_configs.get(MagicAreasFeatures.BLE_TRACKER, {}).get(
        CONF_BLE_TRACKER_ENTITIES, []
    ):
        return []

    try:
        return [
            AreaBLETrackerBinarySensor(
                area_config,
                coordinator,
            )
        ]
    except Exception as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating BLE tracker sensor: %s",
            area_config.slug,
            str(e),
        )
        return []


def create_health_sensors(
    data: MagicAreasData,
    entities_by_domain: dict[str, list[dict[str, str]]],
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
) -> list[AreaHealthBinarySensor]:
    """Add the health sensors for the area."""
    policy = build_default_aggregate_selection_policy()
    spec = policy.health_spec(
        AggregatePolicyContext(
            entities_by_domain=entities_by_domain,
            feature_configs=data.feature_configs,
            enabled_features=data.enabled_features,
        )
    )

    if not spec:
        if MagicAreasFeatures.HEALTH in data.enabled_features:
            _LOGGER.debug(
                "%s: No binary sensors found for configured health device classes.",
                area_config.name,
            )
        return []

    _LOGGER.debug(
        "%s: Creating health sensor with the following entities: %s",
        area_config.slug,
        str(spec.entity_ids),
    )

    try:
        return [
            AreaHealthBinarySensor(
                area_config,
                coordinator,
                device_class=BinarySensorDeviceClass.PROBLEM,
                entity_ids=spec.entity_ids,
            )
        ]
    except Exception as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating area health sensor: %s",
            area_config.slug,
            str(e),
        )
        return []


def create_aggregate_sensors(
    data: MagicAreasData,
    entities_by_domain: dict[str, list[dict[str, str]]],
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
) -> list[Entity]:
    """Create the aggregate sensors for the area."""
    policy = build_default_aggregate_selection_policy()
    definitions = policy.aggregate_definitions(
        AggregatePolicyContext(
            entities_by_domain=entities_by_domain,
            feature_configs=data.feature_configs,
            enabled_features=data.enabled_features,
        )
    )
    return create_aggregate_sensors_from_definitions(
        definitions=definitions,
        area_config=area_config,
        coordinator=coordinator,
    )


def create_aggregate_sensors_from_definitions(
    *,
    definitions: list[AggregateDefinition],
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
) -> list[Entity]:
    """Create binary-sensor aggregates from canonical aggregate definitions."""
    aggregates: list[Entity] = []

    for definition in definitions:
        if definition.domain != BINARY_SENSOR_DOMAIN:
            continue
        if definition.kind is not AggregateKind.STANDARD:
            continue
        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            definition.device_class,
            len(definition.entity_ids),
            area_config.slug,
        )
        try:
            aggregates.append(
                AreaAggregateBinarySensor(
                    area_config,
                    coordinator,
                    definition.device_class,
                    list(definition.entity_ids),
                )
            )
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error creating '%s' aggregate sensor: %s",
                area_config.slug,
                definition.device_class,
                str(e),
            )

    return aggregates
