# Coordinator migration

This document explains why the coordinator was introduced, how it works, and what it replaces.

## Motivation

The pre-coordinator design relied on each platform building its own view of area data. This resulted in:

- duplicated filtering logic for entity lists
- divergent views of entity state across platforms
- increased complexity when adding new features

The coordinator consolidates this into a single, typed snapshot per config entry.

## What changed

- Added `custom_components/magic_areas/coordinator.py` with `MagicAreasCoordinator` and `MagicAreasData`.
- Extended runtime data to include the coordinator object.
- Setup now performs a coordinator refresh before platforms are initialized.
- Platform code prefers `coordinator.data` and falls back to `area` when needed.

## Snapshot data model

`MagicAreasData` represents the area as a stable, read-only view:

- `area`: the active `MagicArea` or `MagicMetaArea`
- `entities`: resolved entity lists by domain
- `magic_entities`: integration-generated entities by domain
- `presence_sensors`: computed presence sensor IDs
- `active_areas`: active child areas (meta only)
- `config`: merged config options
- `updated_at`: UTC timestamp

## Coordinator lifecycle

- created during `async_setup_entry`
- refreshed once before platform setup
- refreshed via standard `DataUpdateCoordinator` methods
- stopped during `async_unload_entry`

## Usage pattern

```
runtime_data = entry.runtime_data
snapshot = runtime_data.coordinator.data
entities_by_domain = snapshot.entities if snapshot else area.entities
```

## Backward compatibility

The coordinator wraps the existing `MagicArea` instance. Tests and platform code that still use `entry.runtime_data.area` continue to work, but should migrate to the snapshot over time.

## Known follow-ups

- move additional derived values into the snapshot
- tighten typing to remove remaining `Any` usage in platform setup
- migrate remaining platforms to snapshot-only behavior
