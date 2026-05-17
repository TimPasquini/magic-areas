"""Binary-sensor entity factories for feature sensors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from custom_components.magic_areas.binary_sensor.ble_tracker import (
    AreaBLETrackerBinarySensor,
)
from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    AreaWaspInABoxBinarySensor,
)
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.config.readers import (
    ble_tracker_config,
)

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


__all__ = [
    "create_ble_tracker_sensor",
    "create_wasp_in_a_box_sensor",
    "EXPECTED_ENTITY_BUILD_ERRORS",
    "log_creation_error",
]
