# Light System Recomposition Plan

## Goal
Eliminate the current light-related sprawl by:
- consolidating light logic under a clear package boundary, and
- introducing an abstract **Control Group** concept that can power default
  light groups as well as custom cross-domain groups.

This plan is about architecture and composition, not just light behavior.

## Scope
- Recompose light-related files into a clear vertical slice.
- Introduce a generalized Control Group abstraction and use light as first adopter.
- Preserve user-visible behavior during migration.

## Non-Goals
- No breaking config schema changes in this phase.
- No custom-control-group UI rollout in initial light migration.
- No forced migration of fan/climate/media in the same PR as light recomposition.

## Compatibility Invariants
- Existing light entity IDs and unique IDs remain stable.
- Existing feature flags/options keys remain valid.
- Existing default light group behavior (overhead/sleep/accent/task/all) remains unchanged.
- Existing dispatcher/listener behavior should not duplicate callbacks.

## Current Pain Points
- Light logic is scattered across:
  - `light.py` (platform)
  - `features/modules/light_groups.py` (feature entry)
  - `light_group_entities.py`, `light_group_events.py`, `light_group_actions.py`
  - `light_groups.py` (config constants)
  - `core/light_control.py`, `core/control.py`
- Entry points are unclear: platform vs feature module vs helpers.
- Control tracking (`core.control`) is effectively light-specific but lives in `core/`.

## Target Architecture
### 1) Light system becomes a vertical slice
Create a `light_groups/` package to hold all light-specific behavior:
```
light_groups/
  __init__.py
  config.py          # constants + defaults
  entities.py        # AreaLightGroup + MagicLightGroup
  events.py          # event wiring (thin)
  actions.py         # service call helpers (or move to executor)
  policy.py          # light-specific policy (priority rules)
  control.py         # light-specific control state (if not generalized yet)
```
The only external entry point is the feature module.

### 2) Introduce Control Groups (abstract)
Create a generalized control-group abstraction used by:
- Light defaults (overhead/sleep/accent/task)
- Fan control
- Climate control
- Media player control
- Custom cross-domain control groups

Light groups become **preconfigured control groups** using light-specific policies.

## Phases
### Phase A — Establish Control Group abstraction
- Define control group model: members, triggers, actions, policy binding.
- Define policy interface: input (snapshot + trigger signals) → decision.
- Define execution interface: action → HA service call.
- Define echo/ownership tracking (generalized, not light-specific).

Acceptance criteria:
- `control_group` model and policy interfaces are in `core/` (or target package).
- Unit tests cover command-echo ownership transitions.
- No light runtime code migrated yet.

### Phase B — Recompose light system to use Control Groups
- Move light group config + event wiring into `light_groups/` package.
- Replace light-specific control state with control-group echo tracking.
- Use a light policy for priority filtering but pass through control-group executor.
- Make `features/modules/light_groups.py` construct default control group
  definitions (overhead/sleep/accent/task).

Acceptance criteria:
- Light file sprawl collapsed into vertical slice package.
- No direct side-door imports from unrelated modules into internal light package files.
- Existing light contract/integration tests pass with parity.

### Phase C — Extend Control Groups to other platforms
- Fan control: migrate to control-group policy and executor.
- Climate control: migrate to control-group policy and executor.
- Media player control: migrate to control-group policy and executor.

Acceptance criteria:
- Platform control behavior remains parity-correct under existing tests.
- Shared control-group executor handles all migrated domains.

### Phase D — Optional custom control groups
- Allow user-defined control groups (cross-domain) as an advanced config feature.
- Provide basic templates (task group, reading group, etc.).

Acceptance criteria:
- Cross-domain control group can combine multi-domain members and trigger criteria.
- Config-flow integration is schema-driven and test-covered.

## Test-First Plan (write before implementation)
Create failing-first, contract-oriented tests before each phase, while keeping pytest
collection stable and deterministic.

Phase A tests:
1. `tests/unit/test_control_group_contract.py`
2. `tests/unit/test_command_echo_tracker.py`
3. Expected initial state: import failures or `NotImplementedError` assertions until
   abstraction is created.

Phase B tests:
1. `tests/unit/test_light_control_group_parity.py`
2. `tests/platforms/test_light_group_integration_parity.py`
3. Assertions:
   - identical entity counts/IDs for light groups
   - identical turn on/off decisions for known state transitions
   - no duplicate listeners

Phase C tests:
1. `tests/unit/test_fan_control_group_parity.py`
2. `tests/unit/test_climate_control_group_parity.py`
3. `tests/unit/test_media_control_group_parity.py`

Pytest stability rules:
- Use existing fixtures only; avoid introducing environment-heavy fixtures in early phase.
- Keep all new tests importable even when implementations are pending:
  - gate expected-failure tests with explicit `pytest.raises` on missing abstractions, or
  - assert current placeholder behavior intentionally fails.
- Add focused iteration commands per phase before full-suite runs.

## Risk / Rollback
- Risk: light behavior regression in edge-case event ordering.
- Mitigation: keep parity tests for known edge cases and listener duplication checks.
- Rollback strategy:
  - keep old light path behind a temporary feature switch during migration window, or
  - revert to previous light entry wiring while retaining new abstraction code.

## Success Criteria
- Light functionality is preserved with fewer files and clearer ownership.
- Control state tracking is shared, not light-specific.
- Feature modules act as entry points only; no hidden side-doors.
- Cross-domain control groups are possible without bespoke logic.
