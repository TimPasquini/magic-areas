# Options Flow Cleanup Repair Plan

Status: repair plan. This is a focused cleanup track for the Magic Areas options
flow. It does not change runtime behavior by itself.

## Problem Statement

The options flow is functionally working, but several forms have grown into flat,
sprawling schemas. Light groups are the clearest example: one feature step now
contains role membership, brightness behavior, adaptive switching safeguards, and
Adaptive Lighting coordination. The result is harder to understand, easier to
break with dynamic schema changes, and harder to validate manually in the HA UI.

Home Assistant provides enough native flow primitives to improve this without
building a custom frontend: menus, multi-step flows, selectors, translations,
`data_description`, and single-level collapsible sections.

This repair also needs a user-exposed surface census. The options flow is only
one half of the user experience: every feature that creates controls, helpers,
labels, or diagnostics needs an explicit contract for what appears in Home
Assistant and where it appears. A feature can later delete or replace one of
those surfaces, but the current branch should make the expected exposed surface
set intentional and test-enforced.

## Goals

- Make complex option surfaces easier to understand in the HA frontend.
- Keep config-flow behavior HA-native and serializer-safe.
- Reduce dynamic-schema risk from mutating shared schema objects.
- Use selector types that match the actual user decision being captured.
- Preserve existing saved-option round trips and hidden-field persistence.
- Keep runtime behavior unchanged unless a separate runtime bug is identified.

## Non-Goals

- No custom frontend panel.
- No broad redesign of runtime policy.
- No removal of existing options during this repair.
- No migration burden for configurations that have not shipped broadly yet.

## Home Assistant Guidance To Apply

- Use multi-step flows or menus when a single form becomes too broad.
- Use selectors instead of raw text fields or frontend-unfriendly validators.
- Use filtered entity selectors where the valid domain/device class is known.
- Use `data_description` for fields whose behavior is not obvious.
- Use `suggested_value` for saved options that should be prefilled but still clearable.
- Use sections for related field groups when a step contains multiple concepts.
- Dynamically show or hide options by rebuilding the schema before rendering the next form;
  do not rely on the frontend to conditionally hide fields live.
- Treat radio/list-style selectors as input controls, not live section controllers. Home
  Assistant config flows can render select choices as list/radio-like controls and can
  render collapsible sections, but the supported dynamic pattern is submit-and-rerender:
  select the mode, submit, then render the schema/section for that mode.
- Use translated menu option descriptions so the root options menu explains where each
  path leads before the user enters it.
- Use translated label/value select options so user-facing labels describe behavior while
  internal stored values remain stable.

## Target Improvements

## Navigation And Persistence Contract

The previous menu-first checkpoint proved that adding a one-item intermediary menu does
not solve the real user problem: Home Assistant form pages do not expose a native
step-local Back button, and the frontend close/X abandons the active flow rather than
routing to the parent menu. The repair direction is therefore:

- Use submenus only when they organize meaningful multi-page domains.
- Do not add intermediary menus whose only real child is a single Settings page plus
  Back.
- Treat `Submit` on a complete page or complete guided subflow as the save boundary.
- Persist with `async_update_entry(..., options=dict(self.area_options))` after a
  successful completion boundary.
- Do not mutate `config_entry.options` directly.
- Treat close/X as "discard only the current unsubmitted page" by ensuring already
  completed pages have been persisted.
- Keep a root Done/Close path if useful, but do not depend on a final Save & Exit for
  previously submitted pages.

Submenu decisions should be based on domain complexity and near-term planned expansion,
not only the current number of implemented child pages.

Keep submenus for:

- Light groups: role membership, brightness behavior, Adaptive Lighting coordination, and
  mode-dependent guided pages.
- Climate automation: climate entity selection and preset mapping.
- Fan automation: even if currently represented by one settings form, this domain is
  expected to split into multiple fan-control use cases:
  - bathroom humidity management
  - bathroom odor/manual-duration management
  - temperature-based fan triggers
  - other sensor-triggered fan uses such as particulate/air-filter control

Remove one-child intermediary menus for:

- Area behavior.
- Presence tracking.
- Area states.
- Custom control groups.
- Health sensors.
- Aggregate sensors.
- Presence hold.
- BLE tracker monitoring.
- Wasp in a Box.
- Area-aware media player.

Completion-boundary rules:

- Single-page root settings persist immediately on successful submit.
- Single-page feature settings persist immediately on successful submit.
- Climate entity selection advances to preset mapping when presets are not complete or
  when the entity changes; preset mapping submit persists the climate feature.
- Light-group role edits can persist on submit because defaults make the role config
  complete enough.
- Light-group brightness mode changes persist immediately only when the selected mode has
  no required dependent page, such as Classic.
- Selecting Advisory or Adaptive brightness mode deactivates fields from other modes for
  UI and runtime purposes, advances to that mode's settings page, and persists only after
  the dependent settings page submits.
- Mode changes must not destructively delete dormant mode-specific settings. A user who
  switches from Adaptive to Advisory and later switches back to Adaptive should see the
  previous Adaptive settings restored as suggested/default values, unless those settings
  reference invalid entities or the user explicitly clears them.
- Runtime policy must only consume settings relevant to the active brightness mode, even
  though dormant settings for inactive modes remain persisted for future restoration.
- Adaptive Lighting `ignore` can persist immediately.
- Adaptive Lighting `adopt_existing` and `manage` should persist only after the required
  pairing or managed-role decisions are submitted.

## Test-First Targets

Write these tests before implementing the next runtime/options-flow adjustment. The
priority list below may be used to slice the work, but this full target list is the
required scope and should not be pruned just because an early slice covers the backbone.

Full target list:

- Complete-page submit persists immediately via `async_update_entry`.
- Validation failure does not persist.
- Closing/X after a submitted complete page does not lose that submitted page.
- Closing/X during an incomplete guided subflow does not persist partial dependent config.
- Single-child intermediary menus are removed.
- Intentional multi-page submenus remain for Light groups, Climate automation, and Fan
  automation.
- Area behavior submit persists immediately and returns to root.
- Presence tracking submit persists immediately and returns to root.
- Area states submit persists immediately and returns to root.
- Custom control groups submit persists immediately and returns to root.
- Single-page feature submit persists immediately and returns to root.
- Fan automation keeps its submenu despite current single settings page.
- Climate entity selection advances to preset mapping when not complete.
- Climate entity selection does not persist until preset mapping succeeds.
- Climate preset mapping submit persists the climate feature.
- Changing the climate entity forces preset remapping before persistence.
- Light roles submit persists immediately because defaults make role config complete.
- Brightness mode `Classic` persists immediately and returns to Light groups menu.
- Brightness mode `Advisory` advances to advisory settings and does not persist
  mode/config until advisory settings submit.
- Brightness mode `Adaptive` advances to adaptive settings and does not persist
  mode/config until adaptive settings submit.
- Advisory settings submit persists advisory mode/config.
- Adaptive settings submit persists adaptive mode/config.
- Switching `Adaptive -> Advisory` deactivates adaptive runtime fields but does not delete
  adaptive settings.
- Switching `Advisory -> Adaptive` restores prior adaptive settings in the UI.
- Switching `Adaptive -> Classic` hides adaptive settings but preserves them.
- Inactive/dormant mode settings do not affect runtime behavior while another brightness
  mode is active.
- Adaptive Lighting `ignore` persists immediately.
- Adaptive Lighting `adopt_existing` does not persist until pairings are submitted.
- Adaptive Lighting `manage` does not persist until managed roles/all-lights choices are
  submitted.
- Switching Adaptive Lighting modes preserves dormant mode-specific settings where useful.
- Root/menu copy no longer says changes are staged until final `Save & Exit`.
- Submit/save copy explains completed pages are saved immediately.
- `finish`/Done path does not perform the only save operation anymore.
- Failed form validation keeps the user on the same form with errors.
- Reopen after submit shows persisted values as suggested/default values.
- Dynamic mode switching does not leave hidden transient fields visible.
- Helper-only features still do not create dead configuration menu paths.
- Enabling configurable features still immediately exposes the expected root menu paths.

Recommended test slices:

1. Incremental persistence backbone:
   - complete-page submit persists immediately
   - validation failure does not persist
   - submitted pages survive later close/X
   - incomplete guided subflows do not persist partial dependent config
2. Menu topology:
   - single-child intermediary menus are removed
   - Light groups, Climate automation, and Fan automation remain intentional submenus
   - helper-only features still do not create dead menu paths
   - configurable features still appear immediately after enabling
3. Root and single-page feature persistence:
   - Area behavior, Presence tracking, Area states, Custom control groups
   - Health, Aggregates, Presence hold, BLE trackers, Wasp in a Box, Area-aware media
     player
   - reopen-cycle suggested/default values after submit
4. Climate guided completion:
   - entity selection advances to presets when incomplete
   - entity-only submit does not persist
   - preset mapping submit persists
   - entity changes force preset remapping before persistence
5. Light-group brightness guided completion:
   - roles submit persists
   - Classic persists immediately
   - Advisory/Adaptive route to dependent pages and persist only after settings submit
   - failed validation remains on the same form
6. Dormant mode preservation and runtime isolation:
   - Adaptive/Advisory settings survive switching away
   - switching back restores prior settings in the UI
   - dormant inactive-mode settings do not affect runtime policy
7. Adaptive Lighting completion boundaries:
   - ignore persists immediately
   - adopt_existing persists only after pairings
   - manage persists only after managed-role/all-lights choices
   - useful dormant mode-specific Adaptive Lighting settings are preserved across mode
     switches
8. Copy/translation contracts:
   - root/menu copy reflects incremental save behavior
   - submit/save copy explains completed pages save immediately
   - Done/finish copy does not imply it is the only persistence path

## Implemented Checkpoint

- Light groups now open as a submenu with dedicated substeps for roles, brightness
  behavior, and Adaptive Lighting coordination.
- Light-group mode-specific rendering is test-enforced for `classic`/internal
  `inhibit`, `advisory`, `adaptive`, Adaptive Lighting `ignore`, `adopt_existing`,
  and `manage`.
- Hidden durable light-group values are preserved across unrelated substep edits, while
  transient Adaptive Lighting pairing fields are normalized instead of leaking into saved
  options.
- Light-group selector contracts are test-enforced for dropdown mode selectors,
  translated selector labels, illuminance-only lux entity selectors, and realistic lux
  numeric ranges.
- Fan automation now uses constrained selectors for required area state, tracked
  aggregate sensor device class, and numeric setpoint instead of relying on raw schema
  primitives.
- Aggregate illuminance threshold now uses the same realistic lux selector range as
  adaptive brightness fields.
- Custom control groups use a structured object selector and now have step-level
  translation guidance so the advanced editor does not render as a blank or context-free
  form.
- The root options menu now orders enabled feature configuration pages by user task rather
  than alphabetically by implementation key.
- The feature-selection form now uses the same user-task ordering so new features are
  selected in the same conceptual order they appear in the options menu.
- Runtime-data dependency failure is represented as a clean translated abort when an
  entry is not loaded.
- User-exposed surface contracts now cover native group helpers/control switches, light
  role labels, aggregate helpers, threshold helpers, health helpers, and first-class
  Magic Areas presence hold/BLE tracker/wasp-in-a-box entities, the climate control
  switch, and the global area-aware media player routing surface. These tests assert
  visibility, area/device attachment, expected helper membership or source attributes,
  and exclusion from Magic Areas self-enumeration where applicable.
- Feature-selection translation guidance now distinguishes enabling a feature from
  whether that feature adds a follow-up configuration page, so helper-only/default
  behavior does not look like a missing menu item.
- Feature-selection E2E coverage now verifies newly enabled configurable features appear
  in the returned root menu immediately, while enabled helper-only/default features do
  not create dead configuration menu paths.
- Non-light configurable feature entry points now open as menu-first sections with
  explicit settings pages and a Back path. E2E coverage verifies each section menu and
  settings form route.
- Fan and aggregate settings now have reopen-cycle coverage proving saved values are
  offered back to the user as suggested values.
- Area-aware media-player notification targets now use all available media-player
  entities in the selector, instead of depending on the current area entity catalog.
- Presence hold, Wasp in a Box, and BLE tracker configuration now use more specific
  selector surfaces: bounded number selectors for timeout/delay fields and sensor-only
  entity selection for BLE tracker sensors.
- Climate control settings now have reopen-cycle coverage for the selected climate entity
  and the preset map. This protects the two-step climate flow from losing or hiding saved
  preset choices.
- Area-aware media-player notification states now have selector and reopen-cycle coverage,
  including translated area-state choices and persisted notification target/state values.
- Health and Wasp in a Box settings now have reopen-cycle coverage so selected device
  classes and timing values remain visible when revisiting the options flow.
- Presence hold now has reopen-cycle coverage for the saved timeout value.
- Cover groups and media-player groups now have E2E coverage proving they are
  helper-only feature toggles: enabling them persists the feature flag without adding
  dead feature-configuration menu paths.
- Custom control groups now treat an empty submit as intentional empty configuration
  and do not silently create or reseed starter-template groups.
- Custom control groups now have selector coverage for translated multi-select trigger
  states inside the guided object editor.
- Area behavior now has selector and reopen-cycle coverage for area type,
  include/exclude entity filters, reload-on-registry-change, and diagnostic/config entity
  filtering.
- Initial setup now uses the same HA select-selector surface for choosing the Home
  Assistant area, including meta-area options, instead of relying on a raw `vol.In`
  dropdown contract.
- Initial setup no longer marks the area-selection form as `last_step`; selecting an
  area creates the entry directly and should not present a skip/finish-style affordance.
- The area behavior exclude selector is confirmed as area-catalog scoped. It should not
  be treated as a global registry selector; tests enforce that distinction so future
  changes do not accidentally broaden the candidate set.
- Presence tracking now has selector and reopen-cycle coverage for platform selection,
  binary-sensor device classes, keep-only entity filtering, and clear-timeout handling.
- Secondary area states now have selector and reopen-cycle coverage for dark/sleep/accent
  entity fields and sleep/extended timing fields.
- Secondary-state calculation mode is now explicitly covered as a meta-area-only
  translated selector. Regular rooms do not expose that meta aggregation field.
- Root-menu translation ordering now matches runtime ordering: area behavior, presence
  tracking, then area states.
- Enabled feature maps are normalized to string feature IDs even when an enum key enters
  through tests or older setup paths. This keeps saved option data aligned with Home
  Assistant's serialized config shape.
- Light-group brightness mode reopen-cycle coverage now verifies that saved `adaptive`
  mode fields appear when reopening the substep, and that switching to `advisory`
  removes adaptive-only fields on the next reopen.
- Feature section leaf forms now return to their local section menu after submit. Tests
  cover Light groups roles, brightness behavior, Adaptive Lighting coordination, health,
  fan groups, aggregates, presence hold, and Wasp in a Box.
- Feature section Back paths now return to the root options menu. Tests cover Light
  groups and non-light configurable feature sections.
- Climate control preserves its required two-step path: entity selection advances to
  preset mapping, and preset mapping submit returns to the Climate automation section
  menu.
- Root-level option categories now use section menus. Tests cover Settings + Back for
  Area behavior, Presence tracking, Area states, and Custom control groups.
- Root-level settings forms now return to their parent section menu after submit. Tests
  also verify staged edits across several root sections remain staged until `Save & Exit`.
- The current automated checkpoint is full Ruff, full mypy, `tests/config_flow`, the
  user-exposed surface integration contract, and full pytest passing.

### 1) Light Group Form Structure

Split the flat light-group form into clearer UI groupings. The current form exposes too
many internal concepts at once; users should move through room-lighting decisions in the
same order they reason about the room.

Implemented direction: substeps for major decision branches, with sections only inside a
substep when several always-relevant fields belong together. Sections alone are probably
not enough because Home Assistant config flows do not provide live conditional frontend
field hiding; mode changes are expressed by submitting and rendering the next schema.

The desired light-group experience is:

- Common controls remain visible before mode-specific decisions:
  - role membership or links to role membership
  - role state triggers
  - role act-on triggers
  - current brightness behavior mode
  - current Adaptive Lighting coordination mode
- `Classic`, `Advisory`, and `Adaptive` are presented as user-facing behavior choices.
  Use a translated select/list presentation where it reads well in the frontend.
- Only the selected behavior's fields are rendered after submit/re-render. Do not attempt
  to make radio choices live-open sections in the same frontend form.
- Adaptive Lighting coordination remains visually separate from brightness switching
  behavior because it controls another integration's adaptation switches, not Magic
  Areas on/off policy itself.

Current substeps:

- Light roles
  - overhead/task/accent/sleep entity membership
  - role state triggers
  - role act-on triggers
- Brightness behavior
  - `classic`, `advisory`, `adaptive`
  - inside bright binary
  - outside bright binary
- Adaptive switching guards
  - minimum on-time
  - bright dwell
  - attribution hold
  - ambient-rise requirement
  - ambient-rise window/delta
  - outside context and outside/inside contrast
- Adaptive Lighting coordination
  - ignore/adopt existing/manage
  - role pairings
  - managed roles
  - all-lights managed group gate

Acceptance criteria:

- A normal user can configure role membership without seeing adaptive guard tuning.
- A user selecting `advisory` or `adaptive` sees only the extra fields that apply to that
  behavior.
- Adaptive Lighting setup is visually separate from Magic Areas on/off switching policy.

### 2) Mode-Specific Rendering

Keep mode-specific field visibility explicit.

- `classic` should show only baseline light-role controls and mode selectors.
- `advisory` should add inside/outside bright binary fields.
- `adaptive` should add advisory fields plus adaptive guard and outside-context fields.
- Adaptive Lighting `ignore` should show no pair/manage fields.
- Adaptive Lighting `adopt_existing` should show role-to-switch-set pairing fields.
- Adaptive Lighting `manage` should show managed-role fields and the separate all-lights gate.

The current internal/default mode name `inhibit` is user-hostile. Rename the user-facing
mode to `classic` or equivalent. Prefer preserving a compatibility alias internally only
if useful during transition; no released user migration is required for this branch.

Do not persist stale transient pairing keys. Do preserve durable hidden settings that are
not currently visible because another mode is being edited.

### 3) Selector Fit

Review selector choices field by field.

Known cleanup targets:

- Raise explicit max values for lux selectors. Outdoor lux can exceed the current default
  number-selector max of `9999`.
- Use illuminance-only entity candidates for lux fields.
- Keep bright-state binary selectors flexible enough for threshold helpers or other binary
  abstractions, but make labels/descriptions clear.
- Use label/value select options for behavior modes where practical. The UI should show
  behavior names and consequences, not internal tokens.
- Force dropdown mode for mode selectors where a compact consistent control is preferable
  to Home Assistant switching between radio/list/dropdown presentation based on option count.
- Consider whether any future role/group selection should use label or target selectors;
  do not switch existing managed membership fields unless the output shape improves the
  implementation.
- Treat raw `ObjectSelector` for custom control groups as a temporary escape hatch.
  Structured `ObjectSelector` with `fields`, `label_field`, `description_field`, and
  `multiple` may be a useful interim improvement before full add/edit/delete subflows.

Selector audit output should be concrete. For each user-exposed configuration field,
record:

- Feature and field name.
- Current selector/input primitive.
- Proposed selector/input primitive.
- Where it appears in the flow.
- Whether it is common, advanced, mode-specific, or integration-specific.
- Whether hidden values are durable and must be preserved when not visible.
- Whether submitted values are transient and should be discarded when the mode changes.

This audit should include at least:

- Area behavior and type.
- Presence tracking devices/classes/timeouts.
- Secondary states.
- Feature selection.
- Light roles, role states, role act-on triggers, brightness behavior, adaptive guards,
  ambient-rise controls, and Adaptive Lighting coordination.
- Fan group trigger inputs.
- Climate preset controls.
- Media notification/area-aware controls.
- Cover group controls.
- Aggregates, thresholds, health surfaces, and any exposed helper/signal settings.
- Custom control groups.

### 4) User-Exposed Surface Census

Build and maintain a feature-by-feature census of user-exposed Home Assistant surfaces.
This is separate from the options-flow field audit: it describes what the user sees after
configuration is saved and the integration reconciles runtime/native surfaces.

For each feature, record:

- Expected control switches.
- Expected native helper entities.
- Expected labels.
- Expected sensors/binary sensors.
- Expected Adaptive Lighting switch/config links, if any.
- Expected device and area attachment.
- Expected hidden/visible status.
- Whether the surface should be excluded from Magic Areas self-enumeration.
- Whether the surface should be cleaned up when the feature/config/group is removed.

Initial census targets:

- Light groups:
  - Native helper light groups for all-lights and configured roles.
  - Global role labels such as `ma:overhead`, `ma:task`, `ma:sleep`, `ma:accent` only
    when applicable.
  - Light control switch.
  - Ambient-rise helper/signal surfaces when adaptive mode requires them.
  - Managed/adopted Adaptive Lighting switch associations.
- Fan groups:
  - Native fan group helper.
  - Fan control switch.
  - Trigger sensor/setpoint options in the options flow.
- Cover groups:
  - Native cover group helpers by device class/role.
  - Cover control switch.
- Media player groups:
  - Native media/player helper surfaces where implemented.
  - Media player control switch.
  - Area-aware media player surface, if enabled.
- Climate control:
  - Climate control switch.
  - Preset mapping options.
- Aggregates and thresholds:
  - Native aggregate/threshold helpers.
  - Correct device class/unit metadata.
  - Exclusion from self-enumeration.
- Health:
  - Health helper/sensor surfaces.
- Presence hold and BLE:
  - First-class Magic Areas entities that are intentionally not handed off to native
    helpers.
- Custom control groups:
  - Scoped `ma:control:*` labels.
  - Cleanup of labels/memberships when the custom group is deleted.

### 5) Dynamic Schema Safety

Dynamic fields must be added to a copied schema, not by mutating a shared feature schema
from the registry.

Acceptance criteria:

- Opening one mode does not leak fields into another mode or another flow instance.
- Reopening the options flow after changing modes shows only expected fields.
- Tests cover repeated open/edit cycles for light groups.

### 6) Feature Selection Menu Refresh

Selecting features should not require saving and exiting the entire options flow before
newly selected configurable features become reachable from the root menu.

Current code intends to update `flow.area_options` and immediately return the root menu.
The repair needs to verify actual HA frontend behavior and clarify edge cases:

- Features with config-flow steps should appear immediately after selection.
- Features without config-flow steps should not appear as broken/empty menu entries.
- The feature-selection screen should distinguish "enabled feature" from "configurable
  feature" when a feature has runtime behavior but no options step.
- Tests should assert the returned menu options after feature selection, not only the
  stored feature map.

If HA frontend menu refresh behavior prevents this from working reliably in one flow,
the feature-selection step should route directly to a "configure newly enabled features"
subflow or show an explicit message telling the user what changed.

### 7) Runtime-Data Dependency

Options flow initialization currently depends on loaded coordinator runtime data for area
config and entity lists. That is useful, but the UI should fail cleanly if runtime data is
not available.

Expected behavior:

- If runtime data is unavailable but the config entry exists, the flow should either use a
  safe fallback for registry-derived entity lists or abort with a clear translated reason.
- It should not crash with an attribute error or produce a broken frontend form.

### 8) Custom Control Groups

The current object editor is functional but not user-friendly.

Future cleanup direction:

- First evaluate structured object-selector fields for a lower-cost improvement:
  - group ID
  - display name
  - members
  - policy/role
  - optional metadata
- Add guided add/edit/delete flows if structured object selectors still feel too raw in
  the HA frontend.
- Keep raw object editing only if it remains useful as an advanced escape hatch.
- Ensure deletion semantics remain explicit: deleting a custom group removes its managed
  labels/helper surfaces during reconciliation.

### 9) Root Menu UX

The root options menu should read like user tasks, not implementation modules.

Target menu direction:

- Area behavior
- Presence tracking
- Secondary states
- Light roles and automation
- Custom control groups
- Feature selection
- Finish

Each menu entry should have a translated description. The user should understand whether a
menu path controls room identity, sensor selection, behavior states, automation roles, or
advanced/custom grouping before selecting it.

## Test Plan

Automated tests should cover:

- A consolidated user-exposed surface contract:
  - required surfaces exist for each enabled feature
  - expected surfaces are attached to the correct area and Magic Areas device
  - helper/control surfaces are visible unless intentionally hidden
  - helper/control surfaces are excluded from Magic Areas self-enumeration where needed
  - feature/group deletion removes the corresponding managed surfaces
- Light-group field visibility for `classic`, `advisory`, and `adaptive`.
- Adaptive Lighting field visibility for `ignore`, `adopt_existing`, and `manage`.
- Hidden durable settings are preserved across unrelated edits.
- Transient pairing fields are not persisted.
- Existing switch-set mappings are preserved when still valid but not visible.
- Dynamic schema fields do not leak across repeated flow openings.
- Lux selectors allow realistic outdoor lux thresholds.
- Options flow handles missing runtime data cleanly.
- Feature-selection submit returns a root menu that includes newly enabled configurable
  features without requiring full options-flow exit/reopen.
- Features without config steps are represented clearly and do not create dead menu paths.

## Legacy Test Clash Audit

Use this section while developing the incremental-save redesign. When a config-flow or
options-flow test fails, first check whether it belongs to one of these categories before
treating it as a new regression. The goal is to distinguish expected failures from real
bugs and avoid preserving tests that enforce the rejected staged-save/intermediary-menu
paradigm.

### A) Final Save / Staged Options Paradigm

Old expectation:

- Forms update `self.area_options` only.
- Nothing reaches `config_entry.options` until the user selects `finish` / `Save & Exit`.
- Tests use `_finish_options_flow(...)` or `next_step_id: "finish"` before asserting
  persisted options.

New expectation:

- A complete page or complete guided subflow persists immediately through
  `async_update_entry(..., options=dict(self.area_options))`.
- `finish`/Done is not the only persistence path.
- Reopen-cycle tests should usually assert persistence immediately after the completing
  submit, not after a final finish step.

Known tests/helpers likely to fail or require rewrite:

- `tests/config_flow/test_config_flow_options_e2e.py::test_options_flow`
- `tests/config_flow/test_config_flow_options_e2e.py::test_options_flow_staged_edits_survive_back_navigation_until_save`
- Reopen/persistence tests in `test_config_flow_options_e2e.py` for Area behavior,
  Presence tracking, Area states, meta secondary states, and Custom control groups.
- Persistence/reopen tests in `test_config_flow_features_e2e.py` for Climate, Fan
  groups, Area-aware media player, Aggregates, Presence hold, BLE trackers, Wasp in a
  Box, Health, Light groups, and Adaptive Lighting coordination.
- `tests/config_flow/test_config_flow_features_e2e.py::_finish_options_flow`
- Any direct `async_configure(... {"next_step_id": "finish"})` used as the only save
  boundary.

Expected action:

- Replace final-save assertions with immediate-persistence assertions at the correct
  completion boundary.
- Keep a smaller Done/finish test only to prove the flow can close without being the only
  save mechanism.

### B) Root Single-Child Intermediary Menus

Old expectation:

- Root sections such as Area behavior, Presence tracking, Area states, and Custom control
  groups open a section menu containing Settings + Back.
- Their forms submit back to that intermediary menu.

New expectation:

- Root single-page sections route directly to their form.
- A successful submit persists immediately and returns to the root menu.
- The HA form page still does not have a native Back button; close/X abandons only the
  current unsubmitted form because prior completed pages are already persisted.

Known tests/helpers likely to fail or require rewrite:

- `tests/config_flow/test_config_flow_options_e2e.py::test_options_flow_root_sections_are_menu_first_with_back`
- `tests/config_flow/test_config_flow_options_e2e.py::test_options_flow_root_leaf_submits_return_to_parent_section_menu`
- `tests/config_flow/test_options_flow_translations.py::test_root_section_submenus_expose_settings_and_back`
- `tests/config_flow/options_flow_testkit.py::go_to_step`, because it currently
  auto-enters root section settings and can hide topology mistakes.

Expected action:

- Delete or rewrite the intermediary-menu tests to assert direct form routing.
- Remove auto-enter behavior from shared test helpers, or split helpers into explicit
  menu-navigation and form-navigation helpers so topology remains visible.

### C) Single-Page Feature Intermediary Menus

Old expectation:

- Every non-light configurable feature opens a section menu with Settings + Back.
- Single-page feature forms submit back to their feature section menu.

New expectation:

- Keep submenus only for domains with meaningful multi-page organization or near-term
  planned domain complexity.
- Keep submenus for Light groups, Climate automation, and Fan automation.
- Simple single-page features should route directly to their form and return to root
  after successful immediate persistence.

Known tests/helpers likely to fail or require rewrite:

- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_non_light_feature_sections_open_menu_first`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_non_light_leaf_submits_return_to_feature_menu`
- `tests/config_flow/test_options_flow_translations.py::test_feature_section_submenus_expose_settings_and_back`
- `tests/config_flow/test_config_flow_features_e2e.py::_open_feature_config_step`,
  because it currently auto-enters `*_settings` forms for non-light feature menus and
  can hide whether a feature incorrectly still has a submenu.
- `tests/config_flow/test_config_flow_feature_conf_handlers.py::test_options_flow_feature_conf_validation_error`
  and `test_options_flow_wasp_in_a_box_selector`, if they continue to assume
  `feature_conf_health_settings` / `feature_conf_wasp_in_a_box_settings` for simple
  single-page features.

Expected action:

- Rewrite topology tests to assert:
  - Light groups, Climate automation, and Fan automation are menu-first.
  - Health, Aggregates, Presence hold, BLE trackers, Wasp in a Box, and Area-aware media
    player route directly to forms.
- Make helper navigation explicit so tests fail when topology regresses.

### D) Climate Guided Completion

Old expectation:

- Climate entity selection can be treated like a normal feature submit in some tests.
- Preset mapping is reached, then persistence is asserted after final finish.

New expectation:

- Climate entity selection is not a persistence boundary when preset mapping is required.
- Entity submit advances to preset mapping.
- Preset mapping submit is the completion boundary and persists the feature.
- Changing the climate entity in an already complete config forces preset remapping
  before persistence.

Known tests likely to fail or require rewrite:

- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_climate_with_presets`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_climate_reopen_preserves_saved_entity_and_presets`
- `tests/config_flow/test_feature_config_climate.py::test_handle_climate_preset_selection_processes_valid_input`
- Climate no-preset/invalid-entity tests may need routing updates but the error
  expectations remain valid.

Expected action:

- Add explicit assertions that entity-only submit does not persist.
- Add explicit assertions that preset mapping submit persists.
- Add an entity-change remap test.

### E) Light-Group Brightness Mode Completion And Dormant Settings

Old expectation:

- Hidden or incompatible mode fields may be pruned/deleted when switching modes.
- Some tests focus on fields not leaking after reopen, which can be misread as requiring
  destructive deletion.

New expectation:

- Mode changes deactivate inactive mode fields for UI/runtime purposes.
- Dormant mode-specific settings remain persisted so switching back restores them.
- Runtime policy consumes only the active brightness mode's settings.
- Classic can persist immediately; Advisory and Adaptive persist after their dependent
  settings pages submit.

Known tests likely to fail or require rewrite:

- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_mode_fields_do_not_leak_after_reopen`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_roles_preserve_hidden_behavior_modes`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_brightness_preserves_hidden_roles`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_advisory_shows_binary_fields_only`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_adaptive_shows_binary_and_lux_fields`
- Light-group selector tests are generally still valid, but their navigation setup may
  need adjustment.

Expected action:

- Split "not visible/not active" assertions from "not persisted" assertions.
- Add tests proving Adaptive/Advisory settings survive switching away and are restored
  when switching back.
- Add runtime-policy tests proving dormant settings do not affect the active mode.

### F) Adaptive Lighting Completion Boundaries

Old expectation:

- Adaptive Lighting mode submit and final finish are sufficient for persistence.
- Transient pair fields should not leak into saved options.

New expectation:

- `ignore` is complete and can persist immediately.
- `adopt_existing` is incomplete until pairings are submitted.
- `manage` is incomplete until managed-role/all-lights choices are submitted.
- Dormant Adaptive Lighting mode-specific settings should be preserved where useful, but
  transient submitted pairing fields should still be normalized into the durable mapping
  shape.

Known tests likely to fail or require rewrite:

- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_adaptive_lighting_ignore_hides_pairings`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_adaptive_lighting_pairings_do_not_leak`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_adopt_existing_pairs_same_area_al_set`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_manage_selects_managed_roles`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_manage_immediately_reveals_targets`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_manage_defaults_to_configured_roles`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_manage_all_lights_uses_separate_gate`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_light_groups_preserves_adaptive_lighting_switch_sets`

Expected action:

- Preserve visibility/selector tests where they remain true.
- Rewrite persistence assertions around `ignore`, `adopt_existing`, and `manage`
  completion boundaries.
- Keep transient pair-field normalization tests, but distinguish them from dormant
  setting preservation.

### G) Feature Selection Persistence And Menu Refresh

Old expectation:

- Feature selection updates `self.area_options` and returns a refreshed menu.
- Some tests do not assert whether feature-selection submit persists immediately.

New expectation:

- Feature selection is a complete page and should persist enabled/disabled feature map on
  submit.
- Configurable features should still appear in the returned root menu immediately.
- Helper-only features should still not create dead config menu paths.

Known tests likely to need expansion:

- `tests/config_flow/test_feature_selection.py::test_handle_feature_selection_enables_selected_features`
- `tests/config_flow/test_feature_selection.py::test_handle_feature_selection_removes_deselected_features`
- `tests/config_flow/test_feature_selection.py::test_handle_feature_selection_creates_features_dict`
- `tests/config_flow/test_options_flow_integration.py::test_options_flow_select_features_then_configure`
- `tests/config_flow/test_options_flow_integration.py::test_options_flow_select_features_returns_refreshed_menu`
- `tests/config_flow/test_options_flow_integration.py::test_options_flow_deselecting_feature_removes_from_options`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_add_feature`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_remove_feature`
- `tests/config_flow/test_config_flow_features_e2e.py::test_options_flow_helper_only_features_enable_without_config_menu`

Expected action:

- Add immediate persistence assertions to feature selection tests.
- Preserve menu-refresh and helper-only/dead-path assertions.

### H) Translation/Copy Contracts

Old expectation:

- Root menu copy explains staged options and final Save & Exit.
- Menu labels include `Save & Exit`.
- Feature descriptions say configurable features add menu pages.

New expectation:

- Copy explains completed page submits save immediately.
- Close/X copy should imply unsubmitted current-page changes are lost, not that all prior
  submitted changes are lost.
- Done/finish should not imply it is the only persistence path.
- Feature-selection copy should distinguish direct config pages, intentional submenus,
  and helper-only features.

Known tests likely to fail or require rewrite:

- `tests/config_flow/test_options_flow_translations.py::test_options_flow_root_menu_uses_task_oriented_labels`
- `tests/config_flow/test_options_flow_translations.py::test_options_flow_root_menu_explains_save_behavior`
- `tests/config_flow/test_options_flow_translations.py::test_feature_selection_distinguishes_configurable_features`
- `tests/config_flow/test_options_flow_translations.py::test_feature_section_submenus_expose_settings_and_back`
- `tests/config_flow/test_options_flow_translations.py::test_root_section_submenus_expose_settings_and_back`
- `tests/config_flow/test_options_flow_translations.py::test_custom_control_groups_step_has_guidance`, if the
  custom-control step id returns from `custom_control_groups_settings` to
  `custom_control_groups`.

Expected action:

- Rewrite copy tests around incremental-save semantics and the new topology.

### I) Likely Compatible Tests

These areas are less likely to enforce the rejected paradigm. They may need small step-id
updates but should not be treated as expected failures unless they touch persistence or
menu topology.

- `tests/config_flow/test_config_flow_basic.py::*`
- `tests/config_flow/test_options_flow_routing.py::*`
- `tests/config_flow/test_config_flow_options_runtime.py::*`
- `tests/config_flow/test_feature_helpers.py::*`
- `tests/config_flow/test_area_steps.py::*`, except for handler-signature changes.
- `tests/config_flow/test_config_flow_errors.py::*`, except climate routing details.

Manual HA-dev validation should cover:

- The options menu labels are readable.
- Light-group configuration is understandable without dev-tools knowledge.
- Mode changes reveal the expected fields after submit/reopen.
- Adaptive Lighting adopt/manage setup is clear in the frontend.
- Custom control group editing is still possible after the cleanup.
- The HA device/entity pages show the expected controls/helpers for representative
  features, without duplicate legacy Magic Areas entities beside native helpers.

## Exit Criteria

- All config-flow tests pass.
- The user-exposed surface census is documented or encoded in tests closely enough that
  deleting/renaming a user-facing surface fails a targeted test.
- Full test suite, ruff, and mypy pass.
- The HA dev instance can open and complete the relevant options-flow paths.
- No frontend serializer errors appear for any feature config step.
- Light-group options are materially easier to navigate than the current flat form.
