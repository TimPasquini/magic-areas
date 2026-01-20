"""Test Magic Area class logic."""

from unittest.mock import ANY, MagicMock, patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    STATE_OFF,
    STATE_ON,
    EntityCategory,
)
from homeassistant.core import CoreState, EventBus, HomeAssistant, StateMachine
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_device_registry,
    mock_registry,
)

from custom_components.magic_areas.area_constants import (
    AREA_STATE_DARK,
)
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.components import (
    MAGIC_AREAS_COMPONENTS,
    MAGIC_DEVICE_ID_PREFIX,
    MAGICAREAS_UNIQUEID_PREFIX,
)
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_LIGHT_GROUPS,
)
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
            minor_version=1,
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


async def test_magic_area_exclusions(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test entity exclusion logic."""

    # Setup registry with various entities
    registry = mock_registry(hass)

    # 1. Magic Area entity (should be excluded)
    ma_entity = registry.async_get_or_create(
        "switch", DOMAIN, "magic_entity", config_entry=mock_config_entry
    )

    # 2. Disabled entity (should be excluded)
    disabled_entity = registry.async_get_or_create(
        "light", "hue", "disabled_light", disabled_by=er.RegistryEntryDisabler.USER
    )

    # 3. Explicitly excluded entity (via config)
    excluded_entity = registry.async_get_or_create("sensor", "mqtt", "excluded_sensor")

    # 4. Diagnostic entity (should be excluded by default)
    diag_entity = registry.async_get_or_create(
        "sensor", "mqtt", "diag_sensor", entity_category=EntityCategory.DIAGNOSTIC
    )

    # 5. Config entity (should be excluded by default)
    conf_entity = registry.async_get_or_create(
        "sensor", "mqtt", "conf_sensor", entity_category=EntityCategory.CONFIG
    )

    # 6. Normal entity (should NOT be excluded)
    normal_entity = registry.async_get_or_create("light", "hue", "normal_light")

    # Update config to exclude specific entity
    data = dict(mock_config_entry.data)
    data[CONF_EXCLUDE_ENTITIES] = [excluded_entity.entity_id]
    hass.config_entries.async_update_entry(mock_config_entry, data=data)

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    # Test _should_exclude_entity directly
    assert area._should_exclude_entity(ma_entity) is True
    assert area._should_exclude_entity(disabled_entity) is True
    assert area._should_exclude_entity(excluded_entity) is True
    assert area._should_exclude_entity(diag_entity) is True
    assert area._should_exclude_entity(conf_entity) is True
    assert area._should_exclude_entity(normal_entity) is False

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_load_entities_from_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test loading entities associated with a device in the area."""

    device_registry = mock_device_registry(hass)
    entity_registry = mock_registry(hass)

    # Create device in the area
    device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("test", "device1")},
    )
    device_registry.async_update_device(device.id, area_id=DEFAULT_MOCK_AREA.value)

    # Create entity linked to device
    entity = entity_registry.async_get_or_create(
        "sensor", "test", "device_sensor", device_id=device.id
    )

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    # Verify entity is loaded
    assert "sensor" in area.entities
    loaded_ids = [e["entity_id"] for e in area.entities["sensor"]]
    assert entity.entity_id in loaded_ids
    assert device.id in area._area_devices

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
    area: MagicArea = entry.runtime_data.area

    # Verify entity is loaded
    assert "switch" in area.entities
    loaded_ids = [e["entity_id"] for e in area.entities["switch"]]
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
    area: MagicArea = entry.runtime_data.area

    # AREA_STATE_DARK maps to "dark_entity" in CONFIGURABLE_AREA_STATE_MAP
    assert area.has_configured_state(AREA_STATE_DARK) is True

    # Sleep is not configured
    assert area.has_configured_state("sleep") is False

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_meta_area_active_areas(
    hass: HomeAssistant, init_integration_all_areas
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
    meta_area = entry.runtime_data.area

    assert meta_area.is_meta()

    # Mock child area states
    # Kitchen (child of Global) -> Occupied
    kitchen_state_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.KITCHEN.value}_area_state"
    hass.states.async_set(kitchen_state_id, STATE_ON)

    # Living Room (child of Global) -> Clear
    living_room_state_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.LIVING_ROOM.value}_area_state"
    hass.states.async_set(living_room_state_id, STATE_OFF)

    active_areas = meta_area.get_active_areas()

    assert MockAreaIds.KITCHEN.value in active_areas
    assert MockAreaIds.LIVING_ROOM.value not in active_areas


async def test_registry_filters(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test registry filters."""

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    entity_filter = area.make_entity_registry_filter()

    # Test entity update in area
    event_data = {
        "action": "update",
        "entity_id": "light.test",
        "changes": {"area_id": DEFAULT_MOCK_AREA.value},  # Removed from area
    }
    # Mock registry lookup to return None or different area to simulate removal
    with patch(
        "custom_components.magic_areas.base.magic.entityreg_async_get"
    ) as mock_er:
        mock_registry_instance = MagicMock()
        mock_er.return_value = mock_registry_instance
        mock_registry_instance.async_get.return_value = (
            None  # Entity not in registry anymore or moved
        )

        assert entity_filter(event_data) is True

    # Test entity create in area
    event_data_create = {
        "action": "create",
        "entity_id": "light.test_new",
    }
    with patch(
        "custom_components.magic_areas.base.magic.entityreg_async_get"
    ) as mock_er:
        mock_registry_instance = MagicMock()
        mock_er.return_value = mock_registry_instance
        mock_entry = MagicMock()
        mock_entry.area_id = DEFAULT_MOCK_AREA.value
        mock_registry_instance.async_get.return_value = mock_entry

        assert entity_filter(event_data_create) is True

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_misc_coverage(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test miscellaneous methods for coverage."""

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    # has_configured_state invalid
    assert area.has_configured_state("invalid_state") is False

    # is_interior / is_exterior
    # Default mock area is interior
    assert area.is_interior() is True
    assert area.is_exterior() is False

    # get_entity_dict with attributes
    hass.states.async_set("light.test_attr", "on", {"brightness": 255})
    entity_dict = area.get_entity_dict("light.test_attr")
    assert entity_dict["brightness"] == "255"
    assert ATTR_ENTITY_ID in entity_dict

    # has_entities
    assert area.has_entities("light") is False  # No lights in default setup

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
    area: MagicArea = entry.runtime_data.area

    assert area.config[CONF_INCLUDE_ENTITIES] == ["light.extra"]

    await shutdown_integration(hass, [mock_config_entry])


async def test_magic_area_legacy_features(hass: HomeAssistant) -> None:
    """Test legacy feature configuration (list)."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = [CONF_FEATURE_LIGHT_GROUPS]

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    await init_integration_helper(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    assert area.has_feature(CONF_FEATURE_LIGHT_GROUPS) is True

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
    area: MagicArea = entry.runtime_data.area

    assert area.has_feature(CONF_FEATURE_LIGHT_GROUPS) is False

    await shutdown_integration(hass, [config_entry])


async def test_magic_area_load_entity_no_domain(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test loading entity without domain."""

    # Let's mock the RegistryEntry
    mock_entry = MagicMock()
    mock_entry.entity_id = "broken.entity"
    mock_entry.domain = None

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    area.load_entity_list([mock_entry])
    # Should log warning and continue, not crash

    await shutdown_integration(hass, [mock_config_entry])


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


async def test_magic_meta_area_reinit(
    hass: HomeAssistant, init_integration_all_areas
) -> None:
    """Test re-initializing meta area."""

    # Get Global Meta Area
    global_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.GLOBAL.value:
            global_entry = entry
            break

    assert global_entry is not None
    entry = hass.config_entries.async_get_entry(global_entry.entry_id)
    meta_area = entry.runtime_data.area

    # Call initialize again
    await meta_area.initialize()
    # Should log debug and return None

    # Test _handle_loaded_area when not running
    hass.set_state(CoreState.not_running)
    await meta_area._handle_loaded_area("type", None, "id")
    # Should return early

    hass.set_state(CoreState.running)


async def test_magic_meta_area_load_entities_bad_id(
    hass: HomeAssistant, init_integration_all_areas
) -> None:
    """Test loading entities with bad ID in meta area."""

    # Get Global Meta Area
    global_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.GLOBAL.value:
            global_entry = entry
            break

    assert global_entry is not None
    entry = hass.config_entries.async_get_entry(global_entry.entry_id)
    meta_area = entry.runtime_data.area

    # Mock magic_entities on a child area to have a non-string entity_id
    # We need to find a child area
    child_area_slug = meta_area.child_areas[0]

    # Find the config entry for the child area
    child_entry = None
    for e in init_integration_all_areas:
        if e.runtime_data.area.slug == child_area_slug:
            child_entry = e
            break

    assert child_entry is not None
    child_area = child_entry.runtime_data.area

    # Inject bad entity
    child_area.magic_entities["binary_sensor"] = [{"entity_id": 123}]  # Not a string

    await meta_area.load_entities()
    # Should skip the bad entity and not crash


async def test_filters_throttling(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test registry filters throttling."""

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    area: MagicArea = entry.runtime_data.area

    # Mock timestamp to be NOW (so it throttles)
    area.timestamp = dt_util.utcnow()

    # Patch THROTTLE to be non-zero to ensure throttling logic triggers
    # (conftest.py sets it to 0 globally)
    with patch(
        "custom_components.magic_areas.base.magic.MetaAreaAutoReloadSettings.THROTTLE",
        5,
    ):
        entity_filter = area.make_entity_registry_filter()
        device_filter = area.make_device_registry_filter()

        event_data = {"entity_id": "light.test", "action": "update", "changes": {}}
        assert entity_filter(event_data) is False

        event_data_device = {
            "device_id": "test_device",
            "action": "update",
            "changes": {},
        }
        assert device_filter(event_data_device) is False

    # Test magic prefix filtering
    event_data_magic = {
        "entity_id": f"light.{MAGICAREAS_UNIQUEID_PREFIX}_test",
        "action": "create",
    }
    assert entity_filter(event_data_magic) is False

    event_data_device_magic = {
        "device_id": f"{MAGIC_DEVICE_ID_PREFIX}test",
        "action": "create",
    }
    assert device_filter(event_data_device_magic) is False

    await shutdown_integration(hass, [mock_config_entry])


async def test_get_active_areas_exception(
    hass: HomeAssistant, init_integration_all_areas
) -> None:
    """Test get_active_areas exception handling."""

    # Get Global Meta Area
    global_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.GLOBAL.value:
            global_entry = entry
            break

    assert global_entry is not None
    entry = hass.config_entries.async_get_entry(global_entry.entry_id)
    meta_area = entry.runtime_data.area

    # Mock hass.states.get to raise exception
    with patch.object(
        StateMachine, "get", side_effect=Exception("Boom"), autospec=True
    ):
        active_areas = meta_area.get_active_areas()
        assert active_areas == []


async def test_get_child_areas_floor_logic(
    hass: HomeAssistant, init_integration_all_areas
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
    meta_area = entry.runtime_data.area

    children = meta_area.get_child_areas()
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
    area: MagicArea = entry.runtime_data.area

    assert area.available_platforms() == MAGIC_AREAS_COMPONENTS

    await shutdown_integration(hass, [mock_config_entry])
