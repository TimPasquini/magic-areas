"""Unit tests for AreaConfig dataclass."""

from typing import Any
from unittest.mock import MagicMock
import pytest

from custom_components.magic_areas.area_state import (
    AreaType,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.components import (
    MAGIC_AREAS_COMPONENTS,
    MAGIC_AREAS_COMPONENTS_GLOBAL,
    MAGIC_AREAS_COMPONENTS_META,
)


@pytest.fixture
def mock_config_entry() -> Any:
    """Create a mock config entry."""
    return MagicMock()


@pytest.fixture
def regular_area_config(mock_config_entry: Any) -> AreaConfig:
    """Create a regular area config."""
    return AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={"test": "value"},
        hass_config=mock_config_entry,
    )


@pytest.fixture
def exterior_area_config(mock_config_entry: Any) -> AreaConfig:
    """Create an exterior area config."""
    return AreaConfig(
        id="patio",
        name="Patio",
        slug="patio",
        area_type=AreaType.EXTERIOR,
        config={"test": "value"},
        hass_config=mock_config_entry,
    )


@pytest.fixture
def meta_area_config(mock_config_entry: Any) -> AreaConfig:
    """Create a meta area config."""
    return AreaConfig(
        id="interior",
        name="Interior",
        slug="interior",
        area_type=AreaType.META,
        config={"test": "value"},
        hass_config=mock_config_entry,
    )


@pytest.fixture
def global_meta_area_config(mock_config_entry: Any) -> AreaConfig:
    """Create a global meta area config."""
    return AreaConfig(
        id=META_AREA_GLOBAL.lower(),
        name="Global",
        slug="global",
        area_type=AreaType.META,
        config={"test": "value"},
        hass_config=mock_config_entry,
    )


def test_area_config_is_meta_false_for_regular_area(regular_area_config: AreaConfig) -> None:
    """Test is_meta returns False for regular areas."""
    assert regular_area_config.is_meta() is False


def test_area_config_is_meta_false_for_exterior_area(exterior_area_config: AreaConfig) -> None:
    """Test is_meta returns False for exterior areas."""
    assert exterior_area_config.is_meta() is False


def test_area_config_is_meta_true_for_meta_area(meta_area_config: AreaConfig) -> None:
    """Test is_meta returns True for meta areas."""
    assert meta_area_config.is_meta() is True


def test_area_config_is_interior_true(regular_area_config: AreaConfig) -> None:
    """Test is_interior returns True for interior areas."""
    assert regular_area_config.is_interior() is True


def test_area_config_is_interior_false_for_exterior(exterior_area_config: AreaConfig) -> None:
    """Test is_interior returns False for exterior areas."""
    assert exterior_area_config.is_interior() is False


def test_area_config_is_interior_false_for_meta(meta_area_config: AreaConfig) -> None:
    """Test is_interior returns False for meta areas."""
    assert meta_area_config.is_interior() is False


def test_area_config_is_exterior_true(exterior_area_config: AreaConfig) -> None:
    """Test is_exterior returns True for exterior areas."""
    assert exterior_area_config.is_exterior() is True


def test_area_config_is_exterior_false_for_interior(regular_area_config: AreaConfig) -> None:
    """Test is_exterior returns False for interior areas."""
    assert regular_area_config.is_exterior() is False


def test_area_config_is_exterior_false_for_meta(meta_area_config: AreaConfig) -> None:
    """Test is_exterior returns False for meta areas."""
    assert meta_area_config.is_exterior() is False


def test_area_config_available_platforms_regular_area(regular_area_config: AreaConfig) -> None:
    """Test available_platforms returns regular platforms for non-meta areas."""
    platforms = regular_area_config.available_platforms()
    assert platforms == MAGIC_AREAS_COMPONENTS
    assert len(platforms) > 0


def test_area_config_available_platforms_exterior_area(exterior_area_config: AreaConfig) -> None:
    """Test available_platforms returns regular platforms for exterior areas."""
    platforms = exterior_area_config.available_platforms()
    assert platforms == MAGIC_AREAS_COMPONENTS
    assert len(platforms) > 0


def test_area_config_available_platforms_meta_area(meta_area_config: AreaConfig) -> None:
    """Test available_platforms returns meta platforms for non-global meta areas."""
    platforms = meta_area_config.available_platforms()
    assert platforms == MAGIC_AREAS_COMPONENTS_META
    assert len(platforms) > 0


def test_area_config_available_platforms_global_meta_area(global_meta_area_config: AreaConfig) -> None:
    """Test available_platforms returns global platforms for global meta area."""
    platforms = global_meta_area_config.available_platforms()
    assert platforms == MAGIC_AREAS_COMPONENTS_GLOBAL
    assert len(platforms) > 0


def test_area_config_hash_stability(regular_area_config: AreaConfig) -> None:
    """Test that hash is stable."""
    hash1 = hash(regular_area_config)
    hash2 = hash(regular_area_config)
    assert hash1 == hash2


def test_area_config_hash_different_for_different_ids(mock_config_entry: Any) -> None:
    """Test that different area IDs produce different hashes."""
    config1 = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=mock_config_entry,
    )
    config2 = AreaConfig(
        id="bedroom",
        name="Bedroom",
        slug="bedroom",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=mock_config_entry,
    )
    assert hash(config1) != hash(config2)


def test_area_config_hash_different_for_different_types(mock_config_entry: Any) -> None:
    """Test that different area types produce different hashes."""
    config1 = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=mock_config_entry,
    )
    config2 = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.EXTERIOR,
        config={},
        hass_config=mock_config_entry,
    )
    assert hash(config1) != hash(config2)


def test_area_config_hash_as_dict_key(regular_area_config: AreaConfig, exterior_area_config: AreaConfig) -> None:
    """Test that AreaConfig can be used as a dictionary key."""
    mapping = {regular_area_config: "interior", exterior_area_config: "exterior"}
    assert mapping[regular_area_config] == "interior"
    assert mapping[exterior_area_config] == "exterior"


def test_area_config_with_optional_fields(mock_config_entry: Any) -> None:
    """Test AreaConfig with optional fields set."""
    config = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=mock_config_entry,
        icon="mdi:home",
        floor_id="floor_1",
    )
    assert config.icon == "mdi:home"
    assert config.floor_id == "floor_1"


def test_area_config_without_optional_fields(mock_config_entry: Any) -> None:
    """Test AreaConfig with optional fields at defaults."""
    config = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=mock_config_entry,
    )
    assert config.icon is None
    assert config.floor_id is None
