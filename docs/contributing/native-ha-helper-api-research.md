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
