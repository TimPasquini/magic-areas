"""End-to-end feature configuration options-flow tests."""

from typing import cast

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.entity_registry import async_get as async_get_er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_NOTIFICATION_DEVICES,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    adaptive_lighting_switch_entity_ids,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    adaptive_lighting_pair_key,
)


def _data_schema(result: ConfigFlowResult) -> vol.Schema:
    """Return a non-optional data schema from a form result."""
    return cast(vol.Schema, result["data_schema"])


def _register_adaptive_lighting_switch_set(
    hass: HomeAssistant,
    name: str,
    *,
    area_id: str,
) -> dict[str, str]:
    """Register one complete Adaptive Lighting switch set for options-flow tests."""
    entity_registry = async_get_er(hass)
    refs = adaptive_lighting_switch_entity_ids(name)
    for entity_id in refs.values():
        domain, object_id = entity_id.split(".", 1)
        entry = entity_registry.async_get_or_create(
            domain,
            "adaptive_lighting",
            object_id,
            suggested_object_id=object_id,
        )
        entity_registry.async_update_entity(entry.entity_id, area_id=area_id)
    return refs


async def _open_feature_config_step(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    feature: MagicAreasFeatures,
    step_id: str,
) -> ConfigFlowResult:
    """Start options flow, enable one feature, and open its config step."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={feature: True}
    )
    return await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": step_id}
    )


async def test_options_flow_climate_no_presets(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Climate flow aborts when selected climate has no preset support."""
    config_entry = init_integration
    er = async_get_er(hass)

    climate_entity = er.async_get_or_create(
        suggested_object_id="test_climate_no_presets",
        unique_id="test_climate_no_presets",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=config_entry,
        capabilities={},
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.CLIMATE_CONTROL,
        "feature_conf_climate_control",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "climate_no_preset_support"


async def test_options_flow_climate_with_presets(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Climate flow stores selected presets when supported."""
    config_entry = init_integration
    er = async_get_er(hass)

    climate_entity = er.async_get_or_create(
        suggested_object_id="test_climate_with_presets",
        unique_id="test_climate_with_presets",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=config_entry,
        capabilities={ATTR_PRESET_MODES: ["home", "away"]},
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.CLIMATE_CONTROL,
        "feature_conf_climate_control",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: "home",
            CONF_CLIMATE_CONTROL_PRESET_CLEAR: "away",
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.CLIMATE_CONTROL
    ] == {
        "entity_id": "climate.test_climate_with_presets",
        "preset_clear": "away",
        "preset_occupied": "home",
        "preset_sleep": "",
        "preset_extended": "",
    }


async def test_options_flow_fan_groups(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan groups flow stores required state and setpoint."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.EXTENDED,
            CONF_FAN_GROUPS_SETPOINT: 25.0,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.FAN_GROUPS
    ] == {
        "required_state": "extended",
        "tracked_device_class": "temperature",
        "setpoint": 25.0,
    }


async def test_options_flow_fan_groups_accepts_integer_setpoint(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan groups flow accepts integer setpoint input and persists float."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.EXTENDED,
            CONF_FAN_GROUPS_SETPOINT: 50,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert (
        config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.FAN_GROUPS][
            "setpoint"
        ]
        == 50.0
    )


async def test_options_flow_area_aware_media_player(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Area-aware media player flow stores selected notification devices."""
    config_entry = init_integration
    er = async_get_er(hass)
    media_player_entity = er.async_get_or_create(
        suggested_object_id="test_media_player",
        unique_id="test_media_player",
        domain=MEDIA_PLAYER_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
        "feature_conf_area_aware_media_player",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_NOTIFICATION_DEVICES: [media_player_entity.entity_id]},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    ] == {
        "notification_devices": ["media_player.test_media_player"],
        "notification_states": ["extended"],
    }


async def test_options_flow_aggregates(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Aggregates flow stores custom aggregate parameters."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.AGGREGATES,
        "feature_conf_aggregates",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_AGGREGATES_MIN_ENTITIES: 3,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 100,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert (
        config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.AGGREGATES][
            "aggregates_min_entities"
        ]
        == 3
    )
    assert (
        config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.AGGREGATES][
            "aggregates_illuminance_threshold"
        ]
        == 100
    )


async def test_options_flow_presence_hold(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Presence hold flow stores timeout value."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.PRESENCE_HOLD,
        "feature_conf_presence_hold",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_PRESENCE_HOLD_TIMEOUT: 10},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.PRESENCE_HOLD
    ] == {"presence_hold_timeout": 10}


async def test_options_flow_ble_trackers(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """BLE trackers flow stores selected tracker entities."""
    config_entry = init_integration
    er = async_get_er(hass)
    sensor_entity = er.async_get_or_create(
        suggested_object_id="test_sensor",
        unique_id="test_sensor",
        domain=SENSOR_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.BLE_TRACKER,
        "feature_conf_ble_trackers",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_BLE_TRACKER_ENTITIES: [sensor_entity.entity_id]},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.BLE_TRACKER
    ] == {"ble_tracker_entities": ["sensor.test_sensor"]}


async def test_options_flow_wasp_in_a_box(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Wasp in a Box flow stores delay and timeout values."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.WASP_IN_A_BOX,
        "feature_conf_wasp_in_a_box",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_WASP_IN_A_BOX_DELAY: 60,
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 5,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.WASP_IN_A_BOX
    ] == {
        "delay": 60,
        "wasp_timeout": 5,
        "wasp_device_classes": ["motion", "occupancy"],
    }


async def test_options_flow_health(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Health flow stores selected health classes."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.HEALTH,
        "feature_conf_health",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem", "smoke"]},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.HEALTH] == {
        "health_binary_sensor_device_classes": ["problem", "smoke"]
    }


async def test_options_flow_light_groups_advisory_shows_binary_fields_only(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Advisory mode should expose inside/outside bright binaries but hide adaptive-only fields."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )
    assert result["type"] == FlowResultType.FORM

    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS not in keys
    assert CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY not in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY not in keys

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"brightness_mode": "advisory"},
    )
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_light_groups"}
    )
    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS not in keys


async def test_options_flow_light_groups_adaptive_shows_binary_and_lux_fields(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Adaptive mode should expose advisory and adaptive-only controls."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"brightness_mode": "adaptive"},
    )
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_light_groups"}
    )
    assert result["type"] == FlowResultType.FORM

    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY in keys


async def test_options_flow_light_groups_adaptive_lighting_ignore_hides_pairings(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Ignore mode should expose only the AL mode selector, not pairing fields."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )

    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE in keys
    assert adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS) not in keys


async def test_options_flow_light_groups_adopt_existing_pairs_same_area_al_set(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Adopt-existing mode should store selected same-area AL switch refs by role."""
    config_entry = init_integration
    refs = _register_adaptive_lighting_switch_set(
        hass,
        "Kitchen Overhead",
        area_id="kitchen",
    )
    _register_adaptive_lighting_switch_set(
        hass,
        "Bedroom Overhead",
        area_id="master_bedroom",
    )
    new_options = config_entry.options.copy()
    new_options.setdefault(CONF_ENABLED_FEATURES, {})
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {
        "overhead_lights": ["light.test_light"],
        "brightness_mode": "inhibit",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
        ),
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )

    assert result["type"] == FlowResultType.FORM
    pair_key = adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS)
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert pair_key in keys

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            pair_key: refs[MAIN_SWITCH],
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS][
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS
    ] == {
        CONF_OVERHEAD_LIGHTS: {
            MAIN_SWITCH: refs[MAIN_SWITCH],
            SLEEP_SWITCH: refs[SLEEP_SWITCH],
            ADAPT_BRIGHTNESS_SWITCH: refs[ADAPT_BRIGHTNESS_SWITCH],
            ADAPT_COLOR_SWITCH: refs[ADAPT_COLOR_SWITCH],
        }
    }


async def test_options_flow_light_groups_manage_selects_managed_roles(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Manage mode should expose role selection and persist selected roles."""
    config_entry = init_integration
    new_options = config_entry.options.copy()
    new_options.setdefault(CONF_ENABLED_FEATURES, {})
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {
        "overhead_lights": ["light.test_light"],
        "brightness_mode": "inhibit",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ),
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )

    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES in keys

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES: [CONF_OVERHEAD_LIGHTS],
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS][
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES
    ] == [CONF_OVERHEAD_LIGHTS]


async def test_options_flow_light_groups_manage_all_lights_uses_separate_gate(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Manage mode should expose all-lights as a boolean, not a role option."""
    config_entry = init_integration
    new_options = config_entry.options.copy()
    new_options.setdefault(CONF_ENABLED_FEATURES, {})
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {
        "overhead_lights": ["light.test_light"],
        "brightness_mode": "inhibit",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ),
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )

    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL in keys
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES in keys
    role_marker = next(
        marker
        for marker in schema.schema
        if getattr(marker, "schema", marker)
        == CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES
    )
    role_validator = schema.schema[role_marker]
    assert role_validator([CONF_OVERHEAD_LIGHTS]) == [CONF_OVERHEAD_LIGHTS]
    with pytest.raises(vol.Invalid):
        role_validator(["all_lights"])

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL: True,
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES: [CONF_OVERHEAD_LIGHTS],
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    feature_options = config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS
    ]
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is True
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] == [
        CONF_OVERHEAD_LIGHTS
    ]


async def test_options_flow_light_groups_preserves_adaptive_lighting_switch_sets(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Mode-specific light group edits should not drop hidden AL switch-set mappings."""
    config_entry = init_integration
    switch_sets = {
        "overhead_lights": {
            "main": "switch.adaptive_lighting_kitchen_overhead",
            "sleep": "switch.adaptive_lighting_sleep_mode_kitchen_overhead",
            "adapt_brightness": (
                "switch.adaptive_lighting_adapt_brightness_kitchen_overhead"
            ),
            "adapt_color": "switch.adaptive_lighting_adapt_color_kitchen_overhead",
        }
    }
    new_options = config_entry.options.copy()
    new_options.setdefault(CONF_ENABLED_FEATURES, {})
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {
        "brightness_mode": "advisory",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: switch_sets,
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"brightness_mode": "inhibit"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert (
        config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS][
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS
        ]
        == switch_sets
    )


async def test_options_flow_remove_feature(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Feature deselection removes existing feature config."""
    config_entry = init_integration

    new_data = config_entry.options.copy()
    if CONF_ENABLED_FEATURES not in new_data:
        new_data[CONF_ENABLED_FEATURES] = {}
    new_data[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {}

    hass.config_entries.async_update_entry(config_entry, options=new_data)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={MagicAreasFeatures.LIGHT_GROUPS: False}
    )
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )

    assert (
        MagicAreasFeatures.LIGHT_GROUPS
        not in config_entry.options[CONF_ENABLED_FEATURES]
    )


async def test_options_flow_add_feature(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Feature selection adds missing feature config."""
    config_entry = init_integration

    new_options = config_entry.options.copy()
    if CONF_ENABLED_FEATURES in new_options:
        if MagicAreasFeatures.LIGHT_GROUPS in new_options[CONF_ENABLED_FEATURES]:
            del new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS]

    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={MagicAreasFeatures.LIGHT_GROUPS: True}
    )

    assert result["type"] == FlowResultType.MENU

    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "finish"}
    )
    assert (
        MagicAreasFeatures.LIGHT_GROUPS in config_entry.options[CONF_ENABLED_FEATURES]
    )


async def test_options_flow_with_light_binary_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Secondary-state dark entity selector accepts light-class binary sensors."""
    config_entry = init_integration
    er = async_get_er(hass)

    er.async_get_or_create(
        suggested_object_id="test_light_sensor",
        unique_id="test_light_sensor",
        domain=BINARY_SENSOR_DOMAIN,
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

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "secondary_states"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_DARK_ENTITY: "binary_sensor.test_light_sensor"},
    )

    assert result["type"] == FlowResultType.MENU
