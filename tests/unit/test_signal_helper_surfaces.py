"""Tests for managed signal-helper surface contracts."""

from __future__ import annotations

from homeassistant.components.derivative.const import DOMAIN as DERIVATIVE_DOMAIN
from homeassistant.components.statistics import DOMAIN as STATISTICS_DOMAIN
from homeassistant.components.statistics.sensor import STAT_CHANGE
from homeassistant.components.trend.const import DOMAIN as TREND_DOMAIN
from homeassistant.const import UnitOfTime

from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ManagedSurfaceKind,
    SignalHelperKind,
    SignalHelperSurface,
    derivative_signal_surface,
    duration_dict,
    statistics_signal_surface,
    trend_signal_surface,
)


def test_trend_signal_surface_uses_config_entry_helper_contract() -> None:
    """Trend signal helpers should compile to managed config-entry helper surfaces."""
    surface = trend_signal_surface(
        entry_id="entry-1",
        area_id="living_room",
        area_name="Living Room",
        role="ambient_rise",
        source_entity_id="sensor.living_room_lux",
        min_gradient=0.25,
        sample_duration=120,
        max_samples=8,
        min_samples=3,
        invert=False,
    )

    assert isinstance(surface, ConfigEntryHelperSurface)
    assert isinstance(surface, SignalHelperSurface)
    assert surface.signal_kind is SignalHelperKind.TREND
    assert surface.domain == TREND_DOMAIN
    assert surface.unique_id == (
        "magic_areas:entry-1:living_room:signals:"
        f"{ManagedSurfaceKind.SIGNAL_HELPER}:trend_ambient_rise"
    )
    assert surface.title == "Magic Areas Signals Living Room Trend Ambient Rise"
    assert surface.options == {
        "name": "Magic Areas Signals Living Room Trend Ambient Rise",
        "entity_id": "sensor.living_room_lux",
        "invert": False,
        "max_samples": 8,
        "min_samples": 3,
        "min_gradient": 0.25,
        "sample_duration": 120,
    }


def test_statistics_signal_surface_preserves_duration_selector_shape() -> None:
    """Statistics signal helpers should expose HA duration selector option payloads."""
    surface = statistics_signal_surface(
        entry_id="entry-1",
        area_id="bathroom",
        area_name="Bathroom",
        role="humidity_settle",
        source_entity_id="sensor.bathroom_humidity",
        state_characteristic=STAT_CHANGE,
        max_age=duration_dict(minutes=15),
        samples_max_buffer_size=20,
        keep_last_sample=True,
        precision=1,
    )

    assert surface.signal_kind is SignalHelperKind.STATISTICS
    assert surface.domain == STATISTICS_DOMAIN
    assert surface.source_entity_id == "sensor.bathroom_humidity"
    assert surface.options == {
        "name": "Magic Areas Signals Bathroom Statistics Humidity Settle",
        "entity_id": "sensor.bathroom_humidity",
        "state_characteristic": "change",
        "keep_last_sample": True,
        "percentile": 50,
        "precision": 1,
        "max_age": {"hours": 0, "minutes": 15, "seconds": 0},
        "sampling_size": 20,
    }


def test_derivative_signal_surface_models_rate_signal_options() -> None:
    """Derivative signal helpers should use HA's source/rate option shape."""
    surface = derivative_signal_surface(
        entry_id="entry-1",
        area_id="kitchen",
        area_name="Kitchen",
        role="lux_rate",
        source_entity_id="sensor.kitchen_lux",
        time_window=duration_dict(minutes=5),
        round_digits=3,
        unit_time=UnitOfTime.MINUTES,
        unit_prefix="k",
        max_sub_interval=duration_dict(seconds=30),
    )

    assert surface.signal_kind is SignalHelperKind.DERIVATIVE
    assert surface.domain == DERIVATIVE_DOMAIN
    assert surface.source_entity_id == "sensor.kitchen_lux"
    assert surface.options == {
        "name": "Magic Areas Signals Kitchen Derivative Lux Rate",
        "source": "sensor.kitchen_lux",
        "round": 3,
        "time_window": {"hours": 0, "minutes": 5, "seconds": 0},
        "unit_time": UnitOfTime.MINUTES,
        "unit_prefix": "k",
        "max_sub_interval": {"hours": 0, "minutes": 0, "seconds": 30},
    }
