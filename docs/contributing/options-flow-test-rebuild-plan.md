# Options-flow test rebuild plan

## Goal

Record the research comparing `main` and `fan-cover-default-automation`
options-flow tests, and identify which parts are structural versus fan/cover
specific.

Decision update: do not rebuild these tests on the main-based
`codex/options-flow-structure` scratch branch. Continue Phase 8 from a clean
`options-flow-structure` branch based on `fan-cover-default-automation`, where
the current options-flow behavior and tests already exist.

This document remains useful as a scope filter while reapplying scratch-branch
implementation work: keep structural options-flow expectations, preserve
fan/cover behavior, and avoid redesigning fan/cover as part of Phase 8.

## Source comparison

Compared:

- `main`
- `fan-cover-default-automation`

The fan-cover branch contains the current options-flow test surface. It includes
both:

- general options-flow structure/navigation coverage that Phase 8 must preserve;
- fan/cover feature coverage that is not new Phase 8 scope, but is a behavioral
  constraint when Phase 8 is based on the fan-cover branch.

The earlier idea of custom-rebuilding a filtered version of these tests on top
of `main` is no longer the preferred path. It would manually reconstruct a
partial version of behavior that already exists on the fan-cover branch and
would keep creating branch-base/test-scope conflicts.

The largest relevant changes are in:

- `tests/config_flow/test_config_flow_features_e2e.py`
- `tests/config_flow/test_config_flow_options_e2e.py`
- `tests/config_flow/test_config_flow_options_runtime.py`
- `tests/config_flow/test_feature_config.py`
- `tests/config_flow/test_options_flow_incremental_persistence.py`
- `tests/config_flow/test_options_flow_integration.py`
- `tests/config_flow/test_options_flow_routing.py`
- `tests/config_flow/test_options_flow_translations.py`
- `tests/config_flow/options_flow_testkit.py`

## Keep from fan-cover: structural behavior

Bring over tests that enforce the intended options-flow structure without
depending on fan/cover production objects.

### Root/options-flow navigation

Keep coverage that enforces:

- root menu task-oriented ordering;
- no final root-level save/finish operation where the newer options-flow model
  persists page-by-page;
- feature selection persists immediately and returns a refreshed menu;
- simple single-page features open forms directly;
- intentional multi-page features open a submenu first;
- page submit returns either to root menu or the relevant feature submenu based
  on page type.

Relevant fan-cover examples to adapt:

- `test_root_single_page_sections_open_forms_directly`
- `test_root_single_page_submit_persists_immediately_and_returns_to_root`
- `test_root_menu_has_no_final_save_operation`
- `test_feature_selection_persists_immediately_and_refreshes_menu`
- `test_single_page_feature_submit_persists_immediately`
- `test_options_flow_show_menu_uses_task_oriented_order`
- `test_options_flow_select_features_returns_refreshed_menu`

### Light-groups submenu structure

Keep coverage that enforces light groups remains a complex submenu, not a
monolithic form:

- `feature_conf_light_groups` returns a menu;
- submenu contains:
  - `feature_conf_light_groups_roles`
  - `feature_conf_light_groups_brightness`
  - `feature_conf_light_groups_adaptive_lighting`
  - `show_menu`
- leaf forms return to the light-groups menu after save;
- role, brightness, and Adaptive Lighting sections do not leak unrelated fields;
- hidden/dormant values are preserved when switching modes;
- dynamic Adaptive Lighting pairing fields do not mutate shared schemas.

Relevant fan-cover examples to adapt:

- `test_options_flow_light_group_leaf_submits_return_to_light_group_menu`
- `test_options_flow_light_groups_root_shows_substep_menu`
- `test_options_flow_light_groups_roles_preserve_hidden_behavior_modes`
- `test_options_flow_light_groups_brightness_preserves_hidden_roles`
- `test_options_flow_light_groups_mode_fields_do_not_leak_after_reopen`
- `test_options_flow_light_groups_adaptive_lighting_pairings_do_not_leak`
- `test_options_flow_dynamic_pairings_do_not_mutate_light_group_schema`
- `test_light_group_roles_submit_persists_immediately`
- `test_light_group_classic_brightness_persists_immediately`
- brightness-dependent mode tests, scoped to existing light-group modes only
- Adaptive Lighting manage/adopt tests, scoped to existing light-group behavior

### Climate-control structural coverage

Keep climate tests only where they are structural and compatible with this
branch:

- climate entry can remain a guided/multi-step flow;
- entity selection advances to preset selection;
- incomplete climate flow does not persist partial config;
- preset mapping submit persists only after the guided flow is complete;
- changing the climate entity forces preset remapping before persistence.

Relevant fan-cover examples to adapt:

- `test_climate_entity_selection_advances_without_persisting`
- `test_abandoning_incomplete_climate_guided_flow_does_not_persist`
- `test_climate_preset_mapping_submit_persists_feature`
- `test_changing_climate_entity_forces_preset_remapping_before_persistence`

Preserve the current branch’s intended behavior for recoverable climate errors if
that behavior remains part of this branch’s production code.

### Simple feature forms

Keep tests for existing simple features only:

- aggregates
- area-aware media player
- BLE tracker
- health
- presence hold
- wasp in a box

Keep tests that verify:

- direct form rendering;
- selector shape;
- reopen suggested values;
- immediate persistence on submit;
- invalid input does not persist partial data.

Do not add new simple-feature coverage merely because it exists on fan-cover if
the feature is fan/cover-specific.

### Routing and translations

Keep general routing/translation tests:

- dynamic `async_step_feature_conf_*` routes through generic dispatch;
- root menu labels are task-oriented;
- light-group submenu labels explain user-facing tasks;
- single-page feature forms explain that submit saves immediately;
- translation tests do not reference removed or fan/cover-only contracts.

Relevant fan-cover examples to adapt:

- `test_options_flow_dynamic_step_attribute_routes_feature_conf`
- `test_options_flow_root_menu_uses_task_oriented_labels`
- `test_root_menu_does_not_expose_final_save_action`
- `test_light_group_submenu_uses_task_oriented_labels`
- `test_light_group_substeps_explain_their_scope`
- `test_single_page_forms_explain_submit_saves_immediately`

## Exclude from fan-cover: fan/cover-specific behavior

Do not port tests, imports, helper branches, or expectations that require these
fan/cover-specific objects:

- `MagicAreasFeatures.FAN_GROUPS`
- `MagicAreasFeatures.COVER_GROUPS`
- any `feature_conf_fan_groups*` step
- any `feature_conf_cover_groups*` step
- `CONF_FAN_*`
- `CONF_FAN_GROUPS_*`
- `CONF_FAN_CONTROLLER_*`
- `CONF_COVER_*`
- `CONF_COVER_GROUPS_*`
- `FanControllerRole`
- `FanDetectionMode`
- `FanClearBehavior`
- `FanSensorUnavailableBehavior`
- `CoverPresetAction`

Specific fan-cover tests to exclude or split:

- fan-group menu and controller tests;
- cover-group settings/preset tests;
- root-menu expectations that include fan or cover entries;
- helper logic that auto-enters `feature_conf_fan_groups` or
  `feature_conf_cover_groups`;
- translation tests for fan/cover labels.

If a test combines structural assertions with fan/cover assertions, split it and
keep only the structural/light-groups/climate/simple-feature portions.

## File-by-file rebuild approach

### `tests/config_flow/options_flow_testkit.py`

Review fan-cover helper additions. Keep only generic helpers that make structural
tests clearer. Do not add helper behavior for fan/cover submenus.

### `tests/config_flow/test_config_flow_features_e2e.py`

Rebuild this file manually:

1. Start from `main`.
2. Add structural helpers from fan-cover:
   - selector extraction helpers;
   - suggested-value helper;
   - light-groups submenu entry helper.
3. Port non-fan/cover structural tests.
4. Exclude all fan/cover imports and tests.
5. Ensure no fan/cover constants remain in imports.

This file is the highest-risk file because fan-cover added many unrelated domain
tests here.

### `tests/config_flow/test_config_flow_options_e2e.py`

Port only the structural navigation changes:

- entering `feature_conf_light_groups` should produce the light-groups submenu;
- role edits happen through `feature_conf_light_groups_roles`;
- returning from the light-groups submenu to root uses `show_menu`;
- final expectations should not include unrelated fan/cover defaults.

### `tests/config_flow/test_config_flow_options_runtime.py`

Keep runtime assertions that are independent of fan/cover:

- generic feature routing reaches the light-groups submenu;
- root initialization/runtime behavior remains compatible with current branch.

Do not port runtime tests that require fan/cover runtime data.

### `tests/config_flow/test_feature_config.py`

Port light-groups submenu unit expectations:

- top-level light-groups entry shows menu;
- `feature_conf_light_groups_roles` renders a form;
- leaf submit returns through the light-groups menu path;
- Adaptive Lighting hidden manage settings are preserved.

Preserve current branch climate tests if they correspond to current production
behavior.

### `tests/config_flow/test_options_flow_incremental_persistence.py`

This file is useful but must be filtered heavily.

Keep:

- root sections persist immediately;
- single-page features persist immediately;
- climate guided flow persistence gates;
- light-groups roles/brightness/adaptive-lighting persistence gates;
- dormant setting preservation for light groups.

Exclude:

- fan group persistence;
- cover group persistence;
- any fan/cover helper paths or constants.

### `tests/config_flow/test_options_flow_integration.py`

Keep:

- enabled-feature map canonicalization;
- feature selection returns refreshed menu;
- root menu ordering, but remove fan/cover expectations;
- no root-level finish/save if that is the current intended branch behavior.

Exclude fan/cover menu entries from expected ordering.

### `tests/config_flow/test_options_flow_routing.py`

Keep:

- dynamic feature-step attribute routing through `async_step`.

No fan/cover-specific routing cases.

### `tests/config_flow/test_options_flow_translations.py`

Keep:

- generic root-menu translation expectations;
- light-group submenu translation expectations;
- single-page submit/save copy expectations.

Exclude:

- fan/cover label assertions;
- fan/cover submenu assertions.

## Rebuild rules

- Do not wholesale copy test files from `fan-cover-default-automation`.
- Do not make tests pass by weakening the user-facing structure assertions.
- Do not use fan/cover imports or constants on this branch.
- The rebuilt tests should describe existing production behavior plus the
  intended options-flow structure refactor.
- If a structural test fails because production code is not yet refactored, keep
  the test as a guide only if we are actively implementing that behavior in this
  branch.
- If a test fails because it expects fan/cover functionality, remove or split the
  fan/cover portion.

## Validation sequence after rebuild

1. Run targeted collection first:

   ```bash
   uv run --extra test pytest tests/config_flow -q --collect-only
   ```

2. Run config-flow tests:

   ```bash
   uv run --extra test pytest tests/config_flow -q
   ```

3. Run formatting/lint/type checks relevant to changed tests and config-flow
   production modules:

   ```bash
   uv run --extra dev --extra test ruff check custom_components/magic_areas/config_flows tests/config_flow
   uv run --extra dev --extra test ruff format --check custom_components/magic_areas/config_flows tests/config_flow
   uv run --extra dev --extra test mypy custom_components/magic_areas/config_flows
   ```

## Exit criteria

- No fan/cover-only imports remain in rebuilt tests.
- `feature_conf_light_groups` is asserted as a submenu, not a monolithic form.
- Simple feature entries are asserted as direct forms.
- Climate guided-flow persistence is covered without fan/cover dependencies.
- Light-groups mode transitions preserve dormant settings.
- Config-flow tests collect on this branch.
- Config-flow tests pass on this branch.
