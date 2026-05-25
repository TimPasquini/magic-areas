"""Feature-config step handler tests for options flow."""

from typing import cast
from unittest.mock import MagicMock, patch

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlowContext
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import SelectSelector
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.components import MagicAreasRuntimeData
from custom_components.magic_areas.config_flow import OptionsFlowHandler
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import FeatureConfigStep


def _enabled_features(flow: OptionsFlowHandler) -> dict[object, object]:
    """Return enabled-features mapping with a concrete type for assertions."""
    return cast(dict[object, object], flow.area_options[CONF_ENABLED_FEATURES])


async def test_options_flow_feature_conf_updates_options(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Feature config input persists and returns to menu."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    flow.context = cast(ConfigFlowContext, {"step_id": "feature_conf_health"})
    result = await flow.async_step_feature_conf(
        user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]}
    )

    assert result["type"] == FlowResultType.MENU
    assert MagicAreasFeatures.HEALTH in _enabled_features(flow)


async def test_options_flow_feature_conf_next_step_calls_handler(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Feature config honors explicit next-step handler."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()

    patched_feature = FeatureConfigStep(
        feature=MagicAreasFeatures.HEALTH,
        step_id="feature_conf_health",
        next_step="show_menu",
    )
    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.get_feature_config_steps",
        return_value={MagicAreasFeatures.HEALTH: patched_feature},
    ):
        flow.context = cast(ConfigFlowContext, {"step_id": "feature_conf_health"})
        result = await flow.async_step_feature_conf(
            user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]}
        )

    assert result["type"] == FlowResultType.MENU


async def test_options_flow_feature_conf_merge_options(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Merge-enabled feature config appends onto existing values."""
    config_entry = cast(ConfigEntry[MagicAreasRuntimeData], init_integration)
    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass
    await flow.async_step_init()
    flow.area_options[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.HEALTH: {"existing": 1}}

    feature_key = MagicAreasFeatures.HEALTH
    patched_feature = FeatureConfigStep(
        feature=feature_key,
        step_id=f"feature_conf_{feature_key.value}",
        schema=vol.Schema({vol.Required("value"): int}),
        merge_options=True,
    )
    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.get_feature_config_steps",
        return_value={feature_key: patched_feature},
    ):
        flow.context = cast(
            ConfigFlowContext, {"step_id": f"feature_conf_{feature_key.value}"}
        )
        result = await flow.async_step_feature_conf(user_input={"value": 2})

    assert result["type"] == FlowResultType.MENU
    assert _enabled_features(flow)[feature_key] == {
        "existing": 1,
        "value": 2,
    }


async def test_options_flow_feature_conf_validation_error(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Validation failures return feature form with invalid_input error."""
    config_entry = init_integration

    options = config_entry.options.copy()
    options.setdefault(CONF_ENABLED_FEATURES, {})[MagicAreasFeatures.HEALTH] = {}
    hass.config_entries.async_update_entry(config_entry, options=options)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_health"}
    )

    patched_feature = FeatureConfigStep(
        feature=MagicAreasFeatures.HEALTH,
        step_id="feature_conf_health",
        schema=MagicMock(side_effect=cast(Exception, vol.MultipleInvalid(None))),
    )
    with patch(
        "custom_components.magic_areas.config_flows.steps.feature_config.get_feature_config_steps",
        return_value={MagicAreasFeatures.HEALTH: patched_feature},
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["problem"]},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_health"
    assert result["errors"] == {"base": "invalid_input"}


async def test_options_flow_wasp_in_a_box_selector(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Wasp device classes selector remains multi-select."""
    config_entry = init_integration

    options = config_entry.options.copy()
    options.setdefault(CONF_ENABLED_FEATURES, {})[MagicAreasFeatures.WASP_IN_A_BOX] = {}
    hass.config_entries.async_update_entry(config_entry, options=options)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "feature_conf_wasp_in_a_box"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["data_schema"] is not None
    schema = result["data_schema"].schema
    wasp_classes_validator = schema[vol.Optional(CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES)]
    assert isinstance(wasp_classes_validator, SelectSelector)
    assert wasp_classes_validator.config["multiple"] is True
