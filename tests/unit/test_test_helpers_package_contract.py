"""Contracts for the shared test-helper compatibility facade."""

from tests import helpers
from tests.helpers import assertions, config_entries, waits


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
