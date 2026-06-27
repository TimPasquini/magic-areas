"""Feature selection and configuration step handlers for options flow."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_FAN_CONTROLLER_ACTIVE_STATES,
    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
    CONF_FAN_CONTROLLER_DETECTION_MODE,
    CONF_FAN_CONTROLLER_HYSTERESIS,
    CONF_FAN_CONTROLLER_MEMBERS,
    CONF_FAN_CONTROLLER_ON_THRESHOLD,
    CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS,
    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
    CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
    CONF_FAN_CONTROLLER_SUPPRESS_STATES,
    CONF_FAN_GROUPS_CONTROLLERS,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanClearBehavior,
    FanControllerRole,
    FanDetectionMode,
    FanSensorUnavailableBehavior,
)
from custom_components.magic_areas.config_flows.base import (
    SelectorMap,
    enabled_feature_map,
    ensure_enabled_feature_map,
    get_feature_config_steps,
    invalid_input_error,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.generic import (
    copy_schema,
    filter_schema_for_keys,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.light_groups import (
    LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP as _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP as _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP as _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
    LIGHT_GROUP_BRIGHTNESS_STEP as _LIGHT_GROUP_BRIGHTNESS_STEP,
    LIGHT_GROUP_MENU_STEP as _LIGHT_GROUP_MENU_STEP,
    LIGHT_GROUP_PRESERVED_HIDDEN_KEYS as _LIGHT_GROUP_PRESERVED_HIDDEN_KEYS,
    LIGHT_GROUP_SUBSTEPS as _LIGHT_GROUP_SUBSTEPS,
    add_light_group_adaptive_lighting_selectors,
    add_light_group_brightness_selectors,
    add_light_group_role_selectors,
    adaptive_lighting_candidate_switch_sets,
    adaptive_lighting_pair_value,
    default_inside_bright_entity,
    handle_light_group_menu_route,
    light_group_manage_all_lights_default,
    light_group_managed_role_options,
    light_group_managed_roles_default,
    light_group_pairing_categories,
    light_group_step_include_keys,
    normalize_light_group_adaptive_lighting_options,
    prune_light_group_options_for_brightness_mode,
    remove_schema_key,
    resolve_adaptive_lighting_mode,
    resolve_light_groups_mode,
    should_rerender_light_group_adaptive_lighting_step,
    should_rerender_light_group_brightness_step,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.simple import (
    add_non_light_feature_selectors,
)
from custom_components.magic_areas.enums import (
    MagicAreasFeatures,
    SelectorTranslationKeys,
)
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
from custom_components.magic_areas.light_groups import (
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_PRESETS,
    adaptive_lighting_pair_key,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_entity_simple,
    build_selector_boolean,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.schemas import CONFIGURABLE_FEATURES

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
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

_LIGHT_GROUP_LUX_SELECTOR_MAX = 120_000
_FAN_GROUP_MENU_STEP = "feature_conf_fan_groups"
_FAN_GROUP_COOLING_STEP = "feature_conf_fan_groups_cooling"
_FAN_GROUP_HUMIDITY_STEP = "feature_conf_fan_groups_humidity"
_FAN_GROUP_ODOR_STEP = "feature_conf_fan_groups_odor"
_FAN_GROUP_SETTINGS_STEP = "feature_conf_fan_groups_settings"
_FAN_GROUP_STEP_ROLE = {
    _FAN_GROUP_COOLING_STEP: FanControllerRole.COOLING.value,
    _FAN_GROUP_HUMIDITY_STEP: FanControllerRole.HUMIDITY.value,
    _FAN_GROUP_ODOR_STEP: FanControllerRole.ODOR.value,
    _FAN_GROUP_SETTINGS_STEP: FanControllerRole.COOLING.value,
}
_FAN_GROUP_SUBSTEPS = set(_FAN_GROUP_STEP_ROLE)
_FEATURE_SETTINGS_STEP_SUFFIX = "_settings"
_FEATURE_MENU_EXCLUSIONS = {
    MagicAreasFeatures.AGGREGATES.value,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER.value,
    MagicAreasFeatures.BLE_TRACKER.value,
    MagicAreasFeatures.FAN_GROUPS.value,
    MagicAreasFeatures.HEALTH.value,
    MagicAreasFeatures.LIGHT_GROUPS.value,
    MagicAreasFeatures.PRESENCE_HOLD.value,
    MagicAreasFeatures.WASP_IN_A_BOX.value,
}
_LIGHT_GROUP_ROLE_KEYS = {
    key
    for preset in LIGHT_GROUP_PRESETS
    for key in (preset.category, preset.states_key, preset.act_on_key)
}
_FEATURE_SELECTION_ORDER = (
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.FAN_GROUPS,
    MagicAreasFeatures.COVER_GROUPS,
    MagicAreasFeatures.CLIMATE_CONTROL,
    MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
    MagicAreasFeatures.AGGREGATES,
    MagicAreasFeatures.HEALTH,
    MagicAreasFeatures.PRESENCE_HOLD,
    MagicAreasFeatures.BLE_TRACKER,
    MagicAreasFeatures.WASP_IN_A_BOX,
)


def _feature_section_step(feature: MagicAreasFeatures) -> str:
    """Return the parent section-menu step for a feature."""
    return f"feature_conf_{feature.value}"


def _fan_entities(flow: "OptionsFlowHandler") -> list[str]:
    """Return selectable fan entities."""
    return sorted(
        entity_id for entity_id in flow.all_entities if entity_id.startswith("fan.")
    )


def _fan_controller_defaults(role: str) -> dict[str, object]:
    """Return role-specific defaults for one fan controller page."""
    if role == FanControllerRole.HUMIDITY:
        return {
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
            ],
            CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.RUN_UNTIL_CLEAR.value,
            CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
                FanSensorUnavailableBehavior.HOLD_THEN_CLEAR.value
            ),
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 60.0,
            CONF_FAN_CONTROLLER_HYSTERESIS: 5.0,
        }
    if role == FanControllerRole.ODOR:
        return {
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
            ],
            CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.RUN_UNTIL_CLEAR.value,
            CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
                FanSensorUnavailableBehavior.CLEAR_REASON.value
            ),
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 0.0,
            CONF_FAN_CONTROLLER_HYSTERESIS: 0.0,
        }
    return {
        CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.EXTENDED.value],
        CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.OCCUPANCY_ONLY.value,
        CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
            FanSensorUnavailableBehavior.CLEAR_REASON.value
        ),
        CONF_FAN_CONTROLLER_ON_THRESHOLD: 0.0,
        CONF_FAN_CONTROLLER_HYSTERESIS: 0.0,
    }


def _fan_controller_config(
    feature_config: Mapping[str, object],
    role: str,
) -> dict[str, object]:
    """Return saved/default controller config for one role."""
    defaults = {
        CONF_FAN_CONTROLLER_MEMBERS: [],
        CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "",
        CONF_FAN_CONTROLLER_DETECTION_MODE: FanDetectionMode.THRESHOLD.value,
        CONF_FAN_CONTROLLER_SUPPRESS_STATES: [],
        CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS: 0,
        **_fan_controller_defaults(role),
    }
    raw_controllers = feature_config.get(CONF_FAN_GROUPS_CONTROLLERS)
    if isinstance(raw_controllers, Mapping):
        raw_role_config = raw_controllers.get(role)
        if isinstance(raw_role_config, Mapping):
            return {**defaults, **dict(raw_role_config)}

    if role == FanControllerRole.COOLING:
        required_state = feature_config.get(CONF_FAN_GROUPS_REQUIRED_STATE)
        if isinstance(required_state, str) and required_state:
            defaults[CONF_FAN_CONTROLLER_ACTIVE_STATES] = [required_state]
        setpoint = feature_config.get(CONF_FAN_GROUPS_SETPOINT)
        if isinstance(setpoint, int | float):
            defaults[CONF_FAN_CONTROLLER_ON_THRESHOLD] = float(setpoint)

    return defaults


def _fan_controller_schema(saved: Mapping[str, object]) -> vol.Schema:
    """Return schema for one fan controller role page."""
    area_state_options = [
        AreaStates.OCCUPIED.value,
        AreaStates.EXTENDED.value,
        AreaStates.DARK.value,
        AreaStates.BRIGHT.value,
        AreaStates.SLEEP.value,
        AreaStates.ACCENT.value,
    ]
    return vol.Schema(
        {
            vol.Optional(
                CONF_FAN_CONTROLLER_MEMBERS,
                default=saved.get(CONF_FAN_CONTROLLER_MEMBERS, []),
            ): cv.ensure_list,
            vol.Optional(
                CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
                default=saved.get(CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID, ""),
            ): cv.string,
            vol.Optional(
                CONF_FAN_CONTROLLER_DETECTION_MODE,
                default=saved.get(
                    CONF_FAN_CONTROLLER_DETECTION_MODE,
                    FanDetectionMode.THRESHOLD.value,
                ),
            ): vol.In(
                [
                    FanDetectionMode.THRESHOLD.value,
                    FanDetectionMode.THRESHOLD_TREND.value,
                    FanDetectionMode.ROOM_STATE.value,
                ]
            ),
            vol.Optional(
                CONF_FAN_CONTROLLER_ON_THRESHOLD,
                default=saved.get(CONF_FAN_CONTROLLER_ON_THRESHOLD, 0.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_FAN_CONTROLLER_HYSTERESIS,
                default=saved.get(CONF_FAN_CONTROLLER_HYSTERESIS, 0.0),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_FAN_CONTROLLER_ACTIVE_STATES,
                default=saved.get(CONF_FAN_CONTROLLER_ACTIVE_STATES, []),
            ): vol.All(cv.ensure_list, [vol.In(area_state_options)]),
            vol.Optional(
                CONF_FAN_CONTROLLER_SUPPRESS_STATES,
                default=saved.get(CONF_FAN_CONTROLLER_SUPPRESS_STATES, []),
            ): vol.All(cv.ensure_list, [vol.In(area_state_options)]),
            vol.Optional(
                CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
                default=saved.get(
                    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
                    FanClearBehavior.OCCUPANCY_ONLY.value,
                ),
            ): vol.In([behavior.value for behavior in FanClearBehavior]),
            vol.Optional(
                CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS,
                default=saved.get(CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS, 0),
            ): vol.Coerce(int),
            vol.Optional(
                CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
                default=saved.get(
                    CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
                    FanSensorUnavailableBehavior.CLEAR_REASON.value,
                ),
            ): vol.In([behavior.value for behavior in FanSensorUnavailableBehavior]),
        },
        extra=vol.REMOVE_EXTRA,
    )


def _fan_controller_selectors(flow: "OptionsFlowHandler") -> SelectorMap:
    """Return selectors for one fan controller role page."""
    area_state_options = [
        AreaStates.OCCUPIED.value,
        AreaStates.EXTENDED.value,
        AreaStates.DARK.value,
        AreaStates.BRIGHT.value,
        AreaStates.SLEEP.value,
        AreaStates.ACCENT.value,
    ]
    return {
        CONF_FAN_CONTROLLER_MEMBERS: build_selector_entity_simple(
            _fan_entities(flow), multiple=True
        ),
        CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: build_selector_entity_simple(
            flow.all_entities, multiple=False
        ),
        CONF_FAN_CONTROLLER_DETECTION_MODE: build_selector_select(
            options=[
                FanDetectionMode.THRESHOLD.value,
                FanDetectionMode.THRESHOLD_TREND.value,
                FanDetectionMode.ROOM_STATE.value,
            ],
            multiple=False,
            translation_key="fan_detection_mode",
        ),
        CONF_FAN_CONTROLLER_ON_THRESHOLD: build_selector_number(
            min_value=0,
            max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
            step=0.1,
            unit_of_measurement="",
        ),
        CONF_FAN_CONTROLLER_HYSTERESIS: build_selector_number(
            min_value=0,
            max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
            step=0.1,
            unit_of_measurement="",
        ),
        CONF_FAN_CONTROLLER_ACTIVE_STATES: build_selector_select(
            options=area_state_options,
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        ),
        CONF_FAN_CONTROLLER_SUPPRESS_STATES: build_selector_select(
            options=area_state_options,
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        ),
        CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: build_selector_select(
            options=[behavior.value for behavior in FanClearBehavior],
            multiple=False,
            translation_key="fan_clear_behavior",
        ),
        CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS: build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        ),
        CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: build_selector_select(
            options=[behavior.value for behavior in FanSensorUnavailableBehavior],
            multiple=False,
            translation_key="fan_sensor_unavailable_behavior",
        ),
    }


def _sync_legacy_fan_options_from_cooling(
    feature_config: dict[str, object],
    controller_config: Mapping[str, object],
) -> None:
    """Keep current runtime-compatible fan keys aligned with Cooling config."""
    active_states = controller_config.get(CONF_FAN_CONTROLLER_ACTIVE_STATES)
    if isinstance(active_states, list) and active_states:
        feature_config[CONF_FAN_GROUPS_REQUIRED_STATE] = str(active_states[0])
    feature_config[CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS] = feature_config.get(
        CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
        "temperature",
    )
    on_threshold = controller_config.get(CONF_FAN_CONTROLLER_ON_THRESHOLD)
    if isinstance(on_threshold, int | float):
        feature_config[CONF_FAN_GROUPS_SETPOINT] = float(on_threshold)


def _normalize_fan_controller_validated(
    validated: Mapping[str, object],
) -> dict[str, object]:
    """Normalize controller form values into JSON-friendly primitive values."""
    normalized = dict(validated)
    for key in (
        CONF_FAN_CONTROLLER_MEMBERS,
        CONF_FAN_CONTROLLER_ACTIVE_STATES,
        CONF_FAN_CONTROLLER_SUPPRESS_STATES,
    ):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
    for key in (
        CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
        CONF_FAN_CONTROLLER_DETECTION_MODE,
        CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
        CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
    ):
        value = normalized.get(key)
        if value is not None:
            normalized[key] = str(value)
    return normalized


async def _handle_fan_controller_form(
    flow: "OptionsFlowHandler",
    *,
    step_id: str,
    user_input: Mapping[str, object] | None,
) -> config_entries.ConfigFlowResult:
    """Handle one fan controller role config page."""
    role = _FAN_GROUP_STEP_ROLE[step_id]
    feature_config = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.FAN_GROUPS.value, {}
    )
    if not isinstance(feature_config, Mapping):
        feature_config = {}
    saved = _fan_controller_config(feature_config, role)
    schema = _fan_controller_schema(saved)

    if user_input is not None:
        try:
            validated = dict(schema(dict(user_input)))
        except vol.MultipleInvalid:
            error_values = {**saved, **dict(user_input)}
            return flow.async_show_form(
                step_id=step_id,
                data_schema=flow._build_schema_from_vol(
                    schema,
                    saved_options=error_values,
                    selectors=_fan_controller_selectors(flow),
                ),
                errors=invalid_input_error(),
            )
        validated = _normalize_fan_controller_validated(validated)

        features = ensure_enabled_feature_map(flow.area_options)
        mutable_config = features.setdefault(MagicAreasFeatures.FAN_GROUPS.value, {})
        if not isinstance(mutable_config, dict):
            mutable_config = {}
            features[MagicAreasFeatures.FAN_GROUPS.value] = mutable_config
        controllers = mutable_config.setdefault(CONF_FAN_GROUPS_CONTROLLERS, {})
        if not isinstance(controllers, dict):
            controllers = {}
            mutable_config[CONF_FAN_GROUPS_CONTROLLERS] = controllers
        controllers[role] = validated
        if role == FanControllerRole.COOLING:
            _sync_legacy_fan_options_from_cooling(mutable_config, validated)

        await flow._persist_options()
        flow._feature_step_id = _FAN_GROUP_MENU_STEP
        return await handle_feature_conf(flow)

    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=saved,
            selectors=_fan_controller_selectors(flow),
        ),
    )


async def _handle_fan_feature_route(
    flow: "OptionsFlowHandler",
    *,
    step_id: str,
    user_input: Mapping[str, object] | None,
) -> config_entries.ConfigFlowResult | None:
    """Handle fan feature menu and controller-role pages."""
    if step_id == _FAN_GROUP_MENU_STEP:
        # noinspection PyTypeChecker
        return flow.async_show_menu(
            step_id=_FAN_GROUP_MENU_STEP,
            menu_options=[
                _FAN_GROUP_COOLING_STEP,
                _FAN_GROUP_HUMIDITY_STEP,
                _FAN_GROUP_ODOR_STEP,
                "show_menu",
            ],
        )
    if step_id in _FAN_GROUP_SUBSTEPS:
        return await _handle_fan_controller_form(
            flow,
            step_id=step_id,
            user_input=user_input,
        )
    return None


def get_feature_list(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
    """Return list of available features for area type."""
    available = FEATURE_REGISTRY.available_features_for_area(area_config)
    ordered = [feature for feature in _FEATURE_SELECTION_ORDER if feature in available]
    ordered.extend(feature for feature in available if feature not in ordered)
    return ordered


def get_configurable_features(
    area_config: "AreaConfig | None",
) -> list[MagicAreasFeatures]:
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

        return await flow._persist_options_and_show_menu()

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
            validated_dict = dict(validated)
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS:
                existing = features.get(feature_key, {})
                if isinstance(existing, Mapping):
                    for key in _LIGHT_GROUP_PRESERVED_HIDDEN_KEYS:
                        if key in existing and key not in user_input:
                            validated_dict[key] = existing[key]
                if isinstance(existing, dict) and isinstance(
                    validated_dict.get(CONF_LIGHT_GROUP_BRIGHTNESS_MODE),
                    str,
                ):
                    prune_light_group_options_for_brightness_mode(
                        existing=existing,
                        mode=validated_dict[CONF_LIGHT_GROUP_BRIGHTNESS_MODE],
                    )
                elif isinstance(existing, dict) and step_id in {
                    _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
                    _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
                }:
                    prune_light_group_options_for_brightness_mode(
                        existing=existing,
                        mode=(
                            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
                            if step_id == _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP
                            else LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
                        ),
                    )
                normalize_light_group_adaptive_lighting_options(
                    flow,
                    validated_dict,
                )
            if merge_options:
                features.setdefault(feature_key, {}).update(validated_dict)
            else:
                features[feature_key] = validated_dict

            if should_rerender_light_group_adaptive_lighting_step(
                step_id=step_id,
                user_input=user_input,
                validated=validated_dict,
            ):
                return await handle_feature_conf(flow)
            if should_rerender_light_group_brightness_step(
                step_id=step_id,
                user_input=user_input,
                validated=validated_dict,
            ):
                return await handle_feature_conf(flow)

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


async def handle_feature_conf(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Configure a specific feature using registry-based approach."""
    step_id = flow._feature_step_id or str(flow.context.get("step_id", ""))
    light_menu_result = handle_light_group_menu_route(flow, step_id=step_id)
    if light_menu_result is not None:
        return light_menu_result
    fan_result = await _handle_fan_feature_route(
        flow,
        step_id=step_id,
        user_input=user_input,
    )
    if fan_result is not None:
        return fan_result
    if step_id == _LIGHT_GROUP_BRIGHTNESS_STEP and user_input is not None:
        mode_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
                    default=LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                ): vol.In(
                    [
                        LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                        LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
                        LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
                    ]
                )
            },
            extra=vol.REMOVE_EXTRA,
        )
        errors: dict[str, str] = {}
        try:
            validated_mode = mode_schema(dict(user_input))
        except vol.MultipleInvalid:
            errors = invalid_input_error()
        else:
            features = ensure_enabled_feature_map(flow.area_options)
            feature_cfg = features.setdefault(MagicAreasFeatures.LIGHT_GROUPS.value, {})
            if not isinstance(feature_cfg, dict):
                feature_cfg = {}
                features[MagicAreasFeatures.LIGHT_GROUPS.value] = feature_cfg
            selected_mode = str(
                validated_mode.get(
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
                    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                )
            )
            feature_cfg[CONF_LIGHT_GROUP_BRIGHTNESS_MODE] = selected_mode
            prune_light_group_options_for_brightness_mode(
                existing=feature_cfg,
                mode=selected_mode,
            )
            if selected_mode == LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT:
                await flow._persist_options()
                flow._feature_step_id = _LIGHT_GROUP_MENU_STEP
                return await handle_feature_conf(flow)
            flow._feature_step_id = (
                _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP
                if selected_mode == LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
                else _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP
            )
            return await handle_feature_conf(flow)
        return flow.async_show_form(
            step_id=_LIGHT_GROUP_BRIGHTNESS_STEP,
            data_schema=flow._build_schema_from_vol(
                mode_schema,
                saved_options=enabled_feature_map(flow.area_options).get(
                    MagicAreasFeatures.LIGHT_GROUPS.value, {}
                ),
                selectors={
                    CONF_LIGHT_GROUP_BRIGHTNESS_MODE: build_selector_select(
                        options=[
                            LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
                            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
                        ],
                        multiple=False,
                        translation_key="light_brightness_mode",
                    )
                },
            ),
            errors=errors,
        )

    if (
        step_id.startswith("feature_conf_")
        and step_id not in _LIGHT_GROUP_SUBSTEPS
        and not step_id.endswith(_FEATURE_SETTINGS_STEP_SUFFIX)
        and step_id != "feature_conf_climate_control_select_presets"
    ):
        section_feature_key = step_id.replace("feature_conf_", "")
        try:
            section_feature_enum = MagicAreasFeatures(section_feature_key)
        except ValueError:
            section_feature_enum = None

        if (
            section_feature_enum is not None
            and section_feature_key not in _FEATURE_MENU_EXCLUSIONS
        ):
            settings_step_id = f"{step_id}{_FEATURE_SETTINGS_STEP_SUFFIX}"
            if user_input is None:
                menu_options: list[str] = [settings_step_id]
                if section_feature_key == MagicAreasFeatures.CLIMATE_CONTROL.value:
                    menu_options.append("feature_conf_climate_control_select_presets")
                menu_options.append("show_menu")
                # noinspection PyTypeChecker
                return flow.async_show_menu(
                    step_id=step_id,
                    menu_options=menu_options,
                )
            step_id = settings_step_id

    if step_id in _LIGHT_GROUP_SUBSTEPS:
        feature_key = MagicAreasFeatures.LIGHT_GROUPS.value
    elif step_id.endswith(_FEATURE_SETTINGS_STEP_SUFFIX):
        feature_key = step_id.removeprefix("feature_conf_").removesuffix(
            _FEATURE_SETTINGS_STEP_SUFFIX
        )
    else:
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
    schema = copy_schema(schema)

    selectors: SelectorMap = {}

    if feature_enum == MagicAreasFeatures.LIGHT_GROUPS:
        mode = resolve_light_groups_mode(flow, user_input)
        adaptive_lighting_mode = resolve_adaptive_lighting_mode(flow, user_input)
        include_keys = light_group_step_include_keys(
            step_id=step_id,
            mode=mode,
            adaptive_lighting_mode=adaptive_lighting_mode,
        )
        feature_config = enabled_feature_map(flow.area_options).get(
            MagicAreasFeatures.LIGHT_GROUPS.value, {}
        )
        if not isinstance(feature_config, Mapping):
            feature_config = {}
        if (
            step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP
            and adaptive_lighting_mode
            == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
        ):
            candidates = adaptive_lighting_candidate_switch_sets(flow, feature_config)
            candidate_options = ["", *candidates]
            for category in light_group_pairing_categories(flow, feature_config):
                pair_key = adaptive_lighting_pair_key(category)
                selected = adaptive_lighting_pair_value(feature_config, category)
                options = list(candidate_options)
                if selected and selected not in options:
                    options.append(selected)
                include_keys.add(pair_key)
                schema.schema[vol.Optional(pair_key, default=selected)] = vol.In(
                    options
                )
                selectors[pair_key] = build_selector_select(
                    options=options,
                    multiple=False,
                    translation_key="adaptive_lighting_switch_set",
                )
        if (
            step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP
            and adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ):
            role_options = light_group_managed_role_options(flow, feature_config)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
            remove_schema_key(schema, CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            remove_schema_key(
                schema,
                CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
            )
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
                    default=light_group_manage_all_lights_default(feature_config),
                )
            ] = cv.boolean
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
                    default=light_group_managed_roles_default(
                        role_options=role_options,
                        feature_config=feature_config,
                    ),
                )
            ] = vol.All(cv.ensure_list, [vol.In(role_options)])
            selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] = (
                build_selector_select(
                    options=role_options,
                    multiple=True,
                    translation_key="adaptive_lighting_managed_roles",
                )
            )
            selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] = (
                build_selector_boolean()
            )
        schema = filter_schema_for_keys(schema, include_keys)

        add_light_group_brightness_selectors(
            flow=flow,
            step_id=step_id,
            selectors=selectors,
        )
        if step_id in {
            _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
            _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
        }:
            remove_schema_key(schema, CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY)
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
                    default=default_inside_bright_entity(
                        flow=flow,
                        feature_config=feature_config,
                    ),
                )
            ] = cv.string
        add_light_group_adaptive_lighting_selectors(
            step_id=step_id,
            selectors=selectors,
        )
        add_light_group_role_selectors(
            step_id=step_id,
            flow=flow,
            selectors=selectors,
        )

    add_non_light_feature_selectors(
        flow=flow,
        feature_enum=feature_enum,
        selectors=selectors,
    )

    return await handle_feature_form(
        flow=flow,
        feature_enum=feature_enum,
        step_id=step_id,
        schema=schema,
        user_input=user_input,
        merge_options=(
            True
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else feature.merge_options
        ),
        next_step=(
            _LIGHT_GROUP_MENU_STEP
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else (
                feature.next_step
                or (
                    _feature_section_step(feature_enum)
                    if step_id.endswith(_FEATURE_SETTINGS_STEP_SUFFIX)
                    else None
                )
            )
        ),
        selectors=selectors,
    )
