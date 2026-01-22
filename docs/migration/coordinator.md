# Coordinator differences

This document explains how the current coordinator-based runtime model differs
from the original fork baseline.

## Original behavior

Each platform assembled its own view of area data by reading `MagicArea`
properties directly. That meant:

- duplicated entity filtering logic across platforms
- inconsistent data reads when multiple platforms updated concurrently
- more surface area to update when new features were added

## Current behavior

A coordinator now owns a single, typed snapshot per config entry:

- `custom_components/magic_areas/coordinator.py` defines `MagicAreasCoordinator`
  and the `MagicAreasData` snapshot.
- runtime data includes the coordinator alongside the `MagicArea`.
- setup performs a refresh before platforms read data.
- platforms prefer `coordinator.data` and only fall back to the area instance
  when the snapshot is unavailable.

## Snapshot data model

`MagicAreasData` is a read-only snapshot containing:

- `area`: the active `MagicArea` or `MagicMetaArea`
- `entities`: resolved entity lists by domain
- `magic_entities`: integration-generated entities by domain
- `presence_sensors`: computed presence sensor IDs
- `active_areas`: active child areas (meta only)
- `config`: merged config options
- `updated_at`: UTC timestamp

## Coordinator lifecycle

- created during `async_setup_entry`
- refreshed before platform setup
- refreshed via standard `DataUpdateCoordinator` methods
- stopped during `async_unload_entry`

## Usage pattern

```
runtime_data = entry.runtime_data
snapshot = runtime_data.coordinator.data
entities_by_domain = snapshot.entities if snapshot else area.entities
```

## Compatibility with the original structure

The coordinator wraps the existing `MagicArea` instance, so code that still
uses `entry.runtime_data.area` continues to work. The main difference is that
current platforms now have a single, consistent snapshot available.
