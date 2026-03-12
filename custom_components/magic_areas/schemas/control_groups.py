"""Schemas for custom control-group definitions."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from custom_components.magic_areas.core.group_contracts import (
    ControlGroupPolicyId,
    is_reserved_policy_id,
)
from custom_components.magic_areas.core.group_metadata import GroupMetadataKey, GroupRole

CUSTOM_CONTROL_GROUP_SCHEMA = vol.Schema(
    {
        vol.Required("group_id"): cv.string,
        vol.Required("members"): cv.entity_ids,
        vol.Optional("trigger_states", default=[]): cv.ensure_list,
        vol.Optional(
            "policy_id", default=str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP)
        ): cv.string,
        vol.Optional("metadata", default={}): dict,
    },
    extra=vol.REMOVE_EXTRA,
)


def _validate_custom_control_groups_payload(
    groups: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Validate list-level custom-group guardrails."""
    seen_group_ids: set[str] = set()
    primary_role_policies: set[str] = set()

    for group in groups:
        group_id = group.get("group_id")
        policy_id = group.get("policy_id")
        metadata = group.get("metadata", {})
        members = group.get("members")

        if not isinstance(group_id, str) or not group_id:
            raise vol.Invalid("group_id must be a non-empty string")
        if group_id in seen_group_ids:
            raise vol.Invalid(f"duplicate group_id: {group_id}")
        seen_group_ids.add(group_id)

        if not isinstance(members, list):
            raise vol.Invalid(f"group {group_id} members must be a list")

        if not isinstance(policy_id, str) or not policy_id:
            raise vol.Invalid(f"group {group_id} must include a valid policy_id")
        if (
            is_reserved_policy_id(policy_id)
            and policy_id != str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP)
        ):
            raise vol.Invalid(
                f"group {group_id} uses reserved policy_id: {policy_id}"
            )

        if not isinstance(metadata, dict):
            raise vol.Invalid(f"group {group_id} metadata must be an object")

        role = metadata.get(str(GroupMetadataKey.ROLE))
        if role == str(GroupRole.PRIMARY):
            if policy_id in primary_role_policies:
                raise vol.Invalid(
                    f"multiple primary-role groups for policy_id: {policy_id}"
                )
            primary_role_policies.add(policy_id)

    return groups


CUSTOM_CONTROL_GROUPS_SCHEMA = vol.All(
    cv.ensure_list,
    [CUSTOM_CONTROL_GROUP_SCHEMA],
    _validate_custom_control_groups_payload,
)
