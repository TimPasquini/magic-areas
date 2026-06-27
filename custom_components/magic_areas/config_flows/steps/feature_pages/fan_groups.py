"""Fan-group feature page routing for options flow."""

from __future__ import annotations

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
)
from custom_components.magic_areas.config_flows.base import (
    SelectorMap,
    enabled_feature_map,
    ensure_enabled_feature_map,
    invalid_input_error,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_entity_simple,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanClearBehavior,
    FanControllerRole,
    FanDetectionMode,
    FanSensorUnavailableBehavior,
)
from custom_components.magic_areas.enums import (
    MagicAreasFeatures,
    SelectorTranslationKeys,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import (
        OptionsFlowHandler,
    )

_NUMERIC_SELECTOR_MAX = 120_000
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

type FeatureConfHandler = Callable[
    ["OptionsFlowHandler"], Awaitable[config_entries.ConfigFlowResult]
]


def _fan_entities(flow: OptionsFlowHandler) -> list[str]:
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


def _fan_controller_selectors(flow: OptionsFlowHandler) -> SelectorMap:
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
            max_value=_NUMERIC_SELECTOR_MAX,
            step=0.1,
            unit_of_measurement="",
        ),
        CONF_FAN_CONTROLLER_HYSTERESIS: build_selector_number(
            min_value=0,
            max_value=_NUMERIC_SELECTOR_MAX,
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
    flow: OptionsFlowHandler,
    *,
    step_id: str,
    user_input: Mapping[str, object] | None,
    show_feature_conf: FeatureConfHandler,
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
        return await show_feature_conf(flow)

    return flow.async_show_form(
        step_id=step_id,
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=saved,
            selectors=_fan_controller_selectors(flow),
        ),
    )


async def handle_fan_feature_route(
    flow: OptionsFlowHandler,
    *,
    step_id: str,
    user_input: Mapping[str, object] | None,
    show_feature_conf: FeatureConfHandler,
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
            show_feature_conf=show_feature_conf,
        )
    return None
