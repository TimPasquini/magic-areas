"""Unit tests for shared feature-module group helper builders."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.magic_areas.core.controls import ControlGroupDefinition
from custom_components.magic_areas.core.controls.builders import (
    CategorizedGroupSpec,
    build_categorized_group_entities,
)


def test_build_categorized_group_entities_builds_children_and_parent() -> None:
    """Builder should create category entities/definitions and one parent group."""
    specs = [
        CategorizedGroupSpec(
            category="overhead",
            members=["light.kitchen_overhead"],
            trigger_states=("occupied",),
        ),
        CategorizedGroupSpec(category="task", members=[], trigger_states=("occupied",)),
        CategorizedGroupSpec(
            category="accent",
            members=["light.kitchen_accent"],
            trigger_states=("dark",),
        ),
    ]

    entities, definitions, child_categories = build_categorized_group_entities(
        specs=specs,
        category_entity_factory=lambda spec: f"entity:{spec.category}",
        category_definition_factory=lambda spec: ControlGroupDefinition(
            group_id=f"group.{spec.category}",
            members=tuple(spec.members),
            trigger_states=spec.trigger_states,
            policy_id="light_groups",
            metadata={},
        ),
        parent_entity_factory=lambda parent_members, child_categories: (
            f"entity:all:{','.join(sorted(parent_members))}:{','.join(child_categories)}"
        ),
        parent_definition_factory=lambda parent_members, _child_categories: (
            ControlGroupDefinition(
                group_id="group.all",
                members=tuple(parent_members),
                trigger_states=(),
                policy_id="light_groups",
                metadata={},
            )
        ),
        logger=MagicMock(),
        group_label="light",
    )

    assert child_categories == ["overhead", "accent"]
    assert entities[0] == "entity:overhead"
    assert entities[1] == "entity:accent"
    assert entities[2] == (
        "entity:all:light.kitchen_accent,light.kitchen_overhead:overhead,accent"
    )
    assert [definition.group_id for definition in definitions] == [
        "group.overhead",
        "group.accent",
        "group.all",
    ]


def test_build_categorized_group_entities_logs_and_continues_on_child_error() -> None:
    """Builder should continue constructing remaining groups after child errors."""
    logger = MagicMock()
    specs = [
        CategorizedGroupSpec(category="bad", members=["light.bad"]),
        CategorizedGroupSpec(category="good", members=["light.good"]),
    ]

    def _child_factory(spec: CategorizedGroupSpec) -> str:
        if spec.category == "bad":
            msg = "boom"
            raise RuntimeError(msg)
        return f"entity:{spec.category}"

    entities, definitions, child_categories = build_categorized_group_entities(
        specs=specs,
        category_entity_factory=_child_factory,
        category_definition_factory=lambda spec: ControlGroupDefinition(
            group_id=f"group.{spec.category}",
            members=tuple(spec.members),
            trigger_states=(),
            policy_id="light_groups",
            metadata={},
        ),
        parent_entity_factory=lambda parent_members, _child_categories: (
            f"entity:all:{','.join(parent_members)}"
        ),
        parent_definition_factory=lambda parent_members, _child_categories: (
            ControlGroupDefinition(
                group_id="group.all",
                members=tuple(parent_members),
                trigger_states=(),
                policy_id="light_groups",
                metadata={},
            )
        ),
        logger=logger,
        group_label="light",
    )

    assert child_categories == ["good"]
    assert entities == ["entity:good", "entity:all:light.good"]
    assert [definition.group_id for definition in definitions] == ["group.good", "group.all"]
    logger.exception.assert_called_once()
