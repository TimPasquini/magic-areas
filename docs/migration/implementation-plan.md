# Implementation plan

This is a living plan for refactoring the current fork from the original
baseline into a cleaner, Home Assistant-aligned architecture. It records the
target structure, boundaries, and sequencing so we can keep changes coherent.
Update this file as decisions change, new work lands, or scope shifts.

## Goals

- reduce cross-module coupling and duplicated logic
- centralize runtime data shaping in the coordinator snapshot
- keep platform files focused on entity wiring only
- preserve current user-facing behavior and config flow UX
- keep Bronze tier requirements satisfied while improving internals
- improve testability by isolating domain logic from HA entity classes
- make future feature additions require changes in one place (core or config)

## Non-goals

- redesign user-facing features or behavior
- change config entry data format unless required by HA
- remove features or reduce existing platform coverage
- introduce new platforms during refactor
- rewrite tests for style or aesthetic changes

## Constraints

- Python 3.13+
- HA integration patterns (config flow, options flow, coordinator, entities)
- strict typing kept consistent with current platinum goal
- tests remain green throughout refactors
- no breaking changes to existing config entry data
- avoid large-scale renames that make diffs hard to review

## Current state summary

- `base/magic.py` is the primary aggregator of area state and domain logic.
  It mixes orchestration, filtering, and derived values in one file.
- platform files (`light.py`, `binary_sensor/presence.py`, etc.) still compute
  entity lists and filters independently, which creates drift risk.
- `config_flow.py` is large and blends flow mechanics with feature logic,
  selectors, and validation patterns.
- coordinator snapshot exists, but not all platforms fully depend on it yet.
- helpers and schemas are used inconsistently across flows and platforms.

## Inventory and hotspots

This list identifies the most complex files and why they are high priority.
Use this as a working checklist when breaking work into smaller tasks.

- `custom_components/magic_areas/base/magic.py`
  - role: main aggregator of area state and derived values
  - concerns: many responsibilities in one file, difficult to isolate tests
  - risk: changes here can impact multiple platforms simultaneously

- `custom_components/magic_areas/binary_sensor/presence.py`
  - role: presence logic and binary sensor behavior
  - concerns: mixes presence rules, entity wiring, and event handling
  - risk: user-visible behavior (occupancy) can regress

- `custom_components/magic_areas/light.py`
  - role: light group coordination and helper behavior
  - concerns: data shaping lives inside platform module
  - risk: light groups and tracking logic are tightly coupled

- `custom_components/magic_areas/config_flow.py`
  - role: UI setup and options flow
  - concerns: large class, feature-specific logic in flow itself
  - risk: test coverage is high but regression surface is large

- `custom_components/magic_areas/helpers/*`
  - role: misc utilities and registry access
  - concerns: shared helpers sometimes hide domain logic
  - risk: helper usage is inconsistent between platforms

## Target layout

The goal is to organize code by responsibility and keep modules narrow.
We will not necessarily rename every file, but new functionality should align
to these boundaries.

- `custom_components/magic_areas/core/`
  - area model and state evaluation
  - entity list assembly and filtering
  - derived values (presence, aggregates, meta area state)
  - snapshot-friendly data structures
  - no HA entity classes or registry calls
  - expected modules:
    - `core/area_model.py`: core representation of a MagicArea state
    - `core/entities.py`: normalized entity list assembly by domain
    - `core/presence.py`: presence, timeouts, and secondary states
    - `core/aggregates.py`: aggregate sensor logic
    - `core/meta.py`: meta area orchestration and child area resolution

- `custom_components/magic_areas/coordinator.py`
  - owns snapshot construction and refresh lifecycle
  - exposes `MagicAreasData` as the only read model for platforms
  - translates `MagicArea` into snapshot fields used by entities
  - no platform-specific filtering outside snapshot building

- `custom_components/magic_areas/platforms/`
  - platform adapters (`sensor`, `binary_sensor`, `light`, etc.)
  - convert snapshot data into entity instances only
  - no domain logic beyond HA entity wiring
  - use shared base entity classes where possible
  - all entity filtering should be snapshot-based, not registry-based

- `custom_components/magic_areas/config/`
  - schemas, validation, and feature metadata
  - config flow helpers and selectors
  - reusable option-building helpers with consistent patterns
  - avoid direct entity registry access unless required for selectors

- `custom_components/magic_areas/helpers/`
  - HA integration helpers (registry access, timers, selectors)
  - runtime utilities that are HA-aware but not domain-specific
  - no feature-specific logic here

## Phased plan

### Phase 1: Align boundaries

- inventory platform files that still compute area state directly
- define which fields must be present in `MagicAreasData`
- add missing snapshot fields to the coordinator
- ensure all platforms can use snapshot values
- add explicit fallbacks where snapshot data might be `None`

Planned actions:

- create a snapshot field matrix by platform:
  - sensors: `entities`, `magic_entities`, `config`, aggregates
  - binary sensors: presence data, secondary state data
  - lights: group members, tracking entities, config options
  - media player: area-aware settings, entity ids
  - switches: feature flags and entity ids
- identify where each platform currently reads `MagicArea` directly
- update coordinator snapshot to include those fields
- add a single fallback path in each platform (snapshot or area), not both
- ensure coordinator refresh is used before platform setup

Deliverables:

- snapshot completeness checklist
- coordinator tests that verify expected snapshot fields
- platform files updated to prefer snapshot fields
- design notes for any snapshot fields not yet supported
- per-platform usage notes (which snapshot fields each platform consumes)

### Phase 2: Extract core domain logic

- split `base/magic.py` into focused modules (presence, aggregates, meta state)
- keep pure logic modules free of HA entity references
- update coordinator to call these modules
- consolidate filtering and derived-state rules into core modules

Planned actions:

- extract entity filtering logic into `core/entities.py`
- move presence timeout logic into `core/presence.py`
- move aggregate calculations into `core/aggregates.py`
- move meta area resolution into `core/meta.py`
- keep `base/magic.py` as a compatibility wrapper that calls core modules
- update coordinator to build snapshot from `core/*` outputs

Deliverables:

- new `core/` modules with targeted tests
- `base/magic.py` reduced to orchestration or removed
- unit tests for core modules that do not import HA entity classes
- cross-module integration tests that verify snapshot correctness

### Phase 3: Simplify platform adapters

- move domain logic from platforms into `core/`
- replace per-platform filtering with snapshot lookups
- remove unused helpers or redundant functions
- unify common entity behaviors through base classes

Planned actions:

- reduce platform modules to entity wiring only
- replace registry reads with snapshot lookups
- remove platform-local selectors or filters where snapshot provides data
- add base entity classes for shared behavior (availability, device info)
- remove platform-specific duplicates of the same filter logic

Deliverables:

- platform modules reduced to entity wiring
- consistent platform behavior across domains
- fewer platform-specific filters or registry calls
- per-platform tests updated only where behavior changed

### Phase 4: Config flow modularization

- move selector builders and feature schemas to `config/`
- keep `config_flow.py` as thin orchestration over registry
- keep options flow routing stable and test-covered
- reduce feature-specific logic inside flow class methods

Planned actions:

- move selector helpers into `config/selectors.py`
- move feature schemas into `config/features.py`
- keep `feature_registry.py` purely declarative
- keep `config_flow.py` responsible only for flow steps and routing
- ensure options flow is tested for each feature path

Deliverables:

- smaller `config_flow.py`
- clear separation between flow mechanics and feature metadata
- consistent selector and validation patterns across features
- no feature-specific schema logic inside flow steps

### Phase 5: Cleanup and consolidation

- remove legacy helpers no longer used by platforms
- update documentation and migration notes
- re-check quality scale and Bronze alignment
- add targeted clean-up tests if refactors altered code paths

Planned actions:

- delete unused helper functions and update imports
- reduce duplication between platform modules
- update docs with the new module map
- confirm quality scale items are accurate and not stale

Deliverables:

- reduced file surface area
- updated docs and diagrams
- final quality scale checklist pass
- release notes summary for upstream review

## Refactor targets by priority

1) `custom_components/magic_areas/base/magic.py`
2) `custom_components/magic_areas/binary_sensor/presence.py`
3) `custom_components/magic_areas/light.py`
4) `custom_components/magic_areas/config_flow.py`
5) `custom_components/magic_areas/helpers/*`
6) `custom_components/magic_areas/media_player/*`
7) `custom_components/magic_areas/switch/*`

## File-by-file migration map

Use this table as a working map of where logic should move.

- `base/magic.py` -> `core/area_model.py`, `core/entities.py`,
  `core/presence.py`, `core/aggregates.py`, `core/meta.py`
- `binary_sensor/presence.py` -> `core/presence.py` (logic), platform module
  becomes entity wiring only
- `light.py` -> `core/entities.py` + `core/aggregates.py` for grouping logic
- `config_flow.py` -> `config/selectors.py`, `config/features.py`,
  `config/validation.py` (flow keeps routing only)
- `helpers/area.py` -> `core/area_model.py` if logic is domain specific
- `helpers/timer.py` -> remain in helpers (HA-aware utility)

## Snapshot field checklist by platform

This checklist defines the minimum snapshot fields each platform should read.
Use it to guide coordinator updates and platform simplification.

### Sensors

- `entities` for sensor domains
- `magic_entities` for integration-managed sensors
- `config` for aggregate and threshold options
- `updated_at` for debug/diagnostic metadata

### Binary sensors

- `presence_sensors` for presence and occupancy signals
- `entities` for source binary sensor lists
- `magic_entities` for integration-managed binary sensors
- `config` for presence timeouts and tracking options

### Lights

- `entities` for light group membership
- `magic_entities` for integration-managed light groups
- `config` for light tracking and transition options

### Media player

- `entities` for media player group membership
- `magic_entities` for integration-managed groups
- `config` for area-aware media player options

### Switches

- `entities` for switch group membership (if any)
- `magic_entities` for integration-managed switches
- `config` for feature enablement and per-feature options

### Fan, cover, climate

- `entities` for grouped domain members
- `magic_entities` for integration-managed group entities
- `config` for domain-specific options and presets

### Meta areas

- `active_areas` for aggregated entity lists
- `entities` and `magic_entities` for child-area aggregation
- `config` for meta aggregation rules

### Diagnostics and health

- `config` for reporting current settings
- `updated_at` for last refresh timestamp
- `area` for identity metadata (name, id, type)

## Phase 1 snapshot gap assessment (current state)

This section records which platforms still read `MagicArea` directly and what
snapshot fields or helpers are missing for a clean migration.

### Platforms already using snapshot (with fallback)

- `sensor/__init__.py`
  - uses snapshot `entities` and `magic_entities` with fallback to area
  - gap: still depends on `area` when snapshot is missing

- `binary_sensor/__init__.py`
  - uses snapshot `entities` and `magic_entities` with fallback to area
  - gap: fallback path still uses direct area reads

- `light.py`
  - uses snapshot `entities` and `magic_entities` with fallback to area
  - gap: fallback path still uses direct area reads

- `binary_sensor/presence.py`
  - uses snapshot `presence_sensors`
  - gap: relies on runtime `area` for feature checks

### Platforms still reading area directly

- `cover.py`
  - reads `area.entities` and `area.magic_entities`
  - needs snapshot `entities` and `magic_entities` for cover domain

- `fan.py`
  - reads `area.entities` and `area.magic_entities`
  - needs snapshot `entities` and `magic_entities` for fan domain

- `media_player/__init__.py`
  - reads `area.entities` for media player groups
  - uses snapshot only when scanning entries for area-aware media player
  - needs snapshot `entities` for group setup and a snapshot-friendly feature
    config accessor for area-aware media player settings

- `switch/__init__.py`
  - reads `area` to check feature flags and add entities
  - needs snapshot-driven feature enablement flags

- `threshold.py`
  - reads `area.entities` and `area.feature_config`
  - needs snapshot `entities` and a helper for feature config access

- `diagnostics.py`
  - reads `area.entities` and `area.magic_entities`
  - should prefer snapshot fields for reporting

### Config flow (intentional direct reads)

- `config_flow.py`
  - uses `area.entities` for selectors and feature validation
  - intended to read live registry state; not a snapshot target

### Snapshot field gaps to resolve in Phase 1

- add snapshot accessors for feature config lookups
  - current pattern: `area.feature_config(feature_key)`
  - proposed: snapshot helper or derived field for feature configs

- add snapshot-derived feature flags
  - current pattern: `area.has_feature(feature_key)`
  - proposed: snapshot `enabled_features` list or mapping

- reduce fallback reliance
  - once snapshot includes the above helpers, remove direct area reads

## Phase 1 tasks with acceptance criteria

These tasks are the concrete Phase 1 deliverables. Each item lists the
expected changes and how we verify them.

### Coordinator snapshot extensions

Task:
- add `enabled_features` and `feature_configs` to `MagicAreasData`
- populate these from `area.config` / `area.feature_config`
- provide a small helper in coordinator for safe access

Acceptance criteria:
- `MagicAreasData` exposes `enabled_features: set[str]` or `list[str]`
- `MagicAreasData` exposes `feature_configs: dict[str, dict[str, Any]]`
- coordinator tests confirm these values are present and non-empty when
  features are configured

### Cover platform (`cover.py`)

Task:
- switch to snapshot `entities` and `magic_entities`
- use snapshot feature flags for `CONF_FEATURE_COVER_GROUPS`

Acceptance criteria:
- no direct read of `area.entities` or `area.magic_entities`
- cover groups still created for each device class
- tests pass without changes to expected behavior

### Fan platform (`fan.py`)

Task:
- switch to snapshot `entities` and `magic_entities`
- use snapshot feature flags for `CONF_FEATURE_FAN_GROUPS`

Acceptance criteria:
- no direct read of `area.entities` or `area.magic_entities`
- fan group creation uses snapshot entity ids
- tests pass without behavior changes

### Media player platform (`media_player/__init__.py`)

Task:
- use snapshot `entities` when building media player groups
- use snapshot feature configs when evaluating area-aware media player settings

Acceptance criteria:
- no direct read of `area.entities` in `setup_media_player_group`
- area-aware media player logic uses snapshot data when available
- existing tests pass without behavior changes

### Switch platform (`switch/__init__.py`)

Task:
- use snapshot `enabled_features` for feature gating
- use snapshot `magic_entities` for cleanup

Acceptance criteria:
- no direct read of `area.has_feature`
- feature switches are still created appropriately
- cleanup still uses snapshot `magic_entities`

### Threshold platform (`threshold.py`)

Task:
- use snapshot `entities` for illuminance sensors
- use snapshot feature configs for aggregation options

Acceptance criteria:
- no direct read of `area.entities` inside threshold creation
- feature configs read via snapshot helper
- threshold tests still pass

### Diagnostics (`diagnostics.py`)

Task:
- report snapshot `entities` and `magic_entities` instead of area fields
- include snapshot `updated_at` in diagnostics

Acceptance criteria:
- diagnostics output matches current structure with updated timestamp
- tests updated only if required for snapshot timestamp field

### Fallback removal

Task:
- remove snapshot fallback to `area` in platforms after fields are present

Acceptance criteria:
- platform code does not branch on snapshot existence
- coordinator refresh happens before platform setup
- tests remain green
## Tests and coverage goals

- all existing tests remain green
- new coordinator snapshot fields get unit tests
- new core modules get focused unit tests
- config flow coverage remains at 100%
- maintain overall coverage above 95%
- add regression tests when moving logic out of platforms
- prioritize behavior-based assertions over internal helpers

Test additions by phase:

- Phase 1: coordinator snapshot field tests per platform
- Phase 2: core module unit tests (presence, aggregates, meta)
- Phase 3: platform tests verifying entity wiring reads snapshot only
- Phase 4: options flow tests remain at 100% coverage
- Phase 5: clean-up tests for any removed legacy paths

## Definition of done (per phase)

- all tests pass
- no new lint or mypy errors
- platform behavior matches current baseline
- migration docs updated to reflect structural changes
- core modules have isolated tests where possible
- platform modules contain no duplicated filtering logic
- coordinator snapshot is the single source of truth for platforms

## Risks and mitigation

- risk: subtle behavior changes during logic extraction
  - mitigation: keep tests behavior-focused and add snapshot tests early
- risk: platform drift if snapshot fields are incomplete
  - mitigation: use snapshot completeness checklist per platform
- risk: config flow regressions due to refactoring
  - mitigation: keep options flow tests comprehensive before changes
- risk: large diffs that are hard to review
  - mitigation: split refactors into small, reviewable commits

## Decision log

Add decisions as they are made:

- 2026-01-08: coordinator snapshot is the preferred read path for platforms
- 2026-01-08: platform logic should migrate to snapshot-only access where
  snapshot data is available
- 2026-01-08: refactors will avoid changing config entry data structures
