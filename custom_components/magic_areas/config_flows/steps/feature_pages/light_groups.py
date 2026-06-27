"""Light-group feature page routing for options flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant import config_entries

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
)
from custom_components.magic_areas.config_flows.base import SelectorMap
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_boolean,
    build_selector_entity_simple,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.enums import SelectorTranslationKeys
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
