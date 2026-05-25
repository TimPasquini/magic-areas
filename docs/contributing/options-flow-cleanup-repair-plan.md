# Options Flow Cleanup Repair Plan

Status: implementation complete; closure pending only deferred bulk copy polish and final commit.

## Purpose

This repair made the Magic Areas options flow easier to navigate and safer to use in the Home Assistant frontend. The core problem was not runtime behavior. The problem was that options pages had become broad, implementation-shaped, and easy to lose work in when navigating or closing the flow.

The repaired options flow now uses Home Assistant's native primitives around a clear user contract:

- Complete pages save when submitted.
- Closing the flow discards only the current unsubmitted page.
- The root menu does not expose a misleading final Done/Save action.
- Single-page tasks open directly.
- Multi-page domains remain grouped under intentional submenus.
- Guided flows persist only when enough information has been provided.

## Final Navigation Contract

Root menu entries that open direct forms:

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

Root menu entries that remain submenus:

- Light roles and automation.
- Fan automation.
- Climate automation.

The root menu does not expose Done, Finish, or Save & Exit. Submitted pages are already persisted, and Home Assistant's completion prompt is misleading under this model.

## Final Persistence Contract

- Area behavior, Presence tracking, Area states, Custom control groups, and single-page feature forms persist on successful submit and return to the root menu.
- Feature selection persists on submit and immediately refreshes the root menu.
- Light roles persist on submit and return to the Light groups submenu.
- Light brightness mode selection routes to the appropriate mode-specific page when needed.
- Classic brightness behavior persists immediately.
- Advisory and Adaptive brightness behavior persist after their mode-specific settings submit.
- Dormant brightness-mode settings are preserved so switching away and back restores prior values.
- Runtime behavior consumes only settings relevant to the active brightness mode.
- Adaptive Lighting ignore persists immediately.
- Adaptive Lighting adopt/manage persist after the required pairing or managed-role choices submit.
- Climate device selection advances to preset mapping; preset mapping is the climate persistence boundary.
- Invalid form submits stay on the form, show errors, and do not persist invalid values.
- Custom control group validation errors preserve the entered record list for correction.

## Completed Implementation

- Removed one-child intermediary menus from direct single-page tasks.
- Kept intentional submenus for Light groups, Fan automation, and Climate automation.
- Added page-level persistence through `async_update_entry` after successful completion boundaries.
- Removed the visible root Done/Save/Finish action.
- Added recursive option copying before staging and persistence so saved options are not mutated by reference.
- Normalized enabled feature maps to serialized string feature IDs.
- Split Light groups into role, brightness behavior, and Adaptive Lighting substeps.
- Added guided mode routing for brightness behavior and Adaptive Lighting behavior.
- Preserved dormant mode-specific settings while hiding inactive mode fields.
- Prevented transient Adaptive Lighting pairing fields from leaking into saved options.
- Improved selector use for fan settings, aggregate lux thresholds, BLE trackers, timing values, and custom control groups.
- Added clean abort behavior when runtime data is unavailable.
- Reworked feature-selection ordering and immediate root-menu refresh.
- Reworked translation contracts so user-facing text describes room behavior rather than implementation modules.
- Fixed custom control group validation so failed submitted records remain visible for correction.

## Test Coverage

Implemented and passing test coverage includes:

- Complete-page submit persists immediately.
- Validation failure does not persist invalid values.
- Failed custom control group validation preserves submitted records in the form.
- Submitted pages survive later close/reopen.
- Incomplete guided subflows do not persist partial dependent config.
- Single-child intermediary menus are removed.
- Light groups, Climate automation, and Fan automation remain intentional submenus.
- Simple feature pages open directly and return to root.
- Feature selection persists and immediately refreshes root menu entries.
- Helper-only features do not create dead configuration menu paths.
- Reopening submitted pages shows saved values as suggested/default values.
- Climate device selection advances to preset mapping and persists only after preset mapping.
- Light brightness modes route to the correct mode-specific fields.
- Dormant Advisory/Adaptive settings survive mode switches and are restored when switching back.
- Adaptive Lighting ignore/adopt/manage have the expected completion boundaries.
- Dynamic mode fields do not leak across repeated flow openings.
- Translation/menu tests enforce the current topology and incremental-save messaging.
- User-exposed surface tests cover representative controls/helpers, area/device attachment, visibility, membership/source attributes, and Magic Areas self-enumeration exclusions.

## Human Validation

Confirmed in the HA dev instance:

- Root options menu has no Done/Save & Exit item.
- Submitted pages persist after closing the flow.
- Area behavior, Presence tracking, Area states, and Custom control groups open directly, save on submit, and return to the root menu.
- Custom control group duplicate/invalid submit stays on the form, shows an error, and preserves entered records for correction.
- Feature selection immediately refreshes the root menu when configurable features are enabled or disabled.
- Light groups, Fan automation, and Climate automation remain intentional submenus.
- Health sensors, Aggregate sensors, Presence hold, Bluetooth tracker monitoring, Wasp in a Box, and Area-aware media player open as direct forms and return to root on submit.
- Light group roles, brightness mode routing, brightness mode field visibility, dormant mode value preservation, and Adaptive Lighting mode routing are usable in the HA UI.
- Climate automation advances from climate device selection to preset mapping, persists on preset mapping submit, and does not persist incomplete device-only changes.

## Deferred Work

Bulk menu/description text polish remains deferred. Current text is functional, tested, and more user-oriented than the prior implementation text, but final wording can be refined directly in translation files later.

This deferred text polish is not a blocker for closing the options-flow repair because the navigation, persistence, validation, and guided-flow behavior are implemented and validated.

## Exit Criteria Status

- Config-flow tests pass: complete.
- Full test suite passes: complete at the current implementation checkpoint.
- Ruff passes: complete.
- Mypy passes: complete.
- HA dev instance can open and complete relevant options-flow paths: complete by manual validation.
- No frontend serializer errors appear for feature config steps: complete by test and manual validation.
- Light-group options are materially easier to navigate than the prior flat form: complete by implementation and manual validation.
- User-exposed surfaces are documented or test-enforced closely enough that accidental removal/renaming fails targeted tests: complete for the representative surfaces in scope.
- Deferred copy polish is explicitly tracked and non-blocking.

## Closure Notes

This plan is now in a closable state. Before deleting this temporary plan, durable documentation should retain the current as-is options-flow behavior:

- Submitted complete pages save immediately.
- Closing the options flow only discards the current unsubmitted page.
- Root Done/Save/Finish is intentionally not exposed.
- Light groups, Fan automation, and Climate automation are intentional submenus.
- Direct single-page tasks should not gain one-child intermediary menus.
- Guided flows should persist only at their defined completion boundaries.
- Failed validation should preserve user-entered values where Home Assistant can safely re-render them.
