"""Shared helpers for core identity/entity-id tests."""

from unittest.mock import MagicMock


def make_registry(*entries: tuple[str, str, str, str]) -> MagicMock:
    """Create a mock entity registry with entries.

    Each entry is (entity_id, domain, platform, unique_id).
    """
    registry = MagicMock()
    lookup: dict[tuple[str, str, str], str] = {}
    mock_entries = []

    for entity_id, domain, platform, unique_id in entries:
        lookup[(domain, platform, unique_id)] = entity_id

        entry = MagicMock()
        entry.entity_id = entity_id
        entry.domain = domain
        entry.platform = platform
        entry.unique_id = unique_id
        mock_entries.append(entry)

    registry.async_get_entity_id = MagicMock(
        side_effect=lambda d, p, u: lookup.get((d, p, u))
    )
    registry.entities.values = MagicMock(return_value=mock_entries)
    return registry
