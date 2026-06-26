"""Area-scoped configuration helpers for Magic Areas."""

from __future__ import annotations

from collections.abc import Mapping

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONFIGURABLE_AREA_STATE_MAP,
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    CONF_SECONDARY_STATES,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_RELOAD_ON_REGISTRY_CHANGE,
    DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
    DEFAULT_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.core.controls import ControlGroupDefinition
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
    GroupMetadataKey,
    GroupRole,
    is_reserved_policy_id,
)

from .feature import coerce_float, enum_string_list, string_list

type ConfigValue = object
type ConfigDict = dict[str, ConfigValue]
type ConfigMapping = Mapping[str, ConfigValue]


def _secondary_float(config: ConfigMapping, *, key: str, default: float) -> float:
    """Read one secondary-state numeric option with float coercion."""
    return coerce_float(
        secondary_states_config(config).get(key, default),
        default=default,
    )


def _string_list_option(
    config: ConfigMapping,
    *,
    key: str,
    default: list[str] | None = None,
) -> list[str]:
    """Read one list-like option as normalized list[str]."""
    value = config.get(key, default if default is not None else [])
    return string_list(value, default=default)


def has_configured_state(config: ConfigMapping, state: AreaStates) -> bool:
    """Check if area supports a given state based on config."""
    state_opts = CONFIGURABLE_AREA_STATE_MAP.get(state, None)
    if not state_opts:
        return False

    secondary_states = secondary_states_config(config)
    return bool(secondary_states.get(state_opts))


def include_entities(config: ConfigMapping) -> list[str]:
    """Return configured include_entities list."""
    return _string_list_option(config, key=CONF_INCLUDE_ENTITIES)


def exclude_entities(config: ConfigMapping) -> list[str]:
    """Return configured exclude_entities list."""
    return _string_list_option(config, key=CONF_EXCLUDE_ENTITIES)


def ignore_diagnostic_entities(config: ConfigMapping) -> bool | None:
    """Return configured ignore_diagnostic_entities value."""
    value = config.get(CONF_IGNORE_DIAGNOSTIC_ENTITIES)
    return value if isinstance(value, bool) else None


def presence_device_platforms(config: ConfigMapping) -> list[str]:
    """Return configured presence device platforms."""
    return _string_list_option(
        config,
        key=CONF_PRESENCE_DEVICE_PLATFORMS,
        default=DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    )


def presence_sensor_device_classes(config: ConfigMapping) -> list[str]:
    """Return configured presence sensor device classes."""
    return enum_string_list(config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS, []))


def keep_only_entities(config: ConfigMapping) -> list[str]:
    """Return configured keep_only_entities list."""
    return _string_list_option(config, key=CONF_KEEP_ONLY_ENTITIES)


def area_type(config: ConfigMapping) -> str | None:
    """Return configured area type value."""
    value = config.get(CONF_TYPE)
    if value is None:
        return None
    return str(value)


def secondary_states_config(config: ConfigMapping) -> ConfigMapping:
    """Return secondary-states config mapping."""
    value = config.get(CONF_SECONDARY_STATES, {})
    return value if isinstance(value, Mapping) else {}


def secondary_states_calculation_mode(config: ConfigMapping) -> str:
    """Return configured secondary-states calculation mode."""
    value = secondary_states_config(config).get(
        CONF_SECONDARY_STATES_CALCULATION_MODE,
        DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
    )
    return str(value)


def extended_time_minutes(config: ConfigMapping) -> float:
    """Return extended-time threshold in minutes."""
    return _secondary_float(
        config,
        key=CONF_EXTENDED_TIME,
        default=DEFAULT_EXTENDED_TIME,
    )


def sleep_timeout_minutes(config: ConfigMapping) -> float:
    """Return sleep timeout in minutes."""
    return _secondary_float(
        config,
        key=CONF_SLEEP_TIMEOUT,
        default=DEFAULT_SLEEP_TIMEOUT,
    )


def extended_timeout_minutes(config: ConfigMapping) -> float:
    """Return extended timeout in minutes."""
    return _secondary_float(
        config,
        key=CONF_EXTENDED_TIMEOUT,
        default=DEFAULT_EXTENDED_TIMEOUT,
    )


def reload_on_registry_change(config: ConfigMapping) -> bool:
    """Return whether registry updates should trigger reload."""
    return bool(
        config.get(CONF_RELOAD_ON_REGISTRY_CHANGE, DEFAULT_RELOAD_ON_REGISTRY_CHANGE)
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    """Return tuple[str, ...] from list-like values."""
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def normalize_custom_control_groups(
    config: ConfigDict,
) -> list[ControlGroupDefinition]:
    """Return normalized custom control-group definitions from area config."""
    raw_groups = config.get(CONF_CUSTOM_CONTROL_GROUPS, [])
    if not isinstance(raw_groups, list):
        return []

    normalized: list[ControlGroupDefinition] = []
    seen_group_ids: set[str] = set()
    primary_role_policies: set[str] = set()

    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            continue

        group_id = raw_group.get("group_id")
        members = raw_group.get("members")
        if (
            not isinstance(group_id, str)
            or not group_id
            or not isinstance(members, list)
            or group_id in seen_group_ids
        ):
            continue
        seen_group_ids.add(group_id)

        policy_id = str(
            raw_group.get("policy_id", ControlGroupPolicyId.CUSTOM_CONTROL_GROUP)
        )
        if is_reserved_policy_id(policy_id) and policy_id != str(
            ControlGroupPolicyId.CUSTOM_CONTROL_GROUP
        ):
            continue

        metadata_value = raw_group.get("metadata")
        metadata: dict[str, object] = (
            dict(metadata_value) if isinstance(metadata_value, dict) else {}
        )
        role = metadata.get(str(GroupMetadataKey.ROLE))
        if role == str(GroupRole.PRIMARY):
            if policy_id in primary_role_policies:
                continue
            primary_role_policies.add(policy_id)

        normalized.append(
            ControlGroupDefinition(
                group_id=group_id,
                members=_string_tuple(members),
                trigger_states=_string_tuple(raw_group.get("trigger_states")),
                policy_id=policy_id,
                metadata=metadata,
            )
        )

    return normalized
