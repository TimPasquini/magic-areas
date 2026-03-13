"""Fan snapshot contract tests."""

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.helpers import init_integration as init_integration_helper
from tests.helpers import shutdown_integration
from tests.mocks import MockFan

pytest_plugins = ("tests.platforms.fan_testkit",)


async def test_fan_snapshot_fields(
    hass: HomeAssistant,
    fan_groups_config_entry: MockConfigEntry,
    entities_fan_multiple: list[MockFan],
) -> None:
    """Test fan snapshot fields used by the platform."""
    await init_integration_helper(hass, [fan_groups_config_entry])

    data = fan_groups_config_entry.runtime_data.coordinator.data
    assert data is not None
    assert MagicAreasFeatures.FAN_GROUPS in data.enabled_features
    assert FAN_DOMAIN in data.entities

    entity_ids = {entity["entity_id"] for entity in data.entities[FAN_DOMAIN]}
    for fan in entities_fan_multiple:
        assert fan.entity_id in entity_ids

    await shutdown_integration(hass, [fan_groups_config_entry])
