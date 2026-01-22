# Architecture overview

This document summarizes the current runtime architecture and explains how
it differs from the original fork baseline.

## Current integration layout

- `custom_components/magic_areas/__init__.py`
  - config entry lifecycle
  - runtime data setup
  - coordinator creation and teardown

- `custom_components/magic_areas/base/`
  - `MagicArea` and `MagicMetaArea`
  - entity base classes and shared helpers

- `custom_components/magic_areas/coordinator.py`
  - shared, typed snapshot for platform use

- `custom_components/magic_areas/{platform}.py`
  - platform setup and entities

- `custom_components/magic_areas/config_flow.py`
  - UI config and options flow

- `custom_components/magic_areas/config_flows/feature_registry.py`
  - per-feature metadata and schemas

## Runtime data flow (current)

```
Config entry setup
  └─ __init__.py
       ├─ build MagicArea / MagicMetaArea
       ├─ create MagicAreasCoordinator
       ├─ coordinator refresh (first refresh during setup)
       └─ runtime_data = { area, coordinator, listeners }

Coordinator refresh
  └─ coordinator.py
       ├─ MagicArea.load_entities()
       ├─ (meta) update child_areas / active_areas
       └─ MagicAreasData snapshot:
            - entities
            - magic_entities
            - presence_sensors
            - active_areas
            - config
            - updated_at

Platform setup
  ├─ sensor/__init__.py
  ├─ binary_sensor/__init__.py
  ├─ light.py
  ├─ media_player/__init__.py
  └─ switch/__init__.py
       └─ read coordinator.data
          └─ fallback to area state if snapshot missing
```

## Runtime data flow (original baseline)

```
Config entry setup
  └─ __init__.py
       ├─ build MagicArea / MagicMetaArea
       └─ runtime_data = { area, listeners }

Platform setup
  ├─ sensor/__init__.py
  ├─ binary_sensor/__init__.py
  ├─ light.py
  ├─ media_player/__init__.py
  └─ switch/__init__.py
       └─ read area.entities and helper methods directly
          └─ platform-specific filtering and list building
```

## Why this matters

- The snapshot ensures consistent entity lists across platforms.
- Refresh logic is centralized and testable in one place.
- Platforms can be simplified over time to read snapshot data only.
