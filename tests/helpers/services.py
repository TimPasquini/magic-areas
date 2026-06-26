"""Mock service registration helpers."""

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)


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
