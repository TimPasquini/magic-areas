"""Canonical group metadata keys and values."""

from __future__ import annotations

from enum import StrEnum


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
