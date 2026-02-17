# Architecture overview

This document summarizes the runtime architecture and explains how it differs
from the fork baseline (commit `d7b5779`). It focuses on information flow,
state ownership, and event propagation so a reviewer can continue development
from the updated structure.

## Updated integration layout

- `custom_components/magic_areas/__init__.py`
  - config entry lifecycle
  - runtime data setup
  - coordinator creation and teardown
  - config entry migrations (unique ID updates)

- `custom_components/magic_areas/base/`
  - `MagicArea` / `MagicMetaArea`
  - entity base classes and shared helpers

- `custom_components/magic_areas/core/`
  - HA-free helpers for config normalization, presence selection, and
    entity grouping

- `custom_components/magic_areas/coordinator.py`
  - shared, typed snapshot for platform use

- `custom_components/magic_areas/{platform}.py`
  - platform setup and entities

- `custom_components/magic_areas/config_flow.py`
  - UI config and options flow

- `custom_components/magic_areas/config_flows/feature_registry.py`
  - per-feature metadata and schemas

- Supporting modules introduced by the split:
  - `config_keys.py`, `defaults.py`, `enums.py`, `features.py`,
    `feature_info.py`, `policy.py`, `area_constants.py`, `area_maps.py`,
    `ha_domains.py`, `icons.py`, `models.py`

## Runtime data flow (updated)

```
Config entry setup
  └─ __init__.py
       ├─ build MagicArea / MagicMetaArea
       ├─ create MagicAreasCoordinator
       ├─ coordinator refresh (first refresh during setup)
       └─ runtime_data = { area, coordinator, listeners }

Coordinator refresh
  └─ coordinator.py
       ├─ Internal MagicArea._async_update_data()
       ├─ (meta) update child_areas / active_areas
       └─ MagicAreasData snapshot:
            - area_config (pure configuration data)
            - area_runtime (pure runtime state)
            - entities
            - magic_entities
            - presence_sensors
            - active_areas
            - config
            - enabled_features
            - feature_configs
            - updated_at

Platform setup
  ├─ sensor/__init__.py
  ├─ binary_sensor/__init__.py
  ├─ light.py
  ├─ media_player/__init__.py
  └─ switch/__init__.py
       └─ read coordinator.data
          └─ skip setup if snapshot is unavailable
```

## Runtime data flow (fork baseline)

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

## Event flow (updated)

```
presence tracking updates
  └─ binary_sensor/presence.py
       ├─ computes new, lost, and current area states
       └─ dispatcher sends AREA_STATE_CHANGED(area_id, (new, lost, current))

platform handlers
  ├─ light groups
  ├─ climate control
  ├─ fan control
  └─ media player control
       └─ react to current state snapshot from event payload
```

The event payload now includes `current_states` to prevent stale reads from
`MagicArea` during async scheduling.

## Identity and availability flow (updated)

```
coordinator refresh
  ├─ success -> area.last_update_success = True
  └─ failure -> area.last_update_success = False

entities
  └─ availability uses coordinator-driven flag

config entry migration
  └─ entity registry unique IDs updated to stable area-based IDs
```

## Unidirectional Data Flow

Data flows in one direction through the system:

```
MagicArea (coordinator-internal)
  ↓
Coordinator.refresh()
  ↓
MagicAreasData snapshot
  ↓
Platforms read coordinator.data
  ├─ binary_sensor/__init__.py
  ├─ sensor/__init__.py
  ├─ light.py
  ├─ fan.py
  └─ etc.
     ↓
Entities created from snapshot
  ├─ Read area_config (immutable)
  ├─ Read area_runtime (current state)
  ├─ Read entities, presence_sensors, config
  └─ NO access back to MagicArea or coordinator methods

Event dispatch (presence state changes)
  └─ AREA_STATE_CHANGED(area_id, snapshot_data)
     ↓
Platform handlers (light, climate, fan, media)
  └─ React to event payload snapshot
     └─ NO calls back to coordinator or MagicArea
```

**Key property**: Platforms and entities consume snapshot data. They never:
- Call methods on MagicArea
- Trigger coordinator refresh
- Modify snapshot data
- Bypass the snapshot to access area state

This unidirectional flow ensures:
- Consistent data reads (all use snapshot)
- Predictable execution (no hidden state mutations)
- Clear ownership (coordinator owns MagicArea, platforms own entities)
- Testable behavior (mock coordinator.data, test entities in isolation)

## Why this matters

- The snapshot ensures consistent entity lists across platforms.
- Refresh logic is centralized and testable in one place.
- Platforms are reduced to wiring snapshot data into entities.
- Event handlers receive explicit state snapshots, preventing stale reads.
- Availability is deterministic and tied to coordinator health.
- Unidirectional flow prevents hidden coupling and state mutation.
