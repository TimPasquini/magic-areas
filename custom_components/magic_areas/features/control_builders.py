"""Feature-local adapter for control-group builders and contracts."""

import custom_components.magic_areas.core.controls.builders as _builders
from custom_components.magic_areas.core.controls import (
    ControlGroupDefinition,
)
from custom_components.magic_areas.core.controls.fan_signals import (
    fan_controller_trend_signal_surface,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    build_fan_control_group_policy,
)

CategorizedGroupSpec = _builders.CategorizedGroupSpec
build_categorized_group_entities = _builders.build_categorized_group_entities
build_control_group_definition = _builders.build_control_group_definition
build_control_switch_entities = _builders.build_control_switch_entities
build_partitioned_group_entities = _builders.build_partitioned_group_entities
build_primary_group_entities = _builders.build_primary_group_entities
register_area_default_groups = _builders.register_area_default_groups

__all__ = [
    "CategorizedGroupSpec",
    "ControlGroupDefinition",
    "build_categorized_group_entities",
    "build_control_group_definition",
    "build_control_switch_entities",
    "build_partitioned_group_entities",
    "build_primary_group_entities",
    "build_fan_control_group_policy",
    "fan_controller_trend_signal_surface",
    "register_area_default_groups",
]
