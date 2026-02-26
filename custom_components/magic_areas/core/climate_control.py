"""Climate control policy for Magic Areas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from custom_components.magic_areas.config_keys import (
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
    DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
    DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
    DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
)
from custom_components.magic_areas.core.state_priority import (
    get_highest_priority_state,
)
from custom_components.magic_areas.area_state import AreaStates


@dataclass(slots=True)
class ClimatePresetPolicy:
    """Policy for selecting climate preset based on area state.

    Attributes:
        preset_map: Mapping from area state to climate preset name
        priority_order: State priority order (defaults to SLEEP > EXTENDED > OCCUPIED > CLEAR)

    """

    preset_map: dict[str, str | None]
    priority_order: Sequence[str] | None = None

    def select_preset_for_state_change(
        self,
        new_states: Sequence[str],
        current_states: Sequence[str],
    ) -> str | None:
        """Determine which preset to apply after state change.

        Args:
            new_states: States that were just added
            current_states: All currently active states

        Returns:
            Preset name to apply, or None if no action needed

        Logic:
            1. If CLEAR was just added, apply CLEAR preset (if configured)
            2. Otherwise, find highest priority new state with a configured preset
            3. Returns None if no applicable preset found

        """
        # CLEAR always takes precedence (ends occupancy)
        if AreaStates.CLEAR in new_states:
            return self.preset_map.get(AreaStates.CLEAR)

        # Use default priority order if not specified
        priority = self.priority_order or [
            AreaStates.SLEEP,
            AreaStates.EXTENDED,
            AreaStates.OCCUPIED,
        ]

        # Find highest priority new state with a configured preset
        highest_state = get_highest_priority_state(new_states, priority)
        if highest_state:
            return self.preset_map.get(highest_state)

        return None


def build_preset_policy(feature_config: dict[str, Any]) -> ClimatePresetPolicy:
    """Build climate preset policy from feature configuration.

    Args:
        feature_config: Climate control feature configuration

    Returns:
        Configured ClimatePresetPolicy instance

    """

    preset_map: dict[str, str | None] = {
        str(AreaStates.CLEAR): feature_config.get(
            CONF_CLIMATE_CONTROL_PRESET_CLEAR, DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR
        ),
        str(AreaStates.OCCUPIED): feature_config.get(
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
            DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
        ),
        str(AreaStates.SLEEP): feature_config.get(
            CONF_CLIMATE_CONTROL_PRESET_SLEEP, DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP
        ),
        str(AreaStates.EXTENDED): feature_config.get(
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
            DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
        ),
    }

    return ClimatePresetPolicy(preset_map=preset_map)
