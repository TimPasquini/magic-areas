# Architecture overview

This document summarizes the runtime architecture and explains how it differs
from the fork baseline (commit `d7b5779`). It focuses on information flow,
state ownership, and event propagation so a reviewer can continue development
from the updated structure.

## Integration layout

- `custom_components/magic_areas/__init__.py`
  - config entry lifecycle (setup, unload, migrate)
  - coordinator creation and first refresh
  - AREA_LOADED dispatch for non-meta areas
  - meta-area reload subscription (via coordinator)
  - config entry migrations (unique ID updates)

- `custom_components/magic_areas/entity.py`
  - shared entity base classes (`MagicEntity`, `MagicGroupEntity`)
  - *(MagicArea and MagicMetaArea classes removed; coordinator owns area state directly)*
  - entity metadata resolved via `feature_info.py` using `feature_id` lookup

- `custom_components/magic_areas/core/`
  - HA-free helpers: config normalization, presence selection, entity grouping,
    aggregate building, state priority, policy evaluation
  - Key modules:
    - `area_config.py` — `AreaConfig` dataclass (immutable per-entry configuration)
    - `area_runtime.py` — `AreaRuntime` dataclass (current runtime state)
    - `aggregate_selection.py` — aggregate spec selection, health spec building (pure)
    - `presence.py` — `build_presence_sensors()`, `compute_secondary_states()` (pure)
    - `light_control.py` — `LightGroupPolicy.evaluate()` with full turn-off conditions
    - `climate_control.py`, `fan_control.py`, `media_routing.py` — control policies
    - `meta_reload.py` — `evaluate_reload()` for meta-area reload throttling
    - `config.py`, `entity_ids.py` — config and entity reference helpers
    - `entity_loading/` — entity ingestion package:
      - `loader.py` — area/meta-area entity load orchestration
      - `registry_queries.py` — entity/device registry queries
      - `filters.py` — shared exclusion rules
      - `snapshots.py` — normalized grouped snapshot output

- `custom_components/magic_areas/coordinator.py`
  - `MagicAreasCoordinator`: owns a private `AreaConfig`, refreshes snapshots
  - meta-area reload: subscribes to `AREA_LOADED`, throttles via `evaluate_reload()`
  - builds `MagicAreasData` snapshot on every refresh

- `custom_components/magic_areas/{platform}.py` / `{platform}/__init__.py`
  - platform setup functions are registry-driven routers
  - each platform reads `coordinator.data` exclusively
  - entity constructors receive `AreaConfig` + `MagicAreasCoordinator`

- `custom_components/magic_areas/features/`
  - `base.py` defines the `FeatureModule` contract + config flow steps
  - `registry.py` is the single runtime registry for feature modules
  - `modules/` hosts per-feature implementations

- `custom_components/magic_areas/config_flow.py`
  - UI config flow entry point
  - `config_flows/options_flow.py` — options flow handler (dynamic feature routing)
  - `config_flows/steps/` — step handlers (area_steps, feature_selection, feature_config)
  - `config_flows/feature_registry.py` — config-flow registry built from feature modules

- Supporting modules:
  - `config_keys.py`, `defaults.py`, `enums.py`, `policy.py`
  - `area_state.py`, `area_maps.py`, `icons.py`
  - `feature_info.py`, `ha_domains.py`, `models.py`, `const.py`

## Runtime data flow (current)

```
Config entry setup
  └─ __init__.py
       ├─ build_area_config_for_config_entry() → AreaConfig (from area/floor registry)
       ├─ create MagicAreasCoordinator(hass, area_config, config_entry)
       │    └─ meta areas: subscribe to AREA_LOADED dispatcher
       ├─ coordinator.async_config_entry_first_refresh()
       ├─ dispatch AREA_LOADED (non-meta areas, after HA start)
       └─ runtime_data = MagicAreasRuntimeData { coordinator, listeners }

Coordinator refresh
  └─ coordinator.py
       ├─ _async_update_data() using self._area_config
       └─ MagicAreasData snapshot:
            - area_config    (AreaConfig — immutable configuration)
            - area_runtime   (AreaRuntime — last_update_success flag)
            - entities       (entity lists by domain)
            - magic_entities (integration-generated entity IDs by domain)
            - presence_sensors
            - active_areas   (meta only: active child area IDs)
            - config         (merged options dict)
            - enabled_features
            - feature_configs
            - entity_references (resolved entity IDs for cross-platform use)
            - updated_at

Options flow (schema-driven)
  └─ config_flows/options_flow.py
       ├─ menu built from enabled features + config-flow registry
       ├─ feature_conf_* steps routed dynamically to a generic handler
       └─ UI forms built directly from vol schemas

Platform setup (registry-driven)
  ├─ binary_sensor/__init__.py
  ├─ sensor/__init__.py
  ├─ light.py
  ├─ media_player/__init__.py
  ├─ switch/__init__.py
  ├─ fan.py, cover.py
       └─ read coordinator.data (MagicAreasData snapshot)
          └─ dispatch to FeatureRegistry modules per domain
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

## Event flow (current)

```
Presence tracking updates
  └─ binary_sensor/presence.py
       ├─ computes new, lost, and current area states
       │    └─ compute_secondary_states() from core/presence.py (pure)
       └─ dispatcher sends AREA_STATE_CHANGED(area_id, (new, lost, current))

Platform handlers
  ├─ light groups      (LightGroupPolicy.evaluate() in core/light_control.py)
  ├─ climate control   (core/climate_control.py policy)
  ├─ fan control       (core/fan_control.py policy)
  └─ media player      (core/media_routing.py)
       └─ react to current state snapshot from event payload
          └─ NO stale reads from coordinator or area state

Meta-area reload
  └─ AREA_LOADED dispatcher (sent by __init__.py after child areas start)
       └─ coordinator._handle_loaded_area()
            └─ evaluate_reload() from core/meta_reload.py (pure)
               → schedule config entry reload if throttle window passed
```

Event payloads include `current_states` to prevent stale reads during async
scheduling.

## Identity and availability flow (current)

```
coordinator refresh
  ├─ success → area_runtime.last_update_success = True
  └─ failure → area_runtime.last_update_success = False

entities
  └─ availability follows coordinator-driven flag (coordinator.last_update_success)

config entry migration (async_migrate_entry)
  └─ entity registry unique IDs updated to stable area-based format
     old: magic_areas_{platform}_{area_slug}_{suffix}
     new: {feature_id}_{area_id}[_{suffix}]
```

## Unidirectional Data Flow

Data flows in one direction through the system:

```
AreaConfig (from area/floor registry + config entry)
  ↓
Coordinator._async_update_data()
  ↓
MagicAreasData snapshot
  ↓
Platforms read coordinator.data
  ├─ binary_sensor/__init__.py
  ├─ sensor/__init__.py
  ├─ light.py
  ├─ fan.py
  ├─ cover.py
  ├─ media_player/__init__.py
  └─ switch/__init__.py
  └─ etc.
     ↓
Entities created from snapshot
  ├─ Receive AreaConfig (immutable) + coordinator reference
  ├─ Read area_config, area_runtime, entities, presence_sensors, config
  └─ NO access to internal coordinator state or platform-adjacent entities

Event dispatch (presence state changes)
  └─ AREA_STATE_CHANGED(area_id, snapshot_data)
     ↓
Platform handlers (light, climate, fan, media)
  └─ React to event payload snapshot
     └─ Pure policy evaluation in core/ modules
        └─ HA service calls only (no coordinator or area access)
```

**Key property**: Platforms and entities consume snapshot data. They never:
- Call methods on a MagicArea/MagicMetaArea object (these classes are removed)
- Trigger coordinator refresh
- Modify snapshot data
- Bypass the snapshot to access area state

## Feature modules and registry (current)

Runtime feature modules are the single source of truth for:
- platform entity construction per feature (`build_entities`)
- feature dependencies (`depends_on`)
- config flow steps (`config_flow_steps`)

```
FeatureRegistry (features/registry.py)
  ├─ AggregatesFeatureModule
  ├─ WaspInABoxFeatureModule
  ├─ LightGroupsFeatureModule (light groups + light control switch)
  ├─ FanGroupsFeatureModule (fan group + control switch)
  ├─ MediaPlayerGroupsFeatureModule (group + control switch)
  ├─ CoverGroupsFeatureModule (device-class cover groups)
  ├─ PresenceHoldFeatureModule (switch)
  ├─ ClimateControlFeatureModule (switch)
  ├─ HealthFeatureModule (problem binary sensor)
  ├─ BLETrackersFeatureModule (monitor sensor)
  └─ AreaAwareMediaPlayerFeatureModule (config-only)

Platforms call FeatureRegistry.modules_for_domain(domain) and attach entities
per module. Config flows build their per-feature menu from the same registry,
ensuring feature metadata is defined once.
```

This unidirectional flow ensures:
- Consistent data reads (all use snapshot)
- Predictable execution (no hidden state mutations)
- Clear ownership (coordinator owns AreaConfig, platforms own entities)
- Testable behavior (mock coordinator.data, test entities in isolation)
- Pure policy evaluation in `core/` modules (testable without HA)

## Why this matters

- The snapshot ensures consistent entity lists across platforms.
- Refresh logic is centralized and testable in one place.
- `AreaConfig` replaces the `MagicArea` god object — it is an immutable
  dataclass derived entirely from the HA area registry and config entry.
- Platforms are thin wiring layers: snapshot data → HA entity constructors.
- Policy decisions (turn on/off, reload, aggregate) live in pure `core/` functions.
- Event handlers receive explicit state snapshots, preventing stale reads.
- Availability is deterministic and tied to coordinator health.
- Unidirectional flow prevents hidden coupling and state mutation.
