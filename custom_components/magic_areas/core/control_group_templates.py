"""Starter templates for custom control groups."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_CUSTOM_CONTROL_GROUP_TEMPLATES: list[dict[str, Any]] = [
    {
        "group_id": "control.task",
        "members": [],
        "trigger_states": ["occupied"],
        "policy_id": "custom_control_group",
        "metadata": {"label": "Task"},
    },
    {
        "group_id": "control.reading",
        "members": [],
        "trigger_states": ["occupied"],
        "policy_id": "custom_control_group",
        "metadata": {"label": "Reading"},
    },
    {
        "group_id": "control.media",
        "members": [],
        "trigger_states": ["occupied"],
        "policy_id": "custom_control_group",
        "metadata": {"label": "Media"},
    },
]


def get_custom_control_group_templates() -> list[dict[str, Any]]:
    """Return a deep-copied list of starter control-group templates."""
    return deepcopy(_CUSTOM_CONTROL_GROUP_TEMPLATES)
