# Control Runtime Consolidation Plan

This temporary planning document scopes the control-runtime consolidation work.
Do not delete it while this work is active. Before removal, transfer any still
useful decisions, standards, validation evidence, or deferred defects into
durable contributor guidance such as `docs/contributing/architecture.md`,
`docs/contributing/runtime-boundaries.md`, or `REPOSITORY_WORK_NOTES.md`.

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
| Deadline/hold timer bookkeeping | Implemented | Fan and cover shared concrete monotonic-deadline mechanics; helper kept scheduling and policy re-evaluation domain-owned. |
| Policy debug attribute updates | Implemented for fan/cover | Mechanical attribute merge extracted; user-facing keys and values remain domain-owned. |
| Current area-state resolution before re-evaluation | No new helper recommended | Existing resolver already owns the shared read/fallback behavior; remaining callers have different event semantics. |
| Target entity state snapshots | No extraction recommended yet | Similar reads exist, but value semantics differ by domain. |
| Expected self-issued state changes | No extraction recommended | Cover expected changes and light command echo are not the same contract. |
| Control switch disabled gating | No extraction recommended | Shared dispatcher-event gate already exists; remaining gates are direct-path/domain gates. |
| Service-call execution and runtime effects | No extraction recommended | Existing control-group executor already owns the common behavior. |

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

Evidence inspected:

- `switch/fan_control.py`
  - `aggregate_sensor_state_changed()` resolves from `_last_states` through
    `resolve_area_presence_states()` before running policy.
  - `_area_sensor_state_changed()` deliberately schedules
    `run_logic([CLEAR])` for raw area-sensor clear events.
  - `run_logic()` resolves again from the supplied state list before refreshing
    fan hold deadlines and policy signals.
  - `_hold_expiry_check()` clears only the fan timer handle, resolves current
    area states from `_last_states`, and calls the fan-owned policy path.
- `switch/cover_control.py`
  - `run_logic()` resolves from the supplied state list before building cover
    policy signals.
  - `_manual_hold_expiry_check()` clears only the cover timer handle, resolves
    current area states from `_last_states`, and calls the cover-owned policy
    path.
- `light_groups/runtime.py`
  - `handle_group_state_change()` uses
    `_current_area_states_for_group_event()` so fresh dispatcher state wins over
    HA sensor fallback.
  - ambient signal/source changes call `read_area_presence_states()` and then
    synthesize an area-state callback only for occupied+bright conditions.
  - existing shared helpers already exist:
    `read_area_presence_states()` and `resolve_area_presence_states()`.
- `switch/climate_control.py`
  - dispatcher events evaluate the climate control-group policy.
  - raw area-sensor events directly schedule clear/occupied preset application
    and intentionally do not mirror fan/cover run-loop behavior.

Why it may be extractable:

- Fan and cover have nearly identical timer-expiry pattern:
  - clear timer handle;
  - resolve current area states from cache + HA state;
  - call `run_logic(states)`.

Why it needs caution:

- Light intentionally distinguishes dispatcher-fresh state from sensor fallback.
- Climate’s direct area-sensor preset behavior is different from fan/cover
  policy re-evaluation.
- The existing shared resolver already covers the repeated low-level mechanic.
- A generic "rerun policy" helper would need to accept bound async callbacks and
  timer-handle mutation. That would hide simple domain-owned control flow
  without reducing policy complexity.

Candidate-specific plan if reopened:

1. Prove at least two production callers still contain identical code after
   the deadline helper migration.
2. Keep any helper limited to pure state resolution, not callback scheduling or
   policy invocation.
3. Add focused tests proving cached state precedence and sensor fallback remain
   identical for each caller.

Assessment:

- Do not add a new helper now.
- The correct shared primitives already exist in
  `core/controls/control_group_runtime.py`.
- Fan and cover expiry methods are short, explicit, and domain-specific enough
  that extracting them would mostly move method calls around.

Do not extract:

- light-group current-state precedence rules;
- climate direct preset application path.
- domain policy callback invocation.

Skeptical review:

- The strongest counterargument is that fan and cover expiry handlers are nearly
  identical. That is true, but the duplicated part is only a few lines after
  Candidate A, and the semantics include domain timer ownership and domain
  `run_logic()` calls. A helper would create an abstraction boundary around
  Home Assistant callbacks rather than around a reusable policy concept.
- This conclusion should be revisited only if a third control domain introduces
  the same "timer expiry resolves area states and reruns policy" shape.

### Candidate D: target entity state snapshots

Evidence inspected:

- `switch/fan_control.py`
  - reads fan-group state for `fan_group_state`.
  - reads tracked aggregate/controller sensor values through
    `ControlSwitchBase._read_float_state()`, including domain-specific missing
    entity log messages.
  - reads Trend helper binary states through `_read_trend_signal_state()` where
    `unknown` and `unavailable` both normalize to `None`.
- `switch/cover_control.py`
  - builds `cover_group_states` from resolved cover group entity IDs as raw
    cover state strings.
- `light_groups/runtime.py`
  - `LightGroupRuntimeController.current_control_target_is_on()` resolves the
    managed native helper and normalizes only `on`/`off` to booleans.
  - `_explicit_target_is_on()` computes aggregate on/off state for an explicit
    target subset during suppression-aware dispatch.

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
- The current shared base already owns float parsing for control switches.

Candidate-specific plan if reopened:

1. Inventory exact return contracts before implementation:
   - raw state string mapping;
   - boolean on/off mapping;
   - float parsing;
   - binary trend `unknown`/`unavailable` mapping.
2. Only extract a helper for a contract used by at least two production callers.
3. Keep logging, entity selection, and policy-signal assembly in domain code.
4. Add tests for missing entities and unknown/unavailable handling before
   replacing any reader.

Assessment:

- Do not extract now.
- There is no single repeated contract here. The repeated action is
  `hass.states.get()`, but each caller interprets the result differently.
- Extracting a broad state-snapshot helper would likely increase code and make
  policy-signal construction less explicit.

Do not extract:

- fan sensor selection;
- Trend helper resolution;
- light target dispatch semantics.
- cover policy-state names.

Skeptical review:

- A raw `entity_state_strings()` helper could reduce the cover dictionary
  comprehension. That is too small to justify a shared API unless another
  production caller needs the same raw mapping.
- A boolean on/off helper could serve light target reads, but it would not serve
  fan or cover. It should wait for a second on/off target-state caller with the
  same aggregate semantics.

### Candidate E: expected self-issued state changes

Evidence inspected:

- `switch/cover_control.py`
  - `_expected_cover_group_state_changes`
  - overridden `_execute_decision()` records target entity IDs before service
    calls.
  - `cover_group_state_changed()` consumes one expected entity ID and returns
    without starting manual hold.
- `light_groups/runtime.py`
  - `apply_runtime_effect()` updates `CommandEchoState` from policy runtime
    effects and may schedule Adaptive Lighting manual-control restore.
  - `_dispatch_controlled_action()` marks command issued, records last intent
    attributes, and dispatches the light action.
  - `process_secondary_group_state_change()` distinguishes awaited command echo
    completion from external/manual changes.

Why it may be extractable:

- Both domains distinguish Magic Areas-issued changes from external/manual
  changes.

Why it needs caution:

- Cover only needs a small expected-target set.
- Light has richer command echo state, awaiting echo behavior, Adaptive Lighting
  coordination, and runtime effects.

Candidate-specific plan if reopened:

1. Treat cover and light as separate contracts unless a second cover-like
   caller appears.
2. If a cover-like caller appears, extract only a tiny expected-target tracker
   with consume-once semantics.
3. Do not connect that helper to light command echo unless the light policy
   state machine is deliberately redesigned.

Assessment:

- Do not extract now.
- The common phrase "self-issued change" hides different contracts:
  - cover: one-shot expected target IDs to suppress manual hold;
  - light: command echo state machine tied to runtime effects, control
    ownership, and Adaptive Lighting coordination.

Do not extract:

- light `CommandEchoState`;
- Adaptive Lighting restore scheduling;
- cover manual-hold decision logic.

Skeptical review:

- A small expected-change set helper would be easy to write, but it would have
  one production caller today. That would add code during a reduction-focused
  refactor and would not reduce conceptual complexity.
- Light should not be used as the second caller because matching it to cover
  would either lose behavior or require a helper broad enough to become another
  framework.

### Candidate F: control switch disabled gating

Evidence inspected:

- `ControlSwitchBase._extract_relevant_area_states()` already handles:
  - optional enabled gating with `require_enabled`;
  - area ID filtering;
  - empty dispatcher payload filtering.
- `switch/fan_control.py`
  - passes `require_enabled=False` for dispatcher events so fan can still
    update cached current states.
  - direct raw sensor and run-loop paths check `self.is_on`.
- `switch/cover_control.py`
  - uses the default dispatcher enabled gate and checks `self.is_on` in
    `run_logic()`.
- `light_groups/runtime.py`
  - `handle_area_state_change()`, ambient signal handling, and controller
    `is_control_enabled()` use light-specific switch lookup and fallback rules.

Assessment:

- The reusable dispatcher-event gate already exists.
- Remaining direct-path gates are not the same contract:
  - switch entities use `self.is_on`;
  - light groups consult a separate light-control switch reference and default
    to enabled when missing.

Candidate-specific plan if reopened:

1. Do not duplicate `_extract_relevant_area_states()`.
2. Consider only call-site cleanup if a domain has repeated local `is_on` checks
   with the same logging and same fallback behavior.
3. Preserve fan's intentional `require_enabled=False` dispatcher path.

Do not extract:

- light-control switch lookup/fallback behavior;
- fan cached-state update behavior while disabled;
- run-loop early return logging.

Skeptical review:

- Disabled gating looks superficially repetitive because every control path has
  some guard. The important contract is what "enabled" means. That differs
  between control switches and light groups, so a common helper would either
  take too many callbacks or flatten behavior that is currently explicit.

### Candidate G: service-call execution and runtime effects

Evidence inspected:

- `core/controls/control_group.py`
  - `evaluate_and_execute_control_group_policy()` owns async policy evaluation
    plus execution callback handling.
  - `evaluate_and_execute_control_group_policy_sync()` owns the sync equivalent
    and rejects awaitable execution results.
  - `execute_control_group_runtime_effects()` iterates policy runtime effects.
  - `execute_control_group_decision()` applies runtime effects and HA service
    calls for `ControlAction` entries.
- `switch/base.py`
  - `_evaluate_policy()` adapts switch entities to the shared async evaluator.
  - `_execute_decision()` delegates service calls to
    `execute_control_group_decision()`.
- `light_groups/runtime.py`
  - uses sync policy evaluation because light dispatch is local/synchronous.
  - applies runtime effects, then dispatches light actions through
    light-specific intent and command-echo handling.

Assessment:

- This is already consolidated enough for now.
- Any further extraction risks hiding light-specific dispatch semantics or
  duplicating the executor that already exists.

Candidate-specific plan if reopened:

1. First prove existing executor functions cannot support the desired behavior.
2. Prefer extending `ControlGroupDecision`/`ControlRuntimeEffect` contracts over
   creating parallel execution helpers.
3. Keep light dispatch separate unless light actions become normal
   `ControlAction` service calls with equivalent semantics.

Do not extract:

- light intent suppression;
- command echo state transitions;
- Adaptive Lighting runtime side effects;
- switch blocking/non-blocking execution choices.

Skeptical review:

- This candidate is the weakest extraction candidate because the shared
  executor already exists and is actively used. Additional helpers here would
  likely be wrapper code, not simplification.
- The only plausible future work is improving the existing executor contract,
  not adding a new abstraction alongside it.

### Remaining-candidate skeptical summary

The skeptical pass supports the current recommendations:

- Candidate C has a real fan/cover similarity, but the shared resolver already
  exists and the remaining duplicated expiry methods are small domain-owned
  callbacks.
- Candidate D has repeated HA state reads, but not repeated interpretation
  contracts.
- Candidate E shares a concept name, not a behavior contract.
- Candidate F is already partly shared; the remaining gates intentionally
  define different meanings of enabled.
- Candidate G is already centralized in `core.controls`; more extraction would
  compete with existing infrastructure.

The follow-up rule is: reopen a rejected candidate only when at least two
production callers demonstrate the same input contract, output contract, and
failure behavior. Similar-looking `hass.states.get()` calls or similar event
shapes are not enough.

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
- Candidate B status: pending evaluation. The remaining debug-attribute
  duplication must be inspected directly before deciding whether to extract it.

### 3. Extract attribute merge helper only if still valuable

After deadline cleanup, reassess fan/cover debug attribute code.

Candidate B must be evaluated directly. Proceed only if the post-deadline code
still has obvious repeated mutation mechanics and the helper clearly removes
code without moving domain key names out of the domain modules.

Required tests:

- pure merge helper behavior;
- existing fan debug attribute tests;
- existing cover manual-hold/debug behavior tests.

Candidate B implementation decision:

- Helper: `merged_extra_state_attributes`, exported through `core.controls`.
- Production callers:
  - `FanControlSwitch`
  - `CoverControlSwitch`
- Inspected:
  - `FanControlSwitch._write_policy_debug_attributes()` copies existing extra
    state attributes, writes fan-owned keys, and assigns the merged dict.
  - `CoverControlSwitch._write_policy_debug_attributes()` copies existing extra
    state attributes, writes cover-owned keys, and assigns the merged dict.
  - light runtime also mutates extra attributes, but those attributes are tied
    to command echo, Adaptive Lighting coordination, and intent observability.
- Decision:
  - Extract only the pure mapping merge mechanic.
  - Keep every debug attribute key and value construction in the owning domain
    module.
  - Do not convert light runtime writes during this candidate because those
    writes are stateful runtime observations rather than the same merge
    contract.
- Tests:
  - Added pure helper tests for merge semantics and missing current attrs.
  - Existing fan and cover tests continue to assert domain debug attributes.
- Validation:
  - Candidate B focused ruff passed.
  - Candidate B focused mypy passed.
  - Candidate B focused tests passed, including import-boundary tests.

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

Remaining candidate evaluation checklist:

- Area-state rerun helper:
  - Fan and cover both re-resolve current area states in hold-expiry callbacks,
    but the existing shared `resolve_area_presence_states()` already owns the
    reusable behavior.
  - A wrapper around "resolve then call `run_logic`" would mainly hide
    domain-owned scheduling callbacks and add indirection.
- Target entity state snapshots:
  - Fan reads fan-group state, controller sensor float states, and Trend helper
    binary states.
  - Cover reads raw cover helper state strings.
  - Light reads target on/off and dispatch-specific state.
  - The mechanics look similar, but the value semantics differ by domain.
- Expected self-issued state changes:
  - Cover has a small expected-target set for service-call echo suppression.
  - Light command echo state is richer and tied to runtime effects and Adaptive
    Lighting coordination.
  - These are not the same contract.
- Disabled gating:
  - `ControlSwitchBase._extract_relevant_area_states()` already owns the shared
    dispatcher-event gate.
  - Remaining direct-path gates are domain-specific enough to leave local.
- Service-call execution/runtime effects:
  - Existing control-group executor paths already consolidate shared service
    call execution.
  - Further extraction would risk hiding light-specific dispatch semantics.

Do not close runtime consolidation until each remaining candidate has been
directly evaluated and any user-approved extraction work is complete.

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
