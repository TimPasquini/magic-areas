"""Contracts for the shared test-helper compatibility facade."""

from tests import helpers
from tests import helpers_timing
from tests.helpers import (
    assertions,
    config_entries,
    entities,
    lifecycle,
    services,
    waits,
)

EXPECTED_COMPATIBILITY_EXPORTS = {
    "VirtualClock",
    "assert_attribute",
    "assert_in_attribute",
    "assert_state",
    "async_mock_service",
    "create_area_state_change_event",
    "drain_hass",
    "get_basic_config_entry_data",
    "immediate_call_factory",
    "init_integration",
    "mock_integration",
    "mock_platform",
    "setup_mock_entities",
    "setup_test_component_platform",
    "shutdown_integration",
    "wait_for_attribute",
    "wait_for_state",
    "wait_until",
}


def test_compatibility_facade_has_an_explicit_public_surface() -> None:
    """The audited facade should expose only intentional compatibility names."""
    assert set(helpers.__all__) == EXPECTED_COMPATIBILITY_EXPORTS


def test_assertion_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the extracted assertion functions."""
    assert helpers.assert_state is assertions.assert_state
    assert helpers.assert_attribute is assertions.assert_attribute
    assert helpers.assert_in_attribute is assertions.assert_in_attribute


def test_wait_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the extracted wait functions."""
    assert helpers.wait_for_state is waits.wait_for_state
    assert helpers.wait_until is waits.wait_until
    assert helpers.wait_for_attribute is waits.wait_for_attribute


def test_config_entry_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the extracted config-entry builders."""
    assert (
        helpers.get_basic_config_entry_data
        is config_entries.get_basic_config_entry_data
    )


def test_lifecycle_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the extracted lifecycle functions."""
    assert helpers.init_integration is lifecycle.init_integration
    assert helpers.shutdown_integration is lifecycle.shutdown_integration
    assert helpers.drain_hass is lifecycle.drain_hass


def test_entity_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the extracted entity setup functions."""
    assert (
        helpers.setup_test_component_platform
        is entities.setup_test_component_platform
    )
    assert helpers.mock_integration is entities.mock_integration
    assert helpers.mock_platform is entities.mock_platform
    assert helpers.setup_mock_entities is entities.setup_mock_entities


def test_service_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the extracted service functions."""
    assert helpers.async_mock_service is services.async_mock_service


def test_timing_helpers_are_exact_compatibility_reexports() -> None:
    """Legacy imports should resolve to the timing helper implementations."""
    assert helpers.VirtualClock is helpers_timing.VirtualClock
    assert (
        helpers.create_area_state_change_event
        is helpers_timing.create_area_state_change_event
    )
    assert helpers.immediate_call_factory is helpers_timing.immediate_call_factory
