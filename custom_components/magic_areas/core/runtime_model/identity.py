"""Pure unique-id builders for runtime entities."""


def build_feature_unique_id(
    *,
    feature_id: str,
    area_id: str,
    translation_key: str | None = None,
    extra_identifiers: list[str] | None = None,
) -> str:
    """Build canonical unique_id for MagicEntity-derived entities."""
    unique_id_parts = [feature_id, area_id]
    if translation_key and translation_key != feature_id:
        unique_id_parts.append(translation_key)
    if extra_identifiers:
        unique_id_parts.extend(extra_identifiers)
    return "_".join(unique_id_parts)


def build_presence_tracking_unique_id(*, area_id: str) -> str:
    """Return unique_id for the area-state presence sensor."""
    return build_feature_unique_id(
        feature_id="presence_tracking",
        area_id=area_id,
        translation_key="area_state",
    )


__all__ = [
    "build_feature_unique_id",
    "build_presence_tracking_unique_id",
]
