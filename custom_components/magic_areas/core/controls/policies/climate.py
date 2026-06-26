"""Climate control policy for Magic Areas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_PRESET_MODE,
)
from custom_components.magic_areas.config_keys.area import (
    CLIMATE_CONTROL_PRESET_KEY_BY_STATE,
)
from custom_components.magic_areas.option_defaults import feature_option_default

from custom_components.magic_areas.core.state_priority import (
    get_highest_priority_state,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
)

__all__ = [
    "ClimateControlGroupPolicy",
    "ClimatePolicySignals",
    "ClimatePresetPolicy",
    "build_climate_control_group_policy",
    "build_preset_policy",
    "climate_preset_to_control_group",
]


@dataclass(slots=True)
class ClimatePresetPolicy:
    """Policy for selecting climate preset based on area state."""

    preset_map: Mapping[str, str | None]
    priority_order: Sequence[str] | None = None

    def select_preset_for_state_change(
        self,
        new_states: Sequence[str],
        current_states: Sequence[str],
    ) -> str | None:
        """Determine which preset to apply after state change."""
        del current_states
        if AreaStates.CLEAR in new_states:
            return self.preset_map.get(AreaStates.CLEAR)

        priority = self.priority_order or [
            AreaStates.SLEEP,
            AreaStates.EXTENDED,
            AreaStates.OCCUPIED,
        ]

        highest_state = get_highest_priority_state(new_states, priority)
        if highest_state:
            return self.preset_map.get(highest_state)

        return None


def build_preset_policy(feature_config: Mapping[str, object]) -> ClimatePresetPolicy:
    """Build climate preset policy from feature configuration."""
    preset_map = {
        state: str(
            feature_config.get(
                key,
                feature_option_default(MagicAreasFeatures.CLIMATE_CONTROL, key),
            )
        )
        for state, key in CLIMATE_CONTROL_PRESET_KEY_BY_STATE.items()
    }
    return ClimatePresetPolicy(preset_map=preset_map)


@dataclass(slots=True)
class ClimateControlGroupPolicy(ControlGroupPolicy):
    """Canonical control-group policy adapter for climate control."""

    preset_policy: ClimatePresetPolicy

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate climate control for a canonical control-group context."""
        signals = ClimatePolicySignals.from_signals(context.signals)
        climate_entity_id = signals.climate_entity_id
        preset_name = signals.preset_name

        if not preset_name:
            preset_name = self.preset_policy.select_preset_for_state_change(
                context.new_states,
                context.current_states,
            )

        return climate_preset_to_control_group(
            climate_entity_id=climate_entity_id,
            preset_name=preset_name,
        )


def build_climate_control_group_policy(
    feature_config: Mapping[str, object],
) -> ClimateControlGroupPolicy:
    """Build canonical climate control-group policy from feature config."""
    return ClimateControlGroupPolicy(preset_policy=build_preset_policy(feature_config))


@dataclass(frozen=True, slots=True)
class ClimatePolicySignals:
    """Typed runtime inputs for climate policy adapters."""

    climate_entity_id: str | None
    preset_name: str | None

    @classmethod
    def from_signals(cls, signals: object) -> ClimatePolicySignals:
        """Parse typed climate signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        return cls(climate_entity_id=None, preset_name=None)


def climate_preset_to_control_group(
    climate_entity_id: str | None, preset_name: str | None
) -> ControlGroupDecision:
    """Translate a selected climate preset into control-group actions."""
    if not climate_entity_id:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="climate_entity_unavailable",
        )

    if not preset_name:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="no_preset_selected",
        )

    return ControlGroupDecision(
        action_type=ControlActionType.ACTIVATE,
        reason=f"apply_preset_{preset_name}",
        actions=(
            ControlAction(
                domain=CLIMATE_DOMAIN,
                service=SERVICE_SET_PRESET_MODE,
                target_entity_ids=(climate_entity_id,),
                service_data={ATTR_PRESET_MODE: preset_name},
            ),
        ),
    )
