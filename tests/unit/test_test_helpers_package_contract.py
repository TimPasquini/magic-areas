"""Contracts for the shared test-helper compatibility facade."""

from tests import helpers
from tests.helpers import (
    assertions,
    config_entries,
    entities,
    lifecycle,
    services,
    waits,
)


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
