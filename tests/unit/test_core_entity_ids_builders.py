"""Unit tests for runtime-model identity unique-id builders and public surface."""

import custom_components.magic_areas.core.runtime_model.identity as core_identity
from custom_components.magic_areas.core.aggregates import aggregate_group_id
from custom_components.magic_areas.core.runtime_model import (
    build_entity_references,
    build_feature_unique_id,
    build_presence_tracking_unique_id,
)

from tests.unit.core_entity_ids_testkit import make_registry


def test_build_entity_references_empty_registry() -> None:
    """Test build_entity_references with empty entity registry."""
    refs = build_entity_references(area_id="kitchen", entity_registry=make_registry())

    assert refs.area_state_sensor is None
    assert refs.presence_hold_switch is None
    assert refs.light_control_switch is None
    assert refs.fan_group is None
    assert refs.fan_control_switch is None
    assert refs.media_player_group is None
    assert refs.media_player_control_switch is None
    assert refs.climate_control_switch is None
    assert refs.cover_group is None
    assert refs.wasp_in_a_box_sensor is None
    assert refs.ble_tracker_monitor is None
    assert refs.threshold_sensor is None
    assert refs.health_sensor is None


def test_build_feature_unique_id_omits_redundant_translation_key() -> None:
    """Feature id and translation key should not duplicate in unique_id."""
    assert (
        build_feature_unique_id(
            feature_id="climate_control",
            area_id="kitchen",
            translation_key="climate_control",
        )
        == "climate_control_kitchen"
    )


def test_build_feature_unique_id_includes_translation_and_extra_identifiers() -> None:
    """Unique-id builder should preserve translation and appended identifiers."""
    assert (
        build_feature_unique_id(
            feature_id="aggregates",
            area_id="kitchen",
            translation_key="aggregate",
            extra_identifiers=["temperature"],
        )
        == "aggregates_kitchen_aggregate_temperature"
    )


def test_common_unique_id_templates_are_canonical() -> None:
    """Template helpers return the expected canonical unique-id shapes."""
    assert (
        build_presence_tracking_unique_id(area_id="kitchen")
        == "presence_tracking_kitchen_area_state"
    )
    assert (
        aggregate_group_id(area_id="kitchen", device_class="temperature")
        == "aggregates_kitchen_aggregate_temperature"
    )


def test_runtime_model_identity_public_surface_remains_generic() -> None:
    """runtime_model.identity should expose only generic identity builders."""
    exported = set(getattr(core_identity, "__all__", []))
    assert exported == {
        "build_feature_unique_id",
        "build_presence_tracking_unique_id",
    }
