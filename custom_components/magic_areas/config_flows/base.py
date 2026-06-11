"""Base class for config flow."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence

import voluptuous as vol

from custom_components.magic_areas.components import MagicAreasConfigEntry
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import FeatureConfigStep
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY

_LOGGER = logging.getLogger(__name__)
_EXPECTED_OPTIONS_FLOW_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)

ConfigValue = object
ConfigMap = Mapping[str, ConfigValue]
MutableConfigMap = dict[str, ConfigValue]
ConfigSubMap = dict[str, ConfigValue]
DynamicValidatorMap = dict[str, object]
SelectorMap = dict[str, object]
ConfigOption = tuple[str, ConfigValue, object]
SuccessCallback = Callable[[], Awaitable[object] | object]


def _suggested_value(value: object) -> object:
    """Return a JSON-serializable suggested value for HA flow forms."""
    if value is vol.UNDEFINED or callable(value):
        return None
    return value


class ConfigBase:
    """Base class for config flow."""

    config_entry: MagicAreasConfigEntry | None = None

    def _build_options_schema(
        self,
        options: Sequence[ConfigOption],
        *,
        saved_options: ConfigMap | None = None,
        dynamic_validators: Mapping[str, object] | None = None,
        selectors: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build schema for configuration options."""
        _LOGGER.debug(
            "ConfigFlow: Building schema from options: %s - dynamic_validators: %s",
            str(options),
            str(dynamic_validators),
        )

        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if saved_options is None and self.config_entry:
            saved_options = self.config_entry.options

        _LOGGER.debug(
            "ConfigFlow: Data for pre-populating fields: %s", str(saved_options)
        )

        schema = {
            vol.Optional(
                name,
                description={
                    "suggested_value": _suggested_value(
                        saved_options.get(name)
                        if saved_options and saved_options.get(name) is not None
                        else default
                    )
                },
                default=default,
            ): (
                selectors[name]
                if name in selectors
                else dynamic_validators.get(name, validation)
            )
            for name, default, validation in options
        }

        _LOGGER.debug("ConfigFlow: Built schema: %s", str(schema))

        return vol.Schema(schema)

    def _build_schema_from_vol(
        self,
        schema: vol.Schema,
        *,
        saved_options: ConfigMap | None = None,
        dynamic_validators: Mapping[str, object] | None = None,
        selectors: Mapping[str, object] | None = None,
    ) -> vol.Schema:
        """Build schema from a voluptuous schema and optional selector overrides."""
        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if saved_options is None and self.config_entry:
            saved_options = self.config_entry.options

        mapped: dict[vol.Marker, object] = {}
        for key, validator in schema.schema.items():
            if isinstance(key, (vol.Optional, vol.Required)):
                name = key.schema
                default = key.default
            else:
                name = key
                default = vol.UNDEFINED

            suggested = (
                saved_options.get(name)
                if saved_options and saved_options.get(name) is not None
                else default
            )

            mapped[
                vol.Optional(
                    name,
                    description={"suggested_value": _suggested_value(suggested)},
                    default=default,
                )
            ] = selectors.get(name, dynamic_validators.get(name, validator))

        return vol.Schema(mapped)

def invalid_input_error() -> dict[str, str]:
    """Return standard invalid-input error payload for flow forms."""
    return {"base": "invalid_input"}


def get_feature_config_steps() -> dict[MagicAreasFeatures, FeatureConfigStep]:
    """Return configurable feature steps keyed by feature enum."""
    registry: dict[MagicAreasFeatures, FeatureConfigStep] = {}
    for module in FEATURE_REGISTRY.modules():
        for step in module.config_flow_steps():
            if step.step_id != f"feature_conf_{step.feature}":
                continue
            registry[step.feature] = step
    return registry


def enabled_feature_map(options: ConfigMap) -> dict[str, ConfigSubMap]:
    """Return enabled-features mapping from area options."""
    value = options.get(CONF_ENABLED_FEATURES, {})
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, ConfigSubMap] = {}
    for key, nested in value.items():
        if isinstance(key, str) and isinstance(nested, dict):
            normalized[str(key)] = dict(nested)
    return normalized


def ensure_enabled_feature_map(options: MutableConfigMap) -> dict[str, ConfigSubMap]:
    """Ensure and return mutable enabled-features mapping in options."""
    features = options.get(CONF_ENABLED_FEATURES)
    if not isinstance(features, dict):
        features = {}
        options[CONF_ENABLED_FEATURES] = features
    normalized: dict[str, ConfigSubMap] = {}
    for key, nested in features.items():
        if isinstance(key, str) and isinstance(nested, dict):
            normalized[str(key)] = nested
    if normalized is not features:
        options[CONF_ENABLED_FEATURES] = normalized
    return normalized


def errors_from_validation(validation: vol.MultipleInvalid) -> dict[str, str]:
    """Convert voluptuous validation errors to Home Assistant form errors."""
    field_errors = {
        str(error.path[0]): str(error.msg)
        for error in validation.errors
        if isinstance(error, vol.Invalid) and error.path
    }
    if field_errors:
        return field_errors
    return invalid_input_error()


async def handle_step_validation(
    *,
    user_input: Mapping[str, object] | None,
    schema: vol.Schema,
    area_name: str,
    step_name: str,
    area_options: MutableConfigMap,
    config_key: str | None = None,
    on_success: SuccessCallback,
) -> tuple[dict[str, str], bool]:
    """Handle validation for a config flow step."""
    errors: dict[str, str] = {}

    if user_input is None:
        return errors, False
    _LOGGER.debug(
        "OptionsFlow: Validating area %s %s config: %s",
        area_name,
        step_name,
        str(user_input),
    )

    try:
        validated = schema(dict(user_input))

        # Update area_options (either root or specific key)
        if config_key:
            if config_key not in area_options:
                area_options[config_key] = {}
            nested_options = area_options[config_key]
            if not isinstance(nested_options, dict):
                nested_options = {}
                area_options[config_key] = nested_options
            nested_options.update(validated)
        else:
            area_options.update(validated)

        _LOGGER.debug(
            "OptionsFlow: Saving area %s %s config: %s",
            area_name,
            step_name,
            str(area_options),
        )

        return errors, True

    except vol.MultipleInvalid as validation:
        errors = errors_from_validation(validation)
        _LOGGER.debug(
            "OptionsFlow: Found the following errors for area %s: %s",
            area_name,
            str(errors),
        )
        return errors, False

    except _EXPECTED_OPTIONS_FLOW_ERRORS as exc:
        _LOGGER.warning(
            "OptionsFlow: Unexpected error in area %s step %s: %s",
            area_name,
            step_name,
            str(exc),
        )
        return invalid_input_error(), False
