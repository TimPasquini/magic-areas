"""Generic feature-page schema helpers for options flow."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.base import (
    enabled_feature_map,
    ensure_enabled_feature_map,
    invalid_input_error,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:
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

type PrepareFeatureFormValidated = Callable[
    ["OptionsFlowHandler", str, dict[str, object], Mapping[str, object]], None
]
type FeatureFormRerenderPredicate = Callable[
    [str, Mapping[str, object], Mapping[str, object]], bool
]
type FeatureFormRerenderHandler = Callable[
    ["OptionsFlowHandler"], Awaitable[config_entries.ConfigFlowResult]
]


def copy_schema(schema: vol.Schema) -> vol.Schema:
    """Return a shallow copy so dynamic flow fields do not mutate shared schemas."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return schema
    return vol.Schema(dict(raw_schema), extra=schema.extra)


def filter_schema_for_keys(schema: vol.Schema, include_keys: set[str]) -> vol.Schema:
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


async def handle_feature_form(
    *,
    flow: OptionsFlowHandler,
    feature_enum: MagicAreasFeatures,
    step_id: str,
    schema: vol.Schema,
    user_input: Mapping[str, object] | None = None,
    merge_options: bool = False,
    next_step: str | None = None,
    selectors: Mapping[str, object] | None = None,
    dynamic_validators: Mapping[str, object] | None = None,
    prepare_validated: PrepareFeatureFormValidated | None = None,
    should_rerender: FeatureFormRerenderPredicate | None = None,
    rerender_handler: FeatureFormRerenderHandler | None = None,
) -> config_entries.ConfigFlowResult:
    """Validate, persist, and render a feature configuration form."""
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
            if prepare_validated is not None:
                prepare_validated(flow, step_id, validated_dict, user_input)
            if merge_options:
                features.setdefault(feature_key, {}).update(validated_dict)
            else:
                features[feature_key] = validated_dict

            if should_rerender is not None and should_rerender(
                step_id,
                user_input,
                validated_dict,
            ):
                if rerender_handler is None:
                    raise ValueError("Feature form rerender requested without handler")
                return await rerender_handler(flow)

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
