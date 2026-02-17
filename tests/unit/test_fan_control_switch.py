"""Unit tests for FanControlSwitch with mocked dependencies."""

from typing import Any

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.core import State, Event
from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.magic_areas.switch.fan_control import FanControlSwitch
from custom_components.magic_areas.core.area_config import AreaConfig


@pytest.fixture
def mock_area_config() -> Any:
    """Create a mock AreaConfig."""
    config = MagicMock(spec=AreaConfig)
    config.id = "test_area"
    config.name = "Test Area"
    config.slug = "test_area"
    config.config = {}
    config.icon = None
    config.floor_id = None
    config.area_type = "interior"
    return config


@pytest.fixture
def mock_coordinator() -> Any:
    """Create a mock coordinator."""
    coordinator = AsyncMock()
    coordinator.data = MagicMock()
    coordinator.data.entity_references = MagicMock()
    coordinator.data.entity_references.area_state_sensor = None
    coordinator.data.entity_references.aggregates_by_device_class = {}
    coordinator.data.entity_references.fan_group = None
    return coordinator


@pytest.fixture
def mock_hass() -> Any:
    """Create a mock hass object."""
    hass = AsyncMock()
    hass.states = MagicMock()
    hass.services = AsyncMock()
    hass.async_create_task = MagicMock()
    return hass


def test_fan_control_switch_initialization(mock_area_config: Any, mock_coordinator: Any) -> None:
    """Test FanControlSwitch initialization."""
    switch = FanControlSwitch(mock_area_config, mock_coordinator)

    assert switch._area_id == "test_area"
    assert switch.tracked_entity_id is None
    assert switch._area_sensor_entity_id is None
    assert switch._fan_group_entity_id is None


def test_fan_control_area_sensor_state_changed_no_new_state(
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
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
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
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
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
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
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
) -> None:
    """Test _area_sensor_state_changed when fan_group_entity_id is None.

    Covers lines 208-212 - the debug log when no fan group.
    """
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

    # Should return early without calling any services
    result = switch._area_sensor_state_changed(event)
    assert result is None

    mock_hass.async_create_task.assert_not_called()




@pytest.mark.asyncio
async def test_fan_control_run_logic_sensor_value_error(
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
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

    # Policy should be called with None sensor_value due to parse error
    switch.policy.evaluate.assert_called_once()
    args = switch.policy.evaluate.call_args[0]
    assert args[1] is None  # sensor_value should be None due to exception


@pytest.mark.asyncio
async def test_fan_control_run_logic_sensor_type_error(
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
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

    # Policy should be called with None sensor_value
    switch.policy.evaluate.assert_called_once()
    args = switch.policy.evaluate.call_args[0]
    assert args[1] is None


@pytest.mark.asyncio
async def test_fan_control_run_logic_sensor_not_found(
    mock_area_config: Any, mock_coordinator: Any, mock_hass: Any
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

    # Policy should be called with None sensor_value
    switch.policy.evaluate.assert_called_once()
    args = switch.policy.evaluate.call_args[0]
    assert args[1] is None


