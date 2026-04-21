"""Runtime-level tests for adaptive light-group guard helpers."""

from types import SimpleNamespace

from custom_components.magic_areas.light_groups.runtime import (
    _ambient_rise_met,
    _inside_bright_met,
    _outside_context_ok,
    _update_inside_lux_tracking,
)


class _FakeStates:
    def __init__(self, mapping: dict[str, object]) -> None:
        self._mapping = mapping

    def get(self, entity_id: str) -> object | None:
        return self._mapping.get(entity_id)


class _FakeHost:
    def __init__(self, *, policy_config: dict[str, object], states: dict[str, object]) -> None:
        self.policy = SimpleNamespace(policy=SimpleNamespace(**policy_config))
        self.hass = SimpleNamespace(states=_FakeStates(states))
        self._inside_lux_samples: list[tuple[float, float]] = []


def _state(value: str) -> object:
    return SimpleNamespace(state=value)


def test_outside_context_ok_with_sun_source() -> None:
    """Sun source should only pass when sun.sun is above horizon."""
    host = _FakeHost(
        policy_config={"outside_context_source": "sun"},
        states={"sun.sun": _state("above_horizon")},
    )
    assert _outside_context_ok(host) is True

    host = _FakeHost(
        policy_config={"outside_context_source": "sun"},
        states={"sun.sun": _state("below_horizon")},
    )
    assert _outside_context_ok(host) is False


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
    assert _outside_context_ok(host) is True

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
    assert _outside_context_ok(host) is False

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
    assert _outside_context_ok(host) is True


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
    assert _outside_context_ok(host) is True

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
    assert _outside_context_ok(host) is False


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
    assert _outside_context_ok(host) is True

    host = _FakeHost(
        policy_config={
            "outside_context_source": "sun",
            "outside_bright_entity": "binary_sensor.outside_bright",
        },
        states={"binary_sensor.outside_bright": _state("off")},
    )
    assert _outside_context_ok(host) is False


def test_inside_bright_met_reads_optional_binary_entity() -> None:
    """Inside bright helper should return None when unset, else boolean."""
    host = _FakeHost(policy_config={}, states={})
    assert _inside_bright_met(host) is None

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={"binary_sensor.room_bright": _state("on")},
    )
    assert _inside_bright_met(host) is True

    host = _FakeHost(
        policy_config={"inside_bright_entity": "binary_sensor.room_bright"},
        states={"binary_sensor.room_bright": _state("off")},
    )
    assert _inside_bright_met(host) is False


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
    assert _ambient_rise_met(host, now) is True

    host = _FakeHost(
        policy_config={
            "adaptive_require_ambient_rise": True,
            "ambient_rise_window_seconds": 120,
            "ambient_rise_min_delta": 20,
        },
        states={},
    )
    assert _ambient_rise_met(host, now) is False

    host._inside_lux_samples = [(now - 100, 100.0), (now - 10, 125.0)]
    assert _ambient_rise_met(host, now) is True

    host._inside_lux_samples = [(now - 100, 100.0), (now - 10, 110.0)]
    assert _ambient_rise_met(host, now) is False


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

    _update_inside_lux_tracking(host, now)

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

    _update_inside_lux_tracking(host, now)

    assert host._inside_lux_samples == [(1000.0, 220.0)]
