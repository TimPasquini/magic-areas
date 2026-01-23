# Migration guide

This folder documents how this integration differs from the version we forked
(commit `d7b5779`). The goal is to make upstream review straightforward by
capturing the actual technical deltas so a reviewer can continue development
from the updated architecture.

## Scope

These documents cover code, runtime, and test deltas between the fork baseline
and this repository, including:

- runtime architecture and information flow
- coordinator snapshot model and availability semantics
- config flow structure and feature metadata layout
- platform adapter responsibilities
- entity identity and migration behavior
- event payload changes and state propagation
- test coverage changes that validate the new behavior
- repository and tooling changes that affect development

## Delta inventory (by category)

Each item below maps to concrete file changes and is covered in one of the
migration documents.

### Runtime architecture and data flow

- Coordinator introduced as the authoritative snapshot source.
- Snapshot gate: platform setup is skipped if data is unavailable.
- Event payloads include full current state snapshots to avoid stale reads.

### Core logic boundaries

- New core helpers under `custom_components/magic_areas/core/` for config
  normalization, presence selection, and entity grouping.
- `base/magic.py` reduced toward orchestration over shared helpers.

### Platform adapters

- `binary_sensor`, `sensor`, `light`, `fan`, `cover`, `media_player`, `switch`,
  and `threshold` now read snapshot fields rather than deriving data locally.
- Climate control, media player control, and fan control now react to event
  snapshots, not cached `MagicArea` state.
- Diagnostics now read snapshot data and updated timestamps.

### Identity and availability

- Unique ID strategy updated to remove domain prefixes and use stable area IDs.
- Migration updates entity registry unique IDs to the new format.
- Availability reflects coordinator refresh success.

### Config flow and schemas

- Feature metadata moved to `config_flows/feature_registry.py`.
- New schema and validation modules consolidate config and options flow logic.
- Constants split into `config_keys.py`, `defaults.py`, `enums.py`, and
  `area_constants.py`.

### Tests and verification

- Expanded integration tests for snapshot usage per platform.
- New tests for coordinator behavior, core helpers, and availability.
- Regression coverage for event payload semantics and edge cases.

### Repository and tooling

- Development guidance consolidated in `AGENTS.md` and `tests/AGENTS.md`.
- Added `uv.lock` and updated Python tooling configuration.
- Editor configs added for local developer environments.

## How to use these notes

- Read `architecture.md` for the updated information flow and event model.
- Read `coordinator.md` for the snapshot model, availability semantics, and
  platform setup rules.
- Read `config-flow.md` for config/option flow structure and schema layout.
- Read `tests.md` for the test coverage delta and delta-to-test mapping.

## Reviewer checklist

- Snapshot is the single source of truth for platform setup.
- Event payloads carry current state snapshots for deterministic handling.
- Unique IDs are stable and migrated correctly.
- Availability reflects coordinator health.
- Config flow metadata and schemas are centralized.
- Tests map to the documented deltas.
