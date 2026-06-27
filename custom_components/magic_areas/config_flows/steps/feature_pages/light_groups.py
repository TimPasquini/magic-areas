"""Light-group feature page routing for options flow."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
)
from custom_components.magic_areas.config_flows.base import (
    SelectorMap,
    enabled_feature_map,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_boolean,
    build_selector_entity_simple,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    AdaptiveLightingSwitchSet,
    switch_set_from_explicit_refs,
    switch_sets_from_hass_registry,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_threshold_light_sensor_unique_id,
)
from custom_components.magic_areas.enums import (
    LightGroupCategory,
    MagicAreasFeatures,
    SelectorTranslationKeys,
)
from custom_components.magic_areas.light_groups import (
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
    LIGHT_GROUP_PRESETS,
    adaptive_lighting_pair_key,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import (
        OptionsFlowHandler,
    )

_LIGHT_GROUP_LUX_SELECTOR_MAX = 120_000

LIGHT_GROUP_MENU_STEP = "feature_conf_light_groups"
LIGHT_GROUP_ROLES_STEP = "feature_conf_light_groups_roles"
LIGHT_GROUP_BRIGHTNESS_STEP = "feature_conf_light_groups_brightness"
LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP = "feature_conf_light_groups_brightness_advisory"
LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP = "feature_conf_light_groups_brightness_adaptive"
LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP = "feature_conf_light_groups_adaptive_lighting"
LIGHT_GROUP_SUBSTEPS = {
    LIGHT_GROUP_MENU_STEP,
    LIGHT_GROUP_ROLES_STEP,
    LIGHT_GROUP_BRIGHTNESS_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
}
LIGHT_GROUP_ADVISORY_KEYS = {
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
}
LIGHT_GROUP_ADAPTIVE_ONLY_KEYS = {
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
LIGHT_GROUP_PRESERVED_HIDDEN_KEYS = {
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
}
LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX = (
    LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX
)
LIGHT_GROUP_ROLE_KEYS = {
    key
    for preset in LIGHT_GROUP_PRESETS
    for key in (preset.category, preset.states_key, preset.act_on_key)
}


def resolve_light_groups_mode(
    flow: OptionsFlowHandler, user_input: Mapping[str, object] | None
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


def remove_schema_key(schema: vol.Schema, key_to_remove: str) -> None:
    """Remove existing markers for one config key before adding dynamic variants."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return
    for marker in tuple(raw_schema):
        if getattr(marker, "schema", marker) == key_to_remove:
            raw_schema.pop(marker, None)


def light_group_step_include_keys(
    *,
    step_id: str,
    mode: str,
    adaptive_lighting_mode: str,
) -> set[str]:
    """Return light-group config keys rendered on one light-group substep."""
    if step_id == LIGHT_GROUP_ROLES_STEP:
        return set(LIGHT_GROUP_ROLE_KEYS)

    if step_id == LIGHT_GROUP_BRIGHTNESS_STEP:
        return {CONF_LIGHT_GROUP_BRIGHTNESS_MODE}

    if step_id == LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP:
        return set(LIGHT_GROUP_ADVISORY_KEYS)

    if step_id == LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP:
        return set(LIGHT_GROUP_ADVISORY_KEYS | LIGHT_GROUP_ADAPTIVE_ONLY_KEYS)

    if step_id == LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
        include_keys = {CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE}
        if adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE:
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
        return include_keys

    return set()


def resolve_adaptive_lighting_mode(
    flow: OptionsFlowHandler, user_input: Mapping[str, object] | None
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


def light_group_pairing_categories(
    flow: OptionsFlowHandler,
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


def configured_adaptive_lighting_switch_sets(
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


def light_group_managed_role_options(
    flow: OptionsFlowHandler,
    feature_config: Mapping[str, object],
) -> list[str]:
    """Return role options that can receive MA-managed Adaptive Lighting configs."""
    options = [
        category
        for category in light_group_pairing_categories(flow, feature_config)
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


def light_group_manage_all_lights_default(
    feature_config: Mapping[str, object],
) -> bool:
    """Return saved room-level manage preference."""
    raw_value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
    try:
        return bool(cv.boolean(raw_value))
    except vol.Invalid:
        return False


def light_group_managed_roles_default(
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


def prune_light_group_options_for_brightness_mode(
    *,
    existing: dict[str, object],
    mode: str,
) -> None:
    """Preserve dormant brightness settings when switching modes."""
    return


def default_inside_bright_entity(
    *,
    flow: OptionsFlowHandler,
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
    if (
        isinstance(threshold_entity, str)
        and threshold_entity in flow.all_binary_entities
    ):
        return threshold_entity

    return ""


def should_rerender_light_group_brightness_step(
    *,
    step_id: str,
    user_input: Mapping[str, object],
    validated: Mapping[str, object],
) -> bool:
    """Return whether brightness mode selection should reveal follow-up controls immediately."""
    if step_id != LIGHT_GROUP_BRIGHTNESS_STEP:
        return False
    if CONF_LIGHT_GROUP_BRIGHTNESS_MODE not in validated:
        return False
    return len(user_input) == 1 and CONF_LIGHT_GROUP_BRIGHTNESS_MODE in user_input


def should_rerender_light_group_adaptive_lighting_step(
    *,
    step_id: str,
    user_input: Mapping[str, object],
    validated: Mapping[str, object],
) -> bool:
    """Return whether mode selection should reveal follow-up controls immediately."""
    if step_id != LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
        return False
    mode = validated.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
    if mode not in {
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
        LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    }:
        return False
    if mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING:
        return not any(
            key.startswith(LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX)
            for key in user_input
        )
    return (
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL not in user_input
        and CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES not in user_input
    )


def adaptive_lighting_candidate_switch_sets(
    flow: OptionsFlowHandler,
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
    for switch_set in configured_adaptive_lighting_switch_sets(
        area_config.id,
        feature_config,
    ).values():
        candidates.setdefault(switch_set.main_switch_entity_id, switch_set)
    return dict(sorted(candidates.items()))


def adaptive_lighting_pair_value(
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


def adaptive_lighting_switch_set_refs(
    switch_set: AdaptiveLightingSwitchSet,
) -> dict[str, str]:
    """Return persisted explicit switch refs for one AL switch set."""
    return {
        MAIN_SWITCH: switch_set.main_switch_entity_id,
        SLEEP_SWITCH: switch_set.sleep_switch_entity_id,
        ADAPT_BRIGHTNESS_SWITCH: switch_set.adapt_brightness_switch_entity_id,
        ADAPT_COLOR_SWITCH: switch_set.adapt_color_switch_entity_id,
    }


def normalize_light_group_adaptive_lighting_options(
    flow: OptionsFlowHandler,
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
            if key.startswith(LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX):
                feature_config.pop(key, None)
        return

    candidates = adaptive_lighting_candidate_switch_sets(flow, feature_config)
    categories = set(light_group_pairing_categories(flow, feature_config))
    for key in feature_config:
        if key.startswith(LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX):
            categories.add(key.removeprefix(LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX))

    switch_sets: dict[str, dict[str, str]] = {}
    for category in sorted(categories):
        pair_key = adaptive_lighting_pair_key(category)
        selected = feature_config.pop(pair_key, "")
        if not isinstance(selected, str) or not selected:
            continue
        switch_set = candidates.get(selected)
        if switch_set is None:
            continue
        switch_sets[category] = adaptive_lighting_switch_set_refs(switch_set)

    feature_config[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS] = switch_sets


def handle_light_group_menu_route(
    flow: OptionsFlowHandler,
    *,
    step_id: str,
) -> config_entries.ConfigFlowResult | None:
    """Handle the light-group section menu."""
    if step_id != LIGHT_GROUP_MENU_STEP:
        return None
    # noinspection PyTypeChecker
    return flow.async_show_menu(
        step_id=LIGHT_GROUP_MENU_STEP,
        menu_options=[
            LIGHT_GROUP_ROLES_STEP,
            LIGHT_GROUP_BRIGHTNESS_STEP,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
            "show_menu",
        ],
    )


def add_light_group_brightness_selectors(
    *,
    flow: OptionsFlowHandler,
    step_id: str,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for the light-group brightness substep."""
    if step_id not in {
        LIGHT_GROUP_BRIGHTNESS_STEP,
        LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
        LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    }:
        return

    if step_id == LIGHT_GROUP_BRIGHTNESS_STEP:
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

    if step_id != LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP:
        return

    selectors[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
    )
    selectors[CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
    )
    selectors[CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS] = build_selector_number(
        min_value=-_LIGHT_GROUP_LUX_SELECTOR_MAX, unit_of_measurement="s"
    )
    selectors[CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE] = build_selector_boolean()
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


def add_light_group_adaptive_lighting_selectors(
    *,
    step_id: str,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for the Adaptive Lighting coordination substep."""
    if step_id != LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
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


def add_light_group_role_selectors(
    *,
    step_id: str,
    flow: OptionsFlowHandler,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for the light-role membership substep."""
    if step_id != LIGHT_GROUP_ROLES_STEP:
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
