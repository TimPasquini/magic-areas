"""Mock entity and platform setup helpers."""

import logging
import pathlib
from collections.abc import Mapping, Sequence
from typing import NoReturn, cast
from unittest.mock import Mock

from homeassistant import loader
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PLATFORM
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.setup import async_setup_component

from tests.const import MockAreaIds
from tests.mocks import MockModule, MockPlatform

_LOGGER = logging.getLogger("tests.helpers")


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
            entry: ConfigEntry[object],
            async_add_entities: AddEntitiesCallback,
        ) -> None:
            """Set up a test component platform."""
            async_add_entities(entities)

        platform.async_setup_entry = _async_setup_entry

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
    setattr(integration, "_import_platform", mock_import_platform)

    _LOGGER.info("Adding mock integration: %s", module.DOMAIN)
    integration_cache = hass.data[loader.DATA_INTEGRATIONS]
    integration_cache[module.DOMAIN] = integration

    module_cache = cast(dict[str, object], hass.data[loader.DATA_COMPONENTS])
    module_cache[module.DOMAIN] = module

    return integration


def mock_platform(
    hass: HomeAssistant,
    platform_path: str,
    module: Mock | MockPlatform | None = None,
    built_in: bool = True,
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
    module_cache = cast(dict[str, object], hass.data[loader.DATA_COMPONENTS])

    if domain not in integration_cache:
        mock_integration(hass, module=MockModule(domain), built_in=built_in)

    # pylint: disable-next=protected-access
    integration = integration_cache[domain]
    # Ensure we have Integration, not Future[Integration]
    if isinstance(integration, loader.Integration):
        integration._top_level_files.add(f"{platform_name}.py")
    _LOGGER.info("Adding mock integration platform: %s", platform_path)
    # Cast is intentional: we're storing mock platforms in HA's cache for testing
    module_cache[platform_path] = module or Mock()


async def setup_mock_entities(
    hass: HomeAssistant,
    domain: str,
    area_entity_map: Mapping[MockAreaIds, Sequence[Entity]],
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

    all_entities: list[Entity] = []
    entity_area_map: dict[str, MockAreaIds] = {}
    seen_unique_ids: set[str] = set()

    for area_id, entity_list in area_entity_map.items():
        for entity in entity_list:
            all_entities.append(entity)
            assert entity.unique_id is not None
            if entity.unique_id in seen_unique_ids:
                raise AssertionError(
                    f"Duplicate entity unique_id {entity.unique_id!r}"
                )
            seen_unique_ids.add(entity.unique_id)
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

        if entity.entity_id is None:
            raise AssertionError(
                f"Entity {entity.unique_id} did not get an entity_id assigned"
            )
        assert entity.unique_id is not None

        entity_entry = entity_registry.async_get(entity.entity_id)
        if not entity_entry:
            raise AssertionError(
                f"Entity registry entry {entity.entity_id} was not created"
            )
        expected_area_id = entity_area_map[entity.unique_id].value
        entity_registry.async_update_entity(
            entity.entity_id,
            area_id=expected_area_id,
        )
        updated_entry = entity_registry.async_get(entity.entity_id)
        assert updated_entry is not None
        if updated_entry.area_id != expected_area_id:
            raise AssertionError(
                f"Entity {entity.entity_id} area assignment failed: "
                f"expected {expected_area_id!r}, got {updated_entry.area_id!r}"
            )
    await hass.async_block_till_done()
