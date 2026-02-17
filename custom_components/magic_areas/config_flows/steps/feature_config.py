"""Feature configuration step handlers for options flow."""

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.schemas.features import CONFIGURABLE_FEATURES

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler


async def handle_feature_conf(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Configure a specific feature using registry-based approach."""
    step_id = flow._feature_step_id or str(flow.context.get("step_id", ""))
    feature_key = step_id.replace("feature_conf_", "")

    if feature_key not in FEATURE_REGISTRY:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")

    feature = FEATURE_REGISTRY[feature_key]
    errors: dict[str, str] = {}

    if user_input is not None:
        try:
            if feature.schema:
                validated = feature.schema(user_input)
            else:
                validated = CONFIGURABLE_FEATURES[MagicAreasFeatures(feature.name)](user_input)
        except vol.MultipleInvalid:
            errors = {"base": "invalid_input"}
        else:
            features = flow.area_options.setdefault(CONF_ENABLED_FEATURES, {})
            if feature.merge_options:
                features.setdefault(feature.name, {}).update(validated)
            else:
                features[feature.name] = validated

            if feature.next_step:
                return await getattr(flow, feature.next_step)()
            # noinspection PyTypeChecker
            return await flow.async_step_show_menu()

    # noinspection PyTypeChecker
    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_options_schema(
            options=feature.options,
            saved_options=flow.area_options.get(CONF_ENABLED_FEATURES, {}).get(
                feature.name, {}
            ),
        ),
        errors=errors,
    )
