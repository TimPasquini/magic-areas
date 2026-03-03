"""Schemas for custom control-group definitions."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

CUSTOM_CONTROL_GROUP_SCHEMA = vol.Schema(
    {
        vol.Required("group_id"): cv.string,
        vol.Required("members"): cv.entity_ids,
        vol.Optional("trigger_states", default=[]): cv.ensure_list,
        vol.Optional("policy_id", default="custom_control_group"): cv.string,
        vol.Optional("metadata", default={}): dict,
    },
    extra=vol.REMOVE_EXTRA,
)

CUSTOM_CONTROL_GROUPS_SCHEMA = vol.All(
    cv.ensure_list,
    [CUSTOM_CONTROL_GROUP_SCHEMA],
)
