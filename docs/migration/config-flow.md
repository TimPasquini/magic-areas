# Config flow differences

This document describes how config and options flow behavior is organized in
this integration compared to the fork baseline (commit `d7b5779`).

## Fork baseline behavior

The options flow used a single, long class with many feature-specific branches.
Adding or updating a feature required touching multiple methods and duplicating
validation logic across steps.

## Updated behavior

Feature configuration is registry-driven:

- `config_flows/feature_registry.py` declares each feature in one place.
- `async_step_feature_conf` handles feature configuration generically.
- schemas, selectors, and validators are built consistently.
- feature-specific step methods remain thin wrappers when needed.

## Supporting schema and config modules

Configuration data and constants are no longer centralized in `const.py` and
are instead split into focused modules:

- `config_keys.py`: all config keys and default values
- `defaults.py`: default policy values and feature defaults
- `enums.py`: typed enums for feature IDs, area states, and policy options
- `schemas/area.py`: area-level schema and defaults
- `schemas/features.py`: per-feature schema definitions
- `schemas/validation.py`: cross-cutting validation helpers
- `features.py` / `feature_info.py`: feature metadata and translations
- `policy.py`: internal policy tables for filtering and behavior

This split is required to keep config flow logic consistent with the
coordinator snapshot and the new core helpers.

## Feature registry structure

Each feature entry provides:

- `name`: feature key
- `options`: list of options for schema generation
- `schema`: optional explicit schema
- `merge_options`: whether to merge or replace feature config
- `next_step`: optional follow-up step ID

This keeps per-feature logic declarative and easier to maintain.

## Delta summary (what changed vs fork baseline)

- Feature metadata moved into `config_flows/feature_registry.py`.
- The flow uses a generic feature handler for most steps and only keeps thin
  wrappers for custom cases.
- Schemas, selectors, and validators are defined once and reused, reducing
  drift between config flow and options flow behavior.

## User-facing behavior

From the user perspective, UI setup and options flow remain stable. The
differences are internal: feature metadata is centralized, config validation is
consistent, and the flow logic is less error-prone.
