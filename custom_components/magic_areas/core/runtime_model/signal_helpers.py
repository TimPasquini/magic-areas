"""Managed native-helper signal surface contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from homeassistant.components.derivative.const import (
    CONF_MAX_SUB_INTERVAL,
    CONF_ROUND_DIGITS,
    CONF_TIME_WINDOW,
    CONF_UNIT_PREFIX,
    CONF_UNIT_TIME,
    DOMAIN as DERIVATIVE_DOMAIN,
)
from homeassistant.components.statistics import DOMAIN as STATISTICS_DOMAIN
from homeassistant.components.statistics.sensor import (
    CONF_KEEP_LAST_SAMPLE,
    CONF_MAX_AGE,
    CONF_PERCENTILE,
    CONF_PRECISION,
    CONF_SAMPLES_MAX_BUFFER_SIZE,
    CONF_STATE_CHARACTERISTIC,
)
from homeassistant.components.trend.const import (
    CONF_INVERT,
    CONF_MAX_SAMPLES,
    CONF_MIN_GRADIENT,
    CONF_MIN_SAMPLES,
    CONF_SAMPLE_DURATION,
    DOMAIN as TREND_DOMAIN,
)
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_SOURCE,
    UnitOfTime,
)

from custom_components.magic_areas.core.runtime_model.managed_surfaces import (
    ConfigEntryHelperSurface,
    ManagedSurfaceKind,
    ManagedSurfaceOptionValue,
    build_managed_surface_unique_id,
)

SIGNAL_HELPERS_FEATURE_ID = "signals"


class SignalHelperKind(StrEnum):
    """Native HA helper kinds used as Magic Areas signal inputs."""

    STATISTICS = "statistics"
    TREND = "trend"
    DERIVATIVE = "derivative"


@dataclass(frozen=True, slots=True, kw_only=True)
class SignalHelperSurface(ConfigEntryHelperSurface):
    """Desired state for a MA-managed signal helper.

    Signal helpers expose measured-condition entities. They are still ordinary
    config-entry-backed helper surfaces for reconciliation; the additional fields make
    the signal boundary explicit to feature planners and tests.
    """

    signal_kind: SignalHelperKind
    source_entity_id: str


def trend_signal_surface(
    *,
    entry_id: str,
    area_id: str,
    area_name: str,
    role: str,
    source_entity_id: str,
    min_gradient: float = 0.0,
    sample_duration: int = 0,
    max_samples: int = 2,
    min_samples: int = 2,
    invert: bool = False,
    attribute: str | None = None,
    device_identifier: tuple[str, str] | None = None,
    device_name: str | None = None,
) -> SignalHelperSurface:
    """Build a managed Trend helper signal surface."""
    title = _signal_title(area_name=area_name, kind=SignalHelperKind.TREND, role=role)
    options: dict[str, ManagedSurfaceOptionValue] = {
        CONF_NAME: title,
        CONF_ENTITY_ID: source_entity_id,
        CONF_INVERT: invert,
        CONF_MAX_SAMPLES: max_samples,
        CONF_MIN_SAMPLES: min_samples,
        CONF_MIN_GRADIENT: min_gradient,
        CONF_SAMPLE_DURATION: sample_duration,
    }
    if attribute is not None:
        options[CONF_ATTRIBUTE] = attribute

    return SignalHelperSurface(
        unique_id=_signal_unique_id(
            entry_id=entry_id,
            area_id=area_id,
            signal_kind=SignalHelperKind.TREND,
            role=role,
        ),
        domain=TREND_DOMAIN,
        title=title,
        options=options,
        area_id=area_id,
        device_identifier=device_identifier,
        device_name=device_name,
        signal_kind=SignalHelperKind.TREND,
        source_entity_id=source_entity_id,
    )


def statistics_signal_surface(
    *,
    entry_id: str,
    area_id: str,
    area_name: str,
    role: str,
    source_entity_id: str,
    state_characteristic: str,
    max_age: dict[str, int] | None = None,
    samples_max_buffer_size: int | None = None,
    keep_last_sample: bool = False,
    percentile: int = 50,
    precision: int = 2,
    device_identifier: tuple[str, str] | None = None,
    device_name: str | None = None,
) -> SignalHelperSurface:
    """Build a managed Statistics helper signal surface."""
    title = _signal_title(
        area_name=area_name,
        kind=SignalHelperKind.STATISTICS,
        role=role,
    )
    options: dict[str, ManagedSurfaceOptionValue] = {
        CONF_NAME: title,
        CONF_ENTITY_ID: source_entity_id,
        CONF_STATE_CHARACTERISTIC: state_characteristic,
        CONF_KEEP_LAST_SAMPLE: keep_last_sample,
        CONF_PERCENTILE: percentile,
        CONF_PRECISION: precision,
    }
    if max_age is not None:
        options[CONF_MAX_AGE] = max_age
    if samples_max_buffer_size is not None:
        options[CONF_SAMPLES_MAX_BUFFER_SIZE] = samples_max_buffer_size

    return SignalHelperSurface(
        unique_id=_signal_unique_id(
            entry_id=entry_id,
            area_id=area_id,
            signal_kind=SignalHelperKind.STATISTICS,
            role=role,
        ),
        domain=STATISTICS_DOMAIN,
        title=title,
        options=options,
        area_id=area_id,
        device_identifier=device_identifier,
        device_name=device_name,
        signal_kind=SignalHelperKind.STATISTICS,
        source_entity_id=source_entity_id,
    )


def derivative_signal_surface(
    *,
    entry_id: str,
    area_id: str,
    area_name: str,
    role: str,
    source_entity_id: str,
    time_window: dict[str, int],
    round_digits: int = 2,
    unit_time: UnitOfTime = UnitOfTime.HOURS,
    unit_prefix: str | None = None,
    max_sub_interval: dict[str, int] | None = None,
    device_identifier: tuple[str, str] | None = None,
    device_name: str | None = None,
) -> SignalHelperSurface:
    """Build a managed Derivative helper signal surface."""
    title = _signal_title(
        area_name=area_name,
        kind=SignalHelperKind.DERIVATIVE,
        role=role,
    )
    options: dict[str, ManagedSurfaceOptionValue] = {
        CONF_NAME: title,
        CONF_SOURCE: source_entity_id,
        CONF_ROUND_DIGITS: round_digits,
        CONF_TIME_WINDOW: time_window,
        CONF_UNIT_TIME: unit_time,
    }
    if unit_prefix is not None:
        options[CONF_UNIT_PREFIX] = unit_prefix
    if max_sub_interval is not None:
        options[CONF_MAX_SUB_INTERVAL] = max_sub_interval

    return SignalHelperSurface(
        unique_id=_signal_unique_id(
            entry_id=entry_id,
            area_id=area_id,
            signal_kind=SignalHelperKind.DERIVATIVE,
            role=role,
        ),
        domain=DERIVATIVE_DOMAIN,
        title=title,
        options=options,
        area_id=area_id,
        device_identifier=device_identifier,
        device_name=device_name,
        signal_kind=SignalHelperKind.DERIVATIVE,
        source_entity_id=source_entity_id,
    )


def duration_dict(
    *,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> dict[str, int]:
    """Return the duration-selector option shape used by native HA helpers."""
    return {"hours": hours, "minutes": minutes, "seconds": seconds}


def _signal_unique_id(
    *,
    entry_id: str,
    area_id: str,
    signal_kind: SignalHelperKind,
    role: str,
) -> str:
    """Build a stable Magic Areas-managed signal helper unique ID."""
    return build_managed_surface_unique_id(
        entry_id=entry_id,
        area_id=area_id,
        feature_id=SIGNAL_HELPERS_FEATURE_ID,
        surface_kind=ManagedSurfaceKind.SIGNAL_HELPER,
        role=f"{signal_kind}_{role}",
    )


def _signal_title(*, area_name: str, kind: SignalHelperKind, role: str) -> str:
    """Build a user-visible title for one managed signal helper."""
    return (
        f"Magic Areas Signals {area_name} "
        f"{kind.value.replace('_', ' ').title()} {role.replace('_', ' ').title()}"
    )


__all__ = [
    "SIGNAL_HELPERS_FEATURE_ID",
    "SignalHelperKind",
    "SignalHelperSurface",
    "derivative_signal_surface",
    "duration_dict",
    "statistics_signal_surface",
    "trend_signal_surface",
]
