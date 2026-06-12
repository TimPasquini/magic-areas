"""Unit tests for FanControlSwitch with mocked dependencies."""

from typing import cast

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import Event, State
from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.switch import FanControlSwitch
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls import ControlGroupContext
from custom_components.magic_areas.core.controls.policies.fan import FanPolicySignals
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
from custom_components.magic_areas.core.controls.policies.fan import (
    FanClearBehavior,
    FanControllerRole,
    FanDetectionMode,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@pytest.fixture
def mock_area_config() -> AreaConfig:
    """Create a mock AreaConfig."""
    config = MagicMock(spec=AreaConfig)
    config.id = "test_area"
    config.name = "Test Area"
    config.slug = "test_area"
    config.config = {}
    config.icon = None
    config.floor_id = None
    config.area_type = "interior"
    config.hass_config = MagicMock()
    config.hass_config.entry_id = "entry-1"
    return cast(AreaConfig, config)


@pytest.fixture
def mock_coordinator() -> MagicAreasCoordinator:
    """Create a mock coordinator."""
    coordinator = AsyncMock()
    coordinator.data = MagicMock()
    coordinator.data.entity_references = MagicMock()
    coordinator.data.entity_references.area_state_sensor = None
    coordinator.data.entity_references.fan_group = None
    return cast(MagicAreasCoordinator, coordinator)


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock hass object."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=lambda: None)
    hass.async_create_task = MagicMock(
        side_effect=lambda coro: coro.close() if hasattr(coro, "close") else None
    )
    return hass


def test_fan_control_switch_initialization(
    mock_area_config: AreaConfig, mock_coordinator: MagicAreasCoordinator
) -> None:
    """Test FanControlSwitch initialization."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)

    assert switch._area_id == "test_area"
    assert switch.tracked_entity_id is None
    assert switch._area_sensor_entity_id is None
    assert switch._fan_group_entity_id is None


def test_fan_control_area_sensor_state_changed_no_new_state(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test _area_sensor_state_changed when event has no new_state.

    Covers line 202 - the `if not new_state: return` path.
    """
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._attr_name = "Test Switch"  # Mock the name property

    # Create event with no new_state
    event = MagicMock(spec=Event)
    event.data = {"new_state": None}

    # Should return early without error
    result = switch._area_sensor_state_changed(event)
    assert result is None  # callback doesn't return anything

    # Should not have tried to call any services
    mock_hass.async_create_task.assert_not_called()


def test_fan_control_area_sensor_state_changed_not_on(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test _area_sensor_state_changed when switch is off."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = False

    # Create event with OFF state
    new_state = MagicMock(spec=State)
    new_state.state = STATE_OFF
    event = MagicMock(spec=Event)
    event.data = {"new_state": new_state}

    # Should return early because switch is_on is False
    result = switch._area_sensor_state_changed(event)
    assert result is None

    # Should not have tried to call any services
    mock_hass.async_create_task.assert_not_called()


def test_fan_control_area_sensor_state_changed_state_not_off(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test _area_sensor_state_changed when state is not OFF."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True

    # Create event with ON state (not OFF)
    new_state = MagicMock(spec=State)
    new_state.state = STATE_ON
    event = MagicMock(spec=Event)
    event.data = {"new_state": new_state}

    # Should return early because state != STATE_OFF
    result = switch._area_sensor_state_changed(event)
    assert result is None

    mock_hass.async_create_task.assert_not_called()


def test_fan_control_area_sensor_state_changed_no_fan_group(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test _area_sensor_state_changed schedules control reevaluation on CLEAR."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = None  # No fan group found
    switch._attr_name = "Test Switch"  # Mock the name property

    # Create event with OFF state
    new_state = MagicMock(spec=State)
    new_state.state = STATE_OFF
    event = MagicMock(spec=Event)
    event.data = {"new_state": new_state}

    # Should schedule reevaluation even when group resolution is missing.
    result = switch._area_sensor_state_changed(event)
    assert result is None

    mock_hass.async_create_task.assert_called_once()




@pytest.mark.asyncio
async def test_fan_control_run_logic_sensor_value_error(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test run_logic handles ValueError when parsing sensor.

    Covers lines 243-249 - the ValueError/TypeError exception handling.
    """
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.test_fan"
    switch.tracked_entity_id = "sensor.test_sensor"
    switch._attr_name = "Test Switch"  # Mock the name property

    # Mock sensor with non-numeric value
    sensor_state = MagicMock(spec=State)
    sensor_state.state = "not_a_number"
    mock_hass.states.get.return_value = sensor_state

    # Mock the policy
    switch.policy = MagicMock()
    switch.policy.evaluate.return_value = MagicMock(
        should_turn_on=False,
        should_turn_off=False,
        reason="test"
    )

    # Should not raise an exception
    await switch.run_logic(["occupied"])

    # Policy should receive canonical context with normalized signal values.
    switch.policy.evaluate.assert_called_once()
    args = switch.policy.evaluate.call_args[0]
    assert isinstance(args[0], ControlGroupContext)
    assert isinstance(args[0].signals, FanPolicySignals)
    assert args[0].signals.sensor_value is None


@pytest.mark.asyncio
async def test_fan_control_run_logic_sensor_type_error(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test run_logic handles TypeError when parsing sensor."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.test_fan"
    switch.tracked_entity_id = "sensor.test_sensor"
    switch._attr_name = "Test Switch"  # Mock the name property

    # Mock sensor with value that causes TypeError
    sensor_state = MagicMock(spec=State)
    sensor_state.state = {}  # dict can't be converted to float
    mock_hass.states.get.return_value = sensor_state

    # Mock the policy
    switch.policy = MagicMock()
    switch.policy.evaluate.return_value = MagicMock(
        should_turn_on=False,
        should_turn_off=False,
        reason="test"
    )

    # Should not raise an exception
    await switch.run_logic(["occupied"])

    # Policy should receive canonical context with normalized signal values.
    switch.policy.evaluate.assert_called_once()
    args = switch.policy.evaluate.call_args[0]
    assert isinstance(args[0], ControlGroupContext)
    assert isinstance(args[0].signals, FanPolicySignals)
    assert args[0].signals.sensor_value is None


@pytest.mark.asyncio
async def test_fan_control_run_logic_sensor_not_found(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Test run_logic when tracked sensor entity doesn't exist."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.test_fan"
    switch.tracked_entity_id = "sensor.test_sensor"
    switch._attr_name = "Test Switch"  # Mock the name property

    # Sensor state not found
    mock_hass.states.get.return_value = None

    # Mock the policy
    switch.policy = MagicMock()
    switch.policy.evaluate.return_value = MagicMock(
        should_turn_on=False,
        should_turn_off=False,
        reason="test"
    )

    # Should not raise an exception
    await switch.run_logic(["occupied"])

    # Policy should receive canonical context with normalized signal values.
    switch.policy.evaluate.assert_called_once()
    args = switch.policy.evaluate.call_args[0]
    assert isinstance(args[0], ControlGroupContext)
    assert isinstance(args[0].signals, FanPolicySignals)
    assert args[0].signals.sensor_value is None


@pytest.mark.asyncio
async def test_aggregate_sensor_state_uses_area_sensor_fallback(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """aggregate_sensor_state_changed should read area-sensor states when cache is empty."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._last_states = []
    switch._area_sensor_entity_id = "binary_sensor.test_area_state"
    run_logic_mock = AsyncMock()
    monkeypatch.setattr(switch, "run_logic", run_logic_mock)

    area_state = MagicMock()
    area_state.attributes = {
        "states": [AreaStates.OCCUPIED, AreaStates.EXTENDED.value],
    }
    mock_hass.states.get.return_value = area_state

    await switch.aggregate_sensor_state_changed(MagicMock(spec=Event))

    run_logic_mock.assert_awaited_once_with(
        [AreaStates.OCCUPIED.value, AreaStates.EXTENDED.value]
    )


@pytest.mark.asyncio
async def test_run_logic_returns_early_without_resolved_fan_group(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """run_logic should still evaluate policy and emit a NOOP decision."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = None
    switch._attr_name = "Test Switch"
    switch.policy = MagicMock()
    switch.policy.evaluate.return_value = MagicMock(
        action_type="noop",
        actions=(),
        reason="fan_group_unavailable",
    )

    await switch.run_logic(["occupied"])

    switch.policy.evaluate.assert_called_once()


@pytest.mark.asyncio
async def test_run_logic_exposes_fan_controller_debug_attributes(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """run_logic should expose controller reason details on the control switch."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.test_fan"
    switch.tracked_entity_id = "sensor.test_sensor"
    switch._attr_name = "Test Switch"

    def get_state(entity_id: str) -> State | None:
        if entity_id == "sensor.test_sensor":
            return State(entity_id, "30")
        if entity_id == "fan.test_fan":
            return State(entity_id, STATE_OFF)
        return None

    mock_hass.states.get.side_effect = get_state

    await switch.run_logic([AreaStates.OCCUPIED, AreaStates.EXTENDED])

    attrs = switch._attr_extra_state_attributes
    assert attrs["active_fan_reasons"] == ["cooling"]
    assert attrs["suppressed_fan_reasons"] == []
    assert attrs["inactive_fan_reasons"] == []
    assert attrs["target_fan_entities"] == []

    switch._post_clear_hold_until_monotonic = {
        FanControllerRole.HUMIDITY.value: float("inf")
    }
    switch._unavailable_hold_until_monotonic = {
        FanControllerRole.ODOR.value: float("inf")
    }
    switch._write_policy_debug_attributes()

    attrs = switch._attr_extra_state_attributes
    assert attrs["post_clear_hold_fan_reasons"] == ["humidity"]
    assert attrs["unavailable_hold_fan_reasons"] == ["odor"]


@pytest.mark.asyncio
async def test_run_logic_uses_persisted_role_controller_sensors_and_members(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Persisted fan roles read their own sensors and target role members."""
    mock_coordinator.data.feature_configs = {
        MagicAreasFeatures.FAN_GROUPS.value: {
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
                }
            }
        }
    }
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.all_bathroom_fans"
    switch._attr_name = "Test Switch"

    def get_state(entity_id: str) -> State | None:
        if entity_id == "sensor.bathroom_humidity":
            return State(entity_id, "65")
        if entity_id == "fan.all_bathroom_fans":
            return State(entity_id, STATE_OFF)
        return None

    mock_hass.states.get.side_effect = get_state

    await switch.run_logic([AreaStates.OCCUPIED.value])

    mock_hass.services.async_call.assert_awaited_once_with(
        "fan",
        "turn_on",
        {"entity_id": "fan.bathroom"},
        blocking=False,
    )
    attrs = switch._attr_extra_state_attributes
    assert attrs["active_fan_reasons"] == ["humidity"]
    assert attrs["target_fan_entities"] == ["fan.bathroom"]


@pytest.mark.asyncio
async def test_run_logic_uses_threshold_trend_signal_state(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Threshold+trend fan roles consume the managed Trend helper state."""
    mock_coordinator.data.feature_configs = {
        MagicAreasFeatures.FAN_GROUPS.value: {
            CONF_FAN_GROUPS_CONTROLLERS: {
                FanControllerRole.HUMIDITY.value: {
                    CONF_FAN_CONTROLLER_MEMBERS: ["fan.bathroom"],
                    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "sensor.bathroom_humidity",
                    CONF_FAN_CONTROLLER_DETECTION_MODE: (
                        FanDetectionMode.THRESHOLD_TREND.value
                    ),
                    CONF_FAN_CONTROLLER_ON_THRESHOLD: 60,
                    CONF_FAN_CONTROLLER_HYSTERESIS: 5,
                    CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.OCCUPIED.value],
                    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: (
                        FanClearBehavior.RUN_UNTIL_CLEAR.value
                    ),
                }
            }
        }
    }
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.all_bathroom_fans"
    switch._controller_trend_signal_entity_ids = {
        FanControllerRole.HUMIDITY.value: "binary_sensor.bathroom_humidity_rising"
    }
    switch._attr_name = "Test Switch"

    def get_state(entity_id: str) -> State | None:
        if entity_id == "sensor.bathroom_humidity":
            return State(entity_id, "57")
        if entity_id == "binary_sensor.bathroom_humidity_rising":
            return State(entity_id, STATE_ON)
        if entity_id == "fan.all_bathroom_fans":
            return State(entity_id, STATE_OFF)
        return None

    mock_hass.states.get.side_effect = get_state

    await switch.run_logic([AreaStates.OCCUPIED.value])

    mock_hass.services.async_call.assert_awaited_once_with(
        "fan",
        "turn_on",
        {"entity_id": "fan.bathroom"},
        blocking=False,
    )
    assert switch._attr_extra_state_attributes["active_fan_reasons"] == ["humidity"]


@pytest.mark.asyncio
async def test_run_logic_publishes_fan_runtime_area_states(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Active fan controller reasons publish visible area-condition states."""
    mock_coordinator.data.feature_configs = {
        MagicAreasFeatures.FAN_GROUPS.value: {
            CONF_FAN_GROUPS_CONTROLLERS: {
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
                }
            }
        }
    }
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.all_bathroom_fans"
    switch._attr_name = "Test Switch"

    def get_state(entity_id: str) -> State | None:
        if entity_id == "sensor.bathroom_voc":
            return State(entity_id, "250")
        if entity_id == "fan.all_bathroom_fans":
            return State(entity_id, STATE_OFF)
        return None

    mock_hass.states.get.side_effect = get_state

    with patch(
        "custom_components.magic_areas.switch.fan_control.dispatcher_send"
    ) as mock_dispatch:
        await switch.run_logic([AreaStates.OCCUPIED.value])

    mock_dispatch.assert_called_once_with(
        mock_hass,
        "magicareas_area_runtime_states_changed",
        "test_area",
        "fan_groups",
        [AreaStates.ODOR.value],
    )


@pytest.mark.asyncio
async def test_fan_hold_expiry_rechecks_current_area_state(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """The expiry callback should clear its handle and rerun fan policy."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._last_states = [AreaStates.OCCUPIED.value]
    switch._hold_timer_cancel = MagicMock()

    with (
        patch(
            "custom_components.magic_areas.switch.fan_control.resolve_area_presence_states",
            return_value=[AreaStates.OCCUPIED.value, AreaStates.EXTENDED.value],
        ),
        patch.object(switch, "run_logic", new=AsyncMock()) as run_logic,
    ):
        await switch._hold_expiry_check(None)

    assert switch._hold_timer_cancel is None
    run_logic.assert_awaited_once_with(
        [AreaStates.OCCUPIED.value, AreaStates.EXTENDED.value]
    )


@pytest.mark.asyncio
async def test_fan_on_without_active_reason_publishes_no_room_condition_state(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Physical fan state alone must not imply humid, odor, or hot."""
    mock_coordinator.data.feature_configs = {
        MagicAreasFeatures.FAN_GROUPS.value: {
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
                }
            }
        }
    }
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.all_bathroom_fans"
    switch._attr_name = "Test Switch"

    def get_state(entity_id: str) -> State | None:
        if entity_id == "sensor.bathroom_humidity":
            return State(entity_id, "45")
        if entity_id == "fan.all_bathroom_fans":
            return State(entity_id, STATE_ON)
        return None

    mock_hass.states.get.side_effect = get_state

    with patch(
        "custom_components.magic_areas.switch.fan_control.dispatcher_send"
    ) as mock_dispatch:
        await switch.run_logic([AreaStates.OCCUPIED.value])

    mock_dispatch.assert_called_once_with(
        mock_hass,
        "magicareas_area_runtime_states_changed",
        "test_area",
        "fan_groups",
        [],
    )
    assert switch._attr_extra_state_attributes["active_fan_reasons"] == []


@pytest.mark.asyncio
async def test_run_logic_supports_sensorless_odor_room_state_fallback(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: MagicMock,
) -> None:
    """Sensorless odor fallback should run from room-state evidence."""
    mock_coordinator.data.feature_configs = {
        MagicAreasFeatures.FAN_GROUPS.value: {
            CONF_FAN_GROUPS_CONTROLLERS: {
                FanControllerRole.ODOR.value: {
                    CONF_FAN_CONTROLLER_MEMBERS: ["fan.bathroom"],
                    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID: "",
                    CONF_FAN_CONTROLLER_DETECTION_MODE: (
                        FanDetectionMode.ROOM_STATE.value
                    ),
                    CONF_FAN_CONTROLLER_ON_THRESHOLD: 0,
                    CONF_FAN_CONTROLLER_HYSTERESIS: 0,
                    CONF_FAN_CONTROLLER_ACTIVE_STATES: [AreaStates.OCCUPIED.value],
                    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR: (
                        FanClearBehavior.OCCUPANCY_ONLY.value
                    ),
                }
            }
        }
    }
    switch = FanControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch._fan_group_entity_id = "fan.all_bathroom_fans"
    switch._attr_name = "Test Switch"

    def get_state(entity_id: str) -> State | None:
        if entity_id == "fan.all_bathroom_fans":
            return State(entity_id, STATE_OFF)
        return None

    mock_hass.states.get.side_effect = get_state

    await switch.run_logic([AreaStates.OCCUPIED.value])

    mock_hass.services.async_call.assert_awaited_once_with(
        "fan",
        "turn_on",
        {"entity_id": "fan.bathroom"},
        blocking=False,
    )
    assert switch._attr_extra_state_attributes["active_fan_reasons"] == ["odor"]
