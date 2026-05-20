"""One-room light scenario helpers for Magic Areas behavior tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, cast

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY,
)
from custom_components.magic_areas.const import ATTR_STATES, DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
)
from tests.mocks import MockBinarySensor, MockLight

LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE = "occupancy"
LIGHT_GROUP_ACT_ON_STATE_CHANGE = "state"
LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY = "advisory"


class ScenarioLightGroup(Protocol):
    """Runtime surface used by scenario tests to emit area-state transitions."""

    category: str
    _attr_extra_state_attributes: dict[str, object]

    def area_state_changed(
        self,
        area_id: str,
        states_tuple: tuple[list[str], list[str], list[str]],
    ) -> object:
        """Handle a room-level area-state transition."""


@dataclass(frozen=True, slots=True)
class LightScenarioSnapshot:
    """Readable room-state snapshot captured at a scenario step."""

    step: str
    occupancy: str | None
    inside_bright: str | None
    area_state: str | None
    area_states: tuple[str, ...]
    control_switch: str | None
    light_group: str | None
    target_light: str | None
    controlling: bool | None
    last_policy_reason: str | None


@dataclass(slots=True)
class OneRoomLightScenario:
    """Small one-room scenario surface around real Magic Areas setup."""

    hass: HomeAssistant
    config_entry: MockConfigEntry
    occupancy_sensor: MockBinarySensor
    inside_bright_sensor: MockBinarySensor
    target_light: MockLight
    secondary_light: MockLight | None = None
    trace: list[LightScenarioSnapshot] = field(default_factory=list)

    @property
    def occupancy_entity_id(self) -> str:
        """Return the occupancy entity id."""
        assert self.occupancy_sensor.entity_id is not None
        return self.occupancy_sensor.entity_id

    @property
    def inside_bright_entity_id(self) -> str:
        """Return the in-room bright entity id."""
        assert self.inside_bright_sensor.entity_id is not None
        return self.inside_bright_sensor.entity_id

    @property
    def target_light_entity_id(self) -> str:
        """Return the controlled light entity id."""
        assert self.target_light.entity_id is not None
        return self.target_light.entity_id

    @property
    def secondary_light_entity_id(self) -> str:
        """Return the secondary room light entity id."""
        assert self.secondary_light is not None
        assert self.secondary_light.entity_id is not None
        return self.secondary_light.entity_id

    @property
    def area_state_entity_id(self) -> str:
        """Return the Magic Areas area-state entity id."""
        return (
            f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_"
            f"{DEFAULT_MOCK_AREA}_area_state"
        )

    @property
    def light_group_entity_id(self) -> str:
        """Return the native helper light-group entity id."""
        return (
            f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_"
            f"{DEFAULT_MOCK_AREA}_overhead_lights"
        )

    @property
    def light_control_entity_id(self) -> str:
        """Return the Magic Areas light-control switch entity id."""
        return (
            f"{SWITCH_DOMAIN}.magic_areas_light_groups_"
            f"{DEFAULT_MOCK_AREA}_light_control"
        )

    def light_group_state(self) -> State | None:
        """Return the current HA state for the policy light group."""
        return self.hass.states.get(self.light_group_entity_id)

    def adaptive_guards(self) -> dict[str, object]:
        """Return the latest adaptive guard diagnostics from the light group."""
        guards = self.light_group_entity()._attr_extra_state_attributes.get(
            "adaptive_guards",
            {},
        )
        return dict(guards) if isinstance(guards, dict) else {}

    def light_group_entity(self) -> ScenarioLightGroup:
        """Return the loaded Magic Areas non-entity light-group runtime."""
        controllers = self.config_entry.runtime_data.runtime_controllers or []
        for controller in controllers:
            if getattr(controller, "category", None) == "overhead_lights":
                return cast(ScenarioLightGroup, controller)
        raise AssertionError("overhead_lights runtime controller not found")

    async def enable_light_control(self) -> None:
        """Enable Magic Areas automatic light control for the room."""
        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.light_control_entity_id},
            blocking=True,
        )
        await self.hass.async_block_till_done()
        self.snapshot("light control enabled")

    async def set_inside_bright(self, state: str) -> None:
        """Set the explicit in-room brightness binary signal."""
        if state == STATE_ON:
            self.inside_bright_sensor.turn_on()
            self.hass.states.async_set(self.inside_bright_entity_id, STATE_ON)
        elif state == STATE_OFF:
            self.inside_bright_sensor.turn_off()
            self.hass.states.async_set(self.inside_bright_entity_id, STATE_OFF)
        elif state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            self.hass.states.async_set(self.inside_bright_entity_id, state)
        else:
            raise ValueError(f"Unsupported inside-bright state: {state}")
        await self.hass.async_block_till_done()
        self.snapshot(f"inside bright -> {state}")

    async def set_occupied(self, occupied: bool) -> None:
        """Set the room occupancy signal."""
        if occupied:
            self.occupancy_sensor.turn_on()
        else:
            self.occupancy_sensor.turn_off()
        await self.hass.async_block_till_done()
        self.snapshot(f"occupied -> {occupied}")

    async def emit_area_state_transition(
        self,
        *,
        new_states: list[AreaStates],
        lost_states: list[AreaStates] | None = None,
        current_states: list[AreaStates] | None = None,
        step: str,
    ) -> bool:
        """Send a room-level area-state transition through the light-group runtime."""
        target_group = self.light_group_entity()
        result = target_group.area_state_changed(
            DEFAULT_MOCK_AREA.value,
            (
                [state.value for state in new_states],
                [state.value for state in (lost_states or [])],
                [state.value for state in (current_states or new_states)],
            ),
        )
        await self.hass.async_block_till_done()
        self.snapshot(step)
        return bool(result)

    def snapshot(self, step: str) -> LightScenarioSnapshot:
        """Capture current room state for assertion diagnostics."""
        area_state = self.hass.states.get(self.area_state_entity_id)
        light_group = self.hass.states.get(self.light_group_entity_id)
        light_runtime = self.light_group_entity()
        runtime_attrs = light_runtime._attr_extra_state_attributes
        occupancy = self.hass.states.get(self.occupancy_entity_id)
        inside_bright = self.hass.states.get(self.inside_bright_entity_id)
        control_switch = self.hass.states.get(self.light_control_entity_id)
        target_light = self.hass.states.get(self.target_light_entity_id)
        area_states = area_state.attributes.get(ATTR_STATES, ()) if area_state else ()
        if not isinstance(area_states, list | tuple):
            area_states = ()
        snapshot = LightScenarioSnapshot(
            step=step,
            occupancy=occupancy.state if occupancy else None,
            inside_bright=inside_bright.state if inside_bright else None,
            area_state=area_state.state if area_state else None,
            area_states=tuple(str(state) for state in area_states),
            control_switch=control_switch.state if control_switch else None,
            light_group=light_group.state if light_group else None,
            target_light=target_light.state if target_light else None,
            controlling=(
                bool(runtime_attrs["controlling"])
                if "controlling" in runtime_attrs
                else None
            ),
            last_policy_reason=(
                str(runtime_attrs["last_policy_reason"])
                if "last_policy_reason" in runtime_attrs
                else None
            ),
        )
        self.trace.append(snapshot)
        return snapshot


async def setup_one_room_advisory_light_scenario(
    hass: HomeAssistant,
    *,
    include_secondary_light_as: str | None = None,
    secondary_light_initial_state: str = STATE_OFF,
    secondary_light_initial_brightness: int | None = None,
    light_group_config_overrides: dict[str, object] | None = None,
) -> OneRoomLightScenario:
    """Set up one real Magic Areas room configured for advisory brightness."""
    target_light = MockLight(
        name="scenario_overhead_light",
        state=STATE_OFF,
        unique_id="scenario_overhead_light",
    )
    secondary_light = MockLight(
        name="scenario_secondary_light",
        state=secondary_light_initial_state,
        unique_id="scenario_secondary_light",
        dimmable=secondary_light_initial_brightness is not None,
    )
    if secondary_light_initial_brightness is not None:
        secondary_light.brightness = secondary_light_initial_brightness
    occupancy_sensor = MockBinarySensor(
        name="scenario_occupancy",
        unique_id="scenario_occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    )
    inside_bright_sensor = MockBinarySensor(
        name="scenario_inside_bright",
        unique_id="scenario_inside_bright",
        device_class=BinarySensorDeviceClass.LIGHT,
    )

    await setup_mock_entities(
        hass,
        LIGHT_DOMAIN,
        {DEFAULT_MOCK_AREA: [target_light, secondary_light]},
    )
    await setup_mock_entities(
        hass,
        BINARY_SENSOR_DOMAIN,
        {DEFAULT_MOCK_AREA: [occupancy_sensor, inside_bright_sensor]},
    )

    assert target_light.entity_id is not None
    assert secondary_light.entity_id is not None
    assert inside_bright_sensor.entity_id is not None

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    light_group_config: dict[str, object] = {
        CONF_LIGHT_GROUP_BRIGHTNESS_MODE: LIGHT_GROUP_BRIGHTNESS_MODE_ADVISORY,
        CONF_LIGHT_GROUP_INSIDE_BRIGHT_ENTITY: inside_bright_sensor.entity_id,
        "overhead_lights": [target_light.entity_id],
        "overhead_lights_states": ["occupied"],
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
    if include_secondary_light_as:
        light_group_config[include_secondary_light_as] = [secondary_light.entity_id]
    if light_group_config_overrides:
        light_group_config.update(light_group_config_overrides)

    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            **light_group_config,
        }
    }
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=DEFAULT_MOCK_AREA.value,
    )
    await init_integration(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    scenario = OneRoomLightScenario(
        hass=hass,
        config_entry=config_entry,
        occupancy_sensor=occupancy_sensor,
        inside_bright_sensor=inside_bright_sensor,
        target_light=target_light,
        secondary_light=secondary_light,
    )
    scenario.snapshot("initial setup")
    return scenario
