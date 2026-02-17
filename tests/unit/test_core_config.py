"""Tests for core config helpers."""

from enum import Enum

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.core.config import (
    get_feature_config,
    has_configured_state,
    has_feature,
    normalize_feature_config,
)


class FeatureEnum(Enum):
    """Example enum for feature normalization."""

    TEST = "test_feature"


def test_normalize_feature_config_list() -> None:
    """Normalize list-based feature config."""
    config = {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain"]}

    enabled, feature_configs = normalize_feature_config(config)

    assert enabled == {"test_feature", "plain"}
    assert feature_configs == {"test_feature": {}, "plain": {}}


def test_normalize_feature_config_dict() -> None:
    """Normalize dict-based feature config."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True},
            "plain": {"value": 10},
        }
    }

    enabled, feature_configs = normalize_feature_config(config)

    assert enabled == {"test_feature", "plain"}
    assert feature_configs == {
        "test_feature": {"flag": True},
        "plain": {"value": 10},
    }


def test_has_configured_state() -> None:
    """Report configured secondary states from config."""
    config = {
        CONF_SECONDARY_STATES: {
            CONF_SLEEP_ENTITY: "light.bedroom",
        }
    }

    assert has_configured_state(config, AreaStates.SLEEP) is True
    assert has_configured_state(config, AreaStates.CLEAR) is False


def test_has_feature_with_list_config() -> None:
    """Check if feature is enabled with list-based config."""
    config = {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain_feature"]}

    assert has_feature(config, "test_feature") is True
    assert has_feature(config, "plain_feature") is True
    assert has_feature(config, "unknown_feature") is False


def test_has_feature_with_dict_config() -> None:
    """Check if feature is enabled with dict-based config."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True},
            "plain": {},
        }
    }

    assert has_feature(config, "test_feature") is True
    assert has_feature(config, "plain") is True
    assert has_feature(config, "unknown") is False


def test_has_feature_with_empty_config() -> None:
    """Check that has_feature returns False for empty config."""
    config: dict = {}

    assert has_feature(config, "any_feature") is False


def test_get_feature_config_returns_config() -> None:
    """Get feature config returns configured options."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True, "value": 42},
            "plain": {"setting": "enabled"},
        }
    }

    assert get_feature_config(config, "test_feature") == {"flag": True, "value": 42}
    assert get_feature_config(config, "plain") == {"setting": "enabled"}


def test_get_feature_config_returns_empty_for_disabled() -> None:
    """Get feature config returns empty dict for disabled feature."""
    config = {
        CONF_ENABLED_FEATURES: {
            FeatureEnum.TEST: {"flag": True},
        }
    }

    assert get_feature_config(config, "unknown_feature") == {}
    assert get_feature_config(config, "plain") == {}


def test_get_feature_config_from_list_config() -> None:
    """Get feature config works with list-based config."""
    config = {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain"]}

    assert get_feature_config(config, "test_feature") == {}
    assert get_feature_config(config, "plain") == {}
    assert get_feature_config(config, "unknown") == {}
