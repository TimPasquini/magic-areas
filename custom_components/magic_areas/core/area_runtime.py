"""Mutable area runtime state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AreaRuntime:
    """Mutable runtime state for a Magic Area.

    Managed exclusively by the coordinator and updated during refresh cycles.
    Presence state is owned by AreaStateTrackerEntity and read from the HA
    state machine; it is not mirrored here.
    """

    # Coordinator status
    last_update_success: bool = True
