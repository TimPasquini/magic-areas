"""Stable fake-house entity names and simulator defaults."""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_CYCLE_SECONDS = 30.0
DEFAULT_RAMP_SECONDS = 10.0
DEFAULT_SAMPLE_SECONDS = 0.5
DEFAULT_STATE_PERIOD_CYCLES = 2.0
DEFAULT_TRACE_PATH = "dev/ha/runtime/traces/latest.jsonl"
DEFAULT_CONFIG_ENTRIES_PATH = "dev/ha/config/.storage/core.config_entries"
FAN_ROOM_CLEAR_TIMEOUT_MINUTES = 1.0
FAN_ROOM_HUMIDITY_HOLD_SECONDS = 4.0
COVER_ROOM_MANUAL_HOLD_SECONDS = 2.0
SEEDED_CLEAR_TIMEOUT_MINUTES = 1.0
BRIGHT_OFF_RUNTIME_TIMEOUT_SECONDS = 10.0
ADAPTIVE_LIGHTING_ALL_LIGHTS_SLEEP_SWITCH = (
    "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
    "adaptive_lighting_sleep_mode_ma_adaptive_lighting_room_all_lights"
)
ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_BRIGHTNESS_SWITCH = (
    "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
    "adaptive_lighting_adapt_brightness_ma_adaptive_lighting_room_all_lights"
)
ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_COLOR_SWITCH = (
    "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
    "adaptive_lighting_adapt_color_ma_adaptive_lighting_room_all_lights"
)

LIVING_ROOM_TRACE_ENTITIES: tuple[str, ...] = (
    "input_boolean.living_room_occupancy",
    "input_boolean.living_room_sleep",
    "input_boolean.living_room_accent",
    "input_boolean.living_room_overhead_power",
    "input_boolean.living_room_lamp_power",
    "input_number.living_room_lux",
    "input_number.outdoor_lux",
    "binary_sensor.living_room_occupancy",
    "binary_sensor.living_room_sleep",
    "binary_sensor.living_room_accent",
    "binary_sensor.living_room_light",
    "binary_sensor.outdoor_bright",
    "sensor.living_room_illuminance",
    "sensor.outdoor_illuminance",
    "light.living_room_overhead",
    "light.living_room_lamp",
    "light.magic_areas_native_light_groups_living_room_overhead_lights",
    "light.magic_areas_native_light_groups_living_room_sleep_lights",
    "light.magic_areas_native_light_groups_living_room_accent_lights",
    "light.magic_areas_native_light_groups_living_room_all_lights",
    "switch.magic_areas_light_groups_living_room_light_control",
    "switch.magic_areas_presence_hold_living_room",
    "binary_sensor.magic_areas_presence_tracking_living_room_area_state",
    "binary_sensor.magic_areas_threshold_living_room_light",
)

BATHROOM_TRACE_ENTITIES: tuple[str, ...] = (
    "input_boolean.bathroom_occupancy",
    "input_boolean.bathroom_sleep",
    "input_boolean.bathroom_overhead_power",
    "input_boolean.bathroom_sleep_light_power",
    "input_number.bathroom_lux",
    "binary_sensor.bathroom_occupancy",
    "binary_sensor.bathroom_sleep",
    "binary_sensor.bathroom_light",
    "sensor.bathroom_illuminance",
    "light.bathroom_overhead",
    "light.bathroom_sleep_light",
    "light.magic_areas_native_light_groups_bathroom_overhead_lights",
    "light.magic_areas_native_light_groups_bathroom_sleep_lights",
    "light.magic_areas_native_light_groups_bathroom_all_lights",
    "switch.magic_areas_light_groups_bathroom_light_control",
    "switch.magic_areas_presence_hold_bathroom",
    "binary_sensor.magic_areas_presence_tracking_bathroom_area_state",
    "binary_sensor.magic_areas_threshold_bathroom_light",
)

FAN_COVER_TRACE_ENTITIES: tuple[str, ...] = (
    "input_boolean.fan_room_occupancy",
    "input_boolean.fan_room_sleep",
    "input_boolean.fan_room_accent",
    "input_boolean.fan_room_exhaust_power",
    "input_number.fan_room_lux",
    "input_number.fan_room_humidity",
    "input_number.fan_room_voc",
    "input_select.fan_room_humidity_availability",
    "input_select.fan_room_voc_availability",
    "input_boolean.cover_room_occupancy",
    "input_boolean.cover_room_sleep",
    "input_boolean.cover_room_accent",
    "input_boolean.cover_room_blinds_open",
    "input_boolean.cover_room_shades_open",
    "input_boolean.cover_room_curtains_open",
    "input_boolean.cover_room_shutters_open",
    "input_boolean.cover_room_window_open",
    "input_boolean.cover_room_garage_open",
    "input_boolean.cover_room_door_open",
    "input_number.cover_room_lux",
    "input_number.outdoor_lux",
    "binary_sensor.fan_room_occupancy",
    "binary_sensor.fan_room_sleep",
    "binary_sensor.fan_room_accent",
    "binary_sensor.fan_room_light",
    "binary_sensor.cover_room_occupancy",
    "binary_sensor.cover_room_sleep",
    "binary_sensor.cover_room_accent",
    "binary_sensor.cover_room_light",
    "binary_sensor.outdoor_bright",
    "sensor.fan_room_illuminance",
    "sensor.fan_room_humidity",
    "sensor.fan_room_voc",
    "binary_sensor.magic_areas_signals_fan_room_trend_fan_controller_humidity",
    "sensor.cover_room_illuminance",
    "fan.fan_room_exhaust",
    "fan.magic_areas_fan_groups_fan_room_fan_group",
    "cover.cover_room_blinds",
    "cover.cover_room_shades",
    "cover.cover_room_curtains",
    "cover.cover_room_shutters",
    "cover.cover_room_window",
    "cover.cover_room_garage",
    "cover.cover_room_door",
    "cover.magic_areas_cover_groups_cover_room_cover_group_blind",
    "cover.magic_areas_cover_groups_cover_room_cover_group_shade",
    "cover.magic_areas_cover_groups_cover_room_cover_group_curtain",
    "cover.magic_areas_cover_groups_cover_room_cover_group_shutter",
    "cover.magic_areas_cover_groups_cover_room_cover_group_window",
    "switch.magic_areas_fan_groups_fan_room_fan_control",
    "switch.magic_areas_presence_hold_fan_room",
    "switch.magic_areas_cover_groups_cover_room_cover_control",
    "switch.magic_areas_presence_hold_cover_room",
    "binary_sensor.magic_areas_presence_tracking_fan_room_area_state",
    "binary_sensor.magic_areas_presence_tracking_cover_room_area_state",
)

CONTROL_MATRIX_ROOM_SLUGS: tuple[str, ...] = (
    "classic_sun_room",
    "classic_sensor_room",
    "advisory_sun_room",
    "advisory_sensor_room",
    "startup_unknown_room",
    "startup_unavailable_room",
    "adaptive_sun_room",
    "adaptive_binary_room",
    "adaptive_lux_room",
    "adaptive_ambient_room",
    "adaptive_manual_light_room",
    "adaptive_lighting_room",
)
CONTROL_MATRIX_TRACE_SLUGS = CONTROL_MATRIX_ROOM_SLUGS

AMBIENT_RISE_ROOM_SLUG = "adaptive_ambient_room"
MANUAL_DIRECT_LIGHT_ROOM_SLUG = "adaptive_manual_light_room"
AMBIENT_RISE_ROOM_SLUGS = frozenset(
    {AMBIENT_RISE_ROOM_SLUG, MANUAL_DIRECT_LIGHT_ROOM_SLUG}
)
STARTUP_UNKNOWN_ROOM_SLUG = "startup_unknown_room"
STARTUP_UNAVAILABLE_ROOM_SLUG = "startup_unavailable_room"
DAYLIGHT_AREA_LIGHT_ROOM_SLUGS = frozenset(
    {"classic_sun_room", "advisory_sun_room"}
)


def ambient_rise_signal_entity(slug: str) -> str:
    """Return the managed ambient-rise Trend helper entity id for a room slug."""
    return f"binary_sensor.magic_areas_signals_{slug}_trend_ambient_rise"


AMBIENT_RISE_SIGNAL_ENTITY = ambient_rise_signal_entity(AMBIENT_RISE_ROOM_SLUG)
MANUAL_DIRECT_LIGHT_RISE_SIGNAL_ENTITY = ambient_rise_signal_entity(
    MANUAL_DIRECT_LIGHT_ROOM_SLUG
)
AMBIENT_BRIGHT_THRESHOLD_LUX = 950
AMBIENT_DAYLIGHT_LUX = 1300
DEFAULT_LUX_JITTER = 1.0

FAN_ROOM_EXPECTED_OPTIONS: Mapping[str, object] = {
    "clear_timeout": 1,
    "presence_device_platforms": ["binary_sensor"],
    "presence_sensor_device_class": ["motion", "occupancy", "presence"],
    "secondary_states": {
        "dark_entity": "binary_sensor.fan_room_light",
        "sleep_entity": "binary_sensor.fan_room_sleep",
        "accent_entity": "binary_sensor.fan_room_accent",
        "sleep_timeout": 1,
        "extended_time": 1,
        "extended_timeout": 1,
    },
    "features": {
        "fan_groups": {
            "controllers": {
                "humidity": {
                    "members": ["fan.fan_room_exhaust"],
                    "sensor_entity_id": "sensor.fan_room_humidity",
                    "detection_mode": "threshold_trend",
                    "on_threshold": 60.0,
                    "hysteresis": 5.0,
                    "active_states": ["occupied", "extended"],
                    "suppress_states": ["sleep"],
                    "clear_behavior": "post_clear_hold",
                    "post_clear_hold_seconds": FAN_ROOM_HUMIDITY_HOLD_SECONDS,
                    "sensor_unavailable_behavior": "hold_then_clear",
                },
                "odor": {
                    "members": ["fan.fan_room_exhaust"],
                    "sensor_entity_id": "sensor.fan_room_voc",
                    "detection_mode": "threshold",
                    "on_threshold": 500.0,
                    "hysteresis": 100.0,
                    "active_states": ["occupied", "extended"],
                    "suppress_states": [],
                    "clear_behavior": "run_until_clear",
                    "post_clear_hold_seconds": 0,
                    "sensor_unavailable_behavior": "hold_until_restored",
                },
            }
        },
        "presence_hold": {"presence_hold_timeout": 0},
    },
}

COVER_ROOM_EXPECTED_OPTIONS: Mapping[str, object] = {
    "clear_timeout": 1,
    "presence_device_platforms": ["binary_sensor"],
    "presence_sensor_device_class": ["motion", "occupancy", "presence"],
    "secondary_states": {
        "dark_entity": "binary_sensor.cover_room_light",
        "sleep_entity": "binary_sensor.cover_room_sleep",
        "accent_entity": "binary_sensor.cover_room_accent",
        "sleep_timeout": 1,
        "extended_time": 1,
        "extended_timeout": 1,
    },
    "features": {
        "cover_groups": {
            "automation_device_classes": [
                "blind",
                "curtain",
                "shade",
                "shutter",
                "window",
            ],
            "manual_hold_seconds": COVER_ROOM_MANUAL_HOLD_SECONDS,
            "daylight_action": "open",
            "daylight_states": ["occupied", "extended"],
            "privacy_action": "close",
            "privacy_states": ["sleep"],
            "accent_action": "close",
            "accent_states": ["accented"],
        },
        "presence_hold": {"presence_hold_timeout": 0},
    },
}
