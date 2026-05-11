# Native HA Helper API Research

## Purpose

Record Stage 1 findings for Magic Areas-managed native Home Assistant surfaces.

This document answers the first reconciler questions:

- how each native HA surface is created
- whether it can be updated in place
- how it can be removed
- how Magic Areas can identify ownership
- whether labels should share a reconciler with helpers

## Summary Recommendation

Use a shared desired-surface model with separate appliers.

```text
DesiredManagedSurface
-> LabelApplier
-> ConfigEntryHelperApplier
-> StorageCollectionHelperApplier
-> RepairIssueApplier
-> RegistryMetadataApplier
```

Do not force one monolithic reconciler. Labels, config-entry helpers, storage collection
helpers, repairs, and registry metadata have different lifecycle APIs. They should share:

- ownership model
- desired/current diffing conventions
- stable keys
- diagnostics result model
- stale managed-surface cleanup behavior

They should not be forced through one create/update/delete implementation.

## Ownership Model

Magic Areas should use stable, deterministic ownership keys for every managed surface.

Recommended stable key shape:

```text
magic_areas:<entry_id>:<area_id>:<feature_id>:<surface_kind>:<role_or_partition>
```

Where possible, store this as:

- config entry `unique_id` for config-entry-backed helpers
- storage collection item ID for storage-backed helpers
- label ID/name prefix for labels
- issue ID for Repairs
- entity/device labels or categories for registry metadata

Do not rely on display names as ownership keys. Display names can change and should be
updated independently from ownership identity.

## Surface Types

## Registry Metadata And Feedback Prevention

Magic Areas-managed native helpers must be treated as exposed HA surfaces, not as new
source devices discovered inside the same room.

Standard behavior for every managed helper applier:

- Create/update the native HA surface using stable Magic Areas ownership metadata.
- After HA creates or reloads helper entities, update the entity registry so helper
  entities have the Magic Area's `area_id`.
- Attach helper entities to the room's Magic Areas device through the device registry.
  The device identifier must match the Magic Areas entity device identifier:
  `("magic_areas", "magic_area_device_<area_id>")`.
- Keep helper registry metadata in sync on every reconcile, not only on first creation.
- Filter Magic Areas-managed helper entities out of regular source-entity ingestion by
  checking the helper config entry's Magic Areas ownership unique ID.
- Do not filter user-owned helpers that happen to be in the same HA area unless they use
  Magic Areas-managed ownership metadata.

This prevents a feedback loop where Magic Areas creates a helper, assigns it to the HA
area for discoverability, and then later enumerates that helper as if it were an
underlying room device.

### Labels

HA API:

- `homeassistant.helpers.label_registry.async_get(hass)`
- `label_registry.async_create(name, color=None, icon=None, description=None)`
- `label_registry.async_update(label_id, name=..., icon=..., description=...)`
- `label_registry.async_delete(label_id)`
- entity/device/area registries store label IDs on registry entries

Update behavior:

- Labels can be updated in place.
- Label ID is generated from the name at creation and remains the registry key when the
  label name is updated.
- Entity/device/area labels are updated by replacing the registry entry's `labels` set.

Reconciler implication:

- Label reconciliation should probably be a dedicated applier sharing ownership/diffing
  primitives with helper appliers.
- Global semantic labels remain the default Magic Areas label model.
- Metadata labels can be policy-added later if the desired-label calculation is clean.

### Group Helpers

HA API shape:

- Config-entry-backed helper groups are created through the `group` integration config
  flow and stored as config entries.
- Group config entries store helper options under `entry.options`.
- Options flow reloads the config entry after changes.
- Supported config-entry group types include binary sensor, cover, fan, light, media
  player, sensor, switch, and more.

Relevant options:

- `group_type`
- `name`
- `entities`
- `hide_members`
- `all` for binary sensor/light/switch group behavior
- sensor group `type` and `ignore_non_numeric`

There is also a legacy/dynamic `group.set` / `group.remove` service path, but that only
creates `group.*` entities, not domain-specific helper groups like `light.group` or
`cover.group`. It is not the right primary path for replacing Magic Areas domain groups.

Update behavior:

- Config-entry-backed group helpers can be updated by changing config entry `options` and
  reloading the entry.
- Config-entry removal is supported through `hass.config_entries.async_remove(entry_id)`.
- Config entries can have `unique_id`; helper config flows do not appear to set one by
  default, so Magic Areas-managed helpers likely need programmatic entry creation or a
  controlled flow path that sets unique ownership another way.

Reconciler implication:

- Use a config-entry helper applier for exact room/domain/role helper groups.
- Cover groups are the best first pilot because they have low policy coupling.
- Avoid legacy `group.set` for the main architecture.

Probe result:

- `tests/integration/test_native_group_helper_lifecycle.py` verifies direct
  programmatic creation of a `group` config entry for a native cover group.
- `hass.config_entries.async_add(entry)` is async and loads the entry immediately in
  this HA version; a separate `async_setup(entry_id)` call is incorrect after add.
- A stable Magic Areas ownership key can be stored as config entry `unique_id`.
- Native helper membership can be updated by `async_update_entry(..., options=...)`
  followed by `async_reload(entry_id)`.
- Native helper removal through `async_remove(entry_id)` removes the helper entity and
  its entity-registry entry.
- This confirms the cover-group pilot can use direct config-entry-backed helper
  reconciliation instead of the legacy `group.set` service path.
- The implemented reconciler path stores desired helper state in
  `ConfigEntryHelperSurface`, matches owned helpers by `magic_areas:<entry_id>:` unique
  ID prefix, updates changed options/title, reloads loaded helpers, and removes stale
  owned helpers.
- Managed helper entities are assigned to the target HA area and attached to the Magic
  Areas room device after create/update.
- Entity ingestion excludes managed helper entities from source enumeration by checking
  the helper config entry ownership prefix.
- `AreaCoverGroup` has been removed after CRG confirmed it became dead code.

### Threshold Helpers

HA API shape:

- `threshold` is config-entry-backed.
- Config flow stores all behavior in `entry.options`.
- Options flow reloads on update.

Relevant options:

- `name`
- `entity_id`
- `lower`
- `upper`
- `hysteresis`

Update behavior:

- Config entry options can be updated and the entry reloaded.
- Source entity changes are tracked by HA helper integration support.
- Removal is config-entry removal.

Reconciler implication:

- Good candidate for managed helper replacement of Magic Areas' current threshold wrapper.
- Must verify direct config-entry creation and source-entity linkage behavior in tests.

### Statistics Helpers

HA API shape:

- `statistics` is config-entry-backed.
- Config flow stores behavior in `entry.options`.
- Options flow reloads on update.

Relevant options:

- `name`
- `entity_id`
- `state_characteristic`
- `sampling_size`
- `max_age`
- `keep_last_sample`
- `percentile`
- `precision`

Update behavior:

- Config entry options can be updated and reloaded.
- Some options are read-only in the UI but can still exist in entry options.
- Removal is config-entry removal.

Reconciler implication:

- Useful for future adaptive and fan signal handling.
- Do not implement custom rolling statistics until the helper suitability is decided.

Signal/API boundary:

- Statistics/trend/derivative helpers should expose measured-condition signals that Magic
  Areas can consume.
- They should not encode Magic Areas room behavior directly. Magic Areas remains
  responsible for interpreting helper states alongside area state, control role,
  suppression state, manual override, and target-resolution policy.
- Helper warm-up, `unknown`, and `unavailable` states must be surfaced as signal quality,
  not silently collapsed into policy decisions such as “bright enough” or “safe to turn
  off.”

Stage 10 recommendation:

- Treat statistics helpers as the first choice for rolling-window scalar summaries where
  Magic Areas needs an actual value, not just a boolean trigger.
- Strong fits:
  - humidity settling / recent humidity change after a shower
  - rolling mean/min/max/variance/noisiness diagnostics
  - binary-source percentages/counts for “recently active” style observability
- Weak fits:
  - immediate edge detection
  - control paths that cannot tolerate sparse-source or startup `unknown` behavior
- Native docs note that statistics can restore from recorder history on startup, but
  without recorder some characteristics need multiple samples before reporting. The
  planner must expose warm-up/unknown handling explicitly in policy debug attributes.
- If Magic Areas generates these, use config-entry helper ownership like group helpers
  and attach the helper entity to the Magic Area device/area while excluding it from
  source enumeration.
- Do not use statistics as the only fan-control truth until policy distinguishes:
  - source unavailable
  - helper warming up
  - helper reporting a valid low/settled value

### Trend Helpers

HA API shape:

- `trend` is config-entry-backed.
- Config flow has setup step for source entity/name and settings/options for trend
  behavior.
- Source entity is read-only in options.

Relevant options:

- `name`
- `entity_id`
- `attribute`
- `invert`
- `max_samples`
- `min_samples`
- `min_gradient`
- `sample_duration`

Update behavior:

- Options flow reloads on update.
- Code comments indicate trend does not allow replacing the input entity through normal
  source-entity change handling.

Reconciler implication:

- If source entity changes, safest approach may be recreate rather than update in place.
- Good candidate for future humidity-rate or ambient-rise signals, but not first pilot.

Stage 10 recommendation:

- Treat trend helpers as the first choice when Magic Areas needs a boolean “rising” or
  “falling” signal over a configured sample window.
- Strong fits:
  - adaptive-light ambient-rise evidence for “daylight is increasing enough”
  - humidity rising/falling triggers for bathroom fan control
  - future odor proxy signals where a binary trend condition is sufficient
- Weak fits:
  - decisions that need the numeric rate value for ranking/debugging
  - source sensors that update too sparsely to satisfy `min_samples` quickly
- Native docs define trend as a fitted trend line compared against `min_gradient`, with
  gradient measured in source units per second. Magic Areas config must present
  user-facing units, then convert to the HA helper’s per-second gradient.
- Because source replacement appears less flexible than option updates, model source
  entity changes as recreate-safe unless tests prove update-in-place works reliably.

### Derivative Helpers

HA API shape:

- `derivative` is config-entry-backed.
- Config flow/options flow store behavior in `entry.options`.
- Options flow reload behavior is enabled.

Relevant options:

- `name`
- `source`
- `round`
- `time_window`
- `unit_prefix`
- `unit_time`
- `max_sub_interval`

Update behavior:

- Config entry options can be updated and reloaded.
- Source compatibility includes unit-of-measurement checks in the options flow.

Reconciler implication:

- Candidate for future rate-of-change calculations.
- Needs semantic comparison with trend/statistics before adopting.

Stage 10 recommendation:

- Treat derivative helpers as the first choice when Magic Areas needs a numeric rate
  output instead of a direct boolean.
- Strong fits:
  - humidity rate-of-rise/rate-of-fall diagnostics
  - adaptive-light lux rise rate when policy needs tunable thresholds or debug visibility
  - chaining into a threshold helper when a managed binary trigger is desired
- Weak fits:
  - simple “rising enough?” conditions where trend can produce the binary signal directly
  - noisy sensors unless `time_window` smoothing is configured
- Native docs define `time_window` smoothing and `max_sub_interval`; Magic Areas should
  surface those only through named presets at first, not raw expert-only knobs.
- If derivative plus threshold are both generated for one behavior, the desired-surface
  planner must own both as a single signal bundle so cleanup, diagnostics, and labels do
  not drift apart.

### Schedule Helpers

HA API shape:

- `schedule` is storage-collection-backed, not config-entry-backed.
- Storage collection supports `async_create_item`, `async_update_item`, and
  `async_delete_item`.
- The schedule entity updates itself from storage collection changes.

Relevant data:

- `name`
- `icon`
- weekday time ranges
- optional custom data per time range

Update behavior:

- Update through storage collection item update.
- Delete through storage collection item delete.
- IDs are storage item IDs, generated from names unless explicitly loaded from YAML.

Reconciler implication:

- Needs a storage-collection helper applier, not the config-entry helper applier.
- Defer implementation until schedule-backed states are actually needed.

Stage 10 recommendation:

- Treat schedule helpers as the preferred HA-native surface for user-editable time
  windows such as sleep eligibility, quiet hours, or future profile constraints.
- Strong fits:
  - user-visible sleep/quiet eligibility windows
  - optional time-window constraints consumed by the future control intent engine
  - profile attributes carried as schedule block data when the data remains small and
    semantic, not scene-like
- Weak fits:
  - current presence/extended/sleep timeout mechanics
  - static scene replacement
  - generated schedules that users are not expected to edit
- Native docs define schedules as weekly on/off entities with non-overlapping time blocks
  and optional active-block attributes. Magic Areas should consume schedule state as an
  eligibility signal, not move room-state resolution into the schedule helper.
- Because schedules are storage-collection-backed, implementation requires a
  `StorageCollectionHelperApplier`; do not force schedules through the config-entry helper
  reconciler.

### Repairs / Issue Registry

HA API:

- `homeassistant.helpers.issue_registry.async_create_issue(...)`
- `homeassistant.helpers.issue_registry.async_delete_issue(...)`

Useful fields:

- `domain`
- `issue_id`
- `is_fixable`
- `severity`
- `translation_key`
- `translation_placeholders`
- `learn_more_url`

Update behavior:

- Creating an existing issue updates stored issue content.
- Deleting clears resolved/stale issues.

Reconciler implication:

- Use a dedicated repair issue applier.
- Good early addition because reconciliation failures should become actionable HA repairs,
  not only logs.

### Entity / Device / Area Registry Metadata

HA APIs:

- entity registry entries have `labels`, `categories`, `area_id`, `device_id`,
  `config_entry_id`, `hidden_by`, and `entity_category`.
- device registry entries have `labels`, `area_id`, and config entry relationships.
- area registry entries have `labels`.

Update behavior:

- Registry update calls replace metadata fields.
- Label updates require preserving non-Magic-Areas labels.

Reconciler implication:

- Use registry metadata as discoverability and ownership hints where it is stable.
- Do not treat device or area labels as precise control membership without filtering.

## Programmatic Config Entry Creation Risk

Home Assistant's config entry manager supports direct add/update/remove operations, but
helper config flows are designed primarily for user-driven flows. The cleanest managed
helper architecture likely needs one of these approaches:

1. Create helper entries through config flow APIs and store ownership elsewhere.
2. Construct `ConfigEntry` objects programmatically with stable `unique_id` and options.
3. Avoid config-entry-backed helpers where direct lifecycle control is too fragile.

Initial recommendation:

- Use direct managed config-entry creation for `group` helpers with stable `unique_id`
  and options.
- Use config entry `unique_id` as the ownership marker for config-entry-backed helpers
  when HA accepts direct creation.
- Keep the fallback path documented for helper types that reject direct creation or have
  special config-flow side effects.

Verified for:

- Native `group` cover helper creation/update/remove in
  `tests/integration/test_native_group_helper_lifecycle.py`.

## Initial Reconciler Architecture Decision

Use shared primitives plus specialized appliers.

```text
DesiredSurfacePlanner
  -> computes desired labels/helpers/issues/metadata

ManagedSurfaceDiff
  -> compares desired/current by stable key

LabelApplier
  -> label registry + entity/device/area registry label sets

ConfigEntryHelperApplier
  -> group, threshold, statistics, trend, derivative helpers

StorageCollectionHelperApplier
  -> schedule helpers

RepairIssueApplier
  -> HA issue registry

RegistryMetadataApplier
  -> entity/device/area metadata updates
```

This avoids duplicating the important logic while respecting that HA exposes different
lifecycle APIs for different surfaces.

## First Implementation Candidate

Pilot with native HA cover group helpers after the config-entry helper applier is proven.

Why:

- simple exact area/domain surface
- no Magic Areas automatic policy entanglement
- clear current wrapper replacement target
- verifies config-entry helper create/update/remove without risking light behavior
