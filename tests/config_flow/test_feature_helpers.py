"""Tests for feature helper functions."""

from unittest.mock import MagicMock

from custom_components.magic_areas.area_state import AreaType, META_AREA_GLOBAL
from custom_components.magic_areas.config_keys.area import CONF_TYPE
from custom_components.magic_areas.config_flows.steps import (
    get_configurable_features,
    get_feature_list,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.registry import FEATURE_REGISTRY
from custom_components.magic_areas.schemas.features import (
    CONFIGURABLE_FEATURES,
    NON_CONFIGURABLE_FEATURES_META,
)

EXPECTED_FEATURE_ORDER_PREFIX = (
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.FAN_GROUPS,
    MagicAreasFeatures.COVER_GROUPS,
    MagicAreasFeatures.CLIMATE_CONTROL,
)


def _assert_same_features_in_task_order(
    result: list[MagicAreasFeatures],
    expected: list[MagicAreasFeatures],
) -> None:
    """Assert helper preserves feature membership while applying UI order."""
    assert set(result) == set(expected)
    ordered_prefix = [feature for feature in EXPECTED_FEATURE_ORDER_PREFIX if feature in expected]
    assert result[: len(ordered_prefix)] == ordered_prefix


class TestGetFeatureList:
    """Tests for get_feature_list() helper function."""

    def test_returns_default_list_when_area_config_is_none(self) -> None:
        """Test that default feature list is returned when area_config is None."""
        result = get_feature_list(None)

        _assert_same_features_in_task_order(
            result,
            FEATURE_REGISTRY.available_features_for_area(None),
        )
        assert len(result) > 0
        assert all(isinstance(f, MagicAreasFeatures) for f in result)

    def test_returns_regular_feature_list_for_regular_area(self) -> None:
        """Test that regular feature list is returned for regular area type."""
        area_config = MagicMock()
        area_config.config = {CONF_TYPE: AreaType.INTERIOR}
        area_config.id = "kitchen"

        result = get_feature_list(area_config)

        _assert_same_features_in_task_order(
            result,
            FEATURE_REGISTRY.available_features_for_area(area_config),
        )
        assert MagicAreasFeatures.LIGHT_GROUPS in result
        assert MagicAreasFeatures.PRESENCE_HOLD in result

    def test_returns_meta_feature_list_for_meta_area(self) -> None:
        """Test that meta feature list is returned for meta area type."""
        area_config = MagicMock()
        area_config.config = {CONF_TYPE: AreaType.META}
        area_config.id = "interior"

        result = get_feature_list(area_config)

        _assert_same_features_in_task_order(
            result,
            FEATURE_REGISTRY.available_features_for_area(area_config),
        )
        assert MagicAreasFeatures.LIGHT_GROUPS in result
        # PRESENCE_HOLD should not be in meta list
        assert MagicAreasFeatures.PRESENCE_HOLD not in result

    def test_returns_global_feature_list_for_global_meta_area(self) -> None:
        """Test that global feature list is returned for global meta-area."""
        area_config = MagicMock()
        area_config.config = {CONF_TYPE: AreaType.META}
        area_config.id = META_AREA_GLOBAL.lower()

        result = get_feature_list(area_config)

        _assert_same_features_in_task_order(
            result,
            FEATURE_REGISTRY.available_features_for_area(area_config),
        )
        assert MagicAreasFeatures.LIGHT_GROUPS in result

    def test_returns_meta_list_for_non_global_meta_areas(self) -> None:
        """Test that meta list is returned for non-global meta areas."""
        area_config = MagicMock()
        area_config.config = {CONF_TYPE: AreaType.META}
        area_config.id = "floor_0"  # Not global

        result = get_feature_list(area_config)

        _assert_same_features_in_task_order(
            result,
            FEATURE_REGISTRY.available_features_for_area(area_config),
        )

    def test_handles_empty_config_dict(self) -> None:
        """Test that default list is used when config dict is empty."""
        area_config = MagicMock()
        area_config.config = {}
        area_config.id = "kitchen"

        result = get_feature_list(area_config)

        _assert_same_features_in_task_order(
            result,
            FEATURE_REGISTRY.available_features_for_area(area_config),
        )

    def test_feature_list_contains_only_enum_members(self) -> None:
        """Test that returned feature lists contain only enum members."""
        lists_to_check = [
            (None, FEATURE_REGISTRY.available_features_for_area(None)),
            (
                MagicMock(config={CONF_TYPE: AreaType.INTERIOR}, id="kitchen"),
                FEATURE_REGISTRY.available_features_for_area(
                    MagicMock(config={CONF_TYPE: AreaType.INTERIOR}, id="kitchen")
                ),
            ),
            (
                MagicMock(config={CONF_TYPE: AreaType.META}, id="interior"),
                FEATURE_REGISTRY.available_features_for_area(
                    MagicMock(config={CONF_TYPE: AreaType.META}, id="interior")
                ),
            ),
        ]

        for area_config, expected_list in lists_to_check:
            result = get_feature_list(area_config)
            _assert_same_features_in_task_order(result, expected_list)
            assert all(isinstance(f, MagicAreasFeatures) for f in result)


class TestGetConfigurableFeatures:
    """Tests for get_configurable_features() helper function."""

    def test_returns_all_configurable_when_area_config_is_none(self) -> None:
        """Test that all configurable features returned when area_config is None."""
        result = get_configurable_features(None)

        # Should return all keys from CONFIGURABLE_FEATURES
        assert len(result) == len(CONFIGURABLE_FEATURES)
        assert result == list(CONFIGURABLE_FEATURES.keys())

    def test_returns_all_configurable_for_regular_area(self) -> None:
        """Test that all configurable features returned for regular area."""
        area_config = MagicMock()
        area_config.is_meta.return_value = False
        area_config.config = {CONF_TYPE: AreaType.INTERIOR}
        area_config.id = "kitchen"

        result = get_configurable_features(area_config)

        assert len(result) == len(CONFIGURABLE_FEATURES)
        assert all(isinstance(f, MagicAreasFeatures) for f in result)

    def test_excludes_non_configurable_features_for_meta_area(self) -> None:
        """Test that non-configurable features excluded for meta areas."""
        area_config = MagicMock()
        area_config.is_meta.return_value = True
        area_config.config = {CONF_TYPE: AreaType.META}
        area_config.id = "interior"

        result = get_configurable_features(area_config)

        # Should have fewer features than regular area
        assert len(result) < len(CONFIGURABLE_FEATURES)

        # Check that all non-configurable features are removed
        for non_config_feature in NON_CONFIGURABLE_FEATURES_META:
            assert non_config_feature not in result

    def test_meta_area_has_fewer_configurable_features(self) -> None:
        """Test that meta areas have fewer configurable features than regular areas."""
        regular_area = MagicMock()
        regular_area.is_meta.return_value = False

        meta_area = MagicMock()
        meta_area.is_meta.return_value = True

        regular_features = get_configurable_features(regular_area)
        meta_features = get_configurable_features(meta_area)

        assert len(meta_features) < len(regular_features)

    def test_all_features_are_enum_members(self) -> None:
        """Test that returned features are all enum members."""
        configs = [
            None,
            MagicMock(is_meta=lambda: False),
            MagicMock(is_meta=lambda: True),
        ]

        for area_config in configs:
            result = get_configurable_features(area_config)
            assert all(isinstance(f, MagicAreasFeatures) for f in result)

    def test_non_configurable_features_are_known_types(self) -> None:
        """Test that NON_CONFIGURABLE_FEATURES_META contains known feature types."""
        for feature in NON_CONFIGURABLE_FEATURES_META:
            assert isinstance(feature, MagicAreasFeatures)

    def test_configurable_features_intersection(self) -> None:
        """Test the relationship between regular and meta configurable features."""
        regular_features = set(get_configurable_features(MagicMock(is_meta=lambda: False)))
        meta_features = set(get_configurable_features(MagicMock(is_meta=lambda: True)))

        # All meta features should be in regular features
        assert meta_features.issubset(regular_features)

        # Feature-specific meta exclusions should include non-configurable-on-meta.
        difference = regular_features - meta_features
        assert set(NON_CONFIGURABLE_FEATURES_META).issubset(difference)
