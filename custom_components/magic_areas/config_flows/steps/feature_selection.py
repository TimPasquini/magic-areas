"""Feature selection step handler for options flow."""

from typing import TYPE_CHECKING, Any

from homeassistant import config_entries

from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.config_flows.steps.feature_helpers import (
    get_feature_list,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler


async def handle_feature_selection(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle feature selection step."""
    feature_list = get_feature_list(flow._area_config)

    if user_input is not None:
        # Convert string keys to enum members
        selected_features = [
            MagicAreasFeatures(feature) for feature, is_selected in user_input.items() if is_selected
        ]

        if CONF_ENABLED_FEATURES not in flow.area_options:
            flow.area_options[CONF_ENABLED_FEATURES] = {}

        for c_feature in feature_list:
            if c_feature in selected_features:
                if c_feature not in flow.area_options.get(
                    CONF_ENABLED_FEATURES, {}
                ):
                    flow.area_options[CONF_ENABLED_FEATURES][c_feature] = {}
            else:
                # Remove feature if we had previously enabled
                if c_feature in flow.area_options.get(CONF_ENABLED_FEATURES, {}):
                    flow.area_options[CONF_ENABLED_FEATURES].pop(c_feature)

        return await flow.async_step_show_menu()

    return flow.async_show_form(
        step_id="select_features",
        data_schema=flow._build_options_schema(
            options=[(str(feature), False, bool) for feature in feature_list],
            saved_options={
                str(feature): (
                    feature in flow.area_options.get(CONF_ENABLED_FEATURES, {})
                )
                for feature in feature_list
            },
        ),
    )
