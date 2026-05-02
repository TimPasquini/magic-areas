"""Public API surface for aggregate selection/runtime contracts."""

from custom_components.magic_areas.core.aggregates.policy import (
    AggregateDefinition,
    AggregateKind,
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.core.aggregates.runtime import (
    aggregate_group_id,
    aggregate_managed_surface_unique_id,
    get_illuminance_threshold_spec,
    register_aggregate_definitions,
    resolve_aggregate_entity_id,
    resolve_aggregate_entity_ids_by_device_class,
)

__all__ = [
    "AggregateDefinition",
    "AggregateKind",
    "AggregatePolicyContext",
    "aggregate_group_id",
    "aggregate_managed_surface_unique_id",
    "build_default_aggregate_selection_policy",
    "get_illuminance_threshold_spec",
    "register_aggregate_definitions",
    "resolve_aggregate_entity_id",
    "resolve_aggregate_entity_ids_by_device_class",
]
