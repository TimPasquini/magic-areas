"""Selector overrides for schema-backed feature config pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_COVER_GROUPS_ACCENT_ACTION,
    CONF_COVER_GROUPS_ACCENT_STATES,
    CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES,
    CONF_COVER_GROUPS_DAYLIGHT_ACTION,
    CONF_COVER_GROUPS_DAYLIGHT_STATES,
    CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS,
    CONF_COVER_GROUPS_PRIVACY_ACTION,
    CONF_COVER_GROUPS_PRIVACY_STATES,
)
from custom_components.magic_areas.config_flows.base import SelectorMap
from custom_components.magic_areas.config_flows.selector_builders import (
    build_selector_entity_simple,
    build_selector_number,
    build_selector_select,
)
from custom_components.magic_areas.core.controls.policies.cover import (
    DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES,
    CoverPresetAction,
)
from custom_components.magic_areas.enums import (
    MagicAreasFeatures,
    SelectorTranslationKeys,
)
from custom_components.magic_areas.features.config.readers import (
    AGGREGATES_OPTION_KEYS,
    AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS,
    BLE_TRACKER_OPTION_KEYS,
    CLIMATE_CONTROL_ENTITY_KEY,
    FAN_GROUPS_OPTION_KEYS,
    HEALTH_OPTION_KEYS,
    PRESENCE_HOLD_OPTION_KEYS,
    WASP_IN_A_BOX_OPTION_KEYS,
)
from custom_components.magic_areas.policy import (
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    ALL_SENSOR_DEVICE_CLASSES,
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.config_flows.options_flow import (
        OptionsFlowHandler,
    )

_NUMERIC_SELECTOR_MAX = 120_000
_COVER_PRESET_ACTION_KEYS = (
    CONF_COVER_GROUPS_DAYLIGHT_ACTION,
    CONF_COVER_GROUPS_PRIVACY_ACTION,
    CONF_COVER_GROUPS_ACCENT_ACTION,
)
_COVER_PRESET_STATE_KEYS = (
    CONF_COVER_GROUPS_DAYLIGHT_STATES,
    CONF_COVER_GROUPS_PRIVACY_STATES,
    CONF_COVER_GROUPS_ACCENT_STATES,
)


def add_non_light_feature_selectors(
    *,
    flow: OptionsFlowHandler,
    feature_enum: MagicAreasFeatures,
    selectors: SelectorMap,
) -> None:
    """Add selector overrides for non-light feature config forms."""
    if feature_enum == MagicAreasFeatures.AGGREGATES:
        selectors.update(
            {
                CONF_AGGREGATES_MIN_ENTITIES: build_selector_number(
                    min_value=1, unit_of_measurement=""
                ),
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: build_selector_number(
                    min_value=0,
                    max_value=_NUMERIC_SELECTOR_MAX,
                    unit_of_measurement="lx",
                ),
                CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS: (
                    build_selector_number(min_value=0, unit_of_measurement="%")
                ),
                AGGREGATES_OPTION_KEYS[3]: build_selector_select(
                    sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
                ),
                AGGREGATES_OPTION_KEYS[4]: build_selector_select(
                    sorted(ALL_SENSOR_DEVICE_CLASSES), multiple=True
                ),
            }
        )

    if feature_enum == MagicAreasFeatures.FAN_GROUPS:
        selectors.update(
            {
                FAN_GROUPS_OPTION_KEYS[0]: build_selector_select(
                    options=[
                        AreaStates.OCCUPIED.value,
                        AreaStates.EXTENDED.value,
                        AreaStates.DARK.value,
                        AreaStates.BRIGHT.value,
                        AreaStates.SLEEP.value,
                        AreaStates.ACCENT.value,
                    ],
                    translation_key=SelectorTranslationKeys.AREA_STATES,
                ),
                FAN_GROUPS_OPTION_KEYS[1]: build_selector_select(
                    sorted(ALL_SENSOR_DEVICE_CLASSES),
                ),
                FAN_GROUPS_OPTION_KEYS[2]: build_selector_number(
                    min_value=0,
                    max_value=_NUMERIC_SELECTOR_MAX,
                    step=0.1,
                    unit_of_measurement="",
                ),
            }
        )

    if feature_enum == MagicAreasFeatures.COVER_GROUPS:
        cover_device_classes = sorted(DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES)
        area_state_options = [
            AreaStates.OCCUPIED.value,
            AreaStates.EXTENDED.value,
            AreaStates.DARK.value,
            AreaStates.BRIGHT.value,
            AreaStates.SLEEP.value,
            AreaStates.ACCENT.value,
        ]
        selectors[CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES] = build_selector_select(
            cover_device_classes, multiple=True
        )
        selectors[CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS] = build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        )
        for key in _COVER_PRESET_ACTION_KEYS:
            selectors[key] = build_selector_select(
                options=[action.value for action in CoverPresetAction],
                multiple=False,
                translation_key="cover_preset_action",
            )
        for key in _COVER_PRESET_STATE_KEYS:
            selectors[key] = build_selector_select(
                options=area_state_options,
                multiple=True,
                translation_key=SelectorTranslationKeys.AREA_STATES,
            )

    if feature_enum == MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER:
        selectors[AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[0]] = (
            build_selector_entity_simple(flow.all_media_players, multiple=True)
        )
        selectors[AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[1]] = build_selector_select(
            options=[
                AreaStates.OCCUPIED.value,
                AreaStates.EXTENDED.value,
                AreaStates.SLEEP.value,
            ],
            multiple=True,
            translation_key=SelectorTranslationKeys.AREA_STATES,
        )

    if feature_enum == MagicAreasFeatures.BLE_TRACKER:
        sensor_entities = [
            entity_id
            for entity_id in flow.all_entities
            if entity_id.startswith("sensor.")
        ]
        selectors[BLE_TRACKER_OPTION_KEYS[0]] = build_selector_entity_simple(
            sensor_entities, multiple=True
        )

    if feature_enum == MagicAreasFeatures.CLIMATE_CONTROL:
        climate_entities = [
            entity_id
            for entity_id in flow.all_entities
            if entity_id.startswith("climate.")
        ]
        selectors[CLIMATE_CONTROL_ENTITY_KEY] = build_selector_entity_simple(
            climate_entities,
            multiple=False,
        )

    if feature_enum == MagicAreasFeatures.HEALTH:
        selectors[HEALTH_OPTION_KEYS[0]] = build_selector_select(
            options=sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES),
            multiple=True,
        )

    if feature_enum == MagicAreasFeatures.PRESENCE_HOLD:
        selectors[PRESENCE_HOLD_OPTION_KEYS[0]] = build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        )

    if feature_enum == MagicAreasFeatures.WASP_IN_A_BOX:
        selectors[WASP_IN_A_BOX_OPTION_KEYS[0]] = build_selector_number(
            min_value=0,
            max_value=86_400,
            unit_of_measurement="seconds",
        )
        selectors[WASP_IN_A_BOX_OPTION_KEYS[1]] = build_selector_number(
            min_value=0,
            max_value=1_440,
            unit_of_measurement="minutes",
        )
        selectors[WASP_IN_A_BOX_OPTION_KEYS[2]] = build_selector_select(
            options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
            multiple=True,
        )
