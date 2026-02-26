"""Feature configuration step handlers for options flow."""

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.config_keys import (
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


async def handle_feature_conf(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Configure a specific feature using registry-based approach."""
    step_id = flow._feature_step_id or str(flow.context.get("step_id", ""))
    feature_key = step_id.replace("feature_conf_", "")
    try:
        feature_enum = MagicAreasFeatures(feature_key)
    except ValueError:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")

    if feature_enum not in FEATURE_REGISTRY:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")

    feature = FEATURE_REGISTRY[feature_enum]
    errors: dict[str, str] = {}

    schema = feature.schema or CONFIGURABLE_FEATURES.get(feature.name)
    if schema is None:
        # noinspection PyTypeChecker
        return flow.async_abort(reason="unknown_feature")

    if user_input is not None:
        try:
            validated = schema(user_input)
        except vol.MultipleInvalid:
            errors = {"base": "invalid_input"}
        else:
            features = flow.area_options.setdefault(CONF_ENABLED_FEATURES, {})
            if feature.merge_options:
                features.setdefault(feature.name, {}).update(validated)
            else:
                features[feature.name] = validated

            if feature.next_step:
                return await getattr(flow, f"async_step_{feature.next_step}")()
            # noinspection PyTypeChecker
            return await flow.async_step_show_menu()

    selectors: dict[str, Any] = {}

    # Wasp in a Box: UI submits a list for wasp_device_classes; override with selector.
    if feature_enum == MagicAreasFeatures.WASP_IN_A_BOX:
        selectors[CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES] = build_selector_select(
            options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
            multiple=True,
        )

    # noinspection PyTypeChecker
    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=flow.area_options.get(CONF_ENABLED_FEATURES, {}).get(
                feature.name, {}
            ),
            selectors=selectors,
        ),
        errors=errors,
    )
