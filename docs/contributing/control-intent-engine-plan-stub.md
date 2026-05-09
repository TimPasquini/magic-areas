# Control Intent Engine Plan

## Purpose

Define an independent decision engine for control suppression and arbitration, scoped to
light groups first, while preserving a contract that can later support fan, climate, and
media control without another architecture rewrite.

This plan is intentionally implementation-oriented, but still light enough to revise as
we learn from the first pass.

Status:

- Active again after merging the native Home Assistant feature-reduction branch.
- Native helper and label reconciliation are now available foundation, not future
  research prerequisites.
- Do not implement the intent engine against current custom group entities or
  `ControlGroupDefinition.members` as membership truth.
- First implementation work should define the engine-facing target model and resolver.

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
- No persistent combo-group entities unless a later UX requirement needs them.
- No custom label system if Home Assistant Labels can provide the needed metadata.
- No assumption that the current control-group registry is the right long-term center of
  membership. The research phase must test that assumption before implementation.

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
6. Make member-level exceptions explicit in the engine output.
7. Treat suppression reason codes as higher priority than brightness or sensor reason
   codes when multiple constraints apply.

## Related Plans

- [Label-Backed Control Membership Plan](./label-backed-control-membership-plan.md)
  defines the membership migration that should feed this engine.
- [Native Home Assistant Feature Reduction Plan](./native-ha-feature-reduction-plan.md)
  defines the pre-work to migrate duplicated HA mechanics to native labels/helpers.
- [Native HA Reduction Roadmap](./native-ha-reduction-roadmap.md)
  defines the branch sequence before intent engine work resumes.

## Research Frame

The label-backed membership investigation is no longer only a feasibility check, and it
is no longer only planned. The native HA reduction branch implemented the first concrete
foundation:

- light role labels: `ma:overhead`, `ma:task`, `ma:sleep`, `ma:accent`
- custom control labels: `ma:control:*`
- exact native HA helper groups for room/domain/role surfaces
- managed helper ownership, update, stale cleanup, Repairs surfacing, registry metadata,
  area/device assignment, and source-enumeration exclusion
- owner-scoped managed-label snapshots so deleted custom groups clear only the label
  memberships that Magic Areas previously applied for that entry

The remaining engine work is therefore not "can labels/helpers work?" The remaining
work is "how should runtime consume labels, helper entities, and explicit entity subsets
through a source-neutral target model?"

The working decision is that Magic Areas-owned HA Labels should become the HA-visible
control membership and control-target surface, reconciled from Magic Areas' existing
enumeration and config flows. See the related label plan for the authoritative migration
details.

The origin point remains Magic Areas:

```text
Magic Areas enumerates entities.
Magic Areas config captures user intent and conceptual grouping.
Magic Areas reconciles magic:* labels.
Home Assistant exposes those labels as target/control surfaces.
Magic Areas and other automations can act on those labels.
```

Home Assistant Labels provide storage, visibility, selectors, and native target
execution. They do not decide what a conceptual role like sleep, accent, odor, or
humidity means in a particular room. Magic Areas still owns the guided role-definition
layer.

Architectures to compare:

- **Current registry-centered model**: config groups remain durable concepts and labels
  are not the primary control surface. This is now treated as the legacy/baseline model
  to migrate away from for light-role and custom-control membership.
- **Label-first model**: HA Labels become the durable control membership primitive;
  overhead/task/sleep/accent config groups become convenience UI surfaces that reconcile
  predefined labels.
- **Compatibility transition model**: config surfaces feed label reconciliation, labels
  feed runtime membership resolution, and both compile into the same membership map
  consumed by the engine. This is a bridge, not a permanent two-truth architecture.

The research phase must challenge whether existing abstractions remain useful:

- `ControlGroupDefinition`
- `GroupRegistry`
- category metadata lookups
- built-in light group config lists
- custom control-group `members` lists
- child/parent group entity resolution
- feature-specific grouping paths for fan/media/climate

The output of this phase should be a recommendation, not just a list of insertion
points.

## Research Findings

### HA Label Capability

Home Assistant's installed APIs support Labels on entities, devices, and areas. That
makes a label-backed control model technically plausible, not speculative.

Available local APIs in the supported HA version include:

- `entity_registry.async_entries_for_label(...)`
- `device_registry.async_entries_for_label(...)`
- `area_registry.async_entries_for_label(...)`
- `label_registry.async_get_label(...)`
- `label_registry.async_get_label_by_name(...)`
- `label_registry.async_create(...)`
- registry update calls that can set `labels` on entities, devices, and areas

Implication:

- Magic Areas can read/write labels without owning a custom tagging system.
- Magic Areas should create, update, and remove labels under its own prefix through a
  scoped reconciliation process.
- Magic Areas must not mutate labels outside its owned prefix.

Additional target-resolution findings:

- HA service targets support `label_id`.
- Multiple `label_id` values are expanded as a union, not an intersection.
- Domain services filter the final expanded set to that domain's registered entities,
  but they do not solve role/area intersection.
- Direct `label_id` targeting is safe for broad semantic commands. Exact room/role
  control surfaces should generally come from native HA helper groups rather than scoped
  labels.
- Magic Areas must resolve explicit entity IDs when the desired target means role plus
  area, role plus suppression exception, or multiple labels combined as an AND query.

This means the engine contract must not assume that a set of labels is executable as an
intersection. It should emit a broad label target, an exact helper target, or an explicit
entity subset.

### Current Membership Architecture

Current control membership is stored in integration-owned structures:

- light groups use preset config lists (`overhead`, `task`, `sleep`, `accent`)
- custom control groups store direct `members` lists
- fan/media groups usually derive members from all area entities in a domain
- climate control stores or resolves a single member entity
- feature modules register `ControlGroupDefinition` objects into `GroupRegistry`
- runtime code resolves members or group entities from registry metadata

This means there are two durable membership concepts today:

- feature-specific config membership
- custom control-group membership

The current registry is useful as a compatibility/runtime catalog, but it also makes
member lists look like durable integration-owned truth. The next engine implementation
must not treat it as the primary membership model.

Current post-reduction state:

- Light groups still register `ControlGroupDefinition` entries, but they also reconcile
  role labels and exact native helper group surfaces.
- Runtime light service calls already prefer reconciled native helper targets and fall
  back to hidden custom policy entities.
- Custom control groups still originate in config member lists, but now compile into
  `ma:control:*` label surfaces and cleanup through managed-label ownership snapshots.
- `GroupRegistry` remains important for compatibility, policy lookup, and current tests,
  but it should feed a source-neutral target map rather than the engine consuming it
  directly.

### Label And Native Helper Architecture Impact

If labels become the HA-visible semantic role layer and native helpers become exact
generated surfaces:

- `overhead`, `task`, `sleep`, and `accent` can become predefined label roles.
- Config groups can become convenience UI for reconciling those labels and exact HA group
  helpers.
- Custom control groups can become label queries plus trigger/policy metadata, rather
  than stored entity lists.
- Light category entities may be replaced by native HA helper groups where exact control
  surfaces are needed.
- Runtime can target HA labels directly for broad role actions, native helper groups for
  exact room/role actions, and resolved member subsets for filtered/intersection
  decisions.

The label resolver should not query global labels and then decide what to control. It
should start from Magic Areas' existing area-scoped/domain-scoped entity universe, then
apply label membership inside that boundary. The current entity ingestion path already
handles area/device assignment, include/exclude lists, diagnostic filtering, and
integration-owned entity exclusion. Reusing that boundary prevents a shared label from
accidentally controlling entities in another room.

Label source semantics should be explicit:

- entity labels are precise control membership.
- device labels can expand to entities, but only after domain and area filtering.
- area labels are contextual metadata and should not directly imply every light, fan, or
  media entity in the area belongs to the same control intent.

Potential simplifications:

- less feature-specific member-list schema
- fewer duplicated entity selector lists in options flows
- one membership query model for lights, fans, media, climate, and custom controls
- easier overlap behavior, because an entity can naturally carry multiple labels
- clearer compatibility with external integrations such as Adaptive Lighting

Potential costs:

- HA Labels are user-visible; Magic Areas reconciliation must be predictable and scoped.
- External edits to Magic Areas-owned labels may be overwritten by reconciliation.
- entity labels, device labels, and area labels have different semantics and may need
  explicit precedence.
- label queries must still be scoped by area/domain to avoid cross-room control mistakes.
- migration from existing config lists must be deliberate.
- tests need HA registry fixtures for label read/write behavior.

### Current Registry-Centered Architecture Impact

If the current group registry remains the durable membership center:

- implementation is smaller and fits existing code.
- current tests and config flows remain closer to unchanged.
- labels can be added as an alternate source for group members.

But this risks creating two parallel membership systems. If labels are later promoted to
the real model, engine work built around `ControlGroupDefinition.members` may need to be
rewritten.

### Hybrid Transition Impact

A compatibility model can compile reconciled labels into the same membership map for the
engine while existing config lists remain convenience/reconciliation inputs.

This is likely the safest migration path if we preserve existing users:

- existing config lists continue to work as config/editing surfaces
- labels are assigned during area-scoped reconciliation
- the engine receives a source-neutral membership map
- runtime policy does not read config lists as membership truth

The compatibility model should not become a permanent two-truth architecture. Its value
is preserving current config UX while labels become the runtime membership surface.

### Research Recommendation

Do label/membership modeling before runtime engine implementation.

The engine should not consume `ControlGroupDefinition.members` directly as its primary
model. It should consume a source-neutral role target map or equivalent structure:

- role id
- domain
- area scope
- label target when the action can safely use broad HA `label_id`
- helper target when an exact native HA helper surface exists
- resolved entity subset when policy needs filtering/intersections
- source (`reconciled_label`, `config_reconciliation`, `device_label`, `area_label`, `custom`)
- optional diagnostics

Then the project can compare reconciliation/resolution paths without changing engine
behavior:

- config-list-to-label reconciliation
- label resolver
- compatibility resolver

The reconciliation side of this is now partially implemented. Initial engine work should
therefore prove boundary-safe **runtime target resolution** first:

- start from the Magic Areas area/domain entity universe
- read reconciled Magic Areas-owned labels inside that boundary
- resolve exact native helper entities when present
- carry explicit entity subsets for intersections and suppressions HA labels cannot
  express
- include compatibility data from current config/group registry only as a bridge

The current `ControlAction` shape already supports explicit `target_entity_ids`. That is
not sufficient for the label/native-helper model. The action contract should support
HA-native targets such as `label_id`, exact helper entity targets, and explicit
`entity_id` targets. Member-level suppression and label-backed subsets do not require
hidden combo entities: broad actions can use label targets, exact room/role actions can
use native helper groups, and filtered/intersection actions can use resolved entity
subsets. Magic Areas custom group entities should not remain policy truth.

Action execution should use an explicit target-resolution ladder:

```text
desired role target
-> is the action intentionally broad enough for a global label?
   -> yes: execute with label_id
-> does a native helper entity represent exactly this set?
   -> yes: execute against helper entity
-> otherwise resolve through Magic Areas area/domain boundary and execute with entity_id
```

The engine should not decide the HA registry mechanics. It should emit a target shape
that allows the runtime adapter to choose the safest execution path.

Because HA target syntax does not provide label intersection semantics, `label_id`
execution is not the exact room/role path. If the target is "Living Room sleep lights"
and the available label is broad `magic:sleep`, runtime should use the reconciled native
Living Room sleep helper group or resolve to entity IDs.

Phase 1 implementation notes to preserve:

- The resolver boundary is the right seam for HA registry mechanics. It can normalize
  managed helpers, labels, explicit subsets, and hidden policy entities without knowing
  light policy, suppressive states, adaptive switching, or feature config semantics.
- Broad label execution must remain explicit opt-in. By default, a label resolves to an
  area/domain-filtered entity subset because HA label service targeting is broad and does
  not express area plus role intersection.
- During transition, an existing label that resolves to no entities inside the supplied
  area/domain boundary currently falls through to compatibility fallback. This preserves
  behavior while labels are not yet the only runtime truth. Later cleanup must decide
  whether strict label-runtime mode should treat an empty reconciled label as an empty
  target instead.
- Hidden `AreaLightGroup` policy entities are not labels, helpers, or subsets. They are
  explicitly modeled as compatibility policy targets so they do not masquerade as the
  durable architecture.
- `RoleTarget` is a resolved runtime target record, not necessarily the pure engine's
  final decision shape. The pure engine may reference a `RoleTarget` while emitting
  narrowed explicit entity subsets for suppression/intersection decisions.

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
- available role targets from the runtime target resolver
- role labels, exact helper entities, and resolved subsets by intent/state/category
- current control ownership/manual override state
- optional mode-specific signals such as brightness guard results

Outputs:

- action kind: `activate`, `deactivate`, or `noop`
- HA-native service target, such as `label_id`, or explicit target entity ids
- target-resolution reason, such as exact label target, scoped entity subset, or
  intersection/suppression subset
- reason code
- optional runtime effects, such as command ownership state updates
- optional diagnostics payload for entity attributes

The engine output should be adaptable into the existing `ControlGroupDecision` rather
than replacing it.

## Current Surface Census

Available foundation after native HA reduction:

- `custom_components/magic_areas/core/runtime_model/managed_surfaces.py`
  defines the desired surface primitives:
  - `LabelSurface`
  - `ConfigEntryHelperSurface`
  - `ManagedSurfaceKind.CONFIG_ENTRY_HELPER`
  - stable ownership IDs via `build_managed_surface_unique_id(...)`
- `custom_components/magic_areas/coordinator/managed_surfaces.py`
  reconciles desired surfaces:
  - creates/updates/removes config-entry-backed helpers
  - applies helper registry metadata to attach helper entities to the Magic Areas device
    and HA area
  - creates/updates/deletes labels by name
  - applies entity-label membership while preserving unrelated labels
  - persists owner-scoped managed-label snapshots under
    `MANAGED_LABEL_SURFACES_DATA_KEY`
  - creates Repairs issues for helper reconciliation failures
- `custom_components/magic_areas/core/managed_surface_registry.py`
  is the current lookup boundary for native helper ownership:
  - `iter_managed_surface_config_entries(...)`
  - `iter_managed_surface_entity_entries(...)`
  - `resolve_managed_surface_entity_id(...)`
- `custom_components/magic_areas/features/modules/light_groups.py`
  declares current light surfaces:
  - exact native HA light helper for all area lights
  - exact native HA light helper for each configured role group with members
  - global role labels for each light role
- `custom_components/magic_areas/light_groups/identity.py`
  defines current light role label names:
  - `ma:overhead`
  - `ma:task`
  - `ma:sleep`
  - `ma:accent`
- `custom_components/magic_areas/features/dispatch.py`
  adds custom control label surfaces from normalized custom control groups:
  - `control.task` -> `ma:control:task`
  - arbitrary custom group IDs -> `ma:control:<slug>`
- `custom_components/magic_areas/light_groups/entities.py`
  already dispatches automatic light actions to the native helper entity when
  `resolve_managed_surface_entity_id(...)` finds one, with hidden custom policy entity
  fallback.
- Source enumeration excludes Magic Areas-managed helper entities through managed-surface
  ownership checks in the entity ingestion pipeline.

Still legacy/compatibility surfaces:

- Hidden custom `AreaLightGroup` entities remain the policy, manual-override, command
  echo, listener, and debug-attribute owner.
- `custom_components/magic_areas/core/controls/registry.py` still stores
  `ControlGroupDefinition` entries by area/group ID and filters them by policy.
- `custom_components/magic_areas/core/controls/control_group_runtime.py` still exposes
  registry-based target helpers:
  - `resolve_group_entity_id(...)`
  - `resolve_group_member_entity_id(...)`
  - `resolve_group_entity_ids_by_metadata(...)`
  - `resolve_group_entity_ids_for_metadata_values(...)`
  - `resolve_group_member_entity_id_by_metadata(...)`
- `GroupRegistry` remains the compatibility source for:
  - current fan/media/climate policy target lookup
  - custom control definitions registered from config
- Light suppression, brightness gating, adaptive guards, and manual override decisions
  remain embedded in `light_groups/policy.py` and `light_groups/runtime.py`.
- Custom control group config still stores member lists as guided UI input, even though
  labels are reconciled from those lists.
- Light role config lists still feed both native helper/label reconciliation and current
  compatibility `ControlGroupDefinition` registration.

Current target-surface inventory:

| Surface | Current source | Runtime use today | Engine target role |
| --- | --- | --- | --- |
| Global light role labels | `LightGroupsFeatureModule.desired_managed_surfaces` | HA-visible membership only | membership/possible broad target |
| Native light helper groups | `ConfigEntryHelperSurface` from light groups | automatic light service target | exact room/role helper target |
| Hidden `AreaLightGroup` entities | light feature entity build | policy/manual override/listeners/fallback target | compatibility policy surface |
| Custom control labels | dispatch-managed `LabelSurface` | HA-visible membership only | future custom role target |
| `GroupRegistry` definitions | feature build + snapshot custom groups | member/group lookup | compatibility resolver input |
| Managed helper registry | config-entry unique IDs | resolve native helper entity IDs | exact helper lookup |

Immediate implication:

- Do not start by rewriting suppression inside the existing light policy.
- Start by defining a source-neutral `RoleTarget`/target map that can be produced from
  current labels, helper surfaces, and compatibility registry data.
- Phase 0 should produce a contract that can represent all current target surfaces
  without forcing runtime to choose one execution style prematurely.

Current ownership decision:

- Move target resolution toward the HA-native path now: labels for semantic membership,
  native helper groups for exact room/role service targets, and explicit entity IDs for
  filtered/intersection/suppression subsets.
- Keep hidden `AreaLightGroup` entities as the light policy listener, command echo,
  manual override, and debug owner until the intent engine has a stable target model.
- Treat hidden policy entities as compatibility policy controllers, not durable
  membership truth.
- Do not attempt to eliminate hidden light policy entities in Phase 6. Revisit them only
  after target resolution and intent dispatch are stable enough to preserve manual
  override behavior deliberately.

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

Those shortcuts are still important. Home Assistant cannot infer which lights are
overhead, sleep-safe, task-oriented, or accent-oriented in a specific home. Magic Areas
must provide the guided assignment surfaces, then reconcile the resulting labels.

This also supports a controller-disabled use case: some users may use Magic Areas mostly
as a guided room-role label manager. They still get stable HA labels for automations,
dashboards, and scripts even if Magic Areas is not issuing the final light commands.

The research must also assess whether keeping category light entities is still necessary
under label-backed membership. A label-first design may prefer resolved target subsets
over persistent category group entities, while still preserving user-facing switches or
diagnostics where they provide real value.

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
- `custom_components/magic_areas/core/control_intents/targets.py`

Likely light changes:

- `custom_components/magic_areas/light_groups/intent_adapter.py`
  - light-specific adapter between current light policy concepts and the pure engine.
  - belongs in the light feature slice, not generic core.
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
- `tests/unit/test_control_intent_targets.py`
- `tests/unit/test_light_control_intent_adapter.py`
- focused extensions in `tests/unit/test_core_light_control.py`

## Implementation Phases

### Phase 0: Surface Census And Target Contract

- Confirm current label/helper/custom policy surfaces after native HA reduction.
- Define engine-facing target dataclasses without changing behavior.
- Define target kinds:
  - broad HA label target
  - exact native helper entity target
  - explicit entity subset target
  - hidden compatibility policy entity target during transition
- Define diagnostics fields for target source, resolution path, and fallback reason.
- Keep this pure and HA-free where possible.
- Current concrete target contract should account for:
  - label name and resolved label ID
  - helper unique ID and resolved helper entity ID
  - explicit entity IDs
  - compatibility source, such as `group_registry` or `config_reconciliation`
  - whether the target is broad, exact, or filtered/intersectional
  - fallback order and fallback reason

Exit criteria:

- [x] Plan and tests describe the current surfaces and target contract.
- [x] No runtime behavior changes.
- [x] The engine contract no longer names `ControlGroupDefinition.members` as primary
  membership truth.
- [x] The contract can model every row in the current target-surface inventory table.
- [x] Any remaining dependency on `GroupRegistry` is documented as compatibility input, not
  durable membership truth.

### Phase 1: Runtime Target Resolver

- Build a boundary-safe resolver that starts from the Magic Areas area/domain entity
  catalog.
- Resolve Magic Areas-owned labels inside that boundary.
- Resolve exact native helper entity targets where a managed helper surface exists.
- Provide compatibility fallback from current config/group registry data.
- Represent intersections/suppression subsets as explicit entity IDs.
- Do not make policy decisions in the resolver.

Exit criteria:

- [x] Unit tests cover label role resolution, native helper target selection, and explicit
  subset fallback.
- [x] Tests prove labels are scoped by area/domain boundary before control use.
- [x] Runtime target records can represent `label_id`, helper entity ID, and explicit
  entity IDs.

### Phase 2: Pure Engine Skeleton

- Add engine dataclasses/protocols.
- Add deterministic intent/constraint evaluation.
- Add target subset support.
- Add stable reason-code handling.

Exit criteria:

- [x] Pure unit tests cover allow, suppress, force-off/noop, and target subset decisions.
- [x] No Home Assistant imports are required by the pure engine module.

### Phase 3: Light Adapter Without Behavior Change

- Build a light adapter that translates existing light policy inputs into engine inputs.
- Preserve current behavior initially, but do not hard-code the new path around generated
  group entity targets.
- Keep existing tests passing.
- Phase 3 adapter lives in `light_groups/intent_adapter.py` because it contains
  light-specific semantics. It keeps the current `LightGroupPolicy` authoritative and
  emits matching intent decisions only for actioning cases. Runtime wiring and moving
  suppression into the engine are intentionally deferred to member-level suppression
  work.

Exit criteria:

- [x] Current light policy tests pass.
- [x] New adapter tests prove current `sleep`, `accented`, manual override, and brightness
  behavior is preserved.

### Phase 4: Member-Level Suppression

- Teach the light adapter to resolve eligible target subsets.
- Apply suppressive states by target membership.
- Avoid hidden combo entities; compute intersections at decision time.
- Use HA `label_id` targets for simple role-wide actions where safe.
- First implementation lives in `light_groups/intent_adapter.py` as
  `evaluate_light_member_suppression(...)`. It accepts an already-resolved target plus
  sleep/accent membership sets, builds suppressive constraints, and lets the pure engine
  compute the surviving explicit subset. Runtime wiring into `LightGroupPolicy` remains
  a separate follow-through step.

Exit criteria:

- [x] Tests cover sleep-only, accent-only, overlap, and neither-member targets.
- [x] Both-states-active behavior matches the example matrix above.
- [x] Runtime decisions can target HA labels or explicit entity ids.

### Phase 4b: Runtime Integration For Member-Level Suppression

The completed Phase 4 adapter proves the subset math, but live light control still uses
the existing whole-target runtime path. Phase 4b wires the adapter into live light-group
dispatch without rewriting brightness, manual override, or command echo.

Current runtime seam:

- `light_groups/runtime.py::evaluate_state_change(...)` builds `LightPolicySignals`,
  evaluates `host.policy`, and calls `apply_decision(...)`.
- `light_groups/runtime.py::apply_decision(...)` maps activate/deactivate decisions to
  `turn_on(...)` or `turn_off(...)`.
- `light_groups/runtime.py::_dispatch_controlled_action(...)` checks command ownership
  and current target state, then calls `host._dispatch_light_action(action)`.
- `light_groups/entities.py::AreaLightGroup._dispatch_light_action(...)` currently
  resolves one native helper or hidden policy entity through `_control_target_entity_id()`
  and dispatches a whole-target `ControlGroupDecision`.

Required runtime inputs:

- current area states from the `states_tuple` already handled by `evaluate_state_change`.
- current group target membership from `host._entity_ids`.
- sleep role membership and accent role membership for the same Magic Area.
- current action from the existing `LightGroupPolicy` decision.
- command-echo state and manual override status from the existing runtime path.

Implementation shape:

- [x] Keep `LightGroupPolicy` as the initial action gate during this phase.
- [x] Only evaluate member-level suppression after the existing policy returns an actioning
  decision and command ownership permits dispatch.
- [x] If no suppressive state is active, keep the current helper/policy target path.
- [x] If suppression leaves the target unchanged, keep the current helper/policy target path.
- [x] If suppression narrows the target, dispatch directly to explicit entity IDs.
- [x] If suppression removes all target members, do not dispatch an activate action.
- [x] For suppressive state entry that requires turning off non-surviving members, dispatch
  explicit `turn_off` entity IDs rather than whole helper groups.
- [x] Do not introduce hidden combo entities.

Membership resolution approach:

- Prefer resolved/reconciled role memberships from labels or native helper surfaces once
  available through the target resolver.
- For the first runtime wiring pass, it is acceptable to use the existing light-role
  config membership as compatibility input if that avoids a larger resolver rewrite.
- The compatibility path must remain explicitly transitional in code/tests. It must not
  re-promote `ControlGroupDefinition.members` as durable truth.

Runtime behavior now wired:

- `TURN_ON` in sleep/accent suppression uses the surviving allowed entity subset.
- `TURN_OFF` in sleep/accent suppression uses the non-surviving suppressed entity
  subset, so sleep/accent members are not turned off by the suppression transition.
- Whole-target helper/policy dispatch remains unchanged when no explicit subset is
  required.

Execution target rules:

- Broad label targets are only safe when the intended action is intentionally broad and
  no suppression/intersection filtering is required.
- Exact helper targets remain preferred for room/role actions when the target is not
  narrowed.
- Explicit entity IDs are required for suppression/intersection subsets.

Exit criteria:

- [x] Runtime tests prove an existing whole-target light action still uses the current
  helper/policy target when no suppression subset is required.
- [x] Runtime tests prove sleep-only, accent-only, and sleep+accent overlap dispatch explicit
  entity IDs when suppression narrows the target.
- [x] Runtime tests prove no service call occurs when suppressive states remove all target
  members from an activate action.
- [x] Runtime tests prove suppressive `turn_off` targets only non-surviving members.
- [x] Existing core light policy tests and unit suite remain green.

### Phase 5: Observability

- [x] Expose last intent decision reason on light group attributes.
- [x] Keep policy reason and intent dispatch reason separate:
  `last_policy_reason` explains the existing light policy decision, while
  `last_intent_reason` explains runtime dispatch/suppression gating.
- [x] Include concise target metadata:
  `last_intent_target_entity_ids` is the actual dispatch target,
  `last_intent_allowed_entity_ids` is the surviving allowed subset, and
  `last_intent_suppressed_entity_ids` is the removed/non-surviving subset.
- [x] Expose whether the last intent executed, plus target-state gate details when
  dispatch was skipped because the target was already in the requested state.
- [x] Keep attributes concise enough for Home Assistant details views.

Reason-code expectations:

- `intent_allowed`: no suppressive state narrowed the target.
- `target_partially_suppressed`: suppressive state narrowed the target.
- `target_suppressed`: suppressive state removed every activate target, so no service
  call should occur.
- `control_disabled`: command ownership/manual override prevented runtime dispatch.
- `target_state_mismatch`: runtime state gate prevented duplicate on/off dispatch.

Exit criteria:

- [x] Debug attributes explain why a group did or did not act.
- [x] Tests cover reason-code stability for important paths.

### Phase 6: Label-Backed Runtime Migration Cleanup

Goal: finish moving runtime membership and target selection toward HA-native labels,
native helpers, and explicit resolver outputs. Keep compatibility surfaces only where
they have a concrete runtime or user-facing purpose.

Consolidated current target-surface census:

| Surface | Current status | Current guidance |
| --- | --- | --- |
| Global light role labels | Implemented as `ma:overhead`, `ma:task`, `ma:sleep`, `ma:accent` | Preferred semantic membership truth for light roles |
| Native light helper groups | Implemented for all lights and configured role groups | Preferred exact room/role service target |
| Hidden `AreaLightGroup` entities | Still present, hidden but enabled | Compatibility policy/manual override/listener/debug surface |
| Custom control labels | Implemented as `ma:control:*` | HA-visible custom membership surface; future custom role target |
| `GroupRegistry` definitions | Still present | Compatibility resolver input, not durable membership truth |
| Managed helper registry | Implemented | Exact helper lookup and ownership discovery |

Established guidance:

- Labels define membership.
- Config lists remain guided UI and reconciliation inputs, not preferred runtime truth.
- Native helper entities are preferred for exact room/role service targets.
- Explicit entity IDs are required for filtered, intersection, and suppression subsets.
- Broad HA `label_id` service targets are only safe when the intended action is broad
  enough that area/domain overreach is impossible or irrelevant.
- Hidden custom policy entities are compatibility policy surfaces, not desired final
  membership truth. They remain the light listener/manual-override/command-echo owner
  for now because that is the most behavior-sensitive part of the system.
- Group entities can remain when they provide dashboard, diagnostics, command, or
  compatibility value.
- Group entities should not remain the durable source of policy membership truth.
- Aggregates remain enumeration-based by default; labels are optional metadata there.
- Fan, media, and climate should only adopt role labels when they need intent-level
  membership distinctions.
- Custom control groups should move toward label/query/helper-backed desired surfaces
  while keeping the guided Magic Areas config UI as the authoring surface.

Current Phase 6 direction:

- Prefer Path 2 for target resolution: push runtime target lookup toward the shared
  resolver, HA labels, native helper entities, and explicit resolved subsets.
- Defer the more invasive listener-ownership move: hidden light policy entities stay as
  command echo, manual override, listener, and debug owners until the intent engine can
  replace that responsibility without changing core behavior.
- This gives HA more responsibility for storage, display, helper ownership, and safe
  service target expansion while keeping MA responsible for policy decisions and
  behavior-sensitive override state.

Implemented Phase 6 slice:

- [x] Move light suppression membership consumption from config-first lists to
  reconciled `ma:sleep` / `ma:accent` labels, filtered inside the current light-group
  entity boundary.
- [x] Resolve all-lights child policy entities by stable policy unique IDs instead of
  `GroupRegistry` category metadata.
- [x] Add custom-control target resolution through the shared resolver: reconciled
  `ma:control:*` labels first, config member lists as compatibility fallback.
- [x] Complete light runtime membership census:
  - `light_groups/runtime.py` no longer reads `GroupRegistry` or category metadata as
    runtime membership truth.
  - `AreaLightGroup._resolved_role_members(...)` resolves sleep/accent memberships
    through reconciled labels first and uses config lists only as bounded compatibility
    fallback.
  - `_entity_ids` remains the current light-group entity boundary and suppression source
    set, not durable role membership truth.
  - `category` remains policy/role identity for branching, diagnostics, and stable unique
    IDs.
- [x] Decide generated light group entity purpose:
  - native HA helper groups remain the preferred user-facing dashboard/command/service
    target for exact room/role light groups.
  - hidden `AreaLightGroup` entities remain compatibility policy entities for listener
    ownership, command echo, manual override, fallback dispatch, and debug attributes.
  - generated `ControlGroupDefinition` entries for light groups remain transitional
    compatibility registration only; they should not regain runtime membership authority.
  - parent/all-lights helpers remain useful as exact room-wide command surfaces, while
    parent hidden policy entities remain useful for all-lights policy coordination.
- [x] Decide broad HA `label_id` usage for this phase:
  - broad label targets are safe only for explicitly broad semantic actions where acting
    on every entity with that label is intended.
  - normal room/role automation must not use broad labels because HA label targets are
    not area/domain/role intersections.
  - exact room/role actions should use native helper entities when available.
  - filtered, intersection, and suppression actions should use explicit resolved entity
    IDs.
- [x] Document explicit compatibility-surface reasons:
  - hidden light policy entities: listener ownership, command echo, manual override,
    fallback dispatch, and debug attributes.
  - native helper groups: preferred HA-facing exact command/dashboard surface.
  - `GroupRegistry`: fan/media/climate target compatibility, custom control definition
    compatibility, and transitional light group registration.
  - config member lists: guided user authoring and reconciliation input.

Remaining Phase 6 working checklist:

- [x] Decide which generated category/parent group entities remain useful as dashboard,
  command, diagnostics, or compatibility surfaces.
- [x] Identify any remaining light runtime paths that still read category/group
  membership as truth instead of labels/helpers/resolved subsets.
- [x] Decide custom control membership model for this phase: keep stored config member
  lists as the authoring surface and reconciliation input; prefer reconciled labels for
  runtime target resolution.
- [x] Route custom control target resolution through the same target resolver where
  practical.
- [x] Decide Phase 6 listener ownership: keep hidden `AreaLightGroup` policy entities as
  command-echo/manual-override/listener owners for now.
- [x] Decide which simple actions can safely use broad HA `label_id` targets.
- [x] Document explicit reasons for every compatibility surface that remains after this
  phase.

Deferred beyond Phase 6:

- Revisit whether hidden `AreaLightGroup` policy entities can be reduced or removed after
  the intent engine target model is stable enough to preserve manual override, command
  echo, listener ownership, and diagnostics deliberately.

Current compatibility fallbacks:

- Light sleep/accent suppression now resolves role labels first via `resolve_role_target`.
  If labels are not available yet, it falls back to the configured role members bounded
  by the current light-group entity list. This keeps startup/reconciliation races safe
  without treating config lists as the preferred runtime truth.
- Native light helper service targets fall back to hidden custom `AreaLightGroup`
  entities when the helper does not exist yet. Hidden policy entities also remain the
  owner for light listener state, command echo, manual override, and debug attributes.
- `GroupRegistry` remains available as compatibility input for current fan/media/climate
  target lookup, custom control definitions, and transitional light group registration.
  Light runtime should not consume it as membership truth.
- Custom control group config still stores explicit member lists because those lists are
  the guided authoring surface and reconciliation input. Runtime target resolution can
  consume reconciled `ma:control:*` labels first and fall back to those config members.

Exit criteria:

- Runtime behavior no longer depends on private member lists where reconciled labels or
  native helper targets can provide the same truth.
- Compatibility fallbacks are documented and intentionally scoped.
- Any remaining custom policy entities have an explicit reason to exist.

### Phase 7: Adaptive Lighting Coordination Research

- Identify Adaptive Lighting entity naming and registry patterns.
- Determine whether room/group/label matching can reliably find the four switches.
- Define desired behavior for sleep, accent, and manual override cooldown interaction.

Research findings:

- Adaptive Lighting exposes four switch entities per configuration:
  - main enable switch: `switch.adaptive_lighting_<name>`
  - sleep mode switch: `switch.adaptive_lighting_sleep_mode_<name>`
  - brightness adaptation switch: `switch.adaptive_lighting_adapt_brightness_<name>`
  - color adaptation switch: `switch.adaptive_lighting_adapt_color_<name>`
- The main switch attributes can expose current settings and manual-control state.
- `adaptive_lighting.apply` can apply the current Adaptive Lighting settings to selected
  lights, with the Adaptive Lighting switch passed as `entity_id` and target lights
  passed as `lights`; options include brightness adaptation, color adaptation,
  transition, and whether to turn on lights.
- `adaptive_lighting.set_manual_control` can mark or unmark selected lights as manually
  controlled. This is the likely bridge for resuming Adaptive Lighting after a Magic
  Areas manual override cooldown.
- Adaptive Lighting fires `adaptive_lighting.manual_control` when it marks a light as
  manually controlled.
- Adaptive Lighting manual-control semantics overlap with Magic Areas command echo/manual
  override semantics. The first implementation must not let the two systems fight over
  ownership.
- Adaptive Lighting switches are behavior-control switches, not light power switches.
  They enable, disable, or change adaptation behavior applied to lights while Adaptive
  Lighting remains responsible for calculating brightness/color behavior.
- Adaptive Lighting exposes `adaptive_lighting.change_switch_settings`, but the documented
  service is runtime-only: changed settings are not persisted and reset on Home Assistant
  restart. It also explicitly disallows changing `entity_id`, `lights`, `name`, and
  `interval`, so it is not a durable create/update API for MA-managed configurations.

Discovery constraints:

- Naming convention is predictable but not sufficient as the only resolver because user
  configuration names may not match Magic Areas room/role names.
- Same-room matching may work when Adaptive Lighting switch entities are assigned to the
  same HA area, but that depends on user registry metadata.
- Label matching is promising once Magic Areas reconciles canonical room/role labels, but
  Adaptive Lighting switches will need explicit user labeling or an adapter-owned
  reconciliation step.
- Exact stored references may be necessary for v1 if automatic discovery is ambiguous.

Recommended first implementation boundary:

- Keep Adaptive Lighting optional.
- Offer three user modes per Magic Areas room/role target:
  - `ignore`: Magic Areas does not coordinate Adaptive Lighting for this target.
  - `adopt_existing`: the user associates existing Adaptive Lighting switch sets with
    Magic Areas groups/roles; Magic Areas coordinates those behavior switches.
  - `manage`: Magic Areas creates/updates Adaptive Lighting configurations and maintains
    their members from the enabled Magic Areas groups/roles.
- Model one Adaptive Lighting switch set as an external ambient-control target associated
  with one Magic Areas room/role target.
- Prefer explicit configured switch references first for `adopt_existing`; add label/area
  discovery only when the matching rules can prove a single unambiguous switch set.
- Defer `manage` mode until the Adaptive Lighting create/update surface is researched and
  tested. The intent is still to support it, but not before the adoption path is stable.
- Use Magic Areas' existing manual override state as the authority for when to pause or
  resume Adaptive Lighting behavior switches. Adaptive Lighting owns the adaptive
  brightness/color calculations.
- Treat sleep coordination as an effect of Magic Areas `sleep`: Magic Areas may turn on
  the corresponding Adaptive Lighting sleep switch while sleep is active and turn it off
  when sleep clears, but only for associated switch sets.
- Treat accent coordination as a suppressive/ambient pause: when accent mode intentionally
  creates a viewing scene, Magic Areas may pause brightness/color adaptation for affected
  lights and restore it when accent clears.
- Restoration should clear Adaptive Lighting manual-control state for affected lights
  only after the Magic Areas manual override cooldown expires.
- Do not expand the current in-runtime ambient-rise code while adding Adaptive Lighting
  coordination. Future daylight/adaptive evidence should come from selected user helpers
  or managed native signal helpers such as trend/statistics/derivative helpers.

First implementable behavior:

- [x] Add pure models for an Adaptive Lighting switch set:
  - main switch entity ID
  - sleep mode switch entity ID
  - adapt brightness switch entity ID
  - adapt color switch entity ID
  - associated Magic Areas area ID
  - optional associated Magic Areas role/group ID
- [x] Add resolver tests for explicit switch-set references and complete conventional
  name candidates, without service calls.
- [x] Add a mocked Adaptive Lighting test harness that creates the four behavior switches,
  captures expected `adaptive_lighting.*` service calls, and can fire manual-control
  events without importing the HACS integration.
- [x] Add pure area/label discovery matching that resolves only one complete,
  unambiguous switch set and rejects incomplete or ambiguous matches.
- [x] Bind area/label discovery to HA registries while keeping ambiguity handling in
  the pure resolver.
- [x] Research Adaptive Lighting create/update APIs before implementing `manage` mode.
  Current result: no documented durable service surface exists for creating/updating
  configurations or changing member lights. `manage` mode remains deferred unless a
  public durable config-entry/options API is identified and tested.
- Add no runtime dependency on Adaptive Lighting services until the resolver model and
  ownership rules are tested.

References:

- Adaptive Lighting docs: `https://adaptive-lighting.nijho.lt/`
- Adaptive Lighting services: `https://adaptive-lighting.nijho.lt/services/`
- Adaptive Lighting manual control:
  `https://adaptive-lighting.nijho.lt/advanced/manual-control/`
- Adaptive Lighting sleep mode:
  `https://adaptive-lighting.nijho.lt/advanced/sleep-mode/`

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

- broad role-wide action maps to correct HA `label_id` service target
- exact room/role action maps to the correct native helper target
- explicit target subset maps to correct HA `entity_id` service target
- no duplicate service calls for the same entity
- child/all light group behavior remains compatible

Label research:

- existing config membership can reconcile equivalent label membership
- convenience-group config can assign/update/remove predefined labels
- guided conceptual role assignment remains in Magic Areas config/UI
- label-backed membership reduces code paths rather than adding a parallel system
- label-backed architecture is treated as the runtime membership surface, not only as a
  resolver plugged into current groups
- custom groups are evaluated as label queries or label-backed intent groups

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
6. Engine outputs can represent HA-native label targets for broad role actions.
7. Engine outputs can represent exact native helper targets.
8. Diagnostics expose stable reason codes.
9. The contract is ready for fan arbitration without implementing fan runtime support.
10. Suppression reason codes take precedence over brightness/sensor reason codes.

## Remaining Open Questions

Resolved:

- Custom control groups remain stored config member lists as the guided authoring surface
  and reconciliation input. Runtime target resolution can prefer reconciled
  `ma:control:*` labels.
- Category and parent light helper entities survive as user-facing dashboard/command
  surfaces. Hidden `AreaLightGroup` entities survive as compatibility policy/listener
  surfaces until the intent target model is stable enough to deliberately replace that
  responsibility.
- Service-target preference is now explicit: broad `label_id` only for intentionally
  broad semantic actions, native helper entities for exact room/role actions, explicit
  entity IDs for filtered/intersection/suppression subsets.
- Suppressed/allowed/target subsets are exposed as concise debug attributes on the light
  policy entity.
- Native helper surfaces required before this branch resumed are in place for label-backed
  light roles, native light helper targets, custom control labels, and managed helper
  lookup.
- Adaptive Lighting discovery starts with explicit switch-set references and complete
  conventional name matches only. Label/area discovery waits until ambiguity rules can
  prove a single switch set.
- Adaptive Lighting coordination should be a runtime adapter/side effect first, not a core
  light intent. Magic Areas sets Adaptive Lighting behavior switches based on Magic Areas
  state; Adaptive Lighting performs the adaptive work.
- Adaptive Lighting v1 mode shape is three-way: ignore, adopt existing switch sets, or
  let Magic Areas manage Adaptive Lighting groups. The implementation order should start
  with ignore/adopt existing and defer full management until the Adaptive Lighting
  create/update surface is proven.
- Adaptive Lighting switches are not light power switches. They control adaptation
  behavior applied to the associated lights when those lights are on.

Still open:

1. What exact Adaptive Lighting create/update surface supports `manage` mode, and can it
   safely maintain members from Magic Areas groups?
2. Should Adaptive Lighting switch sets be reconciled with Magic Areas-owned labels, and
   if so which labels are control-critical versus informational?
3. Which native signal-helper bundle, if any, should replace or supplement the current
   in-runtime ambient-rise evidence before adaptive switching resumes?

## Initial Recommendation

Do not start runtime implementation until label/native-helper reconciliation gives the
engine a source-neutral target map. Do native helper reduction before or alongside the
engine model to avoid building the engine around custom group entities we intend to
remove or demote.
Treat Adaptive Lighting as a research item before implementation, with special attention
to sleep, accent, and manual override cooldown behavior.
