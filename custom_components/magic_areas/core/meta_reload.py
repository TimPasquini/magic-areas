"""Meta-area reload configuration and policy.

Pure functions for determining when and how to reload meta-areas based on
child area changes, throttling, and area type rules.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum


class MetaAreaAutoReloadSettings(IntEnum):
    """Meta area automatic reload timing settings."""

    DELAY = 3
    DELAY_MULTIPLIER = 4
    THROTTLE = 5


@dataclass(frozen=True, slots=True)
class ReloadDecision:
    """Decision about whether and when to reload a meta-area."""

    should_reload: bool
    """Whether reload should proceed."""

    delay_seconds: float
    """Delay before executing reload (0 = no delay)."""

    reason: str
    """Human-readable reason for the decision."""

    retry_after_seconds: float = 0
    """Suggested bounded retry delay when reload was skipped (0 = no retry)."""


def should_reload_on_area_change(
    *,
    meta_slug: str,
    trigger_area_type: str,
    trigger_area_id: str,
    child_areas: list[str],
) -> bool:
    """Determine if meta-area should reload based on area change signal.

    Reload if: global meta-area (always) or trigger is a child area or
    trigger matches meta-area type (e.g., floor).

    Args:
        meta_slug: Meta-area slug (e.g., "global", "interior", "floor_0")
        trigger_area_type: Type of area that triggered the signal
        trigger_area_id: ID of area that triggered the signal
        child_areas: List of child area IDs for this meta-area

    Returns:
        True if reload should proceed, False otherwise.

    """
    if meta_slug == "global":
        return True

    # For non-global meta-areas (interior, exterior, floors), reload if:
    # 1. The trigger is a floor/area matching this meta-area's type
    # 2. The trigger is a child area of this meta-area
    if trigger_area_type == meta_slug or trigger_area_id in child_areas:
        return True

    return False


def evaluate_reload(
    *,
    meta_slug: str,
    trigger_area_type: str,
    trigger_area_id: str,
    child_areas: list[str],
    last_reload: datetime,
    now: datetime,
    throttle_seconds: int | None = None,
    base_delay: float | None = None,
    max_delay_multiplier: int | None = None,
) -> ReloadDecision:
    """Evaluate if reload should proceed and calculate delay.

    This pure function determines the reload decision based on area changes
    and timing constraints. It does not modify any state.

    Args:
        meta_slug: Meta-area slug ("global", "interior", "floor_0", etc.)
        trigger_area_type: Type of area that triggered the signal
        trigger_area_id: ID of area that triggered the signal
        child_areas: List of child area IDs managed by this meta-area
        last_reload: Timestamp of last reload
        now: Current timestamp
        throttle_seconds: Minimum seconds between reloads (default: 5)
        base_delay: Base delay in seconds (default: 3)
        max_delay_multiplier: Multiplier for max delay calculation (default: 4)

    Returns:
        ReloadDecision with should_reload flag, delay, and reason.

    Timing Rationale:
        1. Throttle checks: Prevent reload spam (5 second minimum between)
        2. Base delay: Allow areas to finish loading (3 second default)
        3. Randomization: Spread reloads across ~3-12 second range to prevent
           CPU stagger when multiple meta-areas trigger simultaneously
        4. Global priority: Global meta-area loads LAST by using max delay,
           ensuring all child areas have loaded first

    Example:
        >>> from datetime import datetime, timedelta
        >>> from homeassistant.util import dt as dt_util
        >>> now = dt_util.utcnow()
        >>> last = now - timedelta(seconds=10)  # 10 seconds ago
        >>> decision = evaluate_reload(
        ...     meta_slug="interior",
        ...     trigger_area_type="interior",
        ...     trigger_area_id="kitchen",
        ...     child_areas=["kitchen", "living_room"],
        ...     last_reload=last,
        ...     now=now,
        ... )
        >>> assert decision.should_reload
        >>> assert 3 <= decision.delay_seconds <= 12

    """
    resolved_throttle, resolved_base_delay, resolved_delay_multiplier = (
        _resolve_reload_settings(
            throttle_seconds=throttle_seconds,
            base_delay=base_delay,
            max_delay_multiplier=max_delay_multiplier,
        )
    )

    precondition_decision = _evaluate_reload_preconditions(
        meta_slug=meta_slug,
        trigger_area_type=trigger_area_type,
        trigger_area_id=trigger_area_id,
        child_areas=child_areas,
        last_reload=last_reload,
        now=now,
        throttle_seconds=resolved_throttle,
    )
    if precondition_decision is not None:
        return precondition_decision

    return _build_scheduled_reload_decision(
        meta_slug=meta_slug,
        base_delay=resolved_base_delay,
        max_delay_multiplier=resolved_delay_multiplier,
    )


def _evaluate_reload_preconditions(
    *,
    meta_slug: str,
    trigger_area_type: str,
    trigger_area_id: str,
    child_areas: list[str],
    last_reload: datetime,
    now: datetime,
    throttle_seconds: int,
) -> ReloadDecision | None:
    """Return a skip decision when match/throttle preconditions fail."""
    if not should_reload_on_area_change(
        meta_slug=meta_slug,
        trigger_area_type=trigger_area_type,
        trigger_area_id=trigger_area_id,
        child_areas=child_areas,
    ):
        return _build_not_matched_decision(
            meta_slug=meta_slug,
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
        )

    return _evaluate_throttle(
        last_reload=last_reload,
        now=now,
        throttle_seconds=throttle_seconds,
    )


def _build_scheduled_reload_decision(
    *,
    meta_slug: str,
    base_delay: float,
    max_delay_multiplier: int,
) -> ReloadDecision:
    """Build the positive reload decision after preconditions pass."""
    delay, reason = _compute_reload_delay_and_reason(
        meta_slug=meta_slug,
        base_delay=base_delay,
        max_delay_multiplier=max_delay_multiplier,
    )

    return ReloadDecision(
        should_reload=True,
        delay_seconds=delay,
        reason=reason,
        retry_after_seconds=0,
    )


def _resolve_reload_settings(
    *,
    throttle_seconds: int | None,
    base_delay: float | None,
    max_delay_multiplier: int | None,
) -> tuple[int, float, int]:
    """Resolve optional settings to concrete values."""
    resolved_throttle = (
        throttle_seconds
        if throttle_seconds is not None
        else MetaAreaAutoReloadSettings.THROTTLE
    )
    resolved_base_delay = (
        base_delay if base_delay is not None else MetaAreaAutoReloadSettings.DELAY
    )
    resolved_delay_multiplier = (
        max_delay_multiplier
        if max_delay_multiplier is not None
        else MetaAreaAutoReloadSettings.DELAY_MULTIPLIER
    )
    return resolved_throttle, resolved_base_delay, resolved_delay_multiplier


def _build_not_matched_decision(
    *,
    meta_slug: str,
    trigger_area_type: str,
    trigger_area_id: str,
) -> ReloadDecision:
    """Build the decision returned when an area change does not match."""
    return ReloadDecision(
        should_reload=False,
        delay_seconds=0,
        reason=f"Area {trigger_area_id} (type={trigger_area_type}) not matched for {meta_slug}",
        retry_after_seconds=0,
    )


def _evaluate_throttle(
    *,
    last_reload: datetime,
    now: datetime,
    throttle_seconds: int,
) -> ReloadDecision | None:
    """Return a throttle decision when the reload window has not elapsed."""
    time_since_reload = now - last_reload
    throttle_delta = timedelta(seconds=throttle_seconds)

    if time_since_reload >= throttle_delta:
        return None

    seconds_remaining = (throttle_delta - time_since_reload).total_seconds()
    return ReloadDecision(
        should_reload=False,
        delay_seconds=0,
        reason=f"Throttled: {seconds_remaining:.1f}s remaining ({throttle_seconds}s minimum)",
        retry_after_seconds=seconds_remaining,
    )


def _compute_reload_delay_and_reason(
    *,
    meta_slug: str,
    base_delay: float,
    max_delay_multiplier: int,
) -> tuple[float, str]:
    """Compute delay and reason for a matched non-throttled reload."""
    max_delay = max_delay_multiplier * base_delay

    if meta_slug == "global":
        return max_delay, f"Global reload scheduled with max delay ({max_delay:.1f}s)"

    delay = random.uniform(base_delay, max_delay)
    return delay, f"Reload scheduled with randomized delay ({delay:.1f}s)"
