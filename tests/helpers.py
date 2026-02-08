"""Common test helpers for magic-areas integration.

This module provides comprehensive testing utilities organized into functional categories:

MODULE ORGANIZATION:
    1. Integration Setup Helpers: Configure and initialize the magic-areas integration
       - setup_test_component_platform: Create mock test component platforms
       - mock_integration: Register mock integrations in Home Assistant
       - mock_platform: Register mock platforms for testing
       - async_mock_service: Set up fake services with call logging

    2. Test Setup Helpers: Initialization and teardown of full test environments
       - init_integration: Set up areas, registries, and config entries
       - shutdown_integration: Cleanly unload the integration
       - setup_mock_entities: Register mock entities with areas

    3. Async/Timing Helpers: Manage asyncio virtual time for deterministic testing
       - VirtualClock: Virtual clock class for time-based tests

    4. Configuration Helpers: Create and manage test configuration
       - get_basic_config_entry_data: Generate default config entry data

    5. State Management Helpers: Verify and wait for entity state changes
       - assert_state: Verify an entity's current state
       - assert_attribute: Check specific entity attributes
       - assert_in_attribute: Verify attribute contains expected value
       - wait_for_state: Async wait for entity state change
       - immediate_call_factory: Create timer callback factories

USAGE PATTERNS:
    - Fixtures use init_integration() to set up the full test environment with areas
    - Mock entities are created with setup_mock_entities() for component testing
    - State assertions use assert_state() and wait_for_state() for verification
    - Virtual clock enables deterministic timing tests without real delays

INTEGRATION FLOW:
    1. Use setup_test_component_platform() to register mock component platforms
    2. Use init_integration() to initialize areas, registries, and config entries
    3. Use setup_mock_entities() to register mock entities in specified areas
    4. Use assert_state() and wait_for_state() to verify entity state changes
    5. Use shutdown_integration() to cleanly unload and verify cleanup
"""

import asyncio
import functools
import logging
import pathlib
from asyncio import get_running_loop
from collections.abc import Sequence
from typing import Any, NoReturn
from unittest.mock import Mock, patch

import voluptuous as vol
from homeassistant import loader
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import ATTR_FLOOR_ID, ATTR_NAME, CONF_PLATFORM
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    State,
    SupportsResponse,
    callback,
)
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.floor_registry import async_get as async_get_fr
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.setup import async_setup_component
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
)
from tests.const import DEFAULT_MOCK_AREA, MOCK_AREAS, MockAreaIds
from tests.mocks import MockModule, MockPlatform

_LOGGER = logging.getLogger(__name__)

# ============================================================================
# INTEGRATION SETUP HELPERS
# ============================================================================
# These helpers set up mock integrations, platforms, and services for testing.
# They provide the foundation for initializing Home Assistant test environments.


def setup_test_component_platform(
    hass: HomeAssistant,
    domain: str,
    entities: Sequence[Entity],
    from_config_entry: bool = False,
    built_in: bool = True,
) -> MockPlatform:
    """Create a mock test component platform with entities.

    This helper creates and registers a mock platform that provides entities to
    Home Assistant for testing. The platform can be configured to use either
    config entry setup or platform setup mode.

    Args:
        hass: The Home Assistant instance.
        domain: The component domain (e.g., 'light', 'switch').
        entities: Sequence of Entity objects to register with the platform.
        from_config_entry: If True, use config entry setup mode; if False, use
            platform setup mode. Determines whether async_setup_entry or
            async_setup_platform is used. Default: False.
        built_in: If True, register as a built-in Home Assistant integration;
            if False, register as a custom component. Default: True.

    Returns:
        MockPlatform: The created mock platform instance.

    Example:
        Create a mock light platform with two test lights:

        >>> light1 = MockLight(name="Living Room", unique_id="light_1")
        >>> light2 = MockLight(name="Kitchen", unique_id="light_2")
        >>> platform = setup_test_component_platform(
        ...     hass, "light", [light1, light2], from_config_entry=True
        ... )
    """

    async def _async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> None:
        """Set up a test component platform."""
        async_add_entities(entities)

    platform = MockPlatform(
        async_setup_platform=_async_setup_platform,
    )

    # avoid creating config entry setup if not needed
    if from_config_entry:

        async def _async_setup_entry(
            hass: HomeAssistant,
            entry: ConfigEntry,
            async_add_entities: AddEntitiesCallback,
        ) -> None:
            """Set up a test component platform."""
            async_add_entities(entities)

        platform.async_setup_entry = _async_setup_entry
        platform.async_setup_platform = None

    mock_platform(hass, f"test.{domain}", platform, built_in=built_in)
    return platform


def mock_integration(
    hass: HomeAssistant, *, module: MockModule, built_in: bool = True
) -> loader.Integration:
    """Register a mock integration with Home Assistant.

    This helper creates and registers a mock integration (component) with Home
    Assistant's loader system. The integration appears fully initialized to
    Home Assistant but uses mock code for testing purposes.

    Args:
        hass: The Home Assistant instance.
        module: MockModule instance containing the integration code and metadata.
        built_in: If True, register as built-in; if False, register as custom
            component. Default: True.

    Returns:
        loader.Integration: The registered integration object.

    Note:
        Platform imports are intentionally blocked to prevent loading actual
        platform code during tests. Use mock_platform() to register specific
        mock platforms for testing.

    Example:
        Register a mock integration for testing:

        >>> test_module = MockModule("test_domain")
        >>> integration = mock_integration(hass, module=test_module)
        >>> assert integration.domain == "test_domain"
    """
    integration = loader.Integration(
        hass,
        (
            f"{loader.PACKAGE_BUILTIN}.{module.DOMAIN}"
            if built_in
            else f"{loader.PACKAGE_CUSTOM_COMPONENTS}.{module.DOMAIN}"
        ),
        pathlib.Path(""),
        module.mock_manifest(),
        set(),
    )

    def mock_import_platform(platform_name: str) -> NoReturn:
        raise ImportError(
            f"Mocked unable to import platform '{integration.pkg_path}.{platform_name}'",
            name=f"{integration.pkg_path}.{platform_name}",
        )

    # pylint: disable-next=protected-access
    integration._import_platform = mock_import_platform

    _LOGGER.info("Adding mock integration: %s", module.DOMAIN)
    integration_cache = hass.data[loader.DATA_INTEGRATIONS]
    integration_cache[module.DOMAIN] = integration

    module_cache = hass.data[loader.DATA_COMPONENTS]
    module_cache[module.DOMAIN] = module

    return integration


def mock_platform(
    hass: HomeAssistant,
    platform_path: str,
    module: Mock | MockPlatform | None = None,
    built_in=True,
) -> None:
    """Register a mock platform with Home Assistant.

    Registers a platform (like light.test, switch.test, etc.) with Home
    Assistant's loader system. If the integration doesn't exist, it creates
    a mock integration automatically.

    Args:
        hass: The Home Assistant instance.
        platform_path: Platform path in format 'domain.platform_name'
            (e.g., 'light.test', 'switch.test', 'binary_sensor.test').
        module: The mock module to register. Can be a Mock() or MockPlatform.
            If None, an empty Mock() is created. Default: None.
        built_in: If True, register integration as built-in; if False, register
            as custom component. Default: True.

    Note:
        The integration must exist before the platform can be registered. If
        the integration doesn't exist, this function automatically creates
        a mock integration with the given domain.

    Example:
        Register a test light platform with setup code:

        >>> platform = MockPlatform(async_setup_platform=setup_func)
        >>> mock_platform(hass, "light.test", platform)
    """
    domain, _, platform_name = platform_path.partition(".")
    integration_cache = hass.data[loader.DATA_INTEGRATIONS]
    module_cache = hass.data[loader.DATA_COMPONENTS]

    if domain not in integration_cache:
        mock_integration(hass, module=MockModule(domain), built_in=built_in)

    # pylint: disable-next=protected-access
    integration_cache[domain]._top_level_files.add(f"{platform_name}.py")
    _LOGGER.info("Adding mock integration platform: %s", platform_path)
    module_cache[platform_path] = module or Mock()


def async_mock_service(
    *,
    hass: HomeAssistant,
    domain: str,
    service: str,
    schema: vol.Schema | None = None,
    response: ServiceResponse = None,
    supports_response: SupportsResponse | None = None,
    raise_exception: Exception | None = None,
) -> list[ServiceCall]:
    """Register a mock service and return its call log.

    Creates a fake service that logs all calls for assertion in tests. The
    service can optionally return a response, raise an exception, or execute
    without side effects.

    Args:
        hass: The Home Assistant instance.
        domain: Service domain (e.g., 'light', 'switch').
        service: Service name (e.g., 'turn_on', 'turn_off').
        schema: Optional voluptuous schema to validate service calls.
            Default: None (no validation).
        response: Optional response to return from service calls.
            Default: None.
        supports_response: Whether service supports response. If None, auto-
            detects based on whether response is provided. Default: None.
        raise_exception: Optional exception to raise when service is called.
            Default: None (service succeeds).

    Returns:
        list[ServiceCall]: A list that will contain all ServiceCall objects
            passed to this service. Use this for assertions in tests.

    Example:
        Create a mock light.turn_on service and verify it was called:

        >>> calls = async_mock_service(
        ...     hass=hass, domain="light", service="turn_on"
        ... )
        >>> # Later in test...
        >>> hass.async_create_task(
        ...     hass.services.async_call("light", "turn_on", ...)
        ... )
        >>> await hass.async_block_till_done()
        >>> assert len(calls) == 1
        >>> assert calls[0].data["entity_id"] == "light.test"
    """
    calls = []

    @callback
    def mock_service_log(call):  # pylint: disable=unnecessary-lambda
        """Mock service call."""
        calls.append(call)
        if raise_exception is not None:
            raise raise_exception
        return response

    if supports_response is None:
        if response is not None:
            supports_response = SupportsResponse.OPTIONAL
        else:
            supports_response = SupportsResponse.NONE

    hass.services.async_register(
        domain,
        service,
        mock_service_log,
        schema=schema,
        supports_response=supports_response,
    )

    return calls


# ============================================================================
# TEST SETUP HELPERS
# ============================================================================
# These helpers initialize and tear down complete test environments with
# areas, registries, config entries, and entities.


async def init_integration(
    hass: HomeAssistant,
    config_entries: list[MockConfigEntry],
    areas: list[MockAreaIds] | None = None,
) -> None:
    """Initialize the magic-areas integration with areas and config entries.

    Sets up a complete test environment by creating area and floor registries,
    registering configuration entries, and loading the magic-areas integration.
    This is the primary setup function for integration-level tests.

    Args:
        hass: The Home Assistant instance to set up.
        config_entries: List of MockConfigEntry objects to register and load.
            Each config entry should have valid area IDs and configuration.
        areas: List of MockAreaIds to create as areas in the area registry.
            If None, uses DEFAULT_MOCK_AREA. Each area can optionally be
            associated with a floor. Default: None.

    Raises:
        AssertionError: If the integration fails to load or config entries
            don't reach LOADED state.

    Note:
        This function performs the following steps:
        1. Creates floor and area registries
        2. Registers specified areas (and their floors if applicable)
        3. Adds config entries to Home Assistant
        4. Sets up the magic-areas integration component
        5. Verifies all config entries are in LOADED state

    Example:
        Set up integration with custom kitchen and living room areas:

        >>> from tests.const import MockAreaIds
        >>> config_entry = MockConfigEntry(
        ...     domain=DOMAIN, data=get_basic_config_entry_data(MockAreaIds.KITCHEN)
        ... )
        >>> await init_integration(
        ...     hass, [config_entry],
        ...     areas=[MockAreaIds.KITCHEN, MockAreaIds.LIVING_ROOM]
        ... )
    """

    if not areas:
        areas = [DEFAULT_MOCK_AREA]

    area_registry = async_get_ar(hass)
    floor_registry = async_get_fr(hass)

    # Register areas
    for area in areas:
        area_object = MOCK_AREAS[area]
        floor_id: str | None = None

        if area_object[ATTR_FLOOR_ID]:
            assert area_object[ATTR_FLOOR_ID] is not None
            floor_name = str(area_object[ATTR_FLOOR_ID])
            floor_entry = floor_registry.async_get_floor_by_name(floor_name)
            if not floor_entry:
                floor_entry = floor_registry.async_create(floor_name)
            assert floor_entry is not None
            floor_id = floor_entry.floor_id
        area_registry.async_create(name=area.value, floor_id=floor_id)

    for config_entry in config_entries:
        if hass.config_entries.async_get_entry(config_entry.entry_id):
            continue
        config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    for config_entry in config_entries:
        assert config_entry.state is ConfigEntryState.LOADED

    # Trigger a second coordinator refresh so entity_references picks up
    # the magic_areas entities that were just created during platform setup.
    for config_entry in config_entries:
        runtime_data = getattr(config_entry, "runtime_data", None)
        if runtime_data and hasattr(runtime_data, "coordinator"):
            await runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def shutdown_integration(
    hass: HomeAssistant, config_entries: list[MockConfigEntry]
) -> None:
    """Cleanly unload the magic-areas integration and verify cleanup.

    Unloads all config entries and verifies that the integration data is
    properly cleaned up. Use this function in test teardown or cleanup phases.

    Args:
        hass: The Home Assistant instance to shut down.
        config_entries: List of MockConfigEntry objects to unload. Should be
            the same entries passed to init_integration().

    Raises:
        AssertionError: If the integration data is not properly cleaned up or
            config entries don't reach NOT_LOADED state.

    Note:
        This function performs the following steps:
        1. Unloads all specified config entries
        2. Verifies the magic-areas domain data is cleared from hass.data
        3. Verifies all config entries are in NOT_LOADED state
        4. Logs the unload completion

    Example:
        Clean up after test:

        >>> await shutdown_integration(hass, [config_entry])
    """

    _LOGGER.info("Unloading integration.")
    for config_entry in config_entries:
        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)

    for config_entry in config_entries:
        assert config_entry.state is ConfigEntryState.NOT_LOADED
    _LOGGER.info("Integration unloaded.")


async def setup_mock_entities(
    hass: HomeAssistant, domain: str, area_entity_map: dict[MockAreaIds, list[Any]]
) -> None:
    """Set up multiple mock entities and assign them to areas.

    Creates a mock component platform, registers entities with it, and assigns
    each entity to a specific area in the entity registry. This is the primary
    function for creating test entities that are aware of areas.

    Args:
        hass: The Home Assistant instance.
        domain: The component domain for entities (e.g., 'light', 'switch',
            'binary_sensor', 'sensor').
        area_entity_map: Mapping of area IDs to lists of Entity objects.
            Each entity in the lists will be assigned to the corresponding area.

    Raises:
        AssertionError: If component setup fails, entities don't get entity_ids,
            or area assignment fails.

    Note:
        The function performs these steps:
        1. Creates a mock platform for the domain using all entities
        2. Sets up the component with the mock platform
        3. Waits for all entities to receive entity_ids
        4. Updates the entity registry to assign each entity to its area
        5. Verifies all assignments completed successfully

    Example:
        Create lights in kitchen and living room areas:

        >>> light_kitchen = MockLight(name="Kitchen", unique_id="light_k1")
        >>> light_living = MockLight(name="Living", unique_id="light_l1")
        >>> await setup_mock_entities(
        ...     hass, "light",
        ...     {
        ...         MockAreaIds.KITCHEN: [light_kitchen],
        ...         MockAreaIds.LIVING_ROOM: [light_living],
        ...     }
        ... )
    """

    all_entities: list[Any] = []
    entity_area_map: dict[Any, MockAreaIds] = {}

    for area_id, entity_list in area_entity_map.items():
        for entity in entity_list:
            all_entities.append(entity)
            entity_area_map[entity.unique_id] = area_id

    # Setup entities
    setup_test_component_platform(hass, domain, all_entities)
    assert await async_setup_component(hass, domain, {domain: {CONF_PLATFORM: "test"}})
    await hass.async_block_till_done()

    # Update area IDs
    entity_registry = async_get_er(hass)
    for entity in all_entities:
        assert entity is not None

        # Wait for entity_id to be set
        if entity.entity_id is None:
            for _ in range(10):
                if entity.entity_id is not None:
                    break
                await hass.async_block_till_done()
                await asyncio.sleep(0.1)

        if entity.entity_id is None:
            raise AssertionError(
                f"Entity {entity.unique_id} did not get an entity_id assigned"
            )

        entity_entry = entity_registry.async_get(entity.entity_id)
        if entity_entry:
            entity_registry.async_update_entity(
                entity.entity_id,
                area_id=entity_area_map[entity.unique_id].value,
            )
    await hass.async_block_till_done()


# ============================================================================
# ASYNC/TIMING HELPERS
# ============================================================================
# Virtual clock for deterministic time-based testing.


class VirtualClock:
    """Provide a virtual clock for an asyncio event loop.

    This class enables deterministic testing of time-dependent code by replacing
    real time with a virtual time that advances instantly. Tests using this clock
    complete immediately instead of waiting for real-world delays.

    The clock works by:
    1. Patching the event loop's time() method to return virtual time
    2. Making asyncio.sleep() return instantly while advancing virtual time
    3. Setting clock resolution to 0.1 for predictable timing

    Attributes:
        vtime (float): The current virtual time in seconds.

    Example:
        Use virtual clock in a timing test:

        >>> virtual_clock = VirtualClock()
        >>> @pytest.mark.asyncio
        ... async def test_delayed_action():
        ...     with virtual_clock.patch_loop():
        ...         # This completes instantly instead of waiting 60 seconds
        ...         await asyncio.sleep(60)
        ...         assert virtual_clock.vtime == 60.0
    """

    def __init__(self) -> None:
        """Initialize the clock with a simple time.

        Sets vtime to 0.0, representing the start of virtual time.
        """
        self.vtime = 0.0

    def virtual_time(self) -> float:
        """Return the current virtual time.

        Returns:
            float: The current virtual time in seconds.
        """
        return self.vtime

    def _virtual_select(self, orig_select, timeout):
        """Override select() to advance virtual time without blocking.

        When asyncio's event loop calls select() with a timeout, we advance
        the virtual time by that timeout and then call the original select()
        with a 0 timeout, making it return immediately.

        Args:
            orig_select: The original event loop select method.
            timeout: The timeout requested by the event loop.

        Returns:
            The result of calling orig_select with 0 timeout.
        """
        if timeout is not None:
            self.vtime += timeout
        return orig_select(0)  # override the timeout to zero

    def patch_loop(self):
        """Override methods of the current event loop for virtual time.

        This is a context manager that patches the running event loop so that:
        - asyncio.sleep() returns instantly
        - loop.time() returns virtual time
        - The clock resolution is set to 0.1 seconds

        Yields:
            None: Use in a 'with' statement context.

        Example:
            with virtual_clock.patch_loop():
                # All asyncio code here uses virtual time
                await some_async_function()
        """
        loop = get_running_loop()
        with (
            patch.object(
                loop._selector,  # pylint: disable=protected-access
                "select",
                new=functools.partial(
                    self._virtual_select,
                    loop._selector.select,  # pylint: disable=protected-access
                ),
            ),
            patch.object(
                loop,
                "time",
                new=self.virtual_time,
            ),
            patch.object(
                loop,
                "_clock_resolution",
                new=0.1,
            ),
        ):
            yield


# ============================================================================
# CONFIGURATION HELPERS
# ============================================================================
# Helpers to create and manage test configuration.


def get_basic_config_entry_data(area_id: MockAreaIds) -> dict[str, Any]:
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
        Create a config entry for the bedroom area:

        >>> config_data = get_basic_config_entry_data(MockAreaIds.BEDROOM)
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


# ============================================================================
# STATE MANAGEMENT HELPERS
# ============================================================================
# Helpers for verifying and waiting for entity state changes.


def assert_state(entity_state: State | None, expected_value: str) -> None:
    """Assert that an entity's state matches an expected value.

    Verifies that an entity exists and has the exact state specified. Use this
    for immediate state checks after an action.

    Args:
        entity_state: The State object from hass.states.get(entity_id), or None
            if the entity doesn't exist.
        expected_value: The expected state value as a string (e.g., 'on', 'off',
            '20' for temperature, 'unknown').

    Raises:
        AssertionError: If entity_state is None or state doesn't match
            expected_value.

    Example:
        Verify a light is on:

        >>> state = hass.states.get("light.kitchen")
        >>> assert_state(state, "on")
    """

    assert entity_state is not None
    assert entity_state.state == expected_value


def assert_attribute(
    entity_state: State | None, attribute_key: str, expected_value: str
) -> None:
    """Assert that an entity attribute equals an expected value.

    Verifies that an entity has a specific attribute with an exact value. The
    expected value is converted to a string for comparison, allowing type-
    flexible assertions.

    Args:
        entity_state: The State object from hass.states.get(entity_id), or None
            if the entity doesn't exist.
        attribute_key: The name of the attribute to check (e.g., 'brightness',
            'temperature', 'color_mode').
        expected_value: The expected attribute value as a string.

    Raises:
        AssertionError: If entity_state is None, the attribute doesn't exist,
            or the value doesn't match expected_value.

    Example:
        Verify light brightness:

        >>> state = hass.states.get("light.bedroom")
        >>> assert_attribute(state, "brightness", "200")
    """

    assert entity_state is not None
    assert hasattr(entity_state, "attributes")
    assert attribute_key in entity_state.attributes
    assert str(entity_state.attributes[attribute_key]) == expected_value


def assert_in_attribute(
    entity_state: State | None,
    attribute_key: str,
    expected_value: str,
    negate: bool = False,
) -> None:
    """Assert that an attribute contains (or doesn't contain) an expected value.

    Verifies that a specific substring or item exists (or doesn't exist) in an
    entity attribute. Useful for checking if a value is in a list or string
    attribute.

    Args:
        entity_state: The State object from hass.states.get(entity_id), or None
            if the entity doesn't exist.
        attribute_key: The name of the attribute to check (e.g., 'supported_modes',
            'friendly_name').
        expected_value: The value to search for in the attribute.
        negate: If True, assert the value is NOT in the attribute; if False,
            assert it IS in the attribute. Default: False.

    Raises:
        AssertionError: If entity_state is None, the attribute doesn't exist,
            or the value presence doesn't match the assertion.

    Example:
        Verify a device's supported modes:

        >>> state = hass.states.get("climate.living_room")
        >>> assert_in_attribute(state, "supported_modes", "heat")
        >>> assert_in_attribute(state, "supported_modes", "cool")
        >>> # Verify a mode is NOT supported:
        >>> assert_in_attribute(state, "supported_modes", "auto", negate=True)
    """

    assert entity_state is not None
    assert hasattr(entity_state, "attributes")
    assert attribute_key in entity_state.attributes

    if negate:
        assert expected_value not in entity_state.attributes[attribute_key]
    else:
        assert expected_value in entity_state.attributes[attribute_key]


async def wait_for_state(
    hass: HomeAssistant, entity_id: str, expected_state: str
) -> None:
    """Wait for an entity to reach a specific state, with timeout.

    Asynchronously waits for an entity to transition to an expected state.
    This is useful for testing state changes that happen asynchronously (e.g.,
    after a service call or automation trigger). The function will poll the
    entity state up to 20 times with 0.1 second intervals, providing up to 2
    seconds of waiting time.

    Args:
        hass: The Home Assistant instance.
        entity_id: The entity ID to monitor (e.g., 'light.kitchen',
            'binary_sensor.occupancy').
        expected_state: The state value to wait for (e.g., 'on', 'off', '25').

    Raises:
        AssertionError: If the entity doesn't reach the expected state within
            the timeout (2 seconds).

    Note:
        The timeout is 2 seconds (20 iterations * 0.1 seconds). If you need
        longer waits, use VirtualClock for deterministic timing tests.

    Example:
        Wait for a light to turn on after calling a service:

        >>> hass.async_create_task(
        ...     hass.services.async_call("light", "turn_on", ...)
        ... )
        >>> await wait_for_state(hass, "light.kitchen", "on")
    """
    for _ in range(20):
        state = hass.states.get(entity_id)
        if state and state.state == expected_state:
            return
        await asyncio.sleep(0.1)
        await hass.async_block_till_done()

    # Final check to raise assertion error if still not matching
    state = hass.states.get(entity_id)
    assert_state(state, expected_state)


# ============================================================================
# TIMER/CALLBACK HELPERS
# ============================================================================
# Helpers for managing scheduled callbacks and timers in tests.


def immediate_call_factory(hass, callback_key="callback"):
    """Create a callback factory for testing delayed callbacks without real delays.

    Creates a side_effect function suitable for patching hass.helpers.
    async_call_later(). This factory allows tests to trigger delayed callbacks
    immediately while maintaining the ability to cancel them.

    When used with unittest.mock.patch, this makes tests with hass.async_call_later()
    execute instantly, enabling deterministic testing of timeout-based features
    like presence timeout, extended timeout, and state transitions.

    Args:
        hass: The Home Assistant instance used to create tasks.
        callback_key: Unused parameter, kept for compatibility. Default: "callback".

    Returns:
        callable: A function with signature (hass, delay, callback) that:
            - Creates an asyncio task to run the callback immediately
            - Returns a cancel function to prevent callback execution
            - Respects the cancel function if called before callback runs

    Note:
        This factory is designed to replace:
        >>> from homeassistant.helpers import async_call_later
        >>> handle = async_call_later(hass, delay_seconds, my_callback)
        >>> handle()  # cancels

    Example:
        Mock async_call_later to use immediate callbacks:

        >>> with patch("homeassistant.helpers.async_call_later",
        ...     side_effect=immediate_call_factory(hass)
        ... ):
        ...     # This callback fires immediately instead of after the delay
        ...     await test_delayed_action()

    Usage in Tests:
        Tests using this factory often test:
        - Presence timeout features
        - Extended timeout behaviors
        - State change debouncing
        - Area state transitions
    """

    def immediate_call(hass_arg, delay_arg, callback_arg):
        """Execute a callback immediately, with optional cancellation.

        Args:
            hass_arg: Home Assistant instance (unused, for mock compatibility).
            delay_arg: Delay in seconds (unused, callbacks fire immediately).
            callback_arg: The async callback function to execute.

        Returns:
            callable: A cancel function that prevents callback execution
                if called before the callback runs.
        """
        canceled = False

        def cancel():
            nonlocal canceled
            canceled = True

        async def run_callback():
            if not canceled:
                await callback_arg(utcnow())

        hass.loop.create_task(run_callback())
        return cancel

    return immediate_call
