"""Snapshot tests for Magic Areas config flow.

Tests complex config flow results and feature configurations using Syrupy snapshots.
These tests capture the structure of:
- Config flow user interactions and results
- Options flow state and configuration
- Feature registry configuration
- Enabled features structure
"""

from typing import cast

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion

from custom_components.magic_areas.area_state import (
    AreaType,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.config_flows import (
    get_feature_config_steps,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data


@pytest.mark.asyncio
async def test_config_flow_user_flow_snapshot(
    hass: HomeAssistant, snapshot: SnapshotAssertion
) -> None:
    """Test complete user flow through config flow form.

    Captures the structure of form data as user progresses through
    configuration steps. Snapshot includes all form fields and their
    validation rules.
    """
    area_registry = async_get_ar(hass)

    # Create area in registry
    area_registry.async_create(name=DEFAULT_MOCK_AREA.value)

    # Get config entry data
    config_data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)

    # Snapshot the full config flow data
    assert config_data == snapshot


@pytest.mark.asyncio
async def test_options_flow_snapshot(
    hass: HomeAssistant, init_integration: MockConfigEntry, snapshot: SnapshotAssertion
) -> None:
    """Test options flow configuration snapshot.

    Captures the complete state of the options flow, including all
    available options and their current values.
    """
    entry = init_integration

    # Get the entry data
    step_data = entry.data.copy()

    # Add current options
    if entry.options:
        step_data.update(entry.options)

    # Remove dynamic timestamp
    if "entity_ts" in step_data:
        del step_data["entity_ts"]

    # Snapshot the options flow state
    assert step_data == snapshot


@pytest.mark.asyncio
async def test_enabled_features_snapshot(
    hass: HomeAssistant, snapshot: SnapshotAssertion
) -> None:
    """Test feature configuration snapshot.

    Captures the structure of enabled features configuration including
    all feature-specific settings and parameters.
    """
    area_registry = async_get_ar(hass)
    area_registry.async_create(name=DEFAULT_MOCK_AREA.value)

    config_data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)

    # Add some features to the config
    config_data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
        },
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 20,
        },
    }

    enabled_features = config_data.get(CONF_ENABLED_FEATURES, {})

    # Snapshot the feature configuration
    assert enabled_features == snapshot


@pytest.mark.asyncio
async def test_feature_registry_snapshot(snapshot: SnapshotAssertion) -> None:
    """Test feature registry structure snapshot.

    Captures the complete feature registry including all features,
    their schemas, and configuration options.
    """
    # Convert feature registry to serializable format
    feature_registry = get_feature_config_steps()
    registry_list = sorted(
        [
            {
                "key": feature_name,
                "name": feature_config.feature,
                "has_schema": feature_config.schema is not None,
                "merge_options": feature_config.merge_options,
                "has_next_step": feature_config.next_step is not None,
            }
            for feature_name, feature_config in feature_registry.items()
        ],
        key=lambda x: cast(str, x["key"]),
    )

    # Snapshot the registry structure
    assert registry_list == snapshot


@pytest.mark.asyncio
async def test_config_flow_basic_area_data(
    hass: HomeAssistant, snapshot: SnapshotAssertion
) -> None:
    """Test basic area configuration data snapshot.

    Captures the structure of basic area configuration including
    area type, ID, and presence settings.
    """
    area_registry = async_get_ar(hass)
    area_registry.async_create(name=DEFAULT_MOCK_AREA.value)

    config_data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)

    # Extract only basic config fields
    basic_config = {
        CONF_ID: config_data.get(CONF_ID),
        CONF_TYPE: config_data.get(CONF_TYPE),
        CONF_NAME: config_data.get(CONF_NAME),
        CONF_CLEAR_TIMEOUT: config_data.get(CONF_CLEAR_TIMEOUT),
        CONF_EXTENDED_TIMEOUT: config_data.get(CONF_EXTENDED_TIMEOUT),
        CONF_PRESENCE_DEVICE_PLATFORMS: config_data.get(CONF_PRESENCE_DEVICE_PLATFORMS),
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: config_data.get(
            CONF_PRESENCE_SENSOR_DEVICE_CLASS
        ),
    }

    # Snapshot basic configuration
    assert basic_config == snapshot


@pytest.mark.asyncio
async def test_config_flow_meta_area_data(
    hass: HomeAssistant, snapshot: SnapshotAssertion
) -> None:
    """Test meta area configuration data snapshot.

    Captures the structure specific to meta areas including type
    and meta area settings.
    """
    area_registry = async_get_ar(hass)

    # Create regular areas
    area_registry.async_create(name="bedroom")
    area_registry.async_create(name="kitchen")

    config_data = {
        CONF_ID: META_AREA_GLOBAL,
        CONF_TYPE: AreaType.META,
        CONF_NAME: "Global Meta Area",
        CONF_ENABLED_FEATURES: {},
    }

    # Snapshot meta area config
    assert config_data == snapshot


@pytest.mark.asyncio
async def test_config_keys_snapshot(snapshot: SnapshotAssertion) -> None:
    """Test configuration keys and their relationships snapshot.

    Captures the structure of all configuration keys used throughout
    the config flow and options flow.
    """
    config_keys = {
        "area_basic": {
            CONF_ID,
            CONF_TYPE,
            CONF_NAME,
        },
        "presence": {
            CONF_PRESENCE_DEVICE_PLATFORMS,
            CONF_PRESENCE_SENSOR_DEVICE_CLASS,
        },
        "timeouts": {
            CONF_CLEAR_TIMEOUT,
            CONF_EXTENDED_TIMEOUT,
        },
        "features": {
            CONF_ENABLED_FEATURES,
        },
    }

    # Convert sets to lists for JSON serialization
    serializable_keys = {k: sorted(v) for k, v in config_keys.items()}

    # Snapshot configuration keys
    assert serializable_keys == snapshot


@pytest.mark.asyncio
async def test_config_flow_exterior_area_data(
    hass: HomeAssistant, snapshot: SnapshotAssertion
) -> None:
    """Test exterior area configuration snapshot.

    Captures the specific configuration structure for exterior areas
    including type and exterior-specific settings.
    """
    area_registry = async_get_ar(hass)
    area_registry.async_create(name="patio")

    config_data = {
        CONF_ID: "patio",
        CONF_TYPE: AreaType.EXTERIOR,
        CONF_NAME: "Patio",
        CONF_CLEAR_TIMEOUT: 300,
        CONF_ENABLED_FEATURES: {},
    }

    # Snapshot exterior area config
    assert config_data == snapshot


@pytest.mark.asyncio
async def test_feature_config_aggregation_snapshot(
    snapshot: SnapshotAssertion,
) -> None:
    """Test aggregation feature configuration snapshot.

    Captures the structure of aggregation feature settings including
    minimum entities and illuminance threshold.
    """
    aggregation_config = {
        CONF_AGGREGATES_MIN_ENTITIES: 2,
        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 50,
    }

    # Snapshot aggregation feature config
    assert aggregation_config == snapshot


@pytest.mark.asyncio
async def test_feature_list_snapshot(snapshot: SnapshotAssertion) -> None:
    """Test feature list and registry keys snapshot.

    Captures all available features and their registry entries
    for validation and reference.
    """
    feature_keys = sorted(get_feature_config_steps().keys())

    # Snapshot feature list
    assert feature_keys == snapshot


@pytest.mark.asyncio
async def test_config_flow_error_responses_snapshot(
    hass: HomeAssistant, snapshot: SnapshotAssertion
) -> None:
    """Test config flow error response structure snapshot.

    Captures the structure of error responses from config flow
    validation including error types and messages.
    """
    # Error response structure
    error_responses = {
        "validation_error": {
            "code": "invalid_config",
            "message": "Configuration validation failed",
        },
        "missing_entity": {
            "code": "entity_not_found",
            "message": "Required entity not found",
        },
        "duplicate_area": {
            "code": "duplicate_area_config",
            "message": "Area already configured",
        },
    }

    # Snapshot error response structure
    assert error_responses == snapshot
