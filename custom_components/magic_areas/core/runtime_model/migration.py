"""Unique-id migration helpers for Magic Areas entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from custom_components.magic_areas.components import MAGICAREAS_UNIQUEID_PREFIX

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


def compute_unique_id_from_entity_id(
    *, entity_id: str, area_id: str, area_slug: str
) -> str | None:
    """Compute the new unique_id format from a legacy entity_id."""
    _, _, entity_name = entity_id.partition(".")
    prefix = f"{MAGICAREAS_UNIQUEID_PREFIX}_"
    if not entity_name.startswith(prefix):
        return None

    remainder = entity_name[len(prefix) :]
    marker = f"_{area_slug}_"
    if marker in remainder:
        feature_id, suffix = remainder.split(marker, 1)
    elif remainder.endswith(f"_{area_slug}"):
        feature_id = remainder[: -(len(area_slug) + 1)]
        suffix = ""
    else:
        return None

    if not feature_id:
        return None

    if suffix:
        return f"{feature_id}_{area_id}_{suffix}"
    return f"{feature_id}_{area_id}"


async def async_migrate_unique_ids(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Migrate Magic Areas entity unique_ids to the new format."""
    area_id = config_entry.data.get("id")
    if not area_id:
        return

    area_slug = slugify(config_entry.data.get(ATTR_NAME, area_id))
    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)

    for entry in entries:
        if entry.unique_id and not entry.unique_id.startswith(
            f"{MAGICAREAS_UNIQUEID_PREFIX}_"
        ):
            continue

        new_unique_id = compute_unique_id_from_entity_id(
            entity_id=entry.entity_id,
            area_id=area_id,
            area_slug=area_slug,
        )
        if not new_unique_id or new_unique_id == entry.unique_id:
            continue

        try:
            entity_registry.async_update_entity(
                entry.entity_id, new_unique_id=new_unique_id
            )
        except (
            AttributeError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as err:  # pragma: no cover
            _LOGGER.warning(
                "%s: Unable to migrate unique_id for %s: %s",
                config_entry.data.get(ATTR_NAME, area_id),
                entry.entity_id,
                err,
            )


__all__ = [
    "async_migrate_unique_ids",
    "compute_unique_id_from_entity_id",
]
