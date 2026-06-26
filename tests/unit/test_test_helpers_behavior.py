"""Behavioral contracts for shared test helpers."""

import asyncio
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol
from homeassistant import loader
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_NAME, EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, State, SupportsResponse
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.defaults import (
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
)
from tests.const import MOCK_AREAS, MockAreaIds
from tests.helpers.assertions import (
    assert_attribute,
    assert_in_attribute,
    assert_state,
)
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.entities import (
    setup_mock_entities,
)
from tests.helpers.lifecycle import drain_hass, init_integration, shutdown_integration
from tests.helpers.platforms import (
    mock_integration,
    mock_platform,
    setup_test_component_platform,
)
from tests.helpers.registries import setup_mock_areas
from tests.helpers.services import async_mock_service
from tests.helpers.waits import wait_for_attribute, wait_for_state, wait_until
from tests.mocks import MockLight, MockModule, MockPlatform


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


def test_config_entry_builder_returns_complete_independent_defaults() -> None:
    """Valid config payloads should be complete and avoid shared containers."""
    first = get_basic_config_entry_data(MockAreaIds.KITCHEN)
    second = get_basic_config_entry_data(MockAreaIds.KITCHEN)

    assert first == {
        ATTR_NAME: "Kitchen",
        CONF_ID: MockAreaIds.KITCHEN.value,
        CONF_CLEAR_TIMEOUT: 0,
        CONF_EXTENDED_TIMEOUT: 5,
        CONF_TYPE: MOCK_AREAS[MockAreaIds.KITCHEN][CONF_TYPE],
        CONF_EXCLUDE_ENTITIES: [],
        CONF_INCLUDE_ENTITIES: [],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        CONF_ENABLED_FEATURES: {},
    }
    assert first[CONF_EXCLUDE_ENTITIES] is not second[CONF_EXCLUDE_ENTITIES]
    assert first[CONF_INCLUDE_ENTITIES] is not second[CONF_INCLUDE_ENTITIES]
    assert first[CONF_ENABLED_FEATURES] is not second[CONF_ENABLED_FEATURES]


async def test_lifecycle_helpers_handle_preadded_entry_and_cleanup(
    hass: HomeAssistant,
) -> None:
    """Lifecycle helpers should load and unload one already-registered entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=get_basic_config_entry_data(MockAreaIds.KITCHEN),
    )
    config_entry.add_to_hass(hass)

    await init_integration(
        hass,
        [config_entry],
        areas=[MockAreaIds.KITCHEN],
    )

    assert config_entry.state.name == ConfigEntryState.LOADED.name
    assert hass.config_entries.async_entries(DOMAIN) == [config_entry]
    assert (
        async_get_ar(hass).async_get_area_by_name(MockAreaIds.KITCHEN.value) is not None
    )
    assert config_entry.runtime_data is not None

    await shutdown_integration(hass, [config_entry])

    assert config_entry.state.name == ConfigEntryState.NOT_LOADED.name
    assert not hass.data.get(DOMAIN)


async def test_init_integration_requires_loaded_entry_state(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Initialization should reject entries that never reach LOADED."""
    import tests.helpers.lifecycle as lifecycle_helpers

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=get_basic_config_entry_data(MockAreaIds.KITCHEN),
    )
    config_entry.add_to_hass(hass)
    monkeypatch.setattr(
        lifecycle_helpers,
        "async_setup_component",
        AsyncMock(return_value=True),
    )

    with pytest.raises(AssertionError):
        await init_integration(
            hass,
            [config_entry],
            areas=[MockAreaIds.KITCHEN],
        )

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_drain_hass_runs_requested_cycle_count() -> None:
    """Loop draining should execute exactly the requested number of cycles."""
    hass = Mock(spec=HomeAssistant)
    hass.async_block_till_done = AsyncMock()

    await drain_hass(cast(HomeAssistant, hass), cycles=3)

    assert hass.async_block_till_done.await_count == 3


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

    assert hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0) == listeners_before


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


async def test_wait_until_yields_while_no_ha_work_is_pending(
    hass: HomeAssistant,
) -> None:
    """An idle HA loop should not turn predicate polling into a busy spin."""
    ticker_runs = 0

    async def ticker() -> None:
        nonlocal ticker_runs
        while ticker_runs < 3:
            await asyncio.sleep(0)
            ticker_runs += 1

    ticker_task = asyncio.create_task(ticker())

    with pytest.raises(AssertionError, match="Timed out"):
        await wait_until(hass, lambda: False, timeout=0.02)
    await ticker_task

    assert ticker_runs == 3


async def test_wait_until_observes_delayed_async_work(
    hass: HomeAssistant,
) -> None:
    """Cooperative polling should observe state changed by a delayed task."""
    ready = False

    async def set_ready() -> None:
        nonlocal ready
        await asyncio.sleep(0.01)
        ready = True

    task = asyncio.create_task(set_ready())

    await wait_until(hass, lambda: ready, timeout=0.1)
    await task


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
        hass.services.supports_response("test", "respond") is SupportsResponse.OPTIONAL
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

    assert hass.services.supports_response("test", "fail") is SupportsResponse.NONE
    with pytest.raises(RuntimeError, match="service failed"):
        await hass.services.async_call(
            "test",
            "fail",
            {},
            blocking=True,
        )
    assert len(calls) == 1


def test_mock_integration_registers_custom_component_and_blocks_platform_imports(
    hass: HomeAssistant,
) -> None:
    """Mock integrations should populate HA caches and block unknown platforms."""
    module = MockModule("direct_mock")

    integration = mock_integration(hass, module=module, built_in=False)
    module_cache = cast(dict[str, object], hass.data[loader.DATA_COMPONENTS])

    assert integration.pkg_path == f"{loader.PACKAGE_CUSTOM_COMPONENTS}.direct_mock"
    assert hass.data[loader.DATA_INTEGRATIONS]["direct_mock"] is integration
    assert module_cache["direct_mock"] is module
    with pytest.raises(ImportError, match="direct_mock.sensor"):
        integration._import_platform("sensor")  # pylint: disable=protected-access


def test_mock_platform_reuses_integration_and_populates_platform_cache(
    hass: HomeAssistant,
) -> None:
    """Platform registration should preserve an existing integration object."""
    integration = mock_integration(
        hass,
        module=MockModule("direct_platform"),
    )
    platform = MockPlatform()

    mock_platform(hass, "direct_platform.light", platform)
    module_cache = cast(dict[str, object], hass.data[loader.DATA_COMPONENTS])

    assert hass.data[loader.DATA_INTEGRATIONS]["direct_platform"] is integration
    assert module_cache["direct_platform.light"] is platform
    assert "light.py" in integration._top_level_files  # pylint: disable=protected-access


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
    import tests.helpers.entities as entity_helpers

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
    import tests.helpers.entities as entity_helpers

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
