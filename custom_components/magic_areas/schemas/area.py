"""Area-related voluptuous schemas."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from custom_components.magic_areas.enums import CalculationMode
from custom_components.magic_areas.area_maps import (
    CONF_DARK_ENTITY,
    CONF_ACCENT_ENTITY,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.config_keys import (
    CONF_SLEEP_TIMEOUT,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_TYPE,
    CONF_INCLUDE_ENTITIES,
    CONF_EXCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    DEFAULT_SLEEP_TIMEOUT,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
    DEFAULT_TYPE,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_CLEAR_TIMEOUT,
    DEFAULT_CLEAR_TIMEOUT_META,
    DEFAULT_RELOAD_ON_REGISTRY_CHANGE,
    DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES,
)
from custom_components.magic_areas.area_constants import (
    AREA_TYPE_INTERIOR,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_META,
)
from custom_components.magic_areas.defaults import DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS
from custom_components.magic_areas.schemas.features import FEATURES_SCHEMA

SECONDARY_STATES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DARK_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_ACCENT_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_SLEEP_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(
            CONF_SLEEP_TIMEOUT, default=DEFAULT_SLEEP_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIME, default=DEFAULT_EXTENDED_TIME
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIMEOUT, default=DEFAULT_EXTENDED_TIMEOUT
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)


META_AREA_SECONDARY_STATES_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_SLEEP_TIMEOUT, default=DEFAULT_SLEEP_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIME, default=DEFAULT_EXTENDED_TIME
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIMEOUT, default=DEFAULT_EXTENDED_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_SECONDARY_STATES_CALCULATION_MODE,
            default=DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
        ): vol.In(CalculationMode),
    },
    extra=vol.REMOVE_EXTRA,
)


# Basic Area Options Schema
REGULAR_AREA_BASIC_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=DEFAULT_TYPE): vol.In(
            [AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR]
        ),
        vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_RELOAD_ON_REGISTRY_CHANGE, default=DEFAULT_RELOAD_ON_REGISTRY_CHANGE
        ): cv.boolean,
        vol.Optional(
            CONF_IGNORE_DIAGNOSTIC_ENTITIES, default=DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES
        ): cv.boolean,
    },
    extra=vol.REMOVE_EXTRA,
)

META_AREA_BASIC_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=AREA_TYPE_META): AREA_TYPE_META,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_RELOAD_ON_REGISTRY_CHANGE, default=DEFAULT_RELOAD_ON_REGISTRY_CHANGE
        ): cv.boolean,
    },
    extra=vol.REMOVE_EXTRA,
)


# Presence Tracking Schema
REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_PRESENCE_DEVICE_PLATFORMS, default=DEFAULT_PRESENCE_DEVICE_PLATFORMS
        ): cv.ensure_list,
        vol.Optional(
            CONF_PRESENCE_SENSOR_DEVICE_CLASS,
            default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        ): cv.ensure_list,
        vol.Optional(CONF_KEEP_ONLY_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)

META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT_META
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)


# Magic Areas
REGULAR_AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=DEFAULT_TYPE): vol.In(
            [AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR]
        ),
        vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_RELOAD_ON_REGISTRY_CHANGE, default=DEFAULT_RELOAD_ON_REGISTRY_CHANGE
        ): cv.boolean,
        vol.Optional(
            CONF_IGNORE_DIAGNOSTIC_ENTITIES, default=DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES
        ): cv.boolean,
        vol.Optional(CONF_KEEP_ONLY_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_PRESENCE_DEVICE_PLATFORMS, default=DEFAULT_PRESENCE_DEVICE_PLATFORMS
        ): cv.ensure_list,
        vol.Optional(
            CONF_PRESENCE_SENSOR_DEVICE_CLASS,
            default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        ): cv.ensure_list,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
        ): cv.positive_int,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_SECONDARY_STATES, default={}): SECONDARY_STATES_SCHEMA,
    },
    extra=vol.REMOVE_EXTRA,
)

META_AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=AREA_TYPE_META): AREA_TYPE_META,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_RELOAD_ON_REGISTRY_CHANGE, default=DEFAULT_RELOAD_ON_REGISTRY_CHANGE
        ): cv.boolean,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT_META
        ): cv.positive_int,
        vol.Optional(
            CONF_SECONDARY_STATES, default={}
        ): META_AREA_SECONDARY_STATES_SCHEMA,
    },
    extra=vol.REMOVE_EXTRA,
)

AREA_SCHEMA = vol.Schema(
    vol.Any(REGULAR_AREA_SCHEMA, META_AREA_SCHEMA), extra=vol.REMOVE_EXTRA
)

_DOMAIN_SCHEMA = vol.Schema(
    {cv.slug: vol.Any(AREA_SCHEMA, None)}, extra=vol.REMOVE_EXTRA
)
