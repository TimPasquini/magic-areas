"""Basic fan-group platform tests."""


from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import assert_in_attribute, assert_state
from tests.mocks import MockFan

pytest_plugins = ("tests.platforms.fan_testkit",)


async def test_fan_group_basic(
    hass: HomeAssistant,
    entities_fan_multiple: list[MockFan],
    _setup_integration_fan_groups: None,
) -> None:
    """Test Fan groups basic functionality."""
    fan_group_entity_id = (
        f"{FAN_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_group"
    )

    fan_group_state = hass.states.get(fan_group_entity_id)
    assert_state(fan_group_state, STATE_OFF)
    for fan_entity in entities_fan_multiple:
        assert_in_attribute(fan_group_state, ATTR_ENTITY_ID, fan_entity.entity_id)

    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_group_entity_id}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(fan_group_entity_id), STATE_ON)
    for fan_entity in entities_fan_multiple:
        assert_state(hass.states.get(fan_entity.entity_id), STATE_ON)

    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_group_entity_id}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(fan_group_entity_id), STATE_OFF)
    for fan_entity in entities_fan_multiple:
        assert_state(hass.states.get(fan_entity.entity_id), STATE_OFF)

    first_fan_entity_id = entities_fan_multiple[0].entity_id
    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: first_fan_entity_id}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(first_fan_entity_id), STATE_ON)
    assert_state(hass.states.get(fan_group_entity_id), STATE_ON)
