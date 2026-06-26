"""Mock Home Assistant integration and platform loader helpers."""

import logging
import pathlib
from collections.abc import Sequence
from typing import NoReturn, cast
from unittest.mock import Mock

from homeassistant import loader
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from tests.mocks import MockModule, MockPlatform

_LOGGER = logging.getLogger(__name__)


def setup_test_component_platform(
    hass: HomeAssistant,
    domain: str,
    entities: Sequence[Entity],
    from_config_entry: bool = False,
    built_in: bool = True,
) -> MockPlatform:
    """Create and register a mock component platform with entities."""

    async def _async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> None:
        """Set up a test component platform."""
        async_add_entities(entities)

    platform = MockPlatform(async_setup_platform=_async_setup_platform)

    if from_config_entry:

        async def _async_setup_entry(
            hass: HomeAssistant,
            entry: ConfigEntry[object],
            async_add_entities: AddEntitiesCallback,
        ) -> None:
            """Set up a test component platform from a config entry."""
            async_add_entities(entities)

        platform.async_setup_entry = _async_setup_entry

    mock_platform(hass, f"test.{domain}", platform, built_in=built_in)
    return platform


def mock_integration(
    hass: HomeAssistant,
    *,
    module: MockModule,
    built_in: bool = True,
) -> loader.Integration:
    """Register a mock integration with Home Assistant's loader caches."""
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
    """Register a mock platform with Home Assistant's loader caches."""
    domain, _, platform_name = platform_path.partition(".")
    integration_cache = hass.data[loader.DATA_INTEGRATIONS]
    module_cache = cast(dict[str, object], hass.data[loader.DATA_COMPONENTS])

    if domain not in integration_cache:
        mock_integration(hass, module=MockModule(domain), built_in=built_in)

    integration = integration_cache[domain]
    if isinstance(integration, loader.Integration):
        integration._top_level_files.add(f"{platform_name}.py")
    _LOGGER.info("Adding mock integration platform: %s", platform_path)
    module_cache[platform_path] = module or Mock()
