# Config flow differences

This document describes how config and options flow behavior is organized in
this integration compared to the fork baseline (commit `d7b5779`).

## Fork baseline behavior

The options flow used a single, long class with many feature-specific branches.
Adding or updating a feature required touching multiple methods and duplicating
validation logic across steps. Configuration UI defaults and validation rules
were duplicated across multiple files.

## Current behavior (authoritative)

The options flow is schema-driven and registry-backed:

- `config_flows/helpers.py:get_feature_config_steps` derives configurable steps
  directly from runtime feature modules (`features/registry.py`) and their
  `FeatureConfigStep` definitions.
- `config_flows/steps/feature_config.py` provides a generic handler for feature
  configuration, using the feature schema directly.
- `config_flows/options_flow.py` routes any `feature_conf_*` step dynamically via
  `async_step` and a dynamic step proxy (`__getattr__`) so individual feature
  step methods are not required.
- Config UI is built directly from `vol.Schema` definitions using
  `ConfigBase._build_schema_from_vol`.

Custom feature steps still exist only when necessary:

- Climate control presets use `config_flows/steps/feature_config_climate.py`
  (second step) to build selectors and validators based on the selected entity.
- Light groups use mode-specific inline schema shaping for adaptive switching
  and Adaptive Lighting coordination because the visible fields depend on the
  selected mode.

## Supporting schema and config modules

Configuration data and constants are split into focused modules:

- `config_keys/`: scoped config key modules (area/entities/presence/features/system)
- `defaults.py`: default policy values and feature defaults
- `enums.py`: typed enums for feature IDs, area states, and policy options
- `schemas/area.py`: area-level schemas and defaults
- `features/modules/*.py`: per-feature schema ownership and config-step definitions
- `light_groups/config.py`: light-group preset definitions, adaptive-switching
  settings, and Adaptive Lighting coordination settings
- `feature_info.py`: feature metadata registry (translation keys, icons)
- `policy.py`: internal policy tables for filtering and behavior

## Feature registry structure

`config_flows/helpers.py:get_feature_config_steps` provides a single registry
entry per feature, derived from `FeatureConfigStep`:

- `feature`: feature key (`MagicAreasFeatures`)
- `schema`: the `vol.Schema` used to validate and build the UI
- `merge_options`: whether to merge or replace feature config
- `next_step`: optional follow-up step ID (e.g. climate presets)

This keeps per-feature logic declarative and reduces duplication.

## Config step flow (current)

- `async_step_show_menu` builds a menu from enabled features and the registry.
- `async_step` routes any `feature_conf_*` step to the generic handler.
- `handle_feature_conf` validates against the feature schema and saves to
  `CONF_ENABLED_FEATURES` in options.
- `handle_area_config`, `handle_presence_tracking`, and `handle_secondary_states`
  are still explicit steps, but their UI is schema-driven via
  `_build_schema_from_vol`.

## Delta summary (vs fork baseline)

- Validation/UI is now driven directly from vol schemas (single source of truth).
- The OPTIONS_* lists and the `schemas/validation.py` file are removed.
- The options flow no longer requires one method per feature step; steps are
  routed dynamically.
- Feature configuration and feature UI metadata are centralized and consistent
  with the runtime registry.
- Light-group config can now express:
  - brightness switching mode (`inhibit`, `advisory`, `adaptive`)
  - adaptive guard settings and inside/outside signal selectors
  - Adaptive Lighting mode (`ignore`, `adopt_existing`, `manage`)
  - role-scoped Adaptive Lighting switch-set adoption or managed-role selection

## User-facing behavior
Base UI behavior remains aligned with the fork baseline for existing defaults,
but this fork adds opt-in configuration surfaces for adaptive switching,
managed helper-backed signals, label-backed role membership, and Adaptive
Lighting coordination. Configuration definitions are centralized, UI generation
is schema-driven, and feature steps no longer require boilerplate handlers.
