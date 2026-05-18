"""Light group configuration constants and tables."""

from dataclasses import dataclass
from collections.abc import Mapping

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from custom_components.magic_areas.core.config import feature_config_slice
from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
)
from custom_components.magic_areas.core.control_intents import (
    AdaptiveLightingSwitchSet,
    managed_switch_set_from_hass_registry,
    managed_adaptive_lighting_config,
    switch_set_from_explicit_refs,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

FeatureConfigValue = object
FeatureConfigDict = dict[str, FeatureConfigValue]
FeatureConfigMap = Mapping[str | MagicAreasFeatures, Mapping[str, FeatureConfigValue]]

# Light group options
CONF_OVERHEAD_LIGHTS = "overhead_lights"  # cv.entity_ids
CONF_OVERHEAD_LIGHTS_STATES = "overhead_lights_states"  # cv.ensure_list
CONF_OVERHEAD_LIGHTS_ACT_ON = "overhead_lights_act_on"  # cv.ensure_list
CONF_SLEEP_LIGHTS = "sleep_lights"
CONF_SLEEP_LIGHTS_STATES = "sleep_lights_states"
CONF_SLEEP_LIGHTS_ACT_ON = "sleep_lights_act_on"
CONF_ACCENT_LIGHTS = "accent_lights"
CONF_ACCENT_LIGHTS_STATES = "accent_lights_states"
CONF_ACCENT_LIGHTS_ACT_ON = "accent_lights_act_on"
CONF_TASK_LIGHTS = "task_lights"
CONF_TASK_LIGHTS_STATES = "task_lights_states"
CONF_TASK_LIGHTS_ACT_ON = "task_lights_act_on"
LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE = "occupancy"
LIGHT_GROUP_ACT_ON_STATE_CHANGE = "state"
LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT = "inhibit"
LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY = "advisory"
LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE = "adaptive"
LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN = "sun"
LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX = "outside_lux"
LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE = "none"
LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE = "ignore"
LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING = "adopt_existing"
LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE = "manage"
LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX = "adaptive_lighting_pair_"

LIGHT_GROUP_DEFAULT_ICON = "mdi:lightbulb-group"


@dataclass(frozen=True, slots=True)
class LightGroupPreset:
    """Built-in light-group preset declaration."""

    category: str
    states_key: str
    act_on_key: str
    icon: str
    default_states: tuple[str, ...]
    default_act_on: tuple[str, ...] = (
        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    )


LIGHT_GROUP_PRESETS = (
    LightGroupPreset(
        category=CONF_OVERHEAD_LIGHTS,
        states_key=CONF_OVERHEAD_LIGHTS_STATES,
        act_on_key=CONF_OVERHEAD_LIGHTS_ACT_ON,
        icon="mdi:ceiling-light",
        default_states=("occupied",),
    ),
    LightGroupPreset(
        category=CONF_SLEEP_LIGHTS,
        states_key=CONF_SLEEP_LIGHTS_STATES,
        act_on_key=CONF_SLEEP_LIGHTS_ACT_ON,
        icon="mdi:sleep",
        default_states=(),
    ),
    LightGroupPreset(
        category=CONF_ACCENT_LIGHTS,
        states_key=CONF_ACCENT_LIGHTS_STATES,
        act_on_key=CONF_ACCENT_LIGHTS_ACT_ON,
        icon="mdi:outdoor-lamp",
        default_states=(),
    ),
    LightGroupPreset(
        category=CONF_TASK_LIGHTS,
        states_key=CONF_TASK_LIGHTS_STATES,
        act_on_key=CONF_TASK_LIGHTS_ACT_ON,
        icon="mdi:desk-lamp",
        default_states=(),
    ),
)

LIGHT_GROUP_PRESET_BY_CATEGORY = {
    preset.category: preset for preset in LIGHT_GROUP_PRESETS
}


def get_light_group_preset(category: str) -> LightGroupPreset | None:
    """Return built-in preset by category key when available."""
    return LIGHT_GROUP_PRESET_BY_CATEGORY.get(category)


def feature_string_list(
    feature_config: FeatureConfigDict,
    key: str,
    *,
    default: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Return a normalized list[str] from feature config."""
    fallback = [] if default is None else [str(item) for item in default]
    value = feature_config.get(key, fallback)
    if not isinstance(value, list):
        return fallback
    return [str(item) for item in value]


def light_groups_feature_config(
    feature_configs: FeatureConfigMap,
) -> FeatureConfigDict:
    """Return normalized light-group feature config from feature config map."""
    return feature_config_slice(feature_configs, MagicAreasFeatures.LIGHT_GROUPS)


def preset_members(
    feature_config: FeatureConfigDict,
    preset: LightGroupPreset,
    *,
    available_entities: list[str],
) -> list[str]:
    """Return configured entities for one preset limited to known area lights."""
    configured = feature_config.get(preset.category, [])
    if not isinstance(configured, list):
        return []
    return [entity_id for entity_id in configured if entity_id in available_entities]


def preset_states(
    feature_config: FeatureConfigDict, preset: LightGroupPreset
) -> list[str]:
    """Return configured state triggers for one preset."""
    return feature_string_list(feature_config, preset.states_key, default=[])


def preset_act_on_modes(
    feature_config: FeatureConfigDict, preset: LightGroupPreset
) -> list[str]:
    """Return configured act-on modes for one preset."""
    return feature_string_list(
        feature_config,
        preset.act_on_key,
        default=preset.default_act_on,
    )


def brightness_mode(feature_config: FeatureConfigDict) -> str:
    """Return configured bright-behavior mode."""
    value = feature_config.get(
        CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
        LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
    )
    if not isinstance(value, str):
        return LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT
    normalized = value.lower()
    if normalized in {
        LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
        LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
        LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    }:
        return normalized
    return LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT


def adaptive_lighting_mode(feature_config: FeatureConfigDict) -> str:
    """Return configured Adaptive Lighting coordination mode."""
    value = feature_config.get(
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
    )
    if not isinstance(value, str):
        return LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
    normalized = value.lower()
    if normalized in {
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    }:
        return normalized
    return LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE


def adaptive_lighting_pair_key(category: str) -> str:
    """Return transient options-flow key for pairing one role to an AL switch set."""
    return f"{LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX}{category}"


def adaptive_lighting_managed_roles(feature_config: FeatureConfigDict) -> list[str]:
    """Return role categories selected for MA-managed Adaptive Lighting configs."""
    value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES, [])
    if not isinstance(value, list):
        return []
    return [str(role) for role in value if isinstance(role, str)]


def adaptive_lighting_manage_all_lights(feature_config: FeatureConfigDict) -> bool:
    """Return whether manage mode should create a room-level AL config."""
    value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
    try:
        return bool(cv.boolean(value))
    except vol.Invalid:
        return False


def adaptive_lighting_manages_role(
    feature_config: FeatureConfigDict, category: str
) -> bool:
    """Return whether manage mode should own one AL role config."""
    if category == "all_lights":
        return adaptive_lighting_manage_all_lights(feature_config)
    return category in adaptive_lighting_managed_roles(feature_config)


def _int_option(feature_config: FeatureConfigDict, key: str, default: int = 0) -> int:
    """Read integer option from feature config with safe fallback."""
    value = feature_config.get(key, default)
    if not isinstance(value, str | bytes | bytearray | int | float):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def bright_min_on_seconds(feature_config: FeatureConfigDict) -> int:
    """Return adaptive min-on-time threshold in seconds."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS, default=0
    )


def bright_dwell_seconds(feature_config: FeatureConfigDict) -> int:
    """Return adaptive bright dwell threshold in seconds."""
    return _int_option(feature_config, CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS, default=0)


def outside_context_source(feature_config: FeatureConfigDict) -> str:
    """Return outside context source for adaptive bright-off gating."""
    value = feature_config.get(
        CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
        LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
    )
    if not isinstance(value, str):
        return LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN
    normalized = value.lower()
    if normalized in {
        LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
        LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX,
        LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE,
    }:
        return normalized
    return LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN


def inside_bright_entity(feature_config: FeatureConfigDict) -> str | None:
    """Return configured inside-bright binary entity (if any)."""
    value = feature_config.get(CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY)
    if isinstance(value, str) and value:
        return value
    return None


def outside_bright_entity(feature_config: FeatureConfigDict) -> str | None:
    """Return configured outside-bright binary entity (if any)."""
    value = feature_config.get(CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY)
    if isinstance(value, str) and value:
        return value
    return None


def outside_lux_entity(feature_config: FeatureConfigDict) -> str | None:
    """Return configured outside lux entity (if any)."""
    value = feature_config.get(CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY)
    if isinstance(value, str) and value:
        return value
    return None


def outside_lux_min(feature_config: FeatureConfigDict) -> int:
    """Return minimum outside lux threshold for adaptive bright-off gating."""
    return _int_option(feature_config, CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN, default=0)


def outside_lux_inside_entity(feature_config: FeatureConfigDict) -> str | None:
    """Return configured inside lux entity for outside/inside contrast checks."""
    value = feature_config.get(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY)
    if isinstance(value, str) and value:
        return value
    return None


def outside_lux_inside_delta(feature_config: FeatureConfigDict) -> int:
    """Return required outside-inside lux delta for adaptive bright-off gating."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA, default=0
    )


def outside_lux_inside_ratio_min_percent(feature_config: FeatureConfigDict) -> int:
    """Return required outside/inside lux ratio percentage (100 = 1.0x)."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT, default=0
    )


def bright_attribution_hold_seconds(feature_config: FeatureConfigDict) -> int:
    """Return suppressive hold window after controlled light activity."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS, default=0
    )


def adaptive_require_ambient_rise(feature_config: FeatureConfigDict) -> bool:
    """Return whether adaptive bright-off requires inside ambient rise evidence."""
    value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE, False)
    return bool(value)


def ambient_rise_window_seconds(feature_config: FeatureConfigDict) -> int:
    """Return lookback window used by ambient-rise detector."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS, default=120
    )


def ambient_rise_min_delta(feature_config: FeatureConfigDict) -> int:
    """Return minimum inside lux rise required within the ambient window."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA, default=20
    )


def adaptive_lighting_diagnostics(
    feature_config: FeatureConfigDict,
    *,
    hass: HomeAssistant | None = None,
    area_id: str,
    category: str,
    area_name: str | None = None,
    light_entity_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, object]:
    """Return concise diagnostics for AL coordination availability."""
    mode = adaptive_lighting_mode(feature_config)
    base: dict[str, object] = {
        "mode": mode,
        "role": category,
        "active": False,
    }

    if mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE:
        return {**base, "reason": "mode_ignore"}

    if mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE:
        if not adaptive_lighting_manages_role(feature_config, category):
            return {**base, "reason": "role_not_managed"}
        if area_name is None:
            return {**base, "reason": "missing_area_name"}
        desired = managed_adaptive_lighting_config(
            area_id=area_id,
            area_name=area_name,
            role=category,
            light_entity_ids=light_entity_ids,
        )
        if desired is None:
            return {**base, "reason": "no_light_members"}
        switch_set = (
            managed_switch_set_from_hass_registry(hass, desired)
            if hass is not None
            else None
        )
        return {
            **base,
            "active": True,
            "reason": "associated",
            "main_switch_entity_id": (
                switch_set.main_switch_entity_id
                if switch_set is not None
                else desired.switch_refs["main"]
            ),
        }

    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if not isinstance(raw_switch_sets, Mapping):
        return {**base, "reason": "missing_switch_sets"}

    raw_switch_refs = raw_switch_sets.get(category)
    if not isinstance(raw_switch_refs, Mapping):
        return {**base, "reason": "no_role_pairing"}

    switch_refs = {
        str(key): str(value)
        for key, value in raw_switch_refs.items()
        if isinstance(key, str) and isinstance(value, str)
    }
    switch_set = switch_set_from_explicit_refs(
        area_id=area_id,
        role=category,
        switch_refs=switch_refs,
    )
    if switch_set is None:
        return {**base, "reason": "incomplete_switch_set"}
    return {
        **base,
        "active": True,
        "reason": "associated",
        "main_switch_entity_id": switch_set.main_switch_entity_id,
    }


def adaptive_lighting_switch_set(
    feature_config: FeatureConfigDict,
    *,
    hass: HomeAssistant | None = None,
    area_id: str,
    category: str,
    area_name: str | None = None,
    light_entity_ids: list[str] | tuple[str, ...] = (),
) -> AdaptiveLightingSwitchSet | None:
    """Return explicitly associated Adaptive Lighting switches for a light role."""
    if (
        adaptive_lighting_mode(feature_config)
        == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
    ):
        if not adaptive_lighting_manages_role(feature_config, category):
            return None
        if area_name is None:
            return None
        desired = managed_adaptive_lighting_config(
            area_id=area_id,
            area_name=area_name,
            role=category,
            light_entity_ids=light_entity_ids,
        )
        if desired is None:
            return None
        if hass is not None:
            return managed_switch_set_from_hass_registry(hass, desired)
        return switch_set_from_explicit_refs(
            area_id=area_id,
            role=category,
            switch_refs=desired.switch_refs,
        )

    if (
        adaptive_lighting_mode(feature_config)
        != LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
    ):
        return None

    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if not isinstance(raw_switch_sets, Mapping):
        return None

    raw_switch_refs = raw_switch_sets.get(category)
    if not isinstance(raw_switch_refs, Mapping):
        return None

    switch_refs = {
        str(key): str(value)
        for key, value in raw_switch_refs.items()
        if isinstance(key, str) and isinstance(value, str)
    }
    return switch_set_from_explicit_refs(
        area_id=area_id,
        role=category,
        switch_refs=switch_refs,
    )


def build_light_group_feature_schema() -> vol.Schema:
    """Build light-group feature schema from preset declarations."""
    schema: dict[object, object] = {}
    for preset in LIGHT_GROUP_PRESETS:
        schema[vol.Optional(preset.category, default=[])] = cv.entity_ids
        schema[vol.Optional(preset.states_key, default=list(preset.default_states))] = (
            cv.ensure_list
        )
        schema[vol.Optional(preset.act_on_key, default=list(preset.default_act_on))] = (
            cv.ensure_list
        )
    schema[
        vol.Optional(
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
            default=LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
        )
    ] = cv.string
    schema[
        vol.Optional(
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
            default=LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
        )
    ] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS, default=0)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    schema[vol.Optional(CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS, default=0)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    schema[
        vol.Optional(
            CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
            default=LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
        )
    ] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY, default="")] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY, default="")] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY, default="")] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN, default=0)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY, default="")] = (
        cv.string
    )
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA, default=0)] = (
        vol.All(vol.Coerce(int), vol.Range(min=0))
    )
    schema[
        vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT, default=0)
    ] = vol.All(vol.Coerce(int), vol.Range(min=0))
    schema[
        vol.Optional(CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS, default=0)
    ] = vol.All(vol.Coerce(int), vol.Range(min=0))
    schema[
        vol.Optional(CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE, default=False)
    ] = cv.boolean
    schema[vol.Optional(CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS, default=120)] = (
        vol.All(vol.Coerce(int), vol.Range(min=0))
    )
    schema[vol.Optional(CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA, default=20)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    schema[vol.Optional(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS, default={})] = (
        dict
    )
    schema[
        vol.Optional(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES, default=[])
    ] = cv.ensure_list
    schema[
        vol.Optional(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL, default=False)
    ] = cv.boolean
    return vol.Schema(schema, extra=vol.REMOVE_EXTRA)


LIGHT_GROUP_FEATURE_SCHEMA = build_light_group_feature_schema()

__all__ = [
    "CONF_ACCENT_LIGHTS",
    "CONF_ACCENT_LIGHTS_ACT_ON",
    "CONF_ACCENT_LIGHTS_STATES",
    "CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL",
    "CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES",
    "CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE",
    "CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS",
    "CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE",
    "CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA",
    "CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS",
    "CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS",
    "CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS",
    "CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS",
    "CONF_LIGHT_GROUP_BRIGHTNESS_MODE",
    "CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY",
    "CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY",
    "CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE",
    "CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY",
    "CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA",
    "CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY",
    "CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT",
    "CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN",
    "CONF_OVERHEAD_LIGHTS",
    "CONF_OVERHEAD_LIGHTS_ACT_ON",
    "CONF_OVERHEAD_LIGHTS_STATES",
    "CONF_SLEEP_LIGHTS",
    "CONF_SLEEP_LIGHTS_ACT_ON",
    "CONF_SLEEP_LIGHTS_STATES",
    "CONF_TASK_LIGHTS",
    "CONF_TASK_LIGHTS_ACT_ON",
    "CONF_TASK_LIGHTS_STATES",
    "LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE",
    "LIGHT_GROUP_ACT_ON_STATE_CHANGE",
    "LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING",
    "LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE",
    "LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE",
    "LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX",
    "LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE",
    "LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY",
    "LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT",
    "LIGHT_GROUP_FEATURE_SCHEMA",
    "LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE",
    "LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX",
    "LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN",
    "LIGHT_GROUP_PRESETS",
    "LightGroupPreset",
    "adaptive_lighting_diagnostics",
    "adaptive_lighting_manage_all_lights",
    "adaptive_lighting_manages_role",
    "adaptive_lighting_managed_roles",
    "adaptive_lighting_mode",
    "adaptive_lighting_pair_key",
    "adaptive_lighting_switch_set",
    "adaptive_require_ambient_rise",
    "ambient_rise_min_delta",
    "ambient_rise_window_seconds",
    "bright_attribution_hold_seconds",
    "bright_dwell_seconds",
    "bright_min_on_seconds",
    "brightness_mode",
    "build_light_group_feature_schema",
    "inside_bright_entity",
    "light_groups_feature_config",
    "outside_bright_entity",
    "outside_context_source",
    "outside_lux_entity",
    "outside_lux_inside_delta",
    "outside_lux_inside_entity",
    "outside_lux_inside_ratio_min_percent",
    "outside_lux_min",
    "preset_members",
    "preset_states",
]
