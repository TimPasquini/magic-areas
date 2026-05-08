"""Observability tests for light-group runtime state-change evaluation."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.core.controls import (
    ControlActionType,
    ControlGroupDecision,
)
from custom_components.magic_areas.light_groups.runtime import evaluate_state_change
from custom_components.magic_areas.light_groups.runtime import setup_group


class _FakeStates:
    def __init__(self, mapping: dict[str, object]) -> None:
        self._mapping = mapping

    def get(self, entity_id: str) -> object | None:
        return self._mapping.get(entity_id)


class _FakeHost:
    def __init__(self) -> None:
        self._attr_extra_state_attributes: dict[str, object] = {}
        self._bright_since_monotonic: float | None = 80.0
        self._last_turn_on_monotonic: float | None = 95.0
        self._last_control_activity_monotonic: float | None = 97.0
        self._inside_lux_samples: list[tuple[float, float]] = [(70.0, 80.0), (90.0, 95.0)]
        self._echo_state = CommandEchoState(controlling=True, awaiting_echo=False)
        self.entity_id = "light.magic_areas_light_groups_kitchen_overhead_lights"
        self.name = "Kitchen Overhead"
        self.logger = MagicMock()
        self.hass = SimpleNamespace(
            states=_FakeStates(
                {
                    "sensor.outside_lux": SimpleNamespace(state="500"),
                    "sensor.inside_lux": SimpleNamespace(state="390"),
                }
            )
        )
        self.policy = SimpleNamespace(
            policy=SimpleNamespace(
                bright_dwell_seconds=10,
                bright_min_on_seconds=10,
                bright_attribution_hold_seconds=5,
                outside_context_source="outside_lux",
                outside_lux_entity="sensor.outside_lux",
                outside_lux_min=300,
                outside_lux_inside_entity="sensor.inside_lux",
                outside_lux_inside_delta=100,
                adaptive_require_ambient_rise=True,
                ambient_rise_window_seconds=120,
                ambient_rise_min_delta=20,
            )
        )


class _FakeSetupHost:
    def __init__(self, hass: HomeAssistant) -> None:
        self._attr_extra_state_attributes: dict[str, object] = {}
        self._attr_is_on = False
        self._listeners_initialized = False
        self._last_known_area_states = ["occupied"]
        self._last_known_area_states_from_dispatcher = False
        self._bright_since_monotonic = None
        self._last_turn_on_monotonic = None
        self._last_control_activity_monotonic = None
        self._inside_lux_samples = []
        self._child_categories = ["sleep_lights", "overhead_lights"]
        self._child_ids = None
        self._entity_ids = ["light.sleep_lamp", "light.overhead_lamp"]
        self._area_id = "kitchen"
        self.category = "all_lights"
        self.entity_id = "light.magic_areas_light_groups_kitchen_all_lights"
        self.hass = hass
        self.logger = MagicMock()
        self._echo_state = CommandEchoState(controlling=True, awaiting_echo=False)
        self.setup_listeners_called = False
        self.reset_control_called = False

    @property
    def controlling(self) -> bool:
        return self._echo_state.controlling

    async def async_get_last_state(self) -> None:
        return None

    async def _setup_listeners(self) -> None:
        self.setup_listeners_called = True

    def _set_echo_state(self, state: CommandEchoState) -> None:
        self._echo_state = state

    def _reset_control_state(self) -> None:
        self.reset_control_called = True


def test_evaluate_state_change_sets_guard_attributes_and_last_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """State evaluation should expose guard status and last policy reason."""
    host = _FakeHost()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.monotonic",
        lambda: 100.0,
    )

    def _fake_eval_and_exec(**kwargs: object) -> tuple[ControlGroupDecision, bool | None]:
        context = kwargs["context"]
        execute_decision = kwargs["execute_decision"]
        decision = ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="unit_test_reason",
        )
        captured["context"] = context
        return decision, execute_decision(decision)

    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.evaluate_and_execute_control_group_policy_sync",
        _fake_eval_and_exec,
    )

    result = evaluate_state_change(
        host,  # type: ignore[arg-type]
        ([], [], ["occupied", "bright"]),
        is_primary=False,
    )

    assert result is False

    guards = host._attr_extra_state_attributes.get("adaptive_guards")
    assert isinstance(guards, dict)
    assert guards == {
        "bright_dwell_met": True,
        "min_on_met": False,
        "inside_bright_met": None,
        "outside_context_ok": True,
        "attribution_hold_met": False,
        "ambient_rise_met": True,
    }
    assert host._attr_extra_state_attributes.get("last_policy_reason") == "unit_test_reason"

    context = captured["context"]
    signals = context.signals
    assert signals.bright_dwell_met is True
    assert signals.min_on_met is False
    assert signals.inside_bright_met is None
    assert signals.outside_context_ok is True
    assert signals.attribution_hold_met is False
    assert signals.ambient_rise_met is True


@pytest.mark.asyncio
async def test_setup_group_resolves_child_policy_entities_by_unique_id(
    hass: HomeAssistant,
) -> None:
    """All-light child control state should not require group-registry metadata."""
    entity_registry = er.async_get(hass)
    sleep_child = entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        "light_groups_kitchen_sleep_lights",
    )
    entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        "light_groups_kitchen_task_lights",
    )
    overhead_child = entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        "light_groups_kitchen_overhead_lights",
    )
    host = _FakeSetupHost(hass)

    await setup_group(host)  # type: ignore[arg-type]

    assert host._child_ids == [sleep_child.entity_id, overhead_child.entity_id]
    assert host._attr_extra_state_attributes["child_ids"] == [
        sleep_child.entity_id,
        overhead_child.entity_id,
    ]
    assert host.setup_listeners_called
    assert not host.reset_control_called
