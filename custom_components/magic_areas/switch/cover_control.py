"""Cover control switch."""

from __future__ import annotations

import logging
from collections.abc import Callable
from time import monotonic
from typing import TYPE_CHECKING

from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.const import EntityCategory
from homeassistant.core import Event, EventStateChangedData
from homeassistant.helpers.event import async_call_later

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.core.controls import ControlGroupDecision
    from custom_components.magic_areas.core.runtime_model import AreaConfig

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls import (
    ControlGroupContext,
    MonotonicDeadlineMap,
    resolve_area_presence_states,
    resolve_group_entity_id_by_metadata,
)
from custom_components.magic_areas.core.controls.policies.cover import (
    CoverControlGroupPolicy,
    CoverPolicySignals,
    build_cover_control_group_policy,
)
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
    GroupMetadataKey,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.config.readers import cover_groups_config
from custom_components.magic_areas.switch.base import ControlSwitchBase

_LOGGER = logging.getLogger(__name__)


class CoverControlSwitch(ControlSwitchBase):
    """Switch to enable/disable Magic Areas cover automation."""

    feature_id = MagicAreasFeatures.COVER_GROUPS
    _attr_entity_category = EntityCategory.CONFIG

    policy: CoverControlGroupPolicy
    _cover_group_entity_ids: dict[str, str]
    _last_states: list[str]
    _manual_hold_seconds: int
    _manual_hold_until_monotonic: MonotonicDeadlineMap[str]
    _manual_hold_timer_cancel: Callable[[], None] | None
    _expected_cover_group_state_changes: set[str]

    def __init__(
        self, area_config: AreaConfig, coordinator: MagicAreasCoordinator
    ) -> None:
        """Initialize the cover control switch."""
        super().__init__(area_config, coordinator)
        config = cover_groups_config(self.get_feature_config())
        self.policy = build_cover_control_group_policy(config)
        self._cover_group_entity_ids = {}
        self._last_states = []
        self._manual_hold_seconds = config.manual_hold_seconds
        self._manual_hold_until_monotonic = MonotonicDeadlineMap()
        self._manual_hold_timer_cancel = None
        self._expected_cover_group_state_changes = set()

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        self._cover_group_entity_ids = self._resolve_cover_group_entity_ids()
        self._track_area_state_dispatcher(self.area_state_changed)
        for device_class, entity_id in self._cover_group_entity_ids.items():
            self._track_state_change(
                f"cover_group_state_change_{device_class}",
                entity_id,
                self.cover_group_state_changed,
            )

    async def area_state_changed(
        self,
        area_id: str,
        states_tuple: tuple[list[str], list[str], list[str]],
    ) -> None:
        """Handle area state change events."""
        states = self._extract_relevant_area_states(area_id, states_tuple)
        if not states:
            return

        _new_states, _lost_states, current_states = states
        self._last_states = current_states
        await self.run_logic(current_states)

    async def cover_group_state_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Detect manual cover movement and hold automation briefly."""
        entity_id = event.data["entity_id"]
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if old_state is None or new_state is None or old_state.state == new_state.state:
            return

        if entity_id in self._expected_cover_group_state_changes:
            self._expected_cover_group_state_changes.discard(entity_id)
            return

        if self._manual_hold_seconds > 0:
            self._manual_hold_until_monotonic.set_deadline(
                entity_id,
                monotonic() + self._manual_hold_seconds,
            )
            self._schedule_next_manual_hold_expiry_check()

    async def run_logic(self, states: list[str]) -> None:
        """Run cover control logic."""
        if not self.is_on:
            _LOGGER.debug("%s: Control disabled, skipping.", self.name)
            return

        current_states = resolve_area_presence_states(
            hass=self.hass,
            area_id=self._area_id,
            cached_states=states,
        )
        group_states = {
            entity_id: state.state if state else None
            for entity_id in self._cover_group_entity_ids.values()
            if (state := self.hass.states.get(entity_id)) is not None
        }
        context = ControlGroupContext(
            group_id=f"cover_groups_{self._area_id}",
            current_states=tuple(current_states),
            signals=CoverPolicySignals(
                cover_group_entity_ids=self._cover_group_entity_ids,
                cover_group_states=group_states,
                manual_hold_entity_ids=tuple(self._manual_hold_entity_ids()),
                daylight_open_allowed=AreaStates.DARK not in current_states,
            ),
            is_enabled=self.is_on,
        )
        await self._evaluate_policy(
            policy=self.policy,
            context=context,
            logger=_LOGGER,
        )
        self._write_policy_debug_attributes()
        self._schedule_next_manual_hold_expiry_check()
        if self.platform is not None:
            self.async_write_ha_state()

    async def _execute_decision(
        self,
        decision: ControlGroupDecision,
        *,
        blocking: bool = False,
    ) -> None:
        """Track expected cover state changes before executing service calls."""
        for action in decision.actions:
            self._expected_cover_group_state_changes.update(action.target_entity_ids)
        await super()._execute_decision(decision, blocking=blocking)

    def _manual_hold_active(self, entity_id: str | None = None) -> bool:
        """Return whether manual cover movement is currently holding automation."""
        return bool(self._manual_hold_entity_ids(entity_id))

    def _manual_hold_entity_ids(self, entity_id: str | None = None) -> list[str]:
        """Return cover helper entity IDs currently under manual hold."""
        now = monotonic()
        if entity_id is not None:
            return (
                [entity_id]
                if self._manual_hold_until_monotonic.contains(entity_id, now)
                else []
            )
        return list(self._manual_hold_until_monotonic.active_keys(now))

    def _schedule_next_manual_hold_expiry_check(self) -> None:
        """Re-run cover policy when the next manual hold expires."""
        if self._manual_hold_timer_cancel is not None:
            self._manual_hold_timer_cancel()
            self._manual_hold_timer_cancel = None

        delay = self._manual_hold_until_monotonic.next_delay(monotonic())
        if delay is None:
            return

        self._manual_hold_timer_cancel = async_call_later(
            self.hass,
            delay,
            self._manual_hold_expiry_check,
        )

    async def _manual_hold_expiry_check(self, _now: object) -> None:
        """Reevaluate cover policy after a manual hold timer expires."""
        self._manual_hold_timer_cancel = None
        states = resolve_area_presence_states(
            hass=self.hass,
            area_id=self._area_id,
            cached_states=self._last_states,
        )
        await self.run_logic(states)

    def _resolve_cover_group_entity_ids(self) -> dict[str, str]:
        """Resolve native cover group helpers for configured automation classes."""
        group_registry = self._group_registry()
        if group_registry is None:
            return {}

        resolved: dict[str, str] = {}
        for device_class in self.policy.config.automation_device_classes:
            entity_id = resolve_group_entity_id_by_metadata(
                self.hass,
                group_registry=group_registry,
                area_id=self._area_id,
                policy_id=str(ControlGroupPolicyId.COVER_GROUPS),
                domain=COVER_DOMAIN,
                metadata_key=str(GroupMetadataKey.CATEGORY),
                metadata_value=f"cover_group_{device_class}",
            )
            if entity_id is not None:
                resolved[device_class] = entity_id
        return resolved

    def _write_policy_debug_attributes(self) -> None:
        """Expose cover automation details for troubleshooting."""
        attrs = dict(getattr(self, "_attr_extra_state_attributes", {}) or {})
        attrs.update(
            {
                "cover_automation_targets": dict(self._cover_group_entity_ids),
                "manual_cover_hold_active": self._manual_hold_active(),
                "manual_cover_hold_entities": self._manual_hold_entity_ids(),
            }
        )
        self._attr_extra_state_attributes = attrs

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending manual-hold timers when removed from Home Assistant."""
        if self._manual_hold_timer_cancel is not None:
            self._manual_hold_timer_cancel()
            self._manual_hold_timer_cancel = None
        await super().async_will_remove_from_hass()


__all__ = ["CoverControlSwitch"]
