"""Feature selection and configuration step handlers for options flow."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FAN_CONTROLLER_ACTIVE_STATES,
    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
    CONF_FAN_CONTROLLER_DETECTION_MODE,
    CONF_FAN_CONTROLLER_HYSTERESIS,
    CONF_FAN_CONTROLLER_MEMBERS,
    CONF_FAN_CONTROLLER_ON_THRESHOLD,
    CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS,
    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
    CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
    CONF_FAN_CONTROLLER_SUPPRESS_STATES,
    CONF_FAN_GROUPS_CONTROLLERS,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
)
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    AdaptiveLightingSwitchSet,
    switch_set_from_explicit_refs,
    switch_sets_from_hass_registry,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanClearBehavior,
    FanControllerRole,
    FanDetectionMode,
    FanSensorUnavailableBehavior,
)
from custom_components.magic_areas.config_flows.base import (
    ConfigSubMap,
    SelectorMap,
    enabled_feature_map,
    ensure_enabled_feature_map,
    get_feature_config_steps,
    invalid_input_error,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures, SelectorTranslationKeys
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_threshold_light_sensor_unique_id,
)
from custom_components.magic_areas.features.config.readers import (
    AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS,
    BLE_TRACKER_OPTION_KEYS,
    CLIMATE_CONTROL_ENTITY_KEY,
    CLIMATE_CONTROL_PRESET_OPTION_KEYS,
    FAN_GROUPS_OPTION_KEYS,
    AGGREGATES_OPTION_KEYS,
    HEALTH_OPTION_KEYS,
    PRESENCE_HOLD_OPTION_KEYS,
    WASP_IN_A_BOX_OPTION_KEYS,
)
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
from custom_components.magic_areas.light_groups import (
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_PRESETS,
    adaptive_lighting_pair_key,
)
from custom_components.magic_areas.policy import (
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    ALL_SENSOR_DEVICE_CLASSES,
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
    build_climate_preset_selectors_and_validators,
    build_selector_entity_simple,
    build_selector_boolean,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.schemas import CONFIGURABLE_FEATURES
from custom_components.magic_areas.schemas import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)
from custom_components.magic_areas.enums import LightGroupCategory

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.config_flows.options_flow import (
        OptionsFlowHandler,
    )

_LOGGER = logging.getLogger(__name__)
_EXPECTED_FEATURE_FLOW_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)

_LIGHT_GROUP_ALWAYS_KEYS = {
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
}
_LIGHT_GROUP_ADVISORY_KEYS = {
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
}
_LIGHT_GROUP_ADAPTIVE_ONLY_KEYS = {
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
}
_LIGHT_GROUP_PRESERVED_HIDDEN_KEYS = {
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
}
_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX = (
    LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX
)
_LIGHT_GROUP_LUX_SELECTOR_MAX = 120_000
_LIGHT_GROUP_MENU_STEP = "feature_conf_light_groups"
_LIGHT_GROUP_ROLES_STEP = "feature_conf_light_groups_roles"
_LIGHT_GROUP_BRIGHTNESS_STEP = "feature_conf_light_groups_brightness"
_LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP = (
    "feature_conf_light_groups_brightness_advisory"
)
_LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP = (
    "feature_conf_light_groups_brightness_adaptive"
)
_LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP = "feature_conf_light_groups_adaptive_lighting"
_LIGHT_GROUP_SUBSTEPS = {
    _LIGHT_GROUP_MENU_STEP,
    _LIGHT_GROUP_ROLES_STEP,
    _LIGHT_GROUP_BRIGHTNESS_STEP,
    _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
    _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
}
_FAN_GROUP_MENU_STEP = "feature_conf_fan_groups"
_FAN_GROUP_COOLING_STEP = "feature_conf_fan_groups_cooling"
_FAN_GROUP_HUMIDITY_STEP = "feature_conf_fan_groups_humidity"
_FAN_GROUP_ODOR_STEP = "feature_conf_fan_groups_odor"
_FAN_GROUP_SETTINGS_STEP = "feature_conf_fan_groups_settings"
_FAN_GROUP_STEP_ROLE = {
    _FAN_GROUP_COOLING_STEP: FanControllerRole.COOLING.value,
    _FAN_GROUP_HUMIDITY_STEP: FanControllerRole.HUMIDITY.value,
    _FAN_GROUP_ODOR_STEP: FanControllerRole.ODOR.value,
    _FAN_GROUP_SETTINGS_STEP: FanControllerRole.COOLING.value,
}
_FAN_GROUP_SUBSTEPS = set(_FAN_GROUP_STEP_ROLE)
_FEATURE_SETTINGS_STEP_SUFFIX = "_settings"
_FEATURE_MENU_EXCLUSIONS = {
    MagicAreasFeatures.AGGREGATES.value,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER.value,
    MagicAreasFeatures.BLE_TRACKER.value,
    MagicAreasFeatures.FAN_GROUPS.value,
    MagicAreasFeatures.HEALTH.value,
    MagicAreasFeatures.LIGHT_GROUPS.value,
    MagicAreasFeatures.PRESENCE_HOLD.value,
    MagicAreasFeatures.WASP_IN_A_BOX.value,
}
_LIGHT_GROUP_ROLE_KEYS = {
    key
    for preset in LIGHT_GROUP_PRESETS
    for key in (preset.category, preset.states_key, preset.act_on_key)
}
_FEATURE_SELECTION_ORDER = (
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.FAN_GROUPS,
    MagicAreasFeatures.COVER_GROUPS,
    MagicAreasFeatures.CLIMATE_CONTROL,
    MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
    MagicAreasFeatures.AGGREGATES,
    MagicAreasFeatures.HEALTH,
    MagicAreasFeatures.PRESENCE_HOLD,
    MagicAreasFeatures.BLE_TRACKER,
    MagicAreasFeatures.WASP_IN_A_BOX,
)


def _feature_section_step(feature: MagicAreasFeatures) -> str:
    """Return the parent section-menu step for a feature."""
    return f"feature_conf_{feature.value}"


def _copy_schema(schema: vol.Schema) -> vol.Schema:
    """Return a shallow copy so dynamic flow fields do not mutate registry schemas."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return schema
    return vol.Schema(dict(raw_schema), extra=schema.extra)


def _resolve_light_groups_mode(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None
) -> str:
    """Resolve current light-groups mode from input or saved options."""
    if user_input is not None:
        raw = user_input.get(CONF_LIGHT_GROUP_BRIGHTNESS_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
        }:
            return raw

    saved = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.LIGHT_GROUPS.value, {}
    )
    if isinstance(saved, dict):
        raw = saved.get(CONF_LIGHT_GROUP_BRIGHTNESS_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
        }:
            return raw
    return LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT


def _filter_schema_for_keys(schema: vol.Schema, include_keys: set[str]) -> vol.Schema:
    """Return a copy of schema containing only desired option keys."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return schema

    filtered: dict[object, object] = {}
    for marker, validator in raw_schema.items():
        key = getattr(marker, "schema", marker)
        if isinstance(key, str) and key in include_keys:
            filtered[marker] = validator
    return vol.Schema(filtered, extra=vol.REMOVE_EXTRA)


def _remove_schema_key(schema: vol.Schema, key_to_remove: str) -> None:
    """Remove existing markers for one config key before adding dynamic variants."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return
    for marker in tuple(raw_schema):
        if getattr(marker, "schema", marker) == key_to_remove:
            raw_schema.pop(marker, None)


def _light_group_step_include_keys(
    *,
    step_id: str,
    mode: str,
    adaptive_lighting_mode: str,
) -> set[str]:
    """Return light-group config keys rendered on one light-group substep."""
    if step_id == _LIGHT_GROUP_ROLES_STEP:
        return set(_LIGHT_GROUP_ROLE_KEYS)

    if step_id == _LIGHT_GROUP_BRIGHTNESS_STEP:
        return {CONF_LIGHT_GROUP_BRIGHTNESS_MODE}

    if step_id == _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP:
        return set(_LIGHT_GROUP_ADVISORY_KEYS)

    if step_id == _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP:
        return set(_LIGHT_GROUP_ADVISORY_KEYS | _LIGHT_GROUP_ADAPTIVE_ONLY_KEYS)

    if step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
        include_keys = {CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE}
        if adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE:
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
        return include_keys

    return set()


def _resolve_adaptive_lighting_mode(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None
) -> str:
    """Resolve current Adaptive Lighting mode from input or saved options."""
    if user_input is not None:
        raw = user_input.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
        }:
            return raw

    saved = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.LIGHT_GROUPS.value, {}
    )
    if isinstance(saved, dict):
        raw = saved.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
        }:
            return raw
    return LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE


def _light_group_pairing_categories(
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> tuple[str, ...]:
    """Return light roles that currently have a native group/pairing surface."""
    categories: list[str] = []
    if flow.all_lights:
        categories.append(str(LightGroupCategory.ALL))

    for preset in LIGHT_GROUP_PRESETS:
        raw_members = feature_config.get(preset.category, [])
        if isinstance(raw_members, list) and raw_members:
            categories.append(preset.category)

    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if isinstance(raw_switch_sets, Mapping):
        for category in raw_switch_sets:
            if isinstance(category, str) and category not in categories:
                categories.append(category)

    return tuple(categories)


def _configured_adaptive_lighting_switch_sets(
    area_id: str,
    feature_config: Mapping[str, object],
) -> dict[str, AdaptiveLightingSwitchSet]:
    """Return existing explicit switch-set config by light role."""
    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if not isinstance(raw_switch_sets, Mapping):
        return {}

    switch_sets: dict[str, AdaptiveLightingSwitchSet] = {}
    for category, raw_switch_refs in raw_switch_sets.items():
        if not isinstance(category, str) or not isinstance(raw_switch_refs, Mapping):
            continue
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
        if switch_set is not None:
            switch_sets[category] = switch_set
    return switch_sets


def _light_group_managed_role_options(
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> list[str]:
    """Return role options that can receive MA-managed Adaptive Lighting configs."""
    options = [
        category
        for category in _light_group_pairing_categories(flow, feature_config)
        if category != str(LightGroupCategory.ALL)
    ]
    raw_roles = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
    if isinstance(raw_roles, list):
        for role in raw_roles:
            if (
                isinstance(role, str)
                and role != str(LightGroupCategory.ALL)
                and role not in options
            ):
                options.append(role)
    return options


def _light_group_manage_all_lights_default(
    feature_config: Mapping[str, object],
) -> bool:
    """Return saved room-level manage preference."""
    raw_value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
    try:
        return bool(cv.boolean(raw_value))
    except vol.Invalid:
        return False


def _light_group_managed_roles_default(
    *,
    role_options: list[str],
    feature_config: Mapping[str, object],
) -> list[str]:
    """Return saved managed roles or all configured role options for first manage use."""
    raw_roles = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
    if isinstance(raw_roles, list):
        saved_roles = [role for role in raw_roles if isinstance(role, str)]
        if saved_roles:
            return saved_roles
    return list(role_options)


def _prune_light_group_options_for_brightness_mode(
    *,
    existing: dict[str, object],
    mode: str,
) -> None:
    """Preserve dormant brightness settings when switching modes."""
    return


def _default_inside_bright_entity(
    *,
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> str:
    """Return default inside-bright entity for advisory/adaptive config."""
    current = feature_config.get(CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY)
    if isinstance(current, str) and current:
        return current

    area_config = flow._area_config
    if area_config is None:
        return ""

    entity_registry = er.async_get(flow.hass)
    threshold_entity = entity_registry.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        build_threshold_light_sensor_unique_id(area_id=area_config.id),
    )
    if isinstance(threshold_entity, str) and threshold_entity in flow.all_binary_entities:
        return threshold_entity

    return ""


def _should_rerender_light_group_brightness_step(
    *,
    step_id: str,
    user_input: Mapping[str, object],
    validated: Mapping[str, object],
) -> bool:
    """Return whether brightness mode selection should reveal follow-up controls immediately."""
    if step_id != _LIGHT_GROUP_BRIGHTNESS_STEP:
        return False
    if CONF_LIGHT_GROUP_BRIGHTNESS_MODE not in validated:
        return False
    return (
        len(user_input) == 1
        and CONF_LIGHT_GROUP_BRIGHTNESS_MODE in user_input
    )


def _should_rerender_light_group_adaptive_lighting_step(
    *,
    step_id: str,
    user_input: Mapping[str, object],
    validated: Mapping[str, object],
) -> bool:
    """Return whether mode selection should reveal follow-up controls immediately."""
    if step_id != _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
        return False
    mode = validated.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
    if mode not in {
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    }:
        return False
    if mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING:
        return not any(
            key.startswith(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX)
            for key in user_input
        )
    return (
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL not in user_input
        and CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES not in user_input
    )


def _adaptive_lighting_candidate_switch_sets(
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> dict[str, AdaptiveLightingSwitchSet]:
    """Return selectable AL switch sets keyed by main switch entity ID."""
    area_config = flow._area_config
    if area_config is None:
        return {}

    candidates = {
        switch_set.main_switch_entity_id: switch_set
        for switch_set in switch_sets_from_hass_registry(
            flow.hass,
            area_id=area_config.id,
        )
    }
    for switch_set in _configured_adaptive_lighting_switch_sets(
        area_config.id,
        feature_config,
    ).values():
        candidates.setdefault(switch_set.main_switch_entity_id, switch_set)
    return dict(sorted(candidates.items()))


def _adaptive_lighting_pair_value(
    feature_config: Mapping[str, object],
    category: str,
) -> str:
    """Return currently selected AL main switch for one light role."""
    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if not isinstance(raw_switch_sets, Mapping):
        return ""
    raw_switch_refs = raw_switch_sets.get(category)
    if not isinstance(raw_switch_refs, Mapping):
        return ""
    main_switch = raw_switch_refs.get(MAIN_SWITCH)
    return main_switch if isinstance(main_switch, str) else ""


def _adaptive_lighting_switch_set_refs(
    switch_set: AdaptiveLightingSwitchSet,
) -> dict[str, str]:
    """Return persisted explicit switch refs for one AL switch set."""
    return {
        MAIN_SWITCH: switch_set.main_switch_entity_id,
        SLEEP_SWITCH: switch_set.sleep_switch_entity_id,
        ADAPT_BRIGHTNESS_SWITCH: switch_set.adapt_brightness_switch_entity_id,
        ADAPT_COLOR_SWITCH: switch_set.adapt_color_switch_entity_id,
    }


def _normalize_light_group_adaptive_lighting_options(
    flow: "OptionsFlowHandler",
    feature_config: dict[str, object],
) -> None:
    """Translate transient AL pairing dropdowns into explicit switch-set config."""
    area_config = flow._area_config
    if area_config is None:
        return

    if (
        feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
        != LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
    ):
        for key in tuple(feature_config):
            if key.startswith(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX):
                feature_config.pop(key, None)
        return

    candidates = _adaptive_lighting_candidate_switch_sets(flow, feature_config)
    categories = set(_light_group_pairing_categories(flow, feature_config))
    for key in feature_config:
        if key.startswith(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX):
            categories.add(key.removeprefix(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX))

    switch_sets: dict[str, dict[str, str]] = {}
    for category in sorted(categories):
        pair_key = adaptive_lighting_pair_key(category)
        selected = feature_config.pop(pair_key, "")
        if not isinstance(selected, str) or not selected:
            continue
        switch_set = candidates.get(selected)
        if switch_set is None:
            continue
        switch_sets[category] = _adaptive_lighting_switch_set_refs(switch_set)

    feature_config[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS] = switch_sets


def _fan_entities(flow: "OptionsFlowHandler") -> list[str]:
    """Return selectable fan entities."""
    return sorted(
        entity_id for entity_id in flow.all_entities if entity_id.startswith("fan.")
    )


def _fan_controller_defaults(role: str) -> dict[str, object]:
    """Return role-specific defaults for one fan controller page."""
    if role == FanControllerRole.HUMIDITY:
        return {
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
            ],
            CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.RUN_UNTIL_CLEAR.value,
            CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
                FanSensorUnavailableBehavior.HOLD_THEN_CLEAR.value
            ),
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 60.0,
            CONF_FAN_CONTROLLER_HYSTERESIS: 5.0,
        }
    if role == FanControllerRole.ODOR:
        return {
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
            ],
            CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.RUN_UNTIL_CLEAR.value,
            CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
                FanSensorUnavailableBehavior.CLEAR_REASON.value
            ),
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 0.0,
            CONF_FAN_CONTROLLER_HYSTERESIS: 0.0,
        }
    return {
        CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.EXTENDED.value],
        CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.OCCUPANCY_ONLY.value,
        CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
            FanSensorUnavailableBehavior.CLEAR_REASON.value
        ),
        CONF_FAN_CONTROLLER_ON_THRESHOLD: 0.0,
        CONF_FAN_CONTROLLER_HYSTERESIS: 0.0,
    }


def _fan_controller_config(
    feature_config: Mapping[str, object],
    role: str,
) -> dict[str, object]:
    """Return saved/default controller config for one role."""
    defaults = {
        CONF_FAN_CONTROLLER_MEMBERS: [],
        CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "",
        CONF_FAN_CONTROLLER_DETECTION_MODE: FanDetectionMode.THRESHOLD.value,
        CONF_FAN_CONTROLLER_SUPPRESS_STATES: [],
        CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS: 0,
        **_fan_controller_defaults(role),
    }
    raw_controllers = feature_config.get(CONF_FAN_GROUPS_CONTROLLERS)
    if isinstance(raw_controllers, Mapping):
        raw_role_config = raw_controllers.get(role)
        if isinstance(raw_role_config, Mapping):
            return {**defaults, **dict(raw_role_config)}

    if role == FanControllerRole.COOLING:
        required_state = feature_config.get(CONF_FAN_GROUPS_REQUIRED_STATE)
        if isinstance(required_state, str) and required_state:
            defaults[CONF_FAN_CONTROLLER_ACTIVE_STATES] = [required_state]
        setpoint = feature_config.get(CONF_FAN_GROUPS_SETPOINT)
        if isinstance(setpoint, int | float):
            defaults[CONF_FAN_CONTROLLER_ON_THRESHOLD] = float(setpoint)

    return defaults


def _fan_controller_schema(saved: Mapping[str, object]) -> vol.Schema:
    """Return schema for one fan controller role page."""
    area_state_options = [
        AreaStates.OCCUPIED.value,
        AreaStates.EXTENDED.value,
        AreaStates.DARK.value,
        AreaStates.BRIGHT.value,
        AreaStates.SLEEP.value,
        AreaStates.ACCENT.value,
    ]
    return vol.Schema(
        {
            vol.Optional(
                CONF_FAN_CONTROLLER_MEMBERS,
                default=saved.get(CONF_FAN_CONTROLLER_MEMBERS, []),
            ): cv.ensure_list,
            vol.Optional(
                CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
                default=saved.get(CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID, ""),
            ): cv.string,
            vol.Optional(
                CONF_FAN_CONTROLLER_DETECTION_MODE,
                default=saved.get(
                    CONF_FAN_CONTROLLER_DETECTION_MODE,
                    FanDetectionMode.THRESHOLD.value,
                ),
            ): vol.In([FanDetectionMode.THRESHOLD.value]),
            vol.Optional(
                CONF_FAN_CONTROLLER_ON_THRESHOLD,
                default=saved.get(CONF_FAN_CONTROLLER_ON_THRESHOLD, 0.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_FAN_CONTROLLER_HYSTERESIS,
                default=saved.get(CONF_FAN_CONTROLLER_HYSTERESIS, 0.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_FAN_CONTROLLER_ACTIVE_STATES,
                default=saved.get(CONF_FAN_CONTROLLER_ACTIVE_STATES, []),
            ): vol.All(cv.ensure_list, [vol.In(area_state_options)]),
            vol.Optional(
                CONF_FAN_CONTROLLER_SUPPRESS_STATES,
                default=saved.get(CONF_FAN_CONTROLLER_SUPPRESS_STATES, []),
            ): vol.All(cv.ensure_list, [vol.In(area_state_options)]),
            vol.Optional(
                CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
                default=saved.get(
                    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
                    FanClearBehavior.OCCUPANCY_ONLY.value,
                ),
            ): vol.In([behavior.value for behavior in FanClearBehavior]),
            vol.Optional(
                CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS,
                default=saved.get(CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS, 0),
            ): vol.Coerce(int),
            vol.Optional(
                CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
                default=saved.get(
                    CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
                    FanSensorUnavailableBehavior.CLEAR_REASON.value,
                ),
            ): vol.In([behavior.value for behavior in FanSensorUnavailableBehavior]),
        },
        extra=vol.REMOVE_EXTRA,
    )


def _fan_controller_selectors(flow: "OptionsFlowHandler") -> SelectorMap:
    """Return selectors for one fan controller role page."""
    area_state_options = [
        AreaStates.OCCUPIED.value,
        AreaStates.EXTENDED.value,
        AreaStates.DARK.value,
        AreaStates.BRIGHT.value,
        AreaStates.SLEEP.value,
        AreaStates.ACCENT.value,
    ]
    return {
        CONF_FAN_CONTROLLER_MEMBERS: build_selector_entity_simple(
            _fan_entities(flow), multiple=True
        ),
        CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: build_selector_entity_simple(
            flow.all_entities, multiple=False
        ),
        CONF_FAN_CONTROLLER_DETECTION_MODE: build_selector_select(
            options=[FanDetectionMode.THRESHOLD.value],
            multiple=False,
        ),
        CONF_FAN_CONTROLLER_ON_THRESHOLD: build_selector_number(
            min_value=0,
            max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
            step=0.1,
            unit_of_measurement="",
        ),
        CONF_FAN_CONTROLLER_HYSTERESIS: build_selector_number(
            min_value=0,
            max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
            step=0.1,
            unit_of_measurement="",
        ),
        CONF_FAN_CONTROLLER_ACTIVE_STATES: build_selector_select(
            options=area_state_options,
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        ),
        CONF_FAN_CONTROLLER_SUPPRESS_STATES: build_selector_select(
            options=area_state_options,
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        ),
        CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: build_selector_select(
            options=[behavior.value for behavior in FanClearBehavior],
            multiple=False,
            translation_key="fan_clear_behavior",
        ),
        CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS: build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        ),
        CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: build_selector_select(
            options=[behavior.value for behavior in FanSensorUnavailableBehavior],
            multiple=False,
            translation_key="fan_sensor_unavailable_behavior",
        ),
    }


def _sync_legacy_fan_options_from_cooling(
    feature_config: dict[str, object],
    controller_config: Mapping[str, object],
) -> None:
    """Keep current runtime-compatible fan keys aligned with Cooling config."""
    active_states = controller_config.get(CONF_FAN_CONTROLLER_ACTIVE_STATES)
    if isinstance(active_states, list) and active_states:
        feature_config[CONF_FAN_GROUPS_REQUIRED_STATE] = str(active_states[0])
    feature_config[CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS] = feature_config.get(
        CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
        "temperature",
    )
    on_threshold = controller_config.get(CONF_FAN_CONTROLLER_ON_THRESHOLD)
    if isinstance(on_threshold, int | float):
        feature_config[CONF_FAN_GROUPS_SETPOINT] = float(on_threshold)


def _normalize_fan_controller_validated(
    validated: Mapping[str, object],
) -> dict[str, object]:
    """Normalize controller form values into JSON-friendly primitive values."""
    normalized = dict(validated)
    for key in (
        CONF_FAN_CONTROLLER_MEMBERS,
        CONF_FAN_CONTROLLER_ACTIVE_STATES,
        CONF_FAN_CONTROLLER_SUPPRESS_STATES,
    ):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
    for key in (
        CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
        CONF_FAN_CONTROLLER_DETECTION_MODE,
        CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
        CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
    ):
        value = normalized.get(key)
        if value is not None:
            normalized[key] = str(value)
    return normalized


async def _handle_fan_controller_form(
    flow: "OptionsFlowHandler",
    *,
    step_id: str,
    user_input: Mapping[str, object] | None,
) -> config_entries.ConfigFlowResult:
    """Handle one fan controller role config page."""
    role = _FAN_GROUP_STEP_ROLE[step_id]
    feature_config = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.FAN_GROUPS.value, {}
    )
    if not isinstance(feature_config, Mapping):
        feature_config = {}
    saved = _fan_controller_config(feature_config, role)
    schema = _fan_controller_schema(saved)

    if user_input is not None:
        try:
            validated = dict(schema(dict(user_input)))
        except vol.MultipleInvalid:
            return flow.async_show_form(
                step_id=step_id,
                data_schema=flow._build_schema_from_vol(
                    schema,
                    saved_options=saved,
                    selectors=_fan_controller_selectors(flow),
                ),
                errors=invalid_input_error(),
            )
        validated = _normalize_fan_controller_validated(validated)

        features = ensure_enabled_feature_map(flow.area_options)
        mutable_config = features.setdefault(MagicAreasFeatures.FAN_GROUPS.value, {})
        if not isinstance(mutable_config, dict):
            mutable_config = {}
            features[MagicAreasFeatures.FAN_GROUPS.value] = mutable_config
        controllers = mutable_config.setdefault(CONF_FAN_GROUPS_CONTROLLERS, {})
        if not isinstance(controllers, dict):
            controllers = {}
            mutable_config[CONF_FAN_GROUPS_CONTROLLERS] = controllers
        controllers[role] = validated
        if role == FanControllerRole.COOLING:
            _sync_legacy_fan_options_from_cooling(mutable_config, validated)

        await flow._persist_options()
        flow._feature_step_id = _FAN_GROUP_MENU_STEP
        return await handle_feature_conf(flow)

    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=saved,
            selectors=_fan_controller_selectors(flow),
        ),
    )


async def _handle_fan_feature_route(
    flow: "OptionsFlowHandler",
    *,
    step_id: str,
    user_input: Mapping[str, object] | None,
) -> config_entries.ConfigFlowResult | None:
    """Handle fan feature menu and controller-role pages."""
    if step_id == _FAN_GROUP_MENU_STEP:
        # noinspection PyTypeChecker
        return flow.async_show_menu(
            step_id=_FAN_GROUP_MENU_STEP,
            menu_options=[
                _FAN_GROUP_COOLING_STEP,
                _FAN_GROUP_HUMIDITY_STEP,
                _FAN_GROUP_ODOR_STEP,
                "show_menu",
            ],
        )
    if step_id in _FAN_GROUP_SUBSTEPS:
        return await _handle_fan_controller_form(
            flow,
            step_id=step_id,
            user_input=user_input,
        )
    return None


def _handle_light_group_menu_route(
    flow: "OptionsFlowHandler",
    *,
    step_id: str,
) -> config_entries.ConfigFlowResult | None:
    """Handle the light-group section menu."""
    if step_id != _LIGHT_GROUP_MENU_STEP:
        return None
    # noinspection PyTypeChecker
    return flow.async_show_menu(
        step_id=_LIGHT_GROUP_MENU_STEP,
        menu_options=[
            _LIGHT_GROUP_ROLES_STEP,
            _LIGHT_GROUP_BRIGHTNESS_STEP,
            _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
            "show_menu",
        ],
    )


def _add_light_group_brightness_selectors(
    *,
    flow: "OptionsFlowHandler",
    step_id: str,
    mode: str,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for the light-group brightness substep."""
    if step_id not in {
        _LIGHT_GROUP_BRIGHTNESS_STEP,
        _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
        _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    }:
        return

    if step_id == _LIGHT_GROUP_BRIGHTNESS_STEP:
        selectors[CONF_LIGHT_GROUP_BRIGHTNESS_MODE] = build_selector_select(
            options=[
                LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
                LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
            ],
            multiple=False,
            translation_key="light_brightness_mode",
        )
        return

    selectors[CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY] = build_selector_entity_simple(
        multiple=False
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY] = build_selector_entity_simple(
        multiple=False
    )

    if step_id != _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP:
        return

    selectors[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
    )
    selectors[CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
    )
    selectors[CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS] = (
        build_selector_number(
            min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
        )
    )
    selectors[CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE] = (
        build_selector_boolean()
    )
    selectors[CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
    )
    selectors[CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX,
        max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
        unit_of_measurement="lx",
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE] = build_selector_select(
        options=[
            LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
            LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX,
            LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE,
        ],
        multiple=False,
        translation_key="light_outside_context_source",
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY] = build_selector_entity_simple(
        flow.all_illuminance_entities, multiple=False
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX,
        max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
        unit_of_measurement="lx",
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY] = (
        build_selector_entity_simple(flow.all_illuminance_entities, multiple=False)
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX,
        max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
        unit_of_measurement="lx",
    )
    selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT] = (
        build_selector_number(
            min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="%"
        )
    )


def _add_light_group_adaptive_lighting_selectors(
    *,
    step_id: str,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for the Adaptive Lighting coordination substep."""
    if step_id != _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
        return
    selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE] = build_selector_select(
        options=[
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
        ],
        multiple=False,
        translation_key="adaptive_lighting_mode",
    )


def _add_light_group_role_selectors(
    *,
    step_id: str,
    flow: "OptionsFlowHandler",
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for the light-role membership substep."""
    if step_id != _LIGHT_GROUP_ROLES_STEP:
        return
    for preset in LIGHT_GROUP_PRESETS:
        selectors[preset.category] = build_selector_entity_simple(
            flow.all_lights, multiple=True
        )
        selectors[preset.states_key] = build_selector_select(
            options=[
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
                AreaStates.SLEEP.value,
                AreaStates.ACCENT.value,
            ],
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        )
        selectors[preset.act_on_key] = build_selector_select(
            options=[
                LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                LIGHT_GROUP_ACT_ON_STATE_CHANGE,
            ],
            multiple=True,
            translation_key=SelectorTranslationKeys.CONTROL_ON,
        )


def get_feature_list(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
    """Return list of available features for area type."""
    available = FEATURE_REGISTRY.available_features_for_area(area_config)
    ordered = [feature for feature in _FEATURE_SELECTION_ORDER if feature in available]
    ordered.extend(feature for feature in available if feature not in ordered)
    return ordered


def get_configurable_features(
    area_config: "AreaConfig | None",
) -> list[MagicAreasFeatures]:
    """Return configurable features for area type."""
    return FEATURE_REGISTRY.configurable_features_for_area(area_config)


async def handle_feature_selection(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle feature selection step."""
    feature_list = get_feature_list(flow._area_config)

    if user_input is not None:
        selected_features = [
            MagicAreasFeatures(feature)
            for feature, is_selected in user_input.items()
            if isinstance(feature, str) and bool(is_selected)
        ]

        enabled_features = ensure_enabled_feature_map(flow.area_options)

        for c_feature in feature_list:
            if c_feature in selected_features:
                if c_feature.value not in enabled_features:
                    enabled_features[c_feature.value] = {}
            else:
                enabled_features.pop(c_feature.value, None)

        return await flow._persist_options_and_show_menu()

    return flow.async_show_form(
        step_id="select_features",
        data_schema=flow._build_options_schema(
            options=[(str(feature), False, bool) for feature in feature_list],
            saved_options={
                str(feature): (
                    feature in enabled_feature_map(flow.area_options)
                    or feature.value in enabled_feature_map(flow.area_options)
                )
                for feature in feature_list
            },
        ),
    )


async def handle_feature_form(
    *,
    flow: "OptionsFlowHandler",
    feature_enum: MagicAreasFeatures,
    step_id: str,
    schema: vol.Schema,
    user_input: Mapping[str, object] | None = None,
    merge_options: bool = False,
    next_step: str | None = None,
    selectors: Mapping[str, object] | None = None,
    dynamic_validators: Mapping[str, object] | None = None,
) -> config_entries.ConfigFlowResult:
    """Validate and render a feature configuration form."""
    errors: dict[str, str] = {}

    if user_input is not None:
        try:
            validated = schema(dict(user_input))
        except vol.MultipleInvalid:
            errors = invalid_input_error()
        except _EXPECTED_FEATURE_FLOW_ERRORS as exc:  # pragma: no cover
            _LOGGER.warning(
                "OptionsFlow: Unexpected error validating feature step %s: %s",
                step_id,
                str(exc),
            )
            errors = invalid_input_error()
        else:
            features = ensure_enabled_feature_map(flow.area_options)
            feature_key = feature_enum.value
            validated_dict = dict(validated)
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS:
                existing = features.get(feature_key, {})
                if isinstance(existing, Mapping):
                    for key in _LIGHT_GROUP_PRESERVED_HIDDEN_KEYS:
                        if key in existing and key not in user_input:
                            validated_dict[key] = existing[key]
                if (
                    isinstance(existing, dict)
                    and isinstance(
                        validated_dict.get(CONF_LIGHT_GROUP_BRIGHTNESS_MODE),
                        str,
                    )
                ):
                    _prune_light_group_options_for_brightness_mode(
                        existing=existing,
                        mode=validated_dict[CONF_LIGHT_GROUP_BRIGHTNESS_MODE],
                    )
                elif isinstance(existing, dict) and step_id in {
                    _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
                    _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
                }:
                    _prune_light_group_options_for_brightness_mode(
                        existing=existing,
                        mode=(
                            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
                            if step_id == _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP
                            else LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
                        ),
                    )
                _normalize_light_group_adaptive_lighting_options(
                    flow,
                    validated_dict,
                )
            if merge_options:
                features.setdefault(feature_key, {}).update(validated_dict)
            else:
                features[feature_key] = validated_dict

            if _should_rerender_light_group_adaptive_lighting_step(
                step_id=step_id,
                user_input=user_input,
                validated=validated_dict,
            ):
                return await handle_feature_conf(flow)
            if _should_rerender_light_group_brightness_step(
                step_id=step_id,
                user_input=user_input,
                validated=validated_dict,
            ):
                return await handle_feature_conf(flow)

            if next_step:
                if next_step != "feature_conf_climate_control_select_presets":
                    await flow._persist_options()
                step_handler: Callable[[], Awaitable[config_entries.ConfigFlowResult]]
                step_handler = getattr(flow, f"async_step_{next_step}")
                return await step_handler()
            # noinspection PyTypeChecker
            return await flow._persist_options_and_show_menu()

    # noinspection PyTypeChecker
    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=enabled_feature_map(flow.area_options).get(
                feature_enum.value, {}
            ),
            selectors=selectors or {},
            dynamic_validators=dynamic_validators or {},
        ),
        errors=errors,
    )


def _add_non_light_feature_selectors(
    *,
    flow: "OptionsFlowHandler",
    feature_enum: MagicAreasFeatures,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for non-light feature config forms."""
    if feature_enum == MagicAreasFeatures.AGGREGATES:
        selectors.update(
            {
                CONF_AGGREGATES_MIN_ENTITIES: build_selector_number(
                    min_value=1, unit_of_measurement=""
                ),
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: build_selector_number(
                    min_value=0,
                    max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
                    unit_of_measurement="lx",
                ),
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS: (
                    build_selector_number(min_value=0, unit_of_measurement="%")
                ),
                AGGREGATES_OPTION_KEYS[3]: build_selector_select(
                    sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
                ),
                AGGREGATES_OPTION_KEYS[4]: build_selector_select(
                    sorted(ALL_SENSOR_DEVICE_CLASSES), multiple=True
                ),
            }
        )

    if feature_enum == MagicAreasFeatures.FAN_GROUPS:
        selectors.update(
            {
                FAN_GROUPS_OPTION_KEYS[0]: build_selector_select(
                    options=[
                        AreaStates.OCCUPIED.value,
                        AreaStates.EXTENDED.value,
                        AreaStates.DARK.value,
                        AreaStates.BRIGHT.value,
                        AreaStates.SLEEP.value,
                        AreaStates.ACCENT.value,
                    ],
                    translation_key=SelectorTranslationKeys.AREA_STATES,
                ),
                FAN_GROUPS_OPTION_KEYS[1]: build_selector_select(
                    sorted(ALL_SENSOR_DEVICE_CLASSES),
                ),
                FAN_GROUPS_OPTION_KEYS[2]: build_selector_number(
                    min_value=0,
                    max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
                    step=0.1,
                    unit_of_measurement="",
                ),
            }
        )

    if feature_enum == MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER:
        selectors[AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[0]] = (
            build_selector_entity_simple(flow.all_media_players, multiple=True)
        )
        selectors[AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[1]] = build_selector_select(
            options=[
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
                AreaStates.SLEEP.value,
            ],
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        )

    if feature_enum == MagicAreasFeatures.BLE_TRACKER:
        sensor_entities = [
            entity_id
            for entity_id in flow.all_entities
            if entity_id.startswith("sensor.")
        ]
        selectors[BLE_TRACKER_OPTION_KEYS[0]] = build_selector_entity_simple(
            sensor_entities, multiple=True
        )

    if feature_enum == MagicAreasFeatures.CLIMATE_CONTROL:
        climate_entities = [
            entity_id
            for entity_id in flow.all_entities
            if entity_id.startswith("climate.")
        ]
        selectors[CLIMATE_CONTROL_ENTITY_KEY] = build_selector_entity_simple(
            climate_entities,
            multiple=False,
        )

    if feature_enum == MagicAreasFeatures.HEALTH:
        selectors[HEALTH_OPTION_KEYS[0]] = build_selector_select(
            options=sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES),
            multiple=True,
        )

    if feature_enum == MagicAreasFeatures.PRESENCE_HOLD:
        selectors[PRESENCE_HOLD_OPTION_KEYS[0]] = build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        )

    if feature_enum == MagicAreasFeatures.WASP_IN_A_BOX:
        selectors[WASP_IN_A_BOX_OPTION_KEYS[0]] = build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        )
        selectors[WASP_IN_A_BOX_OPTION_KEYS[1]] = build_selector_number(
            min_value=0,
            max_value=1_440,
            unit_of_measurement="minutes",
        )
        selectors[WASP_IN_A_BOX_OPTION_KEYS[2]] = build_selector_select(
            options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
            multiple=True,
        )


async def handle_feature_conf(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Configure a specific feature using registry-based approach."""
    step_id = flow._feature_step_id or str(flow.context.get("step_id", ""))
    light_menu_result = _handle_light_group_menu_route(flow, step_id=step_id)
    if light_menu_result is not None:
        return light_menu_result
    fan_result = await _handle_fan_feature_route(
        flow,
        step_id=step_id,
        user_input=user_input,
    )
    if fan_result is not None:
        return fan_result
    if step_id == _LIGHT_GROUP_BRIGHTNESS_STEP and user_input is not None:
        mode_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
                    default=LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                ): vol.In(
                    [
                        LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                        LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
                        LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
                    ]
                )
            },
            extra=vol.REMOVE_EXTRA,
        )
        errors: dict[str, str] = {}
        try:
            validated_mode = mode_schema(dict(user_input))
        except vol.MultipleInvalid:
            errors = invalid_input_error()
        else:
            features = ensure_enabled_feature_map(flow.area_options)
            feature_cfg = features.setdefault(MagicAreasFeatures.LIGHT_GROUPS.value, {})
            if not isinstance(feature_cfg, dict):
                feature_cfg = {}
                features[MagicAreasFeatures.LIGHT_GROUPS.value] = feature_cfg
            selected_mode = str(
                validated_mode.get(
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
                    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                )
            )
            feature_cfg[CONF_LIGHT_GROUP_BRIGHTNESS_MODE] = selected_mode
            _prune_light_group_options_for_brightness_mode(
                existing=feature_cfg,
                mode=selected_mode,
            )
            if selected_mode == LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT:
                await flow._persist_options()
                flow._feature_step_id = _LIGHT_GROUP_MENU_STEP
                return await handle_feature_conf(flow)
            flow._feature_step_id = (
                _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP
                if selected_mode == LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
                else _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP
            )
            return await handle_feature_conf(flow)
        return flow.async_show_form(
            step_id=_LIGHT_GROUP_BRIGHTNESS_STEP,
            data_schema=flow._build_schema_from_vol(
                mode_schema,
                saved_options=enabled_feature_map(flow.area_options).get(
                    MagicAreasFeatures.LIGHT_GROUPS.value, {}
                ),
                selectors={
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE: build_selector_select(
                        options=[
                            LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
                            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
                        ],
                        multiple=False,
                        translation_key="light_brightness_mode",
                    )
                },
            ),
            errors=errors,
        )

    if (
        step_id.startswith("feature_conf_")
        and step_id not in _LIGHT_GROUP_SUBSTEPS
        and not step_id.endswith(_FEATURE_SETTINGS_STEP_SUFFIX)
        and step_id != "feature_conf_climate_control_select_presets"
    ):
        section_feature_key = step_id.replace("feature_conf_", "")
        try:
            section_feature_enum = MagicAreasFeatures(section_feature_key)
        except ValueError:
            section_feature_enum = None

        if (
            section_feature_enum is not None
            and section_feature_key not in _FEATURE_MENU_EXCLUSIONS
        ):
            settings_step_id = f"{step_id}{_FEATURE_SETTINGS_STEP_SUFFIX}"
            if user_input is None:
                menu_options: list[str] = [settings_step_id]
                if section_feature_key == MagicAreasFeatures.CLIMATE_CONTROL.value:
                    menu_options.append("feature_conf_climate_control_select_presets")
                menu_options.append("show_menu")
                # noinspection PyTypeChecker
                return flow.async_show_menu(
                    step_id=step_id,
                    menu_options=menu_options,
                )
            step_id = settings_step_id

    if step_id in _LIGHT_GROUP_SUBSTEPS:
        feature_key = MagicAreasFeatures.LIGHT_GROUPS.value
    elif step_id.endswith(_FEATURE_SETTINGS_STEP_SUFFIX):
        feature_key = step_id.removeprefix("feature_conf_").removesuffix(
            _FEATURE_SETTINGS_STEP_SUFFIX
        )
    else:
        feature_key = step_id.replace("feature_conf_", "")
    try:
        feature_enum = MagicAreasFeatures(feature_key)
    except ValueError:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")

    feature_registry = get_feature_config_steps()

    if feature_enum not in feature_registry:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")

    feature = feature_registry[feature_enum]
    schema = feature.schema or CONFIGURABLE_FEATURES.get(feature.feature)
    if schema is None:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")
    schema = _copy_schema(schema)

    selectors: SelectorMap = {}

    if feature_enum == MagicAreasFeatures.LIGHT_GROUPS:
        mode = _resolve_light_groups_mode(flow, user_input)
        adaptive_lighting_mode = _resolve_adaptive_lighting_mode(flow, user_input)
        include_keys = _light_group_step_include_keys(
            step_id=step_id,
            mode=mode,
            adaptive_lighting_mode=adaptive_lighting_mode,
        )
        feature_config = enabled_feature_map(flow.area_options).get(
            MagicAreasFeatures.LIGHT_GROUPS.value, {}
        )
        if not isinstance(feature_config, Mapping):
            feature_config = {}
        if (
            step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP
            and adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
        ):
            candidates = _adaptive_lighting_candidate_switch_sets(flow, feature_config)
            candidate_options = ["", *candidates]
            for category in _light_group_pairing_categories(flow, feature_config):
                pair_key = adaptive_lighting_pair_key(category)
                selected = _adaptive_lighting_pair_value(feature_config, category)
                options = list(candidate_options)
                if selected and selected not in options:
                    options.append(selected)
                include_keys.add(pair_key)
                schema.schema[vol.Optional(pair_key, default=selected)] = vol.In(
                    options
                )
                selectors[pair_key] = build_selector_select(
                    options=options,
                    multiple=False,
                    translation_key="adaptive_lighting_switch_set",
                )
        if (
            step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP
            and adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ):
            role_options = _light_group_managed_role_options(flow, feature_config)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
            _remove_schema_key(schema, CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            _remove_schema_key(
                schema,
                CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
            )
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
                    default=_light_group_manage_all_lights_default(feature_config),
                )
            ] = cv.boolean
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
                    default=_light_group_managed_roles_default(
                        role_options=role_options,
                        feature_config=feature_config,
                    ),
                )
            ] = vol.All(cv.ensure_list, [vol.In(role_options)])
            selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] = (
                build_selector_select(
                    options=role_options,
                    multiple=True,
                    translation_key="adaptive_lighting_managed_roles",
                )
            )
            selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] = (
                build_selector_boolean()
            )
        schema = _filter_schema_for_keys(schema, include_keys)

        _add_light_group_brightness_selectors(
            flow=flow,
            step_id=step_id,
            mode=mode,
            selectors=selectors,
        )
        if step_id in {
            _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
            _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
        }:
            _remove_schema_key(schema, CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY)
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
                    default=_default_inside_bright_entity(
                        flow=flow,
                        feature_config=feature_config,
                    ),
                )
            ] = cv.string
        _add_light_group_adaptive_lighting_selectors(
            step_id=step_id,
            selectors=selectors,
        )
        _add_light_group_role_selectors(
            step_id=step_id,
            flow=flow,
            selectors=selectors,
        )

    _add_non_light_feature_selectors(
        flow=flow,
        feature_enum=feature_enum,
        selectors=selectors,
    )

    return await handle_feature_form(
        flow=flow,
        feature_enum=feature_enum,
        step_id=step_id,
        schema=schema,
        user_input=user_input,
        merge_options=(
            True
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else feature.merge_options
        ),
        next_step=(
            _LIGHT_GROUP_MENU_STEP
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else (
                feature.next_step
                or (
                    _feature_section_step(feature_enum)
                    if step_id.endswith(_FEATURE_SETTINGS_STEP_SUFFIX)
                    else None
                )
            )
        ),
        selectors=selectors,
    )


async def handle_climate_preset_selection(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle climate control preset selection step."""
    climate_cfg: ConfigSubMap = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.CLIMATE_CONTROL.value, {}
    )
    climate_entity_value = climate_cfg.get(CLIMATE_CONTROL_ENTITY_KEY)
    climate_entity_id = (
        climate_entity_value if isinstance(climate_entity_value, str) else None
    )

    try:
        selectors, dynamic_validators = build_climate_preset_selectors_and_validators(
            flow.hass,
            climate_entity_id,
            build_selector_select,
            preset_config_keys=CLIMATE_CONTROL_PRESET_OPTION_KEYS,
        )
    except NoEntitySelectedError:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="no_entity_selected")
    except InvalidEntityError:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="invalid_entity")
    except NoPresetSupportError:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="climate_no_preset_support")

    return await handle_feature_form(
        flow=flow,
        feature_enum=MagicAreasFeatures.CLIMATE_CONTROL,
        step_id="feature_conf_climate_control_select_presets",
        schema=CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
        user_input=user_input,
        merge_options=True,
        next_step=_feature_section_step(MagicAreasFeatures.CLIMATE_CONTROL),
        selectors=selectors,
        dynamic_validators=dynamic_validators,
    )
