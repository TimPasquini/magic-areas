"""Pure Adaptive Lighting coordination contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from homeassistant.util import slugify

SWITCH_DOMAIN = "switch"
ADAPTIVE_LIGHTING_PREFIX = "adaptive_lighting"
MAIN_SWITCH = "main"
SLEEP_SWITCH = "sleep"
ADAPT_BRIGHTNESS_SWITCH = "adapt_brightness"
ADAPT_COLOR_SWITCH = "adapt_color"


@dataclass(frozen=True, slots=True)
class AdaptiveLightingSwitchSet:
    """External Adaptive Lighting switch set associated with a Magic Areas target."""

    area_id: str
    main_switch_entity_id: str
    sleep_switch_entity_id: str
    adapt_brightness_switch_entity_id: str
    adapt_color_switch_entity_id: str
    role: str | None = None

    @property
    def entity_ids(self) -> tuple[str, str, str, str]:
        """Return all switch entity IDs in stable order."""
        return (
            self.main_switch_entity_id,
            self.sleep_switch_entity_id,
            self.adapt_brightness_switch_entity_id,
            self.adapt_color_switch_entity_id,
        )


def adaptive_lighting_switch_entity_ids(name: str) -> dict[str, str]:
    """Return the conventional Adaptive Lighting switch IDs for a configuration name."""
    slug = slugify(name)
    return {
        MAIN_SWITCH: f"{SWITCH_DOMAIN}.{ADAPTIVE_LIGHTING_PREFIX}_{slug}",
        SLEEP_SWITCH: f"{SWITCH_DOMAIN}.{ADAPTIVE_LIGHTING_PREFIX}_sleep_mode_{slug}",
        ADAPT_BRIGHTNESS_SWITCH: (
            f"{SWITCH_DOMAIN}.{ADAPTIVE_LIGHTING_PREFIX}_adapt_brightness_{slug}"
        ),
        ADAPT_COLOR_SWITCH: (
            f"{SWITCH_DOMAIN}.{ADAPTIVE_LIGHTING_PREFIX}_adapt_color_{slug}"
        ),
    }


def switch_set_from_explicit_refs(
    *,
    area_id: str,
    switch_refs: Mapping[str, str],
    role: str | None = None,
) -> AdaptiveLightingSwitchSet | None:
    """Build a switch set from explicit references when all required switches exist."""
    if not _has_required_switch_refs(switch_refs):
        return None
    return AdaptiveLightingSwitchSet(
        area_id=area_id,
        role=role,
        main_switch_entity_id=switch_refs[MAIN_SWITCH],
        sleep_switch_entity_id=switch_refs[SLEEP_SWITCH],
        adapt_brightness_switch_entity_id=switch_refs[ADAPT_BRIGHTNESS_SWITCH],
        adapt_color_switch_entity_id=switch_refs[ADAPT_COLOR_SWITCH],
    )


def switch_set_from_name_candidates(
    *,
    area_id: str,
    name: str,
    candidate_entity_ids: Iterable[str],
    role: str | None = None,
) -> AdaptiveLightingSwitchSet | None:
    """Resolve a switch set by conventional entity IDs when the match is complete."""
    expected = adaptive_lighting_switch_entity_ids(name)
    candidates = set(candidate_entity_ids)
    if not all(entity_id in candidates for entity_id in expected.values()):
        return None
    return switch_set_from_explicit_refs(area_id=area_id, switch_refs=expected, role=role)


def _has_required_switch_refs(switch_refs: Mapping[str, str]) -> bool:
    """Return whether explicit refs include every Adaptive Lighting switch."""
    return all(
        _is_switch_entity_id(switch_refs.get(key, ""))
        for key in (
            MAIN_SWITCH,
            SLEEP_SWITCH,
            ADAPT_BRIGHTNESS_SWITCH,
            ADAPT_COLOR_SWITCH,
        )
    )


def _is_switch_entity_id(entity_id: str) -> bool:
    """Return whether an entity ID is a switch entity."""
    return entity_id.startswith(f"{SWITCH_DOMAIN}.")


__all__ = [
    "ADAPT_BRIGHTNESS_SWITCH",
    "ADAPT_COLOR_SWITCH",
    "MAIN_SWITCH",
    "SLEEP_SWITCH",
    "AdaptiveLightingSwitchSet",
    "adaptive_lighting_switch_entity_ids",
    "switch_set_from_explicit_refs",
    "switch_set_from_name_candidates",
]
