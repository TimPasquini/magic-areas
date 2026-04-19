"""Binary-sensor entity factories for aggregates and feature sensors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor.ble_tracker import (
    AreaBLETrackerBinarySensor,
)
from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    AreaWaspInABoxBinarySensor,
)
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.aggregates import (
    AggregateDefinition,
    AggregateKind,
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.features.config.readers import (
    ble_tracker_config,
)
from custom_components.magic_areas.policy import AGGREGATE_MODE_ALL

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)

type ExpectedEntityBuildErrors = tuple[
    type[KeyError],
    type[TypeError],
    type[ValueError],
    type[AttributeError],
    type[RuntimeError],
]

EXPECTED_ENTITY_BUILD_ERRORS: ExpectedEntityBuildErrors = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


def log_creation_error(*, area_slug: str, label: str, exc: Exception) -> None:
    """Log a standardized entity creation failure."""
    _LOGGER.error("%s: Error creating %s: %s", area_slug, label, str(exc))


class AreaSensorGroupBinarySensor(MagicGroupEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        device_class: str,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group binary sensor."""
        MagicGroupEntity.__init__(
            self,
            area_config=area_config,
            coordinator=coordinator,
            domain=BINARY_SENSOR_DOMAIN,
            member_entity_ids=entity_ids,
            translation_key=device_class,
        )
        BinarySensorGroup.__init__(
            self,
            device_class=(
                BinarySensorDeviceClass(device_class) if device_class else None
            ),
            name="",
            unique_id=self._attr_unique_id,
            entity_ids=self.member_entity_ids,
            mode=device_class in AGGREGATE_MODE_ALL,
        )
        delattr(self, "_attr_name")


class AreaAggregateBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.AGGREGATES


class AreaHealthBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.HEALTH


def create_aggregate_sensors_from_definitions(
    *,
    definitions: list[AggregateDefinition],
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
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
        except EXPECTED_ENTITY_BUILD_ERRORS as exc:  # pragma: no cover
            log_creation_error(
                area_slug=area_config.slug,
                label=f"'{definition.device_class}' aggregate sensor",
                exc=exc,
            )

    return aggregates


def create_wasp_in_a_box_sensor(
    data: MagicAreasData,
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
) -> list[AreaWaspInABoxBinarySensor]:
    """Add the Wasp in a box sensor for the area."""
    if (
        MagicAreasFeatures.WASP_IN_A_BOX not in data.enabled_features
        or MagicAreasFeatures.AGGREGATES not in data.enabled_features
    ):
        return []

    try:
        return [AreaWaspInABoxBinarySensor(area_config, coordinator)]
    except EXPECTED_ENTITY_BUILD_ERRORS as exc:  # pragma: no cover
        log_creation_error(
            area_slug=area_config.slug,
            label="wasp in a box sensor",
            exc=exc,
        )
        return []


def create_ble_tracker_sensor(
    data: MagicAreasData,
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
) -> list[AreaBLETrackerBinarySensor]:
    """Add the BLE tracker sensor for the area."""
    if MagicAreasFeatures.BLE_TRACKER not in data.enabled_features:
        return []

    if not ble_tracker_config(data.feature_configs).entities:
        return []

    try:
        return [AreaBLETrackerBinarySensor(area_config, coordinator)]
    except EXPECTED_ENTITY_BUILD_ERRORS as exc:  # pragma: no cover
        log_creation_error(
            area_slug=area_config.slug,
            label="BLE tracker sensor",
            exc=exc,
        )
        return []


def create_health_sensors(
    data: MagicAreasData,
    entities_by_domain: dict[str, list[dict[str, str]]],
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
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
    except EXPECTED_ENTITY_BUILD_ERRORS as exc:  # pragma: no cover
        log_creation_error(
            area_slug=area_config.slug,
            label="area health sensor",
            exc=exc,
        )
        return []


__all__ = [
    "AreaAggregateBinarySensor",
    "AreaHealthBinarySensor",
    "create_aggregate_sensors_from_definitions",
    "create_ble_tracker_sensor",
    "create_health_sensors",
    "create_wasp_in_a_box_sensor",
    "EXPECTED_ENTITY_BUILD_ERRORS",
    "log_creation_error",
]
