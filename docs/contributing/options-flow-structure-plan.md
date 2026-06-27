# Options-Flow Structure Plan

This temporary planning document scopes and tracks the options-flow structural
work. Do not delete it while this options-flow structure work is active. When
the work closes, transfer any still-useful standards or decisions into durable
guidance before removing this file.

## Goal

Reduce `handle_feature_conf` complexity without changing options-flow behavior.

The target is not a set of bespoke page implementations. The preferred shape is
a generic feature-form handler that can render schema-backed pages from explicit
schemas/selectors, with domain modules using that handler for their own
subpages where practical.

## Scope

The first implementation pass on `codex/options-flow-structure` is now treated
as a scratch branch. It was based on `main`, but the current options-flow surface
that must be preserved already exists on `fan-cover-default-automation`.

Continue Phase 8 from a clean `options-flow-structure` branch based on
`fan-cover-default-automation`. Preserve useful scratch-branch implementation
work by reapplying it selectively. Do not use the scratch branch as the final
integration branch.

Do not redesign fan/cover options-flow behavior during this Phase 8 extraction.
Fan/cover routes already present on the fan-cover branch are behavioral
constraints, not new scope. The generic primitives may support those routes, but
the phase should not change their user-facing flow or add new fan/cover behavior.

Scratch-branch work to preserve if still useful:

- generic page primitives;
- simple feature-page extraction;
- climate-control extraction only where it preserves the fan-cover baseline;
- light-groups extraction corrected to preserve submenu behavior;
- planning/research documents.

Scratch-branch work not to carry forward automatically:

- test rewrites from the main-based scratch branch;
- stubs unless still needed after applying on the fan-cover baseline;
- climate-control error behavior if the fan-cover baseline already fixed it;
- any fan/cover redesign.

## Behavior that must not change

- Root options menu topology.
- Feature section menu topology.
- Incremental page-level persistence.
- Guided-flow completion boundaries.
- Existing validation-error behavior and error keys.
- Frontend serializer compatibility for schemas, defaults, selectors, and
  dynamic validators.
- Dormant light-group settings preservation across dynamic light-group fields.
- Current fan automation schema-backed page behavior.
- Climate entity selection and preset-mapping persistence boundaries.
- Adaptive Lighting pairing/manage-mode dynamic fields.

## Current route inventory

### Generic/simple feature route candidates

These pages are registry-backed, schema-driven, and should be renderable through
one generic page builder with page-specific selector factories:

- `feature_conf_aggregates`
- `feature_conf_area_aware_media_player`
- `feature_conf_ble_trackers`
- `feature_conf_health`
- `feature_conf_presence_hold`
- `feature_conf_wasp_in_a_box`
- `feature_conf_climate_control`
- `feature_conf_cover_groups`
- `feature_conf_fan_groups`
- `feature_conf_media_player_groups`

These routes mostly need:

- feature enum
- step ID
- schema
- saved options source
- merge/replace policy
- optional selector overrides
- optional next-step/menu return

### Complex domain routes

These should live in domain modules, but should still use the generic page
builder for ordinary form rendering once they have produced the concrete
schema/selectors for a subpage.

#### Light groups

Routes:

- `feature_conf_light_groups`

Reasons this needs a domain module:

- One feature page is dynamically reduced from the full feature schema.
- Some fields are dynamically added to the schema.
- Some hidden options must be preserved while editing a subset of fields.
- Adaptive Lighting has adopt-existing and manage-mode branches.
- Selector options depend on current flow entity lists and Adaptive Lighting
  registry discovery.

Generic-builder usage target:

- Domain module computes the concrete schema/selectors for the active light
  subpage.
- Generic form handler renders and persists the resulting page.
- Domain module owns dynamic schema mutation, hidden-key preservation, and
  post-validation normalization through typed hooks.

#### Fan groups

`feature_conf_fan_groups` and its existing fan-cover branch subroutes are in
scope only as behavior to preserve. They may be adapted to use generic page
primitives if that is a mechanical extraction, but their menu topology,
role-specific pages, persistence boundaries, and validation behavior must remain
unchanged.

#### Climate control

Routes:

- `feature_conf_climate_control`
- `feature_conf_climate_control_select_presets`

Reasons this needs a domain module:

- Preset selector page depends on the selected climate entity.
- Preset selectors and validators are generated dynamically from HA state.
- Abort reasons are behaviorally significant:
  - `no_entity_selected`
  - `invalid_entity`
  - `climate_no_preset_support`
- The first climate page uses registry-backed feature configuration and then
  routes to preset selection through `feature.next_step`.

Generic-builder usage target:

- Main climate page uses generic builder as a simple feature page.
- Preset page uses generic form handling after the domain module computes dynamic
  selectors and validators.

## Explicitly deferred routes

The following routes were deferred on the main-based scratch branch. On the
fan-cover baseline, only routes already present there are in scope, and only as
behavior-preserving extraction targets:

- `feature_conf_light_groups_roles`
- `feature_conf_light_groups_brightness`
- `feature_conf_light_groups_brightness_advisory`
- `feature_conf_light_groups_brightness_adaptive`
- `feature_conf_light_groups_adaptive_lighting`
- `feature_conf_fan_groups_cooling`
- `feature_conf_fan_groups_humidity`
- `feature_conf_fan_groups_odor`
- `feature_conf_*_settings` section-menu pattern

## Generic form implementation result

The extraction keeps one generic primitive:

- `handle_feature_form(...)`

It validates a schema, persists feature config, renders saved options through
`flow._build_schema_from_vol`, supports selectors and dynamic validators,
supports simple next-step behavior, and accepts typed callback hooks for
feature-specific preparation and immediate rerender behavior.

The extraction deliberately did not add a page-definition class. The current
codebase did not need another intermediate object to get the desired
separation. Domain modules now provide ordinary schemas/selectors plus typed
hooks to the generic form handler. This avoids `typing.cast`, broad `Any`, and
type-ignore escape hatches in the options-flow extraction.

Implemented generic helpers:

- `copy_schema(schema)`
- `filter_schema_for_keys(schema, include_keys)`
- `handle_feature_form(...)`

## Proposed target module layout

```text
custom_components/magic_areas/config_flows/steps/
  feature_config.py
  feature_pages/
    __init__.py
    generic.py
    simple.py
    light_groups.py
    climate_control.py
```

Notes:

- `generic.py` owns schema copy/filter helpers and generic rendering/persistence.
- `simple.py` should map simple feature pages to selector overrides.
- Complex modules should return either a handled result or the concrete
  schema/selectors/hooks needed by the generic form handler.
- Feature-specific semantics must stay with the owning domain module.

## Implementation sequence

1. Add focused tests only where current behavior lacks coverage. Completed:
   existing config-flow and snapshot coverage was sufficient for this slice.
   - Do not add tests just to mirror implementation structure.
   - Existing config-flow E2E and translation tests already cover most visible
     behavior.

2. Extract generic page primitives. Completed.
   - Move schema copy/filter helpers.
   - Move generic form validation/rendering/persistence into
     `feature_pages/generic.py`.
   - Keep `handle_feature_conf` behavior unchanged.

3. Extract simple feature pages. Completed.
   - Move non-light selector construction into `feature_pages/simple.py`.
   - Replace inline generic selector construction with feature-page helpers.
   - Validate with config-flow focused tests.

4. Extract climate preset handling. Completed.
   - Move preset-selection handling into `feature_pages/climate_control.py`.
   - Preserve abort reasons and feature `next_step` behavior.

5. Extract light-group page handling. Completed.
   - Move light-group schema filtering, selector overrides, dynamic Adaptive
     Lighting fields, hidden-key preservation, and normalization into
     `feature_pages/light_groups.py`.
   - Use generic rendering after the domain module builds schema/selectors and
     supplies persistence-preparation hooks.

6. Reduce `handle_feature_conf`. Completed.
   - Final shape should identify the current step, delegate route handling, and
     call the generic page handler.
   - It should not contain domain-specific schema construction.

7. Validate and update roadmap state. Completed.
   - Run focused config-flow tests during extraction.
   - Run `./scripts/validate.sh` before commit or completion claim.
   - Record final completion/gaps in the active roadmap location.

## Initial validation targets

Focused tests to run repeatedly while extracting:

```bash
uv run --extra test pytest tests/config_flow -q
uv run --extra test pytest tests/snapshots/test_snapshots_config_flow.py -q
```

Current focused validation:

- `uv run ruff check custom_components/magic_areas/config_flows/steps`: passed.
- `uv run mypy custom_components/magic_areas/config_flows/steps/feature_config.py custom_components/magic_areas/config_flows/steps/feature_pages/generic.py custom_components/magic_areas/config_flows/steps/feature_pages/climate_control.py custom_components/magic_areas/config_flows/steps/feature_pages/light_groups.py custom_components/magic_areas/config_flows/steps/feature_pages/fan_groups.py`: passed.
- `uv run --extra test pytest tests/config_flow/test_feature_config.py tests/config_flow/test_feature_config_climate.py tests/config_flow/test_options_flow_routing.py -q`:
  19 passed.

Final validation:

- `./scripts/validate.sh`: passed on 2026-06-27.
  - Ruff: passed.
  - Mypy: passed, 362 source files checked.
  - Pytest: 1452 passed, 26 snapshots passed.

## Exit criteria

- `handle_feature_conf` no longer owns domain-specific page construction.
- Simple feature pages use one generic builder path.
- Complex feature modules use generic builders for ordinary form rendering.
- Existing options-flow behavior is unchanged.
- Config-flow tests and full repository validation pass.
- Master roadmap accurately records completion and any remaining follow-up.
