"""Pure fan controller policy tests."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls.policies.fan import (
    build_fan_control_group_policy,
    FanClearBehavior,
    FanControllerConfig,
    FanControllerRole,
    FanDetectionMode,
    FanSensorUnavailableBehavior,
    evaluate_fan_controllers,
    fan_controller_evaluation_to_control_group,
    legacy_cooling_controller,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_FAN_CONTROLLER_ACTIVE_STATES,
    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
    CONF_FAN_CONTROLLER_DETECTION_MODE,
    CONF_FAN_CONTROLLER_HYSTERESIS,
    CONF_FAN_CONTROLLER_MEMBERS,
    CONF_FAN_CONTROLLER_ON_THRESHOLD,
    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
    CONF_FAN_GROUPS_CONTROLLERS,
)


def _controller(
    controller_id: str,
    *,
    members: tuple[str, ...] = ("fan.room",),
    sensor_entity_id: str = "sensor.room",
    detection_mode: FanDetectionMode = FanDetectionMode.THRESHOLD,
    on_threshold: float = 50.0,
    hysteresis: float = 5.0,
    active_states: tuple[str, ...] = (AreaStates.OCCUPIED,),
    suppress_states: tuple[str, ...] = (),
    clear_behavior: FanClearBehavior = FanClearBehavior.OCCUPANCY_ONLY,
    sensor_unavailable_behavior: FanSensorUnavailableBehavior = (
        FanSensorUnavailableBehavior.CLEAR_REASON
    ),
) -> FanControllerConfig:
    """Build a fan controller test config."""
    return FanControllerConfig(
        controller_id=controller_id,
        members=members,
        sensor_entity_id=sensor_entity_id,
        detection_mode=detection_mode,
        on_threshold=on_threshold,
        hysteresis=hysteresis,
        active_states=active_states,
        suppress_states=suppress_states,
        clear_behavior=clear_behavior,
        sensor_unavailable_behavior=sensor_unavailable_behavior,
    )


def test_cooling_controller_activates_above_threshold() -> None:
    """Cooling activates when occupied and the temperature exceeds setpoint."""
    controller = _controller(FanControllerRole.COOLING, on_threshold=75.0)

    result = evaluate_fan_controllers(
        (controller,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.room": 78.0},
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["cooling"]
    assert result.turn_on_entity_ids == ("fan.room",)
    assert result.turn_off_entity_ids == ()


def test_controller_clears_below_hysteresis_clear_threshold() -> None:
    """An active threshold controller clears once below the hysteresis band."""
    controller = _controller(
        FanControllerRole.HUMIDITY,
        on_threshold=60.0,
        hysteresis=5.0,
    )

    result = evaluate_fan_controllers(
        (controller,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.room": 54.9},
        previously_active_controller_ids=(FanControllerRole.HUMIDITY,),
    )

    assert result.active_reasons == ()
    assert [reason.controller_id for reason in result.inactive_reasons] == ["humidity"]
    assert result.turn_off_entity_ids == ("fan.room",)


def test_controller_holds_inside_hysteresis_band_when_previously_active() -> None:
    """An active threshold controller remains active inside the hysteresis band."""
    controller = _controller(
        FanControllerRole.HUMIDITY,
        on_threshold=60.0,
        hysteresis=5.0,
    )

    result = evaluate_fan_controllers(
        (controller,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.room": 57.0},
        previously_active_controller_ids=(FanControllerRole.HUMIDITY,),
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["humidity"]
    assert result.turn_on_entity_ids == ("fan.room",)


def test_threshold_trend_controller_activates_inside_hysteresis_band_when_rising() -> None:
    """Threshold+trend supplements threshold evidence without replacing clear bounds."""
    controller = _controller(
        FanControllerRole.HUMIDITY,
        detection_mode=FanDetectionMode.THRESHOLD_TREND,
        on_threshold=60.0,
        hysteresis=5.0,
    )

    result = evaluate_fan_controllers(
        (controller,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.room": 57.0},
        trend_states={FanControllerRole.HUMIDITY.value: True},
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["humidity"]
    assert result.active_reasons[0].reason.startswith(
        "active_trend_rising_inside_hysteresis"
    )
    assert result.turn_on_entity_ids == ("fan.room",)


def test_threshold_trend_controller_does_not_activate_below_clear_band() -> None:
    """A rising trend alone is not enough when the sensor is below clear threshold."""
    controller = _controller(
        FanControllerRole.HUMIDITY,
        detection_mode=FanDetectionMode.THRESHOLD_TREND,
        on_threshold=60.0,
        hysteresis=5.0,
    )

    result = evaluate_fan_controllers(
        (controller,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.room": 54.0},
        trend_states={FanControllerRole.HUMIDITY.value: True},
    )

    assert result.active_reasons == ()
    assert [reason.controller_id for reason in result.inactive_reasons] == ["humidity"]


def test_shared_fan_stays_on_until_all_reasons_clear() -> None:
    """A shared fan is not turned off while another controller still needs it."""
    humidity = _controller(
        FanControllerRole.HUMIDITY,
        members=("fan.bathroom",),
        sensor_entity_id="sensor.humidity",
        on_threshold=60.0,
    )
    odor = _controller(
        FanControllerRole.ODOR,
        members=("fan.bathroom",),
        sensor_entity_id="sensor.voc",
        on_threshold=200.0,
    )

    result = evaluate_fan_controllers(
        (humidity, odor),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={
            "sensor.humidity": 45.0,
            "sensor.voc": 250.0,
        },
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["odor"]
    assert result.turn_on_entity_ids == ("fan.bathroom",)
    assert result.turn_off_entity_ids == ()


def test_suppression_applies_to_only_matching_controller() -> None:
    """Suppressing cooling for sleep does not suppress humidity."""
    cooling = _controller(
        FanControllerRole.COOLING,
        members=("fan.bathroom",),
        sensor_entity_id="sensor.temperature",
        on_threshold=75.0,
        suppress_states=(AreaStates.SLEEP,),
    )
    humidity = _controller(
        FanControllerRole.HUMIDITY,
        members=("fan.bathroom",),
        sensor_entity_id="sensor.humidity",
        on_threshold=60.0,
    )

    result = evaluate_fan_controllers(
        (cooling, humidity),
        current_states=(AreaStates.OCCUPIED, AreaStates.SLEEP),
        sensor_values={
            "sensor.temperature": 80.0,
            "sensor.humidity": 65.0,
        },
    )

    assert [reason.controller_id for reason in result.suppressed_reasons] == ["cooling"]
    assert [reason.controller_id for reason in result.active_reasons] == ["humidity"]
    assert result.turn_on_entity_ids == ("fan.bathroom",)


def test_run_until_clear_ignores_area_clear_until_sensor_clears() -> None:
    """Humidity can continue running after occupancy clears."""
    humidity = _controller(
        FanControllerRole.HUMIDITY,
        clear_behavior=FanClearBehavior.RUN_UNTIL_CLEAR,
        on_threshold=60.0,
    )

    result = evaluate_fan_controllers(
        (humidity,),
        current_states=(AreaStates.CLEAR,),
        sensor_values={"sensor.room": 65.0},
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["humidity"]
    assert result.turn_on_entity_ids == ("fan.room",)


def test_sensor_unavailable_behavior_is_per_controller() -> None:
    """One unavailable sensor does not clear a fan needed by another controller."""
    humidity = _controller(
        FanControllerRole.HUMIDITY,
        members=("fan.bathroom",),
        sensor_entity_id="sensor.humidity",
        sensor_unavailable_behavior=FanSensorUnavailableBehavior.CLEAR_REASON,
    )
    odor = _controller(
        FanControllerRole.ODOR,
        members=("fan.bathroom",),
        sensor_entity_id="sensor.voc",
        on_threshold=200.0,
    )

    result = evaluate_fan_controllers(
        (humidity, odor),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={
            "sensor.humidity": None,
            "sensor.voc": 250.0,
        },
    )

    assert [reason.controller_id for reason in result.inactive_reasons] == ["humidity"]
    assert [reason.controller_id for reason in result.active_reasons] == ["odor"]
    assert result.turn_off_entity_ids == ()


def test_sensor_unavailable_can_hold_previously_active_reason() -> None:
    """A controller can hold its reason while waiting for sensor restoration."""
    humidity = _controller(
        FanControllerRole.HUMIDITY,
        sensor_unavailable_behavior=FanSensorUnavailableBehavior.HOLD_UNTIL_RESTORED,
    )

    result = evaluate_fan_controllers(
        (humidity,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.room": None},
        previously_active_controller_ids=(FanControllerRole.HUMIDITY,),
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["humidity"]
    assert result.turn_on_entity_ids == ("fan.room",)


def test_legacy_fan_config_maps_to_cooling_controller() -> None:
    """The existing fan threshold config maps into the Cooling role."""
    controller = legacy_cooling_controller(
        setpoint=72.0,
        required_state=AreaStates.OCCUPIED,
        tracked_sensor_entity_id="sensor.temperature",
        members=("fan.room",),
    )

    result = evaluate_fan_controllers(
        (controller,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.temperature": 72.0},
    )

    assert controller.controller_id == FanControllerRole.COOLING
    assert controller.hysteresis == 0.0
    assert [reason.controller_id for reason in result.active_reasons] == ["cooling"]


def test_build_policy_uses_persisted_role_controllers() -> None:
    """Persisted fan role pages become runtime controller configs."""
    policy = build_fan_control_group_policy(
        {
            CONF_FAN_GROUPS_CONTROLLERS: {
                FanControllerRole.HUMIDITY.value: {
                    CONF_FAN_CONTROLLER_MEMBERS: ["fan.bathroom"],
                    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "sensor.bathroom_humidity",
                    CONF_FAN_CONTROLLER_DETECTION_MODE: FanDetectionMode.THRESHOLD.value,
                    CONF_FAN_CONTROLLER_ON_THRESHOLD: 60,
                    CONF_FAN_CONTROLLER_HYSTERESIS: 5,
                    CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.OCCUPIED.value],
                    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: (
                        FanClearBehavior.RUN_UNTIL_CLEAR.value
                    ),
                },
                FanControllerRole.ODOR.value: {
                    CONF_FAN_CONTROLLER_MEMBERS: ["fan.bathroom"],
                    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "sensor.bathroom_voc",
                    CONF_FAN_CONTROLLER_DETECTION_MODE: FanDetectionMode.THRESHOLD.value,
                    CONF_FAN_CONTROLLER_ON_THRESHOLD: 200,
                    CONF_FAN_CONTROLLER_HYSTERESIS: 10,
                    CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.OCCUPIED.value],
                    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: (
                        FanClearBehavior.RUN_UNTIL_CLEAR.value
                    ),
                },
            }
        }
    )

    assert policy.policy is None
    assert [controller.controller_id for controller in policy.controllers] == [
        FanControllerRole.HUMIDITY.value,
        FanControllerRole.ODOR.value,
    ]

    result = evaluate_fan_controllers(
        policy.controllers,
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={
            "sensor.bathroom_humidity": 45.0,
            "sensor.bathroom_voc": 250.0,
        },
    )

    assert [reason.controller_id for reason in result.active_reasons] == ["odor"]
    assert result.turn_off_entity_ids == ()


def test_controller_evaluation_targets_role_members_before_all_fan_group() -> None:
    """Role-member targets avoid overreaching through the all-fan helper."""
    cooling = _controller(
        FanControllerRole.COOLING,
        members=("fan.ceiling",),
        sensor_entity_id="sensor.temperature",
        on_threshold=75.0,
    )

    result = evaluate_fan_controllers(
        (cooling,),
        current_states=(AreaStates.OCCUPIED,),
        sensor_values={"sensor.temperature": 80.0},
    )
    decision = fan_controller_evaluation_to_control_group(
        evaluation=result,
        fan_group_entity_id="fan.all_room_fans",
        fan_group_state="off",
    )

    assert decision.actions[0].target_entity_ids == ("fan.ceiling",)
