# Native Home Assistant Feature Reduction Plan

## Purpose

Reduce Magic Areas code by handing generic mechanics back to Home Assistant where HA
already has native features that meet the need.

This branch is a pre-work branch for the control intent engine. The intent engine should
not be built on top of Magic Areas-owned copies of HA grouping, helper, threshold,
aggregate, trend, or diagnostic systems if those can be reconciled into native HA
surfaces first.

Related research:

- [Native HA Helper API Research](./native-ha-helper-api-research.md)

## Working Thesis

Magic Areas should own the human automation problem:

```text
room/entity discovery
-> guided role assignment
-> area/domain safety boundaries
-> desired HA labels/helpers metadata
-> reconciliation of Magic Areas-managed HA surfaces
-> policy and intent decisions that HA cannot infer
```

Home Assistant should own generic platform mechanics:

```text
labels
groups
aggregate helper entities
threshold/trend/statistics/derivative helper entities
schedule/timer helper state where appropriate
repairs/issues
entity/device registry metadata
```

The goal is not to delete Magic Areas features. The goal is to stop reimplementing or
subclass-wrapping HA features when Magic Areas can instead calculate the desired state and
reconcile native HA objects.

## Ownership Boundary

Magic Areas-managed HA surfaces are owned by Magic Areas.

Users should edit Magic Areas-managed role membership and helper options through Magic
Areas configuration. Reconciliation may overwrite direct edits to Magic Areas-managed HA
labels/helpers. The UI and docs should be explicit about that.

If a user wants a manually managed HA helper, it should not use the Magic Areas managed
identifier/prefix/ownership metadata.

## Managed Surface Registry Invariants

Every Magic Areas-managed native HA helper must follow the same registry rules. These
rules are not cover-group-specific.

Required behavior:

- The helper config entry must have a stable Magic Areas ownership ID, currently using
  the `magic_areas:<owner_entry_id>:` unique-id prefix.
- The helper entity must be assigned to the same HA area as the Magic Area it represents.
- The helper entity must be attached to the Magic Areas device for that room-space, using
  the same device identifier pattern as Magic Areas entities:
  `("magic_areas", "magic_area_device_<area_id>")`.
- The helper entity must show up with the Magic Areas room device in HA device/entity
  displays.
- If HA helper construction does not expose a needed domain attribute, such as binary
  sensor `device_class`, the managed-surface record must carry it as registry metadata
  rather than forcing a custom entity wrapper to remain.
- The helper must not become a source entity for the same Magic Area just because it has
  been assigned to the HA area.
- Entity ingestion must filter Magic Areas-managed helper entities before feature
  enumeration, while still preserving normal Magic Areas entities in `magic_entities`.
- Meta-area child discovery must include child Magic Areas-managed helper entities,
  because native helper config entries are owned by HA helper domains rather than the
  child Magic Areas config entry.
- User-owned helpers must not be filtered or overwritten unless they carry Magic
  Areas-managed ownership metadata.

Acceptance criteria for every native-helper migration:

- create, update/reload, and stale removal are covered
- area assignment is covered
- Magic Areas device attachment is covered
- source-enumeration exclusion is covered
- user-owned helper preservation is covered where applicable
- downstream Magic Areas runtime consumers resolve managed helper entities through
  managed-surface ownership or aggregate/control metadata, not legacy custom entity
  unique IDs

## Non-Goals

- Do not use HA scenes as the room-state model. Scenes are static snapshots and do not
  fit Magic Areas' dynamic resolution model.
- Do not use HA scripts as a replacement target in this branch.
- Do not demote presence hold or BLE tracking. They remain first-class Magic Areas
  features for now.
- Do not migrate medium/low-suitability features only for architectural symmetry.
- Do not create feature-specific reconciliation paths that duplicate the same helper
  lifecycle logic.

## Reconciliation Architecture

Add a shared reconciliation layer for Magic Areas-managed HA surfaces where doing so
reduces duplication without forcing unrelated lifecycle models into one abstraction.

The layer should accept desired records such as:

```text
ManagedSurface:
  owner_domain: magic_areas
  owner_entry_id
  area_id
  feature_id
  surface_kind: label | group_helper | threshold_helper | trend_helper | statistics_helper | derivative_helper | schedule_helper
  stable_key
  display_name
  labels
  source_entities
  options
  diagnostics
```

The reconciler should:

- find existing Magic Areas-managed surfaces by stable ownership metadata
- create missing surfaces
- update changed surfaces
- remove stale Magic Areas-managed surfaces
- attach helper entities to the correct HA area and Magic Areas device
- prevent managed helper entities from feeding back into Magic Areas source-entity
  enumeration
- leave non-Magic-Areas user surfaces untouched
- emit diagnostics for skipped, failed, or stale surfaces
- avoid doing per-feature create/update/delete logic in feature modules

The exact HA APIs for each helper type need research before runtime implementation. The
architecture should hide those details behind a common reconciler interface.

Label reconciliation should be evaluated as part of this layer, but it is not mandatory
that labels and helper config entries share the exact same implementation. The design
should compare:

- one unified reconciler for labels and helpers
- a shared desired-surface model with separate label/helper appliers
- separate reconcilers that share ownership and diagnostics primitives

Choose the smallest architecture that avoids duplicated ownership, diffing, diagnostics,
and stale-surface cleanup logic. Do not over-generalize just to force a single
reconciler.

## Label Model

Use HA Labels as global semantic metadata, not as hidden scoped group IDs.

Examples:

- `magic:overhead`
- `magic:task`
- `magic:sleep`
- `magic:accent`
- future `magic:humidity`
- future `magic:odor`

HA label targeting is union-only. Magic Areas cannot express intersections by passing
multiple labels to HA service calls. Therefore:

- global labels are the semantic role surface
- exact room/role control surfaces should usually be native HA helper groups
- Magic Areas resolves entity subsets itself when policy needs intersections,
  suppressions, exclusions, or area/domain safety filtering

Metadata labels at broader or finer scales can be added later as policy. Whether labels
are handled by the same reconciler as helpers or by a sibling label reconciler, the
architecture should make metadata labeling an additive desired-label policy change, not a
rewrite.

## Native Handling Targets

### Light Groups

Current Magic Areas feature:

- Role-based light groups: overhead, task, sleep, accent, all.
- Automatic control policy uses area states, brightness gates, manual override, and
  suppressive states.

Native HA equivalent:

- HA light group helper.
- HA labels for global role metadata.

Target direction:

- Magic Areas config remains the guided role assignment surface.
- Magic Areas reconciles global role labels.
- Magic Areas reconciles exact room/role HA light groups for user-facing control surfaces.
- Runtime policy consumes resolved role membership from the shared reconciler, not custom
  group entity membership truth.
- Intent engine later decides whether to call exact helper groups, labels, or entity IDs.

Expected reduction:

- Demote or remove much of `custom_components/magic_areas/light_groups/entities.py`.
- Shrink `custom_components/magic_areas/features/modules/light_groups.py` from custom
  entity construction to desired-surface registration.
- Reduce dependence on `core/controls/registry.py` as membership truth.

Suitability: high.

Relative work: large.

Rework warning:

- Do not start here before the shared reconciler exists. Light groups combine membership,
  exact surfaces, policy, suppression, manual override, and adaptive switching.

### Fan Groups

Current Magic Areas feature:

- Area fan group and optional control switch/policy.

Native HA equivalent:

- HA fan group helper.
- Future threshold/trend/statistics/derivative helpers for humidity/odor-style fan
  triggers.

Target direction:

- Replace Magic Areas fan group entity with reconciled HA fan group helper.
- Keep Magic Areas fan control policy until fan intent arbitration is redesigned.
- Future humidity/odor fan logic should consume native helper sensors where possible.

Current implementation:

- Fan groups now declare native HA `group` helper surfaces instead of building
  custom Magic Areas fan group entities.
- Fan control still runs through the Magic Areas control switch/policy.
- Control switches resolve native helper targets through the managed helper config
  entry when direct entity-registry unique-id lookup is insufficient.
- The former `group_entities.py` custom fan/media group module has been removed.

Remaining reduction:

- Further shrink shared custom group-builder code after light groups no longer need it.

Suitability: high for grouping, medium for full control behavior.

Relative work: small-medium.

### Cover Groups

Current Magic Areas feature:

- Area cover groups partitioned by cover device class.

Native HA equivalent:

- HA cover group helper.

Target direction:

- Use this as the first pilot for native helper reconciliation.
- Reconcile HA cover group helpers from current area/domain/device-class discovery.

Current implementation:

- Cover groups declare native HA `group` helper surfaces instead of building custom
  Magic Areas cover group entities.
- `AreaCoverGroup` has been removed.

Suitability: very high.

Relative work: small.

### Media Player Groups

Current Magic Areas feature:

- Area media player group.

Native HA equivalent:

- HA media player group helper.

Target direction:

- Replace plain area media player group entity with reconciled HA helper.
- Keep area-aware media routing separate; native groups do not replace occupied-area
  routing.

Current implementation:

- Media player groups now declare native HA `group` helper surfaces instead of building
  custom Magic Areas media-player group entities.
- Media player control still runs through the Magic Areas control switch/policy.
- The former `group_entities.py` custom fan/media group module has been removed.

Remaining reduction:

- Further shrink shared custom group-builder code after light groups no longer need it.

Suitability: high for grouping.

Relative work: small.

### Sensor Aggregates

Current Magic Areas feature:

- Area sensor aggregate entities by device class/unit/mode.

Native HA equivalent:

- HA sensor group helper.
- HA statistics helper may be useful for rolling statistics where mean/sum is not enough.

Target direction:

- Keep Magic Areas aggregate selection policy.
- Reconcile native HA sensor group helpers where HA's group semantics match current
  aggregate semantics.
- Add statistics helpers only where the desired behavior is explicitly statistical or
  rolling-window based.
- Assign managed aggregate helpers to the same HA area and Magic Areas device as the
  room-space while excluding those helpers from future source-entity enumeration. This
  prevents aggregate helpers from being selected into their own next aggregate pass.
- Runtime consumers such as threshold sensors and fan control must resolve aggregate
  outputs through aggregate metadata/native helper ownership instead of the old custom
  aggregate entity unique ID.

Current implementation:

- Standard sensor aggregate definitions declare managed native HA `group` helper
  surfaces with `group_type: sensor`.
- Magic Areas still computes aggregate membership and mode selection.
- The native helper owns numeric calculation for supported `mean` and `sum` cases.
- Tests cover source updates flowing through native helper output and downstream fan
  control/threshold/Wasp aggregate resolution.

Expected reduction:

- Remove or demote `AreaSensorGroupSensor` and `AreaAggregateSensor` in
  `custom_components/magic_areas/sensor/__init__.py`.
- Keep `core/aggregates/selection.py` and related policy until native helper inputs are
  proven equivalent.

Suitability: high.

Relative work: medium.

### Binary Sensor Aggregates

Current Magic Areas feature:

- Area binary sensor aggregate entities by device class.

Native HA equivalent:

- HA binary sensor group helper.

Target direction:

- Keep Magic Areas aggregate selection policy.
- Reconcile native HA binary sensor groups for matching device-class aggregate surfaces.
- Assign and protect managed binary aggregate helpers using the same area/device and
  source-enumeration exclusion invariants as every other managed helper.

Current implementation:

- Standard binary sensor aggregate definitions declare managed native HA `group` helper
  surfaces with `group_type: binary_sensor`.
- Magic Areas still computes aggregate membership and `any`/`all` mode selection.
- Wasp-in-a-box aggregate resolution continues through aggregate metadata.
- Binary aggregate helpers carry desired device class as managed registry metadata
  because HA binary group config entries do not pass device class through options.

Expected reduction:

- Remove or demote `AreaSensorGroupBinarySensor` and `AreaAggregateBinarySensor` in
  `custom_components/magic_areas/binary_sensor/aggregate_factory.py`.

Suitability: high.

Relative work: medium.

### Threshold Sensors

Current Magic Areas feature:

- Illuminance threshold binary sensor built from the area illuminance aggregate.

Native HA equivalent:

- HA threshold helper.

Target direction:

- Replace Magic Areas threshold entity wrapper with a managed HA threshold helper.
- Keep Magic Areas responsible for calculating source entity, threshold, and hysteresis.

Current implementation:

- `AggregatesFeatureModule` declares the native HA threshold helper surface after the
  managed aggregate helper surfaces.
- The helper uses the managed illuminance aggregate helper as its source and carries the
  configured upper threshold and hysteresis.
- The managed-surface reconciler attaches the helper to the Magic Areas room device and
  HA area, and the source-ingestion path excludes Magic Areas-managed helper entities.

Expected reduction:

- Removed `AreaThresholdSensor` and the custom
  `custom_components/magic_areas/binary_sensor/threshold.py` runtime wrapper.

Suitability: very high.

Relative work: medium because helper config-entry lifecycle must be proven.

### Health Sensors

Current Magic Areas feature:

- Problem-class binary sensor group for health-style status aggregation.

Native HA equivalent:

- HA binary sensor group helper with problem device class.

Target direction:

- Fold into the same native binary sensor group reconciliation path as binary aggregates.

Current implementation:

- Health now declares a managed native HA binary sensor group helper with
  `group_type: binary_sensor`.
- Magic Areas still computes health membership from configured distress device classes.
- The helper carries `problem` as managed registry device-class metadata because HA
  binary group config entries do not pass device class through options.

Completed reduction:

- Removed `AreaHealthBinarySensor` and `create_health_sensors` from
  `custom_components/magic_areas/binary_sensor/aggregate_factory.py`.
- Shrink `custom_components/magic_areas/features/modules/health.py`.

Suitability: high.

Relative work: low-medium after binary group reconciliation exists.

### Custom Control Groups

Current Magic Areas feature:

- User-defined custom control groups with direct member lists and trigger/policy metadata.

Native HA equivalent:

- HA labels for semantic membership.
- HA group helpers for exact control surfaces.
- Entity/device registry metadata.

Target direction:

- Replace direct private member lists with label/query-driven desired surfaces where
  possible.
- Preserve Magic Areas config UI as the guided abstraction layer.
- Do not move to HA scripts in this branch.

Expected reduction:

- Reshape `custom_components/magic_areas/schemas/control_groups.py`.
- Reduce custom member-list handling in `custom_components/magic_areas/core/controls/builders.py`.
- Reduce private membership reliance in `custom_components/magic_areas/core/controls/registry.py`.

Suitability: high.

Relative work: large.

### Statistics, Trend, And Derivative Helpers

Current Magic Areas/future feature pressure:

- Adaptive brightness ambient-rise detection.
- Future humidity fan rate-of-change logic.
- Possible sensor trend/rate guard conditions.

Native HA equivalents:

- HA statistics helper.
- HA trend binary sensor.
- HA derivative helper.

Target direction:

- Research exact helper semantics before implementing custom rate/slope math.
- Use native helpers as generated surfaces where they express the needed signal.
- Magic Areas policy consumes the resulting helper entities as inputs.
- Keep the boundary explicit: helpers provide the signal/data API, while Magic Areas owns
  interpretation, room-state policy, suppression, manual override behavior, and action
  target selection.

Expected reduction:

- Avoid future rolling-window/rate-of-change code in fan and adaptive switching policy.
- Potentially reduce existing ambient lux sample handling if native helpers cover the
  behavior well.

Suitability: high for future fan/adaptive signals.

Relative work: medium research, medium-large integration if adopted.

### Schedule Helpers

Current Magic Areas/future feature pressure:

- Sleep windows.
- Quiet windows.
- Time-based state eligibility.

Native HA equivalent:

- HA schedule helper.

Target direction:

- Prefer consuming or reconciling HA schedule helpers instead of adding custom time-window
  machinery.
- Keep actual state resolution in Magic Areas.

Expected reduction:

- Avoid future custom schedule/time-window code.
- May simplify sleep/quiet state inputs if those become schedule-backed.

Suitability: medium-high.

Relative work: small-medium research, medium integration.

### Repairs And Issue Registry

Current Magic Areas behavior:

- Some problems are logged or surfaced through config flow errors.

Native HA equivalent:

- HA repairs/issue registry.

Target direction:

- Use Repairs for stale managed helpers, failed reconciliation, invalid source entities,
  reserved names, orphaned managed labels/helpers, and config states that require user
  intervention.

Expected reduction:

- Does not delete feature modules, but reduces bespoke diagnostics/error UX.
- Improves user recovery without adding more custom entities.

Suitability: high.

Relative work: small-medium.

### Entity And Device Registry Metadata

Current Magic Areas behavior:

- Private group metadata, custom runtime registries, and feature-specific lookups.

Native HA equivalent:

- Entity labels.
- Device labels.
- Areas.
- Entity categories.
- Config entry references.
- Device/entity registry metadata.

Target direction:

- Prefer HA registry metadata when it can represent stable ownership, role, or diagnostic
  relationships.
- Keep Magic Areas runtime model for data HA cannot represent.

Expected reduction:

- Reduce reliance on private metadata in `core/runtime_model/groups.py`,
  `core/controls/registry.py`, and feature-specific group lookup paths over time.

Suitability: high.

Relative work: medium.

## Working Priority

1. Shared reconciler foundation.
2. Cover groups pilot.
3. Media player groups.
4. Fan groups, grouping only.
5. Binary sensor aggregate/health helper reconciliation.
6. Sensor aggregate helper reconciliation.
7. Threshold helper reconciliation.
8. Repairs/issues integration for reconciliation failures.
9. Registry metadata cleanup.
10. Light groups.
11. Custom control groups.
12. Statistics/trend/derivative helper research and integration.
13. Schedule helper research and integration.

This order is not pure shortest-time-first. It avoids doing quick migrations in a way
that creates rework for the larger helper reconciliation architecture.
