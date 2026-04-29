# Control Intent Engine Plan

## Purpose

Define an independent decision engine for control suppression and arbitration, scoped to
light groups first, while preserving a contract that can later support fan, climate, and
media control without another architecture rewrite.

This plan is intentionally implementation-oriented, but still light enough to revise as
we learn from the first pass.

## Current Problem

Light-group policy currently mixes several concerns in one decision path:

- area-state eligibility (`occupied`, `dark`, `sleep`, `accented`, etc.)
- brightness gating (`inhibit`, `advisory`, `adaptive`)
- suppressive states (`sleep`, `accented`)
- manual override protection
- whole-group service decisions

That makes behavior hard to reason about when states overlap. The concrete case driving
this is `sleep` plus `accented`: some lights may belong to both behaviors, while other
lights should be suppressed by one state or the other. A whole-group `turn_on` or
`turn_off` decision is too coarse for that.

## Goals

- Move suppression and intent arbitration into an independent, pure policy engine.
- Keep v1 runtime integration limited to light groups.
- Support member-level target decisions, not only group-level actions.
- Preserve current default behavior unless a change is explicitly part of this plan.
- Make overlapping state behavior deterministic and test-covered.
- Keep future fan intent arbitration in mind without implementing fan control in v1.

## Non-Goals

- No fan, climate, or media runtime migration in v1.
- No broad coordinator or registry rewrite.
- No persistent combo-group entities unless a later UX requirement needs them.
- No custom label system if Home Assistant Labels can provide the needed metadata.
- No migration away from existing light-group config in the first implementation pass.

## Existing Code Anchors

The engine should fit into the current control-group architecture:

- `custom_components/magic_areas/core/controls/control_group.py`
  - existing `ControlGroupContext`, `ControlGroupDecision`, `ControlAction`, and
    `ControlGroupPolicy` contracts.
- `custom_components/magic_areas/core/controls/control_group_runtime.py`
  - current runtime helpers for area-state reads, listener registration, and group
    registry resolution.
- `custom_components/magic_areas/light_groups/policy.py`
  - current light policy with embedded suppression and brightness decisions.
- `custom_components/magic_areas/light_groups/runtime.py`
  - current light runtime signal gathering, adaptive guard derivation, and service
    execution.
- `custom_components/magic_areas/light_groups/entities.py`
  - current light entity construction and policy wiring.

## Design Decisions

1. Build an independent engine now, scoped to light-group use.
2. Keep the engine pure: no Home Assistant service calls, no registry reads, no entity
   state access.
3. Keep runtime adapters responsible for gathering signals and executing decisions.
4. Prefer virtual intersections over hidden combo entities.
5. Use HA Labels as first-class membership metadata when label-backed membership is
   added.
6. Keep existing config-defined membership as the v1 source of truth unless label access
   proves simple enough to add safely.
7. Make member-level exceptions explicit in the engine output.
8. Treat suppression reason codes as higher priority than brightness or sensor reason
   codes when multiple constraints apply.

## Engine Vocabulary

- **Intent**: a desired behavior requested by current context, such as `regular_light`,
  `sleep_light`, `accent_light`, `humidity_control`, or `odor_control`.
- **Constraint**: a rule that blocks, limits, delays, or narrows an intent, such as
  `sleep_suppression`, `accent_suppression`, or `manual_override`.
- **Decision**: the resolved outcome after all intents and constraints are evaluated.
- **Target**: the entity subset affected by the decision.
- **Reason code**: a stable machine-readable explanation used by tests, diagnostics, and
  entity attributes.

## Draft Engine Contract

Inputs:

- active area states
- new and lost area states
- control group id
- trigger source/context
- available targets
- target memberships by intent/state/category
- current control ownership/manual override state
- optional mode-specific signals such as brightness guard results

Outputs:

- action kind: `activate`, `deactivate`, or `noop`
- explicit target entity ids, possibly an empty set
- reason code
- optional runtime effects, such as command ownership state updates
- optional diagnostics payload for entity attributes

The engine output should be adaptable into the existing `ControlGroupDecision` rather
than replacing it.

## Light v1 Behavior Model

### Membership

The first implementation should model existing light group membership as intent
membership:

- overhead lights -> regular/occupied light intent
- task lights -> task/occupied light intent
- sleep lights -> sleep light intent
- accent lights -> accent light intent

Overlap is allowed. If the same physical light appears in both sleep and accent
membership, the engine should treat it as valid for both intents.

The label-backed membership research phase should explicitly consider whether the current
config groups can become convenience groups that assign predefined HA Labels. In that
model, `overhead`, `task`, `sleep`, and `accent` remain user-facing shortcuts, but the
engine reads membership from labels instead of bespoke group-specific config lists.

### Suppression

Suppressive states should be evaluated independently from turn-on eligibility:

- `sleep` suppresses lights that are not sleep members.
- `accented` suppresses lights that are not accent members.
- If both states are active, a target must survive both constraints unless a specific
  future rule says otherwise.

Example:

- lamp is sleep + accent
- upright lamp is accent only
- soft lamp is sleep only

Expected target eligibility:

- `sleep` active: lamp and soft lamp eligible; upright lamp suppressed.
- `accented` active: lamp and upright lamp eligible; soft lamp suppressed.
- both active: lamp eligible; upright and soft lamp suppressed.

### Brightness

Brightness should remain a light-specific constraint. The control intent engine should
not know how lux, sun state, dwell timers, or attribution guards are calculated.

Runtime/light policy should pass already-derived brightness signals:

- inside bright met
- outside context ok
- dwell/min-on met
- attribution hold met
- ambient rise met

The engine can then apply the configured mode:

- `inhibit`: bright can block or turn off depending on current behavior.
- `advisory`: bright can block turn-on when room is bright but should not force off.
- `adaptive`: bright-driven off must satisfy adaptive guard signals.

When suppression and brightness both apply, suppression wins for diagnostics and
decision reporting. Example: if `accented` is active for TV viewing mode, non-accent
lights should stay suppressed regardless of brightness sensor activity.

### Manual Override

Manual override remains a constraint. Automatic activate/deactivate decisions that would
claim control should be converted to `noop` when the command ownership state indicates a
manual override is active.

## Fan Expansion Readiness

Fan behavior should eventually be modeled as multiple competing intents:

- `humidity_control`
  - threshold plus hysteresis
  - possible rate-of-rise trigger
  - clear threshold or clear dwell
- `odor_control`
  - binary/event trigger
  - hold timer
- `manual_override`
  - user action lockout window
- `quiet_or_sleep_constraint`
  - optional suppression or speed limit

This matters because fan control is not just suppression. It needs arbitration: one
intent may request `on_high`, another may request `on_low`, and a constraint may limit
or delay the result.

The v1 engine should therefore avoid light-only names in core structures. Use neutral
terms like `intent`, `constraint`, `target`, `priority`, and `reason`.

Fan implementation can wait. The v1 contract should remain compatible with fan
arbitration, but the branch should focus on light suppression, labels, and adaptive
lighting interaction first.

## Adaptive Lighting Integration Research

Many users pair Magic Areas with the Adaptive Lighting HACS integration. The control
intent engine should include a research phase for room/group/label-space coordination
with Adaptive Lighting switch entities.

Adaptive Lighting commonly exposes four switches for a room or group:

- brightness adaptation
- color/temperature adaptation
- combined adaptation
- sleep settings

Questions to investigate:

- Can Magic Areas discover Adaptive Lighting switches by room, group, or HA Label space?
- Should Magic Areas suppress or restore Adaptive Lighting during manual override
  cooldowns?
- Should Magic Areas control Adaptive Lighting sleep switches when Magic Areas `sleep`
  is active?
- How should Magic Areas restore Adaptive Lighting after accent/sleep/manual override
  states clear?
- Should Adaptive Lighting control be modeled as its own intent, or as a constraint that
  modifies light intents?

Initial assumption:

- Treat Adaptive Lighting as a separate integration boundary. The first pass should
  research switch discovery and coordination semantics before runtime implementation.

## Proposed File Shape

New core module:

- `custom_components/magic_areas/core/control_intents/__init__.py`
- `custom_components/magic_areas/core/control_intents/models.py`
- `custom_components/magic_areas/core/control_intents/engine.py`
- `custom_components/magic_areas/core/control_intents/light_adapter.py`

Likely light changes:

- `custom_components/magic_areas/light_groups/policy.py`
  - move suppression/overlap decision logic into the engine adapter path.
  - keep light-specific brightness mode inputs and command echo handling.
- `custom_components/magic_areas/light_groups/runtime.py`
  - continue deriving runtime signals.
  - pass target membership/signal payload into policy.
- `custom_components/magic_areas/light_groups/entities.py`
  - wire policy construction with any new adapter inputs.

Test additions:

- `tests/unit/test_control_intent_engine.py`
- `tests/unit/test_light_control_intent_adapter.py`
- focused extensions in `tests/unit/test_core_light_control.py`

## Implementation Phases

### Phase 1: Pure Engine Skeleton

- Add engine dataclasses/protocols.
- Add deterministic intent/constraint evaluation.
- Add target subset support.
- Add stable reason-code handling.

Exit criteria:

- Pure unit tests cover allow, suppress, force-off/noop, and target subset decisions.
- No Home Assistant imports are required by the pure engine module.

### Phase 2: Light Adapter Without Behavior Change

- Build a light adapter that translates existing light policy inputs into engine inputs.
- Preserve current whole-group decisions initially.
- Keep existing tests passing.

Exit criteria:

- Current light policy tests pass.
- New adapter tests prove current `sleep`, `accented`, manual override, and brightness
  behavior is preserved.

### Phase 3: Member-Level Suppression

- Teach the light adapter to resolve eligible target subsets.
- Apply suppressive states by target membership.
- Avoid hidden combo entities; compute intersections at decision time.

Exit criteria:

- Tests cover sleep-only, accent-only, overlap, and neither-member targets.
- Both-states-active behavior matches the example matrix above.
- Runtime decisions can target explicit entity ids.

### Phase 4: Observability

- Expose last intent decision reason on light group attributes.
- Include constrained/suppressed target lists when useful.
- Keep attributes concise enough for Home Assistant details views.

Exit criteria:

- Debug attributes explain why a group did or did not act.
- Tests cover reason-code stability for important paths.

### Phase 5: Label-Backed Membership Investigation

- Determine whether HA Labels can be read cleanly for entity membership in the current
  supported HA version.
- Decide whether labels supplement or replace existing config membership.
- Assess whether switching to label-backed control membership creates broad project
  simplification, especially in light groups and future fan/media/climate control.
- Compare doing label membership before engine integration versus after engine
  integration, with explicit attention to avoided rework.
- Evaluate whether existing config groups can become convenience groups that assign
  predefined labels.

Exit criteria:

- Documented decision before implementation.
- No label migration is required for v1 runtime behavior.

### Phase 6: Adaptive Lighting Coordination Research

- Identify Adaptive Lighting entity naming and registry patterns.
- Determine whether room/group/label matching can reliably find the four switches.
- Define desired behavior for sleep, accent, and manual override cooldown interaction.

Exit criteria:

- Documented integration boundary and first implementable behavior.
- No runtime dependency on Adaptive Lighting unless the user opts in.

## Test Matrix

Core engine:

- one intent, no constraints -> activate expected targets
- one intent, suppressive constraint -> target subset removed
- all targets suppressed -> noop or deactivate according to trigger
- overlapping memberships -> shared target remains eligible
- stable reason codes for each major branch

Light adapter:

- occupied + dark turns on eligible regular targets
- sleep active suppresses non-sleep targets
- accented active suppresses non-accent targets
- sleep + accented active keeps only overlap targets
- manual override blocks automatic reclaim
- advisory bright blocks turn-on when room is bright
- advisory bright does not force off on bright transition
- adaptive bright off requires guard signals

Runtime:

- explicit target subset maps to correct HA service target
- no duplicate service calls for the same entity
- child/all light group behavior remains compatible

Label research:

- existing config membership can be mapped to equivalent label membership
- convenience-group config can assign or imply predefined labels
- label-backed membership reduces code paths rather than adding a parallel system

Adaptive Lighting research:

- same-room or same-label Adaptive Lighting switches can be discovered or configured
- manual override cooldown behavior is explicit
- sleep switch coordination is explicit

## Acceptance Criteria

1. Light-group suppression and exception behavior flows through the control intent
   engine.
2. The engine is pure and independently unit-tested.
3. Overlapping `sleep` and `accented` memberships are deterministic.
4. Existing default light behavior is preserved except for explicitly approved
   member-level suppression fixes.
5. Engine outputs can represent target subsets.
6. Diagnostics expose stable reason codes.
7. The contract is ready for fan arbitration without implementing fan runtime support.
8. Suppression reason codes take precedence over brightness/sensor reason codes.

## Open Questions

1. Does switching to label-backed control membership broadly simplify the project, or
   does it add a second membership system beside config groups?
2. Is label membership more valuable before engine integration, or after the light
   adapter proves the engine shape?
3. Can current config groups become convenience groups that assign predefined labels?
4. Should whole-group entities remain the primary service target when no subset filtering
   is needed, or should label-backed operation always target resolved members?
5. Should suppressed targets be exposed only as debug attributes?
6. How should Adaptive Lighting discovery work: area, config group, label, or explicit
   entity selection?
7. Should Adaptive Lighting coordination be its own intent or a constraint/effect of
   light intents?

## Initial Recommendation

Build the pure engine and light adapter first using existing config membership, but run
label-backed membership research before large runtime rewiring. The research must answer
whether labels simplify enough code to justify doing them early. Treat Adaptive Lighting
as a research item before implementation, with special attention to sleep, accent, and
manual override cooldown behavior.
