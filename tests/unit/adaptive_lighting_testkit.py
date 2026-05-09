"""Test helpers for mocked Adaptive Lighting coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback

from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    AdaptiveLightingSwitchSet,
    adaptive_lighting_switch_entity_ids,
    switch_set_from_explicit_refs,
)

ADAPTIVE_LIGHTING_DOMAIN = "adaptive_lighting"
SERVICE_APPLY = "apply"
SERVICE_SET_MANUAL_CONTROL = "set_manual_control"
SERVICE_CHANGE_SWITCH_SETTINGS = "change_switch_settings"
EVENT_MANUAL_CONTROL = "adaptive_lighting.manual_control"


@dataclass(slots=True)
class AdaptiveLightingCall:
    """Captured Adaptive Lighting service call."""

    service: str
    data: dict[str, object]


@dataclass(slots=True)
class AdaptiveLightingHarness:
    """Mock Adaptive Lighting switch/service/event surface for tests."""

    hass: HomeAssistant
    name: str
    area_id: str
    role: str | None = None
    calls: list[AdaptiveLightingCall] = field(default_factory=list)
    manual_control_events: list[dict[str, object]] = field(default_factory=list)

    @property
    def switch_entity_ids(self) -> dict[str, str]:
        """Return conventional switch entity IDs for this mocked setup."""
        return adaptive_lighting_switch_entity_ids(self.name)

    @property
    def switch_set(self) -> AdaptiveLightingSwitchSet:
        """Return the resolved switch set for this mocked setup."""
        switch_set = switch_set_from_explicit_refs(
            area_id=self.area_id,
            role=self.role,
            switch_refs=self.switch_entity_ids,
        )
        if switch_set is None:  # pragma: no cover - guarded by local construction.
            raise AssertionError("mock Adaptive Lighting switch set is incomplete")
        return switch_set

    async def async_setup(self) -> None:
        """Create mocked switches and register mocked services/events."""
        self._set_switch_states()
        self._register_services()
        self.hass.bus.async_listen(EVENT_MANUAL_CONTROL, self._record_manual_control_event)
        await self.hass.async_block_till_done()

    def fire_manual_control_event(
        self,
        *,
        entity_id: str,
        switch_entity_id: str | None = None,
    ) -> None:
        """Fire the Adaptive Lighting manual-control event shape MA consumes."""
        self.hass.bus.async_fire(
            EVENT_MANUAL_CONTROL,
            {
                "entity_id": entity_id,
                "switch": switch_entity_id or self.switch_set.main_switch_entity_id,
            },
        )

    def _set_switch_states(self) -> None:
        """Create the four behavior-control switches in HA state."""
        switches = self.switch_entity_ids
        self.hass.states.async_set(
            switches[MAIN_SWITCH],
            STATE_ON,
            {"manual_control": []},
        )
        self.hass.states.async_set(switches[SLEEP_SWITCH], STATE_OFF)
        self.hass.states.async_set(switches[ADAPT_BRIGHTNESS_SWITCH], STATE_ON)
        self.hass.states.async_set(switches[ADAPT_COLOR_SWITCH], STATE_ON)

    def _register_services(self) -> None:
        """Register mocked Adaptive Lighting services and capture calls."""
        for service in (
            SERVICE_APPLY,
            SERVICE_SET_MANUAL_CONTROL,
            SERVICE_CHANGE_SWITCH_SETTINGS,
        ):
            if self.hass.services.has_service(ADAPTIVE_LIGHTING_DOMAIN, service):
                continue
            self.hass.services.async_register(
                ADAPTIVE_LIGHTING_DOMAIN,
                service,
                self._capture_service_call(service),
            )

    def _capture_service_call(self, service: str) -> Callable[[ServiceCall], None]:
        """Return a callback that captures one mocked service call."""

        @callback
        def _capture(call: ServiceCall) -> None:
            self.calls.append(AdaptiveLightingCall(service=service, data=dict(call.data)))

        return _capture

    @callback
    def _record_manual_control_event(self, event: Event[dict[str, object]]) -> None:
        """Record mocked Adaptive Lighting manual-control events."""
        self.manual_control_events.append(dict(event.data))


async def setup_adaptive_lighting_harness(
    hass: HomeAssistant,
    *,
    name: str = "Living Room",
    area_id: str = "living_room",
    role: str | None = "overhead_lights",
) -> AdaptiveLightingHarness:
    """Create and initialize a mocked Adaptive Lighting harness."""
    harness = AdaptiveLightingHarness(
        hass=hass,
        name=name,
        area_id=area_id,
        role=role,
    )
    await harness.async_setup()
    return harness


__all__ = [
    "ADAPTIVE_LIGHTING_DOMAIN",
    "EVENT_MANUAL_CONTROL",
    "SERVICE_APPLY",
    "SERVICE_CHANGE_SWITCH_SETTINGS",
    "SERVICE_SET_MANUAL_CONTROL",
    "AdaptiveLightingCall",
    "AdaptiveLightingHarness",
    "setup_adaptive_lighting_harness",
]
