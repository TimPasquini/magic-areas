"""Pure presence selection helpers for Magic Areas."""

from __future__ import annotations

from enum import Enum
from typing import Any, TYPE_CHECKING

from custom_components.magic_areas.area_maps import CONFIGURABLE_AREA_STATE_MAP
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.ha_domains import BINARY_SENSOR_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.entity_ids import EntityReferences


def build_presence_sensors(
    *,
    entities_by_domain: dict[str, list[dict[str, str]]],
    config: dict[str, Any],
    slug: str,
    enabled_features: set[str],
    entity_references: EntityReferences | None = None,
) -> list[str]:
    """Return list of entity ids used for presence tracking."""
    sensors: list[str] = []

    valid_presence_platforms = config.get(
        CONF_PRESENCE_DEVICE_PLATFORMS, DEFAULT_PRESENCE_DEVICE_PLATFORMS
    )
    allowed_device_classes = [
        dc.value if isinstance(dc, Enum) else dc
        for dc in config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS, [])
    ]

    for component, entities in entities_by_domain.items():
        if component not in valid_presence_platforms:
            continue

        for entity in entities:
            if not entity:
                continue

            if component == BINARY_SENSOR_DOMAIN:
                if ATTR_DEVICE_CLASS not in entity:
                    continue

                if entity[ATTR_DEVICE_CLASS] not in allowed_device_classes:
                    continue

            sensors.append(entity[ATTR_ENTITY_ID])

    # Resolve magic_areas-generated presence sensors from entity references
    if MagicAreasFeatures.PRESENCE_HOLD in enabled_features:
        if entity_references and entity_references.presence_hold_switch:
            sensors.append(entity_references.presence_hold_switch)

    if MagicAreasFeatures.BLE_TRACKER in enabled_features:
        if entity_references and entity_references.ble_tracker_monitor:
            sensors.append(entity_references.ble_tracker_monitor)

    if (
        MagicAreasFeatures.AGGREGATES in enabled_features
        and MagicAreasFeatures.WASP_IN_A_BOX in enabled_features
    ):
        if entity_references and entity_references.wasp_in_a_box_sensor:
            sensors.append(entity_references.wasp_in_a_box_sensor)

    return sensors


def compute_secondary_states(
    *,
    secondary_states_config: dict[str, str | None],
    entity_states: dict[str, str | None],
    valid_on_states: set[str],
) -> list[str]:
    """Compute which secondary states are currently active from entity readings.

    Args:
        secondary_states_config: Mapping from config-key names to entity IDs
            (the value stored at CONF_SECONDARY_STATES in area config).
        entity_states: Snapshot of entity states keyed by entity_id (None if
            the entity was not found in the registry).
        valid_on_states: State strings that count as "on" for binary-style
            sensors (e.g. {"on", "above_horizon"}).

    Returns:
        List of active AreaStates string values.

    """
    # Determine which configurable states have a sensor entity assigned
    configured_states: list[AreaStates] = [
        state
        for state, config_key in CONFIGURABLE_AREA_STATE_MAP.items()
        if secondary_states_config.get(config_key)
    ]

    active_states: list[str] = []

    # DARK is on by default when no light sensor is configured
    if AreaStates.DARK not in configured_states:
        active_states.append(AreaStates.DARK)

    # DARK uses inverted logic: sensor low (below horizon) → area is dark
    inverted_states: set[AreaStates] = {AreaStates.DARK}

    for configurable_state in configured_states:
        config_key = CONFIGURABLE_AREA_STATE_MAP[configurable_state]
        entity_id = secondary_states_config.get(config_key)
        if not entity_id:
            continue

        state_value = entity_states.get(entity_id)
        if state_value is None:
            continue

        has_valid_state = state_value.lower() in valid_on_states

        if configurable_state in inverted_states:
            if not has_valid_state:
                active_states.append(str(configurable_state))
        else:
            if has_valid_state:
                active_states.append(str(configurable_state))

    # Derive BRIGHT: light sensor configured but area is not dark
    if AreaStates.DARK in configured_states and AreaStates.DARK not in active_states:
        active_states.append(AreaStates.BRIGHT)

    return active_states
