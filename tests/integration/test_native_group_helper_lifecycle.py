"""Probe Home Assistant native group helper lifecycle for managed surfaces."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.group import DOMAIN as GROUP_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITIES,
    CONF_NAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import setup_mock_entities
from tests.mocks import MockCover


def _managed_group_entry(
    *,
    entry_id: str,
    unique_id: str,
    name: str,
    entities: list[str],
) -> ConfigEntry:
    """Build the shape a Magic Areas reconciler would manage."""
    return ConfigEntry(
        data={},
        discovery_keys=MappingProxyType({}),
        domain=GROUP_DOMAIN,
        entry_id=entry_id,
        minor_version=1,
        options={
            "group_type": Platform.COVER,
            CONF_NAME: name,
            CONF_ENTITIES: entities,
            "hide_members": False,
        },
        source="import",
        subentries_data=(),
        title=name,
        unique_id=unique_id,
        version=1,
    )


async def test_managed_cover_group_config_entry_lifecycle(
    hass: HomeAssistant,
) -> None:
    """A managed native cover group can be created, updated, reloaded, removed."""
    covers = [
        MockCover(
            name="left_blind",
            unique_id="left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="right_blind",
            unique_id="right_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="shade",
            unique_id="shade",
            device_class=CoverDeviceClass.SHADE,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})

    entry = _managed_group_entry(
        entry_id="magic_areas_cover_group_living_room_blinds",
        unique_id="magic_areas:entry:living_room:cover_groups:group_helper:blind",
        name="Magic Areas Living Room Blinds",
        entities=[covers[0].entity_id, covers[1].entity_id],
    )

    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entity_registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    )
    assert len(registry_entries) == 1

    group_entity_id = registry_entries[0].entity_id
    assert group_entity_id.startswith(f"{COVER_DOMAIN}.")
    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert set(group_state.attributes[ATTR_ENTITY_ID]) == {
        covers[0].entity_id,
        covers[1].entity_id,
    }

    hass.config_entries.async_update_entry(
        entry,
        options={
            **entry.options,
            CONF_ENTITIES: [covers[2].entity_id],
        },
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert group_state.attributes[ATTR_ENTITY_ID] == [covers[2].entity_id]

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(group_entity_id) is None
    assert not er.async_entries_for_config_entry(entity_registry, entry.entry_id)
