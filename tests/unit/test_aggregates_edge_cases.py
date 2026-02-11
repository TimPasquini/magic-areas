"""Unit tests for aggregates.py edge cases."""

import pytest
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT, ATTR_ENTITY_ID
from enum import Enum

from custom_components.magic_areas.core.aggregates import (
    _normalize_allowed_device_classes,
    _is_valid_value,
    _min_entities,
)


class MockDeviceClass(Enum):
    """Mock device class enum."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"


def test_normalize_allowed_device_classes_with_enum_list() -> None:
    """Test normalizing device classes from enum list."""
    result = _normalize_allowed_device_classes(
        [MockDeviceClass.TEMPERATURE, MockDeviceClass.HUMIDITY],
        ["fallback"],
    )
    assert "temperature" in result
    assert "humidity" in result


def test_normalize_allowed_device_classes_with_string_list() -> None:
    """Test normalizing device classes from string list."""
    result = _normalize_allowed_device_classes(
        ["temperature", "humidity"],
        ["fallback"],
    )
    assert "temperature" in result
    assert "humidity" in result


def test_normalize_allowed_device_classes_with_set() -> None:
    """Test normalizing device classes from set."""
    result = _normalize_allowed_device_classes(
        {"temperature", "humidity"},
        ["fallback"],
    )
    assert "temperature" in result
    assert "humidity" in result


def test_normalize_allowed_device_classes_with_tuple() -> None:
    """Test normalizing device classes from tuple."""
    result = _normalize_allowed_device_classes(
        ("temperature", "humidity"),
        ["fallback"],
    )
    assert "temperature" in result
    assert "humidity" in result


def test_normalize_allowed_device_classes_invalid_type() -> None:
    """Test normalizing device classes with invalid type falls back to default."""
    result = _normalize_allowed_device_classes("not_a_list", ["fallback"])
    assert "fallback" in result


def test_normalize_allowed_device_classes_none() -> None:
    """Test normalizing None device classes uses fallback."""
    result = _normalize_allowed_device_classes(None, ["fallback"])
    assert "fallback" in result


def test_normalize_allowed_device_classes_empty_list() -> None:
    """Test normalizing empty list returns empty set."""
    result = _normalize_allowed_device_classes([], ["fallback"])
    assert len(result) == 0


def test_is_valid_value_with_none() -> None:
    """Test is_valid_value returns False for None."""
    assert not _is_valid_value(None)


def test_is_valid_value_with_empty_string() -> None:
    """Test is_valid_value returns False for empty string."""
    assert not _is_valid_value("")


def test_is_valid_value_with_valid_string() -> None:
    """Test is_valid_value returns True for valid string."""
    assert _is_valid_value("temperature")


def test_is_valid_value_with_unknown() -> None:
    """Test is_valid_value returns False for 'unknown'."""
    assert not _is_valid_value("unknown")


def test_is_valid_value_with_none_string() -> None:
    """Test is_valid_value returns False for 'None' string."""
    assert not _is_valid_value("None")


def test_is_valid_value_with_unavailable() -> None:
    """Test is_valid_value returns False for 'unavailable'."""
    assert not _is_valid_value("unavailable")


def test_min_entities_from_empty_config() -> None:
    """Test _min_entities with empty config."""
    result = _min_entities({})
    assert isinstance(result, int)
    assert result >= 0


def test_min_entities_from_config_with_explicit_value() -> None:
    """Test _min_entities with explicit min_entities value."""
    from custom_components.magic_areas.config_keys import CONF_AGGREGATES_MIN_ENTITIES
    from custom_components.magic_areas.features import CONF_FEATURE_AGGREGATION

    config = {
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 5,
        }
    }
    result = _min_entities(config)
    assert result == 5


def test_min_entities_from_config_with_int() -> None:
    """Test _min_entities handles int value correctly."""
    from custom_components.magic_areas.config_keys import CONF_AGGREGATES_MIN_ENTITIES
    from custom_components.magic_areas.features import CONF_FEATURE_AGGREGATION

    config = {
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 3,
        }
    }
    result = _min_entities(config)
    assert result == 3


def test_min_entities_from_config_with_string_int() -> None:
    """Test _min_entities handles string int value correctly."""
    from custom_components.magic_areas.config_keys import CONF_AGGREGATES_MIN_ENTITIES
    from custom_components.magic_areas.features import CONF_FEATURE_AGGREGATION

    config = {
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: "2",
        }
    }
    result = _min_entities(config)
    assert result == 2


def test_min_entities_from_config_with_invalid_string() -> None:
    """Test _min_entities handles invalid string gracefully."""
    from custom_components.magic_areas.config_keys import CONF_AGGREGATES_MIN_ENTITIES
    from custom_components.magic_areas.features import CONF_FEATURE_AGGREGATION

    config = {
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: "invalid",
        }
    }
    result = _min_entities(config)
    assert isinstance(result, int)
