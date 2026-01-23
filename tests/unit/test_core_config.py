"""Tests for core config helpers."""

from enum import Enum

from custom_components.magic_areas.area_constants import AREA_STATE_SLEEP
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.core.config import (
    has_configured_state,
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

    assert has_configured_state(config, AREA_STATE_SLEEP) is True
    assert has_configured_state(config, "unknown") is False
