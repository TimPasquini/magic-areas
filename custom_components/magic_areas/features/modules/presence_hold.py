"""Presence hold feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.config_keys.features import (
    CONF_PRESENCE_HOLD_TIMEOUT,
)
from custom_components.magic_areas.core.feature_defaults import (
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)

PRESENCE_HOLD_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_PRESENCE_HOLD_TIMEOUT, default=DEFAULT_PRESENCE_HOLD_TIMEOUT
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)


class PresenceHoldFeatureModule(BaseFeatureModule):
    """Feature module for presence hold."""

    id = MagicAreasFeatures.PRESENCE_HOLD
    domains = {SWITCH_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return PRESENCE_HOLD_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.PRESENCE_HOLD in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for presence hold."""
        if area_config.is_meta():
            return []

        try:
            return [switch_platform.PresenceHoldSwitch(area_config, coordinator)]
        except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error loading presence hold switch: %s",
                area_config.name,
                str(exc),
            )
            return []

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.PRESENCE_HOLD,
                step_id="feature_conf_presence_hold",
                schema=PRESENCE_HOLD_FEATURE_SCHEMA,
            )
        ]


__all__ = ["PresenceHoldFeatureModule"]
