"""Advanced feature configuration handler with dynamic selector building."""

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.policy import (
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.schemas.features import CONFIGURABLE_FEATURES
from custom_components.magic_areas.schemas.selectors import (
    build_selector_select,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler


async def handle_feature_conf_advanced(
    flow: "OptionsFlowHandler",
    feature_key: str,
    user_input: dict[str, Any] | None = None,
) -> config_entries.ConfigFlowResult:
    """Handle configuration for a single feature with dynamic selectors.

    This is the advanced handler that builds dynamic selectors and handles
    special cases like Wasp in a Box multi-select override.

    Args:
        flow: OptionsFlowHandler instance
        feature_key: Feature key (enum member or string)
        user_input: User input from form submission

    Returns:
        ConfigFlowResult with form or abort result

    """
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
                validated = CONFIGURABLE_FEATURES[MagicAreasFeatures(feature.name)](
                    user_input
                )
        except vol.MultipleInvalid:
            errors = {"base": "invalid_input"}
        else:
            features = flow.area_options.setdefault(CONF_ENABLED_FEATURES, {})
            if feature.merge_options:
                features.setdefault(feature.name, {}).update(validated)
            else:
                features[feature.name] = validated

            if feature.next_step:
                # feature.next_step is a *step_id* (e.g. "feature_conf_climate_control_select_presets")
                return await getattr(flow, f"async_step_{feature.next_step}")()

            # noinspection PyTypeChecker
            return await flow.async_step_show_menu()

    selectors: dict[str, Any] = {}

    # Wasp in a Box: UI submits a list for wasp_device_classes, but schema uses vol.In (single value).
    # Override with a multi-select selector.
    if feature_key == MagicAreasFeatures.WASP_IN_A_BOX:
        selectors[CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES] = build_selector_select(
            options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
            multiple=True,
        )

    # noinspection PyTypeChecker
    return flow.async_show_form(
        step_id=f"feature_conf_{feature_key}",
        data_schema=flow._build_options_schema(
            options=feature.options,
            saved_options=flow.area_options.get(CONF_ENABLED_FEATURES, {}).get(
                feature.name, {}
            ),
            selectors=selectors,
        ),
        errors=errors,
    )
