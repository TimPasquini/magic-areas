"""Compatibility facade for shared Magic Areas test helpers.

Responsibility-focused implementations live in sibling modules such as
``assertions`` and ``waits``. Existing ``from tests.helpers import ...`` imports
remain supported while the remaining helper families are extracted.
"""

from tests import helpers_timing as _helpers_timing
from tests.helpers.assertions import (
    assert_attribute as assert_attribute,
    assert_in_attribute as assert_in_attribute,
    assert_state as assert_state,
)
from tests.helpers.config_entries import (
    get_basic_config_entry_data as get_basic_config_entry_data,
)
from tests.helpers.entities import setup_mock_entities as setup_mock_entities
from tests.helpers.lifecycle import (
    drain_hass as drain_hass,
    init_integration as init_integration,
    shutdown_integration as shutdown_integration,
)
from tests.helpers.services import async_mock_service as async_mock_service
from tests.helpers.waits import (
    wait_for_attribute as wait_for_attribute,
    wait_for_state as wait_for_state,
    wait_until as wait_until,
)

__all__ = [
    "assert_attribute",
    "assert_in_attribute",
    "assert_state",
    "async_mock_service",
    "create_area_state_change_event",
    "drain_hass",
    "get_basic_config_entry_data",
    "immediate_call_factory",
    "init_integration",
    "setup_mock_entities",
    "shutdown_integration",
    "wait_for_attribute",
    "wait_for_state",
    "wait_until",
]

create_area_state_change_event = _helpers_timing.create_area_state_change_event
immediate_call_factory = _helpers_timing.immediate_call_factory


# Timing/callback/event payload helpers are re-exported from
# `tests.helpers_timing` to keep this module's public API stable.
