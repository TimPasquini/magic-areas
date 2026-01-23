"""Fixtures for tests.

Fixtures are organized into sections:
- Core fixtures: Enable integration testing in HA environment
- Autouse fixtures: Applied to all tests automatically
- Timer fixtures: For tests involving async timers/delays
- Config entry fixtures: Mock configuration entries for areas
- Entity fixtures: Pre-built mock entities for platforms
"""

from collections.abc import AsyncGenerator
import logging
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_FLOOR_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.floor_registry import async_get as async_get_fr

from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_ENABLED_FEATURES,
    CONF_ID,
    CONF_TYPE,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
)
from custom_components.magic_areas.enums import (
    AreaType,
)

from tests.const import DEFAULT_MOCK_AREA, MOCK_AREAS, MockAreaIds
from tests.helpers import (
    get_basic_config_entry_data,
    immediate_call_factory,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor, MockLight

_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CORE FIXTURES - Applied automatically to all tests
# ============================================================================


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> AsyncGenerator[None, None]:
    """Enable custom integration in test environment.

    This fixture is automatically applied to all tests. It allows the Magic Areas
    custom integration to be loaded during testing. Required for all integration
    tests.

    Status: MUST KEEP - Required for all tests
    """
    _ = enable_custom_integrations  # unused
    yield


@pytest.fixture(autouse=True)
def mock_http_start_server():
    """Mock HTTP start server to prevent socket binding.

    This fixture is automatically applied to all tests. It patches the HTTP
    server startup to prevent tests from attempting to bind to actual network
    sockets, which would fail in test environments.

    Status: MUST KEEP - Prevents network binding errors
    """
    with patch("homeassistant.components.http.start_http_server_and_save_config"):
        yield


@pytest.fixture(autouse=True)
def patch_reload_settings():
    """Patch meta-area reload settings for instant reload during testing.

    This fixture is automatically applied to all tests. It sets reload delays
    to 0, allowing meta-area reload logic to execute immediately without waiting.
    This is critical for test speed and determinism.

    Patched settings:
    - MetaAreaAutoReloadSettings.DELAY = 0
    - MetaAreaAutoReloadSettings.DELAY_MULTIPLIER = 1
    - MetaAreaAutoReloadSettings.THROTTLE = 0

    Status: SHOULD REVIEW - Needed only by tests that reload meta-areas
    """
    with patch(
        "custom_components.magic_areas.base.magic.MetaAreaAutoReloadSettings"
    ) as mock_settings:
        mock_settings.DELAY = 0
        mock_settings.DELAY_MULTIPLIER = 1
        mock_settings.THROTTLE = 0
        yield


# ============================================================================
# TIMER FIXTURES - For tests involving async timers and delayed callbacks
# ============================================================================


@pytest.fixture
def patch_async_call_later(hass):
    """Patch async_call_later to execute immediately for faster testing.

    Use this fixture when your test involves:
    - Timer-based presence clearing (CONF_CLEAR_TIMEOUT)
    - Extended presence timeouts (CONF_EXTENDED_TIMEOUT)
    - ReusableTimer logic
    - Switch base timer operations

    This fixture makes timers execute immediately instead of waiting, which
    speeds up tests significantly. Without this fixture, timer tests would
    need to use hass.async_block_till_done() extensively.

    Example:
        async def test_timeout(hass, patch_async_call_later):
            # Timer will execute immediately
            await asyncio.sleep(10)  # No actual delay needed
    """
    with (
        patch(
            "custom_components.magic_areas.helpers.timer.async_call_later",
            side_effect=immediate_call_factory(hass),
        ),
        patch(
            "custom_components.magic_areas.switch.base.async_call_later",
            side_effect=immediate_call_factory(hass),
        ),
    ):
        yield


# ============================================================================
# CONFIG ENTRY FIXTURES - Pre-built mock configuration entries
# ============================================================================


@pytest.fixture
async def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock config entry for the default test area.

    Creates a single configuration entry for DEFAULT_MOCK_AREA with basic
    settings. This is the most common fixture for single-area tests.

    Returns:
        MockConfigEntry: A configured entry ready for use in tests

    Example:
        async def test_something(hass, mock_config_entry, init_integration):
            # Test with the configured area
            pass
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    # Set unique_id to match the area ID from the data
    area_id = data.get(CONF_ID, DEFAULT_MOCK_AREA.value)
    entry: MockConfigEntry = MockConfigEntry(
        domain=DOMAIN, data=data, unique_id=area_id  # Add this line!
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture(name="all_areas_with_meta_config_entry")
async def mock_config_entry_all_areas_with_meta_config_entry() -> list[MockConfigEntry]:
    """Create mock config entries for all test areas with aggregation enabled.

    Creates configuration entries for all MockAreaIds (bedroom, kitchen, etc.)
    and enables the CONF_FEATURE_AGGREGATION feature with default settings.

    This fixture is useful for meta-area and aggregation tests where you need
    multiple areas with consistent feature configurations.

    Returns:
        list[MockConfigEntry]: One entry per area with aggregation enabled

    Example:
        async def test_meta_area(hass, all_areas_with_meta_config_entry, init_integration):
            # Test with all areas set up and aggregation enabled
            pass
    """

    config_entries: list[MockConfigEntry] = []
    for area_entry in MockAreaIds:
        data = get_basic_config_entry_data(area_entry)
        data.update(
            {
                CONF_ENABLED_FEATURES: {
                    CONF_FEATURE_AGGREGATION: {
                        CONF_AGGREGATES_MIN_ENTITIES: 1,
                        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 10,
                    }
                }
            }
        )
        # Set unique_id to match the area ID
        area_id = data.get(CONF_ID, area_entry.value)
        config_entries.append(
            MockConfigEntry(
                domain=DOMAIN, data=data, unique_id=area_id  # Add this line!
            )
        )

    return config_entries


# ============================================================================
# ENTITY FIXTURES - Pre-built mock entities for different platforms
# ============================================================================


@pytest.fixture(name="entities_binary_sensor_motion_one")
async def setup_entities_binary_sensor_motion_one(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create one mock sensor and set up the system with it."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="motion_sensor",
            unique_id="unique_motion",
            device_class=BinarySensorDeviceClass.MOTION,
        )
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_binary_sensor_motion_multiple")
async def setup_entities_binary_sensor_motion_multiple(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create multiple mock sensor and set up the system with it."""
    nr_entities = 3
    mock_binary_sensor_entities = []
    for i in range(nr_entities):
        mock_binary_sensor_entities.append(
            MockBinarySensor(
                name=f"motion_sensor_{i}",
                unique_id=f"motion_sensor_{i}",
                device_class=BinarySensorDeviceClass.MOTION,
            )
        )
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_binary_sensor_motion_all_areas_with_meta")
async def setup_entities_binary_sensor_motion_all_areas_with_meta(
    hass: HomeAssistant,
) -> dict[MockAreaIds, list[MockBinarySensor]]:
    """Create multiple mock sensor and set up the system with it."""

    mock_binary_sensor_entities: dict[MockAreaIds, list[MockBinarySensor]] = {}

    for area in MockAreaIds:
        assert area is not None
        area_object = MOCK_AREAS[area]
        assert area_object is not None
        if area_object[CONF_TYPE] == AreaType.META:
            continue

        mock_sensor = MockBinarySensor(
            name=f"motion_sensor_{area.value}",
            unique_id=f"motion_sensor_{area.value}",
            device_class=BinarySensorDeviceClass.MOTION,
        )

        mock_binary_sensor_entities[area] = [
            mock_sensor,
        ]

    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)

    return mock_binary_sensor_entities


@pytest.fixture(name="entities_light_one")
async def setup_entities_light_one(
    hass: HomeAssistant,
) -> list[MockLight]:
    """Create one mock light and set up the system with it."""
    mock_light_entities = [
        MockLight(
            name="mock_light_1",
            state="off",
            unique_id="unique_light",
        )
    ]
    await setup_mock_entities(
        hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: mock_light_entities}
    )
    return mock_light_entities


# Integration setups


@pytest.fixture(name="init_integration_fixture")
async def init_integration_fixture(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> AsyncGenerator[MockConfigEntry, None]:
    """Set up the integration."""

    # Setup area registry
    area_registry = async_get_ar(hass)
    floor_registry = async_get_fr(hass)

    # We assume DEFAULT_MOCK_AREA for the basic mock_config_entry
    area = DEFAULT_MOCK_AREA
    area_object = MOCK_AREAS[area]
    floor_id: str | None = None

    if area_object[ATTR_FLOOR_ID]:
        floor_name = str(area_object[ATTR_FLOOR_ID])
        floor_entry = floor_registry.async_get_floor_by_name(floor_name)
        if not floor_entry:
            floor_entry = floor_registry.async_create(floor_name)
        floor_id = floor_entry.floor_id
    area_registry.async_create(name=area.value, floor_id=floor_id)

    if not hass.config_entries.async_get_entry(mock_config_entry.entry_id):
        mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    yield mock_config_entry

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture(name="_setup_integration_basic")
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with basic config."""
    # This fixture is kept for backward compatibility with other tests,
    # but it now uses the new mock_config_entry fixture

    # We need to manually call the helper init because the new init_integration fixture
    # is designed to be used directly, but this fixture wraps the old helper.
    # However, since mock_config_entry already adds itself to hass, we need to be careful.

    # The old helper init_integration does:
    # 1. Register areas
    # 2. Add config entries to hass (if not already added)
    # 3. async_setup_component(hass, DOMAIN, {})

    # Since mock_config_entry adds itself to hass, step 2 is partially done.

    await init_integration_helper(hass, [mock_config_entry])
    yield
    await shutdown_integration(hass, [mock_config_entry])


@pytest.fixture(name="init_integration_all_areas")
async def init_integration_all_areas(
    hass: HomeAssistant,
    all_areas_with_meta_config_entry: list[MockConfigEntry],
) -> AsyncGenerator[list[MockConfigEntry], None]:
    """Set up integration with all areas and meta-areas."""

    area_registry = async_get_ar(hass)
    floor_registry = async_get_fr(hass)

    # Create areas in registry
    for area_enum in MockAreaIds:
        area_object = MOCK_AREAS[area_enum]
        if area_object[CONF_TYPE] == AreaType.META:
            continue

        floor_id: str | None = None
        if area_object[ATTR_FLOOR_ID]:
            floor_name = str(area_object[ATTR_FLOOR_ID])
            floor_entry = floor_registry.async_get_floor_by_name(floor_name)
            if not floor_entry:
                floor_entry = floor_registry.async_create(floor_name)
            floor_id = floor_entry.floor_id

        area_registry.async_create(name=area_enum.value, floor_id=floor_id)

    # Add and setup all config entries
    for entry in all_areas_with_meta_config_entry:
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)

    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    yield all_areas_with_meta_config_entry

    # Unload
    for entry in all_areas_with_meta_config_entry:
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
async def init_integration(
    init_integration_fixture: MockConfigEntry,
) -> AsyncGenerator[MockConfigEntry, None]:
    """Alias for init_integration_fixture to support existing tests."""
    yield init_integration_fixture
