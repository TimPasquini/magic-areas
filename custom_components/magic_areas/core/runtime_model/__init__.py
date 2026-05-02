"""Runtime model API surface for area/group/identity contracts."""

from custom_components.magic_areas.core.runtime_model.area import (
    AreaConfig,
    AreaDescriptor,
    AreaRuntime,
)
from custom_components.magic_areas.core.runtime_model.groups import (
    ControlGroupDefinitionView,
    ControlGroupPolicyId,
    GroupRegistryView,
    GroupMetadataKey,
    GroupRole,
    RegisteredControlGroupView,
    is_reserved_policy_id,
)
from custom_components.magic_areas.core.runtime_model.identity import (
    build_feature_unique_id,
    build_presence_tracking_unique_id,
)
from custom_components.magic_areas.core.runtime_model.managed_surfaces import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceKind,
    ManagedSurfaceOptionValue,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.core.runtime_model.migration import (
    async_migrate_unique_ids,
    compute_unique_id_from_entity_id,
)
from custom_components.magic_areas.core.runtime_model.references import (
    EntityReferences,
    build_entity_references,
)

__all__ = [
    "AreaConfig",
    "AreaDescriptor",
    "AreaRuntime",
    "ControlGroupDefinitionView",
    "ControlGroupPolicyId",
    "ConfigEntryHelperSurface",
    "EntityReferences",
    "GroupMetadataKey",
    "GroupRegistryView",
    "GroupRole",
    "ManagedSurface",
    "ManagedSurfaceKind",
    "ManagedSurfaceOptionValue",
    "RegisteredControlGroupView",
    "async_migrate_unique_ids",
    "build_managed_surface_unique_id",
    "compute_unique_id_from_entity_id",
    "build_entity_references",
    "build_feature_unique_id",
    "build_presence_tracking_unique_id",
    "is_reserved_policy_id",
]
