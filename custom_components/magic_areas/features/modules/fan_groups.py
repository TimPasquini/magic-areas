"""Fan groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.config_keys import (
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
)
from custom_components.magic_areas.core.control_group import ControlGroupDefinition
from custom_components.magic_areas.core.group_registry import GROUP_REGISTRY
from custom_components.magic_areas.defaults import (
    DEFAULT_FAN_GROUPS_REQUIRED_STATE,
    DEFAULT_FAN_GROUPS_SETPOINT,
    DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
from custom_components.magic_areas.fan_group_entities import AreaFanGroup
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)

FAN_GROUP_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_FAN_GROUPS_REQUIRED_STATE, default=DEFAULT_FAN_GROUPS_REQUIRED_STATE
        ): str,
        vol.Optional(
            CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
            default=DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
        ): str,
        vol.Optional(
            CONF_FAN_GROUPS_SETPOINT, default=DEFAULT_FAN_GROUPS_SETPOINT
        ): float,
    },
    extra=vol.REMOVE_EXTRA,
)


class FanGroupsFeatureModule(BaseFeatureModule):
    """Feature module for fan groups."""

    id = MagicAreasFeatures.FAN_GROUPS
    domains = {FAN_DOMAIN, SWITCH_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return FAN_GROUP_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.FAN_GROUPS in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the fan groups feature."""
        entities: list[Entity] = []
        group_definitions: list[ControlGroupDefinition] = []

        if FAN_DOMAIN not in data.entities:
            _LOGGER.debug("%s: No %s entities for area.", area_config.name, FAN_DOMAIN)
        else:
            fan_entities = [e["entity_id"] for e in data.entities[FAN_DOMAIN]]
            if fan_entities:
                try:
                    entities.append(AreaFanGroup(area_config, coordinator, fan_entities))
                    group_definitions.append(
                        ControlGroupDefinition(
                            group_id=f"fan_groups_{area_config.id}_fan_group",
                            members=tuple(fan_entities),
                            trigger_states=(
                                str(
                                    data.feature_configs.get(
                                        MagicAreasFeatures.FAN_GROUPS, {}
                                    ).get(
                                        CONF_FAN_GROUPS_REQUIRED_STATE,
                                        DEFAULT_FAN_GROUPS_REQUIRED_STATE,
                                    )
                                ),
                            ),
                            policy_id="fan_groups",
                            metadata={"feature": str(MagicAreasFeatures.FAN_GROUPS)},
                        )
                    )
                except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
                    _LOGGER.error(
                        "%s: Error creating fan group: %s",
                        area_config.slug,
                        str(exc),
                    )

        GROUP_REGISTRY.register_area_defaults(
            area_id=area_config.id,
            definitions=group_definitions,
            policy_id="fan_groups",
        )

        if not area_config.is_meta():
            try:
                entities.append(
                    switch_platform.FanControlSwitch(area_config, coordinator)
                )
            except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    "%s: Error loading fan control switch: %s",
                    area_config.name,
                    str(exc),
                )

        return entities

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.FAN_GROUPS,
                step_id="feature_conf_fan_groups",
                schema=FAN_GROUP_FEATURE_SCHEMA,
            )
        ]


__all__ = ["FanGroupsFeatureModule"]
