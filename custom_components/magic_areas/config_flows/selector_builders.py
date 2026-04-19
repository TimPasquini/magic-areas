"""Config-flow selector builder facade."""

import custom_components.magic_areas.schemas.selectors as _selectors

InvalidEntityError = _selectors.InvalidEntityError
NoEntitySelectedError = _selectors.NoEntitySelectedError
NoPresetSupportError = _selectors.NoPresetSupportError
build_climate_preset_selectors_and_validators = (
    _selectors.build_climate_preset_selectors_and_validators
)
build_selector_boolean = _selectors.build_selector_boolean
build_selector_entity_simple = _selectors.build_selector_entity_simple
build_selector_number = _selectors.build_selector_number
build_selector_object = _selectors.build_selector_object
build_selector_select = _selectors.build_selector_select

__all__ = [
    "InvalidEntityError",
    "NoEntitySelectedError",
    "NoPresetSupportError",
    "build_climate_preset_selectors_and_validators",
    "build_selector_boolean",
    "build_selector_entity_simple",
    "build_selector_number",
    "build_selector_object",
    "build_selector_select",
]
