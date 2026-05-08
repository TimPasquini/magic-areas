"""Pure control intent evaluation primitives."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from custom_components.magic_areas.core.control_intents.models import RoleTarget


class IntentAction(StrEnum):
    """Requested or resolved control action."""

    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    NOOP = "noop"


class ConstraintEffect(StrEnum):
    """Effect a constraint has on an intent."""

    SUPPRESS = "suppress"
    FORCE_OFF = "force_off"
    NOOP = "noop"


class IntentReason(StrEnum):
    """Stable reason codes emitted by the pure engine."""

    INTENT_ALLOWED = "intent_allowed"
    TARGET_SUPPRESSED = "target_suppressed"
    TARGET_PARTIALLY_SUPPRESSED = "target_partially_suppressed"
    FORCE_OFF = "force_off"
    CONSTRAINT_NOOP = "constraint_noop"
    EMPTY_TARGET = "empty_target"


@dataclass(frozen=True, slots=True)
class ControlIntent:
    """Policy-neutral request to control a resolved role target."""

    intent_id: str
    action: IntentAction
    target: RoleTarget
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class IntentConstraint:
    """Constraint applied to an intent before runtime execution."""

    constraint_id: str
    effect: ConstraintEffect
    reason: str
    target_entity_ids: tuple[str, ...] = ()
    priority: int = 0


@dataclass(frozen=True, slots=True)
class IntentDecision:
    """Pure engine decision for a control intent."""

    action: IntentAction
    target: RoleTarget | None = None
    target_entity_ids: tuple[str, ...] = ()
    reason: IntentReason = IntentReason.INTENT_ALLOWED
    reason_detail: str | None = None
    applied_constraints: tuple[str, ...] = ()

    @property
    def is_noop(self) -> bool:
        """Return whether the decision intentionally does nothing."""
        return self.action is IntentAction.NOOP


def evaluate_intent(
    intent: ControlIntent,
    constraints: Iterable[IntentConstraint] = (),
) -> IntentDecision:
    """Evaluate one control intent against deterministic constraints.

    This function is intentionally HA-free. It only works with already-resolved target
    records and explicit entity subsets supplied by adapters.
    """
    ordered_constraints = tuple(
        sorted(constraints, key=lambda constraint: constraint.priority, reverse=True)
    )

    noop_constraint = _first_constraint_with_effect(
        ordered_constraints,
        ConstraintEffect.NOOP,
    )
    if noop_constraint is not None:
        return IntentDecision(
            action=IntentAction.NOOP,
            target=intent.target,
            reason=IntentReason.CONSTRAINT_NOOP,
            reason_detail=noop_constraint.reason,
            applied_constraints=(noop_constraint.constraint_id,),
        )

    force_off_constraint = _first_constraint_with_effect(
        ordered_constraints,
        ConstraintEffect.FORCE_OFF,
    )
    if force_off_constraint is not None:
        target_entity_ids = _constraint_target_entity_ids(
            intent.target.target_entity_ids,
            force_off_constraint,
        )
        if not target_entity_ids:
            return IntentDecision(
                action=IntentAction.NOOP,
                target=intent.target,
                reason=IntentReason.EMPTY_TARGET,
                reason_detail=force_off_constraint.reason,
                applied_constraints=(force_off_constraint.constraint_id,),
            )
        return IntentDecision(
            action=IntentAction.DEACTIVATE,
            target=intent.target,
            target_entity_ids=target_entity_ids,
            reason=IntentReason.FORCE_OFF,
            reason_detail=force_off_constraint.reason,
            applied_constraints=(force_off_constraint.constraint_id,),
        )

    target_entity_ids = intent.target.target_entity_ids
    suppression_constraints = tuple(
        constraint
        for constraint in ordered_constraints
        if constraint.effect is ConstraintEffect.SUPPRESS
    )
    if suppression_constraints and target_entity_ids:
        surviving_entity_ids, applied_constraints = _apply_suppression_constraints(
            target_entity_ids,
            suppression_constraints,
        )
        if not surviving_entity_ids:
            return IntentDecision(
                action=IntentAction.NOOP,
                target=intent.target,
                reason=IntentReason.TARGET_SUPPRESSED,
                reason_detail="target_suppressed_by_constraints",
                applied_constraints=applied_constraints,
            )
        if surviving_entity_ids != target_entity_ids:
            return IntentDecision(
                action=intent.action,
                target=intent.target,
                target_entity_ids=surviving_entity_ids,
                reason=IntentReason.TARGET_PARTIALLY_SUPPRESSED,
                reason_detail="target_subset_allowed_after_suppression",
                applied_constraints=applied_constraints,
            )

    if not intent.target.is_executable:
        return IntentDecision(
            action=IntentAction.NOOP,
            target=intent.target,
            reason=IntentReason.EMPTY_TARGET,
            reason_detail="target_not_executable",
        )

    return IntentDecision(
        action=intent.action,
        target=intent.target,
        target_entity_ids=target_entity_ids,
        reason=IntentReason.INTENT_ALLOWED,
        reason_detail=intent.reason,
    )


def _first_constraint_with_effect(
    constraints: tuple[IntentConstraint, ...],
    effect: ConstraintEffect,
) -> IntentConstraint | None:
    """Return the highest-priority constraint with an effect."""
    return next(
        (constraint for constraint in constraints if constraint.effect is effect),
        None,
    )


def _constraint_target_entity_ids(
    intent_entity_ids: tuple[str, ...],
    constraint: IntentConstraint,
) -> tuple[str, ...]:
    """Return the target subset affected by a constraint."""
    if not constraint.target_entity_ids:
        return intent_entity_ids
    constrained = set(constraint.target_entity_ids)
    return tuple(entity_id for entity_id in intent_entity_ids if entity_id in constrained)


def _apply_suppression_constraints(
    target_entity_ids: tuple[str, ...],
    constraints: tuple[IntentConstraint, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Apply suppression constraints as subtractive entity filters."""
    surviving_entity_ids = target_entity_ids
    applied_constraints: list[str] = []
    for constraint in constraints:
        suppressed_entity_ids = _constraint_target_entity_ids(
            surviving_entity_ids,
            constraint,
        )
        if not suppressed_entity_ids:
            continue
        applied_constraints.append(constraint.constraint_id)
        suppressed = set(suppressed_entity_ids)
        surviving_entity_ids = tuple(
            entity_id
            for entity_id in surviving_entity_ids
            if entity_id not in suppressed
        )
    return surviving_entity_ids, tuple(applied_constraints)


__all__ = [
    "ConstraintEffect",
    "ControlIntent",
    "IntentAction",
    "IntentConstraint",
    "IntentDecision",
    "IntentReason",
    "evaluate_intent",
]
