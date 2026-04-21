"""Config entry migration registry and handlers.

This module defines all config entry migrations across versions. Each migration
is explicit and documented, making it easy to understand what changed between
versions and to add new migrations without breaking existing ones.

Migration Application:
1. Version checks determine which migrations apply
2. Migrations run in order
3. Each migration updates the config entry independently
4. After all migrations, entry version is updated to current
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
)
from custom_components.magic_areas.core.runtime_model import async_migrate_unique_ids
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)

type MigrationHandler = Callable[
    [HomeAssistant, "MagicAreasConfigEntry"],
    Awaitable[None],
]


@dataclass(frozen=True, slots=True)
class ConfigMigration:
    """Defines a single config entry migration.

    Migrations are applied in order when a config entry version is older than
    the current version. Each migration is atomic and independent.
    """

    from_version: tuple[int, int]
    """Minimum version this migration applies to (major, minor)."""

    to_version: tuple[int, int]
    """Version this migration targets (major, minor)."""

    description: str
    """Human-readable description of what this migration does."""

    handler: MigrationHandler
    """Async function to apply the migration."""

    async def apply(
        self, hass: HomeAssistant, config_entry: MagicAreasConfigEntry
    ) -> None:
        """Apply this migration to a config entry.

        Args:
            hass: Home Assistant instance
            config_entry: Config entry to migrate

        """
        await self.handler(hass, config_entry)


async def _migrate_1_0_to_2_0(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Migrate from 1.x to 2.x: unique_id format change.

    Changes unique_id format from magic_areas_<feature>_<domain>_<area>_<extra>
    to <feature>_<area>_<extra> (removes domain prefix for stability).

    This migration maps legacy unique IDs to canonical feature/area IDs.
    """
    await async_migrate_unique_ids(hass, config_entry)


async def _migrate_2_2_to_2_3(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Backfill light-groups adaptive brightness keys into feature options."""
    options = dict(config_entry.options)
    enabled_features = options.get(CONF_ENABLED_FEATURES)
    if not isinstance(enabled_features, dict):
        return

    feature_key = MagicAreasFeatures.LIGHT_GROUPS.value
    light_cfg = enabled_features.get(feature_key)
    if not isinstance(light_cfg, dict):
        return

    changed = False
    if CONF_LIGHT_GROUP_BRIGHTNESS_MODE not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_BRIGHTNESS_MODE] = "inhibit"
        changed = True
    if CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS] = 0
        changed = True
    if CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS] = 0
        changed = True
    if CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE] = "sun"
        changed = True
    if CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY] = ""
        changed = True
    if CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN] = 0
        changed = True
    if CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS] = 0
        changed = True
    if CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY] = ""
        changed = True
    if CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA] = 0
        changed = True
    if CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT] = 0
        changed = True
    if CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE] = False
        changed = True
    if CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS] = 120
        changed = True
    if CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA not in light_cfg:
        light_cfg[CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA] = 20
        changed = True

    if not changed:
        return

    enabled_features[feature_key] = light_cfg
    options[CONF_ENABLED_FEATURES] = enabled_features
    hass.config_entries.async_update_entry(config_entry, options=options)


# Registry of all migrations in order
# These are applied sequentially when config entry version is outdated
CONFIG_MIGRATIONS: list[ConfigMigration] = [
    ConfigMigration(
        from_version=(1, 0),
        to_version=(2, 0),
        description="Migrate unique_id format to new stable IDs (remove domain prefix)",
        handler=_migrate_1_0_to_2_0,
    ),
    ConfigMigration(
        from_version=(2, 1),
        to_version=(2, 2),
        description="Backfill unique_id migration for entries created before 2.2",
        handler=_migrate_1_0_to_2_0,
    ),
    ConfigMigration(
        from_version=(2, 2),
        to_version=(2, 3),
        description="Backfill light-groups brightness mode, adaptive guards, and contrast options",
        handler=_migrate_2_2_to_2_3,
    ),
    # Future migrations follow this pattern:
    # ConfigMigration(
    #     from_version=(2, 0),
    #     to_version=(2, 1),
    #     description="Example: Rename feature flags",
    #     handler=_migrate_2_0_to_2_1,
    # ),
]


def get_applicable_migrations(
    from_version: tuple[int, int], to_version: tuple[int, int]
) -> list[ConfigMigration]:
    """Get all migrations that should be applied between versions.

    Args:
        from_version: Config entry's current version (major, minor)
        to_version: Target version (major, minor)

    Returns:
        List of migrations to apply in order.

    Example:
        >>> from_version = (1, 0)
        >>> to_version = (2, 2)
        >>> migrations = get_applicable_migrations(from_version, to_version)
        >>> # Returns migrations from 1.x → 2.x

    """
    applicable = []

    for migration in CONFIG_MIGRATIONS:
        # Skip if we're already at or past this migration's target
        if from_version >= migration.to_version:
            continue

        # Skip if we haven't reached this migration's starting point
        if to_version < migration.from_version:
            continue

        applicable.append(migration)

    return applicable


async def apply_applicable_migrations(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    *,
    from_version: tuple[int, int],
    to_version: tuple[int, int],
) -> int:
    """Apply all applicable migrations and return count applied."""
    applicable = get_applicable_migrations(from_version, to_version)

    for migration in applicable:
        _LOGGER.info(
            "Applying migration %s -> %s: %s",
            migration.from_version,
            migration.to_version,
            migration.description,
        )
        await migration.apply(hass, config_entry)

    return len(applicable)
