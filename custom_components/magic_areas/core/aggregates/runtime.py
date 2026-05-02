"""Runtime helpers for canonical aggregate definitions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import homeassistant.components.sensor.const
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.aggregates.policy import AggregateDefinition
from custom_components.magic_areas.core.controls import ControlGroupDefinition
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.core.runtime_model import GroupMetadataKey
from custom_components.magic_areas.core.runtime_model import (
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.core.controls import (
    GroupRegistry,
    resolve_group_entity_ids_by_metadata,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.config.feature_readers import (
    aggregates_config,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.core.runtime_model import AreaConfig

AGGREGATE_POLICY_ID = ControlGroupPolicyId.AGGREGATE
_LOGGER = logging.getLogger(__name__)


def aggregate_group_id(*, area_id: str, device_class: str) -> str:
    """Return a stable aggregate group ID for an area/device-class pair."""
    return f"aggregates_{area_id}_aggregate_{device_class}"


def aggregate_managed_surface_unique_id(
    *,
    entry_id: str,
    area_id: str,
    definition: AggregateDefinition,
) -> str:
    """Return the native helper ownership ID for an aggregate definition."""
    domain_key = definition.domain.replace("_", "-")
    role = f"aggregate_{domain_key}_{definition.kind.value}_{definition.device_class}"
    return build_managed_surface_unique_id(
        entry_id=entry_id,
        area_id=area_id,
        feature_id=MagicAreasFeatures.AGGREGATES,
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role=role,
    )


def register_aggregate_definitions(
    *,
    group_registry: GroupRegistry,
    area_id: str,
    definitions: list[AggregateDefinition],
    owner_entry_id: str | None = None,
) -> None:
    """Register aggregate definitions as area defaults in the group registry."""
    group_definitions: list[ControlGroupDefinition] = []
    for definition in definitions:
        group_id = (
            aggregate_managed_surface_unique_id(
                entry_id=owner_entry_id,
                area_id=area_id,
                definition=definition,
            )
            if owner_entry_id
            else aggregate_group_id(
                area_id=area_id,
                device_class=definition.device_class,
            )
        )
        group_definitions.append(
            ControlGroupDefinition(
                group_id=group_id,
                members=definition.entity_ids,
                policy_id=AGGREGATE_POLICY_ID,
                metadata={
                    GroupMetadataKey.AGGREGATE_DOMAIN: definition.domain,
                    GroupMetadataKey.AGGREGATE_DEVICE_CLASS: definition.device_class,
                    GroupMetadataKey.AGGREGATE_KIND: definition.kind.value,
                },
            )
        )

    group_registry.register_area_defaults(
        area_id,
        group_definitions,
        policy_id=AGGREGATE_POLICY_ID,
    )


def resolve_aggregate_entity_ids_by_device_class(
    hass: HomeAssistant,
    *,
    group_registry: GroupRegistry,
    area_id: str,
    domain: str,
) -> dict[str, str]:
    """Resolve aggregate entity IDs keyed by device-class for a domain."""
    domain_matches = resolve_group_entity_ids_by_metadata(
        hass,
        group_registry=group_registry,
        area_id=area_id,
        policy_id=str(AGGREGATE_POLICY_ID),
        domain=domain,
        metadata_key=str(GroupMetadataKey.AGGREGATE_DEVICE_CLASS),
        metadata_filters={str(GroupMetadataKey.AGGREGATE_DOMAIN): domain},
    )
    return domain_matches


def resolve_aggregate_entity_id(
    hass: HomeAssistant,
    *,
    group_registry: GroupRegistry,
    area_id: str,
    domain: str,
    device_class: str,
) -> str | None:
    """Resolve one aggregate entity ID from area/domain/device-class metadata."""
    return resolve_aggregate_entity_ids_by_device_class(
        hass,
        group_registry=group_registry,
        area_id=area_id,
        domain=domain,
    ).get(device_class)


def get_illuminance_threshold_spec(
    hass: HomeAssistant,
    data: MagicAreasData,
    area_config: AreaConfig,
) -> tuple[str, float, float, float] | None:
    """Return illuminance threshold config or None if unavailable."""
    if MagicAreasFeatures.AGGREGATES not in data.enabled_features:  # pragma: no cover
        return None

    config = aggregates_config(data.feature_configs)
    illuminance_threshold = config.illuminance_threshold

    if illuminance_threshold == 0:
        return None

    if (  # pragma: no cover
        homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
        not in config.sensor_device_classes
    ):
        return None

    if homeassistant.components.sensor.const.DOMAIN not in data.entities:
        return None

    illuminance_sensors = [
        sensor
        for sensor in data.entities[homeassistant.components.sensor.const.DOMAIN]
        if ATTR_DEVICE_CLASS in sensor
        and sensor[ATTR_DEVICE_CLASS]
        == homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
    ]

    if not illuminance_sensors:  # pragma: no cover
        return None

    illuminance_threshold_hysteresis_percentage = (
        config.illuminance_threshold_hysteresis_percentage
    )
    illuminance_threshold_hysteresis = 0.0

    if illuminance_threshold_hysteresis_percentage > 0:
        illuminance_threshold_hysteresis = illuminance_threshold * (
            illuminance_threshold_hysteresis_percentage / 100
        )

    illuminance_aggregate_entity_id = resolve_aggregate_entity_id(
        hass,
        group_registry=data.group_registry,
        area_id=area_config.id,
        domain=homeassistant.components.sensor.const.DOMAIN,
        device_class=str(
            homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
        ),
    )
    if not illuminance_aggregate_entity_id:
        _LOGGER.debug(
            "Area '%s': Illuminance aggregate not available yet, skipping threshold sensor",
            area_config.slug,
        )
        return None

    return (
        illuminance_aggregate_entity_id,
        float(illuminance_threshold),
        float(illuminance_threshold_hysteresis),
        float(illuminance_threshold_hysteresis_percentage),
    )
