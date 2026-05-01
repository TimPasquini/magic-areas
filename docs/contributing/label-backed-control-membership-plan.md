# Label-Backed Control Membership Plan

## Purpose

Define how Magic Areas should use Home Assistant Labels as the durable membership model
for control intent, starting with light groups and custom control groups.

This plan exists because control membership and control policy are currently tangled. The
control intent engine should not be built around membership structures that we already
expect to replace. Label-backed membership should be settled first, or developed directly
alongside the intent engine, so the engine consumes the right abstraction from the start.

## Core Decision

Magic Areas should treat Home Assistant Labels as the durable HA-visible semantic role
metadata layer for control intent.

The origin point of those labels is still Magic Areas. Home Assistant cannot infer what
"sleep lights", "accent lights", "task lights", "odor control", or "humidity control"
mean in a specific home. Those are human-purpose concepts that Magic Areas must guide the
user through defining.

Correct model:

```text
Magic Areas enumerates entities.
Magic Areas config captures user intent and conceptual grouping.
Magic Areas reconciles magic:* labels from that catalog/config.
Home Assistant exposes those labels as target/control surfaces.
Magic Areas, adapters, dashboards, scripts, and automations can act on those labels.
```

This is only a simplification if labels replace private Magic Areas membership truth. It
is not a simplification if labels are added beside existing config lists as a second
parallel source of truth.

Bad model:

```text
Magic Areas config lists + Magic Areas custom group member lists + HA Labels
```

Good model:

```text
Magic Areas enumerates and catalogs entities as it does today.
Magic Areas config defines area scope, include/exclude rules, and convenience membership.
Magic Areas reconciles its owned HA Labels from that catalog/config.
Magic Areas reconciles exact native HA helper surfaces when exact room/role controls are needed.
Magic Areas runtime can target HA labels directly only for intentionally broad commands.
Magic Areas targets native helper groups or resolved entity subsets when policy requires
room/role exactness, intersections, suppression exceptions, or stricter area/domain
filtering than HA's native target model.
```

Magic Areas keeps responsibility for:

- entity discovery, enumeration, and cataloging
- area/domain scoping
- forced inclusion/exclusion configuration
- canonical role definitions, such as overhead, task, sleep, accent, humidity, and odor
- guided config surfaces for assigning entities to conceptual roles
- computing desired labels from area config and the entity catalog
- reconciliation of Magic Areas-owned labels
- computing subsets when multiple labels/states interact
- control intent logic
- suppression and arbitration
- adapters that derive external integration groups from Magic target groups
- runtime safety checks
- diagnostics
- optional convenience switches/entities

Home Assistant owns responsibility for:

- label storage and native label UI
- native label selectors where useful
- direct `label_id` service targeting when the intended action is broad enough for label
  union semantics
- native helper groups and helper sensors where they meet Magic Areas' generated surface
  needs
- reuse by automations, scripts, dashboards, and other integrations
- exposing Magic Areas' reconciled membership as a normal HA control surface

The important distinction is ownership. Home Assistant owns the label infrastructure.
Magic Areas owns the meaning and reconciliation of labels under its own prefix. The
simplification is not deleting the conceptual grouping UI; it is stopping Magic Areas
from storing and acting on those groupings in private structures after it has calculated
the HA-visible labels.

## Human Problem Boundary

Magic Areas should focus on the actual human problem: making it convenient and guided to
organize room features for common baseline automation.

Examples of conceptual groupings that still need Magic Areas UI/config:

- `magic:overhead`
- `magic:task`
- `magic:sleep`
- `magic:accent`
- future `magic:odor`
- future `magic:humidity`
- future Adaptive Lighting-derived ambient groups

Home Assistant Labels provide storage, visibility, selectors, and broad target execution.
They do not decide what a role means in a particular room. Magic Areas provides that
guided definition layer, then reconciles the resulting labels back into HA.

Global labels are preferred because they match the conceptual intent of labels. Exact
room/role control surfaces should generally come from native HA helper groups rather
than using labels as hidden scoped group IDs.

## Why This Helps The Intent Engine

The control intent engine should answer questions like:

```text
Given these active states and constraints, which target entities should be activated,
deactivated, suppressed, or ignored?
```

It should not need to know whether a target was reconciled from:

- `overhead_lights` config
- `sleep_lights` config
- a custom control-group `members` list
- a group entity's category metadata
- a future label query

If the engine is built directly on current `ControlGroupDefinition.members`, then label
migration will likely require reworking the engine input model. If membership is moved
first into a source-neutral membership map, the engine can stay stable while membership
sources change.

Preferred engine-facing shape:

```text
RoleTarget:
  role
  domain
  area_id
  label_id
  helper_entity_id when exact native helper surface exists
  resolved_entity_ids when needed
  target_kind: label | helper | entity_subset
  source
  diagnostics
```

Example:

```text
role: sleep
  area_id: living_room
  domain: light
  label_id: magic:sleep
  target_kind: label
  source: reconciled_label
```

The engine/action layer should prefer HA-native label targets when the desired operation
is intentionally broad enough for a global role label. It should prefer native helper
groups for exact room/role surfaces and use resolved entity subsets when policy needs
filtering HA cannot express directly.

Then the engine can evaluate suppressive states naturally:

- `sleep` active: allow targets with `sleep` role.
- `accented` active: allow targets with `accent` role.
- both active: allow targets with both roles.

No hidden combo entity is required. Home Assistant supports `label_id` service targets
for broad role-wide commands. Magic Areas can reconcile native helper groups for exact
room/role commands and still resolve explicit entity subsets for filtered/intersection
actions.

## Native HA Label Targeting

Home Assistant service targets support `label_id`. That changes the architecture:
Magic Areas labels are not only metadata and not only an internal membership source.
They can be the actual HA service target for broad straightforward actions.

Implications:

- A broad action like "turn on all Magic Areas sleep-role lights" may target
  `label_id: magic:sleep` instead of expanding the label into entity IDs first.
- Automations and scripts can use the same `magic:*` labels directly.
- Some Magic Areas custom group entities become less important as command surfaces
  because HA labels and native helper groups are HA-native command surfaces.
- Magic Areas still needs its own resolver for operations HA target syntax cannot express,
  such as `magic:sleep AND magic:accent`, suppression exceptions, and area/domain-scoped
  safety checks.
- Adapters can build or maintain external integration groups from canonical Magic target
  labels instead of asking the user to mirror membership manually.

Native HA label targeting expands entity, device, and area labels. Magic Areas should be
deliberate about when it uses native `label_id` targets versus when it resolves to
specific entity IDs:

- First check whether a native `label_id` target can be used without over-reaching or
  under-reaching the intended room/domain/role target.
- Use native label targets when the target set is intentionally broad.
- Use native helper groups when exact room/role control surfaces are needed.
- Resolve to explicit entity IDs when the action requires intersections, exclusions,
  area/domain narrowing, or policy-specific suppression.
- Avoid relying on area labels as direct control targets unless the behavior explicitly
  wants every eligible entity from that area expansion.

This should become an explicit action-target ladder:

```text
desired role target
-> can a label_id represent exactly this target set?
   -> yes: call HA service with label_id
   -> no: resolve through Magic Areas boundary and call HA service with entity_id list
```

The scope question is now answered by combining labels with native helper groups:

- broad role labels are the semantic role metadata surface, such as `magic:sleep`
- native HA helper groups are the exact room/role control surface
- explicit entity resolution remains the policy fallback for intersections and
  suppressions

This avoids turning labels into scoped hidden group IDs while still handing exact group
mechanics back to Home Assistant.

### HA Label Capability Findings

Research against the installed Home Assistant APIs and official documentation found:

- HA labels can be assigned to areas, devices, entities, automations, scenes, scripts,
  and helpers.
- HA labels can be used as targets in automations and scripts.
- Service targets support `label_id` as one string or a list of strings.
- The common HA target resolver expands labels by union, not intersection.
- A target that includes multiple labels means "anything matching any of these labels",
  not "only things matching all of these labels".
- HA target expansion includes directly labeled entities, entities from labeled devices,
  and entities from labeled areas.
- Template helper `label_entities(label)` returns only directly labeled entities; labels
  on devices or areas do not roll up through that helper.
- Device and area label expansion exists in service targeting, but it is broad and must
  be treated carefully for Magic Areas control.
- Entity service handling filters the final target set to registered entities for the
  called domain, so `light.turn_on` will only call light entities from the expanded set.
- HA labels have stable label IDs generated from names; names can be updated while the
  label ID remains the registry key.

Direct implication:

```text
label_id: [magic:sleep, magic:living_room]
```

does not safely mean:

```text
magic:sleep AND magic:living_room
```

It means a union of both label expansions. Therefore, Magic Areas cannot rely on HA
native target syntax for role/area intersections.

This changes the design pressure:

- broad role labels are useful for visibility, dashboards, automations, and broad
  commands.
- exact room/role runtime surfaces should generally be native HA helper groups, not
  scoped labels.
- otherwise, Magic Areas must resolve the intersection through its area/domain boundary
  and send explicit entity IDs.

This does not invalidate the label architecture. It means HA can own semantic label
storage, visibility, and broad targeting, while native HA helper groups own exact
room/role control surfaces. Magic Areas still owns intersection resolution when the
requested target is more specific than any single native surface.

## Current Membership Sources

Magic Areas currently answers "who belongs to this behavior?" differently by feature.

### Light Groups

Current source:

- `overhead_lights`
- `task_lights`
- `sleep_lights`
- `accent_lights`

Current behavior:

- Light group config stores direct entity lists.
- Feature setup turns those lists into category group entities and
  `ControlGroupDefinition` entries.
- Light policy uses group/category state and assigned states to decide on/off behavior.

Target behavior:

- Light group config remains as a guided conceptual assignment surface.
- Reconciliation converts those assignments into `magic:*` labels.
- Simple automation can target those labels directly through HA.
- Magic Areas resolves subsets only for suppressive/intersection behavior.

Relevant code:

- `custom_components/magic_areas/features/modules/light_groups.py`
- `custom_components/magic_areas/light_groups/config.py`
- `custom_components/magic_areas/light_groups/entities.py`
- `custom_components/magic_areas/light_groups/policy.py`
- `custom_components/magic_areas/light_groups/runtime.py`

### Custom Control Groups

Current source:

- area config `custom_control_groups[*].members`

Current behavior:

- Custom groups store direct member entity IDs.
- Schema validates that `members` is a list of entity IDs.
- Normalization builds `ControlGroupDefinition` objects with direct members.

Target behavior:

- Custom groups become guided role/query definitions.
- Reconciliation exposes their target sets as `magic:*` labels.
- Runtime uses label targets for simple actions and resolved subsets for complex
  arbitration.

Relevant code:

- `custom_components/magic_areas/schemas/control_groups.py`
- `custom_components/magic_areas/core/config/area.py`
- `custom_components/magic_areas/core/controls/control_group.py`

### Fan Groups

Current source:

- every fan entity in the area entity universe

Current behavior:

- Feature setup builds one primary fan group from all area fan entities.
- Current behavior is domain membership, not intent membership.

Target behavior:

- Keep the simple all-area fan behavior until there is a real intent split.
- Future bathroom-style fan control should use human-purpose roles such as humidity and
  odor because HA cannot infer those concepts.
- Those roles should reconcile to labels and can become native HA service targets where
  safe.

Relevant code:

- `custom_components/magic_areas/features/modules/fan_groups.py`
- `custom_components/magic_areas/core/controls/policies/fan.py`
- `custom_components/magic_areas/switch/fan_control.py`

### Media Player Groups

Current source:

- every media player entity in the area entity universe

Current behavior:

- Feature setup builds one primary media player group from all area media player entities.
- Current behavior is domain membership, not intent membership.

Target behavior:

- Keep simple all-area behavior until a useful intent split exists.
- Future announcement, accent/media, or presence roles can reconcile to labels.

Relevant code:

- `custom_components/magic_areas/features/modules/media_player_groups.py`
- `custom_components/magic_areas/core/controls/policies/media.py`

### Climate Control

Current source:

- one explicitly configured climate entity

Current behavior:

- Climate control stores a single selected entity and registers it as the group member.

Target behavior:

- A single explicit selector may remain simplest.
- Label-backed climate roles should only be added when multiple conceptual targets exist.

Relevant code:

- `custom_components/magic_areas/features/modules/climate_control.py`
- `custom_components/magic_areas/core/controls/policies/climate.py`

### Aggregates

Current source:

- area/domain/device-class/entity-category enumeration

Current behavior:

- Aggregates are observational, not control intent membership.
- They should continue to use area entity enumeration and device-class style selection.

Relevant code:

- `custom_components/magic_areas/core/aggregates/*`
- `custom_components/magic_areas/coordinator/pipeline/entity_ingestion/*`

## Specific Replacement Accounting

| Current Item | Label Replacement | Advantage | Disadvantage |
| --- | --- | --- | --- |
| `overhead_lights` config list | Reconcile to `magic:overhead` or equivalent role label | Config remains guided assignment; HA receives visible/reusable control target | External label edits may be overwritten by reconciliation |
| `task_lights` config list | Reconcile to `magic:task` role label | Same entity can be task plus sleep/accent without extra schema handling | Role naming must be clear to avoid user confusion |
| `sleep_lights` config list | Reconcile to `magic:sleep` role label | Sleep suppression becomes target-role filtering; simple actions can target label directly | Accidental config/label mismatch must be corrected by reconciliation |
| `accent_lights` config list | Reconcile to `magic:accent` role label | Accent/TV mode suppression becomes target-role filtering; simple actions can target label directly | External edits can alter behavior until reconciliation corrects them |
| Light category metadata | Partially replace | Policy can use target roles instead of category metadata as truth | Metadata may still be useful for diagnostics/entity naming |
| Parent `all` light group membership | Partially replace | Runtime can target labels or resolved members directly | `all` group may remain useful as a user-facing light entity |
| Custom control group `members` | Strong replacement candidate | Custom groups can become label queries plus trigger/policy metadata | Requires a query/editor UX instead of simple entity picker |
| Custom control group templates | Replace/reshape | Templates can create suggested label/query patterns | Needs better presentation than raw label IDs |
| Fan group all-area membership | Not immediate replacement | Future labels can express `humidity_control`, `odor_control`, `quiet`, etc. | Current simple behavior may not benefit yet |
| Media player all-area membership | Not immediate replacement | Future labels can express announcements, TV, playback, etc. | Current simple behavior may not benefit yet |
| Climate single configured entity | Maybe later | A label can identify the room climate target | Single explicit selector may stay simpler and safer |
| Aggregate membership | Do not replace by default | Current area/domain/device-class enumeration fits observational aggregation | Labels only help for future opt-in aggregate subsets |
| Entity ingestion area enumeration | Do not replace | This is the safety boundary for area/domain scoping | Native label targets may bypass this unless labels are area-specific or Magic Areas resolves first |
| `GroupRegistry` durable members | Partially replace | Registry can become runtime/presentation catalog instead of membership truth | Existing tests and resolution helpers rely on it |
| Group builder helpers | Partially shrink | Less feature-specific member-list construction | Still needed if group entities/switches remain |
| Light options entity selectors | Keep/reshape as guided assignment surfaces | Magic Areas captures conceptual intent, then reconciles labels | UI must clearly explain that saved config drives labels |
| Adaptive Lighting matching | Adapter-created groups from canonical Magic targets | Users do not manually mirror Adaptive Lighting groups; adapter derives them from Magic roles | Requires adapter-specific reconciliation semantics |

## Label Naming

Magic Areas labels should have a short, predictable prefix. The current working prefix is
`magic:`.

Reasons:

- Short enough to use comfortably in HA UI and YAML.
- Clearer than `ma:` for users who do not already know the abbreviation.
- Distinct enough to avoid colliding with ordinary user labels.

The exact prefix can still be changed before implementation, but the plan assumes a
single Magic Areas-owned prefix and avoids long labels such as `magic_areas:*`.

## Label Semantics

Labels should represent control roles or intent membership, not raw implementation groups.

Candidate built-in labels:

- `magic:overhead`
- `magic:task`
- `magic:sleep`
- `magic:accent`

Future fan labels may include:

- `magic:humidity`
- `magic:odor`
- `magic:quiet`
- `magic:sleep_exempt`

Future media labels may include:

- `magic:announcement`
- `magic:media_presence`
- `magic:accent_source`

Future Adaptive Lighting-derived labels may include ambient groups generated from
canonical Magic target groups. The exact names should be decided with the adapter design,
but the adapter should derive them from Magic role labels instead of requiring separate
manual membership.

Optional aggregate/member labels may use a longer structured form because they are more
informational and less frequently typed:

- `magic:agg:sensor:<area> <device_class>`
- `magic:agg:binary_sensor:<area> <device_class>`

Exact label names are not finalized. The important decision is that labels express
control intent membership and should be stable, visible, and documented.

Because HA target syntax does not provide label intersections, labels should remain
semantic rather than becoming a scoped group system:

- broad role labels, such as `magic:sleep`
- optional informational labels, such as aggregate/member labels

Exact room/role command surfaces should be native HA helper groups where possible. If a
future case proves that scoped labels are still needed, that should be treated as a
specific exception rather than the default label model.

## Label Source Semantics

Home Assistant supports labels on entities, devices, and areas. These should not all mean
the same thing.

Entity labels:

- Most precise source.
- Best default for control membership.
- Should directly assign a target entity to a role.

Device labels:

- Can expand to entities on the device.
- Must be filtered by area and domain before becoming control targets.
- Useful when a device has several same-purpose entities, but risky when a device exposes
  mixed-purpose entities.

Area labels:

- Should be contextual metadata only.
- Should not directly mean every light, fan, or media player in the area belongs to a
  control role.
- May be useful for discovery, presets, or UI grouping later.

## Reconciliation Model

Magic Areas should assign, update, and remove its owned labels through reconciliation.
The purpose is to keep HA's visible label surface aligned with the Magic Areas area
configuration and entity catalog.

Reconciliation inputs:

- existing Magic Areas discovery and entity enumeration
- current area configuration
- include/exclude entity configuration
- feature configuration such as overhead/task/sleep/accent convenience membership
- optional metadata features, such as aggregate-member labeling
- adapter configuration that derives external integration groups from Magic target groups

Reconciliation triggers:

- initial area creation/config flow completion
- options/config save for that area
- registry/entity changes that already trigger Magic Areas reload or refresh behavior
- a periodic or debounced reconciliation cycle if needed to prevent stale labels

Reconciliation behavior:

- create missing Magic Areas-owned labels as needed
- assign Magic Areas-owned labels to entities that should have them
- remove Magic Areas-owned labels from entities that no longer match
- leave non-Magic-Areas labels untouched
- do not infer control membership from labels outside the Magic Areas prefix

This is not a passive label-reader model. The labels have to actually get assigned and
kept current. The simplification comes from making Home Assistant Labels the exposed
membership surface while Magic Areas owns only the reconciliation logic for its prefix.

Reconciliation should be a set-diff, not a large workflow engine:

```text
desired = labels calculated from current Magic Areas catalog/config
current = current users of each Magic Areas-owned label in HA
add = desired - current
remove = current - desired
```

An "update" is normally an add of a new label plus removal of an old label. Bulk migration
from an old label group to a new label group should be treated as an explicit migration
operation, followed by retiring the old label.

## Resolution Boundary

Label resolution must not start with a global label query and then act on everything it
finds.

Required flow:

```text
Magic Areas area entity ingestion
-> area/domain-scoped entity universe
-> apply include/exclude/diagnostic/integration-owned filtering
-> reconcile Magic Areas-owned labels for this area
-> build role targets:
   - native label target when safe
   - resolved entity subset when filtering/intersection is required
```

Reason:

- The same label can exist on entities in many rooms.
- Magic Areas must not accidentally control another room because the label matched.
- Existing entity ingestion already handles the area safety boundary.
- HA service targets union multiple labels, so Magic Areas cannot express room/role
  intersections by passing multiple `label_id` values to a service call.

Runtime rule:

- Use direct `label_id` only when one label already represents the exact intended target.
- Use explicit entity IDs for role/area intersections, suppression exceptions, and
  anything that needs Magic Areas' area/domain safety boundary.
- Prefer entity labels for precise control membership.
- Treat device and area labels as broad inputs that require filtering before control.

## Relationship To Group Entities And Switches

Label-backed membership does not require deleting group entities.

Group entities and switches can remain useful as:

- command surfaces
- dashboard entities
- diagnostics surfaces
- compatibility surfaces
- convenience controls for resolved label-backed targets

But they should not be the source of policy truth, and they are no longer the only
reasonable command surface. HA label targets can cover simple role-wide commands.

Preferred relationship:

```text
Labels define membership.
Native HA label targets handle simple role commands.
Resolver produces target subsets for filtered/intersection commands.
Intent engine decides actions.
Group/switch entities expose control and diagnostics.
```

This avoids building policy around whether a category group entity exists or which parent
entity contains which child categories.

### The Group Entity Dilemma

The unresolved question is not whether group entities are useful. They are useful. The
question is which responsibility they should retain after labels become the exposed
membership/control surface.

The dilemma:

- If group entities remain the policy target, Magic Areas keeps a private grouping system
  under the label system and loses much of the simplification.
- If group entities are removed too aggressively, users lose convenient dashboard
  controls, diagnostics, and compatibility with existing expectations.
- If group entities are generated from labels but policy also reads labels directly, the
  project must be explicit that labels are truth and group entities are derived surfaces.

Information needed to solve it:

- Which existing group entities are used by current behavior as policy truth versus only
  as command/display surfaces.
- Whether HA `label_id` targets can safely replace each whole-group service call.
- Whether a generated group entity provides user value that a label target does not
  expose well in the HA UI.
- Whether keeping a group entity creates duplicate state, duplicate listeners, reload
  churn, or confusing diagnostics.

Working rule:

- Keep group entities when they provide visible user value or compatibility.
- Do not let group entities remain the durable source of membership truth.
- Prefer labels or resolved entity subsets as runtime targets when that avoids a private
  duplicate grouping layer.

## Configuration Relationship

Magic Areas config remains necessary.

The config flow and options flow still define:

- which Home Assistant area is represented by the Magic Area entry
- include/exclude entity rules
- ignored diagnostic behavior
- feature enablement
- convenience membership surfaces such as overhead/task/sleep/accent lights
- optional metadata labeling features
- adapter configuration for derived external groups

The change is that convenience membership surfaces should be treated as guided conceptual
assignment surfaces. They reconcile labels instead of remaining private long-term
membership stores. For example, editing the overhead-light selection updates the
`magic:overhead` labels for that Magic Area's scoped light entities.

Forced include/exclude settings should remain config-first because they define the entity
universe before label reconciliation and target resolution happen.

Magic Areas may also be useful for users who do not enable Magic Areas controller
features. In that use case, Magic Areas acts as a guided room-role label manager:

- users think in terms of jobs within a room
- Magic Areas helps assign devices/entities to those jobs
- Magic Areas reconciles durable HA labels from that assignment
- dashboards, scripts, and other automations can target those labels directly

This is a valid product shape, not a secondary accident. The label manager abstraction is
valuable even when Magic Areas is not the component issuing the final service calls.

## Optional Informational Labels

Control labels are mandatory for label-backed control resolution. Informational/meta
labels should be opt-in.

Potential opt-in labels:

- aggregate members, such as `magic:agg:sensor:living room temperature`
- groupable category membership that is useful for dashboards or external automations
- diagnostic labels that explain why an entity is part of a generated surface

These labels should not be required for core control behavior. They expose useful
cataloging information to HA without turning every aggregate or sensor category into a
control-membership concern.

## Migration Strategy

The migration should be explicit and reversible during development.

### Phase 1: Label API And Boundary Resolver

- Add label read/write helpers for Magic Areas-owned labels.
- Add a resolver that reads labels only inside the existing area/domain entity universe.
- Prove the boundary before broad reconciliation writes are enabled.
- Produce diagnostics showing which entities matched each role and source.

Exit criteria:

- Unit tests prove entity labels resolve only inside the current area/domain boundary.
- Device labels expand only after area/domain filtering.
- Area labels do not directly create target membership.
- Non-Magic-Areas labels are ignored by Magic Areas membership resolution.

### Phase 2: Source-Neutral Membership Map

- Build a role target map that is populated from reconciled labels.
- Keep compatibility inputs able to generate the same map during transition.
- Make the future intent engine consume this map instead of direct group members.
- Preserve current behavior by compiling current config-list membership into labels and
  then resolving labels.
- Represent both native label targets and resolved entity subsets so policy can choose the
  least custom execution path that is still safe.

Exit criteria:

- Existing light config can produce the same effective membership map as current behavior.
- Reconciled label membership can produce the same map without direct policy reads from
  config lists.
- Diagnostics show source per target/role.
- Tests prove simple role actions can target HA labels directly.
- Tests prove intersection/suppression actions resolve entity subsets instead of using
  overly broad label targets.

### Phase 3: Area-Scoped Reconciliation

- Run reconciliation when a Magic Area is created.
- Run reconciliation when an area's options/config are saved.
- Run reconciliation when registry/entity changes require the area catalog to refresh.
- Scope each reconciliation to the affected Magic Area unless a broader operation is
  explicitly requested.

Exit criteria:

- First-time config flow completion assigns labels for that area.
- Options/config save updates labels for that area.
- Removed/excluded entities lose Magic Areas-owned labels for that area where applicable.
- Reconciliation does not touch labels outside the Magic Areas prefix.

### Phase 4: Label-Backed Light Control

- Use labels as the primary membership source for light roles.
- Keep config lists as convenience editing surfaces that drive reconciliation.
- Make light suppression consume target roles instead of category group membership.
- Use native `label_id` targets for simple role-wide actions where safe.
- Use explicit entity targets for sleep/accent intersections and suppression exceptions.

Exit criteria:

- Sleep/accent overlap is resolved by target labels.
- Existing group entities still work as command surfaces.
- Policy no longer needs category group entities as membership truth.
- Simple label-target service calls are supported where they preserve area/domain safety.

### Phase 5: Custom Control Groups As Label Queries

- Replace direct custom `members` lists with label query definitions where possible.
- Preserve trigger states and policy metadata.
- Use config UI as a convenience surface for defining/reconciling custom labels.

Exit criteria:

- A custom control group can target entities by label query inside area/domain scope.
- Existing custom groups can reconcile labels or compile into the same membership
  map during compatibility transition.

### Phase 6: Evaluate Fan, Media, Climate Expansion

- Do not force labels into fan/media/climate just because the resolver exists.
- Add labels only where they express useful control intent distinctions.

Fan candidates:

- humidity control
- odor control
- quiet/sleep constraints
- manual-only exclusions

Media candidates:

- announcement targets
- TV/accent mode targets
- presence/media-state targets

Climate candidates:

- primary thermostat target
- auxiliary climate target

Exit criteria:

- Each expansion has a concrete behavior reason, not just architectural symmetry.

## Interaction With Adaptive Lighting

Adaptive Lighting is a strong reason to expose canonical Magic target groups through HA
labels.

Intent:

- Do not require the user to manually mirror Magic Areas role groups into Adaptive
  Lighting.
- Build an adapter that can create or maintain Adaptive Lighting groups from Magic Areas
  room/role memberships.
- Let the adapter derive ambient groups from Magic room/role concepts such as overhead,
  task, sleep, and accent.
- Example: a Bedroom overhead role in Magic Areas should be able to produce or maintain a
  corresponding Adaptive Lighting group for Bedroom overhead lights.
- The Adaptive Lighting group would expose its normal control switches for brightness
  adaptation, color/temperature adaptation, combined adaptation, and sleep mode.
- Magic Areas can then coordinate those switches according to Magic Areas room states,
  manual override cooldowns, and role membership.

Potential label uses:

- label Magic Areas-controlled lights and related Adaptive Lighting switches/groups with
  the same room/control-space labels.
- identify which Adaptive Lighting switches should be suspended during manual override.
- identify which Adaptive Lighting sleep switch corresponds to a Magic Areas sleep role.
- restore Adaptive Lighting after Magic Areas accent/sleep/manual override states clear.

Adaptive Lighting should remain an optional integration boundary. Magic Areas should not
require Adaptive Lighting or create a runtime dependency unless the user opts in.

Known constraints:

- Adaptive Lighting groups are configured manually today.
- One Adaptive Lighting group may represent a whole room or a subset of a room.
- That shape resembles Magic Areas role groups such as overhead, lamp, sleep, or accent.
- Automations can apply Adaptive Lighting settings, so the integration exposes surfaces
  that another integration or adapter may be able to coordinate with.
- The adapter should derive Adaptive Lighting membership from Magic Areas' resolved
  memberships, not from a separately maintained user mirror of the same light lists.

Deferred decisions:

- exact Adaptive Lighting API/service/config surface for creating or updating groups
- whether Adaptive Lighting control is modeled as an intent, a constraint, or a runtime
  effect
- cooldown semantics after manual override
- whether Magic Areas sleep should command Adaptive Lighting sleep mode
- whether generated Adaptive Lighting groups should be identified by labels, naming
  convention, config entry metadata, or explicit stored references

## Advantages

- Hands durable control membership back to Home Assistant instead of maintaining a
  private parallel grouping system.
- Keeps Magic Areas focused on guided room-role organization, which is the actual human
  problem.
- Makes membership visible and reusable outside Magic Areas.
- Uses HA's native `label_id` service-target surface for simple commands.
- Reduces feature-specific entity-list config over time.
- Makes overlapping roles natural because an entity can carry multiple labels.
- Positions the intent engine around target roles instead of group entity shape.
- Improves future interoperability with Adaptive Lighting, dashboards, scripts, and HA
  automations.

## Disadvantages And Risks

- HA Labels are user-visible; Magic Areas reconciliation must be predictable and scoped.
- External edits to Magic Areas-owned labels may be overwritten by reconciliation.
- Label naming must be stable and understandable.
- Device and area labels can be ambiguous if treated as direct target membership.
- Native HA label targets can be broader than Magic Areas' intended area/domain scope if
  labels are not reconciled narrowly.
- The transition can temporarily increase complexity if config lists and labels both act as
  active truth instead of config driving reconciliation and labels driving runtime.
- Tests need registry fixtures for label behavior.
- UI work is needed so users understand which config surfaces drive label reconciliation.
- The docs and UI must avoid implying HA labels can infer human-purpose roles by
  themselves.

## Non-Goals

- Do not replace aggregate entity enumeration with labels by default.
- Do not require labels for simple fan/media/climate behavior until a real intent split
  needs them.
- Do not create a Magic Areas-specific tagging system parallel to HA Labels.
- Do not mutate labels outside the Magic Areas-owned prefix.
- Do not require hidden combo group entities for overlapping roles.

## Acceptance Criteria

- A source-neutral membership map exists and is populated from reconciled labels.
- Magic Areas config remains the guided source for conceptual role assignment.
- The action/target model can represent both `label_id` targets and explicit entity IDs.
- Action execution first checks whether `label_id` can target the desired set without
  over-reach or under-reach; otherwise it resolves to explicit entity IDs.
- Label resolution is constrained to Magic Areas' area/domain entity universe.
- Entity labels, device labels, and area labels have explicit semantics.
- Light role membership can be represented by HA Labels.
- Existing light config reconciles Magic Areas-owned labels for the current area.
- The control intent engine consumes resolved target roles, not direct config lists.
- Simple role-wide actions can use HA native label targets when safe.
- Filtered/intersection actions use explicit entity targets.
- Group entities/switches remain command/diagnostic surfaces rather than policy truth.
- Magic Areas can act as a guided room-role label manager even when controller features
  are not enabled.
- Aggregates continue using area/domain/device-class enumeration.
- Tests cover label resolution, boundary safety, compatibility mapping, and role overlap.
- Reconciliation creates, updates, and removes Magic Areas-owned labels without touching
  unrelated HA labels.

## Settled Decisions

- Use a short predictable prefix. Current working prefix: `magic:`.
- Magic Areas will reconcile its owned labels; it is not only a passive label reader.
- Reconciliation is area-scoped during area creation and area config/options save.
- Existing discovery, enumeration, and cataloging remain required.
- Config remains the place for include/exclude rules and conceptual membership editing.
- Label-backed control resolution is mandatory for this model, not an optional alternate
  resolver.
- HA native `label_id` targets should be used where they are safe and reduce custom
  expansion logic.
- Magic Areas must still resolve entity subsets when HA label targeting is too broad for
  the policy decision.
- Aggregate membership remains enumeration-based; aggregate-member labels are opt-in
  metadata only.
- Adaptive Lighting stays conceptual/research-aware until its matching and coordination
  semantics are defined, but the intent is adapter-created ambient groups from canonical
  Magic target groups.

## Remaining Open Questions

1. Is `magic:` the final prefix, or should another short prefix be selected before
   implementation?
2. Should device-label expansion be enabled by default, or only after entity-label
   behavior is proven?
3. Which optional metadata labels are worth exposing after the native helper model is
   implemented?
4. Which generated group entities should be replaced by native HA helper groups first?
5. Which generated group entities provide enough user/compatibility value to keep, and
   which can be demoted once native helper groups become the exact control surface?
6. How should the Adaptive Lighting adapter create/maintain ambient groups from Magic
   room/role memberships?
7. How much native helper migration should land before the first control intent engine runtime
   integration?

## Working Recommendation

Do label-backed semantic metadata and native helper reconciliation before or directly
alongside the control intent engine.

The first implementation should not try to convert every feature to labels. It should
focus on the places where labels and native helpers clearly replace private control
membership:

- global role labels
- exact native helper groups for role/domain surfaces
- custom control group membership where it can compile into labels/helpers

Aggregates should keep Magic Areas' enumeration/selection model, but their generated
surfaces are now candidates for native HA helper reconciliation. Fan, media, and climate
should only adopt role labels when they need intent-level membership distinctions.

The safest path is a compatibility transition internally, but not a permanent two-truth
model:

```text
Current config lists -> reconciliation inputs/convenience editors
HA Labels -> global semantic role metadata
Native HA helpers -> exact generated room/role/domain surfaces
MembershipMap -> engine input with label/helper targets and resolved entity targets
```

That lets the project preserve current users while moving the durable source of control
membership back to Home Assistant.
