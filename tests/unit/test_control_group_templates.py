"""Tests for starter custom control-group templates."""

from custom_components.magic_areas.core.control_group_templates import (
    get_custom_control_group_templates,
)


def test_get_custom_control_group_templates_returns_expected_groups() -> None:
    """Template helper should provide task/reading/media starter groups."""
    templates = get_custom_control_group_templates()
    group_ids = {group["group_id"] for group in templates}

    assert group_ids == {"control.task", "control.reading", "control.media"}


def test_get_custom_control_group_templates_returns_copy() -> None:
    """Template helper should return a copy to avoid shared mutations."""
    templates = get_custom_control_group_templates()
    templates[0]["group_id"] = "control.mutated"

    fresh = get_custom_control_group_templates()
    assert fresh[0]["group_id"] == "control.task"
