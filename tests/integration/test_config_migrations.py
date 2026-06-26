"""Tests for config entry migrations across versions.

This module tests backward compatibility by verifying that config entries
from older versions can be loaded and upgraded to current versions without
data loss or errors.
"""

from unittest.mock import AsyncMock, patch

from custom_components.magic_areas.enums import MagicConfigEntryVersion
from custom_components.magic_areas.migrations import (
    CONFIG_MIGRATIONS,
    ConfigMigration,
    apply_applicable_migrations,
    get_applicable_migrations,
)


class TestMigrationRegistry:
    """Test migration registry structure and logic."""

    def test_migrations_are_ordered(self) -> None:
        """Migrations should be in ascending version order."""
        for i in range(len(CONFIG_MIGRATIONS) - 1):
            current = CONFIG_MIGRATIONS[i]
            next_migration = CONFIG_MIGRATIONS[i + 1]

            # Each migration's target should be <= next migration's source
            assert current.to_version <= next_migration.from_version

    def test_migrations_have_descriptions(self) -> None:
        """All migrations should document their purpose."""
        for migration in CONFIG_MIGRATIONS:
            assert migration.description
            assert len(migration.description) > 10  # Meaningful description

    def test_applicable_migrations_logic(self) -> None:
        """get_applicable_migrations should return correct set."""
        # No migrations from 2.2 to 2.2 (current)
        current = (
            MagicConfigEntryVersion.MAJOR,
            MagicConfigEntryVersion.MINOR,
        )
        migrations = get_applicable_migrations(current, current)
        assert len(migrations) == 0

        # If we had migrations 1.0→2.0, 2.0→2.1, 2.1→2.2:
        # From 1.0 to 2.2 should get all three
        if len(CONFIG_MIGRATIONS) >= 1:
            from_version = CONFIG_MIGRATIONS[0].from_version
            to_version = current
            migrations = get_applicable_migrations(from_version, to_version)
            assert len(migrations) > 0

    async def test_apply_applicable_migrations_executes_in_order(self) -> None:
        """Applicable migrations should execute once each in registry order."""
        calls: list[str] = []

        async def _handler_1(hass: object, config_entry: object) -> None:
            del hass, config_entry
            calls.append("1")

        async def _handler_2(hass: object, config_entry: object) -> None:
            del hass, config_entry
            calls.append("2")

        mock_entry = AsyncMock()
        mock_hass = AsyncMock()

        with patch(
            "custom_components.magic_areas.migrations.CONFIG_MIGRATIONS",
            [
                ConfigMigration(
                    from_version=(1, 0),
                    to_version=(2, 0),
                    description="first",
                    handler=_handler_1,
                ),
                ConfigMigration(
                    from_version=(2, 0),
                    to_version=(2, 2),
                    description="second",
                    handler=_handler_2,
                ),
            ],
        ):
            applied = await apply_applicable_migrations(
                mock_hass,
                mock_entry,
                from_version=(1, 0),
                to_version=(2, 2),
            )

        assert applied == 2
        assert calls == ["1", "2"]


class TestOldConfigLoading:
    """Test loading old config entry formats."""

    def test_old_version_requires_migration(self) -> None:
        """Config entries from v1.0 should be identified as needing migration."""
        old_version = (1, 0)
        current = (
            MagicConfigEntryVersion.MAJOR,
            MagicConfigEntryVersion.MINOR,
        )

        # Should have migrations to apply
        migrations = get_applicable_migrations(old_version, current)
        assert len(migrations) > 0

    def test_current_version_skips_migrations(self) -> None:
        """Config entry at current version should not need migrations."""
        current = (
            MagicConfigEntryVersion.MAJOR,
            MagicConfigEntryVersion.MINOR,
        )

        # No migrations needed from current to current
        migrations = get_applicable_migrations(current, current)
        assert len(migrations) == 0

    def test_future_version_skips(self) -> None:
        """Config entry from future version should not need migrations."""
        # Imaginary future version
        future_version = (99, 99)
        current = (
            MagicConfigEntryVersion.MAJOR,
            MagicConfigEntryVersion.MINOR,
        )

        # No migrations needed from future to current
        migrations = get_applicable_migrations(future_version, current)
        assert len(migrations) == 0


class TestBackwardCompatibility:
    """Test backward compatibility with old config formats."""

    def test_old_feature_flag_values_recognized(self) -> None:
        """Old feature flag string values should still be recognized."""
        # These are the old feature flag values from before consolidation
        old_feature_values = [
            "aggregates",  # Old CONF_FEATURE_AGGREGATION
            "light_groups",
            "climate_control",
            "health",
            "presence_hold",
            "ble_trackers",
            "wasp_in_a_box",
            "fan_groups",
            "cover_groups",
            "media_player_groups",
            "area_aware_media_player",
        ]

        # All old values should still be in the new enum
        from custom_components.magic_areas.enums import MagicAreasFeatures

        enum_values = {f.value for f in MagicAreasFeatures}

        for old_value in old_feature_values:
            assert old_value in enum_values, (
                f"Old feature value '{old_value}' not found in MagicAreasFeatures. "
                f"Breaking change detected!"
            )

    def test_aggregation_to_aggregates_stable(self) -> None:
        """Feature flag consolidation: CONF_FEATURE_AGGREGATION value stable."""
        # This documents the contract: the constant name changed but the value didn't
        from custom_components.magic_areas.enums import MagicAreasFeatures

        # Old: CONF_FEATURE_AGGREGATION = "aggregates"
        # New: MagicAreasFeatures.AGGREGATES = "aggregates"
        assert MagicAreasFeatures.AGGREGATES.value == "aggregates"
        assert MagicAreasFeatures.AGGREGATES.value == "aggregates"


class TestMigrationIsolation:
    """Test that migrations are isolated and don't interfere."""

    def test_no_circular_migration_path(self) -> None:
        """Migrations should not create circular upgrade paths."""
        # Build directed graph of migration edges and detect cycles via DFS.
        adjacency: dict[tuple[int, int], set[tuple[int, int]]] = {}
        nodes: set[tuple[int, int]] = set()

        for migration in CONFIG_MIGRATIONS:
            nodes.add(migration.from_version)
            nodes.add(migration.to_version)
            adjacency.setdefault(migration.from_version, set()).add(
                migration.to_version
            )

        visiting: set[tuple[int, int]] = set()
        visited: set[tuple[int, int]] = set()

        def has_cycle(node: tuple[int, int]) -> bool:
            if node in visited:
                return False
            if node in visiting:
                return True

            visiting.add(node)
            for neighbor in adjacency.get(node, set()):
                if has_cycle(neighbor):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        assert not any(has_cycle(node) for node in nodes), (
            "Circular migration path detected in CONFIG_MIGRATIONS"
        )

    def test_migrations_dont_overlap(self) -> None:
        """Migrations should not have overlapping version ranges."""
        for i, mig1 in enumerate(CONFIG_MIGRATIONS):
            for mig2 in CONFIG_MIGRATIONS[i + 1 :]:
                # to_version of earlier should not overlap with from_version of later
                assert mig1.to_version <= mig2.from_version, (
                    f"Migration overlap detected: {mig1} overlaps with {mig2}"
                )
