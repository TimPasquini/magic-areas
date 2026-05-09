"""Pure Adaptive Lighting coordination contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.util import slugify

SWITCH_DOMAIN = "switch"
ADAPTIVE_LIGHTING_PREFIX = "adaptive_lighting"
MAIN_SWITCH = "main"
SLEEP_SWITCH = "sleep"
ADAPT_BRIGHTNESS_SWITCH = "adapt_brightness"
ADAPT_COLOR_SWITCH = "adapt_color"
ATTR_LIGHTS = "lights"


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


@dataclass(frozen=True, slots=True)
class AdaptiveLightingSwitchCandidate:
    """Registry-shaped Adaptive Lighting switch candidate used for pure matching."""

    entity_id: str
    area_id: str | None = None
    label_ids: frozenset[str] = frozenset()
    label_names: frozenset[str] = frozenset()


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
    return switch_set_from_explicit_refs(
        area_id=area_id, switch_refs=expected, role=role
    )


def switch_set_from_discovery_candidates(
    *,
    area_id: str,
    candidates: Iterable[AdaptiveLightingSwitchCandidate],
    role: str | None = None,
    required_label_ids: Iterable[str] = (),
    required_label_names: Iterable[str] = (),
) -> AdaptiveLightingSwitchSet | None:
    """Resolve one unambiguous switch set from area/label-filtered candidates.

    This stays pure so the matching contract can be proven before binding it to HA
    registries. A candidate must match the requested area or all required labels; this
    prevents area-less switches from being adopted by name alone.
    """
    required_ids = frozenset(required_label_ids)
    required_names = frozenset(required_label_names)
    grouped: dict[str, dict[str, str]] = {}

    for candidate in candidates:
        if not _candidate_matches_scope(
            candidate,
            area_id=area_id,
            required_label_ids=required_ids,
            required_label_names=required_names,
        ):
            continue

        switch_type, group_slug = _adaptive_lighting_switch_parts(candidate.entity_id)
        if switch_type is None or group_slug is None:
            continue
        grouped.setdefault(group_slug, {})[switch_type] = candidate.entity_id

    matches = [
        switch_set
        for switch_refs in grouped.values()
        if (
            switch_set := switch_set_from_explicit_refs(
                area_id=area_id,
                role=role,
                switch_refs=switch_refs,
            )
        )
        is not None
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def adaptive_lighting_apply_data(
    switch_set: AdaptiveLightingSwitchSet,
    *,
    light_entity_ids: Iterable[str],
    adapt_brightness: bool | None = None,
    adapt_color: bool | None = None,
    turn_on_lights: bool | None = None,
    transition: float | None = None,
) -> dict[str, object]:
    """Return documented service data for `adaptive_lighting.apply`."""
    data: dict[str, object] = {
        ATTR_ENTITY_ID: switch_set.main_switch_entity_id,
        ATTR_LIGHTS: tuple(light_entity_ids),
    }
    if adapt_brightness is not None:
        data["adapt_brightness"] = adapt_brightness
    if adapt_color is not None:
        data["adapt_color"] = adapt_color
    if turn_on_lights is not None:
        data["turn_on_lights"] = turn_on_lights
    if transition is not None:
        data["transition"] = transition
    return data


def adaptive_lighting_manual_control_data(
    switch_set: AdaptiveLightingSwitchSet,
    *,
    light_entity_ids: Iterable[str],
    manual_control: bool | str,
) -> dict[str, object]:
    """Return documented service data for `adaptive_lighting.set_manual_control`."""
    return {
        ATTR_ENTITY_ID: switch_set.main_switch_entity_id,
        ATTR_LIGHTS: tuple(light_entity_ids),
        "manual_control": manual_control,
    }


def adaptive_lighting_change_switch_settings_data(
    switch_entity_id: str,
    **settings: object,
) -> dict[str, object]:
    """Return documented service data for `adaptive_lighting.change_switch_settings`."""
    return {ATTR_ENTITY_ID: switch_entity_id, **settings}


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


def _candidate_matches_scope(
    candidate: AdaptiveLightingSwitchCandidate,
    *,
    area_id: str,
    required_label_ids: frozenset[str],
    required_label_names: frozenset[str],
) -> bool:
    """Return whether an AL switch candidate is safely scoped to this MA target."""
    label_ids_match = bool(required_label_ids) and required_label_ids.issubset(
        candidate.label_ids
    )
    label_names_match = bool(required_label_names) and required_label_names.issubset(
        candidate.label_names
    )
    if required_label_ids and not label_ids_match:
        return False
    if required_label_names and not label_names_match:
        return False
    if required_label_ids or required_label_names:
        return True
    return candidate.area_id == area_id


def _adaptive_lighting_switch_parts(entity_id: str) -> tuple[str | None, str | None]:
    """Return the Adaptive Lighting switch type and shared group slug."""
    if not _is_switch_entity_id(entity_id):
        return None, None

    object_id = entity_id.removeprefix(f"{SWITCH_DOMAIN}.")
    prefix = f"{ADAPTIVE_LIGHTING_PREFIX}_"
    if not object_id.startswith(prefix):
        return None, None

    suffix = object_id.removeprefix(prefix)
    for switch_type, switch_prefix in (
        (SLEEP_SWITCH, "sleep_mode_"),
        (ADAPT_BRIGHTNESS_SWITCH, "adapt_brightness_"),
        (ADAPT_COLOR_SWITCH, "adapt_color_"),
    ):
        if suffix.startswith(switch_prefix):
            group_slug = suffix.removeprefix(switch_prefix)
            return (switch_type, group_slug) if group_slug else (None, None)

    return (MAIN_SWITCH, suffix) if suffix else (None, None)


__all__ = [
    "ADAPT_BRIGHTNESS_SWITCH",
    "ADAPT_COLOR_SWITCH",
    "ATTR_LIGHTS",
    "MAIN_SWITCH",
    "SLEEP_SWITCH",
    "AdaptiveLightingSwitchCandidate",
    "AdaptiveLightingSwitchSet",
    "adaptive_lighting_apply_data",
    "adaptive_lighting_change_switch_settings_data",
    "adaptive_lighting_manual_control_data",
    "adaptive_lighting_switch_entity_ids",
    "switch_set_from_discovery_candidates",
    "switch_set_from_explicit_refs",
    "switch_set_from_name_candidates",
]
