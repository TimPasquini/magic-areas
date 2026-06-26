"""Config-entry builders shared across Magic Areas tests."""

from homeassistant.const import ATTR_NAME

from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
)
from tests.const import MOCK_AREAS, MockAreaIds


def get_basic_config_entry_data(area_id: MockAreaIds) -> dict[str, object]:
    """Create basic config entry data for a test area.

    Generates a minimal but valid configuration dictionary for an area that
    can be used with MockConfigEntry. This is the primary factory function
    for creating test configurations.

    Args:
        area_id: The MockAreaIds enum value identifying the area.

    Returns:
        dict[str, Any]: A configuration dictionary with:
            - ATTR_NAME: Human-readable area name
            - CONF_ID: Area ID string
            - CONF_CLEAR_TIMEOUT: Timeout in seconds (set to 0 for testing)
            - CONF_EXTENDED_TIMEOUT: Extended timeout in seconds (5 seconds)
            - CONF_TYPE: Area type from MOCK_AREAS
            - CONF_EXCLUDE_ENTITIES: Empty list (no excluded entities)
            - CONF_INCLUDE_ENTITIES: Empty list (no extra entities)
            - CONF_PRESENCE_SENSOR_DEVICE_CLASS: Default presence sensor class
            - CONF_ENABLED_FEATURES: Empty dict (can add features later)

    Raises:
        AssertionError: If the area_id is not found in MOCK_AREAS.

    Example:
        Create a config entry for the master bedroom area:

        >>> config_data = get_basic_config_entry_data(MockAreaIds.MASTER_BEDROOM)
        >>> config_entry = MockConfigEntry(domain=DOMAIN, data=config_data)
        >>> # Now add features to config_data if needed
        >>> config_data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_LIGHT_GROUPS: {...}}

    """

    area_data = MOCK_AREAS.get(area_id, None)

    assert area_data is not None

    data = {
        ATTR_NAME: area_id.title(),
        CONF_ID: area_id.value,
        CONF_CLEAR_TIMEOUT: 0,
        CONF_EXTENDED_TIMEOUT: 5,
        CONF_TYPE: area_data[CONF_TYPE],
        CONF_EXCLUDE_ENTITIES: [],
        CONF_INCLUDE_ENTITIES: [],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        CONF_ENABLED_FEATURES: {},
    }

    return data
