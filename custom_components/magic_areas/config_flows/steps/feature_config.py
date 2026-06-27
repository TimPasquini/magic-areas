"""Feature selection and configuration step handlers for options flow."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.base import (
    SelectorMap,
    enabled_feature_map,
    ensure_enabled_feature_map,
    get_feature_config_steps,
    invalid_input_error,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.generic import (
    copy_schema,
    handle_feature_form,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.fan_groups import (
    handle_fan_feature_route,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.light_groups import (
    LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP as _LIGHT_GROUP_BRIGHTNESS_ADAPTIVE_STEP,
    LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP as _LIGHT_GROUP_BRIGHTNESS_ADVISORY_STEP,
    LIGHT_GROUP_BRIGHTNESS_STEP as _LIGHT_GROUP_BRIGHTNESS_STEP,
    LIGHT_GROUP_MENU_STEP as _LIGHT_GROUP_MENU_STEP,
    LIGHT_GROUP_SUBSTEPS as _LIGHT_GROUP_SUBSTEPS,
    build_light_group_schema_and_selectors,
    handle_light_group_menu_route,
    prepare_light_group_validated,
    prune_light_group_options_for_brightness_mode,
    should_rerender_light_group_form,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.simple import (
    add_non_light_feature_selectors,
)
from custom_components.magic_areas.enums import (
    MagicAreasFeatures,
)
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
from custom_components.magic_areas.light_groups import (
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_select,
)
from custom_components.magic_areas.schemas import CONFIGURABLE_FEATURES

if TYPE_CHECKING:
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.config_flows.options_flow import (
        OptionsFlowHandler,
    )

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


async def handle_feature_conf(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Configure a specific feature using registry-based approach."""
    step_id = flow._feature_step_id or str(flow.context.get("step_id", ""))
    light_menu_result = handle_light_group_menu_route(flow, step_id=step_id)
    if light_menu_result is not None:
        return light_menu_result
    fan_result = await handle_fan_feature_route(
        flow,
        step_id=step_id,
        user_input=user_input,
        show_feature_conf=handle_feature_conf,
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
        schema, selectors = build_light_group_schema_and_selectors(
            flow=flow,
            step_id=step_id,
            schema=schema,
            user_input=user_input,
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
        prepare_validated=(
            prepare_light_group_validated
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else None
        ),
        should_rerender=(
            should_rerender_light_group_form
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else None
        ),
        rerender_handler=(
            handle_feature_conf
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else None
        ),
    )
