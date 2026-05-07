# Native HA Reduction Roadmap

## Branch Purpose

Branch: `ha-native-feature-reduction`

This branch prepares Magic Areas for the control intent engine by reducing duplicate
implementations of native Home Assistant capabilities.

After this branch:

1. return to the control intent engine branch/work
2. revisit the engine under the new label/helper reconciliation paradigm
3. return to adaptive switching once the runtime target model is stable

## Plan Documents

Primary documents:

- `label-backed-control-membership-plan.md`
- `native-ha-feature-reduction-plan.md`
- `native-ha-helper-api-research.md`
- `native-ha-reduction-roadmap.md`

Deferred follow-up document:

- `control-intent-engine-plan-stub.md`

The intent engine plan should not drive runtime work until native labels/helpers have a
clear implementation path.

## Architecture Sequence

### Stage 1: Shared Reconciler Research

Goal:

- Identify the safe APIs for creating, updating, and deleting Magic Areas-managed HA
  labels and helper config entries.
- Decide whether labels should be handled by the same reconciler as native helpers, by a
  shared desired-surface model with separate appliers, or by a sibling label reconciler.

Research targets:

- label registry
- group helper config entries and dynamic group services
- threshold helper config entries
- statistics helper config entries
- trend helper config entries
- derivative helper config entries
- schedule helper config entries
- repairs/issues registry
- entity/device registry metadata

Exit criteria:

- Documented API path per helper type.
- Clear ownership marker strategy for Magic Areas-managed helpers.
- Clear answer for whether each helper type can be updated in place or must be recreated.
- Explicit decision on label reconciliation architecture:
  - unified with helpers
  - shared model with separate applier
  - separate reconciler sharing ownership/diagnostics primitives
- No feature migration starts before the common reconciliation contract is defined.

Current finding:

- Use shared desired-surface, ownership, diffing, diagnostics, and stale-cleanup
  primitives.
- Use specialized appliers for labels, config-entry helpers, storage-collection helpers,
  repairs, and registry metadata.
- Config-entry-backed native group helper creation is viable for the cover-group pilot.
  The lifecycle probe confirms direct add, update/reload, and remove behavior.
- Prototype each additional config-entry-backed helper type before migrating its feature,
  because group helpers are proven but threshold/statistics/trend/derivative may have
  helper-specific side effects.

### Stage 2: Reconciler Foundation

Status: started.

Goal:

- Build the chosen shared desired-surface reconciliation abstraction.

Required behavior:

- compute desired managed surfaces from current Magic Areas config and entity catalog
- find existing Magic Areas-managed surfaces
- create missing surfaces
- update changed surfaces
- remove stale managed surfaces
- attach helper entities to the correct HA area
- attach helper entities to the correct Magic Areas room device
- exclude managed helper entities from Magic Areas source-entity enumeration
- preserve non-Magic-Areas user surfaces
- emit diagnostics and repairs for failures

Exit criteria:

- Tests cover create/update/remove/no-op cases against HA registries/services.
- The foundation supports the decided label/helper architecture without duplicating
  ownership, diffing, diagnostics, or stale-surface cleanup logic.
- The foundation supports at least one native helper type and either label reconciliation
  directly or a documented sibling label reconciler contract.
- Feature modules declare desired surfaces rather than implementing helper lifecycle.
- Every native-helper migration must prove helper area assignment, Magic Areas device
  attachment, and source-enumeration exclusion.

Current implementation:

- `core/runtime_model/managed_surfaces.py` defines pure desired managed-surface records
  and stable ownership IDs.
- `coordinator/managed_surfaces.py` reconciles config-entry-backed helpers by
  Magic Areas ownership prefix.
- Feature modules can declare desired surfaces through `desired_managed_surfaces`.
- Entry setup reconciles desired surfaces after coordinator refresh and before platform
  forwarding.
- Managed helper entities are assigned to the HA area and Magic Areas device declared by
  the desired surface.
- Entity ingestion filters managed helper entities so assigned helpers do not feed back
  into the same area's source entity catalog.
- The config-entry helper applier supports config-entry-backed helpers.
- The label applier supports scoped entity-label reconciliation for desired label
  surfaces, preserving unrelated user labels and pruning only within the declaring
  surface's eligible entity scope.
- Storage-collection helpers and registry-metadata appliers remain future work.

### Stage 3: Pilot With Cover Groups

Status: implemented for native helper creation/update/remove.

Reason:

- Cover groups are high-suitability and low policy coupling.

Work:

- Convert cover group feature to desired native HA group helpers.
- Keep current entity IDs and user-facing behavior stable where practical.
- Validate stale helper cleanup and repairs behavior.

Exit criteria:

- Cover group feature no longer needs a Magic Areas custom cover group entity.
- Managed HA cover group helper updates when area membership changes.
- Managed HA cover group helper appears under the correct Magic Areas area device.
- Managed HA cover group helper is assigned to the correct HA area.
- Managed HA cover group helper is not re-enumerated as a source cover entity.
- Tests prove user-owned cover groups are untouched.

Current implementation:

- Cover groups now declare native HA `group` helper surfaces instead of building
  `AreaCoverGroup` entities.
- `AreaCoverGroup` has been removed.
- Existing cover platform behavior tests still pass with the native helper surface.
- Direct reconciler tests cover create, update/reload, and stale removal for an owned
  cover group helper.
- Direct reconciler tests cover HA area assignment, Magic Areas device attachment, and
  source-enumeration exclusion.

### Stage 4: Plain Domain Groups

Status: implemented for fan/media native helper creation and switch targeting.

Targets:

- media player groups
- fan groups, grouping only

Work:

- Reuse the cover group reconciliation path.
- Keep area-aware media player separate.
- Keep fan control policy separate from grouping migration.

Exit criteria:

- `AreaMediaPlayerGroup` and `AreaFanGroup` are demoted or removed.
- Existing control switches still have a valid target surface.
- Reconciler handles multiple helper domains without feature-specific lifecycle code.

Current implementation:

- Fan groups declare native HA `group` helper surfaces for `group_type: fan`.
- Media player groups declare native HA `group` helper surfaces for
  `group_type: media_player`.
- Fan/media control switches continue to exist as Magic Areas policy surfaces.
- Control-group runtime resolves both legacy Magic Areas entities and native helper
  config-entry-backed group entities.
- The former custom fan/media `group_entities.py` module has been removed.

### Stage 5: Aggregate Helpers

Status: implemented for standard sensor/binary aggregate helpers, health helper
creation, and illuminance threshold helper creation.

Targets:

- binary sensor aggregates
- health sensor
- sensor aggregates

Work:

- Keep Magic Areas aggregate selection logic.
- Reconcile native HA group helper surfaces for selected aggregate memberships.
- Validate current aggregate semantics against HA helper semantics.
- Apply the standard managed-helper invariants: helper area assignment, Magic Areas room
  device attachment, and source-enumeration exclusion.
- Ensure downstream runtime consumers resolve aggregate helper outputs through managed
  helper ownership/aggregate metadata instead of legacy custom aggregate unique IDs.

Exit criteria:

- Aggregate entity outputs match current behavior for supported cases.
- Aggregate helpers assigned to an HA area do not feed back into Magic Areas source
  enumeration for that same area.
- Threshold, Wasp, and fan-control runtime paths can resolve native aggregate helper
  outputs.
- Health sensor uses the same binary group helper path.
- Unsupported aggregate semantics remain Magic Areas-owned until a native equivalent is
  confirmed.

Current implementation:

- Standard sensor aggregates declare native HA `group` helpers using `group_type:
  sensor` and native mean/sum options.
- Standard binary sensor aggregates declare native HA `group` helpers using
  `group_type: binary_sensor` and native any/all options.
- Aggregate group-registry records use managed helper unique IDs when owned by a Magic
  Areas config entry, so downstream aggregate resolution points at the native helper.
- Meta-area child discovery includes child Magic Areas-managed helper entities, so meta
  aggregates can aggregate native helper outputs from child areas.
- Fan control resolves tracked aggregate outputs through aggregate metadata instead of
  legacy custom aggregate unique IDs.
- Health declares a native HA binary sensor group helper and no longer builds a custom
  `AreaHealthBinarySensor`.
- Managed binary helper surfaces can carry desired registry device-class metadata, which
  covers health `problem` classification and binary aggregate helper classification.
- Illuminance threshold declares a native HA `threshold` helper from the managed
  illuminance aggregate helper entity, area threshold, and hysteresis config.
- Aggregate-adjacent behavior tests cover sensor aggregates, binary aggregates,
  threshold, Wasp, fan control, and health with native helper outputs.

### Stage 6: Threshold Helper

Status: implemented.

Target:

- illuminance threshold sensor

Work:

- Reconcile native HA threshold helper from Magic Areas aggregate source, threshold, and
  hysteresis config.
- Verify updates when aggregate source entity or threshold config changes.

Exit criteria:

- Magic Areas threshold wrapper is removed.
- Threshold helper is attached to the correct HA area and Magic Areas room device by the
  managed-surface reconciler.
- Threshold helper is excluded from source enumeration by the managed-helper exclusion
  path.
- Threshold helper remains linked to the managed illuminance aggregate helper after
  reloads.

### Stage 7: Repairs And Metadata Cleanup

Status: implemented.

Targets:

- repairs/issues registry
- entity/device registry metadata
- ownership diagnostics

Work:

- Surface reconciliation failures through Repairs.
- Add ownership metadata/labels/categories needed to find Magic Areas-managed surfaces.
- Remove private metadata where HA registry metadata is now sufficient.

Exit criteria:

- User-actionable reconciliation failures appear as HA repairs.
- Managed helper ownership is discoverable without fragile name matching.
- Private group metadata is only used where HA metadata cannot represent the relationship.

Current implementation:

- Config-entry helper reconciliation creates a persistent HA Repair when create, update,
  or stale-removal fails for a Magic Areas-managed helper.
- Repair issue IDs are stable per managed surface and do not depend on helper display
  names.
- A later successful reconcile of the same managed surface clears the stale Repair.
- Managed-surface ownership prefix construction and detection are centralized in the
  runtime model, so reconciler lookup, source-enumeration exclusion, and meta-area child
  helper discovery use the same ownership contract.
- HA registry lookup for managed-surface config entries and helper entities is
  centralized in `core.managed_surface_registry`, replacing ad hoc config-entry scans in
  the reconciler, source ingestion, meta-area helper discovery, and control-group runtime
  fallback resolution.

Closure assessment:

- User-actionable reconciliation failures now appear as HA Repairs and are cleared after
  successful reconciliation.
- Managed helper ownership is discoverable through stable managed-surface unique IDs and
  shared registry helpers, not helper display names.
- Remaining private group metadata is intentionally retained because it represents Magic
  Areas policy semantics that HA registry metadata cannot express:
  - `role` selects primary control targets and prevents ambiguous policy resolution.
  - `category` orders and resolves light-group child surfaces for all-light behavior.
  - aggregate domain/device-class/kind metadata maps generated helper outputs back to
    Magic Areas runtime consumers such as threshold, Wasp, and fan control.
- HA registry metadata remains the ownership/discovery layer; private group metadata is
  now limited to policy relationships HA cannot represent safely.

### Stage 8: Light Groups

Status: started.

Reason for delay:

- Light groups combine exact surfaces, role metadata, automatic control, suppression,
  manual override, brightness policy, and future adaptive switching.

Work:

- Keep Magic Areas config as guided role assignment.
- Reconcile global role labels.
- Reconcile exact HA light group helpers for room/role surfaces.
- Make runtime policy consume the reconciled role target map.
- Do not implement the new control intent engine yet; only prepare its membership model.

Exit criteria:

- Light role helper surfaces exist and update through reconciliation.
- Runtime no longer treats custom Magic Areas light group entities as membership truth.
- Existing behavior is preserved unless explicitly changed.

Current implementation:

- Light groups declare exact native HA light group helper surfaces for the area all-light
  target and each configured role target with members.
- Native helper titles intentionally use a distinct `Magic Areas Native Light Groups`
  prefix so they do not collide with existing custom `AreaLightGroup` entity IDs while
  runtime policy still lives on those custom entities.
- The existing custom `AreaLightGroup` runtime remains the behavior-preserving policy
  owner for automatic control, manual override, command echo, suppression, and adaptive
  brightness guards.
- Light-group helper identity is centralized in the light-groups public surface so
  feature declaration and runtime target resolution use the same managed-surface ID
  contract without side-door imports.
- Automatic light-group actions now resolve the reconciled native HA light group helper
  as their service-call target and fall back to the custom `AreaLightGroup` entity only
  when the helper is not available yet.
- Runtime on/off gating now reads the reconciled native helper state first, falling back
  to the custom entity state only when the helper state is missing or not an on/off
  state.
- Custom `AreaLightGroup` entities are hidden by the integration in the entity registry
  while remaining enabled as internal policy/runtime surfaces. Existing visible policy
  entities are re-hidden during setup unless the entry is already hidden by another
  owner.
- Manual override and command-echo tracking remain on the hidden custom policy entity
  for this branch. Native helper service calls still propagate through member state and
  the custom group state listener, so manual native-helper control releases policy
  ownership without moving listeners yet.
- Light groups reconcile global HA role labels for configured light role membership:
  `ma:overhead`, `ma:task`, `ma:sleep`, and `ma:accent`.
- Light role labels are reconciled as scoped entity labels. Each role surface assigns
  its configured members and can remove stale role labels only from the current area's
  eligible light entities, so a global role label in one room does not strip another
  room's membership.
- Reconciler coverage verifies native light helper create, update, stale removal, HA area
  assignment, Magic Areas device attachment, and source-enumeration exclusion.

Remaining work:

- Revisit listener ownership when the control intent engine introduces a dedicated
  policy surface; do not move listeners to native helpers in this branch unless runtime
  evidence shows the hidden-policy listener path is insufficient.
- Decide whether Stage 8 should close with labels as HA-visible membership only, or also
  introduce label-backed runtime target records before returning to custom control groups.

### Stage 9: Custom Control Groups

Work:

- Replace direct private member lists with label/query/helper-backed desired surfaces
  where possible.
- Preserve Magic Areas config UI as the guided abstraction layer.
- Do not use HA scripts as a target for this branch.

Exit criteria:

- Custom control groups compile into the same desired-surface and role-target model as
  built-in groups.
- Direct member-list storage is no longer the preferred runtime truth.

### Stage 10: Signal Helper Research

Targets:

- statistics helpers
- trend helpers
- derivative helpers
- schedule helpers

Work:

- Research helper semantics in relation to adaptive switching and fan humidity/odor
  control.
- Decide which signals should be generated by Magic Areas and which should be selected by
  the user.

Exit criteria:

- Documented recommendation before adaptive switching resumes.
- No custom rolling-window/rate-of-change code is added before native helper suitability
  is decided.

## Branch Exit Criteria

- Native helper reconciliation architecture exists.
- At least one simple group feature is migrated as proof of architecture.
- Plans are updated with what remains before the intent engine branch resumes.
- No runtime behavior changes are made without tests.
- Medium/low-suitability features remain first-class Magic Areas features unless a later
  plan explicitly reopens them.
