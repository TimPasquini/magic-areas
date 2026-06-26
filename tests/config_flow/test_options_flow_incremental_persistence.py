"""Options-flow tests for incremental persistence and guided completion."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast
from unittest.mock import patch

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODES,
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.entity_registry import async_get as async_get_er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_ENABLED_FEATURES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_BLE_TRACKER_ENTITIES,
)
from custom_components.magic_areas.core.control_intents import (
    adaptive_lighting_switch_entity_ids,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
    LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT,
    adaptive_lighting_pair_key,
)


async def _start_options(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> ConfigFlowResult:
    """Start an options flow."""
    return await hass.config_entries.options.async_init(config_entry.entry_id)


async def _choose(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    step_id: str,
) -> ConfigFlowResult:
    """Choose a menu step without auto-entering child settings pages."""
    return await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": step_id}
    )


async def _enable_feature(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    feature: MagicAreasFeatures,
) -> ConfigFlowResult:
    """Enable a feature and return the refreshed root menu."""
    result = await _start_options(hass, config_entry)
    result = await _choose(hass, result, "select_features")
    return await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={feature: True}
    )


def _register_adaptive_lighting_switch_set(
    hass: HomeAssistant,
    name: str,
    *,
    area_id: str,
) -> dict[str, str]:
    """Register one same-area Adaptive Lighting switch set."""
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


def _feature_options(
    config_entry: MockConfigEntry,
    feature: MagicAreasFeatures,
) -> Mapping[str, object]:
    """Return saved feature options regardless of enum/string key normalization."""
    features = cast(
        Mapping[MagicAreasFeatures | str, Mapping[str, object]],
        config_entry.options.get(CONF_ENABLED_FEATURES, {}),
    )
    return features.get(feature, features.get(feature.value, {}))


@pytest.mark.parametrize(
    ("step_id", "expected_step_id"),
    [
        ("area_config", "area_config"),
        ("presence_tracking", "presence_tracking"),
        ("secondary_states", "secondary_states"),
        ("custom_control_groups", "custom_control_groups"),
    ],
)
async def test_root_single_page_sections_open_forms_directly(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    step_id: str,
    expected_step_id: str,
) -> None:
    """Root sections with one config page should not add Settings-only menus."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, step_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == expected_step_id


@pytest.mark.parametrize(
    ("step_id", "user_input", "asserted_key", "asserted_value"),
    [
        ("area_config", {CONF_TYPE: AreaType.EXTERIOR}, CONF_TYPE, AreaType.EXTERIOR),
        (
            "presence_tracking",
            {CONF_CLEAR_TIMEOUT: 6, CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"]},
            CONF_CLEAR_TIMEOUT,
            6,
        ),
        (
            "secondary_states",
            {CONF_SLEEP_TIMEOUT: 4},
            f"{CONF_SECONDARY_STATES}.{CONF_SLEEP_TIMEOUT}",
            4,
        ),
        (
            "custom_control_groups",
            {CONF_CUSTOM_CONTROL_GROUPS: []},
            CONF_CUSTOM_CONTROL_GROUPS,
            [],
        ),
    ],
)
async def test_root_single_page_submit_persists_immediately_and_returns_to_root(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    step_id: str,
    user_input: dict[str, object],
    asserted_key: str,
    asserted_value: object,
) -> None:
    """Completed root pages should save on submit, without waiting for Done."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, step_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=user_input
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"
    if "." in asserted_key:
        parent, child = asserted_key.split(".", 1)
        assert config_entry_value(init_integration, parent, child) == asserted_value
    else:
        assert init_integration.options[asserted_key] == asserted_value


async def test_complete_page_submit_persists_with_async_update_entry(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Completed pages should persist through HA's config-entry update API."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "area_config")
    assert result["type"] == FlowResultType.FORM

    with patch.object(
        hass.config_entries,
        "async_update_entry",
        wraps=hass.config_entries.async_update_entry,
    ) as update_entry:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_TYPE: AreaType.EXTERIOR}
        )

    assert result["type"] == FlowResultType.MENU
    update_entry.assert_called()
    assert update_entry.call_args.kwargs["options"][CONF_TYPE] == AreaType.EXTERIOR


async def test_root_menu_has_no_final_save_operation(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Submitted pages should save without exposing a confusing Done prompt."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "area_config")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_TYPE: AreaType.EXTERIOR}
    )

    assert result["type"] == FlowResultType.MENU
    assert init_integration.options[CONF_TYPE] == AreaType.EXTERIOR
    assert "finish" not in result["menu_options"]
    assert init_integration.options[CONF_TYPE] == AreaType.EXTERIOR


async def test_reopen_after_submit_shows_persisted_values_as_suggestions(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """A submitted page should reopen with persisted values before Done is selected."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "presence_tracking")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CLEAR_TIMEOUT: 6,
            CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"],
        },
    )
    assert result["type"] == FlowResultType.MENU

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "presence_tracking")

    assert result["type"] == FlowResultType.FORM
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_CLEAR_TIMEOUT] == 6
    assert suggested_values[CONF_PRESENCE_DEVICE_PLATFORMS] == ["binary_sensor"]


def config_entry_value(
    config_entry: MockConfigEntry,
    parent: str,
    child: str,
) -> object:
    """Return a nested config-entry option value."""
    nested = cast(Mapping[str, object], config_entry.options[parent])
    return nested[child]


def _schema_suggested_values(result: ConfigFlowResult) -> dict[str, object]:
    """Return suggested values keyed by config key from a form result."""
    schema = cast(vol.Schema, result["data_schema"])
    return {
        getattr(marker, "schema", marker): marker.description["suggested_value"]
        for marker in schema.schema
    }


async def test_submitted_page_survives_abandoned_later_flow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """A later unsubmitted form should not lose an already submitted page."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "area_config")
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_TYPE: AreaType.EXTERIOR}
    )
    assert result["type"] == FlowResultType.MENU

    result = await _choose(hass, result, "presence_tracking")
    assert result["type"] == FlowResultType.FORM
    # Simulate frontend close/X by abandoning this active flow without submitting it.
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "area_config")

    assert init_integration.options[CONF_TYPE] == AreaType.EXTERIOR
    assert result["type"] == FlowResultType.FORM


async def test_validation_failure_does_not_persist_partial_page(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Failed form validation should stay on the form and not save bad values."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "custom_control_groups")
    assert result["type"] == FlowResultType.FORM

    submitted_groups = [
        {
            "group_id": "control.duplicate",
            "members": ["light.one"],
            "trigger_states": ["occupied"],
            "policy_id": "custom_control_group",
        },
        {
            "group_id": "control.duplicate",
            "members": ["light.two"],
            "trigger_states": ["sleep"],
            "policy_id": "custom_control_group",
        },
    ]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CUSTOM_CONTROL_GROUPS: submitted_groups},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_CUSTOM_CONTROL_GROUPS] == submitted_groups
    assert init_integration.options.get(CONF_CUSTOM_CONTROL_GROUPS, []) == []


async def test_feature_selection_persists_immediately_and_refreshes_menu(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Feature selection is a complete page and should save on submit."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "select_features")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            MagicAreasFeatures.LIGHT_GROUPS: True,
            MagicAreasFeatures.HEALTH: True,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert "feature_conf_light_groups" in cast(list[str], result["menu_options"])
    assert "feature_conf_health" in cast(list[str], result["menu_options"])
    features = cast(
        Mapping[MagicAreasFeatures | str, object],
        init_integration.options[CONF_ENABLED_FEATURES],
    )
    assert (
        MagicAreasFeatures.LIGHT_GROUPS in features
        or MagicAreasFeatures.LIGHT_GROUPS.value in features
    )
    assert (
        MagicAreasFeatures.HEALTH in features
        or MagicAreasFeatures.HEALTH.value in features
    )


@pytest.mark.parametrize(
    "feature",
    [
        MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
    ],
)
async def test_helper_only_features_persist_without_dead_config_menu_paths(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
) -> None:
    """Helper-only features should save immediately without adding dead menu entries."""
    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "select_features")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={feature: True},
    )

    assert result["type"] == FlowResultType.MENU
    assert f"feature_conf_{feature.value}" not in cast(
        list[str], result["menu_options"]
    )
    features = cast(
        Mapping[MagicAreasFeatures | str, object],
        init_integration.options[CONF_ENABLED_FEATURES],
    )
    assert feature in features or feature.value in features


@pytest.mark.parametrize(
    ("feature", "step_id", "user_input", "expected_key", "expected_value"),
    [
        (
            MagicAreasFeatures.HEALTH,
            "feature_conf_health",
            {CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]},
            CONF_HEALTH_SENSOR_DEVICE_CLASSES,
            ["problem"],
        ),
        (
            MagicAreasFeatures.AGGREGATES,
            "feature_conf_aggregates",
            {CONF_AGGREGATES_MIN_ENTITIES: 2},
            CONF_AGGREGATES_MIN_ENTITIES,
            2,
        ),
        (
            MagicAreasFeatures.PRESENCE_HOLD,
            "feature_conf_presence_hold",
            {CONF_PRESENCE_HOLD_TIMEOUT: 30},
            CONF_PRESENCE_HOLD_TIMEOUT,
            30,
        ),
        (
            MagicAreasFeatures.WASP_IN_A_BOX,
            "feature_conf_wasp_in_a_box",
            {CONF_WASP_IN_A_BOX_DELAY: 30},
            CONF_WASP_IN_A_BOX_DELAY,
            30,
        ),
    ],
)
async def test_single_page_feature_submit_persists_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    feature: MagicAreasFeatures,
    step_id: str,
    user_input: dict[str, object],
    expected_key: str,
    expected_value: object,
) -> None:
    """Simple feature forms should save immediately on successful submit."""
    result = await _enable_feature(hass, init_integration, feature)
    result = await _choose(hass, result, step_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=user_input
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"
    assert _feature_options(init_integration, feature)[expected_key] == expected_value


async def test_ble_tracker_single_page_submit_persists_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """BLE tracker settings are a single page and should save on submit."""
    er = async_get_er(hass)
    sensor_entity = er.async_get_or_create(
        suggested_object_id="incremental_ble_tracker",
        unique_id="incremental_ble_tracker",
        domain=SENSOR_DOMAIN,
        platform="test",
        config_entry=init_integration,
    )
    await hass.async_block_till_done()

    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.BLE_TRACKER
    )
    result = await _choose(hass, result, "feature_conf_ble_trackers")
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_BLE_TRACKER_ENTITIES: [sensor_entity.entity_id]},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"
    assert _feature_options(init_integration, MagicAreasFeatures.BLE_TRACKER)[
        CONF_BLE_TRACKER_ENTITIES
    ] == [sensor_entity.entity_id]


async def test_area_aware_media_player_single_page_submit_persists_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Area-aware media settings are a single page and should save on submit."""
    er = async_get_er(hass)
    media_player_entity = er.async_get_or_create(
        suggested_object_id="incremental_media_player",
        unique_id="incremental_media_player",
        domain=MEDIA_PLAYER_DOMAIN,
        platform="test",
        config_entry=init_integration,
    )
    await hass.async_block_till_done()

    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    )
    result = await _choose(hass, result, "feature_conf_area_aware_media_player")
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NOTIFICATION_DEVICES: [media_player_entity.entity_id],
            CONF_NOTIFY_STATES: ["extended"],
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "show_menu"
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    )
    assert feature_options[CONF_NOTIFICATION_DEVICES] == [media_player_entity.entity_id]
    assert feature_options[CONF_NOTIFY_STATES] == ["extended"]


async def test_climate_entity_selection_advances_without_persisting(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Climate entity selection is not complete until preset mapping submits."""
    er = async_get_er(hass)
    climate_entity = er.async_get_or_create(
        suggested_object_id="guided_climate",
        unique_id="guided_climate",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=init_integration,
        capabilities={ATTR_PRESET_MODES: ["home", "away"]},
    )
    await hass.async_block_till_done()

    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.CLIMATE_CONTROL
    )
    result = await _choose(hass, result, "feature_conf_climate_control")
    assert result["type"] == FlowResultType.MENU
    result = await _choose(hass, result, "feature_conf_climate_control_settings")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_climate_control_select_presets"
    assert _feature_options(init_integration, MagicAreasFeatures.CLIMATE_CONTROL) == {}


async def test_abandoning_incomplete_climate_guided_flow_does_not_persist(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Abandoning climate before preset mapping should not save partial config."""
    er = async_get_er(hass)
    climate_entity = er.async_get_or_create(
        suggested_object_id="abandoned_climate",
        unique_id="abandoned_climate",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=init_integration,
        capabilities={ATTR_PRESET_MODES: ["home", "away"]},
    )
    await hass.async_block_till_done()

    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.CLIMATE_CONTROL
    )
    result = await _choose(hass, result, "feature_conf_climate_control")
    result = await _choose(hass, result, "feature_conf_climate_control_settings")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: climate_entity.entity_id},
    )
    assert result["step_id"] == "feature_conf_climate_control_select_presets"

    # Simulate frontend close/X before the guided preset page is submitted.
    await _start_options(hass, init_integration)

    assert _feature_options(init_integration, MagicAreasFeatures.CLIMATE_CONTROL) == {}


async def test_climate_preset_mapping_submit_persists_feature(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Climate preset mapping is the climate feature completion boundary."""
    er = async_get_er(hass)
    climate_entity = er.async_get_or_create(
        suggested_object_id="persist_climate",
        unique_id="persist_climate",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=init_integration,
        capabilities={ATTR_PRESET_MODES: ["home", "away"]},
    )
    await hass.async_block_till_done()

    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.CLIMATE_CONTROL
    )
    result = await _choose(hass, result, "feature_conf_climate_control")
    result = await _choose(hass, result, "feature_conf_climate_control_settings")
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

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.CLIMATE_CONTROL
    )
    assert feature_options[CONF_CLIMATE_CONTROL_ENTITY_ID] == climate_entity.entity_id
    assert feature_options[CONF_CLIMATE_CONTROL_PRESET_OCCUPIED] == "home"
    assert feature_options[CONF_CLIMATE_CONTROL_PRESET_CLEAR] == "away"


async def test_changing_climate_entity_forces_preset_remapping_before_persistence(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Changing climate entity should not persist until presets are remapped."""
    er = async_get_er(hass)
    first = er.async_get_or_create(
        suggested_object_id="first_climate",
        unique_id="first_climate",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=init_integration,
        capabilities={ATTR_PRESET_MODES: ["home", "away"]},
    )
    second = er.async_get_or_create(
        suggested_object_id="second_climate",
        unique_id="second_climate",
        domain=CLIMATE_DOMAIN,
        platform="test",
        config_entry=init_integration,
        capabilities={ATTR_PRESET_MODES: ["comfort", "eco"]},
    )
    existing_options = dict(init_integration.options)
    existing_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            CONF_CLIMATE_CONTROL_ENTITY_ID: first.entity_id,
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: "home",
            CONF_CLIMATE_CONTROL_PRESET_CLEAR: "away",
        }
    }
    hass.config_entries.async_update_entry(init_integration, options=existing_options)
    await hass.async_block_till_done()

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "feature_conf_climate_control")
    result = await _choose(hass, result, "feature_conf_climate_control_settings")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CLIMATE_CONTROL_ENTITY_ID: second.entity_id},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_climate_control_select_presets"
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.CLIMATE_CONTROL
    )
    assert feature_options[CONF_CLIMATE_CONTROL_ENTITY_ID] == first.entity_id


async def test_light_group_roles_submit_persists_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Light role membership has complete defaults and should save immediately."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_roles")
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_OVERHEAD_LIGHTS: ["light.test_light"]}
    )

    assert result["type"] == FlowResultType.MENU
    assert _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS)[
        CONF_OVERHEAD_LIGHTS
    ] == ["light.test_light"]


async def test_light_group_classic_brightness_persists_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Classic brightness behavior has no dependent settings page."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "feature_conf_light_groups"
    assert (
        _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS)[
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE
        ]
        == LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT
    )


@pytest.mark.parametrize(
    ("mode", "expected_step_id"),
    [
        (
            LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            "feature_conf_light_groups_brightness_advisory",
        ),
        (
            LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
            "feature_conf_light_groups_brightness_adaptive",
        ),
    ],
)
async def test_light_group_brightness_dependent_modes_advance_without_persisting(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mode: str,
    expected_step_id: str,
) -> None:
    """Advisory and Adaptive modes should save only after dependent settings submit."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_LIGHT_GROUP_BRIGHTNESS_MODE: mode},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == expected_step_id
    assert (
        _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS).get(
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE
        )
        != mode
    )


async def test_light_group_advisory_settings_submit_persists_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Advisory settings submit is the Advisory brightness completion boundary."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: "binary_sensor.room_bright"},
    )

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_BRIGHTNESS_MODE]
        == LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY]
        == "binary_sensor.room_bright"
    )


async def test_light_group_adaptive_settings_submit_persists_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Adaptive settings submit is the Adaptive brightness completion boundary."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: "binary_sensor.room_bright",
            CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS: 45,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN: 1200.0,
        },
    )

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_BRIGHTNESS_MODE]
        == LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
    )
    assert feature_options[CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY] == (
        "binary_sensor.room_bright"
    )
    assert feature_options[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] == 45
    assert feature_options[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] == 1200.0


async def test_brightness_dependent_mode_validation_failure_stays_on_form(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Invalid dependent brightness settings should not save partial mode config."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS: -1,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN: 1200.0,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups_brightness_adaptive"
    assert result["errors"]
    assert (
        _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS).get(
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE
        )
        != LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
    )


async def test_switching_brightness_modes_preserves_dormant_adaptive_settings(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Switching away from Adaptive should hide, not delete, Adaptive settings."""
    existing_options = dict(init_integration.options)
    existing_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
            CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: "binary_sensor.room_bright",
            CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS: 45,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN: 1200.0,
        }
    }
    hass.config_entries.async_update_entry(init_integration, options=existing_options)
    await hass.async_block_till_done()

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: "binary_sensor.room_bright"},
    )

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_BRIGHTNESS_MODE]
        == LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY
    )
    assert feature_options[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] == 45
    assert feature_options[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] == 1200.0


async def test_switching_adaptive_to_classic_preserves_dormant_adaptive_settings(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Switching from Adaptive to Classic should hide, not delete, Adaptive settings."""
    existing_options = dict(init_integration.options)
    existing_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
            CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: "binary_sensor.room_bright",
            CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS: 45,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN: 1200.0,
        }
    }
    hass.config_entries.async_update_entry(init_integration, options=existing_options)
    await hass.async_block_till_done()

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT
        },
    )

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_BRIGHTNESS_MODE]
        == LIGHT_GROUP_BRIGHTNESS_MODE_INHIBIT
    )
    assert feature_options[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] == 45
    assert feature_options[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] == 1200.0


async def test_switching_back_to_adaptive_restores_dormant_adaptive_values(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Dormant Adaptive values should be suggested when Adaptive is selected again."""
    existing_options = dict(init_integration.options)
    existing_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
            CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: "binary_sensor.room_bright",
            CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS: 45,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN: 1200.0,
        }
    }
    hass.config_entries.async_update_entry(init_integration, options=existing_options)
    await hass.async_block_till_done()

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_brightness")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups_brightness_adaptive"
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] == 45
    assert suggested_values[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] == 1200.0


async def test_adaptive_lighting_ignore_persists_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Adaptive Lighting ignore mode has no dependent role/pairing page."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
            )
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert (
        _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS)[
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE
        ]
        == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
    )


async def test_adaptive_lighting_manage_mode_advances_without_persisting(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Managed Adaptive Lighting should persist only after managed targets submit."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_roles")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_OVERHEAD_LIGHTS: ["light.test_light"]}
    )
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            )
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_light_groups_adaptive_lighting"
    assert (
        _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS).get(
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE
        )
        != LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
    )


async def test_adaptive_lighting_manage_targets_submit_persists_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Managed Adaptive Lighting target selection completes the managed subflow."""
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_roles")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_OVERHEAD_LIGHTS: ["light.test_light"]}
    )
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            )
        },
    )
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

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE]
        == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
    )
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is True
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] == [
        CONF_OVERHEAD_LIGHTS
    ]


async def test_adaptive_lighting_mode_switch_preserves_dormant_manage_settings(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Switching AL to ignore should hide, not delete, useful manage settings."""
    existing_options = dict(init_integration.options)
    existing_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            CONF_OVERHEAD_LIGHTS: ["light.test_light"],
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL: True,
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES: [CONF_OVERHEAD_LIGHTS],
        }
    }
    hass.config_entries.async_update_entry(init_integration, options=existing_options)
    await hass.async_block_till_done()

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
            )
        },
    )

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE]
        == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
    )
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is True
    assert feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] == [
        CONF_OVERHEAD_LIGHTS
    ]


async def test_switching_back_to_adaptive_lighting_manage_restores_dormant_values(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Dormant AL manage values should be suggested when manage is selected again."""
    existing_options = dict(init_integration.options)
    existing_options[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            CONF_OVERHEAD_LIGHTS: ["light.test_light"],
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_IGNORE
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL: True,
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES: [CONF_OVERHEAD_LIGHTS],
        }
    }
    hass.config_entries.async_update_entry(init_integration, options=existing_options)
    await hass.async_block_till_done()

    result = await _start_options(hass, init_integration)
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
            )
        },
    )

    assert result["type"] == FlowResultType.FORM
    suggested_values = _schema_suggested_values(result)
    assert suggested_values[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGE_ALL] is True
    assert suggested_values[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MANAGED_ROLES] == [
        CONF_OVERHEAD_LIGHTS
    ]


async def test_adopt_existing_pairing_is_required_before_persistence(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Adopt-existing mode should not persist before role pairings are submitted."""
    _register_adaptive_lighting_switch_set(hass, "Kitchen Overhead", area_id="kitchen")
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_roles")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_OVERHEAD_LIGHTS: ["light.test_light"]}
    )
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            )
        },
    )

    assert result["type"] == FlowResultType.FORM
    schema = cast(vol.Schema, result["data_schema"])
    assert adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS) in {
        getattr(marker, "schema", marker) for marker in schema.schema
    }
    assert (
        _feature_options(init_integration, MagicAreasFeatures.LIGHT_GROUPS).get(
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE
        )
        != LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
    )


async def test_adopt_existing_pairing_submit_persists_mode(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Adopt-existing pair selection completes the adopt-existing subflow."""
    refs = _register_adaptive_lighting_switch_set(
        hass, "Kitchen Overhead", area_id="kitchen"
    )
    pair_key = adaptive_lighting_pair_key(CONF_OVERHEAD_LIGHTS)
    result = await _enable_feature(
        hass, init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    result = await _choose(hass, result, "feature_conf_light_groups")
    result = await _choose(hass, result, "feature_conf_light_groups_roles")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_OVERHEAD_LIGHTS: ["light.test_light"]}
    )
    result = await _choose(hass, result, "feature_conf_light_groups_adaptive_lighting")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            )
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            pair_key: refs["main"],
        },
    )

    assert result["type"] == FlowResultType.MENU
    feature_options = _feature_options(
        init_integration, MagicAreasFeatures.LIGHT_GROUPS
    )
    assert (
        feature_options[CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE]
        == LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
    )
