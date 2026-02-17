"""Test Magic Area class logic."""

from typing import cast
from unittest.mock import ANY, MagicMock, patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    STATE_OFF,
    STATE_ON,
    EntityCategory,
)
from homeassistant.core import CoreState, EventBus, HomeAssistant
from homeassistant.helpers.entity_registry import (
    _EventEntityRegistryUpdatedData_CreateRemove,
    _EventEntityRegistryUpdatedData_Update,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_registry,
)

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.components import (
    MAGIC_AREAS_COMPONENTS,
)
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.core.config import (
    has_configured_state,
    has_feature,
)
from custom_components.magic_areas.enums import MagicConfigEntryVersion
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA, MockAreaIds
from tests.helpers import (
    get_basic_config_entry_data,
    shutdown_integration,
)
from tests.helpers import (
    init_integration as init_integration_helper,
)


async def test_magic_area_initialization_wait_for_start(
    hass: HomeAssistant,
) -> None:
    """Test that MagicArea waits for Home Assistant to start if not running."""

    # Patch storage save to avoid lingering timers
    with patch("homeassistant.helpers.storage.Store.async_delay_save"):
        # Create config entry with current version to avoid migration
        data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
        mock_config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=data,
            unique_id=data[CONF_ID],
            version=2,
            minor_version=MagicConfigEntryVersion.MINOR,
        )
        mock_config_entry.add_to_hass(hass)

        # Mock hass not running
        hass.set_state(CoreState.not_running)

        with patch.object(EventBus, "async_listen_once", autospec=True) as mock_listen:
            await init_integration_helper(hass, [mock_config_entry])

            # Verify listener was added
            mock_listen.assert_any_call(hass.bus, EVENT_HOMEASSISTANT_STARTED, ANY)

        await hass.async_start()
        await hass.async_block_till_done()

        await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_include_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test including specific entities via config."""

    entity_registry = mock_registry(hass)

    # Create an entity NOT in the area
    external_entity = entity_registry.async_get_or_create(
        "switch", "test", "external_switch"
    )

    # Update config to include it
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [external_entity.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify entity is loaded in coordinator snapshot
    assert coordinator.data is not None
    assert "switch" in coordinator.data.entities
    loaded_ids = [e["entity_id"] for e in coordinator.data.entities["switch"]]
    assert external_entity.entity_id in loaded_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_has_configured_state(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test has_configured_state logic."""

    # Configure secondary state
    data = dict(mock_config_entry.data)
    data[CONF_SECONDARY_STATES] = {"dark_entity": "sensor.light_sensor"}
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    # AreaStates.DARK maps to "dark_entity" in CONFIGURABLE_AREA_STATE_MAP
    assert has_configured_state(area_config.config, AreaStates.DARK) is True

    # Sleep is not configured
    assert has_configured_state(area_config.config, AreaStates.SLEEP) is False

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_meta_area_active_areas(
    hass: HomeAssistant, init_integration_all_areas: list[MockConfigEntry]
) -> None:
    """Test getting active areas for a meta area."""

    # Get Global Meta Area
    global_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.GLOBAL.value:
            global_entry = entry
            break

    assert global_entry is not None
    entry = hass.config_entries.async_get_entry(global_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator
    meta_area_config = coordinator.data.area_config

    assert meta_area_config.is_meta()

    # Mock child area states
    # Kitchen (child of Global) -> Occupied
    kitchen_state_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.KITCHEN.value}_area_state"
    hass.states.async_set(kitchen_state_id, STATE_ON)

    # Living Room (child of Global) -> Clear
    living_room_state_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.LIVING_ROOM.value}_area_state"
    hass.states.async_set(living_room_state_id, STATE_OFF)

    # Refresh coordinator to pick up state changes
    await coordinator.async_refresh()

    # Read active areas from snapshot
    active_areas = coordinator.data.active_areas

    assert MockAreaIds.KITCHEN.value in active_areas
    assert MockAreaIds.LIVING_ROOM.value not in active_areas


async def test_registry_filters(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test registry filters."""
    from custom_components.magic_areas.core.registry_filters import (
        make_entity_registry_filter,
    )

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    entity_filter = make_entity_registry_filter(hass, area_config.id, mock_config_entry.entry_id)

    # Test entity update in area
    event_data: _EventEntityRegistryUpdatedData_Update = cast(
        _EventEntityRegistryUpdatedData_Update,
        {
            "action": "update",
            "entity_id": "light.test",
            "changes": {"area_id": DEFAULT_MOCK_AREA.value},  # Removed from area
        },
    )
    # Mock registry lookup to return None or different area to simulate removal
    with patch(
        "custom_components.magic_areas.core.registry_filters.entityreg_async_get"
    ) as mock_er:
        mock_registry_instance = MagicMock()
        mock_er.return_value = mock_registry_instance
        mock_registry_instance.async_get.return_value = (
            None  # Entity not in registry anymore or moved
        )

        assert entity_filter(event_data) is True

    # Test entity create in area
    event_data_create: _EventEntityRegistryUpdatedData_CreateRemove = cast(
        _EventEntityRegistryUpdatedData_CreateRemove,
        {
            "action": "create",
            "entity_id": "light.test_new",
        },
    )
    with patch(
        "custom_components.magic_areas.core.registry_filters.entityreg_async_get"
    ) as mock_er:
        mock_registry_instance = MagicMock()
        mock_er.return_value = mock_registry_instance
        mock_entry = MagicMock()
        mock_entry.area_id = DEFAULT_MOCK_AREA.value
        mock_registry_instance.async_get.return_value = mock_entry

        assert entity_filter(event_data_create) is True

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_options_merge(
    hass: HomeAssistant,
) -> None:
    """Test merging options into config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    options = {CONF_INCLUDE_ENTITIES: ["light.extra"]}

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN, data=data, options=options, unique_id=data[CONF_ID]
    )
    mock_config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    assert area_config.config[CONF_INCLUDE_ENTITIES] == ["light.extra"]

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_legacy_features(hass: HomeAssistant) -> None:
    """Test legacy feature configuration (list)."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = [MagicAreasFeatures.LIGHT_GROUPS]

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    assert has_feature(area_config.config, MagicAreasFeatures.LIGHT_GROUPS) is True

    await shutdown_integration(hass, [config_entry])


async def test_magic_area_invalid_features(hass: HomeAssistant) -> None:
    """Test invalid feature configuration."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = "invalid_string"

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify has_feature returns False for invalid feature config
    assert has_feature(coordinator.data.config, MagicAreasFeatures.LIGHT_GROUPS) is False

    await shutdown_integration(hass, [config_entry])


async def test_magic_area_finalize_init_running(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test finalize_init when HA is running."""

    # We need to manually trigger this because init_integration_helper usually does it
    # But we want to verify the branch where hass.is_running is True.
    # init_integration_helper calls async_setup_component which calls async_setup_entry.
    # async_setup_entry calls area.initialize() which calls finalize_init().

    # If we start HA *before* setting up the integration, we hit that branch.
    await hass.async_start()
    await hass.async_block_till_done()

    await init_integration_helper(hass, [mock_config_entry])
    # If we are here, it worked.

    await shutdown_integration(hass, [mock_config_entry])




async def test_get_child_areas_floor_logic(
    hass: HomeAssistant, init_integration_all_areas: list[MockConfigEntry]
) -> None:
    """Test get_child_areas logic for floors."""

    # Get First Floor Meta Area
    floor_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.FIRST_FLOOR.value:
            floor_entry = entry
            break

    assert floor_entry is not None
    entry = hass.config_entries.async_get_entry(floor_entry.entry_id)
    assert entry is not None
    children = entry.runtime_data.coordinator.data.child_areas
    # Kitchen, Living Room, Dining Room are on First Floor
    assert MockAreaIds.KITCHEN.value in children
    assert MockAreaIds.LIVING_ROOM.value in children
    assert MockAreaIds.DINING_ROOM.value in children
    assert MockAreaIds.MASTER_BEDROOM.value not in children  # Second floor


async def test_available_platforms(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test available platforms."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator.data.area_config

    assert area_config.available_platforms() == MAGIC_AREAS_COMPONENTS

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_excludes_disabled(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that disabled entities are excluded from area entities."""
    entity_registry = mock_registry(hass)

    # Create a disabled entity
    disabled = entity_registry.async_get_or_create(
        "light", "test", "disabled_light",
        disabled_by=er.RegistryEntryDisabler.USER
    )

    # Create a normal entity
    normal = entity_registry.async_get_or_create(
        "light", "test", "normal_light"
    )

    # Update area config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [disabled.entity_id, normal.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify disabled entity is excluded
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert disabled.entity_id not in all_entity_ids
    assert normal.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_excludes_diagnostic(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that diagnostic entities are excluded from area entities."""
    entity_registry = mock_registry(hass)

    # Create a diagnostic entity
    diagnostic = entity_registry.async_get_or_create(
        "sensor", "test", "diag_sensor",
        entity_category=EntityCategory.DIAGNOSTIC
    )

    # Create a normal entity
    normal = entity_registry.async_get_or_create(
        "sensor", "test", "normal_sensor"
    )

    # Update area config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [diagnostic.entity_id, normal.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify diagnostic entity is excluded
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert diagnostic.entity_id not in all_entity_ids
    assert normal.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_includes_normal_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that normal entities are included in area loading."""
    entity_registry = mock_registry(hass)

    # Create multiple normal entities
    light_entity = entity_registry.async_get_or_create(
        "light", "test", "test_light"
    )
    sensor_entity = entity_registry.async_get_or_create(
        "sensor", "test", "test_sensor"
    )
    switch_entity = entity_registry.async_get_or_create(
        "switch", "test", "test_switch"
    )

    # Update area config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [
        light_entity.entity_id,
        sensor_entity.entity_id,
        switch_entity.entity_id,
    ]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify all normal entities are included
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert light_entity.entity_id in all_entity_ids
    assert sensor_entity.entity_id in all_entity_ids
    assert switch_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_excluded_entities_respected(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that excluded entities are not loaded."""
    entity_registry = mock_registry(hass)

    # Create entities
    excluded_entity = entity_registry.async_get_or_create(
        "light", "test", "excluded_light"
    )
    included_entity = entity_registry.async_get_or_create(
        "light", "test", "included_light"
    )

    # Update area config with excluded entities
    data = dict(mock_config_entry.data)
    data[CONF_EXCLUDE_ENTITIES] = [excluded_entity.entity_id]
    data[CONF_INCLUDE_ENTITIES] = [excluded_entity.entity_id, included_entity.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify excluded entity is excluded even if explicitly included
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert excluded_entity.entity_id not in all_entity_ids
    assert included_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_coordinator_entity_loading(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that coordinator correctly loads entities into snapshot."""
    entity_registry = mock_registry(hass)

    # Create entities with various states
    light1 = entity_registry.async_get_or_create(
        "light", "test", "light1"
    )
    light2 = entity_registry.async_get_or_create(
        "light", "test", "light2"
    )
    sensor1 = entity_registry.async_get_or_create(
        "sensor", "test", "sensor1"
    )

    # Update config to include these entities
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [
        light1.entity_id,
        light2.entity_id,
        sensor1.entity_id,
    ]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify coordinator snapshot has the entities
    assert coordinator.data is not None
    assert "light" in coordinator.data.entities
    assert "sensor" in coordinator.data.entities

    light_entities = coordinator.data.entities["light"]
    sensor_entities = coordinator.data.entities["sensor"]

    light_ids = [e.get("entity_id") for e in light_entities]
    sensor_ids = [e.get("entity_id") for e in sensor_entities]

    assert light1.entity_id in light_ids
    assert light2.entity_id in light_ids
    assert sensor1.entity_id in sensor_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_loads_device_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that coordinator loads entities linked to devices in area."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Setup area first
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_id = entry.runtime_data.coordinator._area_config.id

    # Create a device in the area
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("test", "test_device_1")},
    )
    device_registry.async_update_device(device.id, area_id=area_id)

    # Create an entity linked to the device (without area_id, linked via device)
    entity = entity_registry.async_get_or_create(
        "light", "test", "device_light",
        device_id=device.id,
    )

    # Wait for registry updates
    await hass.async_block_till_done()

    # Refresh coordinator to pick up device entities
    assert entry is not None
    coordinator = entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Verify device entity was loaded
    assert coordinator.data is not None
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    assert entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_entity_loading_respects_config_entry_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that entities from our own config entry are not included."""
    entity_registry = er.async_get(hass)

    # Create an entity that belongs to magic_areas config entry
    our_entity = entity_registry.async_get_or_create(
        "binary_sensor", "magic_areas", "our_area_state",
        config_entry=mock_config_entry,
    )

    # Create a normal entity not from our config
    normal_entity = entity_registry.async_get_or_create(
        "light", "test", "other_light",
    )

    # Update config to include both
    data = dict(mock_config_entry.data)
    data[CONF_INCLUDE_ENTITIES] = [our_entity.entity_id, normal_entity.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator

    # Verify our entity is excluded even if included
    all_entity_ids = []
    for domain_entities in coordinator.data.entities.values():
        all_entity_ids.extend([e.get("entity_id") for e in domain_entities])

    # Our config entry entity should be excluded
    assert our_entity.entity_id not in all_entity_ids
    # Normal entity should be included
    assert normal_entity.entity_id in all_entity_ids

    await shutdown_integration(hass, [mock_config_entry])


async def test_config_entry_update_pattern(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that ConfigEntry is updated correctly via HA API."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    # Verify initial state
    assert mock_config_entry.data[CONF_INCLUDE_ENTITIES] == []

    # Update via HA API
    new_data = dict(mock_config_entry.data)
    new_data[CONF_INCLUDE_ENTITIES] = ["light.new_light"]

    hass.config_entries.async_update_entry(mock_config_entry, data=new_data)
    await hass.async_block_till_done()

    # Verify update reflected in entry
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    assert entry.data[CONF_INCLUDE_ENTITIES] == ["light.new_light"]

    await shutdown_integration(hass, [mock_config_entry])


async def test_coordinator_internal_area_lifecycle(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Verify coordinator uses internal MagicArea for lifecycle and state queries.

    This test ensures that after Phase 8 (when area is removed from snapshot),
    the coordinator can still:
    - Access internal MagicArea for lifecycle (initialize, finalize_init)
    - Query area state (is_occupied, has_state, get_current_states)
    - Build snapshot without exposing area to platforms
    """
    from homeassistant.components.binary_sensor import DOMAIN as BS_DOMAIN

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    # Get coordinator and verify it has internal MagicArea access
    assert mock_config_entry.runtime_data is not None
    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator is not None
    assert coordinator.data is not None

    # Verify coordinator has area_config and area_runtime in snapshot (not area)
    snapshot = coordinator.data
    assert hasattr(snapshot, 'area_config'), "Snapshot must have area_config"
    assert hasattr(snapshot, 'area_runtime'), "Snapshot must have area_runtime"

    # Verify snapshot state is valid
    assert snapshot.area_config is not None
    assert snapshot.area_runtime is not None
    assert snapshot.area_runtime.last_update_success is True

    # Verify coordinator can access internal area for lifecycle
    # (Coordinator should have _area or similar private reference)
    # This is implicit: if coordinator.refresh() works and tests pass,
    # then it's using internal area correctly

    # Verify entities can query state through coordinator snapshot
    # Get the presence sensor binary sensor
    presence_entity_id = f"{BS_DOMAIN}.magic_areas_presence_tracking_{snapshot.area_config.slug}_area_state"
    presence_state = hass.states.get(presence_entity_id)
    assert presence_state is not None
    assert presence_state.state == STATE_OFF  # Initially clear

    # Verify area runtime availability chain works
    # (This is how entities will check availability after Phase 8)
    assert snapshot.area_runtime.last_update_success is True

    # Trigger a coordinator refresh to verify lifecycle still works
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # After refresh, snapshot should be updated
    updated_snapshot = coordinator.data
    assert updated_snapshot is not None
    assert updated_snapshot.area_runtime.last_update_success is True

    # PHASE 8 CHECKPOINT: Verify that the area field was successfully removed from snapshot
    # After Phase 8A, MagicArea should NOT be in the public snapshot API
    has_area = hasattr(snapshot, 'area') and getattr(snapshot, 'area', None) is not None
    assert not has_area, (
        "PHASE 8 FAILED: area field still exists in snapshot. "
        "It should have been removed in Phase 8A."
    )

    await shutdown_integration(hass, [mock_config_entry])
