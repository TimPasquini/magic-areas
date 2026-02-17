"""Voluptuous schemas and registries for configurable features."""

from __future__ import annotations

from itertools import chain
from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from voluptuous import Schema

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    DEFAULT_AGGREGATES_MIN_ENTITIES,
    DEFAULT_BLE_TRACKER_ENTITIES,
    DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
    DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
    DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
    DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
    DEFAULT_FAN_GROUPS_REQUIRED_STATE,
    DEFAULT_FAN_GROUPS_SETPOINT,
    DEFAULT_NOTIFY_STATES,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_WASP_IN_A_BOX_DELAY,
    DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
    DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
    DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures, FEATURE_LIST, FEATURE_LIST_GLOBAL
from custom_components.magic_areas.light_groups import (
    CONF_ACCENT_LIGHTS,
    CONF_ACCENT_LIGHTS_ACT_ON,
    CONF_ACCENT_LIGHTS_STATES,
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    CONF_SLEEP_LIGHTS,
    CONF_SLEEP_LIGHTS_ACT_ON,
    CONF_SLEEP_LIGHTS_STATES,
    CONF_TASK_LIGHTS,
    CONF_TASK_LIGHTS_ACT_ON,
    CONF_TASK_LIGHTS_STATES,
    DEFAULT_LIGHT_GROUP_ACT_ON,
)

AGGREGATE_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_AGGREGATES_MIN_ENTITIES, default=DEFAULT_AGGREGATES_MIN_ENTITIES
        ): cv.positive_int,
        vol.Optional(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
        vol.Optional(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
        vol.Optional(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
            default=DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
        ): cv.positive_int,
        vol.Optional(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
            default=DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)

HEALTH_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_HEALTH_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)

PRESENCE_HOLD_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_PRESENCE_HOLD_TIMEOUT, default=DEFAULT_PRESENCE_HOLD_TIMEOUT
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)

BLE_TRACKER_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_BLE_TRACKER_ENTITIES, default=DEFAULT_BLE_TRACKER_ENTITIES
        ): cv.entity_ids,
    },
    extra=vol.REMOVE_EXTRA,
)

WASP_IN_A_BOX_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_WASP_IN_A_BOX_DELAY, default=DEFAULT_WASP_IN_A_BOX_DELAY
        ): cv.positive_int,
        vol.Optional(
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT, default=DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
            default=DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
        ): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)

CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT = vol.Schema(
    {
        vol.Required(CONF_CLIMATE_CONTROL_ENTITY_ID): cv.entity_id,
    }
)

CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT = vol.Schema(
    {
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_CLEAR,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_SLEEP,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
        ): str,
    },
    extra=vol.REMOVE_EXTRA,
)

CLIMATE_CONTROL_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CLIMATE_CONTROL_ENTITY_ID): cv.entity_id,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_CLEAR,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_SLEEP,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
        ): str,
    },
    extra=vol.REMOVE_EXTRA,
)

FAN_GROUP_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_FAN_GROUPS_REQUIRED_STATE, default=DEFAULT_FAN_GROUPS_REQUIRED_STATE
        ): str,
        vol.Optional(
            CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
            default=DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
        ): str,
        vol.Optional(
            CONF_FAN_GROUPS_SETPOINT, default=DEFAULT_FAN_GROUPS_SETPOINT
        ): float,
    },
    extra=vol.REMOVE_EXTRA,
)

LIGHT_GROUP_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_OVERHEAD_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_OVERHEAD_LIGHTS_STATES, default=[AreaStates.OCCUPIED]
        ): cv.ensure_list,
        vol.Optional(
            CONF_OVERHEAD_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_SLEEP_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_SLEEP_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_SLEEP_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_ACCENT_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_ACCENT_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_ACCENT_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_TASK_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_TASK_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_TASK_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)

AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_DEVICES, default=[]): cv.entity_ids,
        vol.Optional(CONF_NOTIFY_STATES, default=DEFAULT_NOTIFY_STATES): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)

ALL_FEATURES = set(FEATURE_LIST) | set(FEATURE_LIST_GLOBAL)

CONFIGURABLE_FEATURES = {
    MagicAreasFeatures.LIGHT_GROUPS: LIGHT_GROUP_FEATURE_SCHEMA,
    MagicAreasFeatures.CLIMATE_CONTROL : CLIMATE_CONTROL_FEATURE_SCHEMA,
    MagicAreasFeatures.FAN_GROUPS: FAN_GROUP_FEATURE_SCHEMA,
    MagicAreasFeatures.AGGREGATES: AGGREGATE_FEATURE_SCHEMA,
    MagicAreasFeatures.HEALTH: HEALTH_FEATURE_SCHEMA,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER: AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA,
    MagicAreasFeatures.PRESENCE_HOLD: PRESENCE_HOLD_FEATURE_SCHEMA,
    MagicAreasFeatures.BLE_TRACKER: BLE_TRACKER_FEATURE_SCHEMA,
    MagicAreasFeatures.WASP_IN_A_BOX: WASP_IN_A_BOX_FEATURE_SCHEMA,
}

NON_CONFIGURABLE_FEATURES_META = [
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.FAN_GROUPS,
]

NON_CONFIGURABLE_FEATURES: dict[str, dict[str, Any]] = {
    str(feature): {} for feature in ALL_FEATURES if feature not in CONFIGURABLE_FEATURES
}

FEATURES_SCHEMA: Schema = vol.Schema(
    {
        vol.Optional(str(feature)): feature_schema
        for feature, feature_schema in chain(
            CONFIGURABLE_FEATURES.items(), NON_CONFIGURABLE_FEATURES.items()
        )
    },
    extra=vol.REMOVE_EXTRA,
)
