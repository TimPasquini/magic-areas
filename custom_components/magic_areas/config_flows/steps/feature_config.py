"""Feature selection and configuration step handlers for options flow."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
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
from custom_components.magic_areas.config_flows.steps.feature_pages.fan_groups import (
    handle_fan_feature_route,
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
    adaptive_lighting_pair_key,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_boolean,
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
