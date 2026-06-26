"""Presence hold feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import (
    PRESENCE_HOLD_OPTION_KEYS,
)
from custom_components.magic_areas.features.control_builders import (
    build_control_switch_entities,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)

PRESENCE_HOLD_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.PRESENCE_HOLD,
    keys_and_validators=((PRESENCE_HOLD_OPTION_KEYS[0], cv.positive_int),),
)


class PresenceHoldFeatureModule(BaseFeatureModule):
    """Feature module for presence hold."""

    id = MagicAreasFeatures.PRESENCE_HOLD
    domains = {SWITCH_DOMAIN}
    feature_schema = PRESENCE_HOLD_FEATURE_SCHEMA
    supports_meta_area = False
    supports_global_meta_area = False

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        _data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for presence hold."""
        return build_control_switch_entities(
            area_config=area_config,
            switch_factory=lambda: switch_platform.PresenceHoldSwitch(
                area_config, coordinator
            ),
            logger=_LOGGER,
            switch_label="presence hold switch",
        )


__all__ = ["PresenceHoldFeatureModule"]
