"""Pure target contracts for control intent resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ControlTargetKind(StrEnum):
    """Execution target shape available to control intent adapters."""

    LABEL = "label"
    HELPER_ENTITY = "helper_entity"
    ENTITY_SUBSET = "entity_subset"
    COMPATIBILITY_ENTITY = "compatibility_entity"


class ControlTargetPrecision(StrEnum):
    """How exactly a target represents the intended role/scope."""

    BROAD = "broad"
    EXACT = "exact"
    FILTERED = "filtered"
    COMPATIBILITY = "compatibility"


class ControlTargetSource(StrEnum):
    """Where target membership or execution surface came from."""

    RECONCILED_LABEL = "reconciled_label"
    MANAGED_HELPER = "managed_helper"
    ENTITY_SUBSET = "entity_subset"
    GROUP_REGISTRY = "group_registry"
    POLICY_ENTITY = "policy_entity"
    CONFIG_RECONCILIATION = "config_reconciliation"


@dataclass(frozen=True, slots=True)
class RoleTarget:
    """Engine-facing role target independent of one membership storage mechanism."""

    role: str
    domain: str
    area_id: str
    kind: ControlTargetKind
    precision: ControlTargetPrecision
    source: ControlTargetSource
    label_name: str | None = None
    label_id: str | None = None
    helper_unique_id: str | None = None
    helper_entity_id: str | None = None
    entity_ids: tuple[str, ...] = ()
    compatibility_entity_id: str | None = None
    resolution_path: tuple[str, ...] = ()
    fallback_reason: str | None = None

    @property
    def target_entity_ids(self) -> tuple[str, ...]:
        """Return explicit entity IDs for target kinds backed by entity IDs."""
        if self.kind is ControlTargetKind.HELPER_ENTITY and self.helper_entity_id:
            return (self.helper_entity_id,)
        if (
            self.kind is ControlTargetKind.COMPATIBILITY_ENTITY
            and self.compatibility_entity_id
        ):
            return (self.compatibility_entity_id,)
        return self.entity_ids

    @property
    def is_executable(self) -> bool:
        """Return whether this target has enough data to execute a service call."""
        if self.kind is ControlTargetKind.LABEL:
            return bool(self.label_id or self.label_name)
        return bool(self.target_entity_ids)

    @property
    def uses_broad_label_target(self) -> bool:
        """Return whether this target should execute through HA label targeting."""
        return self.kind is ControlTargetKind.LABEL


__all__ = [
    "ControlTargetKind",
    "ControlTargetPrecision",
    "ControlTargetSource",
    "RoleTarget",
]
