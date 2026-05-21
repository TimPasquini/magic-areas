"""Schemas and selectors public API for config-flow consumers."""

from custom_components.magic_areas.schemas.area import (
    META_AREA_SCHEMA,
    DOMAIN_SCHEMA,
    META_AREA_BASIC_OPTIONS_SCHEMA,
    META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    META_AREA_SECONDARY_STATES_SCHEMA,
    REGULAR_AREA_SCHEMA,
    REGULAR_AREA_BASIC_OPTIONS_SCHEMA,
    REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    SECONDARY_STATES_SCHEMA,
)
from custom_components.magic_areas.schemas.control_groups import (
    CUSTOM_CONTROL_GROUPS_SCHEMA,
)
from custom_components.magic_areas.schemas.features import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
    CONFIGURABLE_FEATURES,
)
from custom_components.magic_areas.schemas.selectors import (
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
    build_climate_preset_selectors_and_validators,
    build_selector_boolean,
    build_selector_entity_any,
    build_selector_entity_simple,
    build_selector_number,
    build_selector_object,
    build_selector_select,
    build_selector_text,
)

__all__ = [
    "CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT",
    "CONFIGURABLE_FEATURES",
    "CUSTOM_CONTROL_GROUPS_SCHEMA",
    "DOMAIN_SCHEMA",
    "InvalidEntityError",
    "META_AREA_SCHEMA",
    "META_AREA_BASIC_OPTIONS_SCHEMA",
    "META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
    "META_AREA_SECONDARY_STATES_SCHEMA",
    "NoEntitySelectedError",
    "NoPresetSupportError",
    "REGULAR_AREA_SCHEMA",
    "REGULAR_AREA_BASIC_OPTIONS_SCHEMA",
    "REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA",
    "SECONDARY_STATES_SCHEMA",
    "build_climate_preset_selectors_and_validators",
    "build_selector_boolean",
    "build_selector_entity_any",
    "build_selector_entity_simple",
    "build_selector_number",
    "build_selector_object",
    "build_selector_select",
    "build_selector_text",
]
