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

- `config_flows/feature_registry.py` builds a registry from the runtime feature
  modules (`features/registry.py`) and their `FeatureConfigStep` definitions.
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

## Supporting schema and config modules

Configuration data and constants are split into focused modules:

- `config_keys.py`: config keys and default values
- `defaults.py`: default policy values and feature defaults
- `enums.py`: typed enums for feature IDs, area states, and policy options
- `schemas/area.py`: area-level schemas and defaults
- `schemas/features/*.py`: per-feature schema definitions
- `schemas/features/__init__.py`: `CONFIGURABLE_FEATURES` map
- `feature_info.py`: feature metadata registry (translation keys, icons)
- `policy.py`: internal policy tables for filtering and behavior

## Feature registry structure

`config_flows/feature_registry.py` provides a single registry entry per feature,
derived from `FeatureConfigStep`:

- `name`: feature key (`MagicAreasFeatures`)
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

## User-facing behavior
UI behavior is consistent with the fork baseline. The changes are internal:
configuration definitions are centralized, UI generation is schema-driven, and
feature steps no longer require boilerplate handlers.
