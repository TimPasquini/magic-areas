from datetime import datetime
from collections.abc import Sequence

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from custom_components.magic_areas.components import MagicAreasRuntimeData

class MockConfigEntry(ConfigEntry[MagicAreasRuntimeData]):
    def __init__(self, *args: object, **kwargs: object) -> None: ...
    def add_to_hass(self, hass: HomeAssistant) -> None: ...

def mock_registry(
    hass: HomeAssistant,
    mock_entries: dict[str, RegistryEntry] | None = None,
) -> EntityRegistry: ...
def mock_restore_cache(hass: HomeAssistant, states: Sequence[State]) -> None: ...
def async_fire_time_changed(
    hass: HomeAssistant, datetime_: datetime | None = None, fire_all: bool = False
) -> None: ...
