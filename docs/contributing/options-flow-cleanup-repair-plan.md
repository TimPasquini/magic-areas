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

## Navigation Contract

The selector/menu cleanup checkpoint now uses a consistent parent/child navigation
contract for feature sections. Root still owns final persistence through `Save & Exit`;
feature section menus own local Back navigation; and feature leaf forms submit back to
their local section menu instead of dumping the user back at the root menu.

The intended navigation contract is:

- Root menu owns final persistence through `Save & Exit`.
- Section menus own Back navigation to their parent menu.
- Leaf forms submit back to their local section menu, not directly to root, when a local
  section menu exists.
- Root-level leaf forms either need a lightweight section wrapper or an explicit decision
  that returning directly to root is their intended parent behavior.
- The frontend close/X behavior remains HA-owned and should be treated as abandon/cancel;
  Magic Areas should make the safe navigation path obvious enough that users do not need
  to rely on close/X for normal movement.

Implemented feature-section behavior:

- Light groups:
  - Submitting Light roles should return to the Light groups submenu.
  - Submitting Brightness behavior/settings should return to the Light groups submenu.
  - Submitting Adaptive Lighting coordination should return to the Light groups submenu.
  - The Light groups submenu Back option should return to the root options menu.
- Non-light configurable features:
  - Submitting each `*_settings` form should return to that feature's section menu.
  - Climate preset selection should return to the Climate automation section menu.
  - Each feature section menu Back option should return to the root options menu.

## Remaining Work

Feature-section and root-section backwards navigation are implemented and test-enforced.
Root-level settings now use the same menu-first pattern as feature sections:

- Area behavior opens a section menu with Settings and Back.
- Presence tracking opens a section menu with Settings and Back.
- Area states opens a section menu with Settings and Back.
- Custom control groups opens a section menu with Settings and Back.
- Submitting one of those settings forms returns to its parent section menu, not directly
  to root.

Tests still needed:

- Manual frontend validation should confirm the extra Settings screen feels acceptable in
  HA for common edits.
- Any newly added root-level option category should follow the same menu-first contract
  unless explicitly documented otherwise.

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
