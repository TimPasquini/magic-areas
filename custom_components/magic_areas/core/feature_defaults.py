"""Feature default values grouped in one module to reduce tiny-file sprawl."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass

from custom_components.magic_areas.area_state import AreaStates

DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR = ""
DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED = ""
DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED = ""
DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP = ""

DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS = SensorDeviceClass.TEMPERATURE
DEFAULT_FAN_GROUPS_REQUIRED_STATE = AreaStates.EXTENDED
DEFAULT_FAN_GROUPS_SETPOINT = 0.0

DEFAULT_PRESENCE_HOLD_TIMEOUT = 0

DEFAULT_NOTIFY_STATES = [AreaStates.EXTENDED]

DEFAULT_WASP_IN_A_BOX_DELAY = 90
DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT = 0
DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES = [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
]
