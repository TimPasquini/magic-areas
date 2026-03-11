"""Feature module base interface for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import voluptuous as vol
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


@dataclass(frozen=True)
class FeatureConfigStep:
    """Declarative feature config step for options flow."""

    feature: MagicAreasFeatures
    step_id: str
    schema: vol.Schema | None = None
    merge_options: bool = False
    next_step: str | None = None


class FeatureModule(Protocol):
    """Defines the lifecycle contract for a Magic Areas feature."""

    id: MagicAreasFeatures
    domains: set[str]

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        ...

    def option_steps(self) -> list[str]:
        """Return option step identifiers for this feature."""
        ...

    def validate_config(self, config: dict) -> dict:
        """Validate and normalize config for this feature."""
        ...

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        ...

    def depends_on(self) -> set[MagicAreasFeatures]:
        """Return feature dependencies required for this module."""
        ...

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for this feature."""
        ...

    def attach_listeners(
        self,
        entities: list[Entity],
        data: MagicAreasData,
    ) -> None:
        """Attach optional listeners for this feature."""
        ...

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        ...


class BaseFeatureModule:
    """Base class with default FeatureModule behavior."""

    id: MagicAreasFeatures
    domains: set[str]

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return None

    def option_steps(self) -> list[str]:
        """Return option step identifiers for this feature."""
        return []

    def validate_config(self, config: dict) -> dict:
        """Validate and normalize config for this feature."""
        return config

    def depends_on(self) -> set[MagicAreasFeatures]:
        """Return feature dependencies required for this module."""
        return set()

    def attach_listeners(
        self,
        entities: list[Entity],
        data: MagicAreasData,
    ) -> None:
        """Attach optional listeners for this feature."""
        return None

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return []
