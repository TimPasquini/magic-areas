# Config flow differences

This document describes how config and options flow behavior is organized in
this integration compared to the fork baseline (commit `d7b5779`).

## Fork baseline behavior

The options flow used a single, long class with many feature-specific branches.
Adding or updating a feature required touching multiple methods and duplicating
validation logic across steps. Configuration UI defaults and validation rules
were duplicated across multiple files.

The baseline options UI was closer to a staged edit flow: users navigated broad
feature forms and expected a final completion action to write the accumulated
changes. Large feature pages, especially light groups, mixed several decisions
into one screen.

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

## Options flow UX and persistence (current)

The fork now treats a completed options-flow page as the persistence boundary.
Successful submits call `async_update_entry` for the current options payload
instead of staging all edits behind a final root-menu save action.

Current user-facing contract:

- Complete pages save when submitted.
- Closing the options flow discards only the current unsubmitted page.
- The root options menu does not expose Done, Finish, or Save & Exit.
- Invalid submits stay on the same form and do not persist invalid data.
- Failed custom-control group validation re-renders the submitted records so the
  user can correct them instead of starting over.
- Reopened forms use saved values as suggested/default values.

The root menu intentionally distinguishes direct single-page tasks from
multi-page domains.

Direct root forms:

- Area behavior.
- Presence tracking.
- Area states.
- Custom control groups.
- Health sensors.
- Aggregate sensors.
- Presence hold.
- Bluetooth tracker monitoring.
- Wasp in a Box.
- Area-aware media player.

Intentional submenus:

- Light roles and automation: role membership, brightness behavior, and
  Adaptive Lighting coordination.
- Fan automation: retained as a domain submenu for current and planned fan
  triggers such as humidity, odor/manual-duration, temperature, and air quality.
- Climate automation: climate device selection followed by preset mapping.

Guided flows persist only at their completion boundary:

- Climate device selection advances to preset mapping; preset mapping persists
  the climate automation config.
- Light-group Classic brightness behavior persists immediately.
- Light-group Advisory and Adaptive brightness behavior persist after their
  mode-specific settings page submits.
- Adaptive Lighting `ignore` persists immediately.
- Adaptive Lighting `adopt_existing` and `manage` persist after required
  pairing or managed-role/all-lights choices submit.

Dormant mode-specific values are preserved where useful. For example, switching
from Adaptive brightness behavior to Advisory hides Adaptive-only fields from
the active UI/runtime path, but switching back restores the prior Adaptive
settings as suggestions instead of deleting them.

## Delta summary (vs fork baseline)

- Validation/UI is now driven directly from vol schemas (single source of truth).
- The OPTIONS_* lists and the `schemas/validation.py` file are removed.
- The options flow no longer requires one method per feature step; steps are
  routed dynamically.
- Feature configuration and feature UI metadata are centralized and consistent
  with the runtime registry.
- Options-flow persistence is page-level for complete pages rather than final
  root-menu save/finish.
- Root Done/Finish/Save & Exit is intentionally not exposed.
- One-child intermediary menus are removed for direct single-page tasks.
- Light groups, Fan automation, and Climate automation remain intentional
  submenus because they represent multi-step or multi-use-case domains.
- Guided flows persist only when their required dependent choices are complete.
- Failed validation preserves user-entered values where the frontend can safely
  re-render them, notably custom control-group records.
- Light-group config can now express:
  - brightness switching mode (`inhibit`, `advisory`, `adaptive`)
  - adaptive guard settings and inside/outside signal selectors
  - Adaptive Lighting mode (`ignore`, `adopt_existing`, `manage`)
  - role-scoped Adaptive Lighting switch-set adoption or managed-role selection

## User-facing behavior
Compared to the fork baseline, the options UI is task-oriented rather than
module-shaped. Users configure room behavior through direct forms for simple
tasks and guided submenus for domains that require multiple related decisions.
Submitted complete pages save immediately, so users do not lose prior submitted
work when closing the flow after an unrelated mistake.
