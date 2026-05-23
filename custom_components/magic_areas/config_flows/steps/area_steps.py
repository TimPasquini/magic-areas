"""Area configuration step handlers for options flow.

Handles basic area settings, presence tracking configuration, and secondary states.
"""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import ObjectSelectorField

from custom_components.magic_areas.config_keys.area import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.config_flows.base import (
    DynamicValidatorMap,
    SelectorMap,
    handle_step_validation,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_SECONDARY_STATES,
    CONF_TYPE,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
)
from custom_components.magic_areas.defaults import (
    ALL_PRESENCE_DEVICE_PLATFORMS,
)
from custom_components.magic_areas.area_state import AreaStates, AreaType
from custom_components.magic_areas.enums import CalculationMode, SelectorTranslationKeys
from custom_components.magic_areas.policy import ALL_BINARY_SENSOR_DEVICE_CLASSES
from custom_components.magic_areas.schemas import (
    META_AREA_BASIC_OPTIONS_SCHEMA,
    META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    META_AREA_SECONDARY_STATES_SCHEMA,
    REGULAR_AREA_BASIC_OPTIONS_SCHEMA,
    REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    SECONDARY_STATES_SCHEMA,
)
from custom_components.magic_areas.schemas import (
    CUSTOM_CONTROL_GROUPS_SCHEMA,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_boolean,
    build_selector_entity_any,
    build_selector_entity_simple,
    build_selector_number,
    build_selector_object,
    build_selector_select,
    build_selector_text,
)
from custom_components.magic_areas.core.controls import get_custom_control_group_templates

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler

EMPTY_ENTRY = [""]


class _SerializableSelector(Protocol):
    """Selector object that can expose HA's serialized selector config."""

    def serialize(self) -> Mapping[str, object]:
        """Return HA selector serialization."""
        ...

CUSTOM_CONTROL_GROUP_TRIGGER_STATES = [
    str(AreaStates.OCCUPIED),
    str(AreaStates.EXTENDED),
    str(AreaStates.SLEEP),
    str(AreaStates.DARK),
    str(AreaStates.BRIGHT),
    str(AreaStates.ACCENT),
]


def _custom_control_group_selector() -> object:
    """Build a guided object selector for custom control groups."""
    return build_selector_object(
        fields={
            "group_id": ObjectSelectorField(
                label="Group ID",
                required=True,
                selector=_field_selector(build_selector_text()),
            ),
            "members": ObjectSelectorField(
                label="Members",
                required=True,
                selector=_field_selector(build_selector_entity_any(multiple=True)),
            ),
            "trigger_states": ObjectSelectorField(
                label="Trigger states",
                required=False,
                selector=_field_selector(
                    build_selector_select(
                        options=CUSTOM_CONTROL_GROUP_TRIGGER_STATES,
                        multiple=True,
                        translation_key=SelectorTranslationKeys.AREA_STATES,
                    )
                ),
            ),
            "policy_id": ObjectSelectorField(
                label="Policy ID",
                required=False,
                selector=_field_selector(build_selector_text()),
            ),
            "metadata": ObjectSelectorField(
                label="Metadata",
                required=False,
                selector=_field_selector(build_selector_object()),
            ),
        },
        multiple=True,
        label_field="group_id",
        description_field="policy_id",
        translation_key="custom_control_groups",
    )


def _field_selector(selector_obj: _SerializableSelector) -> dict[str, object]:
    """Return the serialized selector config ObjectSelector fields expect."""
    selector_config = selector_obj.serialize().get("selector")
    if not isinstance(selector_config, dict):
        raise TypeError("Object selector field requires a serialized selector config")
    return selector_config


async def handle_area_config(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
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

    all_selectors: SelectorMap = {
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
        CONF_RELOAD_ON_REGISTRY_CHANGE: build_selector_boolean(),
        CONF_IGNORE_DIAGNOSTIC_ENTITIES: build_selector_boolean(),
    }

    data_schema = flow._build_schema_from_vol(
        options_schema,
        saved_options=flow.area_options,
        selectors=all_selectors,
    )

    return flow.async_show_form(
        step_id="area_config",
        data_schema=data_schema,
        errors=errors,
    )


async def handle_presence_tracking(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
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

    all_selectors: SelectorMap = {
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

    data_schema = flow._build_schema_from_vol(
        options_schema,
        saved_options=flow.area_options,
        selectors=all_selectors,
    )

    return flow.async_show_form(
        step_id="presence_tracking",
        data_schema=data_schema,
        errors=errors,
    )


async def handle_secondary_states(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
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

    dynamic_validators: DynamicValidatorMap = {
        CONF_DARK_ENTITY: vol.In(
            EMPTY_ENTRY + flow.all_light_tracking_entities
        ),
        CONF_SLEEP_ENTITY: vol.In(EMPTY_ENTRY + flow.all_binary_entities),
        CONF_ACCENT_ENTITY: vol.In(EMPTY_ENTRY + flow.all_binary_entities),
        CONF_SECONDARY_STATES_CALCULATION_MODE: vol.In(CalculationMode),
    }
    selectors: SelectorMap = {
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
    }
    saved_secondary_states = flow.area_options.get(CONF_SECONDARY_STATES)

    return flow.async_show_form(
        step_id="secondary_states",
        data_schema=flow._build_schema_from_vol(
            area_state_schema,
            saved_options=(
                saved_secondary_states
                if isinstance(saved_secondary_states, dict)
                else {}
            ),
            dynamic_validators=dynamic_validators,
            selectors=selectors,
        ),
        errors=errors,
    )


async def handle_custom_control_groups(
    flow: "OptionsFlowHandler", user_input: Mapping[str, object] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle custom control-group configuration step."""
    if CONF_CUSTOM_CONTROL_GROUPS in flow.area_options:
        default_groups = flow.area_options[CONF_CUSTOM_CONTROL_GROUPS]
    else:
        default_groups = get_custom_control_group_templates()

    schema = vol.Schema(
        {
            vol.Optional(
                CONF_CUSTOM_CONTROL_GROUPS, default=default_groups
            ): CUSTOM_CONTROL_GROUPS_SCHEMA,
        },
        extra=vol.REMOVE_EXTRA,
    )

    errors, validated = await handle_step_validation(
        user_input=user_input,
        schema=schema,
        area_name=flow._area_config.name if flow._area_config else "Unknown",
        step_name="custom_control_groups",
        area_options=flow.area_options,
        on_success=flow.async_step_show_menu,
    )

    if validated:
        return await flow.async_step_show_menu()

    return flow.async_show_form(
        step_id="custom_control_groups",
        data_schema=flow._build_schema_from_vol(
            schema,
            saved_options=flow.area_options,
            selectors={
                CONF_CUSTOM_CONTROL_GROUPS: _custom_control_group_selector(),
            },
        ),
        errors=errors,
    )
