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
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.core import HomeAssistant

if False:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


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

    handler: Callable
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


# Placeholder migration handlers (actual migrations go here)
async def _migrate_1_0_to_2_0(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Migrate from 1.x to 2.x: unique_id format change.

    Changes unique_id format from magic_areas_<feature>_<domain>_<area>_<extra>
    to <feature>_<area>_<extra> (removes domain prefix for stability).

    This migration is handled in __init__.py's _async_migrate_unique_ids().
    """
    # Actual implementation is in __init__.py
    pass


# Registry of all migrations in order
# These are applied sequentially when config entry version is outdated
CONFIG_MIGRATIONS: list[ConfigMigration] = [
    ConfigMigration(
        from_version=(1, 0),
        to_version=(2, 0),
        description="Migrate unique_id format to new stable IDs (remove domain prefix)",
        handler=_migrate_1_0_to_2_0,
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
