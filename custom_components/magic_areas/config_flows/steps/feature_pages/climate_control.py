"""Climate-control feature page handling for options flow."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from homeassistant import config_entries

from custom_components.magic_areas.config_flows.base import (
    ConfigSubMap,
    enabled_feature_map,
)
from custom_components.magic_areas.config_flows.selector_builders import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
    build_climate_preset_selectors_and_validators,
    build_selector_select,
)
from custom_components.magic_areas.config_flows.steps.feature_pages.generic import (
    handle_feature_form,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.config.readers import (
    CLIMATE_CONTROL_ENTITY_KEY,
    CLIMATE_CONTROL_PRESET_OPTION_KEYS,
)
from custom_components.magic_areas.schemas import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import (
        OptionsFlowHandler,
    )


async def handle_climate_preset_selection(
    flow: OptionsFlowHandler, user_input: Mapping[str, object] | None = None
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
        next_step="feature_conf_climate_control",
        selectors=selectors,
        dynamic_validators=dynamic_validators,
    )
