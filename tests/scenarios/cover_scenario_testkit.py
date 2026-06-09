"""One-room cover scenario helpers for Magic Areas behavior tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.entities import setup_mock_entities
from tests.helpers.lifecycle import init_integration, shutdown_integration
from tests.helpers.waits import wait_for_state
from tests.mocks import MockBinarySensor, MockCover, MockLight

LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE = "occupancy"
LIGHT_GROUP_ACT_ON_STATE_CHANGE = "state"


class _ScenarioLightGroup(Protocol):
    """Runtime surface used to emit light area-state transitions."""

    category: str

    def area_state_changed(
        self,
        area_id: str,
        states_tuple: tuple[list[str], list[str], list[str]],
    ) -> object:
        """Handle a room-level area-state transition."""


@dataclass(slots=True)
class OneRoomCoverScenario:
    """Scenario surface around one real Magic Areas cover room."""

    hass: HomeAssistant
    config_entry: MockConfigEntry
    blind: MockCover

    @property
    def cover_group_entity_id(self) -> str:
        """Return the scenario blind helper entity id."""
        return (
            f"{COVER_DOMAIN}.magic_areas_cover_groups_"
            f"{DEFAULT_MOCK_AREA}_cover_group_blind"
        )

    @property
    def cover_control_entity_id(self) -> str:
        """Return the scenario cover-control switch entity id."""
        return (
            f"{SWITCH_DOMAIN}.magic_areas_cover_groups_"
            f"{DEFAULT_MOCK_AREA}_cover_control"
        )

    async def enable_cover_control(self) -> None:
        """Enable automatic cover control for the scenario room."""
        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.cover_control_entity_id},
            blocking=True,
        )
        await self.hass.async_block_till_done()

    async def emit_area_state_transition(
        self,
        *,
        new_states: list[AreaStates],
        lost_states: list[AreaStates] | None = None,
        current_states: list[AreaStates] | None = None,
    ) -> None:
        """Emit a Magic Areas room-state transition."""
        dispatcher_send(
            self.hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            DEFAULT_MOCK_AREA.value,
            (
                [state.value for state in new_states],
                [state.value for state in (lost_states or [])],
                [state.value for state in (current_states or new_states)],
            ),
        )
        await self.hass.async_block_till_done()

    async def wait_for_cover_state(self, expected_state: str) -> None:
        """Wait for the grouped cover to reach the expected state."""
        await wait_for_state(
            self.hass,
            self.cover_group_entity_id,
            expected_state,
        )

    async def shutdown(self) -> None:
        """Unload the scenario integration."""
        await shutdown_integration(self.hass, [self.config_entry])


@dataclass(slots=True)
class CoverLightScenario(OneRoomCoverScenario):
    """Cover scenario with adaptive-light context and control."""

    overhead: MockLight
    occupancy: MockBinarySensor
    inside_bright: MockBinarySensor

    @property
    def light_control_entity_id(self) -> str:
        """Return the scenario light-control switch entity id."""
        return (
            f"{SWITCH_DOMAIN}.magic_areas_light_groups_"
            f"{DEFAULT_MOCK_AREA}_light_control"
        )

    @property
    def overhead_light_entity_id(self) -> str:
        """Return the scenario overhead light entity id."""
        assert self.overhead.entity_id is not None
        return self.overhead.entity_id

    def _light_group_runtime(self) -> _ScenarioLightGroup:
        """Return the loaded overhead light-group runtime."""
        controllers = self.config_entry.runtime_data.runtime_controllers or []
        for controller in controllers:
            if getattr(controller, "category", None) == "overhead_lights":
                return cast(_ScenarioLightGroup, controller)
        raise AssertionError("overhead_lights runtime controller not found")

    async def enable_light_control(self) -> None:
        """Enable automatic light control for the scenario room."""
        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.light_control_entity_id},
            blocking=True,
        )
        await self.hass.async_block_till_done()

    async def emit_light_area_state_transition(
        self,
        *,
        new_states: list[AreaStates],
        lost_states: list[AreaStates] | None = None,
        current_states: list[AreaStates] | None = None,
    ) -> None:
        """Emit a room-state transition through the light runtime."""
        self._light_group_runtime().area_state_changed(
            DEFAULT_MOCK_AREA.value,
            (
                [state.value for state in new_states],
                [state.value for state in (lost_states or [])],
                [state.value for state in (current_states or new_states)],
            ),
        )
        await self.hass.async_block_till_done()

    async def wait_for_overhead_state(self, expected_state: str) -> None:
        """Wait for the controlled overhead light state."""
        await wait_for_state(
            self.hass,
            self.overhead_light_entity_id,
            expected_state,
        )


def _cover_config_entry(*, with_adaptive_lights: bool) -> MockConfigEntry:
    """Build the scenario config entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    enabled_features: dict[MagicAreasFeatures, dict[str, object]] = {
        MagicAreasFeatures.COVER_GROUPS: {},
    }
    if with_adaptive_lights:
        enabled_features[MagicAreasFeatures.LIGHT_GROUPS] = {
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: "adaptive",
            CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: (
                "binary_sensor.scenario_inside_bright"
            ),
            "overhead_lights": ["light.scenario_overhead_light"],
            "overhead_lights_states": [AreaStates.OCCUPIED.value],
            "overhead_lights_act_on": [
                LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                LIGHT_GROUP_ACT_ON_STATE_CHANGE,
            ],
            "sleep_lights": [],
            "sleep_lights_states": [],
            "sleep_lights_act_on": [
                LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                LIGHT_GROUP_ACT_ON_STATE_CHANGE,
            ],
            "accent_lights": [],
            "accent_lights_states": [],
            "accent_lights_act_on": [
                LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                LIGHT_GROUP_ACT_ON_STATE_CHANGE,
            ],
            "task_lights": [],
            "task_lights_states": [],
            "task_lights_act_on": [
                LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
                LIGHT_GROUP_ACT_ON_STATE_CHANGE,
            ],
        }
    data[CONF_ENABLED_FEATURES] = enabled_features
    return MockConfigEntry(domain=DOMAIN, data=data)


async def setup_one_room_cover_scenario(
    hass: HomeAssistant,
) -> OneRoomCoverScenario:
    """Set up one room with one blind and cover automation."""
    config_entry = _cover_config_entry(with_adaptive_lights=False)
    blind = MockCover(
        name="scenario_blind",
        unique_id="scenario_blind",
        device_class=CoverDeviceClass.BLIND,
        state=STATE_OPEN,
    )
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: [blind]})
    await init_integration(hass, [config_entry])
    return OneRoomCoverScenario(
        hass=hass,
        config_entry=config_entry,
        blind=blind,
    )


async def setup_cover_light_scenario(
    hass: HomeAssistant,
) -> CoverLightScenario:
    """Set up one room with cover automation and adaptive light control."""
    config_entry = _cover_config_entry(with_adaptive_lights=True)
    overhead = MockLight(
        name="scenario_overhead_light",
        state=STATE_OFF,
        unique_id="scenario_overhead_light",
    )
    occupancy = MockBinarySensor(
        name="scenario_occupancy",
        unique_id="scenario_occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    )
    inside_bright = MockBinarySensor(
        name="scenario_inside_bright",
        unique_id="scenario_inside_bright",
        device_class=BinarySensorDeviceClass.LIGHT,
    )
    blind = MockCover(
        name="scenario_blind",
        unique_id="scenario_blind",
        device_class=CoverDeviceClass.BLIND,
        state=STATE_OPEN,
    )
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: [overhead]})
    await setup_mock_entities(
        hass,
        BINARY_SENSOR_DOMAIN,
        {DEFAULT_MOCK_AREA: [occupancy, inside_bright]},
    )
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: [blind]})
    await init_integration(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    return CoverLightScenario(
        hass=hass,
        config_entry=config_entry,
        blind=blind,
        overhead=overhead,
        occupancy=occupancy,
        inside_bright=inside_bright,
    )
