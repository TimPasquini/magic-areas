"""Feature-page helpers for options flow."""

from custom_components.magic_areas.config_flows.steps.feature_pages.generic import (
    copy_schema,
    filter_schema_for_keys,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.light_groups import (
    LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
    LIGHT_GROUP_BRIGHTNESS_STEP,
    LIGHT_GROUP_MENU_STEP,
    LIGHT_GROUP_ROLES_STEP,
    LIGHT_GROUP_SUBSTEPS,
    add_light_group_adaptive_lighting_selectors,
    add_light_group_brightness_selectors,
    add_light_group_role_selectors,
    handle_light_group_menu_route,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.simple import (
    add_non_light_feature_selectors,
)

__all__ = [
    "LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP",
    "LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP",
    "LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP",
    "LIGHT_GROUP_BRIGHTNESS_STEP",
    "LIGHT_GROUP_MENU_STEP",
    "LIGHT_GROUP_ROLES_STEP",
    "LIGHT_GROUP_SUBSTEPS",
    "add_light_group_adaptive_lighting_selectors",
    "add_light_group_brightness_selectors",
    "add_light_group_role_selectors",
    "add_non_light_feature_selectors",
    "copy_schema",
    "filter_schema_for_keys",
    "handle_light_group_menu_route",
]
