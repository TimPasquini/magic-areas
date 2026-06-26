"""Unit tests for core.group_registry."""

from custom_components.magic_areas.core.controls import ControlGroupDefinition
from custom_components.magic_areas.core.controls import GroupRegistry


def test_returns_defaults_for_area() -> None:
    """Areas should receive globally-registered default groups."""
    registry = GroupRegistry()
    registry.register_default(
        ControlGroupDefinition(group_id="light.overhead", members=("light.one",))
    )

    groups = registry.get_for_area("kitchen")

    assert len(groups) == 1
    assert groups[0].definition.group_id == "light.overhead"
    assert groups[0].is_custom is False


def test_custom_group_overrides_default_for_same_id() -> None:
    """Area custom groups should override defaults with matching group IDs."""
    registry = GroupRegistry()
    registry.register_default(
        ControlGroupDefinition(
            group_id="control.task",
            members=("light.default",),
            trigger_states=("occupied",),
        )
    )
    registry.register_custom(
        "office",
        ControlGroupDefinition(
            group_id="control.task",
            members=("light.office", "switch.soldering_iron"),
            trigger_states=("occupied", "focused"),
        ),
    )

    office_groups = registry.get_for_area("office")
    kitchen_groups = registry.get_for_area("kitchen")

    office_task = next(
        g for g in office_groups if g.definition.group_id == "control.task"
    )
    kitchen_task = next(
        g for g in kitchen_groups if g.definition.group_id == "control.task"
    )

    assert office_task.definition.members == ("light.office", "switch.soldering_iron")
    assert office_task.is_custom is True
    assert kitchen_task.definition.members == ("light.default",)
    assert kitchen_task.is_custom is False


def test_area_specific_groups_do_not_leak() -> None:
    """Custom groups should only apply to their registered area."""
    registry = GroupRegistry()
    registry.register_custom(
        "bathroom",
        ControlGroupDefinition(group_id="control.vent", members=("fan.bathroom",)),
    )

    bathroom_groups = registry.get_for_area("bathroom")
    bedroom_groups = registry.get_for_area("bedroom")

    assert any(group.definition.group_id == "control.vent" for group in bathroom_groups)
    assert all(group.definition.group_id != "control.vent" for group in bedroom_groups)


def test_area_default_groups_are_scoped_to_area() -> None:
    """Area defaults should not appear in unrelated areas."""
    registry = GroupRegistry()
    registry.register_area_default(
        "office",
        ControlGroupDefinition(group_id="light.task", members=("light.office_task",)),
    )

    office_groups = registry.get_for_area("office")
    kitchen_groups = registry.get_for_area("kitchen")

    assert any(group.definition.group_id == "light.task" for group in office_groups)
    assert all(group.definition.group_id != "light.task" for group in kitchen_groups)


def test_register_area_defaults_replaces_prior_policy_defaults() -> None:
    """register_area_defaults should replace previous non-custom entries for a policy."""
    registry = GroupRegistry()
    registry.register_area_default(
        "office",
        ControlGroupDefinition(
            group_id="light_groups_office_sleep",
            members=("light.sleep",),
            policy_id="light_groups",
        ),
    )
    registry.register_area_default(
        "office",
        ControlGroupDefinition(
            group_id="fan_groups_office_fan_group",
            members=("fan.office",),
            policy_id="fan_groups",
        ),
    )

    registry.register_area_defaults(
        "office",
        [
            ControlGroupDefinition(
                group_id="light_groups_office_overhead",
                members=("light.overhead",),
                policy_id="light_groups",
            )
        ],
        policy_id="light_groups",
    )

    office_groups = registry.get_for_area("office")
    office_group_ids = {group.definition.group_id for group in office_groups}
    assert "light_groups_office_sleep" not in office_group_ids
    assert "light_groups_office_overhead" in office_group_ids
    assert "fan_groups_office_fan_group" in office_group_ids


def test_register_area_defaults_keeps_custom_entries() -> None:
    """register_area_defaults must not remove area custom entries."""
    registry = GroupRegistry()
    registry.register_custom(
        "office",
        ControlGroupDefinition(
            group_id="control.task",
            members=("light.task",),
            policy_id="custom_groups",
        ),
    )

    registry.register_area_defaults(
        "office",
        [
            ControlGroupDefinition(
                group_id="light_groups_office_overhead",
                members=("light.overhead",),
                policy_id="light_groups",
            )
        ],
        policy_id="light_groups",
    )

    office_groups = registry.get_for_area("office")
    office_group_ids = {group.definition.group_id for group in office_groups}
    assert "control.task" in office_group_ids
    assert "light_groups_office_overhead" in office_group_ids


def test_get_first_for_area_policy_returns_match() -> None:
    """Policy filtered lookup should return the first matching entry."""
    registry = GroupRegistry()
    registry.register_area_default(
        "office",
        ControlGroupDefinition(
            group_id="fan_groups_office_fan_group",
            members=("fan.office",),
            policy_id="fan_groups",
        ),
    )

    match = registry.get_first_for_area_policy("office", "fan_groups")
    missing = registry.get_first_for_area_policy("office", "media_player_groups")

    assert match is not None
    assert match.definition.group_id == "fan_groups_office_fan_group"
    assert missing is None


def test_get_first_for_area_policy_is_deterministic() -> None:
    """Policy-filtered lookup should be deterministic across insertion order."""
    registry = GroupRegistry()
    registry.register_area_default(
        "office",
        ControlGroupDefinition(
            group_id="fan_groups_office_zeta",
            members=("fan.zeta",),
            policy_id="fan_groups",
        ),
    )
    registry.register_area_default(
        "office",
        ControlGroupDefinition(
            group_id="fan_groups_office_alpha",
            members=("fan.alpha",),
            policy_id="fan_groups",
        ),
    )

    match = registry.get_first_for_area_policy("office", "fan_groups")

    assert match is not None
    assert match.definition.group_id == "fan_groups_office_alpha"


def test_register_area_customs_replaces_prior_custom_groups() -> None:
    """register_area_customs should replace existing area custom entries."""
    registry = GroupRegistry()
    registry.register_custom(
        "office",
        ControlGroupDefinition(
            group_id="control.task",
            members=("light.task",),
            policy_id="custom_groups",
        ),
    )
    registry.register_custom(
        "office",
        ControlGroupDefinition(
            group_id="control.media",
            members=("media_player.tv",),
            policy_id="custom_groups",
        ),
    )

    registry.register_area_customs(
        "office",
        [
            ControlGroupDefinition(
                group_id="control.work",
                members=("light.desk", "switch.monitor"),
                policy_id="custom_groups",
            )
        ],
    )

    group_ids = {group.definition.group_id for group in registry.get_for_area("office")}
    assert "control.task" not in group_ids
    assert "control.media" not in group_ids
    assert "control.work" in group_ids
