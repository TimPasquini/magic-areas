"""Area-aware media player feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.config_keys import (
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
)
from custom_components.magic_areas.defaults import DEFAULT_NOTIFY_STATES
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_DEVICES, default=[]): cv.entity_ids,
        vol.Optional(CONF_NOTIFY_STATES, default=DEFAULT_NOTIFY_STATES): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)


class AreaAwareMediaPlayerFeatureModule(BaseFeatureModule):
    """Feature module for area-aware media player config."""

    id = MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    domains: set[str] = set()

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """No entities are built via registry for area-aware media player."""
        return []

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
                step_id="feature_conf_area_aware_media_player",
                schema=AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA,
            )
        ]


__all__ = ["AreaAwareMediaPlayerFeatureModule"]
