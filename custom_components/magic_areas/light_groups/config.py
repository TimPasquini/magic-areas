"""Light group configuration constants and tables."""

from dataclasses import dataclass
from collections.abc import Mapping

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from custom_components.magic_areas.core.config import feature_config_slice
from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
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


def _int_option(feature_config: FeatureConfigDict, key: str, default: int = 0) -> int:
    """Read integer option from feature config with safe fallback."""
    value = feature_config.get(key, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def bright_min_on_seconds(feature_config: FeatureConfigDict) -> int:
    """Return adaptive min-on-time threshold in seconds."""
    return _int_option(feature_config, CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS, default=0)


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
    return _int_option(feature_config, CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA, default=0)


def outside_lux_inside_ratio_min_percent(feature_config: FeatureConfigDict) -> int:
    """Return required outside/inside lux ratio percentage (100 = 1.0x)."""
    return _int_option(
        feature_config, CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT, default=0
    )


def bright_attribution_hold_seconds(feature_config: FeatureConfigDict) -> int:
    """Return suppressive hold window after controlled light activity."""
    return _int_option(feature_config, CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS, default=0)


def adaptive_require_ambient_rise(feature_config: FeatureConfigDict) -> bool:
    """Return whether adaptive bright-off requires inside ambient rise evidence."""
    value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE, False)
    return bool(value)


def ambient_rise_window_seconds(feature_config: FeatureConfigDict) -> int:
    """Return lookback window used by ambient-rise detector."""
    return _int_option(feature_config, CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS, default=120)


def ambient_rise_min_delta(feature_config: FeatureConfigDict) -> int:
    """Return minimum inside lux rise required within the ambient window."""
    return _int_option(feature_config, CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA, default=20)


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
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY, default="")] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN, default=0)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY, default="")] = cv.string
    schema[vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA, default=0)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    schema[
        vol.Optional(CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT, default=0)
    ] = vol.All(vol.Coerce(int), vol.Range(min=0))
    schema[
        vol.Optional(CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS, default=0)
    ] = vol.All(vol.Coerce(int), vol.Range(min=0))
    schema[vol.Optional(CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE, default=False)] = (
        cv.boolean
    )
    schema[
        vol.Optional(CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS, default=120)
    ] = vol.All(vol.Coerce(int), vol.Range(min=0))
    schema[vol.Optional(CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA, default=20)] = vol.All(
        vol.Coerce(int), vol.Range(min=0)
    )
    return vol.Schema(schema, extra=vol.REMOVE_EXTRA)


LIGHT_GROUP_FEATURE_SCHEMA = build_light_group_feature_schema()
