"""Registry for default and custom control-group definitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Protocol


class ControlGroupPolicyId(StrEnum):
    """Policy IDs used for control/aggregate group registration and lookup."""

    LIGHT_GROUPS = "light_groups"
    FAN_GROUPS = "fan_groups"
    CLIMATE_CONTROL = "climate_control"
    MEDIA_PLAYER_GROUPS = "media_player_groups"
    AGGREGATE = "aggregate"
    CUSTOM_CONTROL_GROUP = "custom_control_group"


class GroupMetadataKey(StrEnum):
    """Canonical keys used in control-group metadata maps."""

    FEATURE = "feature"
    ROLE = "role"
    CATEGORY = "category"
    AGGREGATE_DOMAIN = "aggregate_domain"
    AGGREGATE_DEVICE_CLASS = "aggregate_device_class"
    AGGREGATE_KIND = "aggregate_kind"


class GroupRole(StrEnum):
    """Canonical role labels used for metadata-based target selection."""

    PRIMARY = "primary"


class ControlGroupDefinitionView(Protocol):
    """Structural view of a control-group definition for runtime resolution."""

    @property
    def group_id(self) -> str:
        """Stable unique group identifier."""

    @property
    def policy_id(self) -> str | None:
        """Owning control policy id."""

    @property
    def members(self) -> tuple[str, ...]:
        """Ordered member entity IDs."""

    @property
    def metadata(self) -> Mapping[str, object]:
        """Typed metadata map used for runtime selectors."""


class RegisteredControlGroupView(Protocol):
    """Structural view of a registered control-group entry."""

    @property
    def definition(self) -> ControlGroupDefinitionView:
        """Stored group definition payload."""


class GroupRegistryView(Protocol):
    """Structural contract required by control-group runtime resolvers."""

    def get_for_area_policy(
        self, area_id: str, policy_id: str
    ) -> Sequence[RegisteredControlGroupView]:
        """Return all area groups for a policy."""

    def get_first_for_area_policy(
        self, area_id: str, policy_id: str
    ) -> RegisteredControlGroupView | None:
        """Return first area group for a policy when present."""


RESERVED_POLICY_IDS: frozenset[str] = frozenset(
    str(policy) for policy in ControlGroupPolicyId
)


def is_reserved_policy_id(policy_id: str) -> bool:
    """Return True when the policy ID is reserved by built-in control flows."""
    return policy_id in RESERVED_POLICY_IDS


__all__ = [
    "ControlGroupPolicyId",
    "GroupRegistryView",
    "GroupMetadataKey",
    "GroupRole",
    "RegisteredControlGroupView",
    "is_reserved_policy_id",
]
