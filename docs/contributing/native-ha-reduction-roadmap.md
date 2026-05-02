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
- The first applier supports config-entry-backed helpers only; label, storage,
  repairs, and registry-metadata appliers remain future work.

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

Status: started for standard sensor/binary aggregate helpers; health aggregation remains
pending.

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
- Fan control resolves tracked aggregate outputs through aggregate metadata instead of
  legacy custom aggregate unique IDs.
- Aggregate-adjacent behavior tests cover sensor aggregates, binary aggregates,
  threshold, Wasp, and fan control with native helper outputs.

### Stage 6: Threshold Helper

Target:

- illuminance threshold sensor

Work:

- Reconcile native HA threshold helper from Magic Areas aggregate source, threshold, and
  hysteresis config.
- Verify updates when aggregate source entity or threshold config changes.

Exit criteria:

- Magic Areas threshold wrapper is demoted or removed.
- Threshold helper remains linked to the correct source after reloads and entity renames.

### Stage 7: Repairs And Metadata Cleanup

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

### Stage 8: Light Groups

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
