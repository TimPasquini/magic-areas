"""Mutable area runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.util import dt as dt_util


@dataclass(slots=True)
class AreaRuntime:
    """Mutable runtime state for a Magic Area.

    This dataclass holds the dynamic state of an area that changes during
    operation. It's managed exclusively by the coordinator and updated
    during refresh cycles.

    Changes to this object should only happen in:
    - Coordinator._async_update_data()
    - Coordinator refresh handlers
    """

    # Entity lists (loaded from registry during coordinator refresh)
    entities: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    magic_entities: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    # Area state (updated by presence tracking logic)
    states: list[str] = field(default_factory=list)
    last_changed: datetime = field(default_factory=dt_util.utcnow)

    # Coordinator status
    last_update_success: bool = True

    # Loading state
    loaded_platforms: list[str] = field(default_factory=list)

    # Timestamps for diagnostics and reload detection
    timestamp: datetime = field(default_factory=dt_util.utcnow)
    _last_reload: datetime = field(
        default_factory=lambda: __import__("datetime").datetime.min.replace(
            tzinfo=dt_util.UTC
        )
    )
    reloading: bool = False
