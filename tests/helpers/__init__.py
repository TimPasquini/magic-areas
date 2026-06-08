"""Compatibility facade for shared Magic Areas test helpers.

Responsibility-focused implementations live in sibling modules such as
``assertions`` and ``waits``. Existing ``from tests.helpers import ...`` imports
remain supported while the remaining helper families are extracted.
"""

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)

from tests import helpers_timing as _helpers_timing
from tests.helpers.assertions import (
    assert_attribute as assert_attribute,
    assert_in_attribute as assert_in_attribute,
    assert_state as assert_state,
)
from tests.helpers.config_entries import (
    get_basic_config_entry_data as get_basic_config_entry_data,
)
from tests.helpers.entities import (
    mock_integration as mock_integration,
    mock_platform as mock_platform,
    setup_mock_entities as setup_mock_entities,
    setup_test_component_platform as setup_test_component_platform,
)
from tests.helpers.lifecycle import (
    drain_hass as drain_hass,
    init_integration as init_integration,
    shutdown_integration as shutdown_integration,
)
from tests.helpers.waits import (
    wait_for_attribute as wait_for_attribute,
    wait_for_state as wait_for_state,
    wait_until as wait_until,
)

VirtualClock = _helpers_timing.VirtualClock
create_area_state_change_event = _helpers_timing.create_area_state_change_event
immediate_call_factory = _helpers_timing.immediate_call_factory

def async_mock_service(
    *,
    hass: HomeAssistant,
    domain: str,
    service: str,
    schema: vol.Schema | None = None,
    response: ServiceResponse = None,
    supports_response: SupportsResponse | None = None,
    raise_exception: Exception | None = None,
) -> list[ServiceCall]:
    """Register a mock service and return its call log.

    Creates a fake service that logs all calls for assertion in tests. The
    service can optionally return a response, raise an exception, or execute
    without side effects.

    Args:
        hass: The Home Assistant instance.
        domain: Service domain (e.g., 'light', 'switch').
        service: Service name (e.g., 'turn_on', 'turn_off').
        schema: Optional voluptuous schema to validate service calls.
            Default: None (no validation).
        response: Optional response to return from service calls.
            Default: None.
        supports_response: Whether service supports response. If None, auto-
            detects based on whether response is provided. Default: None.
        raise_exception: Optional exception to raise when service is called.
            Default: None (service succeeds).

    Returns:
        list[ServiceCall]: A list that will contain all ServiceCall objects
            passed to this service. Use this for assertions in tests.

    Example:
        Create a mock light.turn_on service and verify it was called:

        >>> calls = async_mock_service(
        ...     hass=hass, domain="light", service="turn_on"
        ... )
        >>> # Later in test...
        >>> hass.async_create_task(
        ...     hass.services.async_call("light", "turn_on", ...)
        ... )
        >>> await hass.async_block_till_done()
        >>> assert len(calls) == 1
        >>> assert calls[0].data["entity_id"] == "light.test"

    """
    calls = []

    @callback
    def mock_service_log(call: ServiceCall) -> ServiceResponse:
        """Mock service call."""
        calls.append(call)
        if raise_exception is not None:
            raise raise_exception
        return response

    if supports_response is None:
        if response is not None:
            supports_response = SupportsResponse.OPTIONAL
        else:
            supports_response = SupportsResponse.NONE

    hass.services.async_register(
        domain,
        service,
        mock_service_log,
        schema=schema,
        supports_response=supports_response,
    )

    return calls


# Timing/callback/event payload helpers are re-exported from
# `tests.helpers_timing` to keep this module's public API stable.
