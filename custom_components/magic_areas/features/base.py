"""Feature module base interface for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

import voluptuous as vol
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.option_defaults import feature_option_default

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.core.runtime_model import (
        ManagedSurface,
    )
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

type FeatureConfigValue = object
type FeatureOptionValidator = object


@dataclass(frozen=True)
class FeatureConfigStep:
    """Declarative feature config step for options flow."""

    feature: MagicAreasFeatures
    step_id: str
    schema: vol.Schema | None = None
    merge_options: bool = False
    next_step: str | None = None


_MISSING = object()


@dataclass(frozen=True)
class FeatureOption:
    """Declarative option definition for feature schemas."""

    key: str
    validator: FeatureOptionValidator
    default: FeatureConfigValue = _MISSING


def default_feature_option(
    *,
    feature: MagicAreasFeatures,
    key: str,
    validator: FeatureOptionValidator,
) -> FeatureOption:
    """Build a feature option with default sourced from option definitions."""
    return FeatureOption(
        key=key,
        validator=validator,
        default=feature_option_default(feature, key),
    )


def default_feature_options(
    *,
    feature: MagicAreasFeatures,
    keys: Sequence[str],
    validator: FeatureOptionValidator,
) -> list[FeatureOption]:
    """Build multiple feature options sharing one validator."""
    return [
        default_feature_option(feature=feature, key=key, validator=validator)
        for key in keys
    ]


def schema_from_default_options(
    *,
    feature: MagicAreasFeatures,
    keys_and_validators: Sequence[tuple[str, FeatureOptionValidator]],
    required_keys: set[str] | None = None,
    include_keys: set[str] | None = None,
) -> vol.Schema:
    """Build a schema directly from defaulted feature options."""
    return schema_from_options(
        options=[
            default_feature_option(feature=feature, key=key, validator=validator)
            for key, validator in keys_and_validators
        ],
        required_keys=required_keys,
        include_keys=include_keys,
    )


def schema_from_options(
    *,
    options: list[FeatureOption],
    required_keys: set[str] | None = None,
    include_keys: set[str] | None = None,
) -> vol.Schema:
    """Build a voluptuous schema from declarative option definitions."""
    required = required_keys or set()
    include = include_keys or {option.key for option in options}

    schema_map: dict[object, object] = {}
    for option in options:
        if option.key not in include:
            continue
        marker: object
        if option.key in required:
            marker = vol.Required(option.key)
        elif option.default is _MISSING:
            marker = vol.Optional(option.key)
        else:
            marker = vol.Optional(option.key, default=option.default)
        schema_map[marker] = option.validator
    return vol.Schema(schema_map, extra=vol.REMOVE_EXTRA)


class FeatureModule(Protocol):
    """Defines the lifecycle contract for a Magic Areas feature."""

    id: MagicAreasFeatures
    domains: set[str]
    supports_regular_area: bool
    supports_meta_area: bool
    supports_global_meta_area: bool
    configurable_on_meta: bool
    configurable_on_global_meta: bool

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
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

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Return HA-managed surfaces desired by this feature."""
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
    feature_schema: vol.Schema | None = None
    feature_config_step_schema: vol.Schema | None = None
    feature_step_id: str | None = None
    feature_merge_options: bool = False
    feature_next_step: str | None = None
    supports_regular_area: bool = True
    supports_meta_area: bool = True
    supports_global_meta_area: bool = True
    configurable_on_meta: bool = True
    configurable_on_global_meta: bool = True

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return self.feature_schema

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return self.id in data.enabled_features

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

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Return HA-managed surfaces desired by this feature."""
        return []

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        schema = self.feature_config_step_schema or self.feature_schema
        if not schema:
            return []
        return [
            FeatureConfigStep(
                feature=self.id,
                step_id=self.feature_step_id or f"feature_conf_{self.id}",
                schema=schema,
                merge_options=self.feature_merge_options,
                next_step=self.feature_next_step,
            )
        ]
