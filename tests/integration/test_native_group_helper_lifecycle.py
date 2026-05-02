"""Probe Home Assistant native group helper lifecycle for managed surfaces."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITIES,
    CONF_NAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.coordinator.managed_surfaces import (
    async_reconcile_config_entry_helpers,
)
from custom_components.magic_areas.coordinator.pipeline.entity_ingestion import (
    load_area_entities,
)
from custom_components.magic_areas.core.runtime_model.managed_surfaces import (
    ConfigEntryHelperSurface,
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import setup_mock_entities
from tests.mocks import MockCover

GROUP_DOMAIN = "group"


def _managed_group_entry(
    *,
    entry_id: str,
    unique_id: str,
    name: str,
    entities: list[str],
) -> ConfigEntry[object]:
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


async def test_reconciler_manages_cover_group_helper_lifecycle(
    hass: HomeAssistant,
) -> None:
    """The Magic Areas reconciler creates, updates, and removes helper entries."""
    covers = [
        MockCover(
            name="left_blind",
            unique_id="reconcile_left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="right_blind",
            unique_id="reconcile_right_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="shade",
            unique_id="reconcile_shade",
            device_class=CoverDeviceClass.SHADE,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})
    owner_entry_id = "magic_area_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Kitchen",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="cover_groups",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="cover_group_blind",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=GROUP_DOMAIN,
                title="Magic Areas Living Room Blinds",
                options={
                    "group_type": Platform.COVER,
                    CONF_NAME: "Magic Areas Living Room Blinds",
                    CONF_ENTITIES: [covers[0].entity_id, covers[1].entity_id],
                    "hide_members": False,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Kitchen",
            )
        ],
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entry = next(
        entry
        for entry in hass.config_entries.async_entries(GROUP_DOMAIN)
        if entry.unique_id == unique_id
    )
    group_entity_id = er.async_entries_for_config_entry(entity_registry, entry.entry_id)[
        0
    ].entity_id
    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert set(group_state.attributes[ATTR_ENTITY_ID]) == {
        covers[0].entity_id,
        covers[1].entity_id,
    }
    group_registry_entry = entity_registry.async_get(group_entity_id)
    assert group_registry_entry is not None
    assert group_registry_entry.area_id == DEFAULT_MOCK_AREA.value
    assert group_registry_entry.device_id is not None
    device = dr.async_get(hass).async_get(group_registry_entry.device_id)
    assert device is not None
    assert (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}") in device.identifiers

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=GROUP_DOMAIN,
                title="Magic Areas Living Room Shades",
                options={
                    "group_type": Platform.COVER,
                    CONF_NAME: "Magic Areas Living Room Shades",
                    CONF_ENTITIES: [covers[2].entity_id],
                    "hide_members": False,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Kitchen",
            )
        ],
    )
    await hass.async_block_till_done()

    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert group_state.attributes[ATTR_ENTITY_ID] == [covers[2].entity_id]
    entities, _magic_entities = await load_area_entities(
        hass=hass,
        area_id=DEFAULT_MOCK_AREA.value,
        config_entry_id=owner_entry_id,
        config={},
    )
    assert group_entity_id not in {
        entity["entity_id"] for entity in entities.get(COVER_DOMAIN, [])
    }

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )
    await hass.async_block_till_done()

    assert hass.states.get(group_entity_id) is None
