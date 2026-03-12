"""Climate control preset selection step handler."""

from typing import TYPE_CHECKING, Any

from homeassistant import config_entries
from homeassistant.const import ATTR_ENTITY_ID

from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.config_keys.features import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.schemas.features import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)
from custom_components.magic_areas.schemas.feature_builders import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
    build_climate_preset_selectors_and_validators,
)
from custom_components.magic_areas.schemas.selectors import build_selector_select

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler


async def handle_climate_preset_selection(
    flow: "OptionsFlowHandler", user_input: dict[str, Any] | None = None
) -> config_entries.ConfigFlowResult:
    """Handle climate control preset selection step.

    This is the second step in climate control configuration, where the user
    selects which presets (clear, occupied, sleep, extended) to use based on
    the capabilities of the selected climate entity.

    Args:
        flow: OptionsFlowHandler instance
        user_input: User input from form submission

    Returns:
        ConfigFlowResult with form or abort result

    """
    # The first climate step stores the selected entity id under the climate feature config.
    climate_cfg = flow.area_options.get(CONF_ENABLED_FEATURES, {}).get(
        MagicAreasFeatures.CLIMATE_CONTROL, {}
    )

    climate_entity_id: str | None = climate_cfg.get(
        CONF_CLIMATE_CONTROL_ENTITY_ID
    ) or climate_cfg.get(ATTR_ENTITY_ID)  # backward/alternate storage

    # Build dynamic selectors and validators based on climate entity capabilities
    try:
        selectors, dynamic_validators = build_climate_preset_selectors_and_validators(
            flow.hass,
            climate_entity_id,
            build_selector_select,
            preset_config_keys=(
                CONF_CLIMATE_CONTROL_PRESET_CLEAR,
                CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
                CONF_CLIMATE_CONTROL_PRESET_SLEEP,
                CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
            ),
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

    # Delegate to generic feature config handler with climate-specific options

    # Manually build form result similar to do_feature_config
    errors: dict[str, str] = {}

    if user_input is not None:
        try:
            validated_input = CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT(user_input)
        except Exception:  # pylint: disable=broad-exception-caught
            errors = {"base": "invalid_input"}
        else:
            features = flow.area_options.setdefault(CONF_ENABLED_FEATURES, {})
            # Climate presets merge with existing climate config
            if MagicAreasFeatures.CLIMATE_CONTROL not in features:
                features[MagicAreasFeatures.CLIMATE_CONTROL] = {}

            features[MagicAreasFeatures.CLIMATE_CONTROL].update(validated_input)

            # noinspection PyTypeChecker
            return await flow.async_step_show_menu()

    # noinspection PyTypeChecker
    return flow.async_show_form(
        step_id="feature_conf_climate_control_select_presets",
        data_schema=flow._build_schema_from_vol(
            CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
            saved_options=flow.area_options.get(CONF_ENABLED_FEATURES, {}).get(
                MagicAreasFeatures.CLIMATE_CONTROL, {}
            ),
            dynamic_validators=dynamic_validators,
            selectors=selectors,
        ),
        errors=errors,
    )
