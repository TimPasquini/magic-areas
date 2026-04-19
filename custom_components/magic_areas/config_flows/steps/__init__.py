"""Public step-handler surface for options flow."""

from custom_components.magic_areas.config_flows.steps.area_steps import (
    handle_area_config,
    handle_custom_control_groups,
    handle_presence_tracking,
    handle_secondary_states,
)
from custom_components.magic_areas.config_flows.steps.feature_config import (
    get_configurable_features,
    get_feature_list,
    handle_feature_selection,
    handle_climate_preset_selection,
    handle_feature_conf,
)

__all__ = [
    "handle_area_config",
    "handle_custom_control_groups",
    "handle_presence_tracking",
    "handle_secondary_states",
    "handle_climate_preset_selection",
    "handle_feature_conf",
    "handle_feature_selection",
    "get_configurable_features",
    "get_feature_list",
]
