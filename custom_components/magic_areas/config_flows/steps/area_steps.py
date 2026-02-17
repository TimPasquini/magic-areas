"""Area configuration step handlers for options flow.

Handles basic area settings, presence tracking configuration, and secondary states.
"""

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.area_maps import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
)
from custom_components.magic_areas.config_flows.helpers import (
    handle_step_validation,
)
from custom_components.magic_areas.config_keys import (
    ALL_PRESENCE_DEVICE_PLATFORMS,
    CONF_EXCLUDE_ENTITIES,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    CONF_SECONDARY_STATES,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_TIMEOUT,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_CLEAR_TIMEOUT,
    CONF_TYPE,
    CalculationMode,
)
from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.enums import SelectorTranslationKeys
from custom_components.magic_areas.policy import ALL_BINARY_SENSOR_DEVICE_CLASSES
from custom_components.magic_areas.schemas.area import (
    META_AREA_BASIC_OPTIONS_SCHEMA,
    META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    META_AREA_SECONDARY_STATES_SCHEMA,
    REGULAR_AREA_BASIC_OPTIONS_SCHEMA,
    REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    SECONDARY_STATES_SCHEMA,
)
from custom_components.magic_areas.schemas.selectors import (
    build_selector_boolean,
    build_selector_entity_simple,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.schemas.validation import (
    OPTIONS_AREA,
    OPTIONS_AREA_META,
    OPTIONS_PRESENCE_TRACKING,
    OPTIONS_PRESENCE_TRACKING_META,
    OPTIONS_SECONDARY_STATES,
    OPTIONS_SECONDARY_STATES_META,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler

EMPTY_ENTRY = [""]


async def handle_area_config(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle area configuration step."""
    options_schema = (
        META_AREA_BASIC_OPTIONS_SCHEMA
        if (flow._area_config and flow._area_config.is_meta())
        else REGULAR_AREA_BASIC_OPTIONS_SCHEMA
    )

    errors, validated = await handle_step_validation(
        user_input=user_input,
        schema=options_schema,
        area_name=flow._area_config.name if flow._area_config else "Unknown",
        step_name="area_config",
        area_options=flow.area_options,
        on_success=flow.async_step_show_menu,
    )

    if validated:
        return await flow.async_step_show_menu()

    all_selectors = {
        CONF_TYPE: build_selector_select(
            sorted([AreaType.INTERIOR, AreaType.EXTERIOR]),
            translation_key=SelectorTranslationKeys.AREA_TYPE,
        ),
        CONF_INCLUDE_ENTITIES: build_selector_entity_simple(
            flow.all_entities, multiple=True
        ),
        CONF_EXCLUDE_ENTITIES: build_selector_entity_simple(
            flow.all_area_entities, multiple=True
        ),
        CONF_RELOAD_ON_REGISTRY_CHANGE: build_selector_boolean(),  # type: ignore[no-untyped-call]
        CONF_IGNORE_DIAGNOSTIC_ENTITIES: build_selector_boolean(),  # type: ignore[no-untyped-call]
    }

    options = (
        OPTIONS_AREA_META if (flow._area_config and flow._area_config.is_meta())
        else OPTIONS_AREA
    )

    selectors = {opt[0]: all_selectors[opt[0]] for opt in options}

    data_schema = flow._build_options_schema(
        options=options, saved_options=flow.area_options, selectors=selectors
    )

    return flow.async_show_form(
        step_id="area_config",
        data_schema=data_schema,
        errors=errors,
    )


async def handle_presence_tracking(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle presence tracking configuration step."""
    options_schema = (
        META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
        if (flow._area_config and flow._area_config.is_meta())
        else REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
    )

    errors, validated = await handle_step_validation(
        user_input=user_input,
        schema=options_schema,
        area_name=flow._area_config.name if flow._area_config else "Unknown",
        step_name="presence_tracking",
        area_options=flow.area_options,
        on_success=flow.async_step_show_menu,
    )

    if validated:
        return await flow.async_step_show_menu()

    all_selectors = {
        CONF_PRESENCE_DEVICE_PLATFORMS: build_selector_select(
            sorted(ALL_PRESENCE_DEVICE_PLATFORMS), multiple=True
        ),
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: build_selector_select(
            sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
        ),
        CONF_KEEP_ONLY_ENTITIES: build_selector_entity_simple(
            sorted(
                flow._coordinator_data.presence_sensors
                if flow._coordinator_data
                else []
            ),
            multiple=True,
        ),
        CONF_CLEAR_TIMEOUT: build_selector_number(unit_of_measurement="minutes"),
    }

    options = (
        OPTIONS_PRESENCE_TRACKING_META
        if (flow._area_config and flow._area_config.is_meta())
        else OPTIONS_PRESENCE_TRACKING
    )

    selectors = {opt[0]: all_selectors[opt[0]] for opt in options}

    data_schema = flow._build_options_schema(
        options=options, saved_options=flow.area_options, selectors=selectors
    )

    return flow.async_show_form(
        step_id="presence_tracking",
        data_schema=data_schema,
        errors=errors,
    )


async def handle_secondary_states(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle secondary states configuration step."""
    area_state_schema = (
        META_AREA_SECONDARY_STATES_SCHEMA
        if (flow._area_config and flow._area_config.is_meta())
        else SECONDARY_STATES_SCHEMA
    )

    errors, validated = await handle_step_validation(
        user_input=user_input,
        schema=area_state_schema,
        area_name=flow._area_config.name if flow._area_config else "Unknown",
        step_name="secondary_states",
        area_options=flow.area_options,
        config_key=CONF_SECONDARY_STATES,
        on_success=flow.async_step_show_menu,
    )

    if validated:
        return await flow.async_step_show_menu()

    return flow.async_show_form(
        step_id="secondary_states",
        data_schema=flow._build_options_schema(
            options=(
                OPTIONS_SECONDARY_STATES_META
                if (flow._area_config and flow._area_config.is_meta())
                else OPTIONS_SECONDARY_STATES
            ),
            saved_options=flow.area_options.get(CONF_SECONDARY_STATES, {}),
            dynamic_validators={
                CONF_DARK_ENTITY: vol.In(
                    EMPTY_ENTRY + flow.all_light_tracking_entities
                ),
                CONF_SLEEP_ENTITY: vol.In(EMPTY_ENTRY + flow.all_binary_entities),
                CONF_ACCENT_ENTITY: vol.In(EMPTY_ENTRY + flow.all_binary_entities),
                CONF_SECONDARY_STATES_CALCULATION_MODE: vol.In(CalculationMode),
            },
            selectors={
                CONF_DARK_ENTITY: build_selector_entity_simple(
                    flow.all_light_tracking_entities
                ),
                CONF_SLEEP_ENTITY: build_selector_entity_simple(
                    flow.all_binary_entities
                ),
                CONF_ACCENT_ENTITY: build_selector_entity_simple(
                    flow.all_binary_entities
                ),
                CONF_SLEEP_TIMEOUT: build_selector_number(
                    unit_of_measurement="minutes"
                ),
                CONF_EXTENDED_TIME: build_selector_number(
                    unit_of_measurement="minutes"
                ),
                CONF_EXTENDED_TIMEOUT: build_selector_number(
                    unit_of_measurement="minutes"
                ),
                CONF_SECONDARY_STATES_CALCULATION_MODE: build_selector_select(
                    options=list(CalculationMode),
                    translation_key=SelectorTranslationKeys.CALCULATION_MODE,
                ),
            },
        ),
        errors=errors,
    )
