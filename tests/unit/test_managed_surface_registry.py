"""Tests for HA registry helpers around managed surfaces."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from custom_components.magic_areas.core.managed_surface_registry import (
    is_managed_surface_config_entry,
    iter_managed_surface_config_entries,
    iter_managed_surface_entity_entries,
    resolve_managed_surface_entity_id,
)


def _entry(
    *,
    entry_id: str,
    unique_id: str | None,
    state: ConfigEntryState = ConfigEntryState.LOADED,
    domain: str = "group",
) -> SimpleNamespace:
    """Build a minimal config entry test double."""
    return SimpleNamespace(
        entry_id=entry_id,
        unique_id=unique_id,
        state=state,
        domain=domain,
    )


def _config_entry(entry: SimpleNamespace) -> ConfigEntry[object]:
    """Cast minimal config-entry doubles to the HA type expected by helpers."""
    return cast(ConfigEntry[object], entry)


def _hass(value: SimpleNamespace) -> HomeAssistant:
    """Cast minimal hass doubles to the HA type expected by helpers."""
    return cast(HomeAssistant, value)


def _entity_registry(value: SimpleNamespace) -> EntityRegistry:
    """Cast minimal registry doubles to the HA type expected by helpers."""
    return cast(EntityRegistry, value)


def test_managed_surface_config_entry_predicate_scopes_by_owner() -> None:
    """Managed-surface entries should be matchable globally or by owner."""
    entry = _entry(
        entry_id="helper-1",
        unique_id="magic_areas:owner-1:area-1:fan_groups:config_entry_helper:fan_group",
    )

    assert is_managed_surface_config_entry(_config_entry(entry))
    assert is_managed_surface_config_entry(
        _config_entry(entry), owner_entry_id="owner-1"
    )
    assert not is_managed_surface_config_entry(
        _config_entry(entry), owner_entry_id="owner-2"
    )
    assert not is_managed_surface_config_entry(
        _config_entry(_entry(entry_id="user-helper", unique_id="fan_group"))
    )


def test_iter_managed_surface_config_entries_filters_domain_owner_and_state() -> None:
    """Managed config-entry iteration should hide user and unrelated helper entries."""
    entries = [
        _entry(
            entry_id="loaded-owned",
            unique_id="magic_areas:owner-1:area-1:fan_groups:config_entry_helper:fan_group",
            state=ConfigEntryState.LOADED,
            domain="group",
        ),
        _entry(
            entry_id="not-loaded-owned",
            unique_id="magic_areas:owner-1:area-1:cover_groups:config_entry_helper:blind",
            state=ConfigEntryState.NOT_LOADED,
            domain="group",
        ),
        _entry(
            entry_id="other-owner",
            unique_id="magic_areas:owner-2:area-2:fan_groups:config_entry_helper:fan_group",
            state=ConfigEntryState.LOADED,
            domain="group",
        ),
        _entry(
            entry_id="other-domain",
            unique_id="magic_areas:owner-1:area-1:threshold:config_entry_helper:light",
            state=ConfigEntryState.LOADED,
            domain="threshold",
        ),
        _entry(
            entry_id="user-owned",
            unique_id="user-group",
            state=ConfigEntryState.LOADED,
            domain="group",
        ),
    ]
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_entries=lambda domain=None: [
                entry for entry in entries if domain is None or entry.domain == domain
            ]
        )
    )

    resolved = list(
        iter_managed_surface_config_entries(
            _hass(hass),
            owner_entry_id="owner-1",
            domain="group",
            loaded_only=True,
        )
    )

    assert [entry.entry_id for entry in resolved] == ["loaded-owned"]


def test_iter_managed_surface_entity_entries_and_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed entity lookup should use config-entry ownership, not display names."""
    unique_id = "magic_areas:owner-1:area-1:fan_groups:config_entry_helper:fan_group"
    entries = [
        _entry(entry_id="helper-1", unique_id=unique_id),
        _entry(entry_id="user-helper", unique_id="fan_group"),
    ]
    registry_entries = {
        "helper-1": [
            SimpleNamespace(domain="fan", entity_id="fan.magic_areas_fan_group"),
            SimpleNamespace(domain="sensor", entity_id="sensor.not_requested"),
        ],
        "user-helper": [
            SimpleNamespace(domain="fan", entity_id="fan.user_group"),
        ],
    }
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_entries=lambda domain=None: [
                entry for entry in entries if domain is None or entry.domain == domain
            ]
        )
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
        lambda registry, entry_id: registry_entries.get(entry_id, []),
    )

    entity_entries = list(
        iter_managed_surface_entity_entries(
            _hass(hass),
            _entity_registry(SimpleNamespace()),
            owner_entry_id="owner-1",
            config_entry_domain="group",
            entity_domain="fan",
        )
    )

    assert [entry.entity_id for entry in entity_entries] == [
        "fan.magic_areas_fan_group"
    ]
    assert (
        resolve_managed_surface_entity_id(
            _hass(hass),
            _entity_registry(SimpleNamespace()),
            unique_id=unique_id,
            entity_domain="fan",
            config_entry_domain="group",
        )
        == "fan.magic_areas_fan_group"
    )
