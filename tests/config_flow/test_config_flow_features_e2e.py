"""End-to-end feature configuration options-flow tests."""

from typing import Protocol, cast

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
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
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_FAN_CONTROLLER_ACTIVE_STATES,
    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
    CONF_FAN_CONTROLLER_DETECTION_MODE,
    CONF_FAN_CONTROLLER_HYSTERESIS,
    CONF_FAN_CONTROLLER_MEMBERS,
    CONF_FAN_CONTROLLER_ON_THRESHOLD,
    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
    CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
    CONF_FAN_CONTROLLER_SUPPRESS_STATES,
    CONF_FAN_GROUPS_CONTROLLERS,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    adaptive_lighting_switch_entity_ids,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanClearBehavior,
    FanControllerRole,
    FanDetectionMode,
    FanSensorUnavailableBehavior,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_threshold_light_sensor_unique_id,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    CONF_SLEEP_LIGHTS,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_FEATURE_SCHEMA,
    adaptive_lighting_pair_key,
)


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
    """Return schema suggested values keyed by config key."""
    return {
        getattr(marker, "schema", marker): marker.description["suggested_value"]
        for marker in _data_schema(result).schema
    }


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
    if step_id.startswith("feature_conf_light_groups_"):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"next_step_id": "feature_conf_light_groups"},
        )
    if step_id.startswith("feature_conf_fan_groups_"):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"next_step_id": "feature_conf_fan_groups"},
        )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": step_id}
    )
    if (
        step_id.startswith("feature_conf_")
        and not step_id.startswith("feature_conf_light_groups")
        and not step_id.endswith("_settings")
        and step_id != "feature_conf_climate_control_select_presets"
        and result["type"] == FlowResultType.MENU
    ):
        return await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": f"{step_id}_settings"}
        )
    return result


async def _open_existing_light_groups_adaptive_lighting_step(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> ConfigFlowResult:
    """Open the Adaptive Lighting substep for an already-enabled Light Groups config."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups"},
    )
    return await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups_adaptive_lighting"},
    )


async def _open_light_groups_brightness_mode_step(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> ConfigFlowResult:
    """Open the light-groups brightness mode selector step."""
    return await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_brightness",
    )


@pytest.mark.parametrize(
    ("feature", "step_id", "expected_menu_options"),
    [
        (
            MagicAreasFeatures.FAN_GROUPS,
            "feature_conf_fan_groups",
            {
                "feature_conf_fan_groups_cooling",
                "feature_conf_fan_groups_humidity",
                "feature_conf_fan_groups_odor",
                "show_menu",
            },
        ),
        (
            MagicAreasFeatures.CLIMATE_CONTROL,
            "feature_conf_climate_control",
            {
                "feature_conf_climate_control_settings",
                "feature_conf_climate_control_select_presets",
                "show_menu",
            },
        ),
    ],
)
async def test_options_flow_intentional_domain_features_open_menu_first(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
    step_id: str,
    expected_menu_options: set[str],
) -> None:
    """Features with multi-page or planned domain complexity should keep submenus."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={feature: True}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": step_id}
    )
    assert result["type"] == FlowResultType.MENU
    assert set(cast(list[str], result["menu_options"])) == expected_menu_options


@pytest.mark.parametrize(
    ("feature", "step_id"),
    [
        (MagicAreasFeatures.HEALTH, "feature_conf_health"),
        (
            MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
            "feature_conf_area_aware_media_player",
        ),
        (MagicAreasFeatures.AGGREGATES, "feature_conf_aggregates"),
        (MagicAreasFeatures.PRESENCE_HOLD, "feature_conf_presence_hold"),
        (MagicAreasFeatures.BLE_TRACKER, "feature_conf_ble_trackers"),
        (MagicAreasFeatures.WASP_IN_A_BOX, "feature_conf_wasp_in_a_box"),
    ],
)
async def test_options_flow_single_page_features_open_forms_directly(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
    step_id: str,
) -> None:
    """Simple single-page feature config entry points should render forms directly."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={feature: True}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": step_id}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id


@pytest.mark.parametrize(
    ("feature", "step_id"),
    [
        (
            MagicAreasFeatures.HEALTH,
            "feature_conf_health",
        ),
        (
            MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
            "feature_conf_area_aware_media_player",
        ),
        (
            MagicAreasFeatures.AGGREGATES,
            "feature_conf_aggregates",
        ),
        (
            MagicAreasFeatures.PRESENCE_HOLD,
            "feature_conf_presence_hold",
        ),
        (
            MagicAreasFeatures.BLE_TRACKER,
            "feature_conf_ble_trackers",
        ),
        (
            MagicAreasFeatures.WASP_IN_A_BOX,
            "feature_conf_wasp_in_a_box",
        ),
    ],
)
async def test_options_flow_single_page_feature_helpers_open_direct_forms(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
    step_id: str,
) -> None:
    """Feature-config helper routing should land simple features on their direct form."""
    result = await _open_feature_config_step(
        hass,
        init_integration,
        feature,
        step_id,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id


async def _select_light_groups_brightness_mode(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    mode: str,
) -> ConfigFlowResult:
    """Submit light-groups brightness mode and return mode-specific step result."""
    return await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"brightness_mode": mode}
    )


async def _finish_options_flow(
    hass: HomeAssistant,
    result: ConfigFlowResult,
) -> ConfigFlowResult:
    """Navigate back to root when needed after page-level options save."""
    menu_options = result.get("menu_options", [])
    if (
        result["type"] == FlowResultType.MENU
        and isinstance(menu_options, list)
        and "show_menu" in menu_options
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"next_step_id": "show_menu"}
        )
    return result


async def test_options_flow_light_group_leaf_submits_return_to_light_group_menu(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Light-group leaf forms should return to the light-group section menu."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_roles",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_OVERHEAD_LIGHTS: ["light.test_light"]},
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "feature_conf_light_groups"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups_brightness"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"brightness_mode": "inhibit"},
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "feature_conf_light_groups"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups_adaptive_lighting"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: "ignore",
        },
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "feature_conf_light_groups"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "show_menu"},
    )
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"


@pytest.mark.parametrize(
    ("feature", "step_id", "user_input"),
    [
        (
            MagicAreasFeatures.HEALTH,
            "feature_conf_health",
            {CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]},
        ),
        (
            MagicAreasFeatures.AGGREGATES,
            "feature_conf_aggregates",
            {CONF_AGGREGATES_MIN_ENTITIES: 2},
        ),
        (
            MagicAreasFeatures.PRESENCE_HOLD,
            "feature_conf_presence_hold",
            {CONF_PRESENCE_HOLD_TIMEOUT: 30},
        ),
        (
            MagicAreasFeatures.WASP_IN_A_BOX,
            "feature_conf_wasp_in_a_box",
            {CONF_WASP_IN_A_BOX_DELAY: 30},
        ),
    ],
)
async def test_options_flow_single_page_feature_submit_returns_to_root(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
    step_id: str,
    user_input: dict[str, object],
) -> None:
    """Simple single-page feature submits should save the page and return to root."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={feature: True}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": step_id}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.CLIMATE_CONTROL
    ] == {
        "entity_id": "climate.test_climate_with_presets",
        "preset_clear": "away",
        "preset_occupied": "home",
        "preset_sleep": "",
        "preset_extended": "",
    }


async def test_options_flow_climate_reopen_preserves_saved_entity_and_presets(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Climate settings should reopen with saved entity and preset mapping."""
    config_entry = init_integration
    er = async_get_er(hass)
    climate_entity = er.async_get_or_create(
        suggested_object_id="reopen_climate_with_presets",
        unique_id="reopen_climate_with_presets",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=config_entry,
        capabilities={ATTR_PRESET_MODES: ["home", "away", "sleep"]},
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
            CONF_CLIMATE_CONTROL_PRESET_SLEEP: "sleep",
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.CLIMATE_CONTROL,
        "feature_conf_climate_control",
    )
    assert result["type"] == FlowResultType.FORM
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_CLIMATE_CONTROL_ENTITY_ID] == climate_entity.entity_id

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )
    assert result["type"] == FlowResultType.FORM
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_CLIMATE_CONTROL_PRESET_OCCUPIED] == "home"
    assert suggested_values[CONF_CLIMATE_CONTROL_PRESET_CLEAR] == "away"
    assert suggested_values[CONF_CLIMATE_CONTROL_PRESET_SLEEP] == "sleep"


async def test_options_flow_climate_entity_selector_surface(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Climate feature step should render an entity selector for climate entity."""
    config_entry = init_integration
    er = async_get_er(hass)
    climate_entity = er.async_get_or_create(
        suggested_object_id="selector_surface_climate",
        unique_id="selector_surface_climate",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=config_entry,
        capabilities={ATTR_PRESET_MODES: ["home"]},
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.CLIMATE_CONTROL,
        "feature_conf_climate_control",
    )

    assert result["type"] == FlowResultType.FORM
    selectors = _schema_selectors(result)
    assert CONF_CLIMATE_CONTROL_ENTITY_ID in selectors
    selector = selectors[CONF_CLIMATE_CONTROL_ENTITY_ID]
    assert selector.config["multiple"] is False
    include_entities = selector.config.get("include_entities", [])
    assert isinstance(include_entities, list)
    assert climate_entity.entity_id in include_entities


async def test_options_flow_fan_groups(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan groups flow stores required state and setpoint."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_cooling",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.EXTENDED],
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 25.0,
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    fan_options = config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.FAN_GROUPS
    ]
    assert fan_options[CONF_FAN_GROUPS_REQUIRED_STATE] == "extended"
    assert fan_options[CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS] == "temperature"
    assert fan_options[CONF_FAN_GROUPS_SETPOINT] == 25.0
    assert fan_options[CONF_FAN_GROUPS_CONTROLLERS][FanControllerRole.COOLING.value][
        CONF_FAN_CONTROLLER_ACTIVE_STATES
    ] == ["extended"]


async def test_options_flow_fan_groups_accepts_integer_setpoint(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan groups flow accepts integer setpoint input and persists float."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_cooling",
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.EXTENDED],
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 50,
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert (
        config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.FAN_GROUPS][
            "setpoint"
        ]
        == 50.0
    )


async def test_options_flow_fan_groups_reopen_preserves_saved_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan settings should reopen with saved values as suggested values."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_cooling",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.SLEEP],
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 55,
            CONF_FAN_CONTROLLER_HYSTERESIS: 2.5,
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_cooling",
    )
    assert result["type"] == FlowResultType.FORM
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_FAN_CONTROLLER_ACTIVE_STATES] == [
        AreaStates.SLEEP.value
    ]
    assert suggested_values[CONF_FAN_CONTROLLER_ON_THRESHOLD] == 55.0
    assert suggested_values[CONF_FAN_CONTROLLER_HYSTERESIS] == 2.5


async def test_options_flow_fan_groups_uses_constrained_selectors(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan automation fields should use HA selectors instead of raw inputs."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_cooling",
    )

    selectors = _schema_selectors(result)
    members_selector = selectors[CONF_FAN_CONTROLLER_MEMBERS]
    active_states_selector = selectors[CONF_FAN_CONTROLLER_ACTIVE_STATES]
    setpoint_selector = selectors[CONF_FAN_CONTROLLER_ON_THRESHOLD]
    unavailable_selector = selectors[CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR]
    detection_selector = selectors[CONF_FAN_CONTROLLER_DETECTION_MODE]

    assert members_selector.config["multiple"] is True
    assert active_states_selector.config["mode"] == "dropdown"
    assert active_states_selector.config["translation_key"] == "area_states"
    required_state_options = cast(
        list[str], active_states_selector.config["options"]
    )
    assert AreaStates.OCCUPIED.value in required_state_options
    assert AreaStates.SLEEP.value in required_state_options

    assert setpoint_selector.config["mode"] == "box"
    assert setpoint_selector.config["min"] == 0
    assert setpoint_selector.config["max"] == 120000
    assert setpoint_selector.config["step"] == 0.1
    assert unavailable_selector.config["translation_key"] == (
        "fan_sensor_unavailable_behavior"
    )
    assert detection_selector.config["translation_key"] == "fan_detection_mode"
    detection_options = cast(list[str], detection_selector.config["options"])
    assert FanDetectionMode.ROOM_STATE.value in detection_options


async def test_options_flow_fan_groups_stores_independent_controller_roles(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Fan role pages should persist independently and allow shared fans."""
    config_entry = init_integration
    er = async_get_er(hass)
    fan_entry = er.async_get_or_create(
        "fan",
        "test",
        "bathroom_fan",
        suggested_object_id="bathroom_fan",
    )
    sensor_entry = er.async_get_or_create(
        SENSOR_DOMAIN,
        "test",
        "bathroom_humidity",
        suggested_object_id="bathroom_humidity",
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_humidity",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_CONTROLLER_MEMBERS: [fan_entry.entity_id],
            CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: sensor_entry.entity_id,
            CONF_FAN_CONTROLLER_ON_THRESHOLD: 60,
            CONF_FAN_CONTROLLER_HYSTERESIS: 5,
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [
                AreaStates.OCCUPIED,
                AreaStates.EXTENDED,
            ],
            CONF_FAN_CONTROLLER_SUPPRESS_STATES: [AreaStates.SLEEP],
            CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.RUN_UNTIL_CLEAR,
            CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR: (
                FanSensorUnavailableBehavior.HOLD_THEN_CLEAR
            ),
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    humidity = config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.FAN_GROUPS
    ][CONF_FAN_GROUPS_CONTROLLERS][FanControllerRole.HUMIDITY.value]
    assert humidity[CONF_FAN_CONTROLLER_MEMBERS] == [fan_entry.entity_id]
    assert humidity[CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID] == sensor_entry.entity_id
    assert humidity[CONF_FAN_CONTROLLER_ON_THRESHOLD] == 60.0
    assert humidity[CONF_FAN_CONTROLLER_HYSTERESIS] == 5.0
    assert humidity[CONF_FAN_CONTROLLER_SUPPRESS_STATES] == ["sleep"]
    assert humidity[CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR] == "run_until_clear"


async def test_options_flow_fan_groups_stores_sensorless_odor_fallback(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Odor role should allow explicit room-state-only fallback without a sensor."""
    config_entry = init_integration
    er = async_get_er(hass)
    fan_entry = er.async_get_or_create(
        "fan",
        "test",
        "bathroom_fan",
        suggested_object_id="bathroom_fan",
    )
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.FAN_GROUPS,
        "feature_conf_fan_groups_odor",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FAN_CONTROLLER_MEMBERS: [fan_entry.entity_id],
            CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "",
            CONF_FAN_CONTROLLER_DETECTION_MODE: FanDetectionMode.ROOM_STATE.value,
            CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.OCCUPIED],
            CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: FanClearBehavior.OCCUPANCY_ONLY,
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    odor = config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.FAN_GROUPS][
        CONF_FAN_GROUPS_CONTROLLERS
    ][FanControllerRole.ODOR.value]
    assert odor[CONF_FAN_CONTROLLER_MEMBERS] == [fan_entry.entity_id]
    assert odor[CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID] == ""
    assert odor[CONF_FAN_CONTROLLER_DETECTION_MODE] == FanDetectionMode.ROOM_STATE.value
    assert odor[CONF_FAN_CONTROLLER_ACTIVE_STATES] == ["occupied"]


async def test_options_flow_area_aware_media_player_uses_entity_selector(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Area-aware media settings should select from media players only."""
    config_entry = init_integration
    er = async_get_er(hass)
    media_player_entity = er.async_get_or_create(
        suggested_object_id="selector_media_player",
        unique_id="selector_media_player",
        domain=MEDIA_PLAYER_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    sensor_entity = er.async_get_or_create(
        suggested_object_id="selector_sensor",
        unique_id="selector_sensor",
        domain=SENSOR_DOMAIN,
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
    selectors = _schema_selectors(result)
    notification_selector = selectors[CONF_NOTIFICATION_DEVICES]
    include_entities = cast(
        list[str], notification_selector.config["include_entities"]
    )

    assert notification_selector.config["multiple"] is True
    assert media_player_entity.entity_id in include_entities
    assert sensor_entity.entity_id not in include_entities


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    ] == {
        "notification_devices": ["media_player.test_media_player"],
        "notification_states": ["extended"],
    }


async def test_options_flow_area_aware_media_player_states_selector_and_reopen(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Notification states should use translated area-state choices and persist."""
    config_entry = init_integration
    er = async_get_er(hass)
    media_player_entity = er.async_get_or_create(
        suggested_object_id="reopen_media_player",
        unique_id="reopen_media_player",
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
    selectors = _schema_selectors(result)
    states_selector = selectors[CONF_NOTIFY_STATES]
    assert states_selector.config["multiple"] is True
    assert states_selector.config["translation_key"] == "area_states"
    state_options = cast(list[str], states_selector.config["options"])
    assert AreaStates.OCCUPIED.value in state_options
    assert AreaStates.SLEEP.value in state_options

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NOTIFICATION_DEVICES: [media_player_entity.entity_id],
            CONF_NOTIFY_STATES: [AreaStates.OCCUPIED.value, AreaStates.SLEEP.value],
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
        "feature_conf_area_aware_media_player",
    )
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_NOTIFICATION_DEVICES] == [
        media_player_entity.entity_id
    ]
    assert suggested_values[CONF_NOTIFY_STATES] == [
        AreaStates.OCCUPIED.value,
        AreaStates.SLEEP.value,
    ]


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
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


async def test_options_flow_aggregates_illuminance_threshold_allows_daylight_lux(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Aggregate illuminance threshold selector should allow realistic daylight values."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.AGGREGATES,
        "feature_conf_aggregates",
    )
    assert result["type"] == FlowResultType.FORM

    selectors = _schema_selectors(result)
    threshold_selector = selectors[CONF_AGGREGATES_ILLUMINANCE_THRESHOLD]

    assert threshold_selector.config["mode"] == "box"
    assert threshold_selector.config["unit_of_measurement"] == "lx"
    assert threshold_selector.config["max"] == 120000


async def test_options_flow_aggregates_reopen_preserves_saved_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Aggregate settings should reopen with saved thresholds and classes."""
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
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 1500,
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.AGGREGATES,
        "feature_conf_aggregates",
    )
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_AGGREGATES_MIN_ENTITIES] == 2
    assert suggested_values[CONF_AGGREGATES_ILLUMINANCE_THRESHOLD] == 1500.0


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.PRESENCE_HOLD
    ] == {"presence_hold_timeout": 10}


async def test_options_flow_presence_hold_uses_seconds_selector(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Presence hold timeout should render as a bounded seconds input."""
    result = await _open_feature_config_step(
        hass,
        init_integration,
        MagicAreasFeatures.PRESENCE_HOLD,
        "feature_conf_presence_hold",
    )
    selectors = _schema_selectors(result)
    timeout_selector = selectors[CONF_PRESENCE_HOLD_TIMEOUT]

    assert timeout_selector.config["mode"] == "box"
    assert timeout_selector.config["min"] == 0
    assert timeout_selector.config["max"] == 86400
    assert timeout_selector.config["unit_of_measurement"] == "seconds"


async def test_options_flow_presence_hold_reopen_preserves_timeout(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Presence hold timeout should reopen with the saved timeout value."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.PRESENCE_HOLD,
        "feature_conf_presence_hold",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_PRESENCE_HOLD_TIMEOUT: 42},
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.PRESENCE_HOLD,
        "feature_conf_presence_hold",
    )
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_PRESENCE_HOLD_TIMEOUT] == 42


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.BLE_TRACKER
    ] == {"ble_tracker_entities": ["sensor.test_sensor"]}


async def test_options_flow_ble_trackers_uses_sensor_selector(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """BLE tracker config should offer sensor entities, not arbitrary entities."""
    config_entry = init_integration
    er = async_get_er(hass)
    sensor_entity = er.async_get_or_create(
        suggested_object_id="ble_selector_sensor",
        unique_id="ble_selector_sensor",
        domain=SENSOR_DOMAIN,
        platform="test",
        config_entry=config_entry,
    )
    media_player_entity = er.async_get_or_create(
        suggested_object_id="ble_selector_media_player",
        unique_id="ble_selector_media_player",
        domain=MEDIA_PLAYER_DOMAIN,
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
    selectors = _schema_selectors(result)
    tracker_selector = selectors[CONF_BLE_TRACKER_ENTITIES]
    include_entities = cast(list[str], tracker_selector.config["include_entities"])

    assert tracker_selector.config["multiple"] is True
    assert sensor_entity.entity_id in include_entities
    assert media_player_entity.entity_id not in include_entities


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.WASP_IN_A_BOX
    ] == {
        "delay": 60,
        "wasp_timeout": 5,
        "wasp_device_classes": ["motion", "occupancy"],
    }


async def test_options_flow_wasp_in_a_box_uses_number_and_class_selectors(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Wasp settings should use numeric selectors and multi-select device classes."""
    result = await _open_feature_config_step(
        hass,
        init_integration,
        MagicAreasFeatures.WASP_IN_A_BOX,
        "feature_conf_wasp_in_a_box",
    )
    selectors = _schema_selectors(result)
    delay_selector = selectors[CONF_WASP_IN_A_BOX_DELAY]
    timeout_selector = selectors[CONF_WASP_IN_A_BOX_WASP_TIMEOUT]
    class_selector = selectors[CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES]

    assert delay_selector.config["mode"] == "box"
    assert delay_selector.config["min"] == 0
    assert delay_selector.config["max"] == 86400
    assert delay_selector.config["unit_of_measurement"] == "seconds"
    assert timeout_selector.config["mode"] == "box"
    assert timeout_selector.config["min"] == 0
    assert timeout_selector.config["max"] == 1440
    assert timeout_selector.config["unit_of_measurement"] == "minutes"
    assert class_selector.config["multiple"] is True


async def test_options_flow_wasp_in_a_box_reopen_preserves_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Wasp settings should reopen with saved delay, timeout, and device classes."""
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
            CONF_WASP_IN_A_BOX_DELAY: 30,
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT: 12,
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES: ["motion", "presence"],
        },
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.WASP_IN_A_BOX,
        "feature_conf_wasp_in_a_box",
    )
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_WASP_IN_A_BOX_DELAY] == 30
    assert suggested_values[CONF_WASP_IN_A_BOX_WASP_TIMEOUT] == 12
    assert suggested_values[CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES] == [
        "motion",
        "presence",
    ]


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
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.HEALTH] == {
        "health_binary_sensor_device_classes": ["problem", "smoke"]
    }


async def test_options_flow_health_selector_and_reopen_preserves_classes(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Health device classes should use multi-select and persist."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.HEALTH,
        "feature_conf_health",
    )
    selectors = _schema_selectors(result)
    class_selector = selectors[CONF_HEALTH_SENSOR_DEVICE_CLASSES]
    assert class_selector.config["multiple"] is True
    class_options = cast(list[str], class_selector.config["options"])
    assert BinarySensorDeviceClass.PROBLEM in class_options
    assert BinarySensorDeviceClass.SMOKE in class_options

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem", "smoke"]},
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.HEALTH,
        "feature_conf_health",
    )
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_HEALTH_SENSOR_DEVICE_CLASSES] == [
        "problem",
        "smoke",
    ]


async def test_options_flow_light_groups_advisory_shows_binary_fields_only(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Advisory mode should expose inside/outside bright binaries but hide adaptive-only fields."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_brightness",
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
    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY in keys


async def test_options_flow_light_groups_inside_bright_defaults_to_threshold_sensor(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Inside bright entity should default to MA threshold binary helper when present."""
    config_entry = init_integration
    entity_registry = async_get_er(hass)
    threshold_unique_id = build_threshold_light_sensor_unique_id(
        area_id=str(config_entry.unique_id),
    )
    threshold_entry = entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        threshold_unique_id,
        suggested_object_id="magic_areas_threshold_test_threshold_light",
    )

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_brightness",
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups_brightness"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"brightness_mode": "advisory"},
    )
    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    marker = next(
        marker
        for marker in schema.schema
        if getattr(marker, "schema", marker) == CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY
    )
    assert marker.default() == threshold_entry.entity_id


async def test_options_flow_light_groups_uses_translated_selectors(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Light-group selectors should show translated state and trigger labels."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_roles",
    )
    assert result["type"] == FlowResultType.FORM

    schema = _data_schema(result)
    selectors = {
        getattr(marker, "schema", marker): selector
        for marker, selector in schema.schema.items()
    }

    assert (
        selectors[CONF_OVERHEAD_LIGHTS_STATES].config["translation_key"]
        == "area_states"
    )
    assert (
        selectors[CONF_OVERHEAD_LIGHTS_ACT_ON].config["translation_key"]
        == "control_on"
    )


async def test_options_flow_light_groups_mode_selectors_use_dropdowns(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Mode selection should stay compact and translated for the frontend."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_brightness",
    )
    assert result["type"] == FlowResultType.FORM
    selectors = _schema_selectors(result)

    brightness_selector = selectors["brightness_mode"]
    assert brightness_selector.config["mode"] == "dropdown"
    assert brightness_selector.config["translation_key"] == "light_brightness_mode"

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_adaptive_lighting",
    )
    assert result["type"] == FlowResultType.FORM
    selectors = _schema_selectors(result)

    adaptive_lighting_selector = selectors[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE]
    assert adaptive_lighting_selector.config["mode"] == "dropdown"
    assert (
        adaptive_lighting_selector.config["translation_key"]
        == "adaptive_lighting_mode"
    )


async def test_options_flow_light_groups_adaptive_shows_binary_and_lux_fields(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Adaptive mode should expose advisory and adaptive-only controls."""
    config_entry = init_integration
    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    assert result["type"] == FlowResultType.FORM

    result = await _select_light_groups_brightness_mode(
        hass, result, "adaptive"
    )
    assert result["type"] == FlowResultType.FORM

    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY in keys
    assert CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS in keys
    assert CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY in keys


async def test_options_flow_light_groups_mode_fields_do_not_leak_after_reopen(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Reopening after a mode change should render only fields for the saved mode."""
    config_entry = init_integration
    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    result = await _select_light_groups_brightness_mode(hass, result, "adaptive")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: ""},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    assert result["type"] == FlowResultType.FORM
    result = await _select_light_groups_brightness_mode(hass, result, "adaptive")
    adaptive_keys = {getattr(marker, "schema", marker) for marker in _data_schema(result).schema}
    assert CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS in adaptive_keys
    assert CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY in adaptive_keys

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_light_groups_brightness"}
    )
    result = await _select_light_groups_brightness_mode(hass, result, "advisory")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: ""},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU

    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    assert result["type"] == FlowResultType.FORM
    result = await _select_light_groups_brightness_mode(hass, result, "advisory")
    advisory_keys = {
        getattr(marker, "schema", marker) for marker in _data_schema(result).schema
    }
    assert CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY in advisory_keys
    assert CONF_LIGHT_GROUP_OUTSIDE_BRIGHT_ENTITY in advisory_keys
    assert CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS not in advisory_keys
    assert CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY not in advisory_keys


async def test_options_flow_light_groups_adaptive_selectors_are_lux_safe(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Adaptive lux selectors should expose only illuminance entities with realistic ranges."""
    config_entry = init_integration
    hass.states.async_set(
        "sensor.outdoor_lux",
        "1200",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE},
    )
    hass.states.async_set(
        "sensor.living_room_temperature",
        "72",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE},
    )
    hass.states.async_set(
        "binary_sensor.daylight_flag",
        "on",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    result = await _select_light_groups_brightness_mode(hass, result, "adaptive")
    assert result["type"] == FlowResultType.FORM
    selectors = _schema_selectors(result)

    outside_lux_selector = selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY]
    inside_lux_selector = selectors[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY]
    for selector in (outside_lux_selector, inside_lux_selector):
        include_entities = cast(list[str], selector.config["include_entities"])
        assert "sensor.outdoor_lux" in include_entities
        assert "sensor.living_room_temperature" not in include_entities
        assert "binary_sensor.daylight_flag" not in include_entities

    assert (
        selectors[CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE].config["translation_key"]
        == "light_outside_context_source"
    )
    for key in (
        CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
        CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
        CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    ):
        selector = selectors[key]
        assert selector.config["mode"] == "box"
        assert selector.config["unit_of_measurement"] == "lx"
        assert selector.config["max"] == 120000


async def test_options_flow_light_groups_adaptive_lux_accepts_bright_outdoor_values(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Adaptive outside-lux threshold should allow realistic daylight values."""
    config_entry = init_integration
    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    result = await _select_light_groups_brightness_mode(hass, result, "adaptive")

    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    marker = next(
        marker
        for marker in schema.schema
        if getattr(marker, "schema", marker) == CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN
    )
    validator = schema.schema[marker]

    assert validator(12000) == 12000.0


async def test_options_flow_light_groups_adaptive_lighting_ignore_hides_pairings(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Ignore mode should expose only the AL mode selector, not pairing fields."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_adaptive_lighting",
    )

    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE in keys
    assert adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS) not in keys


async def test_options_flow_light_groups_root_shows_substep_menu(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Light groups should open as task-focused substeps instead of a flat form."""
    result = await _open_feature_config_step(
        hass,
        init_integration,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups",
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "feature_conf_light_groups"
    assert result["menu_options"] == [
        "feature_conf_light_groups_roles",
        "feature_conf_light_groups_brightness",
        "feature_conf_light_groups_adaptive_lighting",
        "show_menu",
    ]


async def test_options_flow_light_groups_roles_preserve_hidden_behavior_modes(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Role edits should not drop brightness or Adaptive Lighting mode choices."""
    config_entry = init_integration
    new_options = config_entry.options.copy()
    new_options.setdefault(CONF_ENABLED_FEATURES, {})
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {
        "brightness_mode": "adaptive",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ),
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL: True,
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_roles",
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"overhead_lights": ["light.test_light"]},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)

    feature_options = config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS
    ]
    assert result["type"] == FlowResultType.MENU
    assert feature_options["brightness_mode"] == "adaptive"
    assert (
        feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE]
        == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
    )
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is True


async def test_options_flow_light_groups_brightness_preserves_hidden_roles(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Brightness edits should not drop hidden role membership."""
    config_entry = init_integration
    new_options = config_entry.options.copy()
    new_options.setdefault(CONF_ENABLED_FEATURES, {})
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS] = {
        "overhead_lights": ["light.test_light"],
        "overhead_lights_states": ["occupied"],
        "overhead_lights_act_on": ["occupancy", "state"],
        "brightness_mode": "inhibit",
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_brightness",
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"brightness_mode": "advisory"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: ""},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)

    feature_options = config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS
    ]
    assert result["type"] == FlowResultType.MENU
    assert feature_options["brightness_mode"] == "advisory"
    assert feature_options["overhead_lights"] == ["light.test_light"]
    assert feature_options["overhead_lights_states"] == ["occupied"]
    assert feature_options["overhead_lights_act_on"] == ["occupancy", "state"]


async def test_options_flow_light_groups_adaptive_lighting_pairings_do_not_leak(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Dynamic AL pairing fields should not leak after switching back to ignore."""
    config_entry = init_integration
    _register_adaptive_lighting_switch_set(
        hass,
        "Kitchen Overhead",
        area_id="kitchen",
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

    result = await _open_existing_light_groups_adaptive_lighting_step(
        hass, config_entry
    )

    assert result["type"] == FlowResultType.FORM
    pair_key = adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS)
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert pair_key in keys

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: "ignore",
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups_adaptive_lighting"},
    )

    assert result["type"] == FlowResultType.FORM
    schema = _data_schema(result)
    keys = {getattr(marker, "schema", marker) for marker in schema.schema}
    assert pair_key not in keys


async def test_options_flow_dynamic_pairings_do_not_mutate_light_group_schema(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Dynamic AL pairing fields should not be added to the canonical schema."""
    config_entry = init_integration
    _register_adaptive_lighting_switch_set(
        hass,
        "Kitchen Overhead",
        area_id="kitchen",
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

    pair_key = adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS)
    before_keys = {
        getattr(marker, "schema", marker) for marker in LIGHT_GROUP_FEATURE_SCHEMA.schema
    }
    assert pair_key not in before_keys

    result = await _open_existing_light_groups_adaptive_lighting_step(
        hass, config_entry
    )

    assert result["type"] == FlowResultType.FORM
    rendered_keys = {
        getattr(marker, "schema", marker)
        for marker in _data_schema(result).schema
    }
    assert pair_key in rendered_keys
    after_keys = {
        getattr(marker, "schema", marker) for marker in LIGHT_GROUP_FEATURE_SCHEMA.schema
    }
    assert pair_key not in after_keys


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

    result = await _open_existing_light_groups_adaptive_lighting_step(
        hass, config_entry
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
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
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
    new_options[CONF_ENABLED_FEATURES] = dict(
        new_options.get(CONF_ENABLED_FEATURES, {})
    )
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS.value] = {
        "overhead_lights": ["light.test_light"],
        "brightness_mode": "inhibit",
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
            LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ),
    }
    hass.config_entries.async_update_entry(config_entry, options=new_options)
    await hass.async_block_till_done()

    result = await _open_existing_light_groups_adaptive_lighting_step(
        hass, config_entry
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
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert config_entry.options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS][
        CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES
    ] == [CONF_OVERHEAD_LIGHTS]


async def test_options_flow_light_groups_manage_immediately_reveals_targets(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Selecting manage mode should stay on the step and reveal target fields."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_roles",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_OVERHEAD_LIGHTS: ["light.test_light"],
            CONF_SLEEP_LIGHTS: ["light.sleep_light"],
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups_adaptive_lighting"},
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            ),
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups_adaptive_lighting"
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
    assert role_marker.default() == [CONF_OVERHEAD_LIGHTS, CONF_SLEEP_LIGHTS]


async def test_options_flow_light_groups_manage_defaults_to_configured_roles(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Manage mode should default to configured role groups instead of no-op."""
    config_entry = init_integration
    result = await _open_feature_config_step(
        hass,
        config_entry,
        MagicAreasFeatures.LIGHT_GROUPS,
        "feature_conf_light_groups_roles",
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_OVERHEAD_LIGHTS: ["light.test_light"],
            CONF_SLEEP_LIGHTS: ["light.sleep_light"],
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": "feature_conf_light_groups_adaptive_lighting"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            ),
        },
    )

    assert result["type"] == FlowResultType.FORM
    role_marker = next(
        marker
        for marker in _data_schema(result).schema
        if getattr(marker, "schema", marker)
        == CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES
    )
    assert role_marker.default() == [CONF_OVERHEAD_LIGHTS, CONF_SLEEP_LIGHTS]


async def test_options_flow_light_groups_manage_all_lights_uses_separate_gate(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Manage mode should expose all-lights as a boolean, not a role option."""
    config_entry = init_integration
    new_options = config_entry.options.copy()
    new_options[CONF_ENABLED_FEATURES] = dict(
        new_options.get(CONF_ENABLED_FEATURES, {})
    )
    new_options[CONF_ENABLED_FEATURES][MagicAreasFeatures.LIGHT_GROUPS.value] = {
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
        "feature_conf_light_groups_adaptive_lighting",
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
        result["flow_id"], user_input={"next_step_id": "show_menu"}
    )
    result = await _finish_options_flow(hass, result)

    feature_options = config_entry.options[CONF_ENABLED_FEATURES][
        MagicAreasFeatures.LIGHT_GROUPS
    ]
    assert result["type"] == FlowResultType.MENU
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

    result = await _open_light_groups_brightness_mode_step(hass, config_entry)
    result = await _select_light_groups_brightness_mode(hass, result, "inhibit")
    assert result["type"] == FlowResultType.MENU
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
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
    assert result["type"] == FlowResultType.MENU

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
        result["flow_id"],
        user_input={
            MagicAreasFeatures.LIGHT_GROUPS: True,
            MagicAreasFeatures.COVER_GROUPS: True,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert "feature_conf_light_groups" in result["menu_options"]
    assert "feature_conf_cover_groups" not in result["menu_options"]
    assert result["type"] == FlowResultType.MENU
    assert (
        MagicAreasFeatures.LIGHT_GROUPS in config_entry.options[CONF_ENABLED_FEATURES]
    )
    assert (
        MagicAreasFeatures.COVER_GROUPS in config_entry.options[CONF_ENABLED_FEATURES]
    )


@pytest.mark.parametrize(
    "feature",
    [
        MagicAreasFeatures.COVER_GROUPS,
        MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
    ],
)
async def test_options_flow_helper_only_features_enable_without_config_menu(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
) -> None:
    """Native helper-only features should enable without dead config menu entries."""
    config_entry = init_integration
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_features"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={feature: True},
    )

    assert result["type"] == FlowResultType.MENU
    assert f"feature_conf_{feature.value}" not in result["menu_options"]
    result = await _finish_options_flow(hass, result)
    assert result["type"] == FlowResultType.MENU
    assert feature in config_entry.options[CONF_ENABLED_FEATURES]


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
