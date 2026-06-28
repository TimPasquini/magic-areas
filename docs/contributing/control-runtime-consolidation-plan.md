# Control Runtime Consolidation Plan

This temporary planning document scopes the control-runtime consolidation work.
Do not delete it while this work is active. Before removal, transfer any still
useful decisions, standards, validation evidence, or deferred defects into
`docs/contributing/master-architecture-roadmap-plan.md` or durable contributor
guidance.

## Goal

Reduce repeated runtime glue across fan, cover, light, climate, and media
control paths without creating an over-general automation framework.

The target is shared runtime support for repeated mechanics only. Domain policy
decisions, domain-specific signal interpretation, user-facing debug attribute
names, and Home Assistant service semantics must remain feature-owned unless
direct evidence shows an identical contract in more than one domain.

## Current implementation inventory

### Shared control foundation already present

The repository already has meaningful shared control primitives. Phase work
should build on these, not replace them:

- `core/controls/control_group.py`
  - `ControlAction`
  - `ControlGroupContext`
  - `ControlGroupDecision`
  - `ControlGroupPolicy`
  - `evaluate_and_execute_control_group_policy`
  - `evaluate_and_execute_control_group_policy_sync`
  - `execute_control_group_runtime_effects`
  - `execute_control_group_decision`
- `core/controls/control_group_runtime.py`
  - control-group entity/member resolution by policy and metadata
  - area-state dispatcher/state-change listener helpers
  - area presence state resolution
- `switch/base.py`
  - `ControlSwitchBase`
  - listener tracking
  - area-state event filtering
  - policy evaluation/execution adapter
  - coordinator snapshot entity/group registry accessors
  - primary group/member resolution helpers
  - float state parsing helper

This means Phase work should be incremental. A new runtime-support module is
only justified where current repeated code cannot cleanly live in the existing
shared modules.

### Active implementation scope

The first executable slice is deliberately narrow:

1. Add a pure monotonic-deadline helper.
2. Migrate cover manual-hold bookkeeping to that helper.
3. Migrate fan post-clear hold bookkeeping to that helper.
4. Migrate fan unavailable-sensor hold bookkeeping to that helper.
5. Stop and reassess before extracting anything else.

Climate and media are included in this inventory as reviewed control domains,
not as expected first-pass edit targets. Do not touch climate or media during
the first slice unless direct implementation work exposes a repeated mechanic
with at least two production callers and behavior-preserving tests.

Expected first-slice production edit surface:

- add one helper module under `custom_components/magic_areas/core/controls/`;
- update `custom_components/magic_areas/switch/cover_control.py`;
- update `custom_components/magic_areas/switch/fan_control.py`;
- add or update focused unit tests for the helper and affected fan/cover switch
  behavior.

Unexpected edits to light runtime, climate runtime, media runtime, feature
modules, config flow, or policy semantics are out of scope and require a fresh
decision before continuing.

Before implementation, record the observed current behavior for each deadline
map directly from the existing code:

- whether repeated activation preserves the original deadline or replaces it;
- when expired entries are pruned;
- what schedules or cancels the next callback;
- which callback reruns policy;
- which attributes expose active hold state.

Do not infer those behaviors from the planned helper API. The helper API must
fit the current behavior, not the reverse.

Observed pre-implementation deadline behavior at start commit `2dd86e0` on
branch `fan-cover-default-automation`:

Cover manual holds:

- Repeated unexpected movement for the same cover group replaces the prior
  deadline with `monotonic() + manual_hold_seconds`.
- Expected Magic Areas-issued cover group state changes are consumed from
  `_expected_cover_group_state_changes` and do not start a manual hold.
- `_manual_hold_entity_ids()` prunes expired holds before returning active
  entity IDs.
- `_manual_hold_entity_ids(entity_id)` returns a one-item list if that entity
  remains held, otherwise an empty list.
- Active cover hold IDs are returned sorted.
- `_schedule_next_manual_hold_expiry_check()` cancels any existing callback,
  prunes expired holds via `_manual_hold_entity_ids()`, then schedules the next
  callback for `max(min(deadlines) - monotonic(), 0.0)`.
- `_manual_hold_expiry_check()` clears the callback handle, resolves current
  area presence states from `_last_states`, and calls `run_logic(states)`.
- `run_logic()` writes debug attributes and reschedules the next manual-hold
  expiry after policy evaluation.
- `async_will_remove_from_hass()` cancels any pending manual-hold callback.
- Debug attributes expose `manual_cover_hold_active` and
  `manual_cover_hold_entities`.

Fan post-clear holds:

- Repeated activation for the same controller preserves the first deadline via
  `setdefault(controller_id, now + hold_seconds)`.
- The post-clear hold is removed when the controller gate is no longer cleared.
- `_active_hold_ids()` prunes expired holds before returning sorted controller
  IDs.
- `_drop_expired_holds(now)` prunes both fan hold namespaces.
- `_schedule_next_hold_expiry_check()` cancels any existing callback and
  schedules the next callback for
  `max(min(all_fan_deadlines) - monotonic(), 0.0)`.
- `_hold_expiry_check()` clears the callback handle, resolves current area
  presence states from `_last_states`, and calls `run_logic(states)`.
- `run_logic()` writes debug attributes and reschedules the next hold expiry
  after policy evaluation.
- Debug attributes expose `post_clear_hold_fan_reasons`.

Fan unavailable-sensor holds:

- Repeated activation for the same controller preserves the first deadline via
  `setdefault(controller_id, now + hold_seconds)`.
- The unavailable hold is removed when the controller sensor value is available
  again.
- It shares fan hold pruning, scheduling, expiry callback, and run-logic
  behavior with post-clear holds.
- Debug attributes expose `unavailable_hold_fan_reasons`.

### Domain switch/runtime files inspected

Fan:

- `switch/fan_control.py`
- `core/controls/policies/fan.py`
- `features/modules/fan_groups.py`
- tests:
  - `tests/unit/test_fan_control_switch.py`
  - `tests/unit/test_fan_controller_policy.py`

Cover:

- `switch/cover_control.py`
- `core/controls/policies/cover.py`
- `features/modules/cover_groups.py`
- tests:
  - `tests/unit/test_cover_control_policy.py`
  - `tests/unit/test_cover_control_switch.py` if added during work; currently
    cover switch behavior is partly covered through policy tests using
    `CoverControlSwitch` internals.
  - If existing tests do not directly preserve manual-hold scheduling,
    expiration, and expected-change behavior, add focused switch-level coverage
    before or with the cover migration.

Climate:

- `switch/climate_control.py`
- `core/controls/policies/climate.py`
- `features/modules/climate_control.py`
- tests:
  - `tests/unit/test_climate_control_switch.py`
  - `tests/platforms/test_climate_control_logic.py`

Media:

- `switch/media_player_control.py`
- `core/controls/policies/media.py`
- `features/modules/media_player_groups.py`
- tests:
  - `tests/unit/test_media_player_control_switch.py`

Light:

- `light_groups/runtime.py`
- `light_groups/policy.py`
- `light_groups/controller.py`
- `light_groups/intent_adapter.py`
- tests:
  - `tests/unit/test_light_group_runtime.py`
  - `tests/unit/test_light_control_group_policy_adapter.py`
  - `tests/unit/test_light_control_group_parity.py`

## Pattern inventory and extraction candidates

Candidate disposition summary:

| Candidate | First-pass disposition | Reason |
| --- | --- | --- |
| Deadline/hold timer bookkeeping | Proceed first | Fan and cover share concrete monotonic-deadline mechanics. |
| Policy debug attribute updates | Reassess after deadline cleanup | Repetition exists, but debug keys are user-facing/domain-owned. |
| Current area-state resolution before re-evaluation | Defer | Existing resolver already exists; remaining duplication may shrink after deadline cleanup. |
| Target entity state snapshots | Defer | Similar reads exist, but value semantics differ by domain. |
| Expected self-issued state changes | Do not extract first pass | Cover expected changes and light command echo are not the same contract. |
| Control switch disabled gating | Do not extract first pass | Shared dispatcher-event gate already exists. |
| Service-call execution and runtime effects | Do not extract first pass | Existing control-group executor already owns the common behavior. |

### Candidate A: deadline/hold timer bookkeeping

Evidence:

- `switch/fan_control.py`
  - `_post_clear_hold_until_monotonic`
  - `_unavailable_hold_until_monotonic`
  - `_active_hold_ids`
  - `_drop_expired_holds`
  - `_schedule_next_hold_expiry_check`
  - `_hold_expiry_check`
- `switch/cover_control.py`
  - `_manual_hold_until_monotonic`
  - `_manual_hold_active`
  - `_manual_hold_entity_ids`
  - `_schedule_next_manual_hold_expiry_check`
  - `_manual_hold_expiry_check`

Why it may be extractable:

- Both domains store monotonic deadlines keyed by IDs.
- Both prune expired entries before exposing active IDs.
- Both schedule one Home Assistant callback for the next expiry.
- Both rerun domain policy when the timer expires.

Why it needs caution:

- Fan has multiple hold namespaces and controller-specific activation rules.
- Cover has one manual-hold namespace tied to unexpected group state changes.
- Expiry callbacks call domain-specific `run_logic` with current area states.

Likely shape:

- A small `DeadlineTracker` or `MonotonicDeadlineMap` pure helper that owns:
  - `setdefault_deadline(key, deadline)`
  - `discard(key)`
  - `drop_expired(now)`
  - `active_keys(now)`
  - `next_delay(now)`
- Keep Home Assistant scheduling and domain re-evaluation in switch modules
  unless a second pass proves a shared scheduler wrapper is also worthwhile.

First-pass helper boundary:

- The helper owns only deadline-map state.
- The helper must not own Home Assistant callback handles.
- The helper must not store entity method references.
- The helper must not call `async_call_later`, `run_logic`, or any other HA
  runtime API.
- Do not add a generic scheduler wrapper in the first pass.

Behavioral invariants to preserve:

- Cover manual holds remain tied to unexpected cover-group state changes.
- Fan post-clear holds and unavailable-sensor holds remain separate namespaces.
- Existing deadline extension behavior must match current code exactly. If the
  current code preserves the first deadline for an ID, the helper migration must
  preserve that. If the current code replaces a deadline, the migration must
  preserve that instead.
- Expired holds are pruned before exposing active hold IDs or evaluating policy.
- The next expiry callback remains scheduled for the soonest active deadline.
- Expiry callbacks continue to re-resolve current area states and call the
  domain-owned policy path.
- Callback cancellation and cleanup behavior remain unchanged.
- Cover expected/manual movement detection remains unchanged.

Suggested first extraction:

1. Add pure unit tests for the deadline helper.
2. Convert cover manual hold to use it; cover is simpler.
3. Convert fan hold maps to use two instances.
4. Validate fan/cover unit tests after each conversion.

Do not extract:

- Home Assistant callback scheduling;
- fan controller hold rules;
- cover manual movement detection;
- policy re-evaluation callbacks.

### Candidate B: policy debug attribute updates

Evidence:

- `switch/fan_control.py`
  - `_write_policy_debug_attributes`
  - writes active/suppressed/inactive reasons, target fan entities, and hold IDs
- `switch/cover_control.py`
  - `_write_policy_debug_attributes`
  - writes cover automation targets and manual hold state
- `light_groups/runtime.py`
  - `apply_decision`
  - writes `last_policy_reason`
  - other runtime paths write control/debug attributes such as `controlling`,
    last intent, direct-light activity, and command echo state

Why it may be extractable:

- Multiple domains merge new debug keys into `_attr_extra_state_attributes`.
- Some behavior is mechanical: preserve existing attrs, update specific keys,
  assign the merged dict back.

Why it needs caution:

- Attribute names are user/debug contracts.
- Values are domain-specific and often tested.
- Light-group attributes are more tightly coupled to runtime state than switch
  attributes.

Likely shape:

- A small helper such as:
  - `merge_extra_state_attributes(entity, updates)`
  - or a pure `merged_extra_state_attributes(existing, updates)`
- Keep all key names and value construction in the domain modules.

Suggested extraction:

1. Add a pure unit test for merge semantics.
2. Use it in fan and cover only.
3. Consider light usage only if it reduces code without obscuring state
   ownership.

Do not extract:

- debug key names;
- active reason formatting;
- command echo state;
- last-intent semantics.

### Candidate C: current area-state resolution before re-evaluation

Evidence:

- `switch/fan_control.py`
  - area sensor clear path schedules `run_logic([CLEAR])`
  - run logic calls `resolve_area_presence_states`
  - hold expiry re-resolves current area states
- `switch/cover_control.py`
  - run logic calls `resolve_area_presence_states`
  - manual hold expiry re-resolves current area states
- `light_groups/runtime.py`
  - group event handling uses `_current_area_states_for_group_event`
  - ambient signal changes call `read_area_presence_states`
  - existing helper `resolve_area_presence_states` is already shared
- `switch/climate_control.py`
  - area sensor state changes directly apply configured clear/occupied presets

Why it may be extractable:

- Fan and cover have nearly identical timer-expiry pattern:
  - clear timer handle;
  - resolve current area states from cache + HA state;
  - call `run_logic(states)`.

Why it needs caution:

- Light intentionally distinguishes dispatcher-fresh state from sensor fallback.
- Climate’s direct area-sensor preset behavior is different from fan/cover
  policy re-evaluation.

Likely shape:

- Do not add a new area-state resolver; one already exists.
- Consider a small `rerun_policy_with_current_area_states` helper only if it can
  be typed cleanly and only after deadline-helper extraction shows remaining
  duplication.

Suggested extraction:

- Defer until Candidate A is complete. Reassess remaining duplication after
  fan/cover hold maps are simplified.

Do not extract:

- light-group current-state precedence rules;
- climate direct preset application path.

### Candidate D: target entity state snapshots

Evidence:

- `switch/fan_control.py`
  - reads fan-group state for policy signals
  - reads multiple controller sensor float states
  - reads Trend helper binary states
- `switch/cover_control.py`
  - builds `cover_group_states` from resolved cover group entity IDs
- `light_groups/runtime.py`
  - reads current target on/off state and explicit target state during dispatch

Why it may be extractable:

- Repeated mechanical pattern: read HA states for a known set of entity IDs and
  return a normalized mapping.

Why it needs caution:

- Fan sensor values require float parsing and missing-log behavior.
- Fan Trend helper values use `STATE_ON`, `STATE_UNKNOWN`, and
  `STATE_UNAVAILABLE`.
- Cover only needs raw state strings.
- Light state reads are tied to dispatch decisions and may need on/off-specific
  semantics.

Likely shape:

- Possible pure helpers:
  - `entity_state_strings(hass, entity_ids) -> dict[str, str | None]`
  - `binary_state_values(hass, entity_ids) -> dict[str, bool | None]`
- Keep float parsing in `ControlSwitchBase._read_float_state` unless at least
  one more domain needs it.

Suggested extraction:

- Lower priority. Consider only after timer/debug cleanup.

Do not extract:

- fan sensor selection;
- Trend helper resolution;
- light target dispatch semantics.

### Candidate E: expected self-issued state changes

Evidence:

- `switch/cover_control.py`
  - `_expected_cover_group_state_changes`
  - overridden `_execute_decision` records targets before service calls
  - `cover_group_state_changed` ignores expected changes
- `light_groups/runtime.py`
  - command echo state tracks whether a group change came from Magic Areas or an
    external/manual action
  - runtime effects update command echo state

Why it may be extractable:

- Both domains distinguish Magic Areas-issued changes from external/manual
  changes.

Why it needs caution:

- Cover only needs a small expected-target set.
- Light has richer command echo state, awaiting echo behavior, Adaptive Lighting
  coordination, and runtime effects.

Likely shape:

- Do not extract during the first pass.
- If future cover logic grows, consider a tiny expected-change tracker, but do
  not force light command echo into it.

### Candidate F: control switch disabled gating

Evidence:

- `ControlSwitchBase._extract_relevant_area_states` already handles enabled
  gating for dispatcher events.
- `switch/fan_control.py`, `switch/cover_control.py`, and light runtime also
  gate direct re-evaluation paths with `is_on` or `is_control_enabled()`.

Assessment:

- The reusable dispatcher-event gate already exists.
- Remaining direct-path gates are domain-specific enough to leave in place for
  now.

Do not extract in the first pass.

### Candidate G: service-call execution and runtime effects

Evidence:

- `core/controls/control_group.py` already executes `ControlAction` service
  calls and runtime effects.
- `switch/base.py` already adapts switch entities to policy evaluation and
  execution.
- `light_groups/runtime.py` uses sync policy evaluation and applies runtime
  effects separately before dispatching light actions.

Assessment:

- This is already consolidated enough for now.
- Any further extraction risks hiding light-specific dispatch semantics.

Do not extract in this phase unless direct duplication appears during another
candidate.

## Recommended implementation sequence

### 1. Establish baseline and branch

- Start state for this plan:
  - branch: `fan-cover-default-automation`
  - commit: `2dd86e0`
- Create a dedicated implementation branch from that start state before code
  changes unless the user explicitly chooses to continue directly on
  `fan-cover-default-automation`.
- Run or record current validation baseline:
  - `./scripts/validate.sh`
  - relevant focused switch/policy tests listed below.
- Rebuild CRG before and after structural changes if using graph impact data.
- If baseline validation is already known from the immediately preceding work,
  state the exact command and result instead of rerunning blindly.

Checkpoint discipline:

- Keep the helper addition and each domain migration reviewable as separate
  slices.
- After each slice, inspect the diff before running broader validation.
- Do not proceed from cover to fan if cover required domain-specific adapter
  logic that makes the helper questionable.
- Do not proceed from fan post-clear to fan unavailable holds if the second fan
  namespace needs a different abstraction.
- Commit only after the current slice is coherent and validation appropriate to
  that slice passes.

Focused baseline commands:

```bash
uv run --extra test pytest \
  tests/unit/test_fan_control_switch.py \
  tests/unit/test_cover_control_policy.py \
  tests/unit/test_climate_control_switch.py \
  tests/unit/test_media_player_control_switch.py \
  tests/unit/test_light_group_runtime.py \
  tests/unit/test_control_group_executor.py \
  tests/unit/test_control_group_listeners.py \
  -q
```

### 2. Extract deadline map helper

Create a small pure helper for monotonic deadline maps.

Preferred location:

```text
custom_components/magic_areas/core/controls/runtime_support.py
```

If the helper remains purely generic and does not need control-specific types,
consider `core/controls/timers.py` instead, but avoid creating a broad dumping
ground.

Repository boundary contract:

- `custom_components.magic_areas.core.controls` is the public control API.
- New shared control primitives used outside `core.controls` must be exported
  through `core/controls/__init__.py`.
- Runtime callers such as `switch/*` and `light_groups/*` must import shared
  control primitives from `custom_components.magic_areas.core.controls`.
- Direct imports from `custom_components.magic_areas.core.controls.<module>` are
  side-door imports unless that submodule is explicitly listed as a public
  surface in `tests/unit/test_import_boundaries.py`.
- Do not expand the public-surface allowlist for a new helper unless the module
  itself is intended to be a stable sub-surface with a coherent public API.

Chosen first-pass helper contract:

- name: `MonotonicDeadlineMap`
- module: `custom_components/magic_areas/core/controls/runtime_support.py`
- key type: generic hashable key type
- stored value: monotonic deadline as `float`
- `setdefault_deadline(key, deadline)` preserves an existing deadline
- `set_deadline(key, deadline)` replaces an existing deadline
- `discard(key)` removes one key if present
- `drop_expired(now)` removes expired deadlines and returns removed keys as a
  sorted tuple
- `active_keys(now)` prunes expired deadlines and returns active keys as a
  sorted tuple
- `contains(key, now)` prunes expired deadlines and returns whether the key is
  still active
- `next_delay(now)` returns `None` for no active deadlines, otherwise
  a positive delay until the next active deadline
- `__bool__` returns whether any unpruned deadlines are currently stored; use
  `active_keys(now)` or `next_delay(now)` when expiry pruning is required.

The helper must not read time itself. Callers pass `monotonic()` so tests and
domain code control the clock boundary.

Import/export boundary:

- Export the helper through `core/controls/__init__.py` and import it from
  `custom_components.magic_areas.core.controls`.
- The repository import-boundary tests treat direct imports from
  `core.controls.runtime_support` as side-door imports.
- Do not expose domain-specific aliases from the helper module.
- Do not add an import-boundary allowlist exception for fan or cover. If the
  boundary test fails, fix the import/export surface instead.

Required tests:

- new pure helper tests for:
  - adding a deadline;
  - replacing an existing deadline;
  - preserving an existing deadline when using setdefault semantics;
  - expiring old deadlines;
  - returning sorted active keys as tuples;
  - returning `None` or a positive float from `next_delay()` as appropriate;
  - checking one key after pruning expired deadlines;
  - handling empty maps.

Likely new test file:

```text
tests/unit/test_control_runtime_support.py
```

Cover switch coverage requirement:

- Before migrating cover manual holds, confirm existing tests directly cover
  expected-change suppression, manual-hold deadline replacement, sorted active
  entities, expiry pruning, and callback rescheduling.
- If they do not, add focused coverage in:

```text
tests/unit/test_cover_control_switch.py
```

Migration order:

1. Cover manual holds.
2. Fan post-clear holds.
3. Fan unavailable-sensor holds.

Stop after this if code reduction and clarity are achieved.

Proceed beyond this candidate only if:

- fan and cover runtime files are smaller or materially clearer;
- the helper has no domain-specific names or Home Assistant runtime coupling;
- no production `Any`, casts, or type ignores were introduced;
- focused fan/cover tests pass.

Stop after this candidate if:

- the helper saves little code;
- scheduling becomes harder to reason about;
- fan/cover behavior requires adapter glue to fit the helper;
- preserving behavior requires moving domain rules into the shared module.

Decision record required after this candidate:

- list the helper's production callers;
- state whether line count and complexity moved in the intended direction;
- identify any behavior intentionally left duplicated;
- identify any remaining extraction candidates that are now obsolete;
- decide explicitly whether Candidate B should proceed or be deferred.

Candidate A implementation decision:

- Helper: `MonotonicDeadlineMap`, exported through `core.controls` because
  repository import-boundary tests prohibit switch modules from importing
  `core.controls.runtime_support` directly.
- Production callers:
  - `CoverControlSwitch`
  - `FanControlSwitch`
- Covered behavior:
  - cover manual holds replace existing deadlines;
  - fan post-clear and unavailable holds preserve existing deadlines;
  - expired holds are pruned before active IDs are exposed;
  - fan and cover scheduling still cancel old callbacks and schedule the next
    soonest deadline;
  - expiry callbacks still re-resolve current area state and call domain-owned
    `run_logic`.
- Intentionally left duplicated:
  - Home Assistant callback ownership and `async_call_later` scheduling remain
    in fan/cover switch modules;
  - fan controller hold rules remain fan-owned;
  - cover expected/manual movement detection remains cover-owned.
- Complexity result:
  - repeated raw dict deadline mutation/pruning logic moved behind one typed
    helper;
  - no Home Assistant runtime behavior moved into the helper;
  - no production `Any`, casts, or type ignores were introduced.
- Validation:
  - helper-only ruff, mypy, and tests passed;
  - cover migration ruff, mypy, and tests passed;
  - fan migration ruff, mypy, and tests passed;
  - final focused control validation passed;
  - full `./scripts/validate.sh` passed with `1466 passed`.
- Candidate B decision: defer by default. The remaining debug-attribute
  duplication is small and domain-owned; do not extract it unless a later
  review finds clearer repeated mechanics after this helper is committed.

### 3. Extract attribute merge helper only if still valuable

After deadline cleanup, reassess fan/cover debug attribute code.

Candidate B is deferred by default. Proceed only if the post-deadline code still
has obvious repeated mutation mechanics and the helper clearly removes code
without moving domain key names out of the domain modules.

Required tests:

- pure merge helper behavior;
- existing fan debug attribute tests;
- existing cover manual-hold/debug behavior tests.

Candidate B reassessment:

- Result: deferred.
- Remaining overlap:
  - `FanControlSwitch._write_policy_debug_attributes()` copies existing extra
    state attributes, writes fan-owned keys, and assigns the merged dict.
  - `CoverControlSwitch._write_policy_debug_attributes()` copies existing extra
    state attributes, writes cover-owned keys, and assigns the merged dict.
  - light runtime also mutates extra attributes, but those attributes are tied
    to command echo, Adaptive Lighting coordination, and intent observability.
- Decision:
  - Do not add a debug-attribute helper now.
  - The remaining fan/cover overlap is too small to justify another public
    helper.
  - Debug attribute keys and value construction are domain-owned contracts and
    should remain local.
- Tests:
  - Existing fan and cover tests cover the debug attributes that matter for the
    deadline extraction.
  - No new tests are required because no debug-attribute behavior is changing.

### 4. Reassess remaining candidates

Do not pre-commit to extracting area-state rerun helpers, entity-state snapshots,
or expected-change trackers. Reassess after the first two candidates because the
remaining duplication may be too small or too domain-specific.

For every additional extraction candidate, require:

- at least two direct production callers;
- unchanged public/debug attributes;
- focused tests before and after;
- no new `Any`, casts, or type ignores in production code.

Do not continue to another extraction only because the plan lists a candidate.
Each candidate after deadline cleanup requires a fresh local decision based on
the post-cleanup code.

Each fresh decision must record:

- exact duplicated code or mechanic still present;
- files and callers that would change;
- why the shared helper would reduce code or improve clarity;
- tests that already cover the behavior;
- tests that need to be added before or during the extraction;
- explicit reason for proceeding or deferring.

Remaining candidate reassessment:

- Area-state rerun helper: deferred.
  - Fan and cover both re-resolve current area states in hold-expiry callbacks,
    but the existing shared `resolve_area_presence_states()` already owns the
    reusable behavior.
  - A wrapper around "resolve then call `run_logic`" would mainly hide
    domain-owned scheduling callbacks and add indirection.
- Target entity state snapshots: deferred.
  - Fan reads fan-group state, controller sensor float states, and Trend helper
    binary states.
  - Cover reads raw cover helper state strings.
  - Light reads target on/off and dispatch-specific state.
  - The mechanics look similar, but the value semantics differ by domain.
- Expected self-issued state changes: deferred.
  - Cover has a small expected-target set for service-call echo suppression.
  - Light command echo state is richer and tied to runtime effects and Adaptive
    Lighting coordination.
  - These are not the same contract.
- Disabled gating: not extracted.
  - `ControlSwitchBase._extract_relevant_area_states()` already owns the shared
    dispatcher-event gate.
  - Remaining direct-path gates are domain-specific enough to leave local.
- Service-call execution/runtime effects: not extracted.
  - Existing control-group executor paths already consolidate shared service
    call execution.
  - Further extraction would risk hiding light-specific dispatch semantics.

No additional extraction is justified after Candidate A. The runtime
consolidation work should close after roadmap transfer, final validation, CRG
refresh, and user-approved retirement of this temporary plan.

## Explicit non-goals

- Do not rewrite fan, cover, climate, media, or light policies.
- Do not hide domain states/actions behind generic names.
- Do not change Home Assistant service calls or target entity semantics.
- Do not change debug attribute names unless deliberately versioned and covered.
- Do not redesign light command echo or Adaptive Lighting runtime effects.
- Do not move fan controller reason logic out of fan-owned code.
- Do not move cover preset/manual movement policy out of cover-owned code.
- Do not build a framework that requires domains to contort into a common shape.

## Validation requirements

Helper-only validation:

```bash
uv run ruff check custom_components/magic_areas/core/controls tests/unit/test_control_runtime_support.py
uv run mypy custom_components/magic_areas/core/controls
uv run --extra test pytest tests/unit/test_control_runtime_support.py tests/unit/test_import_boundaries.py -q
```

Cover migration validation:

```bash
uv run ruff check custom_components/magic_areas/core/controls custom_components/magic_areas/switch/cover_control.py tests/unit/test_control_runtime_support.py tests/unit/test_cover_control_policy.py
uv run mypy custom_components/magic_areas/core/controls custom_components/magic_areas/switch/cover_control.py
uv run --extra test pytest tests/unit/test_control_runtime_support.py tests/unit/test_cover_control_policy.py -q
```

If `tests/unit/test_cover_control_switch.py` is added for manual-hold coverage,
include it in the cover migration `ruff` and `pytest` commands.

Fan migration validation:

```bash
uv run ruff check custom_components/magic_areas/core/controls custom_components/magic_areas/switch/fan_control.py tests/unit/test_control_runtime_support.py tests/unit/test_fan_control_switch.py tests/unit/test_fan_controller_policy.py
uv run mypy custom_components/magic_areas/core/controls custom_components/magic_areas/switch/fan_control.py
uv run --extra test pytest tests/unit/test_control_runtime_support.py tests/unit/test_fan_control_switch.py tests/unit/test_fan_controller_policy.py -q
```

Final focused control validation:

```bash
uv run ruff check custom_components/magic_areas/core/controls custom_components/magic_areas/switch custom_components/magic_areas/light_groups tests/unit
uv run mypy custom_components/magic_areas/core/controls custom_components/magic_areas/switch custom_components/magic_areas/light_groups
uv run --extra test pytest \
  tests/unit/test_import_boundaries.py \
  tests/unit/test_fan_control_switch.py \
  tests/unit/test_cover_control_policy.py \
  tests/unit/test_climate_control_switch.py \
  tests/unit/test_media_player_control_switch.py \
  tests/unit/test_light_group_runtime.py \
  tests/unit/test_control_group_executor.py \
  tests/unit/test_control_group_listeners.py \
  -q
```

Full validation before completion:

```bash
./scripts/validate.sh
```

Live simulator validation:

- Not required for pure helper extraction when full tests prove behavior
  unchanged.
- Required if service-call timing, room-control behavior, light/fan/cover action
  selection, Adaptive Lighting coordination, or manual/hold behavior changes.
- Prefer asking the user to run the full simulator suite when needed; it is slow.

## Exit criteria

- Every extraction has at least two production callers.
- Domain policy files and runtime switch files are smaller or materially
  clearer.
- The helper must have at least two production callers before this work is
  considered successful.
- Fan/cover production code should not grow overall unless the added code is
  justified by focused behavior coverage or materially clearer boundaries.
- If the helper adds more code than it removes without a clear readability or
  testability benefit, stop and reassess instead of continuing to additional
  candidates.
- Fan, cover, light, climate, and media behavior remains unchanged.
- Existing debug attributes are preserved or intentionally documented as changed.
- Focused tests and `./scripts/validate.sh` pass.
- CRG is rebuilt after structural changes.
- The roadmap records what was actually extracted, what was deliberately left
  alone, validation evidence, and any still-relevant deferred candidates.
- Do not update the roadmap after every small implementation slice. Update it
  after the consolidation decision is settled, recording final extraction and
  deferral decisions rather than implementation chatter.
- Durable contributor guidance is updated if any current commands, module
  boundaries, or development rules changed.
- This temporary plan is deleted only after it has no unique information left
  outside the roadmap or durable contributor guidance.
