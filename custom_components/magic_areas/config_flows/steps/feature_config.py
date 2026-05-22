"""Feature selection and configuration step handlers for options flow."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
)
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    AdaptiveLightingSwitchSet,
    switch_set_from_explicit_refs,
    switch_sets_from_hass_registry,
)
from custom_components.magic_areas.config_flows.base import (
    ConfigSubMap,
    SelectorMap,
    enabled_feature_map,
    ensure_enabled_feature_map,
    get_feature_config_steps,
    invalid_input_error,
)
from custom_components.magic_areas.enums import MagicAreasFeatures, SelectorTranslationKeys
from custom_components.magic_areas.features.config.readers import (
    AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS,
    BLE_TRACKER_OPTION_KEYS,
    CLIMATE_CONTROL_ENTITY_KEY,
    CLIMATE_CONTROL_PRESET_OPTION_KEYS,
    AGGREGATES_OPTION_KEYS,
    HEALTH_OPTION_KEYS,
    WASP_IN_A_BOX_OPTION_KEYS,
)
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
from custom_components.magic_areas.light_groups import (
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX,
    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_PRESETS,
    adaptive_lighting_pair_key,
)
from custom_components.magic_areas.policy import (
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    ALL_SENSOR_DEVICE_CLASSES,
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
    build_climate_preset_selectors_and_validators,
    build_selector_entity_simple,
    build_selector_boolean,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.schemas import CONFIGURABLE_FEATURES
from custom_components.magic_areas.schemas import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)
from custom_components.magic_areas.enums import LightGroupCategory

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

_LIGHT_GROUP_ALWAYS_KEYS = {
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
}
_LIGHT_GROUP_ADVISORY_KEYS = {
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
}
_LIGHT_GROUP_ADAPTIVE_ONLY_KEYS = {
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
}
_LIGHT_GROUP_PRESERVED_HIDDEN_KEYS = {
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
}
_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX = (
    LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_KEY_PREFIX
)
_LIGHT_GROUP_LUX_SELECTOR_MAX = 120_000
_LIGHT_GROUP_MENU_STEP = "feature_conf_light_groups"
_LIGHT_GROUP_ROLES_STEP = "feature_conf_light_groups_roles"
_LIGHT_GROUP_BRIGHTNESS_STEP = "feature_conf_light_groups_brightness"
_LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP = "feature_conf_light_groups_adaptive_lighting"
_LIGHT_GROUP_SUBSTEPS = {
    _LIGHT_GROUP_MENU_STEP,
    _LIGHT_GROUP_ROLES_STEP,
    _LIGHT_GROUP_BRIGHTNESS_STEP,
    _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
}
_LIGHT_GROUP_ROLE_KEYS = {
    key
    for preset in LIGHT_GROUP_PRESETS
    for key in (preset.category, preset.states_key, preset.act_on_key)
}


def _copy_schema(schema: vol.Schema) -> vol.Schema:
    """Return a shallow copy so dynamic flow fields do not mutate registry schemas."""
    raw_schema = schema.schema
    if not isinstance(raw_schema, dict):
        return schema
    return vol.Schema(dict(raw_schema), extra=schema.extra)


def _resolve_light_groups_mode(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None
) -> str:
    """Resolve current light-groups mode from input or saved options."""
    if user_input is not None:
        raw = user_input.get(CONF_LIGHT_GROUP_BRIGHTNESS_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
        }:
            return raw

    saved = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.LIGHT_GROUPS.value, {}
    )
    if isinstance(saved, dict):
        raw = saved.get(CONF_LIGHT_GROUP_BRIGHTNESS_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
        }:
            return raw
    return LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT


def _filter_schema_for_keys(schema: vol.Schema, include_keys: set[str]) -> vol.Schema:
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


def _light_group_step_include_keys(
    *,
    step_id: str,
    mode: str,
    adaptive_lighting_mode: str,
) -> set[str]:
    """Return light-group config keys rendered on one light-group substep."""
    if step_id == _LIGHT_GROUP_ROLES_STEP:
        return set(_LIGHT_GROUP_ROLE_KEYS)

    if step_id == _LIGHT_GROUP_BRIGHTNESS_STEP:
        include_keys = {CONF_LIGHT_GROUP_BRIGHTNESS_MODE}
        if mode in {
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
        }:
            include_keys.update(_LIGHT_GROUP_ADVISORY_KEYS)
        if mode == LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE:
            include_keys.update(_LIGHT_GROUP_ADAPTIVE_ONLY_KEYS)
        return include_keys

    if step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
        include_keys = {CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE}
        if adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE:
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
        return include_keys

    return set()


def _resolve_adaptive_lighting_mode(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None
) -> str:
    """Resolve current Adaptive Lighting mode from input or saved options."""
    if user_input is not None:
        raw = user_input.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
        }:
            return raw

    saved = enabled_feature_map(flow.area_options).get(
        MagicAreasFeatures.LIGHT_GROUPS.value, {}
    )
    if isinstance(saved, dict):
        raw = saved.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
        if isinstance(raw, str) and raw in {
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
        }:
            return raw
    return LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE


def _light_group_pairing_categories(
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> tuple[str, ...]:
    """Return light roles that currently have a native group/pairing surface."""
    categories: list[str] = []
    if flow.all_lights:
        categories.append(str(LightGroupCategory.ALL))

    for preset in LIGHT_GROUP_PRESETS:
        raw_members = feature_config.get(preset.category, [])
        if isinstance(raw_members, list) and raw_members:
            categories.append(preset.category)

    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if isinstance(raw_switch_sets, Mapping):
        for category in raw_switch_sets:
            if isinstance(category, str) and category not in categories:
                categories.append(category)

    return tuple(categories)


def _configured_adaptive_lighting_switch_sets(
    area_id: str,
    feature_config: Mapping[str, object],
) -> dict[str, AdaptiveLightingSwitchSet]:
    """Return existing explicit switch-set config by light role."""
    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if not isinstance(raw_switch_sets, Mapping):
        return {}

    switch_sets: dict[str, AdaptiveLightingSwitchSet] = {}
    for category, raw_switch_refs in raw_switch_sets.items():
        if not isinstance(category, str) or not isinstance(raw_switch_refs, Mapping):
            continue
        switch_refs = {
            str(key): str(value)
            for key, value in raw_switch_refs.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        switch_set = switch_set_from_explicit_refs(
            area_id=area_id,
            role=category,
            switch_refs=switch_refs,
        )
        if switch_set is not None:
            switch_sets[category] = switch_set
    return switch_sets


def _light_group_managed_role_options(
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> list[str]:
    """Return role options that can receive MA-managed Adaptive Lighting configs."""
    options = [
        category
        for category in _light_group_pairing_categories(flow, feature_config)
        if category != str(LightGroupCategory.ALL)
    ]
    raw_roles = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
    if isinstance(raw_roles, list):
        for role in raw_roles:
            if (
                isinstance(role, str)
                and role != str(LightGroupCategory.ALL)
                and role not in options
            ):
                options.append(role)
    return options


def _light_group_manage_all_lights_default(
    feature_config: Mapping[str, object],
) -> bool:
    """Return saved room-level manage preference."""
    raw_value = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
    try:
        return bool(cv.boolean(raw_value))
    except vol.Invalid:
        return False


def _adaptive_lighting_candidate_switch_sets(
    flow: "OptionsFlowHandler",
    feature_config: Mapping[str, object],
) -> dict[str, AdaptiveLightingSwitchSet]:
    """Return selectable AL switch sets keyed by main switch entity ID."""
    area_config = flow._area_config
    if area_config is None:
        return {}

    candidates = {
        switch_set.main_switch_entity_id: switch_set
        for switch_set in switch_sets_from_hass_registry(
            flow.hass,
            area_id=area_config.id,
        )
    }
    for switch_set in _configured_adaptive_lighting_switch_sets(
        area_config.id,
        feature_config,
    ).values():
        candidates.setdefault(switch_set.main_switch_entity_id, switch_set)
    return dict(sorted(candidates.items()))


def _adaptive_lighting_pair_value(
    feature_config: Mapping[str, object],
    category: str,
) -> str:
    """Return currently selected AL main switch for one light role."""
    raw_switch_sets = feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS)
    if not isinstance(raw_switch_sets, Mapping):
        return ""
    raw_switch_refs = raw_switch_sets.get(category)
    if not isinstance(raw_switch_refs, Mapping):
        return ""
    main_switch = raw_switch_refs.get(MAIN_SWITCH)
    return main_switch if isinstance(main_switch, str) else ""


def _adaptive_lighting_switch_set_refs(
    switch_set: AdaptiveLightingSwitchSet,
) -> dict[str, str]:
    """Return persisted explicit switch refs for one AL switch set."""
    return {
        MAIN_SWITCH: switch_set.main_switch_entity_id,
        SLEEP_SWITCH: switch_set.sleep_switch_entity_id,
        ADAPT_BRIGHTNESS_SWITCH: switch_set.adapt_brightness_switch_entity_id,
        ADAPT_COLOR_SWITCH: switch_set.adapt_color_switch_entity_id,
    }


def _normalize_light_group_adaptive_lighting_options(
    flow: "OptionsFlowHandler",
    feature_config: dict[str, object],
) -> None:
    """Translate transient AL pairing dropdowns into explicit switch-set config."""
    area_config = flow._area_config
    if area_config is None:
        return

    if (
        feature_config.get(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE)
        != LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
    ):
        for key in tuple(feature_config):
            if key.startswith(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX):
                feature_config.pop(key, None)
        return

    candidates = _adaptive_lighting_candidate_switch_sets(flow, feature_config)
    categories = set(_light_group_pairing_categories(flow, feature_config))
    for key in feature_config:
        if key.startswith(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX):
            categories.add(key.removeprefix(_LIGHT_GROUP_ADAPTIVE_LIGHTING_PAIR_PREFIX))

    switch_sets: dict[str, dict[str, str]] = {}
    for category in sorted(categories):
        pair_key = adaptive_lighting_pair_key(category)
        selected = feature_config.pop(pair_key, "")
        if not isinstance(selected, str) or not selected:
            continue
        switch_set = candidates.get(selected)
        if switch_set is None:
            continue
        switch_sets[category] = _adaptive_lighting_switch_set_refs(switch_set)

    feature_config[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS] = switch_sets


def get_feature_list(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
    """Return list of available features for area type."""
    return FEATURE_REGISTRY.available_features_for_area(area_config)


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
            validated_dict = dict(validated)
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS:
                existing = features.get(feature_key, {})
                if isinstance(existing, Mapping):
                    for key in _LIGHT_GROUP_PRESERVED_HIDDEN_KEYS:
                        if key in existing and key not in user_input:
                            validated_dict[key] = existing[key]
                _normalize_light_group_adaptive_lighting_options(
                    flow,
                    validated_dict,
                )
            if merge_options:
                features.setdefault(feature_key, {}).update(validated_dict)
            else:
                features[feature_key] = validated_dict

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
    if step_id == _LIGHT_GROUP_MENU_STEP:
        # noinspection PyTypeChecker
        return flow.async_show_menu(
            step_id=_LIGHT_GROUP_MENU_STEP,
            menu_options=[
                _LIGHT_GROUP_ROLES_STEP,
                _LIGHT_GROUP_BRIGHTNESS_STEP,
                _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP,
                "show_menu",
            ],
        )

    if step_id in _LIGHT_GROUP_SUBSTEPS:
        feature_key = MagicAreasFeatures.LIGHT_GROUPS.value
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
    schema = _copy_schema(schema)

    selectors: SelectorMap = {}

    if feature_enum == MagicAreasFeatures.AGGREGATES:
        selectors.update(
            {
                CONF_AGGREGATES_MIN_ENTITIES: build_selector_number(
                    min_value=1, unit_of_measurement=""
                ),
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: build_selector_number(
                    min_value=0, unit_of_measurement="lx"
                ),
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS: (
                    build_selector_number(min_value=0, unit_of_measurement="%")
                ),
                AGGREGATES_OPTION_KEYS[3]: build_selector_select(
                    sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
                ),
                AGGREGATES_OPTION_KEYS[4]: build_selector_select(
                    sorted(ALL_SENSOR_DEVICE_CLASSES), multiple=True
                ),
            }
        )

    if feature_enum == MagicAreasFeatures.LIGHT_GROUPS:
        mode = _resolve_light_groups_mode(flow, user_input)
        adaptive_lighting_mode = _resolve_adaptive_lighting_mode(flow, user_input)
        include_keys = _light_group_step_include_keys(
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
            and adaptive_lighting_mode == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
        ):
            candidates = _adaptive_lighting_candidate_switch_sets(flow, feature_config)
            candidate_options = ["", *candidates]
            for category in _light_group_pairing_categories(flow, feature_config):
                pair_key = adaptive_lighting_pair_key(category)
                selected = _adaptive_lighting_pair_value(feature_config, category)
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
            role_options = _light_group_managed_role_options(flow, feature_config)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL)
            include_keys.add(CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES)
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
                    default=_light_group_manage_all_lights_default(feature_config),
                )
            ] = cv.boolean
            schema.schema[
                vol.Optional(
                    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
                    default=feature_config.get(
                        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
                        [],
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
        schema = _filter_schema_for_keys(schema, include_keys)

        if step_id == _LIGHT_GROUP_BRIGHTNESS_STEP:
            selectors[CONF_LIGHT_GROUP_BRIGHTNESS_MODE] = build_selector_select(
                options=[
                    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
                    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
                    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
                ],
                multiple=False,
                translation_key="light_brightness_mode",
            )
        if step_id == _LIGHT_GROUP_ADAPTIVE_LIGHTING_STEP:
            selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE] = build_selector_select(
                options=[
                    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
                    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
                    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
                ],
                multiple=False,
                translation_key="adaptive_lighting_mode",
            )
        if mode in {
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
        } and step_id == _LIGHT_GROUP_BRIGHTNESS_STEP:
            selectors[CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY] = (
                build_selector_entity_simple(flow.all_binary_entities, multiple=False)
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY] = (
                build_selector_entity_simple(flow.all_binary_entities, multiple=False)
            )
        if (
            mode == LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
            and step_id == _LIGHT_GROUP_BRIGHTNESS_STEP
        ):
            selectors[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] = build_selector_number(
                min_value=0, unit_of_measurement="s"
            )
            selectors[CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS] = build_selector_number(
                min_value=0, unit_of_measurement="s"
            )
            selectors[CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS] = (
                build_selector_number(min_value=0, unit_of_measurement="s")
            )
            selectors[CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE] = (
                build_selector_boolean()
            )
            selectors[CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS] = (
                build_selector_number(min_value=0, unit_of_measurement="s")
            )
            selectors[CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA] = build_selector_number(
                min_value=0,
                max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
                unit_of_measurement="lx",
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE] = build_selector_select(
                options=[
                    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_SUN,
                    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_OUTSIDE_LUX,
                    LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE_NONE,
                ],
                multiple=False,
                translation_key="light_outside_context_source",
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY] = (
                build_selector_entity_simple(
                    flow.all_illuminance_entities, multiple=False
                )
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] = build_selector_number(
                min_value=0,
                max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
                unit_of_measurement="lx",
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY] = (
                build_selector_entity_simple(
                    flow.all_illuminance_entities, multiple=False
                )
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA] = (
                build_selector_number(
                    min_value=0,
                    max_value=_LIGHT_GROUP_LUX_SELECTOR_MAX,
                    unit_of_measurement="lx",
                )
            )
            selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT] = (
                build_selector_number(min_value=0, unit_of_measurement="%")
            )
        if step_id == _LIGHT_GROUP_ROLES_STEP:
            for preset in LIGHT_GROUP_PRESETS:
                selectors[preset.category] = build_selector_entity_simple(
                    flow.all_lights, multiple=True
                )
                selectors[preset.states_key] = build_selector_select(
                    options=[
                        AreaStates.OCCUPIED.value,
                        AreaStates.EXTENDED.value,
                        AreaStates.SLEEP.value,
                        AreaStates.ACCENT.value,
                    ],
                    multiple=True,
                    translation_key=SelectorTranslationKeys.AREA_STATES,
                )
                selectors[preset.act_on_key] = build_selector_select(
                    options=[
                        LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                        LIGHT_GROUP_ACT_ON_STATE_CHANGE,
                    ],
                    multiple=True,
                    translation_key=SelectorTranslationKeys.CONTROL_ON,
                )

    if feature_enum == MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER:
        selectors[AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[0]] = (
            build_selector_entity_simple(flow.all_media_players, multiple=True)
        )
        selectors[AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[1]] = build_selector_select(
            options=[
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
                AreaStates.SLEEP.value,
            ],
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        )

    if feature_enum == MagicAreasFeatures.BLE_TRACKER:
        selectors[BLE_TRACKER_OPTION_KEYS[0]] = build_selector_entity_simple(
            flow.all_entities, multiple=True
        )

    if feature_enum == MagicAreasFeatures.HEALTH:
        selectors[HEALTH_OPTION_KEYS[0]] = build_selector_select(
            options=sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES),
            multiple=True,
        )

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
        merge_options=(
            True
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else feature.merge_options
        ),
        next_step=(
            _LIGHT_GROUP_MENU_STEP
            if feature_enum == MagicAreasFeatures.LIGHT_GROUPS
            else feature.next_step
        ),
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
