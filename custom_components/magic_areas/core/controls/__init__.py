"""Public API for shared control-group contracts, execution, and runtime helpers."""

from custom_components.magic_areas.core.controls.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    evaluate_and_execute_control_group_policy,
    evaluate_and_execute_control_group_policy_sync,
    execute_control_group_decision,
    execute_control_group_runtime_effects,
    ControlGroupDecision,
    ControlGroupDefinition,
    ControlGroupPolicy,
    ControlRuntimeEffect,
    ControlRuntimeEffectType,
    build_noop_decision,
    get_custom_control_group_templates,
)
from custom_components.magic_areas.core.controls.control_group_runtime import (
    read_area_presence_states,
    register_area_and_group_state_listeners,
    resolve_area_presence_states,
    resolve_group_entity_id,
    resolve_group_entity_id_by_metadata,
    resolve_group_entity_ids_by_metadata,
    resolve_group_entity_ids_for_metadata_values,
    resolve_group_member_entity_id,
    resolve_group_member_entity_id_by_metadata,
)
from custom_components.magic_areas.core.controls.registry import (
    GroupRegistry,
    RegisteredControlGroup,
)
from custom_components.magic_areas.core.controls.runtime_support import (
    MonotonicDeadlineMap,
)
from custom_components.magic_areas.core.controls.builders import (
    CategorizedGroupSpec,
    build_categorized_group_entities,
    build_control_switch_entities,
    register_area_default_groups,
)

__all__ = [
    "CategorizedGroupSpec",
    "ControlAction",
    "ControlActionType",
    "ControlGroupContext",
    "ControlGroupDecision",
    "ControlGroupDefinition",
    "ControlGroupPolicy",
    "ControlRuntimeEffect",
    "ControlRuntimeEffectType",
    "GroupRegistry",
    "MonotonicDeadlineMap",
    "RegisteredControlGroup",
    "build_noop_decision",
    "build_categorized_group_entities",
    "build_control_switch_entities",
    "evaluate_and_execute_control_group_policy",
    "evaluate_and_execute_control_group_policy_sync",
    "execute_control_group_decision",
    "execute_control_group_runtime_effects",
    "get_custom_control_group_templates",
    "read_area_presence_states",
    "register_area_default_groups",
    "register_area_and_group_state_listeners",
    "resolve_area_presence_states",
    "resolve_group_entity_id",
    "resolve_group_entity_id_by_metadata",
    "resolve_group_entity_ids_by_metadata",
    "resolve_group_entity_ids_for_metadata_values",
    "resolve_group_member_entity_id",
    "resolve_group_member_entity_id_by_metadata",
]
