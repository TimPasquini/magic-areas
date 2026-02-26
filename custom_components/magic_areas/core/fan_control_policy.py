"""Fan control policy for Magic Areas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from custom_components.magic_areas.config_keys import (
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_FAN_GROUPS_REQUIRED_STATE,
    DEFAULT_FAN_GROUPS_SETPOINT,
)
from custom_components.magic_areas.area_state import AreaStates


@dataclass(slots=True)
class FanControlDecision:
    """Fan control decision result."""

    should_turn_on: bool
    should_turn_off: bool
    reason: str  # For debugging/logging


@dataclass(slots=True)
class FanControlPolicy:
    """Policy for controlling fans based on area state and sensor values.

    Attributes:
        setpoint: Temperature/humidity/etc threshold for fan activation
        required_state: Area state required for fan operation (e.g., "occupied")

    """

    setpoint: float
    required_state: str

    def evaluate(
        self,
        current_states: Sequence[str],
        sensor_value: float | None,
    ) -> FanControlDecision:
        """Evaluate whether fan should turn on or off.

        Args:
            current_states: Currently active area states
            sensor_value: Current value from tracked aggregate sensor (or None if unavailable)

        Returns:
            FanControlDecision with action and reason

        Logic:
            1. If area is CLEAR -> turn off
            2. If required state not present -> turn off
            3. If sensor unavailable -> turn off (safe default)
            4. If sensor >= setpoint -> turn on
            5. If sensor < setpoint -> turn off

        """
        # Area clear -> always turn off
        if AreaStates.CLEAR in current_states:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason="area_clear",
            )

        # Required state not met -> turn off
        if self.required_state not in current_states:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason=f"required_state_not_met ({self.required_state})",
            )

        # Sensor unavailable -> turn off (safe default)
        if sensor_value is None:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason="sensor_unavailable",
            )

        # Check setpoint
        if sensor_value >= self.setpoint:
            return FanControlDecision(
                should_turn_on=True,
                should_turn_off=False,
                reason=f"setpoint_reached ({sensor_value:.1f} >= {self.setpoint:.1f})",
            )
        else:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason=f"below_setpoint ({sensor_value:.1f} < {self.setpoint:.1f})",
            )


def build_fan_policy(feature_config: dict[str, Any]) -> FanControlPolicy:
    """Build fan control policy from feature configuration.

    Args:
        feature_config: Fan groups feature configuration

    Returns:
        Configured FanControlPolicy instance

    """

    setpoint = float(
        feature_config.get(CONF_FAN_GROUPS_SETPOINT, DEFAULT_FAN_GROUPS_SETPOINT)
    )
    required_state = feature_config.get(
        CONF_FAN_GROUPS_REQUIRED_STATE, DEFAULT_FAN_GROUPS_REQUIRED_STATE
    )

    return FanControlPolicy(setpoint=setpoint, required_state=required_state)
