"""Feature selection and configuration step handlers for options flow."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.base import (
    ConfigSubMap,
    SelectorMap,
    enabled_feature_map,
    ensure_enabled_feature_map,
    get_feature_config_steps,
    invalid_input_error,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.config.readers import (
    CLIMATE_CONTROL_ENTITY_KEY,
    CLIMATE_CONTROL_PRESET_OPTION_KEYS,
    WASP_IN_A_BOX_OPTION_KEYS,
)
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
from custom_components.magic_areas.policy import (
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
    build_climate_preset_selectors_and_validators,
    build_selector_select,
)
from custom_components.magic_areas.schemas import CONFIGURABLE_FEATURES
from custom_components.magic_areas.schemas import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler

_LOGGER = logging.getLogger(__name__)
_EXPECTED_FEATURE_FLOW_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)

def get_feature_list(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
    """Return list of available features for area type."""
    return FEATURE_REGISTRY.available_features_for_area(area_config)


def get_configurable_features(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
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

        return await flow.async_step_show_menu()

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
            if merge_options:
                features.setdefault(feature_key, {}).update(dict(validated))
            else:
                features[feature_key] = dict(validated)

            if next_step:
                step_handler: Callable[[], Awaitable[config_entries.ConfigFlowResult]]
                step_handler = getattr(flow, f"async_step_{next_step}")
                return await step_handler()
            # noinspection PyTypeChecker
            return await flow.async_step_show_menu()

    # noinspection PyTypeChecker
    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=enabled_feature_map(flow.area_options).get(feature_enum.value, {}),
            selectors=selectors or {},
            dynamic_validators=dynamic_validators or {},
        ),
        errors=errors,
    )


async def handle_feature_conf(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Configure a specific feature using registry-based approach."""
    step_id = flow._feature_step_id or str(flow.context.get("step_id", ""))
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

    selectors: SelectorMap = {}

    # Wasp in a Box: UI submits a list for wasp_device_classes; override with selector.
    if feature_enum == MagicAreasFeatures.WASP_IN_A_BOX:
        selectors[WASP_IN_A_BOX_OPTION_KEYS[2]] = build_selector_select(
            options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
            multiple=True,
        )

    return await handle_feature_form(
        flow=flow,
        feature_enum=feature_enum,
        step_id=step_id,
        schema=schema,
        user_input=user_input,
        merge_options=feature.merge_options,
        next_step=feature.next_step,
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
        selectors=selectors,
        dynamic_validators=dynamic_validators,
    )
