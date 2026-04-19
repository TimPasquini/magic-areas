"""Tests for area lifecycle and initialization."""

from unittest.mock import ANY, patch

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import CoreState, EventBus, HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import CONF_ID
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicConfigEntryVersion
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
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

        with patch.object(EventBus, "async_listen", autospec=True) as mock_listen:
            await init_integration_helper(hass, [mock_config_entry])

            # Verify readiness listener was added
            mock_listen.assert_any_call(hass.bus, EVENT_STATE_CHANGED, ANY)
            assert mock_config_entry.runtime_data is not None

        await hass.async_start()
        await hass.async_block_till_done()
        assert mock_config_entry.state is ConfigEntryState.LOADED

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
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None
    assert mock_config_entry.runtime_data.coordinator.data is not None

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
    from homeassistant.const import STATE_OFF

    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_block_till_done()

    # Get coordinator and verify it has internal MagicArea access
    assert mock_config_entry.runtime_data is not None
    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator is not None
    assert coordinator.data is not None

    # Verify coordinator has area_config and area_runtime in snapshot (not area)
    snapshot = coordinator.data
    assert hasattr(snapshot, "area_config"), "Snapshot must have area_config"
    assert hasattr(snapshot, "area_runtime"), "Snapshot must have area_runtime"

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
    presence_entity_id = (
        f"{BS_DOMAIN}.magic_areas_presence_tracking_"
        f"{snapshot.area_config.slug}_area_state"
    )
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

    # PHASE 8 CHECKPOINT: Verify that the area field was successfully removed
    # After Phase 8A, MagicArea should NOT be in the public snapshot API
    has_area = (
        hasattr(snapshot, "area")
        and getattr(snapshot, "area", None) is not None
    )
    assert not has_area, (
        "PHASE 8 FAILED: area field still exists in snapshot. "
        "It should have been removed in Phase 8A."
    )

    await shutdown_integration(hass, [mock_config_entry])
