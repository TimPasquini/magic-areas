# Repository Operating Contract

This file records execution rules learned from work on this repository. Read it
with `CLAUDE.md` before changing code, tests, plans, or simulator infrastructure.

## End Goal

Build a reliable Home Assistant integration whose behavior is demonstrated at
three levels:

1. Pure policy and helper behavior.
2. Home Assistant runtime integration.
3. Real behavior inside the live fake-house simulator.

Plans organize the work, but code and runtime evidence determine whether the
work is complete.

## Work Discipline

- Start at the exact roadmap or audit item requested. Do not skip ahead because
  a later item appears easier or more interesting.
- Read the implementation, callers, tests, documentation, and relevant logs
  before assessing an item's status. A checked box and a prior completion
  report are claims, not evidence.
- If an item is incomplete, finish its implementation, coverage, documentation,
  and validation before marking it complete.
- Do not mark partially addressed work complete. Record every remaining defect,
  missing test, uncertain contract, and deferred decision explicitly.
- Continue through the requested sequence unless there is a genuine blocker or
  a decision that requires user input. Do not stop merely to report routine
  progress.
- Before reporting a phase or audit complete, perform a separate adversarial
  sweep for skipped work, shallow tests, stale callers, stale documentation,
  compatibility leftovers, and behavior that was inferred rather than run.
- Preserve unrelated working-tree changes. Keep commits scoped, and stop if
  unexpected changes appear in files being modified.

## Completion Evidence

An item is complete only when all applicable evidence exists:

- The intended behavior is implemented in the actual codebase.
- All production callers use the intended API and no stale path is overlooked.
- Tests exercise the stated contract, including failure and boundary behavior
  where relevant.
- Documentation and examples describe the current API and behavior.
- Required static, unit, integration, and simulation validation has passed.
- The active roadmap accurately records both completion and remaining gaps.

Passing tests do not prove completion when the tests do not exercise the real
contract. Do not describe browser or UI behavior as autonomously validated when
the evidence came only from API calls, fixtures, or test clients.

## Validation

- Run focused tests while implementing a change.
- Use `./scripts/validate_basic.sh` for a quick static validation pass.
- Run `./scripts/validate.sh` before a commit, phase exit, or completion claim.
- Invoke repository scripts directly. Do not introduce `UV_CACHE_DIR`, custom
  cache locations, sandbox workarounds, or alternate dependency procedures for
  routine validation.
- If validation fails, report the actual command and failure. Do not silently
  substitute a narrower command and call the original requirement complete.
- After structural refactors, refresh CRG against the current committed tree
  before using its results. Treat CRG findings as candidates requiring direct
  code and caller verification, not proof of dead code or architectural drift.

## Simulator Contract

- The simulator validates real Home Assistant behavior in real elapsed time. It
  is not a unit-test harness.
- The default 30-second cycle is intentional. Scenario waits must respect real,
  configured cycle timing; short settle delays cannot replace behavioral waits.
- The Setup Room exists only for config-flow and manual setup testing. Never use
  it for active simulation scenarios.
- Simulation scenarios share one fake house and must run serially. Reset and
  bootstrap operations must restore a deterministic baseline, including the
  Setup Room.
- A simulator assertion should prove both the expected positive behavior and
  protection against bad outcomes, including contaminated or overlapping input
  conditions where applicable.
- Changes to automation behavior or the simulator require live fake-house
  validation and corresponding updates to
  `docs/contributing/dev-simulation-guidance.md`.

## Plans And Audit Material

- Do not delete temporary repair, audit, or checklist documents while they
  contain unique defects, decisions, expected outcomes, or coverage plans.
- Transfer required knowledge into the durable roadmap or repository guidance
  before proposing removal. Remove temporary material only when its purpose is
  complete and any required user decision has been made.
- Preserve technical detail from superseded plans. A replacement roadmap must
  contain the work itself, ordered into actionable steps, not merely references
  to the old documents.

## Repository State

- Track source inputs needed to reproduce validation, including handwritten
  type stubs.
- Keep reproducible generated artifacts untracked.
- The nested simulator configuration repository preserves non-reproducible
  fake-house state. Generated or bootstrap-recreated state does not need to be
  copied into the main repository.
