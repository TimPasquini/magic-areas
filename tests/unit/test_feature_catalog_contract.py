"""Contracts for canonical feature catalog wiring."""

from __future__ import annotations

from custom_components.magic_areas.features.catalog import FEATURE_INFO_BY_FEATURE
from custom_components.magic_areas.features.catalog import FEATURE_REGISTRATIONS
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY


def test_registration_ids_match_module_ids() -> None:
    """Each registration pairs module + metadata for the same feature id."""
    for registration in FEATURE_REGISTRATIONS:
        assert registration.module.id == registration.info.id


def test_default_registry_features_match_catalog_order() -> None:
    """Registry feature order should match canonical catalog order."""
    assert FEATURE_REGISTRY.all_features() == [
        registration.module.id for registration in FEATURE_REGISTRATIONS
    ]


def test_registry_feature_info_comes_from_catalog() -> None:
    """Registry should expose the same metadata instances as catalog."""
    for feature in FEATURE_REGISTRY.all_features():
        assert FEATURE_REGISTRY.feature_info_for(feature) is FEATURE_INFO_BY_FEATURE[feature]
