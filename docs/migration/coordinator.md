# Coordinator differences

This document explains how the coordinator-based runtime model differs from the
fork baseline (commit `d7b5779`) and how snapshot data is now the authoritative
source for platform setup.

## Fork baseline behavior

Each platform assembled its own view of area data by reading `MagicArea`
properties directly. This resulted in:

- duplicated entity filtering logic across platforms
- inconsistent data reads when multiple platforms updated concurrently
- more surface area to update when new features were added

## Updated behavior

A coordinator now owns a single, typed snapshot per config entry:

- `custom_components/magic_areas/coordinator.py` defines `MagicAreasCoordinator`
  and the `MagicAreasData` snapshot.
- runtime data includes the coordinator alongside the `MagicArea`.
- setup performs a refresh before platforms read data.
- platforms read `coordinator.data` and skip setup when the snapshot is
  unavailable.
- coordinator refresh status drives entity availability.

## Snapshot data model

`MagicAreasData` is a read-only snapshot containing:

- `area`: the active `MagicArea` or `MagicMetaArea`
- `entities`: resolved entity lists by domain
- `magic_entities`: integration-generated entities by domain
- `presence_sensors`: computed presence sensor IDs
- `active_areas`: active child areas (meta only)
- `config`: merged config options
- `updated_at`: UTC timestamp

### Snapshot field sources

- `entities` and `magic_entities`: collected from registry + state via
  `MagicArea.load_entities()` and core entity grouping helpers.
- `presence_sensors`: computed by core presence helpers and passed into
  `binary_sensor` setup.
- `config`: merged entry data and options so platforms read one source.
- `active_areas`: derived from meta area child resolution.

### Platform setup guard

Platforms now follow a single guard path:

1) If `coordinator.data` is missing, refresh once.
2) If snapshot remains unavailable, skip platform setup.
3) Entities are created from snapshot data only.

This removes platform-specific fallbacks to `MagicArea` for list assembly.

### Availability semantics

Entity availability is tied to coordinator refresh success:

- on refresh success: `area.last_update_success = True`
- on refresh failure: `area.last_update_success = False`
- entities read this flag for availability

### Diagnostics alignment

Diagnostics now read snapshot data and rely on the coordinator timestamp for
freshness. This keeps diagnostics output consistent with what platforms see.

## Usage pattern

```
runtime_data = entry.runtime_data
if runtime_data.coordinator.data is None:
    await runtime_data.coordinator.async_refresh()
snapshot = runtime_data.coordinator.data
if snapshot is None:
    return
entities_by_domain = snapshot.entities
```

## Compatibility with the forked structure

The coordinator wraps the existing `MagicArea` instance, so code that still
uses `entry.runtime_data.area` continues to work. The main difference is that
platforms now have a single, consistent snapshot available.
