"""Light groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_ENTITIES, CONF_NAME
from homeassistant.helpers.entity import Entity

import custom_components.magic_areas.switch as switch_platform
from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.control_intents import (
    ManagedAdaptiveLightingConfig,
    managed_adaptive_lighting_config,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ControlGroupPolicyId,
    GroupMetadataKey,
    LabelSurface,
    ManagedSurface,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_light_group_id,
)
from custom_components.magic_areas.enums import LightGroupCategory, MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigDict,
)
from custom_components.magic_areas.features.control_builders import (
    CategorizedGroupSpec,
    ControlGroupDefinition,
    build_categorized_group_entities,
    build_control_group_definition,
    build_control_switch_entities,
    register_area_default_groups,
)
from custom_components.magic_areas.light_groups import (
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE,
    LIGHT_GROUP_FEATURE_SCHEMA,
    LIGHT_GROUP_PRESETS,
    LIGHT_GROUP_ROLE_LABELS,
    AreaLightGroup,
    MagicLightGroup,
    adaptive_lighting_manage_all_lights,
    adaptive_lighting_managed_roles,
    adaptive_lighting_mode,
    ambient_rise_signal_surface,
    build_light_group_helper_surface_unique_id,
    light_groups_feature_config,
    preset_members,
    preset_states,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import (
        MagicAreasCoordinator,
        MagicAreasData,
    )
    from custom_components.magic_areas.core.runtime_model import AreaConfig

_LOGGER = logging.getLogger(__name__)
LIGHT_GROUPS_POLICY_ID = str(ControlGroupPolicyId.LIGHT_GROUPS)


class LightGroupsFeatureModule(BaseFeatureModule):
    """Feature module for light groups."""

    id = MagicAreasFeatures.LIGHT_GROUPS
    domains = {LIGHT_DOMAIN, SWITCH_DOMAIN}
    feature_schema = LIGHT_GROUP_FEATURE_SCHEMA
    configurable_on_meta = False
    configurable_on_global_meta = False

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the light groups feature."""
        light_entities = [e["entity_id"] for e in data.entities.get(LIGHT_DOMAIN, [])]
        feature_config = light_groups_feature_config(data.feature_configs)
        light_groups: list[Entity] = []
        registered_group_defs: list[ControlGroupDefinition] = []

        if LIGHT_DOMAIN not in data.entities:
            _LOGGER.debug(
                "%s: No %s entities for area.", area_config.name, LIGHT_DOMAIN
            )
        else:
            if area_config.is_meta():
                light_groups, registered_group_defs = self._build_meta_light_groups(
                    area_config=area_config,
                    coordinator=coordinator,
                    light_entities=light_entities,
                )
            else:
                light_groups, registered_group_defs = self._build_area_light_groups(
                    area_config=area_config,
                    coordinator=coordinator,
                    light_entities=light_entities,
                    feature_config=feature_config,
                )

        register_area_default_groups(
            area_id=area_config.id,
            definitions=registered_group_defs,
            policy_id=LIGHT_GROUPS_POLICY_ID,
            group_registry=data.group_registry,
        )

        light_groups.extend(
            build_control_switch_entities(
                area_config=area_config,
                switch_factory=lambda: switch_platform.LightControlSwitch(
                    area_config,
                    coordinator,
                ),
                logger=_LOGGER,
                switch_label="light group control switch",
            )
        )

        return light_groups

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Build desired native HA light group helper surfaces."""
        light_entities = [e["entity_id"] for e in data.entities.get(LIGHT_DOMAIN, [])]
        if not light_entities:
            return []

        feature_config = light_groups_feature_config(data.feature_configs)
        surfaces: list[ManagedSurface] = [
            _light_group_surface(
                area_config=area_config,
                category=LightGroupCategory.ALL,
                members=light_entities,
            )
        ]
        for preset in LIGHT_GROUP_PRESETS:
            members = preset_members(
                feature_config,
                preset,
                available_entities=light_entities,
            )
            surfaces.append(
                _light_group_role_label_surface(
                    category=preset.category,
                    members=members,
                    eligible_entities=light_entities,
                )
            )
            if not members:
                continue
            surfaces.append(
                _light_group_surface(
                    area_config=area_config,
                    category=preset.category,
                    members=members,
                )
            )
        ambient_rise_surface = ambient_rise_signal_surface(
            entry_id=area_config.hass_config.entry_id,
            area_id=area_config.id,
            area_name=area_config.name,
            feature_config=feature_config,
            device_identifier=(DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}"),
            device_name=area_config.name,
        )
        if ambient_rise_surface is not None:
            surfaces.append(ambient_rise_surface)
        return surfaces

    def desired_managed_adaptive_lighting_configs(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedAdaptiveLightingConfig]:
        """Build desired MA-managed Adaptive Lighting configs for selected roles."""
        light_entities = [e["entity_id"] for e in data.entities.get(LIGHT_DOMAIN, [])]
        if not light_entities:
            return []

        feature_config = light_groups_feature_config(data.feature_configs)
        if (
            adaptive_lighting_mode(feature_config)
            != LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_MANAGE
        ):
            return []

        configs: list[ManagedAdaptiveLightingConfig] = []
        managed_roles = set(adaptive_lighting_managed_roles(feature_config))
        if adaptive_lighting_manage_all_lights(feature_config):
            config = managed_adaptive_lighting_config(
                area_id=area_config.id,
                area_name=area_config.name,
                role=str(LightGroupCategory.ALL),
                light_entity_ids=light_entities,
            )
            if config is not None:
                configs.append(config)
        for preset in LIGHT_GROUP_PRESETS:
            if preset.category not in managed_roles:
                continue
            members = preset_members(
                feature_config,
                preset,
                available_entities=light_entities,
            )
            config = managed_adaptive_lighting_config(
                area_id=area_config.id,
                area_name=area_config.name,
                role=preset.category,
                light_entity_ids=members,
            )
            if config is not None:
                configs.append(config)
        return configs

    def _build_meta_light_groups(
        self,
        *,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        light_entities: list[str],
    ) -> tuple[list[Entity], list[ControlGroupDefinition]]:
        groups: list[Entity] = [
            MagicLightGroup(
                area_config,
                coordinator,
                light_entities,
                translation_key=LightGroupCategory.ALL,
            )
        ]
        definitions = [
            build_control_group_definition(
                group_id=build_light_group_id(
                    area_id=area_config.id, category=LightGroupCategory.ALL
                ),
                members=light_entities,
                trigger_states=(),
                policy_id=LIGHT_GROUPS_POLICY_ID,
                feature_id=MagicAreasFeatures.LIGHT_GROUPS,
                role=None,
                metadata={GroupMetadataKey.CATEGORY: LightGroupCategory.ALL},
            )
        ]
        return groups, definitions

    def _build_area_light_groups(
        self,
        *,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        light_entities: list[str],
        feature_config: FeatureConfigDict,
    ) -> tuple[list[Entity], list[ControlGroupDefinition]]:
        def _build_category_entity(spec: CategorizedGroupSpec) -> Entity:
            return AreaLightGroup(
                area_config,
                coordinator,
                spec.members,
                spec.category,
                feature_config=feature_config,
            )

        def _build_parent_entity(
            _parent_members: list[str], child_categories: list[str]
        ) -> Entity:
            return AreaLightGroup(
                area_config,
                coordinator,
                light_entities,
                category=LightGroupCategory.ALL,
                child_categories=child_categories,
                feature_config=feature_config,
            )

        specs = [
            CategorizedGroupSpec(
                category=preset.category,
                members=preset_members(
                    feature_config,
                    preset,
                    available_entities=light_entities,
                ),
                trigger_states=tuple(preset_states(feature_config, preset)),
            )
            for preset in LIGHT_GROUP_PRESETS
        ]

        groups, definitions, child_categories = build_categorized_group_entities(
            specs=specs,
            category_entity_factory=_build_category_entity,
            category_definition_factory=lambda spec: build_control_group_definition(
                group_id=build_light_group_id(
                    area_id=area_config.id,
                    category=spec.category,
                ),
                members=spec.members,
                trigger_states=spec.trigger_states,
                policy_id=LIGHT_GROUPS_POLICY_ID,
                feature_id=MagicAreasFeatures.LIGHT_GROUPS,
                role=None,
                metadata={GroupMetadataKey.CATEGORY: spec.category},
            ),
            parent_entity_factory=_build_parent_entity,
            parent_definition_factory=lambda _parent_members,
            _child_categories: build_control_group_definition(
                group_id=build_light_group_id(
                    area_id=area_config.id, category=LightGroupCategory.ALL
                ),
                members=light_entities,
                trigger_states=(),
                policy_id=LIGHT_GROUPS_POLICY_ID,
                feature_id=MagicAreasFeatures.LIGHT_GROUPS,
                role=None,
                metadata={GroupMetadataKey.CATEGORY: LightGroupCategory.ALL},
            ),
            logger=_LOGGER,
            group_label="light",
        )

        return groups, definitions


def _light_group_surface_unique_id(
    *,
    area_config: AreaConfig,
    category: str,
) -> str:
    """Return managed helper unique ID for a light role group."""
    return build_light_group_helper_surface_unique_id(
        entry_id=area_config.hass_config.entry_id,
        area_id=area_config.id,
        category=category,
    )


def _light_group_role_label_surface(
    *,
    category: str,
    members: list[str],
    eligible_entities: list[str],
) -> LabelSurface:
    """Build the global HA label surface for one light role."""
    return LabelSurface(
        name=LIGHT_GROUP_ROLE_LABELS[category],
        entity_ids=tuple(members),
        prune_entity_ids=tuple(eligible_entities),
        icon="mdi:label",
        description=f"Magic Areas light role: {str(category).replace('_lights', '')}",
    )


def _light_group_surface(
    *,
    area_config: AreaConfig,
    category: str,
    members: list[str],
) -> ConfigEntryHelperSurface:
    """Build one native HA light group helper surface."""
    role_label = str(category).replace("_", " ").title()
    title = (
        f"Magic Areas Native Light Groups {area_config.name} "
        f"{role_label}"
    )
    return ConfigEntryHelperSurface(
        unique_id=_light_group_surface_unique_id(
            area_config=area_config,
            category=category,
        ),
        domain="group",
        title=title,
        options={
            "group_type": LIGHT_DOMAIN,
            CONF_NAME: title,
            CONF_ENTITIES: members,
            "hide_members": False,
        },
        area_id=area_config.id,
        device_identifier=(DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}"),
        device_name=area_config.name,
        entity_name=role_label,
    )


__all__ = ["LightGroupsFeatureModule"]
