"""Runtime behavior tests for options-flow helper paths."""

from typing import cast
from unittest.mock import patch

from homeassistant import setup
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant, State, StateMachine
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.components import MagicAreasRuntimeData
from custom_components.magic_areas.config_flow import OptionsFlowHandler
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.config_flows import ADDITIONAL_LIGHT_TRACKING_ENTITIES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures


async def test_options_flow_select_features_initializes_enabled_features(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Selecting features initializes enabled-feature mapping when absent."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    coordinator = config_entry.runtime_data.coordinator
    coordinator_data = coordinator.data
    assert coordinator_data is not None
    flow._area_config = coordinator_data.area_config
    flow._coordinator_data = coordinator_data
    flow.area_options = {}

    result = await flow.async_step_select_features(
        user_input={MagicAreasFeatures.LIGHT_GROUPS: True}
    )

    assert result["type"] == FlowResultType.MENU
    assert CONF_ENABLED_FEATURES in flow.area_options


async def test_options_flow_init_aborts_when_entry_runtime_data_unavailable(
    hass: HomeAssistant,
) -> None:
    """Options flow should fail cleanly while the config entry is not loaded."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"id": "kitchen", "name": "Kitchen", "type": "interior"},
        unique_id="kitchen",
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(cast(ConfigEntry[MagicAreasRuntimeData], config_entry))
    flow.hass = hass

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_loaded"


async def test_options_flow_init_skips_missing_light_tracking_state(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Missing state entries are ignored for light tracking entities."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    missing_entity = "binary_sensor.missing_light"
    hass.states.async_set(
        missing_entity, "off", {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT}
    )

    original_get = StateMachine.get

    def _patched_get(self: StateMachine, entity_id: str) -> State | None:
        if entity_id == missing_entity:
            return None
        return original_get(self, entity_id)

    with patch.object(StateMachine, "get", autospec=True, side_effect=_patched_get):
        await flow.async_step_init()

    assert missing_entity not in flow.all_light_tracking_entities


async def test_options_flow_async_step_routes_feature_conf(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Generic async_step routes feature_conf_* ids to feature-config handler."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()
    flow.context = {}

    result = await flow.async_step("feature_conf_light_groups")

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "feature_conf_light_groups"


async def test_options_flow_light_tracking_entities(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Additional tracking entities are included in light tracking set."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)

    await setup.async_setup_component(hass, "sun", {})
    await hass.async_block_till_done()

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    assert "sun.sun" in ADDITIONAL_LIGHT_TRACKING_ENTITIES
    assert "sun.sun" in flow.all_light_tracking_entities


async def test_options_flow_illuminance_entities_exclude_sun_and_binary(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Outside/inside lux selectors should be illuminance sensors only."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)

    await setup.async_setup_component(hass, "sun", {})
    hass.states.async_set(
        "sensor.outdoor_lux",
        "1200",
        {ATTR_DEVICE_CLASS: SensorDeviceClass.ILLUMINANCE},
    )
    hass.states.async_set(
        "binary_sensor.daylight_flag",
        "on",
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.LIGHT},
    )
    await hass.async_block_till_done()

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    assert "sensor.outdoor_lux" in flow.all_illuminance_entities
    assert "sun.sun" not in flow.all_illuminance_entities
    assert "binary_sensor.daylight_flag" not in flow.all_illuminance_entities
