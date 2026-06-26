"""Tests for custom control-group schema guardrails."""

from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.magic_areas.schemas.control_groups import (
    CUSTOM_CONTROL_GROUPS_SCHEMA,
)


def test_custom_control_groups_schema_rejects_duplicate_group_ids() -> None:
    """Schema should reject duplicate group IDs in one payload."""
    with pytest.raises(vol.Invalid):
        CUSTOM_CONTROL_GROUPS_SCHEMA(
            [
                {
                    "group_id": "control.task",
                    "members": ["light.one"],
                },
                {
                    "group_id": "control.task",
                    "members": ["light.two"],
                },
            ]
        )


def test_custom_control_groups_schema_rejects_reserved_policy_id() -> None:
    """Schema should reject reserved built-in policy IDs for custom groups."""
    with pytest.raises(vol.Invalid):
        CUSTOM_CONTROL_GROUPS_SCHEMA(
            [
                {
                    "group_id": "control.task",
                    "members": ["light.one"],
                    "policy_id": "fan_groups",
                }
            ]
        )


def test_custom_control_groups_schema_accepts_default_custom_policy() -> None:
    """Schema should accept default custom-control-group policy ID."""
    payload = CUSTOM_CONTROL_GROUPS_SCHEMA(
        [
            {
                "group_id": "control.task",
                "members": ["light.one"],
                "policy_id": "custom_control_group",
                "metadata": {"role": "primary"},
            }
        ]
    )
    assert len(payload) == 1
