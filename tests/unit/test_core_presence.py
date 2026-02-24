"""Tests for core presence helpers."""

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.core.entity_ids import EntityReferences
from custom_components.magic_areas.core.presence import (
    build_presence_sensors,
    compute_secondary_states,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.ha_domains import (
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
)


def test_build_presence_sensors_filters_devices() -> None:
    """Filter presence sensors by domain and device class."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "binary_sensor.motion_one",
                ATTR_DEVICE_CLASS: "motion",
            },
            {
                ATTR_ENTITY_ID: "binary_sensor.door_one",
                ATTR_DEVICE_CLASS: "door",
            },
        ],
        "device_tracker": [
            {ATTR_ENTITY_ID: "device_tracker.phone"},
        ],
    }

    config = {
        CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN, "device_tracker"],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
    }

    sensors = build_presence_sensors(
        entities_by_domain=entities_by_domain,
        config=config,
        slug="kitchen",
        enabled_features=set(),
    )

    assert sensors == [
        "binary_sensor.motion_one",
        "device_tracker.phone",
    ]


def test_build_presence_sensors_adds_feature_entities() -> None:
    """Append feature-driven presence entities when entity_references provided."""
    entities_by_domain: dict[str, list[dict[str, str]]] = {}
    config = {
        CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
    }

    # Simulate resolved entity references
    entity_refs = EntityReferences(
        presence_hold_switch=f"{SWITCH_DOMAIN}.magic_areas_presence_hold_kitchen",
        ble_tracker_monitor=f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
        wasp_in_a_box_sensor=f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_kitchen",
    )

    sensors = build_presence_sensors(
        entities_by_domain=entities_by_domain,
        config=config,
        slug="kitchen",
        enabled_features={
            MagicAreasFeatures.PRESENCE_HOLD,
            MagicAreasFeatures.BLE_TRACKER,
            MagicAreasFeatures.WASP_IN_A_BOX,
            MagicAreasFeatures.AGGREGATES,
        },
        entity_references=entity_refs,
    )

    assert sensors == [
        f"{SWITCH_DOMAIN}.magic_areas_presence_hold_kitchen",
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_kitchen",
    ]


class TestComputeSecondaryStates:
    """Tests for compute_secondary_states()."""

    def test_dark_active_by_default(self) -> None:
        """DARK defaults to active when no light sensor is configured."""
        result = compute_secondary_states(
            secondary_states_config={},
            entity_states={},
            valid_on_states={"on", "above_horizon"},
        )
        assert AreaStates.DARK in result
        assert AreaStates.BRIGHT not in result

    def test_dark_from_light_sensor_low(self) -> None:
        """DARK is active when the light sensor reads below threshold."""
        result = compute_secondary_states(
            secondary_states_config={CONF_DARK_ENTITY: "sensor.lux"},
            entity_states={"sensor.lux": "below_horizon"},
            valid_on_states={"above_horizon"},
        )
        assert AreaStates.DARK in result
        assert AreaStates.BRIGHT not in result

    def test_bright_derived_when_light_sensor_high(self) -> None:
        """BRIGHT is derived when light sensor is above threshold (DARK not active)."""
        result = compute_secondary_states(
            secondary_states_config={CONF_DARK_ENTITY: "sensor.lux"},
            entity_states={"sensor.lux": "above_horizon"},
            valid_on_states={"above_horizon"},
        )
        assert AreaStates.DARK not in result
        assert AreaStates.BRIGHT in result

    def test_sleep_active_when_entity_on(self) -> None:
        """SLEEP is active when its entity is in a valid-on state."""
        result = compute_secondary_states(
            secondary_states_config={CONF_SLEEP_ENTITY: "input_boolean.sleep_mode"},
            entity_states={"input_boolean.sleep_mode": "on"},
            valid_on_states={"on", "above_horizon"},
        )
        assert AreaStates.SLEEP in result
        assert AreaStates.DARK in result  # default dark (no dark sensor configured)

    def test_sleep_not_active_when_entity_off(self) -> None:
        """SLEEP is not added when its entity is not in a valid-on state."""
        result = compute_secondary_states(
            secondary_states_config={CONF_SLEEP_ENTITY: "input_boolean.sleep_mode"},
            entity_states={"input_boolean.sleep_mode": "off"},
            valid_on_states={"on", "above_horizon"},
        )
        assert AreaStates.SLEEP not in result

    def test_entity_missing_from_readings_skipped(self) -> None:
        """State not added when configured entity has no reading."""
        result = compute_secondary_states(
            secondary_states_config={CONF_SLEEP_ENTITY: "input_boolean.sleep_mode"},
            entity_states={},  # entity not present
            valid_on_states={"on", "above_horizon"},
        )
        assert AreaStates.SLEEP not in result

    def test_multiple_states_active_simultaneously(self) -> None:
        """Multiple secondary states can be active at the same time."""
        result = compute_secondary_states(
            secondary_states_config={
                CONF_DARK_ENTITY: "sensor.lux",
                CONF_SLEEP_ENTITY: "input_boolean.sleep_mode",
            },
            entity_states={
                "sensor.lux": "below_horizon",
                "input_boolean.sleep_mode": "on",
            },
            valid_on_states={"on", "above_horizon"},
        )
        assert AreaStates.DARK in result
        assert AreaStates.SLEEP in result
        assert AreaStates.BRIGHT not in result

    def test_accent_active_when_entity_on(self) -> None:
        """ACCENT is active when its entity is in a valid-on state."""
        result = compute_secondary_states(
            secondary_states_config={CONF_ACCENT_ENTITY: "input_boolean.accent"},
            entity_states={"input_boolean.accent": "on"},
            valid_on_states={"on"},
        )
        assert AreaStates.ACCENT in result


def test_build_presence_sensors_skips_features_without_references() -> None:
    """Skip feature entities when entity_references is not provided."""
    sensors = build_presence_sensors(
        entities_by_domain={},
        config={
            CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN],
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
        },
        slug="kitchen",
        enabled_features={
            MagicAreasFeatures.PRESENCE_HOLD,
            MagicAreasFeatures.BLE_TRACKER,
            MagicAreasFeatures.WASP_IN_A_BOX,
            MagicAreasFeatures.AGGREGATES,
        },
    )

    assert sensors == []
