"""Probe Home Assistant native group helper lifecycle for managed surfaces."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.components.statistics import DOMAIN as STATISTICS_DOMAIN
from homeassistant.components.statistics.sensor import STAT_CHANGE
from homeassistant.components.threshold.const import (
    CONF_HYSTERESIS,
    CONF_LOWER,
    CONF_UPPER,
)
from homeassistant.components.trend.const import DOMAIN as TREND_DOMAIN
from homeassistant.components.derivative.const import DOMAIN as DERIVATIVE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITIES,
    CONF_ENTITY_ID,
    CONF_NAME,
    LIGHT_LUX,
    Platform,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import label_registry as lr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN, MANAGED_LABEL_SURFACES_DATA_KEY
from custom_components.magic_areas.coordinator import (
    async_reconcile_config_entry_helpers,
    async_reconcile_label_surfaces,
)
from custom_components.magic_areas.coordinator.managed_surfaces import (
    _surface_repair_issue_id,
)
from custom_components.magic_areas.coordinator.pipeline.entity_ingestion import (
    load_area_entities,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    LabelSurface,
    ManagedSurfaceKind,
    derivative_signal_surface,
    duration_dict,
    statistics_signal_surface,
    trend_signal_surface,
    build_managed_surface_unique_id,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import setup_mock_entities
from tests.mocks import MockCover, MockLight, MockSensor

GROUP_DOMAIN = "group"
THRESHOLD_DOMAIN = "threshold"


async def test_reconciler_manages_scoped_label_membership(
    hass: HomeAssistant,
) -> None:
    """Label reconciliation should preserve unrelated labels and prune only scope."""
    lights = [
        MockLight("overhead_1", "off", unique_id="label_overhead_1"),
        MockLight("task_1", "off", unique_id="label_task_1"),
        MockLight("other_1", "off", unique_id="label_other_1"),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    entity_registry = er.async_get(hass)
    label_registry = lr.async_get(hass)
    user_label = label_registry.async_create("User Label")
    entity_registry.async_update_entity(
        lights[0].entity_id,
        labels={user_label.label_id},
    )

    async_reconcile_label_surfaces(
        hass=hass,
        desired_surfaces=[
            LabelSurface(
                name="ma:overhead",
                entity_ids=(lights[0].entity_id,),
                prune_entity_ids=tuple(light.entity_id for light in lights),
            ),
            LabelSurface(
                name="ma:task",
                entity_ids=(lights[1].entity_id,),
                prune_entity_ids=tuple(light.entity_id for light in lights),
            ),
        ],
    )

    overhead_label = label_registry.async_get_label_by_name("ma:overhead")
    task_label = label_registry.async_get_label_by_name("ma:task")
    assert overhead_label is not None
    assert task_label is not None
    assert overhead_label.label_id in entity_registry.async_get(lights[0].entity_id).labels
    assert task_label.label_id in entity_registry.async_get(lights[1].entity_id).labels
    assert user_label.label_id in entity_registry.async_get(lights[0].entity_id).labels

    async_reconcile_label_surfaces(
        hass=hass,
        desired_surfaces=[
            LabelSurface(
                name="ma:overhead",
                entity_ids=(lights[2].entity_id,),
                prune_entity_ids=tuple(light.entity_id for light in lights),
            ),
            LabelSurface(
                name="ma:task",
                entity_ids=(),
                prune_entity_ids=tuple(light.entity_id for light in lights),
            ),
        ],
    )

    assert overhead_label.label_id not in entity_registry.async_get(
        lights[0].entity_id
    ).labels
    assert overhead_label.label_id in entity_registry.async_get(lights[2].entity_id).labels
    assert task_label.label_id not in entity_registry.async_get(lights[1].entity_id).labels
    assert user_label.label_id in entity_registry.async_get(lights[0].entity_id).labels


async def test_reconciler_clears_deleted_owner_label_surfaces(
    hass: HomeAssistant,
) -> None:
    """Deleted managed labels should prune only memberships owned by that entry."""
    lights = [
        MockLight("owner_1_task", "off", unique_id="owner_1_task"),
        MockLight("owner_2_task", "off", unique_id="owner_2_task"),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    owner_1 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="label_owner_1",
        title="Kitchen",
        unique_id="label-owner-1",
    )
    owner_2 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="label_owner_2",
        title="Office",
        unique_id="label-owner-2",
    )
    owner_1.add_to_hass(hass)
    owner_2.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    label_registry = lr.async_get(hass)

    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner_1.entry_id,
        desired_surfaces=[
            LabelSurface(
                name="ma:control:task",
                entity_ids=(lights[0].entity_id,),
                prune_entity_ids=(lights[0].entity_id,),
            ),
        ],
    )
    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner_2.entry_id,
        desired_surfaces=[
            LabelSurface(
                name="ma:control:task",
                entity_ids=(lights[1].entity_id,),
                prune_entity_ids=(lights[1].entity_id,),
            ),
        ],
    )

    task_label = label_registry.async_get_label_by_name("ma:control:task")
    assert task_label is not None
    assert task_label.label_id in entity_registry.async_get(lights[0].entity_id).labels
    assert task_label.label_id in entity_registry.async_get(lights[1].entity_id).labels

    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner_1.entry_id,
        desired_surfaces=[],
    )

    assert task_label.label_id not in entity_registry.async_get(lights[0].entity_id).labels
    assert task_label.label_id in entity_registry.async_get(lights[1].entity_id).labels
    assert label_registry.async_get_label_by_name("ma:control:task") is not None
    assert owner_1.data[MANAGED_LABEL_SURFACES_DATA_KEY] == {}

    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner_2.entry_id,
        desired_surfaces=[],
    )

    assert task_label.label_id not in entity_registry.async_get(lights[1].entity_id).labels
    assert label_registry.async_get_label_by_name("ma:control:task") is None
    assert owner_2.data[MANAGED_LABEL_SURFACES_DATA_KEY] == {}


async def test_reconciler_prunes_previous_owner_members_for_retained_label(
    hass: HomeAssistant,
) -> None:
    """Retained labels should still prune members previously owned by this entry."""
    lights = [
        MockLight("previous_task", "off", unique_id="previous_task"),
        MockLight("current_task", "off", unique_id="current_task"),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    owner = MockConfigEntry(
        domain=DOMAIN,
        entry_id="label_owner_retained",
        title="Kitchen",
        unique_id="label-owner-retained",
    )
    owner.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    label_registry = lr.async_get(hass)

    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner.entry_id,
        desired_surfaces=[
            LabelSurface(
                name="ma:control:reading",
                entity_ids=(lights[0].entity_id,),
                prune_entity_ids=(),
            ),
        ],
    )

    reading_label = label_registry.async_get_label_by_name("ma:control:reading")
    assert reading_label is not None
    assert reading_label.label_id in entity_registry.async_get(lights[0].entity_id).labels

    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner.entry_id,
        desired_surfaces=[
            LabelSurface(
                name="ma:control:reading",
                entity_ids=(lights[1].entity_id,),
                prune_entity_ids=(),
            ),
        ],
    )

    assert reading_label.label_id not in entity_registry.async_get(
        lights[0].entity_id
    ).labels
    assert reading_label.label_id in entity_registry.async_get(lights[1].entity_id).labels


def _managed_group_entry(
    *,
    entry_id: str,
    unique_id: str,
    name: str,
    entities: list[str],
) -> ConfigEntry[object]:
    """Build the shape a Magic Areas reconciler would manage."""
    return ConfigEntry(
        data={},
        discovery_keys=MappingProxyType({}),
        domain=GROUP_DOMAIN,
        entry_id=entry_id,
        minor_version=1,
        options={
            "group_type": Platform.COVER,
            CONF_NAME: name,
            CONF_ENTITIES: entities,
            "hide_members": False,
        },
        source="import",
        subentries_data=(),
        title=name,
        unique_id=unique_id,
        version=1,
    )


async def test_managed_cover_group_config_entry_lifecycle(
    hass: HomeAssistant,
) -> None:
    """A managed native cover group can be created, updated, reloaded, removed."""
    covers = [
        MockCover(
            name="left_blind",
            unique_id="left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="right_blind",
            unique_id="right_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="shade",
            unique_id="shade",
            device_class=CoverDeviceClass.SHADE,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})

    entry = _managed_group_entry(
        entry_id="magic_areas_cover_group_living_room_blinds",
        unique_id="magic_areas:entry:living_room:cover_groups:group_helper:blind",
        name="Magic Areas Living Room Blinds",
        entities=[covers[0].entity_id, covers[1].entity_id],
    )

    await hass.config_entries.async_add(entry)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entity_registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    )
    assert len(registry_entries) == 1

    group_entity_id = registry_entries[0].entity_id
    assert group_entity_id.startswith(f"{COVER_DOMAIN}.")
    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert set(group_state.attributes[ATTR_ENTITY_ID]) == {
        covers[0].entity_id,
        covers[1].entity_id,
    }

    hass.config_entries.async_update_entry(
        entry,
        options={
            **entry.options,
            CONF_ENTITIES: [covers[2].entity_id],
        },
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert group_state.attributes[ATTR_ENTITY_ID] == [covers[2].entity_id]

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(group_entity_id) is None
    assert not er.async_entries_for_config_entry(entity_registry, entry.entry_id)


async def test_reconciler_manages_cover_group_helper_lifecycle(
    hass: HomeAssistant,
) -> None:
    """The Magic Areas reconciler creates, updates, and removes helper entries."""
    covers = [
        MockCover(
            name="left_blind",
            unique_id="reconcile_left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="right_blind",
            unique_id="reconcile_right_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="shade",
            unique_id="reconcile_shade",
            device_class=CoverDeviceClass.SHADE,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})
    owner_entry_id = "magic_area_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Kitchen",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="cover_groups",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="cover_group_blind",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=GROUP_DOMAIN,
                title="Magic Areas Living Room Blinds",
                options={
                    "group_type": Platform.COVER,
                    CONF_NAME: "Magic Areas Living Room Blinds",
                    CONF_ENTITIES: [covers[0].entity_id, covers[1].entity_id],
                    "hide_members": False,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Kitchen",
            )
        ],
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entry = next(
        entry
        for entry in hass.config_entries.async_entries(GROUP_DOMAIN)
        if entry.unique_id == unique_id
    )
    group_entity_id = er.async_entries_for_config_entry(entity_registry, entry.entry_id)[
        0
    ].entity_id
    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert set(group_state.attributes[ATTR_ENTITY_ID]) == {
        covers[0].entity_id,
        covers[1].entity_id,
    }
    group_registry_entry = entity_registry.async_get(group_entity_id)
    assert group_registry_entry is not None
    assert group_registry_entry.area_id == DEFAULT_MOCK_AREA.value
    assert group_registry_entry.device_id is not None
    device = dr.async_get(hass).async_get(group_registry_entry.device_id)
    assert device is not None
    assert (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}") in device.identifiers

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=GROUP_DOMAIN,
                title="Magic Areas Living Room Shades",
                options={
                    "group_type": Platform.COVER,
                    CONF_NAME: "Magic Areas Living Room Shades",
                    CONF_ENTITIES: [covers[2].entity_id],
                    "hide_members": False,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Kitchen",
            )
        ],
    )
    await hass.async_block_till_done()

    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert group_state.attributes[ATTR_ENTITY_ID] == [covers[2].entity_id]
    entities, _magic_entities = await load_area_entities(
        hass=hass,
        area_id=DEFAULT_MOCK_AREA.value,
        config_entry_id=owner_entry_id,
        config={},
    )
    assert group_entity_id not in {
        entity["entity_id"] for entity in entities.get(COVER_DOMAIN, [])
    }

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )
    await hass.async_block_till_done()

    assert hass.states.get(group_entity_id) is None


async def test_reconciler_manages_light_group_helper_lifecycle(
    hass: HomeAssistant,
) -> None:
    """Managed native light group helpers can be reconciled and excluded."""
    lights = [
        MockLight(
            name="overhead_light",
            state="off",
            unique_id="native_helper_overhead_light",
        ),
        MockLight(
            name="task_light",
            state="off",
            unique_id="native_helper_task_light",
        ),
    ]
    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    owner_entry_id = "magic_area_light_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Kitchen",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="light_groups",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="light_group_overhead_lights",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=GROUP_DOMAIN,
                title="Magic Areas Native Light Groups Kitchen Overhead Lights",
                options={
                    "group_type": Platform.LIGHT,
                    CONF_NAME: "Magic Areas Native Light Groups Kitchen Overhead Lights",
                    CONF_ENTITIES: [lights[0].entity_id],
                    "hide_members": False,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Kitchen",
            )
        ],
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entry = next(
        entry
        for entry in hass.config_entries.async_entries(GROUP_DOMAIN)
        if entry.unique_id == unique_id
    )
    group_registry_entry = er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    )[0]
    group_entity_id = group_registry_entry.entity_id
    assert group_entity_id.startswith(f"{LIGHT_DOMAIN}.")
    assert group_registry_entry.area_id == DEFAULT_MOCK_AREA.value
    assert group_registry_entry.device_id is not None

    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert group_state.attributes[ATTR_ENTITY_ID] == [lights[0].entity_id]

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=GROUP_DOMAIN,
                title="Magic Areas Native Light Groups Kitchen Task Lights",
                options={
                    "group_type": Platform.LIGHT,
                    CONF_NAME: "Magic Areas Native Light Groups Kitchen Task Lights",
                    CONF_ENTITIES: [lights[1].entity_id],
                    "hide_members": False,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Kitchen",
            )
        ],
    )
    await hass.async_block_till_done()

    group_state = hass.states.get(group_entity_id)
    assert group_state is not None
    assert group_state.attributes[ATTR_ENTITY_ID] == [lights[1].entity_id]
    entities, _magic_entities = await load_area_entities(
        hass=hass,
        area_id=DEFAULT_MOCK_AREA.value,
        config_entry_id=owner_entry_id,
        config={},
    )
    assert group_entity_id not in {
        entity["entity_id"] for entity in entities.get(LIGHT_DOMAIN, [])
    }

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )
    await hass.async_block_till_done()

    assert hass.states.get(group_entity_id) is None


async def test_reconciler_manages_threshold_helper_lifecycle(
    hass: HomeAssistant,
) -> None:
    """The reconciler manages native threshold helpers with metadata/exclusion."""
    source_sensor = MockSensor(
        name="living_room_lux",
        unique_id="living_room_lux",
        native_value=250,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        unit_of_measurement=LIGHT_LUX,
    )
    await setup_mock_entities(
        hass,
        SENSOR_DOMAIN,
        {DEFAULT_MOCK_AREA: [source_sensor]},
    )
    owner_entry_id = "magic_area_threshold_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Living Room",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="threshold",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="threshold_light",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            ConfigEntryHelperSurface(
                unique_id=unique_id,
                domain=THRESHOLD_DOMAIN,
                title="Magic Areas Threshold Living Room Threshold Light",
                options={
                    CONF_NAME: "Magic Areas Threshold Living Room Threshold Light",
                    CONF_ENTITY_ID: source_sensor.entity_id,
                    CONF_HYSTERESIS: 10.0,
                    CONF_LOWER: None,
                    CONF_UPPER: 100.0,
                },
                area_id=DEFAULT_MOCK_AREA.value,
                device_identifier=(
                    DOMAIN,
                    f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
                ),
                device_name="Living Room",
                device_class=BinarySensorDeviceClass.LIGHT,
            )
        ],
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entry = next(
        entry
        for entry in hass.config_entries.async_entries(THRESHOLD_DOMAIN)
        if entry.unique_id == unique_id
    )
    threshold_registry_entry = er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    )[0]
    threshold_entity_id = threshold_registry_entry.entity_id
    assert threshold_entity_id.startswith(f"{BINARY_SENSOR_DOMAIN}.")
    assert threshold_registry_entry.area_id == DEFAULT_MOCK_AREA.value
    assert threshold_registry_entry.device_id is not None
    assert threshold_registry_entry.device_class == BinarySensorDeviceClass.LIGHT

    device = dr.async_get(hass).async_get(threshold_registry_entry.device_id)
    assert device is not None
    assert (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}") in device.identifiers

    threshold_state = hass.states.get(threshold_entity_id)
    assert threshold_state is not None

    entities, _magic_entities = await load_area_entities(
        hass=hass,
        area_id=DEFAULT_MOCK_AREA.value,
        config_entry_id=owner_entry_id,
        config={},
    )
    assert threshold_entity_id not in {
        entity["entity_id"] for entity in entities.get(BINARY_SENSOR_DOMAIN, [])
    }

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )
    await hass.async_block_till_done()

    assert hass.states.get(threshold_entity_id) is None


async def test_reconciler_manages_signal_helper_lifecycle(
    hass: HomeAssistant,
) -> None:
    """Signal helpers reconcile as managed native helpers with metadata/exclusion."""
    source_sensor = MockSensor(
        name="living_room_signal_lux",
        unique_id="living_room_signal_lux",
        native_value=250,
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        unit_of_measurement=LIGHT_LUX,
    )
    await setup_mock_entities(
        hass,
        SENSOR_DOMAIN,
        {DEFAULT_MOCK_AREA: [source_sensor]},
    )
    owner_entry_id = "magic_area_signal_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Living Room",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    device_identifier = (
        DOMAIN,
        f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
    )
    trend_surface = trend_signal_surface(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        area_name="Living Room",
        role="ambient_rise",
        source_entity_id=source_sensor.entity_id,
        min_gradient=0.25,
        sample_duration=120,
        max_samples=8,
        min_samples=3,
        device_identifier=device_identifier,
        device_name="Living Room",
    )
    statistics_surface = statistics_signal_surface(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        area_name="Living Room",
        role="lux_change",
        source_entity_id=source_sensor.entity_id,
        state_characteristic=STAT_CHANGE,
        max_age=duration_dict(minutes=15),
        samples_max_buffer_size=20,
        keep_last_sample=True,
        precision=1,
        device_identifier=device_identifier,
        device_name="Living Room",
    )
    derivative_surface = derivative_signal_surface(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        area_name="Living Room",
        role="lux_rate",
        source_entity_id=source_sensor.entity_id,
        time_window=duration_dict(minutes=5),
        round_digits=3,
        unit_time=UnitOfTime.MINUTES,
        device_identifier=device_identifier,
        device_name="Living Room",
    )
    surfaces = [trend_surface, statistics_surface, derivative_surface]

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=surfaces,
    )
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    helper_entity_ids: set[str] = set()
    for surface in surfaces:
        entry = next(
            entry
            for entry in hass.config_entries.async_entries(surface.domain)
            if entry.unique_id == surface.unique_id
        )
        assert entry.state is ConfigEntryState.LOADED
        assert entry.options == surface.options
        registry_entries = er.async_entries_for_config_entry(
            entity_registry,
            entry.entry_id,
        )
        assert len(registry_entries) == 1
        registry_entry = registry_entries[0]
        helper_entity_ids.add(registry_entry.entity_id)
        assert registry_entry.area_id == DEFAULT_MOCK_AREA.value
        assert registry_entry.device_id is not None
        device = device_registry.async_get(registry_entry.device_id)
        assert device is not None
        assert device_identifier in device.identifiers
        assert hass.states.get(registry_entry.entity_id) is not None

    assert {
        entry.domain
        for entry in hass.config_entries.async_entries()
        if entry.unique_id in {surface.unique_id for surface in surfaces}
    } == {TREND_DOMAIN, STATISTICS_DOMAIN, DERIVATIVE_DOMAIN}

    updated_trend_surface = trend_signal_surface(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        area_name="Living Room",
        role="ambient_rise",
        source_entity_id=source_sensor.entity_id,
        min_gradient=0.5,
        sample_duration=180,
        max_samples=10,
        min_samples=4,
        device_identifier=device_identifier,
        device_name="Living Room",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            updated_trend_surface,
            statistics_surface,
            derivative_surface,
        ],
    )
    await hass.async_block_till_done()

    trend_entry = next(
        entry
        for entry in hass.config_entries.async_entries(TREND_DOMAIN)
        if entry.unique_id == trend_surface.unique_id
    )
    assert trend_entry.options == updated_trend_surface.options

    entities, _magic_entities = await load_area_entities(
        hass=hass,
        area_id=DEFAULT_MOCK_AREA.value,
        config_entry_id=owner_entry_id,
        config={},
    )
    enumerated_sensor_ids = {
        entity["entity_id"] for entity in entities.get(SENSOR_DOMAIN, [])
    }
    enumerated_binary_sensor_ids = {
        entity["entity_id"] for entity in entities.get(BINARY_SENSOR_DOMAIN, [])
    }
    assert helper_entity_ids.isdisjoint(enumerated_sensor_ids)
    assert helper_entity_ids.isdisjoint(enumerated_binary_sensor_ids)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )
    await hass.async_block_till_done()

    for entity_id in helper_entity_ids:
        assert hass.states.get(entity_id) is None


async def test_reconciler_reports_and_clears_managed_surface_repair(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reconciliation failures are visible through Repairs and clear on success."""
    covers = [
        MockCover(
            name="repair_left_blind",
            unique_id="repair_left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})
    owner_entry_id = "magic_area_repair_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Living Room",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="cover_groups",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="cover_group_blind",
    )
    surface = ConfigEntryHelperSurface(
        unique_id=unique_id,
        domain=GROUP_DOMAIN,
        title="Magic Areas Living Room Blinds",
        options={
            "group_type": Platform.COVER,
            CONF_NAME: "Magic Areas Living Room Blinds",
            CONF_ENTITIES: [covers[0].entity_id],
            "hide_members": False,
        },
        area_id=DEFAULT_MOCK_AREA.value,
        device_identifier=(
            DOMAIN,
            f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
        ),
        device_name="Living Room",
    )
    original_async_add = hass.config_entries.async_add

    async def fail_async_add(entry: ConfigEntry[object]) -> None:
        raise RuntimeError("helper create failed")

    monkeypatch.setattr(hass.config_entries, "async_add", fail_async_add)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[surface],
    )

    issue_registry = ir.async_get(hass)
    issue_id = _surface_repair_issue_id(unique_id)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == "managed_surface_reconciliation_failed"
    assert issue.translation_placeholders == {
        "action": "create",
        "domain": GROUP_DOMAIN,
        "surface": "Magic Areas Living Room Blinds",
        "error": "RuntimeError: helper create failed",
    }

    monkeypatch.setattr(hass.config_entries, "async_add", original_async_add)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[surface],
    )
    await hass.async_block_till_done()

    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_reconciler_reports_and_clears_update_repair(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed-surface update failures are repaired and then cleared."""
    covers = [
        MockCover(
            name="repair_update_left_blind",
            unique_id="repair_update_left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="repair_update_right_blind",
            unique_id="repair_update_right_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})
    owner_entry_id = "magic_area_update_repair_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Living Room",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="cover_groups",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="cover_group_blind",
    )
    original_surface = ConfigEntryHelperSurface(
        unique_id=unique_id,
        domain=GROUP_DOMAIN,
        title="Magic Areas Living Room Blinds",
        options={
            "group_type": Platform.COVER,
            CONF_NAME: "Magic Areas Living Room Blinds",
            CONF_ENTITIES: [covers[0].entity_id],
            "hide_members": False,
        },
        area_id=DEFAULT_MOCK_AREA.value,
        device_identifier=(
            DOMAIN,
            f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
        ),
        device_name="Living Room",
    )
    updated_surface = ConfigEntryHelperSurface(
        unique_id=unique_id,
        domain=GROUP_DOMAIN,
        title="Magic Areas Living Room Shades",
        options={
            "group_type": Platform.COVER,
            CONF_NAME: "Magic Areas Living Room Shades",
            CONF_ENTITIES: [covers[1].entity_id],
            "hide_members": False,
        },
        area_id=DEFAULT_MOCK_AREA.value,
        device_identifier=(
            DOMAIN,
            f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
        ),
        device_name="Living Room",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[original_surface],
    )
    await hass.async_block_till_done()

    original_async_reload = hass.config_entries.async_reload

    async def fail_async_reload(entry_id: str) -> bool:
        raise RuntimeError("helper reload failed")

    monkeypatch.setattr(hass.config_entries, "async_reload", fail_async_reload)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[updated_surface],
    )

    issue_registry = ir.async_get(hass)
    issue_id = _surface_repair_issue_id(unique_id)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {
        "action": "update",
        "domain": GROUP_DOMAIN,
        "surface": "Magic Areas Living Room Shades",
        "error": "RuntimeError: helper reload failed",
    }

    monkeypatch.setattr(hass.config_entries, "async_reload", original_async_reload)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[updated_surface],
    )
    await hass.async_block_till_done()

    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_reconciler_reports_and_clears_stale_removal_repair(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed-surface removal failures are repaired and then cleared."""
    covers = [
        MockCover(
            name="repair_remove_left_blind",
            unique_id="repair_remove_left_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
    ]
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})
    owner_entry_id = "magic_area_remove_repair_owner"
    MockConfigEntry(
        domain=DOMAIN,
        entry_id=owner_entry_id,
        title="Living Room",
        unique_id=DEFAULT_MOCK_AREA.value,
    ).add_to_hass(hass)
    unique_id = build_managed_surface_unique_id(
        entry_id=owner_entry_id,
        area_id=DEFAULT_MOCK_AREA.value,
        feature_id="cover_groups",
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="cover_group_blind",
    )
    surface = ConfigEntryHelperSurface(
        unique_id=unique_id,
        domain=GROUP_DOMAIN,
        title="Magic Areas Living Room Blinds",
        options={
            "group_type": Platform.COVER,
            CONF_NAME: "Magic Areas Living Room Blinds",
            CONF_ENTITIES: [covers[0].entity_id],
            "hide_members": False,
        },
        area_id=DEFAULT_MOCK_AREA.value,
        device_identifier=(
            DOMAIN,
            f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
        ),
        device_name="Living Room",
    )

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[surface],
    )
    await hass.async_block_till_done()

    original_async_remove = hass.config_entries.async_remove

    async def fail_async_remove(entry_id: str) -> bool:
        raise RuntimeError("helper remove failed")

    monkeypatch.setattr(hass.config_entries, "async_remove", fail_async_remove)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )

    issue_registry = ir.async_get(hass)
    issue_id = _surface_repair_issue_id(unique_id)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {
        "action": "remove",
        "domain": GROUP_DOMAIN,
        "surface": "Magic Areas Living Room Blinds",
        "error": "RuntimeError: helper remove failed",
    }

    monkeypatch.setattr(hass.config_entries, "async_remove", original_async_remove)

    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[],
    )
    await hass.async_block_till_done()

    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None
