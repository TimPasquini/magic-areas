"""Integration lifecycle helpers shared across Magic Areas tests."""

import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import DOMAIN
from tests.const import DEFAULT_MOCK_AREA, MockAreaIds
from tests.helpers.registries import setup_mock_areas

_LOGGER = logging.getLogger("tests.helpers")


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

    setup_mock_areas(hass, areas)

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
    """Unload the magic-areas integration and verify cleanup.

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


async def drain_hass(hass: HomeAssistant, *, cycles: int = 2) -> None:
    """Flush pending loop work without real-time sleeps."""
    for _ in range(cycles):
        await hass.async_block_till_done()
