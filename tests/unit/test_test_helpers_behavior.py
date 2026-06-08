"""Behavioral contracts for shared test helpers."""

import asyncio
from typing import cast

import pytest
import voluptuous as vol
from homeassistant import loader
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, State, SupportsResponse
from homeassistant.helpers.entity_registry import async_get as async_get_er

from tests.const import MockAreaIds
from tests.helpers.assertions import (
    assert_attribute,
    assert_in_attribute,
    assert_state,
)
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.entities import (
    setup_mock_entities,
    setup_test_component_platform,
)
from tests.helpers.registries import setup_mock_areas
from tests.helpers.services import async_mock_service
from tests.helpers.waits import wait_for_attribute, wait_for_state, wait_until
from tests.mocks import MockLight


def test_assertion_helpers_cover_success_failure_and_negation() -> None:
    """Assertion helpers should enforce each documented condition."""
    state = State(
        "sensor.test",
        "on",
        {"count": 2, "modes": ["heat", "cool"]},
    )

    assert_state(state, "on")
    assert_attribute(state, "count", "2")
    assert_in_attribute(state, "modes", "heat")
    assert_in_attribute(state, "modes", "auto", negate=True)

    with pytest.raises(AssertionError):
        assert_state(None, "on")
    with pytest.raises(AssertionError):
        assert_attribute(state, "missing", "value")
    with pytest.raises(AssertionError):
        assert_in_attribute(state, "modes", "heat", negate=True)


def test_config_entry_builder_rejects_unknown_areas() -> None:
    """Unknown area identifiers should fail instead of producing partial data."""
    with pytest.raises(AssertionError):
        get_basic_config_entry_data(cast(MockAreaIds, "missing"))


async def test_wait_helpers_cover_immediate_and_event_success(
    hass: HomeAssistant,
) -> None:
    """Wait helpers should handle both existing and future matching state."""
    hass.states.async_set("sensor.immediate", "ready", {"count": 1})

    await wait_for_state(hass, "sensor.immediate", "ready")
    await wait_for_attribute(hass, "sensor.immediate", "count", 1)

    async def set_future_state() -> None:
        await asyncio.sleep(0)
        hass.states.async_set("sensor.future_state", "ready")

    async def set_future_attribute() -> None:
        await asyncio.sleep(0)
        hass.states.async_set("sensor.future_attribute", "ready", {"count": 2})

    hass.async_create_task(set_future_state())
    await wait_for_state(hass, "sensor.future_state", "ready")

    hass.async_create_task(set_future_attribute())
    await wait_for_attribute(hass, "sensor.future_attribute", "count", 2)


async def test_wait_helpers_raise_assertion_errors_on_timeout(
    hass: HomeAssistant,
) -> None:
    """Timeout failures should use the helpers' documented exception type."""
    listeners_before = hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0)

    with pytest.raises(AssertionError, match="did not reach state"):
        await wait_for_state(
            hass,
            "sensor.missing",
            "ready",
            timeout=0.01,
        )

    with pytest.raises(AssertionError, match="did not reach attribute"):
        await wait_for_attribute(
            hass,
            "sensor.missing",
            "count",
            2,
            timeout=0.01,
        )

    with pytest.raises(AssertionError, match="Timed out"):
        await wait_until(hass, lambda: False, timeout=0.01)

    assert (
        hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0)
        == listeners_before
    )


async def test_wait_until_returns_when_predicate_becomes_true(
    hass: HomeAssistant,
) -> None:
    """The generic wait should drain Home Assistant until its predicate passes."""
    attempts = 0

    def predicate() -> bool:
        nonlocal attempts
        attempts += 1
        return attempts > 1

    await wait_until(hass, predicate)


async def test_mock_service_supports_schema_response_and_call_logging(
    hass: HomeAssistant,
) -> None:
    """Mock services should validate data, return responses, and record calls."""
    calls = async_mock_service(
        hass=hass,
        domain="test",
        service="respond",
        schema=vol.Schema({vol.Required("value"): int}),
        response={"result": "ok"},
    )

    assert (
        hass.services.supports_response("test", "respond")
        is SupportsResponse.OPTIONAL
    )
    response = await hass.services.async_call(
        "test",
        "respond",
        {"value": 1},
        blocking=True,
        return_response=True,
    )

    assert response == {"result": "ok"}
    assert [call.data for call in calls] == [{"value": 1}]

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            "test",
            "respond",
            {"value": "invalid"},
            blocking=True,
            return_response=True,
        )


async def test_mock_service_honors_explicit_response_mode_and_exception(
    hass: HomeAssistant,
) -> None:
    """Explicit response support and raised exceptions should be preserved."""
    calls = async_mock_service(
        hass=hass,
        domain="test",
        service="fail",
        supports_response=SupportsResponse.NONE,
        raise_exception=RuntimeError("service failed"),
    )

    assert (
        hass.services.supports_response("test", "fail")
        is SupportsResponse.NONE
    )
    with pytest.raises(RuntimeError, match="service failed"):
        await hass.services.async_call(
            "test",
            "fail",
            {},
            blocking=True,
        )
    assert len(calls) == 1


def test_component_platform_supports_config_entries_and_custom_components(
    hass: HomeAssistant,
) -> None:
    """Platform setup should honor both optional setup modes."""
    light = MockLight(name="Test", state="off", unique_id="test_light")

    platform = setup_test_component_platform(
        hass,
        LIGHT_DOMAIN,
        [light],
        from_config_entry=True,
        built_in=False,
    )

    assert hasattr(platform, "async_setup_entry")
    integration = hass.data[loader.DATA_INTEGRATIONS]["test"]
    assert isinstance(integration, loader.Integration)
    assert integration.pkg_path == f"{loader.PACKAGE_CUSTOM_COMPONENTS}.test"
    cached_platform = cast(
        object,
        hass.data[loader.DATA_COMPONENTS]["test.light"],
    )
    assert cached_platform is platform


async def test_setup_mock_entities_assigns_and_verifies_registry_area(
    hass: HomeAssistant,
) -> None:
    """Entity setup should leave a verified area assignment in the registry."""
    setup_mock_areas(hass, [MockAreaIds.KITCHEN])
    light = MockLight(name="Test", state="off", unique_id="test_light")

    await setup_mock_entities(
        hass,
        LIGHT_DOMAIN,
        {MockAreaIds.KITCHEN: [light]},
    )

    assert light.entity_id is not None
    entry = async_get_er(hass).async_get(light.entity_id)
    assert entry is not None
    assert entry.area_id == MockAreaIds.KITCHEN.value


async def test_setup_mock_entities_rejects_duplicate_unique_ids(
    hass: HomeAssistant,
) -> None:
    """Duplicate unique IDs cannot be mapped reliably to separate areas."""
    first = MockLight(name="First", state="off", unique_id="duplicate")
    second = MockLight(name="Second", state="off", unique_id="duplicate")

    with pytest.raises(AssertionError, match="Duplicate entity unique_id"):
        await setup_mock_entities(
            hass,
            LIGHT_DOMAIN,
            {
                MockAreaIds.KITCHEN: [first],
                MockAreaIds.LIVING_ROOM: [second],
            },
        )


async def test_setup_mock_entities_fails_when_registry_entry_is_missing(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entity setup should fail if HA does not create a registry entry."""
    from tests.helpers import entities as entity_helpers

    class MissingRegistry:
        def async_get(self, entity_id: str) -> None:
            return None

    light = MockLight(name="Missing", state="off", unique_id="missing")
    monkeypatch.setattr(
        entity_helpers,
        "async_get_er",
        lambda hass: MissingRegistry(),
    )

    with pytest.raises(AssertionError, match="was not created"):
        await setup_mock_entities(
            hass,
            LIGHT_DOMAIN,
            {MockAreaIds.KITCHEN: [light]},
        )


async def test_setup_mock_entities_fails_when_area_assignment_does_not_stick(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entity setup should verify the registry accepted the area update."""
    from tests.helpers import entities as entity_helpers

    class NoopUpdateRegistry:
        def __init__(self) -> None:
            self._real_registry = async_get_er(hass)

        def async_get(self, entity_id: str) -> object | None:
            return self._real_registry.async_get(entity_id)

        def async_update_entity(self, entity_id: str, *, area_id: str) -> None:
            return None

    light = MockLight(name="Noop", state="off", unique_id="noop")
    monkeypatch.setattr(
        entity_helpers,
        "async_get_er",
        lambda hass: NoopUpdateRegistry(),
    )

    with pytest.raises(AssertionError, match="area assignment failed"):
        await setup_mock_entities(
            hass,
            LIGHT_DOMAIN,
            {MockAreaIds.KITCHEN: [light]},
        )
