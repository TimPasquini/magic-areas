"""End-to-end options-flow tests for area options and control groups."""

from typing import Protocol, cast

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.entity_registry import async_get as async_get_er
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys.area import (
    CONF_ACCENT_ENTITY,
    CONF_CLEAR_TIMEOUT,
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
)
from custom_components.magic_areas.enums import CalculationMode, MagicAreasFeatures

from .options_flow_testkit import go_to_step, start_options_flow, submit_step


def _data_schema(result: ConfigFlowResult) -> vol.Schema:
    """Return a non-optional data schema from a form result."""
    return cast(vol.Schema, result["data_schema"])


class _SelectorWithConfig(Protocol):
    """Minimal selector contract used by options-flow tests."""

    config: dict[str, object]


def _schema_selectors(result: ConfigFlowResult) -> dict[str, _SelectorWithConfig]:
    """Return selectors keyed by config key from a form result."""
    return cast(
        dict[str, _SelectorWithConfig],
        {
            getattr(marker, "schema", marker): selector
            for marker, selector in _data_schema(result).schema.items()
        },
    )


def _schema_suggested_values(result: ConfigFlowResult) -> dict[str, object]:
    """Return suggested values keyed by config key from a form result."""
    return {
        getattr(marker, "schema", marker): marker.description["suggested_value"]
        for marker in _data_schema(result).schema
    }


def _selector_list(selector: _SelectorWithConfig, key: str) -> list[str]:
    """Return a selector config list value."""
    return cast(list[str], selector.config[key])


async def test_options_flow(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Area options flow stores core settings and light-group config."""
    config_entry = init_integration
    er = async_get_er(hass)

    er.async_get_or_create(
        suggested_object_id="test_light",
        unique_id="test_light",
        domain=LIGHT_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"

    result = await go_to_step(hass, result, "area_config")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {CONF_TYPE: AreaType.EXTERIOR})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "presence_tracking")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(
        hass,
        result,
        {
            CONF_CLEAR_TIMEOUT: 2,
            CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"],
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "secondary_states")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {CONF_SLEEP_TIMEOUT: 3})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "select_features")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {MagicAreasFeatures.LIGHT_GROUPS: True})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "feature_conf_light_groups")
    assert result["type"] == FlowResultType.MENU
    result = await go_to_step(hass, result, "feature_conf_light_groups_roles")
    assert result["type"] == FlowResultType.FORM
    result = await submit_step(hass, result, {"overhead_lights": ["light.test_light"]})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "show_menu")
    assert result["type"] == FlowResultType.MENU
    result = await go_to_step(hass, result, "finish")

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_TYPE] == AreaType.EXTERIOR
    assert config_entry.options[CONF_CLEAR_TIMEOUT] == 2
    assert config_entry.options[CONF_PRESENCE_DEVICE_PLATFORMS] == ["binary_sensor"]
    assert config_entry.options["secondary_states"][CONF_SLEEP_TIMEOUT] == 3
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] == {
        "overhead_lights": ["light.test_light"],
        "overhead_lights_states": ["occupied"],
        "overhead_lights_act_on": ["occupancy", "state"],
        "sleep_lights": [],
        "sleep_lights_states": [],
        "sleep_lights_act_on": ["occupancy", "state"],
        "accent_lights": [],
        "accent_lights_states": [],
        "accent_lights_act_on": ["occupancy", "state"],
        "task_lights": [],
        "task_lights_states": [],
        "task_lights_act_on": ["occupancy", "state"],
    }


async def test_options_flow_area_config_uses_task_fit_selectors(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Area behavior fields should use constrained selector surfaces."""
    config_entry = init_integration
    er = async_get_er(hass)
    light_entity = er.async_get_or_create(
        suggested_object_id="area_config_light",
        unique_id="area_config_light",
        domain=LIGHT_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    er.async_update_entity(light_entity.entity_id, area_id=str(config_entry.unique_id))
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "area_config")
    assert result["type"] == FlowResultType.FORM

    selectors = _schema_selectors(result)
    area_type_selector = selectors[CONF_TYPE]
    include_selector = selectors[CONF_INCLUDE_ENTITIES]
    exclude_selector = selectors[CONF_EXCLUDE_ENTITIES]

    assert area_type_selector.config["mode"] == "dropdown"
    assert area_type_selector.config["translation_key"] == "area_type"
    assert include_selector.config["multiple"] is True
    assert exclude_selector.config["multiple"] is True
    assert light_entity.entity_id in _selector_list(
        include_selector, "include_entities"
    )
    assert isinstance(exclude_selector.config["include_entities"], list)
    assert CONF_RELOAD_ON_REGISTRY_CHANGE in selectors
    assert CONF_IGNORE_DIAGNOSTIC_ENTITIES in selectors


async def test_options_flow_area_config_reopen_preserves_saved_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Area behavior should reopen with saved type and entity filters."""
    config_entry = init_integration
    er = async_get_er(hass)
    include_entity = er.async_get_or_create(
        suggested_object_id="manual_include",
        unique_id="manual_include",
        domain=LIGHT_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    exclude_entity = er.async_get_or_create(
        suggested_object_id="noisy",
        unique_id="noisy",
        domain="sensor",
        platform="test",
        config_entry=config_entry,
    )
    er.async_update_entity(exclude_entity.entity_id, area_id=str(config_entry.unique_id))
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "area_config")
    result = await submit_step(
        hass,
        result,
        {
            CONF_TYPE: AreaType.EXTERIOR,
            CONF_INCLUDE_ENTITIES: [include_entity.entity_id],
            CONF_EXCLUDE_ENTITIES: [exclude_entity.entity_id],
            CONF_RELOAD_ON_REGISTRY_CHANGE: False,
            CONF_IGNORE_DIAGNOSTIC_ENTITIES: False,
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "area_config")
    suggested_values = _schema_suggested_values(result)

    assert suggested_values[CONF_TYPE] == AreaType.EXTERIOR
    assert suggested_values[CONF_INCLUDE_ENTITIES] == [include_entity.entity_id]
    assert suggested_values[CONF_EXCLUDE_ENTITIES] == [exclude_entity.entity_id]
    assert suggested_values[CONF_RELOAD_ON_REGISTRY_CHANGE] is False
    assert suggested_values[CONF_IGNORE_DIAGNOSTIC_ENTITIES] is False


async def test_options_flow_presence_tracking_uses_task_fit_selectors(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Presence tracking fields should use translated multi-select and number selectors."""
    result = await start_options_flow(hass, init_integration)
    result = await go_to_step(hass, result, "presence_tracking")
    assert result["type"] == FlowResultType.FORM

    selectors = _schema_selectors(result)
    platform_selector = selectors[CONF_PRESENCE_DEVICE_PLATFORMS]
    class_selector = selectors[CONF_PRESENCE_SENSOR_DEVICE_CLASS]
    keep_only_selector = selectors[CONF_KEEP_ONLY_ENTITIES]
    timeout_selector = selectors[CONF_CLEAR_TIMEOUT]

    assert platform_selector.config["multiple"] is True
    assert "binary_sensor" in _selector_list(platform_selector, "options")
    assert "media_player" in _selector_list(platform_selector, "options")
    assert class_selector.config["multiple"] is True
    assert BinarySensorDeviceClass.MOTION in _selector_list(class_selector, "options")
    assert keep_only_selector.config["multiple"] is True
    assert timeout_selector.config["mode"] == "box"
    assert timeout_selector.config["unit_of_measurement"] == "minutes"


async def test_options_flow_presence_tracking_reopen_preserves_saved_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Presence tracking should reopen with saved platforms, classes, filters, timeout."""
    config_entry = init_integration
    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "presence_tracking")
    result = await submit_step(
        hass,
        result,
        {
            CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"],
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
            CONF_KEEP_ONLY_ENTITIES: ["binary_sensor.motion_keep"],
            CONF_CLEAR_TIMEOUT: 7,
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "presence_tracking")
    suggested_values = _schema_suggested_values(result)

    assert suggested_values[CONF_PRESENCE_DEVICE_PLATFORMS] == ["binary_sensor"]
    assert suggested_values[CONF_PRESENCE_SENSOR_DEVICE_CLASS] == ["motion"]
    assert suggested_values[CONF_KEEP_ONLY_ENTITIES] == ["binary_sensor.motion_keep"]
    assert suggested_values[CONF_CLEAR_TIMEOUT] == 7


async def test_options_flow_secondary_states_uses_task_fit_selectors(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Secondary states should expose entity selectors and minute timeout controls."""
    config_entry = init_integration
    er = async_get_er(hass)
    light_binary = er.async_get_or_create(
        suggested_object_id="secondary_light_binary",
        unique_id="secondary_light_binary",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
        original_device_class=BinarySensorDeviceClass.LIGHT,
    )
    sleep_binary = er.async_get_or_create(
        suggested_object_id="secondary_sleep_binary",
        unique_id="secondary_sleep_binary",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
    )
    hass.states.async_set(
        light_binary.entity_id,
        "off",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    selectors = _schema_selectors(result)

    dark_selector = selectors[CONF_DARK_ENTITY]
    sleep_selector = selectors[CONF_SLEEP_ENTITY]
    accent_selector = selectors[CONF_ACCENT_ENTITY]
    assert light_binary.entity_id in _selector_list(
        dark_selector, "include_entities"
    )
    assert sleep_binary.entity_id in _selector_list(
        sleep_selector, "include_entities"
    )
    assert sleep_binary.entity_id in _selector_list(
        accent_selector, "include_entities"
    )
    for key in (CONF_SLEEP_TIMEOUT, CONF_EXTENDED_TIME, CONF_EXTENDED_TIMEOUT):
        selector = selectors[key]
        assert selector.config["mode"] == "box"
        assert selector.config["unit_of_measurement"] == "minutes"
    assert CONF_SECONDARY_STATES_CALCULATION_MODE not in selectors


async def test_options_flow_secondary_states_reopen_preserves_saved_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Secondary states should reopen with saved entity and timeout choices."""
    config_entry = init_integration
    er = async_get_er(hass)
    dark_entity = er.async_get_or_create(
        suggested_object_id="room_dark",
        unique_id="room_dark",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
        original_device_class=BinarySensorDeviceClass.LIGHT,
    )
    sleep_entity = er.async_get_or_create(
        suggested_object_id="room_sleep",
        unique_id="room_sleep",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
    )
    accent_entity = er.async_get_or_create(
        suggested_object_id="room_accent",
        unique_id="room_accent",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
    )
    hass.states.async_set(
        dark_entity.entity_id,
        "off",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    result = await submit_step(
        hass,
        result,
        {
            CONF_DARK_ENTITY: dark_entity.entity_id,
            CONF_SLEEP_ENTITY: sleep_entity.entity_id,
            CONF_ACCENT_ENTITY: accent_entity.entity_id,
            CONF_SLEEP_TIMEOUT: 4,
            CONF_EXTENDED_TIME: 8,
            CONF_EXTENDED_TIMEOUT: 12,
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    suggested_values = _schema_suggested_values(result)

    assert suggested_values[CONF_DARK_ENTITY] == dark_entity.entity_id
    assert suggested_values[CONF_SLEEP_ENTITY] == sleep_entity.entity_id
    assert suggested_values[CONF_ACCENT_ENTITY] == accent_entity.entity_id
    assert suggested_values[CONF_SLEEP_TIMEOUT] == 4
    assert suggested_values[CONF_EXTENDED_TIME] == 8
    assert suggested_values[CONF_EXTENDED_TIMEOUT] == 12


async def test_options_flow_meta_secondary_states_exposes_calculation_mode(
    hass: HomeAssistant, init_integration_all_areas: list[MockConfigEntry]
) -> None:
    """Meta-area secondary states should expose translated calculation mode choices."""
    config_entry = next(
        entry for entry in init_integration_all_areas if entry.data.get(CONF_TYPE) == "meta"
    )

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    selectors = _schema_selectors(result)
    calculation_selector = selectors[CONF_SECONDARY_STATES_CALCULATION_MODE]

    assert calculation_selector.config["mode"] == "dropdown"
    assert calculation_selector.config["translation_key"] == "calculation_mode"
    assert set(_selector_list(calculation_selector, "options")) == {
        CalculationMode.ANY.value,
        CalculationMode.ALL.value,
        CalculationMode.MAJORITY.value,
    }

    result = await submit_step(
        hass,
        result,
        {CONF_SECONDARY_STATES_CALCULATION_MODE: CalculationMode.MAJORITY},
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    suggested_values = _schema_suggested_values(result)
    assert (
        suggested_values[CONF_SECONDARY_STATES_CALCULATION_MODE]
        == CalculationMode.MAJORITY
    )


async def test_options_flow_custom_control_groups_step(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups should validate and persist through options flow."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "custom_control_groups")
    assert result["type"] == FlowResultType.FORM

    result = await submit_step(
        hass,
        result,
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "group_id": "control.task",
                    "members": ["light.test_light"],
                    "trigger_states": ["occupied"],
                    "policy_id": "custom_control_group",
                    "metadata": {"label": "Task"},
                }
            ]
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_CUSTOM_CONTROL_GROUPS][0]["group_id"] == "control.task"


async def test_options_flow_custom_control_groups_uses_guided_selector(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups should expose a structured object editor."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")

    schema = result["data_schema"]
    assert schema is not None
    selector = next(iter(schema.schema.values()))

    assert selector.config["multiple"] is True
    assert selector.config["label_field"] == "group_id"
    assert selector.config["description_field"] == "policy_id"
    fields = selector.config["fields"]
    assert set(fields) == {
        "group_id",
        "members",
        "trigger_states",
        "policy_id",
        "metadata",
    }
    assert fields["group_id"]["required"] is True
    assert fields["members"]["required"] is True
    trigger_selector = fields["trigger_states"]["selector"]["select"]
    assert trigger_selector["multiple"] is True
    assert trigger_selector["translation_key"] == "area_states"


async def test_options_flow_custom_control_groups_empty_submit_does_not_seed_templates(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups should not create templates from an empty submit."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")
    assert result["type"] == FlowResultType.FORM

    result = await submit_step(hass, result, {})
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_CUSTOM_CONTROL_GROUPS] == []


async def test_options_flow_custom_control_groups_explicit_empty_does_not_reseed(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Explicitly deleting all custom control groups should not restore templates."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")
    result = await submit_step(
        hass,
        result,
        {CONF_CUSTOM_CONTROL_GROUPS: []},
    )
    assert result["type"] == FlowResultType.MENU

    result = await go_to_step(hass, result, "finish")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_CUSTOM_CONTROL_GROUPS] == []

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")
    schema = result["data_schema"]
    assert schema is not None
    marker = next(iter(schema.schema))
    assert marker.description["suggested_value"] == []


async def test_options_flow_custom_control_groups_rejects_invalid_payload(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Custom control groups step should reject invalid payloads."""
    config_entry = init_integration

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "custom_control_groups")

    result = await submit_step(
        hass,
        result,
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "group_id": "control.duplicate",
                    "members": ["light.test_light"],
                    "trigger_states": ["occupied"],
                    "policy_id": "custom_control_group",
                },
                {
                    "group_id": "control.duplicate",
                    "members": ["light.other"],
                    "trigger_states": ["sleep"],
                    "policy_id": "custom_control_group",
                },
            ]
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "custom_control_groups"
    assert result["errors"]


async def test_options_flow_with_light_binary_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Secondary-state dark entity selector accepts light-class binary sensors."""
    config_entry = init_integration
    er = async_get_er(hass)

    er.async_get_or_create(
        suggested_object_id="test_light_sensor",
        unique_id="test_light_sensor",
        domain="binary_sensor",
        platform="test",
        config_entry=config_entry,
        original_device_class=BinarySensorDeviceClass.LIGHT,
    )
    hass.states.async_set(
        "binary_sensor.test_light_sensor",
        "off",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    result = await start_options_flow(hass, config_entry)
    result = await go_to_step(hass, result, "secondary_states")
    result = await submit_step(
        hass,
        result,
        {"dark_entity": "binary_sensor.test_light_sensor"},
    )

    assert result["type"] == FlowResultType.MENU
