"""Pure presence state helpers for Magic Areas."""

from __future__ import annotations

from custom_components.magic_areas.area_maps import CONFIGURABLE_AREA_STATE_MAP
from custom_components.magic_areas.area_state import AreaStates


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
