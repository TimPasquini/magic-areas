"""Cover automation policy configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from homeassistant.components.cover import CoverDeviceClass

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_COVER_GROUPS_ACCENT_ACTION,
    CONF_COVER_GROUPS_ACCENT_STATES,
    CONF_COVER_GROUPS_DAYLIGHT_ACTION,
    CONF_COVER_GROUPS_DAYLIGHT_STATES,
    CONF_COVER_GROUPS_PRIVACY_ACTION,
    CONF_COVER_GROUPS_PRIVACY_STATES,
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


__all__ = [
    "COVER_PRESET_CONFIG_KEYS",
    "DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES",
    "DEFAULT_COVER_PRESETS",
    "CoverGroupsConfig",
    "CoverPresetAction",
    "CoverPresetConfig",
    "CoverPresetRole",
]
