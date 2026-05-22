"""User-exposed surface contracts for Magic Areas features."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_NAME,
    CONF_ENTITIES,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.config_keys.area import (
    CONF_ENABLED_FEATURES,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.coordinator.pipeline.entity_ingestion import (
    load_area_entities,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
)
from tests.mocks import MockCover, MockFan, MockLight, MockMediaPlayer

GROUP_DOMAIN = "group"
CONF_ACCENT_LIGHTS = "accent_lights"
CONF_OVERHEAD_LIGHTS = "overhead_lights"
CONF_SLEEP_LIGHTS = "sleep_lights"
CONF_TASK_LIGHTS = "task_lights"


def _registry_entry(
    entity_registry: er.EntityRegistry,
    entity_id: str,
) -> er.RegistryEntry:
    """Return an existing registry entry for a user-exposed surface."""
    entry = entity_registry.async_get(entity_id)
    assert entry is not None, f"Missing registry entry for {entity_id}"
    return entry


def _assert_visible_area_device_surface(
    *,
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    entity_id: str,
) -> None:
    """Assert an entity is visible and attached to the Magic Area area/device."""
    state = hass.states.get(entity_id)
    assert state is not None, f"Missing state for {entity_id}"

    entry = _registry_entry(entity_registry, entity_id)
    assert entry.area_id == DEFAULT_MOCK_AREA.value
    assert entry.hidden_by is None
    assert entry.device_id is not None

    device = dr.async_get(hass).async_get(entry.device_id)
    assert device is not None
    assert (
        DOMAIN,
        f"{MAGIC_DEVICE_ID_PREFIX}{DEFAULT_MOCK_AREA.value}",
    ) in device.identifiers


def _helper_entity_id(*, domain: str, title: str) -> str:
    """Return the default entity id HA assigns to a managed helper title."""
    return f"{domain}.{slugify(title)}"


def _assert_group_members(
    hass: HomeAssistant,
    entity_id: str,
    expected_members: Iterable[str],
) -> None:
    """Assert a native group helper exposes the intended member entities."""
    state = hass.states.get(entity_id)
    assert state is not None, f"Missing state for {entity_id}"
    assert set(state.attributes.get(ATTR_ENTITY_ID, ())) == set(expected_members)


async def test_group_control_features_expose_expected_user_surfaces(
    hass: HomeAssistant,
) -> None:
    """Core group/control features should expose their HA-facing surfaces."""
    lights = [
        MockLight("contract_overhead", "off", unique_id="contract_overhead"),
        MockLight("contract_task", "off", unique_id="contract_task"),
        MockLight("contract_sleep", "off", unique_id="contract_sleep"),
        MockLight("contract_accent", "off", unique_id="contract_accent"),
    ]
    fan = MockFan(name="contract_fan", unique_id="contract_fan")
    covers = [
        MockCover(
            name="contract_blind",
            unique_id="contract_blind",
            device_class=CoverDeviceClass.BLIND,
        ),
        MockCover(
            name="contract_shade",
            unique_id="contract_shade",
            device_class=CoverDeviceClass.SHADE,
        ),
    ]
    media_player = MockMediaPlayer(
        name="contract_media_player",
        unique_id="contract_media_player",
    )

    await setup_mock_entities(hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: lights})
    await setup_mock_entities(hass, FAN_DOMAIN, {DEFAULT_MOCK_AREA: [fan]})
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: covers})
    await setup_mock_entities(
        hass,
        MEDIA_PLAYER_DOMAIN,
        {DEFAULT_MOCK_AREA: [media_player]},
    )

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: [lights[0].entity_id],
                    CONF_TASK_LIGHTS: [lights[1].entity_id],
                    CONF_SLEEP_LIGHTS: [lights[2].entity_id],
                    CONF_ACCENT_LIGHTS: [lights[3].entity_id],
                },
                MagicAreasFeatures.FAN_GROUPS: {
                    CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.OCCUPIED,
                    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS: "humidity",
                    CONF_FAN_GROUPS_SETPOINT: 55.0,
                },
                MagicAreasFeatures.COVER_GROUPS: {},
                MagicAreasFeatures.MEDIA_PLAYER_GROUPS: {},
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    await init_integration(hass, [config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    label_registry = lr.async_get(hass)

    expected_helpers = {
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_all_lights": [
            light.entity_id for light in lights
        ],
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights": [
            lights[0].entity_id
        ],
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_task_lights": [
            lights[1].entity_id
        ],
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_sleep_lights": [
            lights[2].entity_id
        ],
        f"{LIGHT_DOMAIN}.magic_areas_native_light_groups_{DEFAULT_MOCK_AREA}_accent_lights": [
            lights[3].entity_id
        ],
        _helper_entity_id(
            domain=FAN_DOMAIN,
            title=f"Magic Areas Fan Groups {data[ATTR_NAME]} Fan Group",
        ): [fan.entity_id],
        _helper_entity_id(
            domain=COVER_DOMAIN,
            title=f"Magic Areas Cover Groups {data[ATTR_NAME]} Cover Group Blind",
        ): [covers[0].entity_id],
        _helper_entity_id(
            domain=COVER_DOMAIN,
            title=f"Magic Areas Cover Groups {data[ATTR_NAME]} Cover Group Shade",
        ): [covers[1].entity_id],
        _helper_entity_id(
            domain=MEDIA_PLAYER_DOMAIN,
            title=(
                f"Magic Areas Media Player Groups {data[ATTR_NAME]} "
                "Media Player Group"
            ),
        ): [media_player.entity_id],
    }
    expected_control_switches = {
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control",
        f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_control",
        f"{SWITCH_DOMAIN}.magic_areas_cover_groups_{DEFAULT_MOCK_AREA}_cover_control",
        (
            f"{SWITCH_DOMAIN}.magic_areas_media_player_groups_"
            f"{DEFAULT_MOCK_AREA}_media_player_control"
        ),
    }

    for entity_id, expected_members in expected_helpers.items():
        _assert_visible_area_device_surface(
            hass=hass,
            entity_registry=entity_registry,
            entity_id=entity_id,
        )
        _assert_group_members(hass, entity_id, expected_members)

    for entity_id in expected_control_switches:
        _assert_visible_area_device_surface(
            hass=hass,
            entity_registry=entity_registry,
            entity_id=entity_id,
        )

    for label_name, member in {
        "ma:overhead": lights[0].entity_id,
        "ma:task": lights[1].entity_id,
        "ma:sleep": lights[2].entity_id,
        "ma:accent": lights[3].entity_id,
    }.items():
        label = label_registry.async_get_label_by_name(label_name)
        assert label is not None, f"Missing label {label_name}"
        assert label.label_id in _registry_entry(entity_registry, member).labels

    legacy_light_groups = {
        entity_id
        for entity_id in hass.states.async_entity_ids(LIGHT_DOMAIN)
        if entity_id.startswith(
            f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_"
        )
    }
    assert legacy_light_groups == set()

    entities, _magic_entities = await load_area_entities(
        hass=hass,
        area_id=DEFAULT_MOCK_AREA.value,
        config_entry_id=config_entry.entry_id,
        config=data,
    )
    for domain, entity_id in {
        LIGHT_DOMAIN: next(
            entity_id
            for entity_id in expected_helpers
            if entity_id.startswith(f"{LIGHT_DOMAIN}.")
        ),
        FAN_DOMAIN: next(
            entity_id
            for entity_id in expected_helpers
            if entity_id.startswith(f"{FAN_DOMAIN}.")
        ),
        COVER_DOMAIN: next(
            entity_id
            for entity_id in expected_helpers
            if entity_id.startswith(f"{COVER_DOMAIN}.")
        ),
        MEDIA_PLAYER_DOMAIN: next(
            entity_id
            for entity_id in expected_helpers
            if entity_id.startswith(f"{MEDIA_PLAYER_DOMAIN}.")
        ),
    }.items():
        assert entity_id not in {
            entity["entity_id"] for entity in entities.get(domain, [])
        }

    helper_config_entries = [
        entry
        for entry in hass.config_entries.async_entries(GROUP_DOMAIN)
        if entry.unique_id
        and entry.unique_id.startswith(f"magic_areas:{config_entry.entry_id}:")
    ]
    for entry in helper_config_entries:
        assert entry.options[CONF_NAME]
        assert entry.options[CONF_ENTITIES]

    await shutdown_integration(hass, [config_entry])
