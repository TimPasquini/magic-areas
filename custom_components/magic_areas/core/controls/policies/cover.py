"""Cover automation policy configuration and control-group adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.const import (
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    STATE_CLOSED,
    STATE_OPEN,
)

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_COVER_GROUPS_ACCENT_ACTION,
    CONF_COVER_GROUPS_ACCENT_STATES,
    CONF_COVER_GROUPS_DAYLIGHT_ACTION,
    CONF_COVER_GROUPS_DAYLIGHT_STATES,
    CONF_COVER_GROUPS_PRIVACY_ACTION,
    CONF_COVER_GROUPS_PRIVACY_STATES,
)
from custom_components.magic_areas.core.controls.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
)

DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES: tuple[str, ...] = (
    CoverDeviceClass.BLIND.value,
    CoverDeviceClass.CURTAIN.value,
    CoverDeviceClass.SHADE.value,
    CoverDeviceClass.SHUTTER.value,
    CoverDeviceClass.WINDOW.value,
)


class CoverPresetRole(StrEnum):
    """Built-in cover automation preset roles."""

    DAYLIGHT = "daylight"
    PRIVACY = "privacy"
    ACCENT = "accent"


class CoverPresetAction(StrEnum):
    """Configured cover action for one preset role."""

    NONE = "none"
    OPEN = "open"
    CLOSE = "close"


@dataclass(frozen=True, slots=True)
class CoverPresetConfig:
    """Normalized config for one cover preset role."""

    role: CoverPresetRole
    action: CoverPresetAction
    states: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CoverGroupsConfig:
    """Normalized config for cover automation."""

    automation_device_classes: tuple[str, ...]
    manual_hold_seconds: int
    presets: tuple[CoverPresetConfig, ...]


@dataclass(frozen=True, slots=True)
class CoverPolicySignals:
    """Typed runtime inputs for cover policy adapters."""

    cover_group_entity_ids: Mapping[str, str]
    cover_group_states: Mapping[str, str | None]
    manual_hold_active: bool = False

    @classmethod
    def from_signals(cls, signals: object) -> CoverPolicySignals:
        """Parse typed cover signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        return cls(cover_group_entity_ids={}, cover_group_states={})


@dataclass(frozen=True, slots=True)
class CoverPresetDecision:
    """Pure cover preset evaluation result."""

    action: CoverPresetAction
    role: CoverPresetRole | None
    reason: str


@dataclass(frozen=True, slots=True)
class CoverControlGroupPolicy(ControlGroupPolicy):
    """Canonical control-group policy adapter for cover automation."""

    config: CoverGroupsConfig

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate cover presets for a canonical control-group context."""
        signals = CoverPolicySignals.from_signals(context.signals)
        decision = evaluate_cover_presets(
            self.config,
            current_states=context.current_states,
            manual_hold_active=signals.manual_hold_active,
        )
        return cover_preset_decision_to_control_group(
            decision=decision,
            cover_group_entity_ids=signals.cover_group_entity_ids,
            cover_group_states=signals.cover_group_states,
        )


COVER_PRESET_CONFIG_KEYS: dict[CoverPresetRole, tuple[str, str]] = {
    CoverPresetRole.DAYLIGHT: (
        CONF_COVER_GROUPS_DAYLIGHT_ACTION,
        CONF_COVER_GROUPS_DAYLIGHT_STATES,
    ),
    CoverPresetRole.PRIVACY: (
        CONF_COVER_GROUPS_PRIVACY_ACTION,
        CONF_COVER_GROUPS_PRIVACY_STATES,
    ),
    CoverPresetRole.ACCENT: (
        CONF_COVER_GROUPS_ACCENT_ACTION,
        CONF_COVER_GROUPS_ACCENT_STATES,
    ),
}

DEFAULT_COVER_PRESETS: dict[CoverPresetRole, CoverPresetConfig] = {
    CoverPresetRole.DAYLIGHT: CoverPresetConfig(
        role=CoverPresetRole.DAYLIGHT,
        action=CoverPresetAction.OPEN,
        states=(AreaStates.OCCUPIED.value, AreaStates.EXTENDED.value),
    ),
    CoverPresetRole.PRIVACY: CoverPresetConfig(
        role=CoverPresetRole.PRIVACY,
        action=CoverPresetAction.CLOSE,
        states=(AreaStates.SLEEP.value,),
    ),
    CoverPresetRole.ACCENT: CoverPresetConfig(
        role=CoverPresetRole.ACCENT,
        action=CoverPresetAction.CLOSE,
        states=(AreaStates.ACCENT.value,),
    ),
}


def build_cover_control_group_policy(
    config: CoverGroupsConfig,
) -> CoverControlGroupPolicy:
    """Build a cover control-group policy adapter."""
    return CoverControlGroupPolicy(config=config)


def evaluate_cover_presets(
    config: CoverGroupsConfig,
    *,
    current_states: Sequence[str],
    manual_hold_active: bool = False,
) -> CoverPresetDecision:
    """Evaluate configured cover presets and return the selected action."""
    if manual_hold_active:
        return CoverPresetDecision(
            action=CoverPresetAction.NONE,
            role=None,
            reason="manual_hold_active",
        )

    current_state_set = {str(state) for state in current_states}
    presets = {preset.role: preset for preset in config.presets}

    for role in (CoverPresetRole.PRIVACY, CoverPresetRole.ACCENT):
        preset = presets.get(role)
        if preset and _preset_matches(preset, current_state_set):
            return CoverPresetDecision(
                action=preset.action,
                role=role,
                reason=f"{role.value}_preset_matched",
            )

    daylight = presets.get(CoverPresetRole.DAYLIGHT)
    if daylight and _preset_matches(daylight, current_state_set):
        return CoverPresetDecision(
            action=daylight.action,
            role=CoverPresetRole.DAYLIGHT,
            reason="daylight_preset_matched",
        )

    return CoverPresetDecision(
        action=CoverPresetAction.NONE,
        role=None,
        reason="no_cover_preset_matched",
    )


def cover_preset_decision_to_control_group(
    *,
    decision: CoverPresetDecision,
    cover_group_entity_ids: Mapping[str, str],
    cover_group_states: Mapping[str, str | None],
) -> ControlGroupDecision:
    """Translate a cover preset decision into cover service actions."""
    if decision.action is CoverPresetAction.NONE:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason=decision.reason,
        )

    targets = tuple(sorted(set(cover_group_entity_ids.values())))
    if not targets:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason=f"{decision.reason}_no_cover_targets",
        )

    if decision.action is CoverPresetAction.OPEN:
        service = SERVICE_OPEN_COVER
        actionable_targets = tuple(
            target for target in targets if cover_group_states.get(target) != STATE_OPEN
        )
    else:
        service = SERVICE_CLOSE_COVER
        actionable_targets = tuple(
            target
            for target in targets
            if cover_group_states.get(target) != STATE_CLOSED
        )

    if not actionable_targets:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason=f"{decision.reason}_already_applied",
        )

    return ControlGroupDecision(
        action_type=ControlActionType.ACTIVATE,
        reason=decision.reason,
        actions=(
            ControlAction(
                domain=COVER_DOMAIN,
                service=service,
                target_entity_ids=actionable_targets,
            ),
        ),
    )


def _preset_matches(preset: CoverPresetConfig, current_states: set[str]) -> bool:
    """Return whether a preset applies to current room states."""
    return bool(preset.states) and any(state in current_states for state in preset.states)


__all__ = [
    "COVER_PRESET_CONFIG_KEYS",
    "DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES",
    "DEFAULT_COVER_PRESETS",
    "CoverControlGroupPolicy",
    "CoverGroupsConfig",
    "CoverPolicySignals",
    "CoverPresetAction",
    "CoverPresetConfig",
    "CoverPresetDecision",
    "CoverPresetRole",
    "build_cover_control_group_policy",
    "cover_preset_decision_to_control_group",
    "evaluate_cover_presets",
]
