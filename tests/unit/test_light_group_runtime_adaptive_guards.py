"""Runtime-level tests for adaptive light-group guard helpers."""

from types import SimpleNamespace
from collections.abc import Callable
from typing import cast

import pytest
from custom_components.magic_areas.light_groups.runtime import (
    _LightGroupHost,
    _adaptive_bright_recheck_delay,
    _ambient_rise_met,
    _direct_light_output_changed,
    _inside_bright_met,
    _outside_context_ok,
    _schedule_adaptive_bright_recheck_if_needed,
    _update_inside_lux_tracking,
)
from custom_components.magic_areas.area_state import AreaStates


class _FakeStates:
    def __init__(self, mapping: dict[str, object]) -> None:
        self._mapping = mapping

    def get(self, entity_id: str) -> object | None:
        return self._mapping.get(entity_id)


class _FakeHost:
    def __init__(
        self, *, policy_config: dict[str, object], states: dict[str, object]
    ) -> None:
        self.policy = SimpleNamespace(policy=SimpleNamespace(**policy_config))
        self.hass = SimpleNamespace(states=_FakeStates(states))
        self._inside_lux_samples: list[tuple[float, float]] = []
        self._ambient_rise_signal_unique_id: str | None = None
        self._last_direct_light_activity_monotonic: float | None = None
        self._ambient_rise_trend_contaminated = False
        self._area_id = ""
        self._last_known_area_states: list[str] = []
        self._bright_since_monotonic: float | None = None
        self.area_state_changed: Callable[
            [str, tuple[list[str], list[str], list[str]]], bool
        ] = lambda _area_id, _states: False
        self.track_group_listener: Callable[[Callable[[], None], str], None] = (
            lambda _remove, _name: None
        )


def _state(value: str, attributes: dict[str, object] | None = None) -> object:
    return SimpleNamespace(state=value, attributes=attributes or {})


def _host(host: _FakeHost) -> _LightGroupHost:
    return cast(_LightGroupHost, host)


def test_outside_context_ok_with_sun_source() -> None:
    """Sun source should only pass when sun.sun is above horizon."""
    host = _FakeHost(
        policy_config={"outside_context_source": "sun"},
        states={"sun.sun": _state("above_horizon")},
    )
    assert _outside_context_ok(_host(host)) is True

    host = _FakeHost(
        policy_config={"outside_context_source": "sun"},
        states={"sun.sun": _state("below_horizon")},
    )
    assert _outside_context_ok(_host(host)) is False


def test_outside_context_ok_with_outside_lux_contrast_gate() -> None:
    """Outside-lux source should respect min-lux and optional contrast delta."""
    host = _FakeHost(
        policy_config={
            "outside_context_source": "outside_lux",
            "outside_lux_entity": "sensor.outside",
            "outside_lux_min": 300,
            "outside_lux_inside_entity": "sensor.inside",
            "outside_lux_inside_delta": 100,
        },
        states={
            "sensor.outside": _state("500"),
            "sensor.inside": _state("350"),
        },
    )
    assert _outside_context_ok(_host(host)) is True

    host = _FakeHost(
        policy_config={
            "outside_context_source": "outside_lux",
            "outside_lux_entity": "sensor.outside",
            "outside_lux_min": 600,
            "outside_lux_inside_entity": "sensor.inside",
            "outside_lux_inside_delta": 100,
        },
        states={
            "sensor.outside": _state("500"),
            "sensor.inside": _state("350"),
        },
    )
    assert _outside_context_ok(_host(host)) is False

    host = _FakeHost(
        policy_config={
            "outside_context_source": "outside_lux",
            "outside_lux_entity": "sensor.outside",
            "outside_lux_min": 300,
            "outside_lux_inside_entity": "",
            "outside_lux_inside_delta": 0,
        },
        states={"sensor.outside": _state("500")},
    )
    assert _outside_context_ok(_host(host)) is True


def test_outside_context_ok_with_outside_lux_ratio_gate() -> None:
    """Outside-lux ratio gate should enforce configured outside/inside ratio."""
    host = _FakeHost(
        policy_config={
            "outside_context_source": "outside_lux",
            "outside_lux_entity": "sensor.outside",
            "outside_lux_min": 100,
            "outside_lux_inside_entity": "sensor.inside",
            "outside_lux_inside_delta": 0,
            "outside_lux_inside_ratio_min_percent": 150,
        },
        states={
            "sensor.outside": _state("300"),
            "sensor.inside": _state("180"),
        },
    )
    assert _outside_context_ok(_host(host)) is True

    host = _FakeHost(
        policy_config={
            "outside_context_source": "outside_lux",
            "outside_lux_entity": "sensor.outside",
            "outside_lux_min": 100,
            "outside_lux_inside_entity": "sensor.inside",
            "outside_lux_inside_delta": 0,
            "outside_lux_inside_ratio_min_percent": 200,
        },
        states={
            "sensor.outside": _state("300"),
            "sensor.inside": _state("180"),
        },
    )
    assert _outside_context_ok(_host(host)) is False


def test_outside_context_uses_binary_override_when_configured() -> None:
    """Outside bright binary should override source-based outside checks."""
    host = _FakeHost(
        policy_config={
            "outside_context_source": "outside_lux",
            "outside_bright_entity": "binary_sensor.outside_bright",
            "outside_lux_entity": "sensor.outside",
            "outside_lux_min": 9000,
        },
        states={
            "binary_sensor.outside_bright": _state("on"),
            "sensor.outside": _state("100"),
        },
    )
    assert _outside_context_ok(_host(host)) is True

    host = _FakeHost(
        policy_config={
            "outside_context_source": "sun",
            "outside_bright_entity": "binary_sensor.outside_bright",
        },
        states={"binary_sensor.outside_bright": _state("off")},
    )
    assert _outside_context_ok(_host(host)) is False


def test_inside_bright_met_reads_optional_binary_entity() -> None:
    """Inside bright helper should return None for unknown source, else boolean."""
    host = _FakeHost(policy_config={}, states={})
    assert _inside_bright_met(_host(host)) is None

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={},
    )
    assert _inside_bright_met(_host(host)) is None

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={"binary_sensor.room_bright": _state("on")},
    )
    assert _inside_bright_met(_host(host)) is True

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={"binary_sensor.room_bright": _state("off")},
    )
    assert _inside_bright_met(_host(host)) is False

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={"binary_sensor.room_bright": _state("unknown")},
    )
    assert _inside_bright_met(_host(host)) is None

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={"binary_sensor.room_bright": _state("unavailable")},
    )
    assert _inside_bright_met(_host(host)) is None


def test_ambient_rise_met_respects_require_window_and_delta() -> None:
    """Ambient-rise helper should gate based on requirement/window/delta."""
    now = 1000.0
    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": False,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={},
    )
    assert _ambient_rise_met(_host(host), now) is True

    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": True,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={},
    )
    assert _ambient_rise_met(_host(host), now) is False

    host._inside_lux_samples = [(now - 100, 100.0), (now - 10, 125.0)]
    assert _ambient_rise_met(_host(host), now) is True

    host._inside_lux_samples = [(now - 100, 100.0), (now - 10, 110.0)]
    assert _ambient_rise_met(_host(host), now) is False


def test_ambient_rise_met_prefers_managed_trend_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed Trend helper state should replace transitional in-runtime samples."""
    now = 1000.0
    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": True,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={"binary_sensor.managed_ambient_rise": _state("on")},
    )
    host._ambient_rise_signal_unique_id = (
        "magic_areas:entry-1:area-1:signals:signal_helper:trend_ambient_rise"
    )
    host._inside_lux_samples = [(now - 100, 100.0), (now - 10, 101.0)]
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.er.async_get",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.resolve_managed_surface_entity_id",
        lambda *_args, **_kwargs: "binary_sensor.managed_ambient_rise",
    )

    assert _ambient_rise_met(_host(host), now) is True


def test_ambient_rise_met_blocks_contaminated_managed_trend_until_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed Trend on is invalid until a non-on state clears contamination."""
    now = 1000.0
    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": True,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={"binary_sensor.managed_ambient_rise": _state("on")},
    )
    host._ambient_rise_signal_unique_id = (
        "magic_areas:entry-1:area-1:signals:signal_helper:trend_ambient_rise"
    )
    host._ambient_rise_trend_contaminated = True
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.er.async_get",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.resolve_managed_surface_entity_id",
        lambda *_args, **_kwargs: "binary_sensor.managed_ambient_rise",
    )

    assert _ambient_rise_met(_host(host), now) is False

    host.hass.states._mapping["binary_sensor.managed_ambient_rise"] = _state("off")
    assert _ambient_rise_met(_host(host), now) is False
    assert host._ambient_rise_trend_contaminated is False

    host.hass.states._mapping["binary_sensor.managed_ambient_rise"] = _state("on")
    assert _ambient_rise_met(_host(host), now) is True


def test_ambient_rise_met_falls_back_when_managed_trend_helper_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable managed helper startup state should keep fallback behavior alive."""
    now = 1000.0
    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": True,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={"binary_sensor.managed_ambient_rise": _state("unknown")},
    )
    host._ambient_rise_signal_unique_id = (
        "magic_areas:entry-1:area-1:signals:signal_helper:trend_ambient_rise"
    )
    host._inside_lux_samples = [(now - 100, 100.0), (now - 10, 130.0)]
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.er.async_get",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.resolve_managed_surface_entity_id",
        lambda *_args, **_kwargs: "binary_sensor.managed_ambient_rise",
    )

    assert _ambient_rise_met(_host(host), now) is True


def test_adaptive_bright_recheck_polls_managed_ambient_rise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ambient-rise waits should poll managed Trend state if listener events miss."""
    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": True,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={"binary_sensor.managed_ambient_rise": _state("off")},
    )
    host._ambient_rise_signal_unique_id = (
        "magic_areas:entry-1:area-1:signals:signal_helper:trend_ambient_rise"
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.er.async_get",
        lambda _hass: object(),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.resolve_managed_surface_entity_id",
        lambda *_args, **_kwargs: "binary_sensor.managed_ambient_rise",
    )

    assert (
        _adaptive_bright_recheck_delay(
            _host(host),
            "bright_adaptive_waiting_ambient_rise",
        )
        == 1.0
    )


def test_adaptive_bright_recheck_executes_scheduled_state_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scheduled recheck should evaluate the latest live area states."""
    callbacks: list[object] = []
    cancellations: list[bool] = []
    state_changes: list[tuple[str, tuple[list[str], list[str], list[str]]]] = []
    tracked: list[tuple[object, str]] = []
    host = _FakeHost(
        policy_config={"brightness_mode": "adaptive"},
        states={},
    )
    host._area_id = "area-1"
    host._last_known_area_states = [AreaStates.BRIGHT.value]
    host._bright_since_monotonic = None

    def call_later(_delay: float, callback: Callable[[], None]) -> object:
        callbacks.append(callback)

        def cancel() -> None:
            cancellations.append(True)

        return SimpleNamespace(cancel=cancel)

    def area_state_changed(
        area_id: str,
        states: tuple[list[str], list[str], list[str]],
    ) -> bool:
        state_changes.append((area_id, states))
        return True

    def track_group_listener(remove: Callable[[], None], name: str) -> None:
        tracked.append((remove, name))

    host.hass.loop = SimpleNamespace(call_later=call_later)
    host.area_state_changed = area_state_changed
    host.track_group_listener = track_group_listener
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.read_area_presence_states",
        lambda _hass, _area_id: [
            AreaStates.OCCUPIED.value,
            AreaStates.BRIGHT.value,
        ],
    )

    _schedule_adaptive_bright_recheck_if_needed(
        _host(host),
        "bright_adaptive_waiting_dwell",
        [AreaStates.BRIGHT.value],
    )

    assert len(callbacks) == 1
    assert len(tracked) == 1
    assert tracked[0][1] == "adaptive_bright_recheck"
    callback = cast(Callable[[], None], callbacks[0])
    callback()
    assert state_changes == [
        (
            "area-1",
            (
                [],
                [],
                [AreaStates.OCCUPIED.value, AreaStates.BRIGHT.value],
            ),
        )
    ]
    remove_listener = cast(Callable[[], None], tracked[0][0])
    remove_listener()
    assert cancellations == [True]


def test_direct_light_output_changed_detects_on_and_brightness_increase() -> None:
    """Direct-light watcher should flag brightness increases but not color changes."""
    assert _direct_light_output_changed(_state("off"), _state("on")) is True
    assert (
        _direct_light_output_changed(
            _state("on", {"brightness": 20}),
            _state("on", {"brightness": 90}),
        )
        is True
    )
    assert (
        _direct_light_output_changed(
            _state("on", {"brightness": 90}),
            _state("on", {"brightness": 20}),
        )
        is False
    )
    assert (
        _direct_light_output_changed(
            _state("on", {"color_temp_kelvin": 2700}),
            _state("on", {"color_temp_kelvin": 3000}),
        )
        is False
    )


def test_update_inside_lux_tracking_adds_and_prunes_samples() -> None:
    """Tracking helper should append latest inside lux and prune outside window."""
    now = 1000.0
    host = _FakeHost(
        policy_config={
            "outside_lux_inside_entity": "sensor.inside",
            "ambient_rise_window_seconds": 60,
        },
        states={"sensor.inside": _state("120")},
    )
    host._inside_lux_samples = [(800.0, 80.0), (950.0, 100.0)]

    _update_inside_lux_tracking(_host(host), now)

    assert host._inside_lux_samples == [(950.0, 100.0), (1000.0, 120.0)]


def test_update_inside_lux_tracking_window_zero_keeps_latest_only() -> None:
    """Zero window should keep only the latest sample for deterministic behavior."""
    now = 1000.0
    host = _FakeHost(
        policy_config={
            "outside_lux_inside_entity": "sensor.inside",
            "ambient_rise_window_seconds": 0,
        },
        states={"sensor.inside": _state("220")},
    )
    host._inside_lux_samples = [(900.0, 100.0), (950.0, 150.0)]

    _update_inside_lux_tracking(_host(host), now)

    assert host._inside_lux_samples == [(1000.0, 220.0)]
