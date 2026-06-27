# Master Architecture Roadmap Plan

Status: active consolidation plan. This document consolidates the information
from the current branch plans, durable simulation guidance, options-flow repair
plan, adaptive-switching plan, and CRG architecture audit into one sequential
roadmap. It is intended to become the primary planning surface once the temporary
branch plans are retired.

## Purpose

Magic Areas is moving from entity-level helper behavior toward room-level control
behavior. That shift has created several overlapping planning surfaces:

- fan and cover default automation
- live fake-house simulation coverage
- adaptive light switching
- options-flow cleanup
- codebase architecture and cleanup work surfaced by CRG

This roadmap keeps the actual information from those plans, not just references
to them, and orders the work so behavior branches can close before broad
structural refactors begin.

The sequencing rule is:

```text
Close behavior branches first. Preserve known gaps. Refactor support
architecture second. Expand coverage only after the harness can support it.
```

## Source Documents Consolidated

This roadmap incorporates the current useful content from:

- `docs/contributing/fan-cover-default-automation-plan.md`
- `docs/contributing/dev-simulation-guidance.md`
- `docs/contributing/options-flow-cleanup-repair-plan.md`
- `docs/contributing/lighting-adaptive-switching-plan.md`
- CRG architecture audit rebuilt on June 3, 2026

CRG rebuild summary:

```text
Files: 359
Nodes: 3516
Edges: 27431
Languages: python, bash
Last updated: 2026-06-03T22:28:41
```

## Current Architecture Baseline

Magic Areas is a Home Assistant custom integration with a coordinator/snapshot
runtime architecture. The broad architectural layers are:

- config entry lifecycle and migration
- coordinator snapshot creation and refresh
- entity and presence ingestion
- feature modules and feature dispatch
- native helper reconciliation
- policy/runtime layers for control domains
- HA platform adapters and entities
- pytest unit/platform/integration/scenario tests
- live fake-house simulation through a real local HA instance

The intended direction remains:

- Native Home Assistant helpers provide durable control/signal surfaces when
  practical.
- Magic Areas owns room intent, policy, conflict resolution, and setup guidance.
- Control groups define membership and policy boundaries.
- Control switches are master opt-ins for automatic action.
- Area states are the shared room-condition language.
- Domain policies may share signals, but one domain should not directly command
  another domain unless that is the explicit domain responsibility.

## CRG Architecture Findings

CRG communities after rebuild:

| Community | Size | Meaning |
|---|---:|---|
| `unit-area` | 1122 | unit and behavior-focused tests |
| `light-groups-group` | 1105 | main production runtime/policy/feature cluster |
| `config-flow-options` | 233 | config and options-flow surface |
| `platforms-setup` | 166 | Home Assistant platform setup paths |
| `scripts-area` | 151 | dev scripts and simulator |
| `integration-area` | 148 | config-entry lifecycle and integration setup |
| `tests-mock` | 124 | shared test helpers/mocks |
| `scenarios-light` | 63 | pytest scenario harness |
| `snapshots-snapshot` | 29 | snapshot coverage |
| `commit-models-commit` | 9 | small support cluster |
| `core-aggregates` | 7 | aggregate edge-case cluster |

High-coupling warnings:

| Coupling | Edges | Interpretation |
|---|---:|---|
| `light-groups-group` -> `unit-area` | 449 | many tests exercise runtime internals directly |
| `tests-mock` -> `platforms-setup` | 389 | shared test helpers are over-centralized |
| `tests-mock` -> `integration-area` | 308 | integration tests depend heavily on shared helpers |
| `tests-mock` -> `scenarios-light` | 42 | scenario tests pull generic helper substrate |
| `light-groups-group` -> `integration-area` | 23 | production runtime/lifecycle coupling should stay bounded |
| `light-groups-group` -> `platforms-setup` | 11 | minor but worth monitoring |

Key hotspots:

| Symbol | Degree | Risk |
|---|---:|---|
| `tests/helpers.py::assert_state` | 458 | central test assertion helper |
| `tests/helpers.py::shutdown_integration` | 224 | central lifecycle helper |
| `scripts/ha_dev_simulate.py::fan_cover_matrix` | 221 | simulator scenario hub |
| `tests/helpers.py::wait_for_state` | 170 | central async wait helper |
| `scripts/ha_dev_simulate.py::ExpectedState` | 168 | simulator assertion model |
| `tests/helpers.py::get_basic_config_entry_data` | 164 | central config-entry helper |
| `scripts/ha_dev_simulate.py::control_matrix` | 104 | simulator scenario hub |
| `feature_config.py::handle_feature_conf` | 88 | options-flow routing hotspot |
| `wasp_state_machine.py::WaspStateMachine` | 78 | production bridge |
| `fan.py::evaluate_fan_controllers` | 62 | fan policy hotspot |

Current branch impact:

```text
Risk: high
Changed files: 15
Impacted files: 109
Impacted nodes: 500
```

The high risk is expected because fan/cover policy, switch runtime, fake-house
config, bootstrap, simulator, tests, and docs changed together. It argues for
finishing branch closure before broad refactors.

## Validation Contract

Basic static validation:

```bash
./scripts/validate_basic.sh
```

Full Python validation:

```bash
./scripts/validate.sh
```

Full validation currently means:

```bash
uv run --extra dev --extra test ruff check custom_components tests scripts
MYPYPATH=. uv run --extra dev mypy --no-incremental --explicit-package-bases custom_components tests scripts
uv run --extra dev --extra test pytest tests -q
```

Mandatory phase-exit rule:

- Every phase must end with a fresh `./scripts/validate.sh` run after that
  phase's final code, test, and documentation changes.
- A phase is not complete until its numbered phase-exit validation item is
  checked and the result is recorded in this roadmap.
- Validation performed during extraction/refactor batches does not replace the
  final phase-exit run.
- Documentation-only retirement after a successful phase-exit run does not
  require repeating Python validation unless executable/configuration content
  changed after the run.

Live fake-house validation when simulator or room-control behavior changes:

```bash
./scripts/ha_dev_bootstrap.sh --force-magic-area-options
./scripts/ha_dev_simulate.sh --scenario fan-cover-matrix
./scripts/ha_dev_simulate.sh --scenario control-matrix
```

CRG validation after structural changes:

```bash
code-review-graph build --repo "/home/tim/Python Repos/magic-areas"
code-review-graph status --repo "/home/tim/Python Repos/magic-areas"
```

## Phase 0: Current Branch Stabilization

Goal: close the active fan/cover branch without expanding scope.

Execution evidence from 2026-06-05:

- `./scripts/validate_basic.sh`: passed.
- `./scripts/validate.sh`: passed; pytest reported `1405 passed in 39.41s`.
- `./scripts/ha_dev_bootstrap.sh --force-magic-area-options`: passed.
- `./scripts/ha_dev_simulate.sh --scenario fan-cover-matrix`: passed; log captured at `/tmp/magic-areas-fan-cover-matrix.log`.
- `./scripts/ha_dev_simulate.sh --scenario control-matrix`: passed with `exit=0`; log captured at `/tmp/magic-areas-control-matrix.log`.
- Failure scans for both simulator logs found no failed checks, tracebacks, or error markers.

Do now:

- Preserve currently passing fan/cover behavior.
- Preserve simulator real-time timing semantics.
- Preserve Setup Room as config-flow/manual setup only.
- Keep validation wrappers as the standard path.
- Keep the active plan files accurate until they are intentionally retired.

Do not do now:

- Do not modularize the simulator before branch closeout.
- Do not split test helpers before branch closeout.
- Do not remove dead code before branch closeout.
- Do not restructure options-flow routing before branch closeout.
- Do not broaden live simulation scope unless needed to prove a current branch
  requirement.

Exit criteria:

- `./scripts/validate.sh` passes.
- Default `fan-cover-matrix` passes.
- Default `control-matrix` passes.
- Current fan/cover plan accurately distinguishes completed work from future
  gaps.
- Temporary simulator repair document is absent.

## Phase 1: Fan/Cover Default Automation Closure

Goal: close the fan/cover branch plan while preserving detailed future work.

Evidence map:

- Fan policy coverage lives in `tests/unit/test_fan_controller_policy.py`.
- Fan runtime switch coverage lives in `tests/unit/test_fan_control_switch.py`.
- Fan config-flow coverage lives in `tests/config_flow/test_config_flow_features_e2e.py`.
- Cover policy/runtime coverage lives in `tests/unit/test_cover_control_policy.py`.
- Cover scenario coverage lives in `tests/scenarios/test_cover_automation.py`.
- Fan/Cover live fake-house coverage lives in `scripts/ha_dev_simulate.py` under the `fan-cover-matrix` scenario.
- Current live evidence is captured in `/tmp/magic-areas-fan-cover-matrix.log`; the run completed with no failed checks or error markers on 2026-06-05.
- Full validation evidence is captured by the 2026-06-05 `./scripts/validate.sh` run; pytest reported `1405 passed in 39.41s`.

### Fan Automation Model

Fan automation is a reusable controller/reason model.

Built-in controller roles:

- `cooling`
- `humidity`
- `odor`

Each role represents a reason a fan should run. A controller owns:

- fan membership
- signal source
- activation logic
- clear behavior
- unavailable-sensor behavior
- required area states
- suppression states
- debug reason state

Fan on/off contract:

- A fan turns on when at least one controller reason targeting that fan is active.
- A fan turns off only when no controller reason targeting that fan remains active
  and all applicable holds have expired.
- No individual controller may turn off a fan still required by another active
  controller.
- Area-state gating and suppression are evaluated per controller.
- The fan control switch remains the master automation enable.

Controller config contract:

- `controller_id`: stable role ID, initially `cooling`, `humidity`, or `odor`.
- `members`: fan entities controlled by this controller.
- `sensor_entity_id`: selected sensor or managed/aggregate signal source.
- detection mode: threshold, threshold+trend, or room-state fallback where
  supported.
- threshold and hysteresis fields where sensor-driven.
- required active states.
- suppress states.
- clear behavior.
- unavailable behavior.
- hold durations where relevant.

Completed fan behavior:

- Cooling controller activates above threshold.
- Cooling controller clears below threshold/hysteresis.
- Humidity controller can remain active after occupancy clears.
- Humidity threshold-only mode is tested.
- Humidity threshold+trend mode is tested.
- Trend/rate signal supplements threshold/hysteresis rather than replacing it.
- Managed Trend helper is created and consumed for a configured fan controller.
- Odor controller activates from VOC/air-quality threshold.
- Explicit room-state odor fallback runtime is implemented and unit-tested.
- Same fan assigned to humidity and odor stays on until both reasons clear.
- Suppress states block only the configured controller.
- Sensor unavailable behavior is applied per controller.
- Fan decisions never turn off a fan still needed by another active reason.
- `post_clear_hold` is enforced with timer/expiry coverage.
- `hold_then_clear` unavailable behavior is enforced with timer/expiry coverage.
- `hold_until_restored` unavailable behavior is live-asserted for VOC/odor.
- Fan-derived visible area states are implemented for `humid`, `odor`, and `hot`.
- Fan on/off state alone does not create false room-condition states.
- Runtime debug attributes expose active reasons, suppressed reasons, held
  reasons, unavailable timers, and target fans.
- Master fan control switch disables automatic action.
- Managed helper/self-enumeration protections still hold.

Completed fan config-flow behavior:

- Fan automation submenu exposes Cooling, Humidity, and Odor pages.
- Controller pages use appropriate selectors.
- Same fan can be selected in multiple controller roles.
- Existing single fan config reopens as Cooling settings.
- Each controller page persists independently.
- Invalid values remain on the form and do not persist.
- UI/config does not expose timer modes that runtime cannot honor unless runtime
  implements them.

Completed fan live simulation:

- Fan Room is the dedicated live fan validation surface.
- Setup Room is not used for active fan simulation.
- Dedicated VOC/air-quality sensor path is live-simulated.
- Humidity + odor overlap is live-simulated.
- Managed fan Trend helper behavior is live-asserted.
- `threshold_trend` detection is live-asserted.
- `post_clear_hold` timer expiry is live-asserted after the real seeded clear
  window and configured post-clear hold duration.
- `hold_then_clear` sensor-unavailable timer expiry is live-asserted.
- `hold_until_restored` unavailable behavior is live-asserted.
- Sleep suppression for humidity controller is live-asserted.
- Disabled fan-control switch behavior is live-asserted.

Open fan gaps:

- Explicit room-state odor fallback is covered at lower test layers but is not
  live-simulated.
- Fan behavior across Home Assistant reload/restart is not live-asserted.
- Multiple physical fans and overlapping roles targeting different fans are not
  simulated.
- Cooling fan occupancy run is not live-simulated as a distinct room story.
- Bathroom humidity shower and Bathroom odor/VOC runs remain future scenario
  stories if Bathroom becomes a domain-specific live surface.

### Cover Automation Model

Cover automation is preset-based and uses existing native cover helper groups as
targets.

Default eligible automation classes:

- `blind`
- `curtain`
- `shade`
- `shutter`
- `window`

Default excluded automation classes:

- `awning`
- `garage`
- `gate`
- `door`
- `damper`

Cover presets:

- Daylight
- Privacy/Sleep
- Media/Accent

Cover runtime contract:

- Cover movement is opt-in.
- Cover control switch gates automatic movement.
- Daylight can open eligible covers only when configured state tokens match and
  runtime daylight context allows it.
- Runtime daylight context currently derives from room dark/bright context.
- Privacy/Sleep wins over Daylight.
- Media/Accent wins over Daylight while active.
- Media/Accent release may reopen covers only when configured Daylight state
  tokens match and runtime Daylight context allows it.
- Cover policy emits cover service calls only; it does not directly command
  lights.
- Light/adaptive policy reacts to changed brightness/context separately.
- Manual cover-helper state changes start a hold scoped to the changed cover
  helper/entity set.
- State changes expected from Magic Areas service calls do not start manual hold.
- Manual hold expiry schedules policy reevaluation so automation can reclaim the
  held cover.

Completed cover behavior:

- Cover preset config saves and reopens.
- Editable presets expose meaningful defaults.
- Manual hold duration saves and reopens.
- Cover automation remains opt-in.
- Eligible cover classes are selected for automation.
- Excluded cover classes remain helper/control surfaces only.
- Privacy/Sleep wins over Daylight.
- Media/Accent wins over Daylight while active.
- Media/Accent release can reopen when configured Daylight state tokens match.
- Media/Accent release can reopen only when runtime Daylight context allows it.
- Unit tests prove Daylight does not open covers when runtime daylight context is
  invalid.
- Runtime tests prove manual hold is scoped to the changed helper/group/member
  set.
- Cover policy emits no light service calls.
- Cover opening can support adaptive light-off through brightness context.
- Cover closing can support light-on when occupied/dark through light policy.
- Media/Accent cover close does not directly command lights.
- Manual cover movement is not immediately reversed.

Completed cover live simulation:

- Cover Room is the dedicated live cover validation surface.
- Setup Room is not used for active cover simulation.
- Blind, shade, curtain, shutter, and window classes are live-tested.
- Excluded garage/door covers are live-tested as not moved by default automation.
- Daylight open is live-tested.
- Sleep/Privacy close is live-tested.
- Media/Accent close/release is live-tested.
- Dark-context no-open is live-tested.
- Disabled cover-control switch behavior is live-tested.
- Manual hold expiry/release is live-tested.
- Manual hold on shade alongside blind hold is live-tested.
- Multiple simultaneous manual holds are live-tested.
- Cover scenario is asserted alongside room bright/dark signal so Daylight open
  blocking is validated against real room context.
- Live dev-house harness traces cover open with bright context.
- Live dev-house harness traces cover close with dark context.

Open cover gaps:

- Partial position/tilt behavior is not simulated.
- Cover movement states such as `opening`/`closing` are not simulated.
- Time-of-day or richer daylight policy is not simulated beyond room bright/dark
  binary.
- Cover behavior across Home Assistant reload/restart is not live-asserted.
- Reconciliation after cover membership/class changes is not live-asserted.
- Cover/adaptive debug context is not proven if the desired debug contract
  requires explicit cover movement/source attribution.

### Cross-Domain Fan/Cover Gaps

Open cross-domain gaps:

- Fan Room and Cover Room are independent; there is no combined active room
  testing fan, cover, light, and adaptive interactions together.
- Dedicated rooms do not fully live-assert cover-induced brightness affecting
  adaptive switching through a full fake-house pipeline.
- Media-player integration signals are not used; accent stands in for
  media/accent context.
- Config-flow UI automation does not validate that a user can manually create
  these exact room configs.
- Helper/entity registry repair after entity removal, rename, or
  reclassification is not live-asserted.

Phase 1 exit criteria:

- Fan/cover completed behavior remains validated.
- Future fan/cover gaps above live in this roadmap or durable guidance.
- Temporary fan/cover plan can be deleted without losing branch knowledge.

## Phase 2: Options-Flow Cleanup Plan Retirement

Goal: preserve the options-flow cleanup contract and retire the temporary repair
plan.

The cleanup addressed options pages that had become broad,
implementation-shaped, and easy for users to lose work in while navigating or
closing the flow. The durable contract therefore prioritizes task-oriented
navigation and explicit page-level persistence boundaries.

Evidence map:

- Options-flow topology, persistence, selector, guided-flow, and reopen behavior
  are covered by `tests/config_flow/test_config_flow_features_e2e.py`.
- Feature-selection root refresh behavior is covered by
  `tests/config_flow/test_options_flow_integration.py`.
- Translation/menu topology and incremental-save messaging are covered by
  `tests/config_flow/test_options_flow_translations.py`.
- User-exposed helper/control surface contracts are covered by
  `tests/integration/test_user_exposed_surface_contract.py`.
- Current branch validation passed on 2026-06-05 via `./scripts/validate.sh`;
  pytest reported `1405 passed in 39.41s`.
- Forced options bootstrap passed on 2026-06-05 via
  `./scripts/ha_dev_bootstrap.sh --force-magic-area-options`.
- Fresh forced options bootstrap passed on 2026-06-06. It reconfigured every
  active fake-house Magic Area through Home Assistant's real options-flow REST
  endpoints and ended with `Home Assistant dev bootstrap complete`.
- Fresh rendered-frontend validation on 2026-06-06 used authenticated headless
  Firefox against the real dev instance. The Magic Areas integration page
  rendered successfully with version `4.4.1`, its hub list, and current
  devices/entities.
- A post-bootstrap scan of the preceding ten minutes of Home Assistant logs
  found no error, exception, traceback, serializer, failed, or invalid markers.

### Final Navigation Contract

Root menu entries that open direct forms:

- Area behavior
- Presence tracking
- Area states
- Custom control groups
- Health sensors
- Aggregate sensors
- Presence hold
- Bluetooth tracker monitoring
- Wasp in a Box
- Area-aware media player

Root menu entries that remain submenus:

- Light roles and automation
- Fan automation
- Climate automation

The root menu does not expose Done, Finish, or Save & Exit. Submitted pages are
already persisted, and Home Assistant's completion prompt is misleading under
this model.

### Final Persistence Contract

- Area behavior, Presence tracking, Area states, Custom control groups, and
  single-page feature forms persist on successful submit and return to the root
  menu.
- Feature selection persists on submit and immediately refreshes the root menu.
- Light roles persist on submit and return to the Light groups submenu.
- Light brightness mode selection routes to the appropriate mode-specific page
  when needed.
- Classic brightness behavior persists immediately.
- Advisory and Adaptive brightness behavior persist after mode-specific settings
  submit.
- Dormant brightness-mode settings are preserved so switching away and back
  restores prior values.
- Runtime behavior consumes only settings relevant to the active brightness mode.
- Adaptive Lighting ignore persists immediately.
- Adaptive Lighting adopt/manage persist after required pairing or managed-role
  choices submit.
- Climate device selection advances to preset mapping.
- Climate preset mapping is the climate persistence boundary.
- Invalid form submits stay on the form, show errors, and do not persist invalid
  values.
- Custom control group validation errors preserve the entered record list for
  correction.
- Validation failures should preserve submitted user values wherever Home
  Assistant can safely re-render them.

### Completed Options-Flow Implementation

- Removed one-child intermediary menus from direct single-page tasks.
- Kept intentional submenus for Light groups, Fan automation, and Climate
  automation.
- Added page-level persistence through `async_update_entry` after completion
  boundaries.
- Removed visible root Done/Save/Finish action.
- Added recursive option copying before staging and persistence so saved options
  are not mutated by reference.
- Normalized enabled feature maps to serialized string feature IDs.
- Split Light groups into role, brightness behavior, and Adaptive Lighting
  substeps.
- Added guided mode routing for brightness behavior and Adaptive Lighting
  behavior.
- Preserved dormant mode-specific settings while hiding inactive mode fields.
- Prevented transient Adaptive Lighting pairing fields from leaking into saved
  options.
- Improved selector use for fan settings, aggregate lux thresholds, BLE trackers,
  timing values, and custom control groups.
- Added clean abort behavior when runtime data is unavailable.
- Reworked feature-selection ordering and immediate root-menu refresh.
- Reworked translation contracts so user-facing text describes room behavior
  rather than implementation modules.
- Fixed custom control group validation so failed submitted records remain
  visible for correction.

### Options-Flow Test Coverage To Preserve

- Complete-page submit persists immediately.
- Validation failure does not persist invalid values.
- Failed custom control group validation preserves submitted records.
- Submitted pages survive later close/reopen.
- Incomplete guided subflows do not persist partial dependent config.
- Single-child intermediary menus are removed.
- Light groups, Climate automation, and Fan automation remain intentional
  submenus.
- Simple feature pages open directly and return to root.
- Feature selection persists and immediately refreshes root menu entries.
- Helper-only features do not create dead configuration menu paths.
- Reopening submitted pages shows saved values as suggested/default values.
- Climate device selection advances to preset mapping and persists only after
  preset mapping.
- Light brightness modes route to correct mode-specific fields.
- Dormant Advisory/Adaptive settings survive mode switches and restore when
  switching back.
- Adaptive Lighting ignore/adopt/manage have expected completion boundaries.
- Dynamic mode fields do not leak across repeated flow openings.
- Translation/menu tests enforce topology and incremental-save messaging.
- User-exposed surface tests cover representative controls/helpers, area/device
  attachment, visibility, membership/source attributes, and Magic Areas
  self-enumeration exclusions.
- Representative user-exposed surfaces remain protected by tests so accidental
  removal or renaming fails targeted validation.

### Options-Flow Manual Validation To Preserve

- Root options menu has no Done/Save & Exit item.
- Submitted pages persist after closing the flow.
- Area behavior, Presence tracking, Area states, and Custom control groups open
  directly, save on submit, and return to root.
- Custom control group duplicate/invalid submit stays on the form, shows an
  error, and preserves entered records.
- Feature selection immediately refreshes the root menu when configurable
  features are enabled or disabled.
- Light groups, Fan automation, and Climate automation remain intentional
  submenus.
- Health sensors, Aggregate sensors, Presence hold, Bluetooth tracker monitoring,
  Wasp in a Box, and Area-aware media player open as direct forms and return to
  root on submit.
- Light group roles, brightness mode routing, brightness mode field visibility,
  dormant mode value preservation, and Adaptive Lighting mode routing are usable
  in the Home Assistant UI.
- Climate automation advances from climate device selection to preset mapping,
  persists on preset mapping submit, and does not persist incomplete
  device-only changes.
- Relevant feature-configuration steps produced no frontend serializer errors
  during Home Assistant dev-instance validation.

Fresh live validation note:

- The 2026-06-06 forced bootstrap freshly exercised the live root options menu,
  Area behavior, Presence tracking, Area states, feature selection, Light
  brightness/Adaptive Lighting/role pages, Fan humidity/odor pages, Cover
  settings, and Presence hold through Home Assistant's real flow endpoints.
- Authenticated headless Firefox freshly proved the current integration page
  renders in the real frontend. Automated tests remain the evidence for the
  complete navigation/persistence matrix and detailed invalid-submit behavior;
  no unattended claim is made about subjective visual usability.

Deferred options-flow work:

- Bulk menu/description text polish remains deferred.
- Current text is functional, tested, and more user-oriented than prior
  implementation text.
- Final wording can be refined directly in translation files later.

Phase 2 exit criteria:

- Durable docs preserve the options-flow behavior above.
- Temporary options-flow repair plan can be deleted without losing behavior
  contract or validation history.

## Phase 3: Dev Simulation Guidance Consolidation

Goal: preserve the live simulator's design intent, current coverage, and gaps.

### Simulation Purpose

The project uses two complementary simulation layers:

- `tests/scenarios/` for deterministic pytest regression coverage.
- `dev/ha/` for a real local Home Assistant fake-house instance that supports
  human inspection and timed live simulation.

Neither layer replaces normal unit, platform, or integration tests.

Live fake-house simulation is required when behavior depends on:

- real HA runtime ordering
- frontend/config-flow inspection
- Adaptive Lighting compatibility
- native helper propagation
- human judgment about expected room behavior
- real timing semantics

### Real-Time Simulation Rules

- Live scenarios test real Home Assistant runtime behavior.
- The default simulation cycle is 30 seconds.
- Minute-based Magic Areas timing must be represented as real elapsed time.
- Do not shorten minute-based Magic Areas timers for simulator convenience.
- Do not use `checkpoint_settle_seconds` as a proxy for clear, extended, sleep,
  manual-hold, post-clear-hold, dwell, attribution, or helper sampling behavior.
- Immediate propagation waits must be separate from behavioral waits.
- Behavior waits should be named and derived from cycle timing or fake-house
  runtime constants.
- Setup Room must not be used in active simulation scenarios.

### Current Pytest Scenario Coverage

Current scenario coverage includes:

- advisory brightness behavior for bright, not-bright, invalid startup, and
  recovery
- adaptive bright-off gates for dwell, minimum on-time, outside context, outside
  lux contrast, ambient-rise evidence, and attribution hold after Magic
  Areas-controlled or manually activated configured room-light output
- room-state-driven Adaptive Lighting switch coordination for sleep and accent
  transitions
- configured in-room light brightness increases blocking ambient-rise adaptive
  off decisions
- adopted Adaptive Lighting brightness increases blocking ambient-rise adaptive
  off decisions through the actual controlled light entity
- cover preset runtime behavior
- cover dark-context no-open
- cover open contributing to adaptive light-off
- cover close contributing to adaptive light-on

Scenario trace expectations:

- step name
- occupancy state
- area `states` attribute
- in-room bright signal state
- outdoor context state when present
- Magic Areas light-control switch state when present
- native helper group state
- target member light states
- manual/control ownership state when present
- policy or decision reason when exposed through stable public/debug surface

### Current Live Fake-House Rooms

Active/current room matrix:

- Living Room
- Bathroom
- Classic Sun Room
- Classic Sensor Room
- Advisory Sun Room
- Advisory Sensor Room
- Startup Unknown Room
- Startup Unavailable Room
- Adaptive Sun Room
- Adaptive Binary Room
- Adaptive Lux Room
- Adaptive Ambient Room
- Adaptive Manual Light Room
- Adaptive Lighting Room
- Fan Room
- Cover Room
- Setup Room
- Outdoor Test

Room responsibilities:

- Living Room covers basic timed room story and manual override flows.
- Bathroom may be used for additional light behavior inspection and future fan
  bathroom stories.
- Control-matrix rooms cover classic, advisory, adaptive, startup fallback, and
  Adaptive Lighting behavior.
- Fan Room is the dedicated active fan automation validation room.
- Cover Room is the dedicated active cover automation validation room.
- Setup Room is intentionally unconfigured by bootstrap and reserved for
  frontend/config-flow/manual setup validation.

### Current Live Scenarios

Current live scenarios:

```bash
./scripts/ha_dev_simulate.sh --scenario living-room-demo
./scripts/ha_dev_simulate.sh --scenario control-matrix
./scripts/ha_dev_simulate.sh --scenario disabled-light-controls
./scripts/ha_dev_simulate.sh --scenario adaptive-negative-context
./scripts/ha_dev_simulate.sh --scenario manual-override
./scripts/ha_dev_simulate.sh --scenario presence-hold
./scripts/ha_dev_simulate.sh --scenario adaptive-lighting-manual-release
./scripts/ha_dev_simulate.sh --scenario fan-cover-matrix
```

Current live simulation coverage:

- Dark occupied rooms turn configured overhead lights on.
- Classic brightness behavior turns overhead lights off when the room becomes
  bright.
- Advisory brightness behavior does not force overhead lights off when the room
  becomes bright.
- Advisory daylight-context behavior still allows occupancy-on overhead lighting
  when advisory in-room brightness is not bright.
- Startup unknown/unavailable in-room brightness behavior is covered.
- Disabled Magic Areas light-control switch behavior is covered.
- Adaptive brightness behavior turns overhead lights off when outside context and
  timing gates are satisfied.
- Adaptive outside-context negative cases are asserted for outside binary not
  bright, outside lux below minimum, and insufficient outside/inside contrast.
- Adaptive ambient-rise behavior covers contaminated and clean evidence.
- Initial rise after Magic Areas turns a light on does not immediately turn that
  light back off.
- Manually activated configured room-light output does not turn overhead off.
- Later clean daylight-style rise turns adaptive overhead lighting off after
  attribution clears.
- Accent suppresses overhead lights and turns accent-role lights on.
- Sleep suppresses overhead lights and turns sleep-role lights on.
- Sleep plus accent overlap preserves lights belonging to both suppressive roles.
- Clear/empty behavior is asserted after occupancy, sleep, and accent inputs turn
  off and configured clear timing settles.
- Native HA light helper groups are asserted with member lights.
- Real Adaptive Lighting integration is present.
- Magic Areas sleep state turns on managed Adaptive Lighting sleep-mode switches.
- Manual light turn-off while occupied releases Magic Areas control and blocks
  automatic reacquire during bright/dark churn.
- Clear followed by re-occupancy resets manual override and allows Magic Areas to
  reclaim control.
- Presence hold is asserted as an independent occupancy source.
- Adaptive Lighting manual-control release is asserted through real HA
  `call_service` event for `adaptive_lighting.set_manual_control`.
- Fan Room coverage listed in Phase 1 is live-asserted.
- Cover Room coverage listed in Phase 1 is live-asserted.

Current high-value simulation gaps:

- Extended-state behavior is incidental rather than directly asserted.
- Manual override release without room clear is not covered because current light
  runtime does not implement a standalone manual-override timer.
- Adaptive Lighting `adopt_existing` mode is not covered live.
- Ambient-rise false positives from Adaptive Lighting brightness changes are
  covered in pytest scenarios but not live fake-house script.
- Ambient-rise false positives from neighboring/spill-over lights are not
  covered.
- Media and other future control-domain overlap cases are not covered.
- Config flow and frontend behavior are not automated by fake-house simulation.
- Reconciliation behavior after entity/helper/group membership changes is not
  covered by fake-house simulation.

Phase 3 exit criteria:

- `dev-simulation-guidance.md` remains durable source of truth.
- This roadmap carries future simulation backlog so temporary branch plans can be
  retired.

## Phase 4: Lighting Adaptive Switching Consolidation

Goal: preserve completed adaptive-switching behavior and deferred work.

### Problem And Constraints

The original failure mode was treating `BRIGHT` as a hard inhibitor even when
the configured brightness source did not represent actual in-room light level,
such as using `sun.sun` during daytime. That could suppress needed occupancy
lighting in a physically dark room.

Adaptive switching must:

- allow occupied rooms to turn lights on when measured in-room brightness is low
- preserve clear/timeout/profile off behavior
- work without requiring an outside lux sensor
- optionally use outside/inside contrast when outside lux exists
- avoid feedback loops when controlled lights affect the in-room lux sensor

Rollout constraints:

- no broad coordinator/runtime refactor as part of the feature
- no mandatory new entities or sensors for existing users
- no breaking default behavior; `inhibit` remains the default
- brightness mode remains feature-level rather than per-role in the current
  model

Evidence map:

- Policy-mode and adaptive safeguard coverage lives in
  `tests/unit/test_core_light_control.py`.
- Runtime guard derivation, managed Trend preference, contamination handling,
  and recheck behavior live in
  `tests/unit/test_light_group_runtime_adaptive_guards.py`.
- Signal-helper surface coverage lives in
  `tests/unit/test_signal_helper_surfaces.py` and
  `tests/unit/test_feature_module_contracts_light_groups.py`.
- Config/options-flow adaptive field visibility and persistence live in
  `tests/config_flow/test_config_flow_features_e2e.py`.
- Migration/backfill coverage lives in `tests/integration/test_config_migrations.py`.
- Adaptive Lighting coordination coverage lives in
  `tests/unit/test_adaptive_lighting_contracts.py`,
  `tests/unit/test_adaptive_lighting_executor.py`, and
  `tests/unit/test_managed_adaptive_lighting_reconciler.py`.
- Live fake-house adaptive behavior is covered by the `control-matrix`,
  `adaptive-negative-context`, and `adaptive-lighting-manual-release` scenarios
  in `scripts/ha_dev_simulate.py`.
- Current live `control-matrix` evidence is captured in
  `/tmp/magic-areas-control-matrix.log`; the run completed with `exit=0` and no
  failed checks or error markers on 2026-06-05.

### Adaptive Switching Model

Modes:

- `inhibit`: current/legacy behavior; `BRIGHT` may block or turn off lights.
- `advisory`: `BRIGHT` never directly forces off.
- `adaptive`: `BRIGHT` may force off only after safety checks.

Signal boundary:

- Home Assistant/native helpers answer measured-condition questions.
- Magic Areas answers room-policy questions.
- Adaptive Lighting owns brightness/color behavior for lights that are on.
- Magic Areas owns on/off switching policy and AL coordination switches.

Signal inputs:

- inside brightness, preferably threshold binary from in-room lux
- outside context from sun, outside lux, binary override, or none
- ambient-rise evidence, preferably managed Trend helper
- direct-light attribution from Magic Areas-controlled lights, configured in-room
  lights, user changes, Adaptive Lighting changes, and future spill-over lights

Fallback and degradation behavior:

- with outside lux, use inside brightness plus configured outside/inside contrast
  rules
- without outside lux but with sun context, use inside brightness plus daytime,
  dwell, and minimum-on-time gates
- without outside lux or usable sun context, degrade toward advisory behavior
- optional spill-over lights must be user-configured because Magic Areas cannot
  infer which neighboring outputs affect a particular lux sensor

Adaptive safeguards:

- minimum on-time before bright-driven off
- bright dwell/debounce duration
- optional outside-inside contrast gating
- attribution guard after controlled or direct light output changes

Observability and risk boundaries:

- stable decision context is exposed through `adaptive_guards`,
  `brightness_mode`, and `last_policy_reason`
- a generic Trend helper can identify rising lux but cannot prove the source was
  daylight
- Magic Areas must not rebuild generic rolling-window/rate machinery or delegate
  room-specific policy to helper combinations
- thresholds remain configurable to avoid overfitting one sensor topology and
  excessive state churn
- direct-light attribution must continue guarding against feedback from Magic
  Areas actions, user actions, Adaptive Lighting changes, and future configured
  spill-over lights

### Completed Adaptive Switching Work

- `LightGroupPolicy` supports `inhibit`, `advisory`, and `adaptive`.
- Default mode remains `inhibit`.
- Advisory behavior is tested.
- Adaptive bright-off gating is tested.
- Legacy/default bright behavior is preserved.
- Runtime derives min-on, bright-dwell, attribution-hold, outside-context,
  inside-bright, and ambient-rise guard values.
- Guard values pass through `LightPolicySignals`.
- Runtime exposes `adaptive_guards` attributes.
- Ambient-rise prefers managed Trend helper when valid.
- Transitional in-runtime detector remains as fallback for helper warm-up/missing
  state.
- Light-group schema/defaults include brightness mode, adaptive guard durations,
  inside/outside brightness sources, contrast settings, and ambient-rise settings.
- Options flow conditionally exposes advisory/adaptive fields by mode.
- Options-flow tests cover mode-specific field visibility and preservation.
- Outside-context sources include `sun`, `outside_lux`, and `none`.
- Optional outside-bright binary can override source checks.
- Outside-lux mode supports minimum lux, delta, and ratio gates.
- Migration `2.2 -> 2.3` backfills adaptive-switching keys.
- Managed signal-helper work required no additional migration beyond `2.3`.
- Configured in-room light on/off attribution includes all light-group roles in
  the room, not only the role currently evaluating policy.
- Live fake-house validation covers contaminated and clean ambient-rise evidence.
- Manual configured room-light output does not turn overhead off.
- Configured room-light brightness increases are scenario-covered as
  direct-light contamination.
- Adopted Adaptive Lighting brightness increases are scenario-covered through
  the actual controlled light entity.
- A later clean daylight-style rise turns adaptive overhead lighting off after
  attribution clears.

Deferred adaptive work:

- User-configured spill-over light attribution.
- Derivative/statistics helper bundles for richer future signals.
- Live fake-house coverage for Adaptive Lighting brightness-change false
  positives.
- Debug context for cover-derived brightness source if required.

Phase 4 exit criteria:

- Lighting adaptive switching plan can be retired without losing completed
  behavior or deferred work.

## Phase 5: Simulator Modularization

Goal: split `scripts/ha_dev_simulate.py` into maintainable modules without
changing behavior.

CRG driver:

- `fan_cover_matrix`: degree 221.
- `control_matrix`: degree 104.
- `ExpectedState`: degree 168.

Target structure:

```text
scripts/ha_dev_simulation/
  __init__.py
  cli.py
  client.py
  timing.py
  expectations.py
  reset.py
  preflight.py
  traces.py
  entities.py
  scenarios/
    __init__.py
    lights.py
    fan_cover.py
    living_room.py
```

Module responsibilities:

- `cli.py`: argument parsing and scenario dispatch helpers.
- `client.py`: websocket connection, service calls, and state reads.
- `timing.py`: `SimulationTiming` and real-time wait helpers.
- `expectations.py`: `ExpectedState`, assertion helpers, and evaluation helpers.
- `reset.py`: fake-house reset and clear-state isolation.
- `preflight.py`: live config-entry/option validation.
- `traces.py`: trace output and checkpoint formatting.
- `entities.py`: fake-house entity naming helpers and constants.
- `scenarios/lights.py`: control-matrix and light-specific scenarios.
- `scenarios/fan_cover.py`: fan-cover-matrix.
- `scenarios/living_room.py`: living-room-demo schedule story.

Extraction sequence:

1. Extract constants and passive dataclasses.
2. Extract HA websocket/service/state helpers.
3. Extract timing helpers.
4. Extract `ExpectedState` and evaluation helpers.
5. Extract trace/checkpoint output helpers.
6. Extract preflight validation.
7. Extract fan-cover scenario.
8. Extract light/control-matrix scenario.
9. Extract living-room schedule scenario.
10. Leave `scripts/ha_dev_simulate.py` as CLI compatibility wrapper until callers
    can move safely.

Rules:

- Preserve public CLI and shell wrapper.
- Keep default 30-second timing semantics.
- Move by concern, not arbitrary line ranges.
- Validate after each extraction batch.
- Do not convert live simulation into unit-test timing.

Validation per extraction batch:

```bash
./scripts/validate_basic.sh
./scripts/ha_dev_simulate.sh --scenario fan-cover-matrix
./scripts/ha_dev_simulate.sh --scenario control-matrix
```

Phase exit validation:

```bash
./scripts/validate.sh
```

Exit criteria:

- Existing simulator commands still work.
- Default live scenarios pass.
- No behavior waits are shortened or anonymized.
- CRG no longer reports `fan_cover_matrix` as one massive hub.

## Phase 6: Test Helper Architecture Cleanup

Goal: split broad test helpers into responsibility-focused modules.

CRG driver:

- `assert_state`: degree 458.
- `shutdown_integration`: degree 224.
- `wait_for_state`: degree 170.
- `get_basic_config_entry_data`: degree 164.
- `setup_mock_entities`: degree 109.

Target structure:

```text
tests/helpers/
  __init__.py
  assertions.py
  waits.py
  lifecycle.py
  config_entries.py
  entities.py
  services.py
  registries.py
```

Responsibilities:

- `assertions.py`: `assert_state`, `assert_attribute`, `assert_in_attribute`.
- `waits.py`: `wait_for_state`, `wait_until`, `wait_for_attribute`.
- `lifecycle.py`: init/shutdown/drain integration helpers.
- `config_entries.py`: config-entry builders and default data.
- `entities.py`: mock entity setup helpers.
- `services.py`: service mocks and logging helpers.
- `registries.py`: shared area/floor registry setup helpers. Keep
  scenario-specific device/entity registry mutations local unless repeated
  patterns justify a narrow helper.

Migration rules:

- Preserve backwards-compatible imports during first pass if practical.
- Move one helper family at a time.
- Do not change helper semantics while moving files.
- Prefer explicit test-local helpers over expanding global helpers.

Suggested order:

1. Extract assertions.
2. Extract waits.
3. Extract config-entry builders.
4. Extract lifecycle helpers.
5. Extract entity setup helpers.
6. Extract service helpers.
7. Audit remaining `tests/helpers.py` and convert to compatibility re-export or
   delete.

Validation:

```bash
./scripts/validate.sh
```

Exit criteria:

- Test helper responsibilities are clear.
- Scenario tests depend on scenario helpers, not broad platform setup helpers.
- Integration tests still pass.
- CRG helper hub degrees reduce.

## Phase 7: Manual Dead-Code Audit

Goal: remove genuinely unused code without deleting dynamic framework contracts.

CRG reported:

- 255 function candidates
- 39 class candidates

False-positive categories:

- Home Assistant entry points such as `async_setup_entry`, `async_unload_entry`,
  and `async_step_*`.
- Entity properties and HA service methods such as `state`, `available`,
  `device_info`, `supported_features`, and `native_value`.
- pytest fixtures.
- mocks implementing Home Assistant interfaces.
- feature module classes and methods dispatched through registries.
- callbacks/properties invoked by Home Assistant conventions.

Initial plausible audit targets:

- `AggregateKind`
- `ControlActionType`
- `ControlRuntimeEffectType`
- `ControlGroupPolicyId`
- `GroupMetadataKey`
- `FeatureRegistration`
- `IntentReason`
- `ControlTargetKind`
- `ControlTargetPrecision`
- `VirtualClock`

Audit process:

1. Search direct references with `rg`.
2. Search string/serialized references.
3. Check registry and HA callback conventions.
4. Decide remove/keep/document/test.
5. Remove only small proven groups.
6. Run validation after each batch.

Validation:

```bash
./scripts/validate.sh
```

Exit criteria:

- Only proven-dead symbols are removed.
- Framework contracts remain intact.
- Remaining retained candidates have rationale.

## Phase 8: Options-Flow Structural Follow-Up

Goal: reduce config-flow routing complexity after the behavior contract is
retired from temporary plan form.

CRG driver:

- `handle_feature_conf` remains a high-fan-out hotspot.

Current behavior to preserve:

- root menu topology
- incremental persistence
- guided-flow completion boundaries
- dormant light-mode settings
- fan automation submenu behavior
- climate preset mapping persistence boundary
- validation-error behavior
- frontend serializer compatibility

Possible target structure:

```text
custom_components/magic_areas/config_flows/steps/
  feature_config.py
  feature_pages/
    __init__.py
    simple_features.py
    light_groups.py
    fan_groups.py
    climate_control.py
    aggregates.py
    custom_control_groups.py
```

Suggested sequence:

1. Add tests around current `handle_feature_conf` routing if any route is weak.
2. Extract pure page builders by feature domain.
3. Extract persistence-boundary helpers.
4. Extract validation-error normalization.
5. Reduce `handle_feature_conf` to orchestration.
6. Keep translations/copy polish separate.

Validation:

```bash
./scripts/validate.sh
```

Exit criteria:

- `handle_feature_conf` fan-out is reduced.
- Domain form construction is testable in isolation.
- Existing options-flow behavior remains unchanged.
- No frontend serializer regressions.

Execution evidence from 2026-06-27:

- `handle_feature_conf` now delegates generic form validation/rendering to
  `feature_pages/generic.py`.
- Simple non-light selector overrides live in `feature_pages/simple.py`.
- Climate preset selection remains in `feature_pages/climate_control.py`.
- Fan-group submenu/controller routing remains in `feature_pages/fan_groups.py`.
- Light-group subpage schema/selector construction, hidden-field preservation,
  and Adaptive Lighting normalization live in `feature_pages/light_groups.py`.
- Focused options-flow validation passed:
  - `uv run ruff check custom_components/magic_areas/config_flows/steps`
  - `uv run mypy custom_components/magic_areas/config_flows/steps/feature_config.py custom_components/magic_areas/config_flows/steps/feature_pages/generic.py custom_components/magic_areas/config_flows/steps/feature_pages/climate_control.py custom_components/magic_areas/config_flows/steps/feature_pages/light_groups.py custom_components/magic_areas/config_flows/steps/feature_pages/fan_groups.py`
  - `uv run --extra test pytest tests/config_flow/test_feature_config.py tests/config_flow/test_feature_config_climate.py tests/config_flow/test_options_flow_routing.py -q`
- Full repository validation passed: `./scripts/validate.sh`; pytest reported
  1452 passed and 26 snapshots passed.

## Phase 9: Control Runtime Pattern Consolidation

Goal: reduce repeated runtime glue across fan, cover, light, climate, and media
control paths without creating an over-general automation framework.

Repeated patterns to inspect:

- control switch enabled/disabled gating
- policy input assembly
- configured state/action token parsing
- target entity/helper resolution
- service-call execution
- manual/hold/suppression state tracking
- debug attribute publication
- last-decision/last-reason recording

Potential extraction:

```text
custom_components/magic_areas/core/controls/runtime_support.py
```

Candidate contents:

- common enabled-switch gate helpers
- common target normalization helpers
- common hold-deadline state helpers
- common debug attribute builders
- shared policy execution result model
- shared service-call tracing helpers

Rules:

- Extract only patterns proven in at least two domains.
- Keep domain policy decisions domain-specific.
- Do not hide fan/cover/light semantics behind generic names.
- Preserve debug attributes or intentionally version changes.
- Validate all domains after each extraction.

Exit criteria:

- Domain-specific policy files are smaller and clearer.
- Runtime switch/platform files have less repeated glue.
- Control behavior remains unchanged.

## Phase 10: Future Live Simulation Expansion

Goal: expand live fake-house coverage after simulator modularization.

Fan coverage backlog:

- Explicit room-state odor fallback.
- Cooling fan occupancy path.
- Multiple physical fans with overlapping roles targeting different fans.
- Home Assistant reload/restart behavior.

Cover coverage backlog:

- Partial position and tilt behavior.
- Cover `opening` and `closing` movement states.
- Richer daylight/time-like policy context.
- Home Assistant reload/restart behavior.
- Membership/class reconciliation.

Cross-domain backlog:

- Combined fan/cover/light/adaptive active room.
- Cover-induced brightness affecting adaptive switching through fuller live
  fake-house pipeline.
- Real media-player state instead of accent stand-in.
- Helper/entity registry repair after removal, rename, or reclassification.

Config-flow/manual setup backlog:

- Keep Setup Room reserved for config-flow/manual setup validation.
- Add UI/manual validation instructions or automation for creating exact room
  configs.
- Do not use Setup Room in active simulation tests.

Rules:

- Add new live coverage only when simulator structure can support it.
- Every new live scenario states what real HA behavior it proves.
- Every new scenario uses named timing helpers.
- Durable simulation guidance is updated with coverage/gap changes.

Exit criteria:

- Future coverage is added without creating a new monolithic scenario hub.
- Setup Room remains excluded from active simulation.
- Live coverage gaps remain current.

## Phase 11: Documentation Consolidation

Goal: reduce plan-file sprawl after active plans are closed.

Temporary documents that can eventually be deleted:

- `docs/contributing/fan-cover-default-automation-plan.md`
- `docs/contributing/options-flow-cleanup-repair-plan.md`
- `docs/contributing/lighting-adaptive-switching-plan.md`, if completed behavior
  and deferred work are preserved elsewhere

Durable documents to keep:

- `CLAUDE.md`
- `docs/contributing/dev-simulation-guidance.md`
- architecture/runtime-boundary docs
- this master roadmap while active

Deletion checklist for any temporary plan:

1. Completed behavior is documented durably.
2. Remaining gaps are represented in this roadmap or durable guidance.
3. Validation evidence exists for closed behavior.
4. The plan contains no unique operational instructions.
5. User explicitly agrees the plan can be removed.

Exit criteria:

- Fewer active plan files.
- No loss of implementation knowledge.
- Future work is sequenced in one place.

## Ordered Work Breakdown

Use `x.y.z` IDs for tracking:

- `x`: work area
- `y`: subfocus
- `z`: individual step

The IDs below are the execution map for the roadmap. The detailed context for
each work area remains in the phase sections above.

### 0. Current Branch Stabilization

#### 0.1. Validation Baseline

- [x] `0.1.1` Run `./scripts/validate_basic.sh`.
- [x] `0.1.2` Run `./scripts/validate.sh`.
- [x] `0.1.3` Run `./scripts/ha_dev_bootstrap.sh --force-magic-area-options`.
- [x] `0.1.4` Run `./scripts/ha_dev_simulate.sh --scenario fan-cover-matrix`.
- [x] `0.1.5` Run `./scripts/ha_dev_simulate.sh --scenario control-matrix`.
- [x] `0.1.6` Record any validation failure as a blocker before structural work.

Validation assessment:

- `0.1.1`: complete. `./scripts/validate_basic.sh` passed on 2026-06-05; Ruff reported `All checks passed!` and mypy reported `Success: no issues found in 349 source files`.
- `0.1.2`: complete. `./scripts/validate.sh` passed on 2026-06-05; Ruff and mypy passed, and pytest reported `1405 passed in 41.18s`.
- `0.1.3`: complete. `./scripts/ha_dev_bootstrap.sh --force-magic-area-options` passed on 2026-06-05 and ended with `Home Assistant dev bootstrap complete`.
- `0.1.4`: complete. `/tmp/magic-areas-fan-cover-matrix.log` ends with evaluation/trace output, contains no failed-check/error markers, and its final checkpoints pass.
- `0.1.5`: complete. `/tmp/magic-areas-control-matrix.log` was produced by a run with `exit=0`, ends with evaluation/trace output, and contains no failed-check/error markers.
- `0.1.6`: complete. No validation failure was found while processing `0.1.1` through `0.1.5`, so there is no blocker to record before the next closeout step.

#### 0.2. Branch Scope Protection

- [x] `0.2.1` Avoid broad simulator refactors until fan/cover closure is complete.
- [x] `0.2.2` Avoid test-helper refactors until fan/cover closure is complete.
- [x] `0.2.3` Avoid dead-code deletion until fan/cover closure is complete.
- [x] `0.2.4` Avoid options-flow routing refactors until fan/cover closure is complete.
- [x] `0.2.5` Keep Setup Room reserved for config-flow/manual setup validation only.

Scope assessment:

- `0.2.1`: complete for this pass. No simulator modularization/refactor was started before fan/cover validation closeout; only validation and roadmap status edits were made.
- `0.2.2`: complete for this pass. No test-helper refactor was started.
- `0.2.3`: complete for this pass. No dead-code deletion was started.
- `0.2.4`: complete for this pass. No options-flow routing refactor was started.
- `0.2.5`: complete. Setup Room appears in fake-house seed/reset state and durable documentation as a setup/manual validation room, while active simulation checkpoints use Living Room, control-matrix rooms, Fan Room, Cover Room, and adaptive rooms.

#### 0.3. Temporary Repair Cleanup

- [x] `0.3.1` Confirm temporary simulator repair document is removed.
- [x] `0.3.2` Confirm simulator timing rules live in durable simulation guidance.
- [x] `0.3.3` Confirm no remaining temporary repair item exists only in deleted documentation.

Repair cleanup assessment:

- `0.3.1`: complete. `rg --files docs/contributing | rg 'simulator-repair|repair-standard|dev-simulator-repair'` returns no temporary simulator repair document.
- `0.3.2`: complete. `docs/contributing/dev-simulation-guidance.md` preserves the default 30-second cycle, real elapsed-time behavior waits, and the successful default-cycle `fan-cover-matrix` guidance.
- `0.3.3`: complete. The durable simulation guidance and this roadmap preserve the simulator timing rules, Setup Room exclusion, current live coverage, and future simulation gaps; no remaining repair topic was found only in a temporary repair document.

#### 0.4. Phase Exit Validation

- [x] `0.4.1` Run `./scripts/validate.sh` after Phase 0 work is complete.

Phase 0 exit validation:

- `0.4.1`: complete. The Phase 0 full validation run passed Ruff, mypy across
  349 source files, and `1405` pytest tests.

### 1. Fan/Cover Branch Closure

#### 1.1. Fan Behavior Closure

- [x] `1.1.1` Verify cooling threshold activation and hysteresis clear remain covered.
- [x] `1.1.2` Verify humidity threshold-only mode remains covered.
- [x] `1.1.3` Verify humidity threshold+trend mode remains covered.
- [x] `1.1.4` Verify managed Trend helper creation and consumption remain covered.
- [x] `1.1.5` Verify VOC/odor sensor mode remains covered.
- [x] `1.1.6` Verify explicit room-state odor fallback remains documented as implemented at lower test layers but not live-simulated.
- [x] `1.1.7` Verify overlapping humidity/odor reasons keep the shared fan on until both reasons clear.
- [x] `1.1.8` Verify suppression states block only the configured fan reason.
- [x] `1.1.9` Verify fan-derived area states `humid`, `odor`, and `hot` remain covered.
- [x] `1.1.10` Verify fan on/off state alone does not create false room-condition states.

Fan behavior assessment:

- `1.1.1`: complete. `test_cooling_controller_activates_above_threshold` and `test_controller_clears_below_hysteresis_clear_threshold` cover activation and hysteresis clear.
- `1.1.2`: complete. Threshold-only humidity behavior is covered by fan policy tests and `test_run_logic_uses_persisted_role_controller_sensors_and_members`.
- `1.1.3`: complete. Threshold+trend activation and below-clear-band rejection are covered in `tests/unit/test_fan_controller_policy.py`.
- `1.1.4`: complete. Managed Trend helper construction is covered by `test_fan_groups_module_declares_threshold_trend_signal_surface`; runtime consumption is covered by `test_run_logic_uses_threshold_trend_signal_state`; the live log passes `humidity trend helper activates fan inside hysteresis band`.
- `1.1.5`: complete. VOC/odor threshold mode is covered by policy/runtime tests and the live VOC overlap, unavailable, restore, and clear checkpoints.
- `1.1.6`: complete. Explicit room-state odor fallback is covered by `test_odor_controller_can_use_room_state_fallback_without_sensor`, `test_room_state_fallback_clears_when_required_state_is_absent`, and `test_run_logic_supports_sensorless_odor_room_state_fallback`; this roadmap records that it is not live-simulated.
- `1.1.7`: complete. `test_shared_fan_stays_on_until_all_reasons_clear` and the live `voc odor keeps shared fan after humidity clears` checkpoint cover shared-fan overlap.
- `1.1.8`: complete. `test_suppression_applies_to_only_matching_controller` covers per-controller suppression; the live sleep checkpoint proves humidity suppression.
- `1.1.9`: complete. Fan runtime role mapping publishes `humid`, `odor`, and `hot`; runtime publication and presence-state projection/clear tests cover the visible area-state path, and live humidity/odor checkpoints assert the corresponding states.
- `1.1.10`: complete. Added `test_fan_on_without_active_reason_publishes_no_room_condition_state`, proving a physically on fan publishes no fan-derived room state when no controller reason is active.

Targeted verification on 2026-06-05:

- `uv run --extra dev --extra test pytest tests/unit/test_fan_controller_policy.py tests/unit/test_fan_control_switch.py tests/unit/test_feature_module_contracts_control_groups.py tests/unit/test_presence_write_contracts.py -q`
- Result: `59 passed in 1.58s`.

#### 1.2. Fan Timer And Unavailable Closure

- [x] `1.2.1` Verify `post_clear_hold` policy/runtime tests pass.
- [x] `1.2.2` Verify live `post_clear_hold` waits the real seeded clear window.
- [x] `1.2.3` Verify live `post_clear_hold` waits configured post-clear hold duration.
- [x] `1.2.4` Verify `hold_then_clear` unavailable behavior is covered at unit and live levels.
- [x] `1.2.5` Verify `hold_until_restored` unavailable behavior is live-covered for VOC/odor.
- [x] `1.2.6` Verify held fan reasons do not turn off a fan still needed by another active reason.
- [x] `1.2.7` Verify debug attributes expose active, held, unavailable, suppressed, and cleared reasons.

Fan timer/unavailable assessment:

- `1.2.1`: complete. Fan policy tests cover post-clear activation, expiry, state-gate restoration, and runtime adapter propagation.
- `1.2.2`: complete. The live scenario waits for the area to reach `clear` using `configured_minutes_timeout(FAN_ROOM_CLEAR_TIMEOUT_MINUTES)` where the seeded clear timeout is one minute; it does not substitute checkpoint settling for the clear timer.
- `1.2.3`: complete. The live scenario calls `wait_configured_seconds(FAN_ROOM_HUMIDITY_HOLD_SECONDS)` before asserting expiry; the configured hold is four seconds.
- `1.2.4`: complete. Policy tests cover hold, expiry, and sensor recovery for `hold_then_clear`; live checkpoints pass `humidity unavailable hold keeps fan briefly` and `humidity unavailable hold expires and clears fan`.
- `1.2.5`: complete. Live checkpoints pass `voc unavailable holds odor fan until restored` and `voc restored clears held odor fan`.
- `1.2.6`: complete. Per-controller unavailable handling and shared-fan overlap tests ensure one reason cannot turn off a fan required by another; the live humidity/odor overlap keeps the fan on while odor remains.
- `1.2.7`: complete. Runtime attributes expose active, suppressed, inactive/cleared, post-clear hold, unavailable hold, and target-fan fields. The debug-attribute test now asserts both hold categories explicitly.

Targeted verification on 2026-06-05:

- `uv run --extra dev --extra test pytest tests/unit/test_fan_controller_policy.py tests/unit/test_fan_control_switch.py -q`
- Result: `38 passed in 1.18s`.

#### 1.3. Fan Config-Flow Closure

- [x] `1.3.1` Verify Fan automation submenu exposes Cooling, Humidity, and Odor.
- [x] `1.3.2` Verify controller pages use appropriate selectors.
- [x] `1.3.3` Verify the same fan can be selected in multiple controller roles.
- [x] `1.3.4` Verify existing single fan config reopens as Cooling settings.
- [x] `1.3.5` Verify each controller page persists independently.
- [x] `1.3.6` Verify invalid fan values remain on the form and do not persist.

Fan config-flow assessment:

- `1.3.1`: complete. Options-flow topology and translation tests assert the Fan automation submenu contains Cooling, Humidity, and Odor.
- `1.3.2`: complete. `test_options_flow_fan_groups_uses_constrained_selectors` asserts fan member, state, threshold, unavailable-behavior, and detection-mode selectors.
- `1.3.3`: complete after strengthening `test_options_flow_fan_groups_stores_independent_controller_roles`; it now saves the same fan under Humidity and Odor.
- `1.3.4`: complete. `test_options_flow_fan_groups_reopen_preserves_saved_values` proves the legacy/default Cooling page reopens with saved values.
- `1.3.5`: complete after strengthening the independent-role test; saving Odor preserves the previously saved Humidity controller unchanged.
- `1.3.6`: complete. Fan form validation preserves submitted values when validation reaches the integration handler. Home Assistant schema validation rejects selector-invalid values before the handler, keeps the same flow active for correction, and does not persist the invalid submission; the test proves a corrected submission succeeds through the same flow.

Targeted verification on 2026-06-05:

- `uv run --extra dev --extra test pytest tests/config_flow/test_config_flow_features_e2e.py tests/config_flow/test_options_flow_translations.py -q -k 'fan_groups or fan_automation'`
- Result: `8 passed, 74 deselected in 1.26s`.

#### 1.4. Cover Behavior Closure

- [x] `1.4.1` Verify cover preset config saves and reopens.
- [x] `1.4.2` Verify eligible cover classes are selected for default automation.
- [x] `1.4.3` Verify excluded cover classes remain helper/control surfaces only.
- [x] `1.4.4` Verify Daylight open respects runtime dark/daylight context.
- [x] `1.4.5` Verify Privacy/Sleep wins over Daylight.
- [x] `1.4.6` Verify Media/Accent wins over Daylight while active.
- [x] `1.4.7` Verify Media/Accent release can reopen only when configured and context-allowed.
- [x] `1.4.8` Verify cover policy emits no light service calls.
- [x] `1.4.9` Verify cover opening can support adaptive light-off through brightness context.
- [x] `1.4.10` Verify cover closing can support light-on through brightness context.

Cover behavior assessment:

- `1.4.1`: complete. `test_options_flow_cover_groups_stores_presets_and_reopens` covers preset and manual-hold persistence/reopen.
- `1.4.2`: complete. The live Daylight checkpoint opens blind, shade, curtain, shutter, and window classes.
- `1.4.3`: complete. The same live checkpoints keep garage and door covers closed while their helper surfaces remain present.
- `1.4.4`: complete. Policy and scenario tests block Daylight open when runtime daylight context is invalid; the live dark-occupied checkpoint keeps covers closed.
- `1.4.5`: complete. Privacy policy/scenario tests and the live sleep checkpoint close covers despite Daylight eligibility.
- `1.4.6`: complete. Accent policy tests and the live accent checkpoint close eligible covers.
- `1.4.7`: complete. Accent-release policy coverage restores Daylight only when configured/context-allowed; live Daylight release reopens in bright context and does not reopen in dark context.
- `1.4.8`: complete. Cover decisions target cover helpers only; cover policy tests contain no light target/action path.
- `1.4.9`: complete. `test_cover_opening_can_support_adaptive_light_off` proves cover-driven brightness context can support adaptive light-off without direct light calls from cover policy.
- `1.4.10`: complete. `test_cover_closing_can_support_occupied_dark_light_on` proves cover-driven dark context can support light-on through light policy.

#### 1.5. Cover Manual Hold Closure

- [x] `1.5.1` Verify manual cover movement is not immediately reversed.
- [x] `1.5.2` Verify manual hold is scoped to changed helper/group/member set.
- [x] `1.5.3` Verify manual hold expiry schedules policy reevaluation.
- [x] `1.5.4` Verify blind and shade simultaneous manual holds remain scoped.
- [x] `1.5.5` Verify disabled cover-control switch blocks automatic movement.

Cover manual-hold assessment:

- `1.5.1`: complete. Unit/scenario coverage and the live `manual blind close not immediately reversed` checkpoint prove the hold.
- `1.5.2`: complete. Policy/runtime tests skip only held helpers; the live blind hold leaves shade, curtain, shutter, and window open.
- `1.5.3`: complete. Runtime tests assert unexpected movement schedules the next hold-expiry check, and the live expiry checkpoint proves reevaluation reopens the held blind.
- `1.5.4`: complete. Live simultaneous blind/shade checkpoints prove only those groups are held and both reopen after expiry.
- `1.5.5`: complete. The live disabled-controls checkpoint keeps all eligible and excluded covers stationary while the cover-control switch is off.

Targeted verification on 2026-06-05:

- `uv run --extra dev --extra test pytest tests/unit/test_cover_control_policy.py tests/scenarios/test_cover_automation.py tests/config_flow/test_config_flow_features_e2e.py -q -k 'cover'`
- Result: `18 passed, 70 deselected in 1.39s`.

#### 1.6. Fan/Cover Future Gap Preservation

- [x] `1.6.1` Preserve explicit room-state odor fallback live simulation as future work.
- [x] `1.6.2` Preserve fan reload/restart behavior as future work.
- [x] `1.6.3` Preserve multiple physical fans with overlapping roles as future work.
- [x] `1.6.4` Preserve cover partial position/tilt as future work.
- [x] `1.6.5` Preserve cover `opening`/`closing` movement states as future work.
- [x] `1.6.6` Preserve richer daylight/time-like cover context as future work.
- [x] `1.6.7` Preserve cover reload/restart behavior as future work.
- [x] `1.6.8` Preserve cover membership/class reconciliation as future work.
- [x] `1.6.9` Preserve combined fan/cover/light/adaptive active-room coverage as future work.
- [x] `1.6.10` Preserve real media-player signal coverage as future work.
- [x] `1.6.11` Preserve config-flow UI automation for exact fan/cover room creation as future work.
- [x] `1.6.12` Preserve helper/entity registry repair scenarios as future work.

Future-gap assessment:

- `1.6.1` through `1.6.12`: complete as preservation tasks. Each gap remains explicitly listed in the Phase 1 open-gap sections and/or Phase 10 future live simulation backlog; none was silently treated as implemented.

#### 1.7. Fan/Cover Plan Retirement

- [x] `1.7.1` Confirm completed behavior is documented outside the temporary plan.
- [x] `1.7.2` Confirm future gaps are represented in this roadmap or durable guidance.
- [x] `1.7.3` Confirm validation evidence exists for closed behavior.
- [x] `1.7.4` Delete or retire the temporary fan/cover plan only after explicit user agreement.

Plan-retirement assessment:

- `1.7.1`: complete. The fan/cover behavior model, completed behavior, live coverage, and evidence maps are contained in this roadmap.
- `1.7.2`: complete. Future fan/cover gaps are explicitly preserved in `1.6`, the Phase 1 open-gap sections, and Phase 10.
- `1.7.3`: complete. Fresh full validation after the Phase 1 fixes passed Ruff, mypy across 349 source files, and `1407` pytest tests in `39.71s`.
- `1.7.4`: complete. The user approved retirement and `docs/contributing/fan-cover-default-automation-plan.md` was deleted; this master roadmap is now the planning source for that work.

#### 1.8. Phase Exit Validation

- [x] `1.8.1` Run `./scripts/validate.sh` after Phase 1 work is complete.

Phase 1 exit validation:

- `1.8.1`: complete. The final Phase 1 run passed Ruff, mypy across 349 source
  files, and `1407` pytest tests in `39.71s`. The only subsequent Phase 1 change
  was deletion of the approved temporary Markdown plan.

### 2. Options-Flow Plan Retirement

#### 2.1. Navigation Contract Preservation

- [x] `2.1.1` Preserve direct root entries for Area behavior, Presence tracking, Area states, and Custom control groups.
- [x] `2.1.2` Preserve direct root entries for Health, Aggregate sensors, Presence hold, BLE tracker monitoring, Wasp in a Box, and Area-aware media player.
- [x] `2.1.3` Preserve intentional submenus for Light roles and automation, Fan automation, and Climate automation.
- [x] `2.1.4` Preserve absence of root Done/Save/Finish action.

Navigation assessment:

- `2.1.1` through `2.1.4`: complete. A focused run across the incremental
  persistence, translation, end-to-end feature, and options-flow integration
  suites passed `22` tests. The exercised contracts cover direct root forms,
  intentional Light/Fan/Climate submenus, root-menu ordering, and the absence
  of a final Done, Save, or Finish operation.

#### 2.2. Persistence Contract Preservation

- [x] `2.2.1` Preserve complete-page immediate persistence.
- [x] `2.2.2` Preserve close/discard behavior for only the current unsubmitted page.
- [x] `2.2.3` Preserve feature-selection immediate persistence and root refresh.
- [x] `2.2.4` Preserve Light role submit returning to Light submenu.
- [x] `2.2.5` Preserve Classic brightness immediate persistence.
- [x] `2.2.6` Preserve Advisory/Adaptive persistence after mode-specific submit.
- [x] `2.2.7` Preserve dormant brightness-mode settings.
- [x] `2.2.8` Preserve Adaptive Lighting ignore/adopt/manage completion boundaries.
- [x] `2.2.9` Preserve Climate preset mapping as the persistence boundary.
- [x] `2.2.10` Preserve invalid-submit behavior and error visibility.
- [x] `2.2.11` Preserve custom control group submitted records after validation errors.

Persistence assessment:

- `2.2.1` through `2.2.11`: complete. A focused run of the incremental
  persistence and end-to-end feature suites passed `52` tests. The run covered
  complete-page saves, later-flow abandonment, feature-selection refresh,
  Light submenu returns and mode boundaries, dormant settings, Adaptive
  Lighting ignore/adopt/manage boundaries, Climate preset mapping, invalid
  submissions, and preservation of submitted custom-control records.

#### 2.3. Options-Flow Evidence Preservation

- [x] `2.3.1` Preserve test coverage list in durable documentation.
- [x] `2.3.2` Preserve manual validation findings in durable documentation.
- [x] `2.3.3` Preserve deferred copy polish as non-blocking future work.
- [x] `2.3.4` Confirm options-flow tests pass before retiring temporary plan.

Evidence-preservation assessment:

- `2.3.1`: complete. The durable Phase 2 contract retains the full options-flow
  regression coverage list from the temporary repair plan.
- `2.3.2`: complete. The durable Phase 2 contract retains the Home Assistant
  manual-validation findings and the behavior each UI path demonstrated. A
  fresh forced options bootstrap, authenticated frontend render, and clean
  Home Assistant error-log scan were completed on 2026-06-06.
- `2.3.3`: complete. Bulk menu and description copy polish remains explicitly
  deferred and non-blocking.
- `2.3.4`: complete. The full `tests/config_flow` suite passed `223` tests in
  `7.96s`.

#### 2.4. Options-Flow Plan Retirement

- [x] `2.4.1` Confirm temporary options-flow plan has no unique operational knowledge.
- [x] `2.4.2` Delete or retire temporary options-flow plan only after explicit user agreement.

Plan-retirement assessment:

- `2.4.1`: complete. The temporary plan's navigation and persistence contracts,
  implementation summary, regression coverage, Home Assistant manual findings,
  serializer result, deferred copy work, and closure rules are retained in this
  roadmap. Its remaining content is status and retirement metadata rather than
  unique operational knowledge.
- `2.4.2`: complete. The user approved continuing with the roadmap after the
  final three contextual details were transferred, and
  `docs/contributing/options-flow-cleanup-repair-plan.md` was deleted.

#### 2.5. Phase Exit Validation

- [x] `2.5.1` Run `./scripts/validate.sh` after Phase 2 work is complete.

Phase 2 exit validation:

- `2.5.1`: complete. The final Phase 2 run passed Ruff, mypy across `349`
  source files, and `1407` pytest tests in `40.50s`. The only remaining Phase 2
  operation is the explicitly gated, documentation-only retirement in `2.4.2`;
  under the phase-exit rule, that deletion does not require repeating Python
  validation.

### 3. Simulation Guidance Consolidation

#### 3.1. Real-Time Rule Preservation

- [x] `3.1.1` Preserve default 30-second cycle rule.
- [x] `3.1.2` Preserve real elapsed time for minute-based Magic Areas timers.
- [x] `3.1.3` Preserve separation between immediate propagation waits and behavior waits.
- [x] `3.1.4` Preserve prohibition on `checkpoint_settle_seconds` as timer shortcut.
- [x] `3.1.5` Preserve Setup Room exclusion from active simulation scenarios.

Real-time rule assessment:

- `3.1.1`: complete. The CLI default remains `30` seconds and the durable
  simulation guidance now states that requirement explicitly.
- `3.1.2`: complete. `SimulationTiming.seeded_minute_seconds` derives configured
  minute timing from `cycle_seconds * state_period_cycles`; seeded defaults use
  two complete cycles per configured minute.
- `3.1.3`: complete. `settle_setup`, `settle_checkpoint`, and
  `settle_immediate_guard` are distinct from `wait_configured_minutes` and
  `wait_configured_seconds`.
- `3.1.4`: complete. Durable guidance now prohibits checkpoint settling as a
  shortcut for behavioral timers; code uses it only for immediate propagation
  or as an additive polling margin.
- `3.1.5`: complete. Setup Room references in the simulator are confined to
  baseline fake-state reset. No active scenario checkpoint or trace contract
  uses Setup Room, and durable guidance now excludes it from the active room
  matrix.

#### 3.2. Current Live Coverage Preservation

- [x] `3.2.1` Preserve light control-matrix coverage.
- [x] `3.2.2` Preserve disabled light-control switch coverage.
- [x] `3.2.3` Preserve adaptive-negative-context coverage.
- [x] `3.2.4` Preserve manual override and reclaim coverage.
- [x] `3.2.5` Preserve presence-hold coverage.
- [x] `3.2.6` Preserve Adaptive Lighting manual-control release coverage.
- [x] `3.2.7` Preserve Fan Room coverage.
- [x] `3.2.8` Preserve Cover Room coverage.

Live-coverage assessment:

- `3.2.1`: complete. `control_matrix` retains dark/bright, classic, advisory,
  adaptive, contamination, accent, sleep, clear, native-group, and managed
  Adaptive Lighting checkpoints. Its retained live log ends successfully.
- `3.2.2`: complete. `disabled_light_controls` asserts occupied room state while
  configured member lights and native groups remain off.
- `3.2.3`: complete. `adaptive_negative_context` asserts outside-binary,
  outside-lux minimum, and outside-lux contrast negative gates.
- `3.2.4`: complete. `manual_override` asserts manual release, blocked
  reacquisition during state churn, clear reset, and re-occupancy reclaim.
- `3.2.5`: complete. `presence_hold` asserts independent occupancy and later
  configured clear after the hold is released.
- `3.2.6`: complete. `adaptive_lighting_manual_release` observes the real
  `adaptive_lighting.set_manual_control` release event after room clear.
- `3.2.7`: complete. `fan_cover_matrix` retains Fan Room threshold, trend,
  overlap, suppression, unavailable-sensor, and real-time hold checkpoints.
- `3.2.8`: complete. `fan_cover_matrix` retains Cover Room daylight, privacy,
  accent, dark-context, eligibility, disabled-control, and scoped manual-hold
  checkpoints. Its retained live log ends successfully.

Only `control-matrix` and `fan-cover-matrix` have retained fresh run logs at this
checkpoint. The other items above are preservation findings from executable
scenario checkpoints and durable guidance, not claims that every scenario was
rerun during Phase 3.

#### 3.3. Simulation Gap Preservation

- [x] `3.3.1` Preserve extended-state direct coverage gap.
- [x] `3.3.2` Preserve manual override release without room clear gap.
- [x] `3.3.3` Preserve Adaptive Lighting `adopt_existing` live gap.
- [x] `3.3.4` Preserve AL brightness-change false-positive live gap.
- [x] `3.3.5` Preserve neighboring/spill-over light false-positive gap.
- [x] `3.3.6` Preserve media and future control-domain overlap gaps.
- [x] `3.3.7` Preserve config-flow/frontend automation gap.
- [x] `3.3.8` Preserve helper/entity reconciliation live gap.

Simulation-gap assessment:

- `3.3.1` through `3.3.8`: complete. Each gap remains explicitly listed in
  `docs/contributing/dev-simulation-guidance.md`, including the reason manual
  override release without room clear is not currently covered and the boundary
  between fake-house simulation and config-flow/frontend validation.

#### 3.4. Phase Exit Validation

- [x] `3.4.1` Run `./scripts/validate.sh` after Phase 3 work is complete.

Phase 3 exit validation:

- `3.4.1`: complete. The final Phase 3 run passed Ruff, mypy across `349`
  source files, and `1407` pytest tests in `46.44s`.

### 4. Adaptive Switching Consolidation

#### 4.1. Completed Adaptive Behavior Preservation

- [x] `4.1.1` Preserve `inhibit`, `advisory`, and `adaptive` modes.
- [x] `4.1.2` Preserve default `inhibit` behavior.
- [x] `4.1.3` Preserve min-on, dwell, attribution, outside-context, inside-bright, and ambient-rise guard derivation.
- [x] `4.1.4` Preserve managed Trend helper preference.
- [x] `4.1.5` Preserve transitional in-runtime detector fallback.
- [x] `4.1.6` Preserve light config/options-flow adaptive settings.
- [x] `4.1.7` Preserve migration/backfill behavior.
- [x] `4.1.8` Preserve in-room direct-light attribution across all configured roles.
- [x] `4.1.9` Preserve contaminated and clean ambient-rise live behavior.

Completed adaptive-behavior assessment:

- `4.1.1` through `4.1.8`: complete. A focused policy, runtime, helper,
  config-flow, migration, Adaptive Lighting, and scenario suite passed `222`
  tests in `8.05s`.
- `4.1.9`: complete. The executable `control_matrix` retains contaminated
  Magic Areas output, manual configured-light contamination, and later clean
  ambient-rise checkpoints; its retained live log completed successfully.

#### 4.2. Deferred Adaptive Work Preservation

- [x] `4.2.1` Preserve user-configured spill-over attribution as future work.
- [x] `4.2.2` Preserve derivative/statistics helper bundles as future work.
- [x] `4.2.3` Preserve live AL brightness-change false-positive coverage as future work.
- [x] `4.2.4` Preserve cover-derived brightness debug context decision as future work.

Deferred adaptive-work assessment:

- `4.2.1` through `4.2.4`: complete. The roadmap retains each deferred item,
  including why spill-over attribution must be explicitly user-configured and
  why generic Trend evidence cannot establish the source of a lux rise.

#### 4.3. Adaptive Plan Retirement

- [x] `4.3.1` Confirm completed adaptive behavior is documented durably.
- [x] `4.3.2` Confirm deferred adaptive work is represented in this roadmap.
- [x] `4.3.3` Delete or retire adaptive plan only after explicit user agreement.

Adaptive-plan retirement assessment:

- `4.3.1`: complete. The roadmap now retains the problem statement, constraints,
  signal/policy boundary, fallback matrix, observability contract, risks,
  completed implementation, and evidence map.
- `4.3.2`: complete. Spill-over attribution, richer helper bundles, live
  Adaptive Lighting brightness-change coverage, and optional cover-derived
  brightness debug context remain explicit future work.
- `4.3.3`: complete. The user approved continuing after the adaptive plan's
  unique design context was transferred, and
  `docs/contributing/lighting-adaptive-switching-plan.md` was deleted.

#### 4.4. Phase Exit Validation

- [x] `4.4.1` Run `./scripts/validate.sh` after Phase 4 work is complete.

Phase 4 exit validation:

- `4.4.1`: complete. The final Phase 4 run passed Ruff, mypy across `349`
  source files, and `1407` pytest tests in `51.04s`. The only remaining Phase 4
  operation is the explicitly gated, documentation-only retirement in `4.3.3`.

### 5. Simulator Modularization

#### 5.1. Preparation

- [x] `5.1.1` Rebuild CRG before starting simulator modularization.
- [x] `5.1.2` Confirm default `fan-cover-matrix` passes.
- [x] `5.1.3` Confirm default `control-matrix` passes.
- [x] `5.1.4` Identify all public CLI and wrapper compatibility requirements.

Simulator preparation assessment:

- `5.1.1`: complete. The full rebuild exceeded the CRG tool's response window,
  so a successful incremental update reparsed `64` changed/dependent files with
  full post-processing. Current CRG still reports `fan_cover_matrix` degree
  `221`, `ExpectedState` degree `168`, and `control_matrix` degree `104`.
- `5.1.2`: complete. The default real-time `fan-cover-matrix` run completed
  successfully, all emitted checks passed, and its failure scan found no failed
  checks, simulator failure, traceback, error, or exception markers. Evidence is
  retained in `/tmp/magic-areas-phase5-fan-cover.log`.
- `5.1.3`: complete. The default real-time `control-matrix` run completed
  successfully, all emitted checks passed, and its failure scan found no failed
  checks, simulator failure, traceback, error, or exception markers. Evidence is
  retained in `/tmp/magic-areas-phase5-control-matrix.log`.
- `5.1.4`: complete. Preserve `./scripts/ha_dev_simulate.sh`,
  `python -m scripts.ha_dev_simulate`, all current CLI option names, defaults,
  scenario choices, repeatable `--trace-entity` behavior, trace/evaluation and
  config-entry paths, process exit codes, and actionable error output. No
  production or test module imports simulator internals, so
  `scripts/ha_dev_simulate.py` can remain the compatibility entrypoint while
  implementation concerns move behind it.

#### 5.2. Module Extraction

- [x] `5.2.1` Extract constants and passive dataclasses.
- [x] `5.2.2` Extract HA websocket/service/state helpers.
- [x] `5.2.3` Extract timing helpers.
- [x] `5.2.4` Extract `ExpectedState` and evaluation helpers.
- [x] `5.2.5` Extract trace/checkpoint output helpers.
- [x] `5.2.6` Extract preflight validation.
- [x] `5.2.7` Extract fan-cover scenario.
- [x] `5.2.8` Extract light/control-matrix scenario.
- [x] `5.2.9` Extract living-room schedule scenario.
- [x] `5.2.10` Reduce `ha_dev_simulate.py` to CLI compatibility wrapper.

Simulator extraction progress:

- `5.2.1`: complete. Simulator defaults, stable entity sets, expected seeded
  room options, and the unchanged passive trace/evaluation dataclasses now live
  in `scripts/ha_dev_simulation/entities.py` and
  `scripts/ha_dev_simulation/models.py`. The compatibility module imports those
  definitions without changing their constructor or field contracts. The
  extraction batch passed `./scripts/validate_basic.sh`: Ruff passed and mypy
  found no issues across `352` source files.
- `5.2.2`: complete. HA state reads, generic service calls, typed input/switch/
  light setters, single-state polling, and call-service event listening now live
  in `scripts/ha_dev_simulation/client.py` with unchanged signatures and
  behavior. The extraction batch passed `./scripts/validate_basic.sh`: Ruff
  passed and mypy found no issues across `353` source files.
- `5.2.3`: complete. The unchanged real-time `SimulationTiming` contract now
  lives in `scripts/ha_dev_simulation/timing.py`, including the 30-second-cycle
  minute conversion, propagation settles, runtime polling, and configured hold
  waits. The extraction batch passed `./scripts/validate_basic.sh`: Ruff passed
  and mypy found no issues across `354` source files.
- `5.2.4`: complete. Expectation matching, checkpoint collection and JSON
  output, and multi-state polling now live in
  `scripts/ha_dev_simulation/expectations.py`. The extraction batch passed
  `./scripts/validate_basic.sh`: Ruff passed and mypy found no issues across
  `355` source files.
- `5.2.5`: complete. Trace entity selection, room-derived trace lists, and the
  state-change recorder now live in `scripts/ha_dev_simulation/traces.py`; the
  checkpoint-output half of this boundary remains colocated with evaluation.
  The extraction batch passed `./scripts/validate_basic.sh`: Ruff passed and
  mypy found no issues across `356` source files.
- `5.2.6`: complete. Config-entry storage loading, subset comparison, and the
  Fan Room/Cover Room option contract now live in
  `scripts/ha_dev_simulation/preflight.py`. The support/scenario extraction
  batch passed `./scripts/validate_basic.sh`: Ruff passed and mypy found no
  issues across `359` source files.
- `5.2.7`: complete. The unchanged live fan/cover event and checkpoint sequence
  now lives in `scripts/ha_dev_simulation/scenarios/fan_cover.py`; shared
  fake-house reset and input driving live in
  `scripts/ha_dev_simulation/reset.py`. The same batch passed basic validation,
  then the default real-time `fan-cover-matrix` completed in `213s` with exit
  code `0`, all emitted checks passing, and no failure markers in
  `/tmp/magic-areas-phase5-extracted-fan-cover.log`.
- `5.2.8`: complete. The control-matrix expectation builders, reset, main
  matrix, and related light-control scenarios now live in
  `scripts/ha_dev_simulation/scenarios/lights.py`. The batch passed
  `./scripts/validate_basic.sh` with mypy clean across `360` source files, then
  the default real-time `control-matrix` completed in `232s` with exit code `0`,
  all emitted checks passing, and no failure markers in
  `/tmp/magic-areas-phase5-extracted-control-matrix.log`.
- `5.2.9`: complete. The living-room wall-clock schedule and display helpers now
  live in `scripts/ha_dev_simulation/scenarios/living_room.py`. The extraction batch
  passed `./scripts/validate_basic.sh`: Ruff passed and mypy found no issues
  across `361` source files.
- `5.2.10`: complete. Public argument parsing and `main()` now live in
  `scripts/ha_dev_simulation/cli.py`; connection, tracing, and scenario
  dispatch live in `scripts/ha_dev_simulation/runner.py`.
  `scripts/ha_dev_simulate.py` remains a compatibility wrapper that re-exports
  `main`, `parse_args`, and `simulate`, and `python -m scripts.ha_dev_simulate`
  still works. The final basic run passed `./scripts/validate_basic.sh`: Ruff
  passed and mypy found no issues across `365` source files.

#### 5.3. Simulator Validation

- [x] `5.3.1` Run `./scripts/validate_basic.sh` after each extraction batch.
- [x] `5.3.2` Run default `fan-cover-matrix` after scenario extraction and final structural changes.
- [x] `5.3.3` Run default `control-matrix` after scenario extraction and final structural changes.
- [x] `5.3.4` Run `./scripts/validate.sh` at phase exit.
- [x] `5.3.5` Rebuild CRG and confirm `fan_cover_matrix` hub pressure is reduced.
- [x] `5.3.6` Add direct characterization tests for extracted simulator contracts.
- [x] `5.3.7` Run every public scenario with default real-time arguments.

Simulator validation progress:

- `5.3.1`: complete. Every extraction batch through the final runner/CLI split
  passed `./scripts/validate_basic.sh`; the final basic run reported Ruff clean
  and mypy clean across `365` source files.
- `5.3.2`: complete. The original per-intermediate-batch wording was not
  followed and could not be reconstructed after the fact. Corrective validation
  reran the default real-time `fan-cover-matrix` after the final package layout,
  direct tests, and orchestration split; it exited `0` with no failure markers
  in `/tmp/magic-areas-phase5-corrective-fan-cover-matrix.log`.
- `5.3.3`: complete. The original per-intermediate-batch wording was not
  followed and could not be reconstructed after the fact. Corrective validation
  reran the default real-time `control-matrix` after the final package layout
  and direct tests; it exited `0` with no failure markers in
  `/tmp/magic-areas-phase5-corrective-control-matrix.log`.
- `5.3.4`: complete. The final corrective Phase 5 `./scripts/validate.sh`
  passed Ruff, mypy across `365` source files, and `1415` pytest tests in
  `42.56s`.
- `5.3.5`: complete. A fresh full CRG build indexed `377` files, `3551` nodes,
  and `27657` edges. Before the phase split, `fan_cover_matrix` was a degree
  `221` top-three hub. After splitting orchestration into ordered behavioral
  phases under `scripts/ha_dev_simulation/scenarios/fan_cover.py`, it is a
  10-line dispatcher outside the top 25 hubs; the largest delegated phase is
  `_run_fan_controller_checks` at degree `95`.
- `5.3.6`: complete. `tests/unit/test_ha_dev_simulation_modules.py` directly
  covers parser defaults and repeatable options, trace selection, state
  decoding, expectation matching, real-time timing calculations, seeded option
  preflight, intentional Setup Room reset coverage, wrapper/module help
  equivalence, and CLI error behavior. The focused suite passed `8` tests with
  Ruff and mypy clean.
- `5.3.7`: complete. Corrective default-argument live runs passed for all eight
  public scenarios: `living-room-demo`, `control-matrix`,
  `disabled-light-controls`, `adaptive-negative-context`, `manual-override`,
  `presence-hold`, `adaptive-lighting-manual-release`, and
  `fan-cover-matrix`. Their logs are stored as
  `/tmp/magic-areas-phase5-corrective-<scenario>.log`, and the complete failure
  scan found no failed checkpoints, simulator failures, tracebacks, errors, or
  exceptions.

Post-Phase 5 roadmap integrity audit on 2026-06-07:

- Reexamined every checked Phase 0 through Phase 5 work area against the current
  implementation, tests, durable guidance, retained live-simulation logs, and
  retained frontend artifact text.
- Confirmed that the Phase 1 fan/cover runtime, config-flow, fake-house,
  bootstrap, and focused test changes were complete but had remained
  uncommitted while later roadmap and simulator work proceeded.
- Focused fan/cover verification passed `34` selected tests.
- `./scripts/validate.sh` passed Ruff, mypy across `365` source files, and
  `1415` pytest tests in `47.42s`.
- No checked roadmap item was reopened by the audit. IDE configuration and local
  assistant metadata are not roadmap deliverables and remain outside the
  roadmap-related commit scope.

### 6. Test Helper Architecture Cleanup

#### 6.1. Preparation

- [x] `6.1.1` Rebuild CRG before test-helper cleanup.
- [x] `6.1.2` Identify all imports of `tests.helpers`.
- [x] `6.1.3` Decide whether first pass keeps compatibility re-exports.

Test-helper preparation progress:

- `6.1.1`: complete. The pre-extraction CRG rebuild indexed `377` files,
  `3551` nodes, and `27657` edges. `assert_state` was the largest hub at degree
  `458`; `shutdown_integration`, `wait_for_state`,
  `get_basic_config_entry_data`, and `setup_mock_entities` were also major
  helper hubs or bridges.
- `6.1.2`: complete. Imports span conftest, scenario, snapshot, integration,
  platform, and unit suites. The most imported symbols are `init_integration`
  (`47` import sites), `get_basic_config_entry_data` and
  `shutdown_integration` (`46` each), `setup_mock_entities` (`24`), and
  `assert_state` (`23`).
- `6.1.3`: complete. The first pass keeps explicit compatibility re-exports
  from `tests.helpers` while implementation moves into responsibility-focused
  modules. This avoids broad import churn during semantic-preserving moves.

#### 6.2. Helper Family Extraction

- [x] `6.2.1` Extract assertion helpers.
- [x] `6.2.2` Extract wait helpers.
- [x] `6.2.3` Extract config-entry builders.
- [x] `6.2.4` Extract lifecycle helpers.
- [x] `6.2.5` Extract entity setup helpers.
- [x] `6.2.6` Extract service helpers.
- [x] `6.2.7` Extract registry helpers.
- [x] `6.2.8` Audit remaining `tests/helpers/__init__.py` facade.
- [x] `6.2.9` Reduce the remaining package facade to compatibility re-exports
  or delete it after imports migrate.

Test-helper extraction progress:

- `6.2.1`: complete. The package conversion required by the target structure
  occurred before the first family move: `tests/helpers.py` became the
  compatibility facade `tests/helpers/__init__.py`. `assert_state`,
  `assert_attribute`, and `assert_in_attribute` then moved unchanged to
  `tests/helpers/assertions.py`. Existing `from tests.helpers import ...`
  imports remain supported.
- Assertion-family validation passed `./scripts/validate.sh`: Ruff passed,
  mypy found no issues across `366` source files, and pytest passed `1415`
  tests in `40.73s`.
- `6.2.2`: complete. `wait_for_state`, `wait_until`, and
  `wait_for_attribute` moved to `tests/helpers/waits.py` and remain available
  from `tests.helpers`. `drain_hass` remains in the lifecycle family.
- Wait-family validation passed `./scripts/validate.sh`: Ruff passed, mypy
  found no issues across `367` source files, and pytest passed `1415` tests in
  `39.96s`.
- Post-extraction audit corrected the first batch to restore the original
  assertion guards, comments, and helper documentation exactly. Direct
  contract tests now verify that every extracted assertion and wait helper is
  the same function object exported by the `tests.helpers` compatibility
  facade.
- Corrective validation passed `./scripts/validate.sh`: Ruff passed, mypy found
  no issues across `368` source files, and pytest passed `1417` tests in
  `40.32s`.
- `6.2.3`: complete. `get_basic_config_entry_data` moved unchanged to
  `tests/helpers/config_entries.py` and remains available from
  `tests.helpers`. The direct facade contract now verifies the re-export.
- Config-entry validation passed `./scripts/validate.sh`: Ruff passed, mypy
  found no issues across `369` source files, and pytest passed `1418` tests in
  `39.90s`.
- `6.2.4`: complete. `init_integration`, `shutdown_integration`, and
  `drain_hass` moved unchanged to `tests/helpers/lifecycle.py` and remain
  available from `tests.helpers`. The original `tests.helpers` logger name is
  preserved for lifecycle log messages, and the direct facade contract covers
  all three exports.
- Lifecycle validation passed `./scripts/validate.sh`: Ruff passed, mypy found
  no issues across `370` source files, and pytest passed `1419` tests in
  `40.25s`.
- `6.2.5`: complete. `setup_test_component_platform`, `mock_integration`,
  `mock_platform`, and `setup_mock_entities` moved to
  `tests/helpers/entities.py` as the complete entity-platform setup dependency
  closure. The public `setup_mock_entities` import remains supported through
  the compatibility facade.
- Entity-helper validation passed `./scripts/validate.sh`: Ruff passed, mypy
  found no issues across `371` source files, and pytest passed `1420` tests in
  `44.74s`.
- `6.2.6`: complete. `async_mock_service` moved unchanged to
  `tests/helpers/services.py` and remains available from `tests.helpers`
  through an exact compatibility re-export. The direct facade contract covers
  the extracted service helper.
- Service-helper validation passed `./scripts/validate.sh`: Ruff passed, mypy
  found no issues across `372` source files, and pytest passed `1421` tests in
  `47.80s`.
- `6.2.7`: complete. Shared mock area/floor registration moved to
  `tests/helpers/registries.py`. `init_integration` and both duplicated
  fixture setup paths now use `setup_mock_areas`, while preserving each
  caller's existing area selection and meta-area filtering. Entity-to-area
  registry assignment remains with entity setup in `tests/helpers/entities.py`;
  scenario-specific device/entity registry operations remain test-local rather
  than expanding the global helper surface.
- Registry-helper tests cover shared-floor reuse, area floor assignment, and
  areas without floors. Full validation passed `./scripts/validate.sh`: Ruff
  passed, mypy found no issues across `374` source files, and pytest passed
  `1423` tests in `46.18s`.
- `6.2.8`: complete. The remaining `tests/helpers/__init__.py` facade defines
  no functions or classes and contains only compatibility re-exports. Its
  public surface is explicit through `__all__`, covering `14` actively used
  helper names. Direct contracts verify the complete export set and exact
  function identity.
- The audit found that the facade remains heavily used: `init_integration`,
  `get_basic_config_entry_data`, and `shutdown_integration` each have at least
  `46` import sites, with other helper families also imported broadly.
  Therefore caller migration or facade deletion remains isolated to `6.2.9`;
  `setup_mock_areas` intentionally remains a direct registry-module import
  rather than expanding the compatibility API.
- Facade-audit validation passed `./scripts/validate.sh`: Ruff passed, mypy
  found no issues across `374` source files, and pytest passed `1425` tests in
  `48.42s`.
- Post-extraction hardening for `6.2.1` through `6.2.8` is complete.
- `6.2.1` through `6.2.8` hardening: direct behavioral and facade-contract
  tests now cover the extracted assertion, wait, config-entry,
  lifecycle-adjacent platform setup, entity setup, service, registry, and
  compatibility-export contracts, including failure paths.
- `6.2.2` hardening: `wait_for_state` and `wait_for_attribute` now accept
  explicit timeout values, consistently convert timeout failures to
  `AssertionError`, and are tested for listener cleanup.
- `6.2.3` hardening: the stale `MockAreaIds.BEDROOM` documentation example now
  uses the valid `MockAreaIds.MASTER_BEDROOM` identifier.
- `6.2.5` hardening: `setup_mock_entities` now rejects duplicate unique IDs and
  verifies both registry-entry creation and persisted area assignment.
- `6.2.7` hardening: the roadmap and implementation boundary now define
  `registries.py` as shared area/floor setup only; scenario-specific
  device/entity registry mutations remain local unless repetition justifies a
  narrow helper.
- `6.2.9` partial progress: the unused compatibility-export decision is
  complete. `VirtualClock`, `setup_test_component_platform`,
  `mock_integration`, and `mock_platform` were removed from the package facade
  while their implementations remain available from their responsibility
  modules.
- `6.2.9` remains open only for migrating the actively used facade imports and
  then either retaining `tests/helpers/__init__.py` as a minimal compatibility
  facade or deleting it once no callers require it.
- `6.2.9` migration strategy: incrementally migrate callers to
  responsibility-focused modules while retaining the compatibility facade.
  After each bounded helper-family batch, manually update CRG and confirm the
  remaining callers with both graph data and source search. Delete the facade
  only after both checks report no active callers.
- `6.2.9` assertion/wait batch: all callers of `assert_state`,
  `assert_attribute`, and `assert_in_attribute` now import from
  `tests.helpers.assertions`; all callers of `wait_for_state`,
  `wait_for_attribute`, and `wait_until` now import from
  `tests.helpers.waits`. The facade remains intact for compatibility while
  other helper families migrate.
- The assertion/wait batch reduced files importing from the facade from `76`
  to `59`. A manual incremental CRG update processed `39` changed files and
  refreshed the graph to `387` files, `3593` nodes, and `27943` edges.
- `6.2.9` utility/submodule batch: callers of `async_mock_service` and
  `drain_hass` now import from their service and lifecycle modules; callers of
  `immediate_call_factory` and `create_area_state_change_event` now import
  from `tests.helpers_timing`. Helper contract tests now import responsibility
  modules directly instead of retrieving modules through the package facade.
- The utility/submodule batch reduced facade-using files from `59` to `56`.
  Source search now shows only four facade-export names in active use:
  `init_integration`, `shutdown_integration`,
  `get_basic_config_entry_data`, and `setup_mock_entities`. A manual CRG
  update refreshed the graph after the batch.
- `6.2.9` entity batch: all `setup_mock_entities` callers now import directly
  from `tests.helpers.entities`. The package facade remains available while
  lifecycle and config-entry callers migrate.
- The entity batch reduced facade-using files from `56` to `55`. Source search
  now shows only `init_integration`, `shutdown_integration`, and
  `get_basic_config_entry_data` entering through the facade. A manual CRG
  update refreshed the graph to `387` files, `3593` nodes, and `27965` edges.
- `6.2.9` final config/lifecycle batch: all remaining callers now import
  `get_basic_config_entry_data` from `tests.helpers.config_entries` and
  `init_integration` / `shutdown_integration` from
  `tests.helpers.lifecycle`.
- Source search and a manual CRG update both confirmed zero active facade
  symbol callers before deletion. `tests/helpers/__init__.py` and its obsolete
  facade-only contract test were then removed. Responsibility modules remain
  directly importable through the `tests.helpers` namespace package.

#### 6.3. Test Helper Validation

- [x] `6.3.1` Run `./scripts/validate.sh` after each helper-family move.
- [x] `6.3.2` Rebuild CRG at phase exit.
- [x] `6.3.3` Confirm helper hub degrees are reduced.
- [x] `6.3.4` Run a final `./scripts/validate.sh` at phase exit.

Test-helper phase-exit progress:

- The full phase-exit CRG rebuild indexed `385` files, `3583` nodes, and
  `27982` edges. The deleted facade and facade-contract test are absent.
- `6.3.3` closed after the `6.4` structural cleanup and final CRG comparison.
  Scenario coupling and broad wait-helper coupling decreased, while remaining
  high-degree leaf assertions, lifecycle operations, config builders, and
  entity setup primitives are narrow, directly tested responsibilities rather
  than aggregate facades. Exact classifications are recorded under `6.4.13`.
- Final `./scripts/validate.sh` passed: Ruff reported no issues, mypy reported
  no issues across `373` source files, and pytest passed all `1429` tests in
  `41.49` seconds.

#### 6.4. Missed Opportunity Cleanup

The first Phase 6 pass completed the mechanical module extraction and removed
the compatibility facade, but it did not satisfy every original exit criterion.
A post-phase implementation audit also exposed responsibilities and regression
guards that were not apparent when the extraction plan was written.

- [x] `6.4.1` Establish a fresh CRG baseline for the responsibility modules and
  define a meaningful hub-reduction target. Measure cross-cluster coupling and
  broad setup dependencies in addition to raw call fan-in so that ubiquitous
  leaf assertions are not replaced with pass-through wrappers solely to lower
  a metric.
- [x] `6.4.2` Build a cover scenario testkit that owns cover-scenario config
  construction, mock-entity setup, integration lifecycle, and state-wait
  operations.
- [x] `6.4.3` Migrate `tests/scenarios/test_cover_automation.py` to the cover
  scenario testkit, then audit every scenario test so scenario modules consume
  scenario-level operations rather than assembling broad platform/setup
  helpers directly.
- [x] `6.4.4` Add direct behavioral contracts for `init_integration`,
  `shutdown_integration`, and `drain_hass`, including successful setup,
  duplicate-entry handling, unload cleanup, entry-state assertions, and the
  requested number of drain cycles.
- [x] `6.4.5` Add direct behavioral contracts for `mock_integration` and
  `mock_platform`, covering built-in and custom-component registration,
  integration reuse, platform cache placement, and failure behavior.
- [x] `6.4.6` Add a positive config-entry builder contract that verifies the
  complete valid default payload, independent mutable containers between
  calls, and the existing invalid-area failure contract.
- [x] `6.4.7` Make `setup_mock_areas` explicitly idempotent for repeated setup
  of the same area/floor set, or document and enforce a single-use contract.
  Add tests for whichever contract is selected so repeated lifecycle setup
  cannot silently create duplicate registry entries.
- [x] `6.4.8` Split platform-loader mocking
  (`setup_test_component_platform`, `mock_integration`, and `mock_platform`)
  from entity registration if CRG and call-site review confirm that
  `tests/helpers/entities.py` still spans two responsibilities. Migrate callers
  directly and do not add a new aggregate facade.
- [x] `6.4.9` Consolidate the parallel integration setup and teardown paths in
  `tests/conftest.py` with `tests/helpers/lifecycle.py`, preserving fixture
  semantics while removing duplicated area registration, entry setup, unload,
  and event-loop draining logic.
- [x] `6.4.10` Characterize `wait_until` under an immediately false predicate
  and delayed HA work. Ensure the loop yields cooperatively, honors explicit
  timeout values without a CPU-bound spin, and has deterministic success and
  timeout tests.
- [x] `6.4.11` Add an import-boundary regression contract that rejects
  `from tests.helpers import ...`, direct imports of a recreated aggregate
  facade, and an implementation-bearing `tests/helpers/__init__.py`.
- [x] `6.4.12` Remove stale facade-era references after the architecture is
  settled, including `docs/migration/tests.md` references to
  `tests/helpers.py` and obsolete `tests.helpers` logger names in responsibility
  modules.
- [x] `6.4.13` Rebuild CRG after the cleanup and record before/after degrees,
  cross-cluster edges, and remaining justified helper hubs. Complete `6.3.3`
  only when the measured architecture satisfies the target defined in
  `6.4.1`.

Additional-sweep evidence:

- The original Phase 6 exit criterion that scenario tests depend on scenario
  helpers is not yet satisfied:
  `tests/scenarios/test_cover_automation.py` directly imports four generic
  helper families.
- Direct helper contracts do not currently exercise `init_integration`,
  `shutdown_integration`, `drain_hass`, `mock_integration`, or `mock_platform`.
  The valid output of `get_basic_config_entry_data` is also only covered
  indirectly.
- `tests/helpers/entities.py` is still a `304`-line mixed boundary containing
  both HA loader/platform mocking and mock-entity registration.
- `tests/conftest.py` contains lifecycle fixture paths that independently
  register areas, set up entries, unload entries, and drain HA alongside the
  extracted lifecycle helpers.
- `setup_mock_areas` reuses existing floors but unconditionally creates areas;
  no contract currently defines behavior when the same area is set up twice.
- The facade was deleted without a static boundary guard against its
  reintroduction. `docs/migration/tests.md` also still describes the deleted
  `tests/helpers.py` module.
- `wait_until` repeatedly drains HA until a wall-clock deadline, but its direct
  tests do not prove cooperative behavior when no HA work is pending.

`6.4.1` baseline and acceptance target:

- A fresh full CRG build indexed `385` files, `3595` nodes, and `28084` edges.
  The postprocessed graph contains `3583` queryable nodes and `27982` edges.
- The extracted helper community has `21` nodes and cohesion `0.0035`.
  Cross-community coupling is `357` edges to `platforms-setup`, `262` to
  `integration-area`, `33` to `scenarios-light`, `32` to `unit-area`, and `10`
  to `snapshots-snapshot`.
- Current helper degrees are `assert_state=462`,
  `shutdown_integration=224`, `wait_for_state=177`,
  `get_basic_config_entry_data=168`, and `setup_mock_entities=123`.
- Leaf assertions, waits, and data builders may remain high fan-in when they
  expose one narrow behavior and have direct contracts. Phase 6 will not add
  pass-through wrappers merely to reduce those degrees.
- Broad setup/orchestration dependencies must improve structurally: scenario
  test modules must have zero direct imports of generic entity, config-entry,
  registry, service, or lifecycle helpers; platform-loader mocking must no
  longer share an implementation module with entity registration; and
  `conftest.py` lifecycle fixtures must delegate shared setup/teardown behavior
  instead of maintaining parallel implementations.
- At `6.4.13`, compare all five helper degrees and the helper-community
  cross-community edge counts with this baseline. Any metric that does not
  decrease must be tied to a narrow, directly tested responsibility and
  documented as intentionally central before `6.3.3` can close.
- `6.4.2`: complete. `tests/scenarios/cover_scenario_testkit.py` now owns cover
  and cover/light config construction, mock-entity setup, integration
  lifecycle, control enablement, room-state transitions, and state waits
  through typed `OneRoomCoverScenario` and `CoverLightScenario` surfaces.
- `6.4.3`: complete. `tests/scenarios/test_cover_automation.py` now contains
  behavioral setup fixtures and assertions only; it has no direct generic
  helper imports. The scenario-suite audit found no `test_*.py` module directly
  importing generic entity, config-entry, lifecycle, registry, or service
  helpers. Focused Ruff and mypy passed, and all `5` cover scenario tests
  passed in `1.03s`.
- `6.4.4`: complete. Direct lifecycle contracts now cover setup with an entry
  already registered in Home Assistant, singular entry registration, area
  creation, runtime-data initialization, loaded/unloaded entry states, domain
  cleanup, failure when setup does not load the entry, and exact
  `drain_hass(cycles=...)` behavior. The combined helper and cover-scenario
  suite passed all `20` tests in `1.21s`; focused Ruff and mypy passed.
- `6.4.5`: complete. Direct loader contracts cover custom-component package
  registration, integration and component cache placement, intentional
  platform-import failure, reuse of an existing integration, platform cache
  placement, and top-level platform-file registration. The focused helper
  suite passed all `17` tests in `1.18s`; Ruff and mypy passed.
- `6.4.6`: complete. The config-entry builder contract now verifies the entire
  valid default payload and proves that exclusion, inclusion, and enabled-
  feature containers are independent between calls while retaining the
  invalid-area failure contract. The focused helper suite passed all `18`
  tests in `1.12s`; Ruff and mypy passed.
- The completed `6.4.1` through `6.4.6` batch passed
  `./scripts/validate.sh`: Ruff passed, mypy found no issues across `374`
  source files, all `26` snapshots passed, and pytest passed all `1435` tests
  in `41.04s`.
- `6.4.7`: complete. `setup_mock_areas` now reuses existing named areas,
  reconciles their configured floor assignment, and adds only missing areas or
  floors. Direct tests cover repeated identical batches, mixed existing/new
  batches, floor reuse, floorless areas, and correction of an existing area's
  floor. All `5` focused tests passed in `0.71s`; Ruff and mypy passed.
- `6.4.8`: complete. `tests/helpers/platforms.py` now owns
  `setup_test_component_platform`, `mock_integration`, and `mock_platform`;
  `tests/helpers/entities.py` contains only mock-entity registration and
  verified area assignment. Callers import the responsibility modules
  directly and no aggregate facade was added. All `23` focused helper and
  registry tests passed in `1.52s`; Ruff and mypy passed.
- `6.4.9`: complete. `tests/helpers/lifecycle.py` now owns shared config-entry
  registration, sequential per-entry setup with optional HA startup, and
  idempotent unload/drain behavior. `tests/conftest.py` delegates its basic,
  compatibility, and all-area/meta-area fixture paths to those lifecycle
  primitives while retaining the required sequential meta-entry setup order.
  A representative fixture/lifecycle suite passed all `30` tests in `1.61s`;
  Ruff and mypy passed.
- `6.4.10`: complete. `wait_until` now drains HA and then yields through a
  bounded `loop.call_at` pause, avoiding both idle-loop busy spinning and
  dependence on `loop.call_later`, which tests may legitimately patch. Direct
  contracts cover idle timeout fairness and delayed asynchronous success; all
  existing area-reload and WASP config callers pass. Focused results were `20`
  helper tests, `2` area-reload tests, and `2` WASP tests; Ruff and mypy passed.
- `6.4.11`: complete. A static AST boundary contract rejects
  `from tests.helpers import ...`, exact `import tests.helpers`, and recreation
  of `tests/helpers/__init__.py`. The guard scans the complete Python test tree
  so future facade regressions fail validation.
- `6.4.12`: complete. Migration documentation now describes the
  responsibility-focused `tests/helpers/` package, responsibility modules use
  their own logger names, and source search finds no stale `tests/helpers.py`,
  aggregate-import, or `tests.helpers` logger references outside historical
  roadmap evidence. The combined boundary/helper suite passed all `26` tests
  in `2.00s`; Ruff and mypy passed.
- `6.4.13`: complete. The final full CRG build indexed `386` files, `3612`
  nodes, and `28189` edges; postprocessing produced `3600` queryable nodes and
  `28087` edges. The helper community decreased from `21` to `18` nodes, with
  cohesion moving from `0.0035` to `0.0034`. Cross-community edges changed
  from `357` to `357` for platforms, `262` to `262` for integration, `33` to
  `24` for scenarios, `32` to `46` for unit tests, and remained `10` for
  snapshots. The unit increase is attributable to the new direct behavioral
  and import-boundary contracts rather than broader production-test coupling.
- Final helper degrees are `assert_state=462` (unchanged and intentionally
  central as a directly tested leaf assertion), `shutdown_integration=224`
  (unchanged and intentionally central as the shared lifecycle teardown),
  `wait_for_state=161` (reduced from `177`),
  `get_basic_config_entry_data=175` (up from `168` because scenario testkits
  and direct contracts use the narrow builder), and `setup_mock_entities=123`
  (unchanged and intentionally central as the verified entity-registration
  primitive). No remaining metric represents an aggregate facade or mixed
  implementation responsibility, so the acceptance rule from `6.4.1` is
  satisfied and `6.3.3` is closed without manufacturing pass-through helpers.

#### 6.5. Exit Re-evaluation

- [x] `6.5.1` Re-audit every checked `6.1.x` through `6.4.x` item against the
  current code, focused test output, and retained CRG evidence rather than
  trusting roadmap status.
- [x] `6.5.2` Confirm source and import-boundary scans find no aggregate
  `tests.helpers` facade imports, no recreated implementation facade, and no
  scenario test that directly assembles generic lifecycle/entity/config setup.
- [x] `6.5.3` Run the focused helper, fixture, scenario, and boundary-contract
  tests added or changed during `6.4`, and record the exact result.
- [x] `6.5.4` Run `./scripts/validate.sh` and record exact Ruff, mypy, pytest,
  snapshot, and timing results.
- [x] `6.5.5` Perform a full CRG rebuild and postprocess pass. Compare the final
  graph with the `6.4.1` baseline and explicitly classify every remaining
  high-degree helper as reduced, intentionally central, or still requiring
  work.
- [x] `6.5.6` Reconcile `6.3.3` and every Phase 6 exit criterion with the final
  evidence. Do not declare Phase 6 complete while any criterion is unmet or
  justified exception is undocumented.
- [x] `6.5.7` Commit the completed Phase 6 cleanup as an isolated roadmap scope,
  leaving unrelated local IDE and assistant metadata changes untouched.

Exit re-evaluation evidence:

- `6.5.1`: complete. Every checked `6.1.x` through `6.4.x` item was compared
  with the current responsibility modules, callers, direct contracts, retained
  validation results, and final CRG data. No checked item required reopening.
- `6.5.2`: complete. Source and AST scans find no aggregate
  `tests.helpers` imports and `tests/helpers/__init__.py` remains absent.
  Scenario test modules have no direct imports of generic lifecycle, entity,
  config-entry, registry, service, or platform-loader helpers; those
  dependencies are confined to scenario testkits.
- `6.5.3`: complete. The focused helper, registry, import-boundary, cover
  scenario, integration lifecycle/state/meta/reload, and WASP regression suite
  passed all `47` tests in `4.93s`.
- `6.5.4`: complete. `./scripts/validate.sh` passed with Ruff clean, mypy
  reporting no issues across `376` source files, all `26` snapshots passing,
  and pytest passing all `1441` tests in `43.27s`.
- `6.5.5`: complete. The final CRG rebuild and postprocess results, baseline
  comparison, cross-community edge changes, and classification of all five
  measured helper hubs are recorded under `6.4.13`.
- `6.5.6`: complete. The final audit confirms direct responsibility-module
  imports, scenario-level setup ownership, consolidated fixture lifecycle,
  split platform/entity helpers, direct behavioral contracts, idempotent area
  setup, cooperative waits, and a static facade boundary. All Phase 6 exit
  criteria are satisfied; the justified central helpers are documented under
  `6.4.13`.
- `6.5.7`: complete in the isolated Phase 6 cleanup commit; unrelated local
  IDE and assistant metadata remain outside the commit.

Explicit exit re-evaluation:

- `6.5.1` was rerun against the committed tree. All responsibility modules,
  lifecycle delegation primitives, idempotent registry behavior, cooperative
  wait implementation, scenario testkit, and static boundary contract remain
  present. No checked `6.1.x` through `6.4.x` item required reopening.
- `6.5.2` source scans again found no aggregate `tests.helpers` import, no
  `tests/helpers/__init__.py`, and no scenario test module directly importing
  generic lifecycle, entity, config-entry, registry, service, or
  platform-loader setup helpers.
- `6.5.3` reran the complete focused helper, registry, boundary, cover
  scenario, integration lifecycle/state/meta/reload, and WASP regression set.
  All `47` tests passed in `4.52s`.
- `6.5.4` reran `./scripts/validate.sh`: Ruff passed, mypy found no issues
  across `376` source files, all `26` snapshots passed, and pytest passed all
  `1441` tests in `37.06s`.
- `6.5.5` performed a fresh full CRG build: `388` files, `3621` nodes, and
  `28256` edges; the query graph contains `3609` indexed rows and `28154`
  edges. The helper community contains `24` nodes with cohesion `0.0054`.
  Cross-community edges are `357` to platforms, `262` to integration, `50` to
  unit tests, `24` to scenarios, and `10` to snapshots.
- Final helper degrees remain `assert_state=462`,
  `shutdown_integration=224`, `get_basic_config_entry_data=175`,
  `wait_for_state=161`, and `setup_mock_entities=123`. The scenario and wait
  reductions remain intact. The other hubs remain narrow, directly tested
  shared utilities; the increased unit coupling represents direct behavioral
  and boundary contracts rather than restored facade coupling.
- `6.5.6` found every Phase 6 exit criterion still satisfied with no
  undocumented exception or remaining helper-architecture work.
- `6.5.7` verified commit `9bd9a76` contains exactly the roadmap,
  documentation, fixture, helper, and helper-contract files belonging to the
  Phase 6 cleanup.

### 7. Manual Dead-Code Audit

#### 7.1. Audit Guardrails

- [x] `7.1.1` Do not remove HA entry points based only on CRG.
- [x] `7.1.2` Do not remove HA entity properties based only on CRG.
- [x] `7.1.3` Do not remove pytest fixtures based only on CRG.
- [x] `7.1.4` Do not remove feature registry-dispatched classes/methods based only on CRG.
- [x] `7.1.5` Do not remove HA interface mock methods based only on CRG.

#### 7.2. Initial Candidate Audit

- [x] `7.2.1` Audit `AggregateKind`.
- [x] `7.2.2` Audit `ControlActionType`.
- [x] `7.2.3` Audit `ControlRuntimeEffectType`.
- [x] `7.2.4` Audit `ControlGroupPolicyId`.
- [x] `7.2.5` Audit `GroupMetadataKey`.
- [x] `7.2.6` Audit `FeatureRegistration`.
- [x] `7.2.7` Audit `IntentReason`.
- [x] `7.2.8` Audit `ControlTargetKind`.
- [x] `7.2.9` Audit `ControlTargetPrecision`.
- [x] `7.2.10` Audit `VirtualClock`.

#### 7.3. Dead-Code Validation

- [x] `7.3.1` Search direct references with `rg`.
- [ ] `7.3.2` Search string/serialized references.
- [x] `7.3.3` Check registry and HA callback conventions.
- [x] `7.3.4` Remove only small proven groups.
- [x] `7.3.5` Document rationale for retained dynamic/contract symbols.
- [x] `7.3.6` Run `./scripts/validate.sh` after each removal batch.
- [x] `7.3.7` Run a final `./scripts/validate.sh` at phase exit.

Expanded-audit correction:

- The initial pass completed the ten named candidate reviews and removed eight
  proven-dead symbols, but the subsequent retained-candidate inventory used
  broad file/path classifications instead of preserving per-symbol evidence.
  The expanded audit therefore used a temporary per-symbol checklist. A later
  review found that grouped evidence and missing candidate-specific coverage,
  disposition, or rationale had caused incomplete entries to be marked
  complete. Every record was reopened, repaired, and independently checked
  against the final source tree, collected tests, and rebuilt graph before the
  temporary checklist was retired.
- [x] `7.3.8` Export and inventory the complete current CRG dead-code candidate
  set rather than limiting review to the ten initial plausible targets.
- [x] `7.3.9` Classify every candidate by framework/dynamic false-positive
  category or by concrete suspicion requiring source review.
- [ ] `7.3.10` Investigate every remaining plausible candidate with direct,
  serialized, registry, callback, fixture, and test-reference evidence.
- [ ] `7.3.11` Review whether dynamically retained symbols have adequate
  contract coverage and add focused tests where the retention mechanism is not
  already proven.
- [x] `7.3.12` Rebuild CRG after all removal batches and confirm removed symbols
  are absent while retained dynamic contracts are documented.
- [ ] `7.3.13` Transfer lasting architectural rationale, coverage requirements,
  and unresolved work from the temporary audit into this roadmap or the
  appropriate durable documentation.
- [x] `7.3.14` Retire the temporary audit checklist after its verified
  conclusions have been transferred.
- [ ] `7.3.15` Commit the completed Phase 7 removals, tests, roadmap, and durable
  documentation changes as an isolated scope.

#### 7.4. Completion-Scrutiny Corrections

- [ ] `7.4.1` Correct the Wasp-in-a-Box timeout-unit contract. Configuration is
  expressed as minutes, while `WaspStateUpdate.request_timer` and
  `ReusableTimer` consume seconds; perform the conversion at one explicit
  boundary and keep state-machine/entity documentation consistent.
- [ ] `7.4.2` Add a behavioral timing contract that captures the delay passed
  to the Wasp timer and proves a configured one-minute timeout schedules 60
  seconds. Do not use the immediate-timer fixture for this duration assertion.
- [ ] `7.4.3` Retain the existing timeout-expiry, cancellation-on-open, and
  cancellation-on-reseen behavior tests, and confirm the unit correction does
  not regress those behaviors.
- [ ] `7.4.4` Remove or replace the stale
  `next_step_id="finish"` fallback in `scripts/ha_dev_bootstrap.py`.
  Bootstrap must treat the page-level persistence menu as the completed
  options state and must not call the removed `async_step_finish` route.
- [ ] `7.4.5` Add direct tests for `configure_magic_area_options` covering the
  expected final menu and malformed/unexpected final responses. Assert that no
  request targets the removed `finish` route.
- [ ] `7.4.6` Repeat the direct and serialized-reference sweep for every Phase
  7 removal across production code, tests, scripts, translations, and durable
  documentation. Record and resolve every remaining runtime caller rather than
  relying on symbol-definition absence.
- [ ] `7.4.7` Reconstruct a durable candidate-by-candidate disposition for the
  final CRG candidate set, or provide an equally reproducible generated
  artifact and command. The evidence must map each candidate identity to its
  retention/removal mechanism and relevant source or test evidence.
- [ ] `7.4.8` Reconcile the reconstructed final candidate set with the
  287-candidate baseline, the 16 removed definitions, and the 20 definitions
  made statically live. Resolve any count or identity mismatch before closure.
- [ ] `7.4.9` Rebuild CRG from the committed correction tree and record the
  exact commit, raw/indexed graph metrics, and final candidate count.
- [ ] `7.4.10` Run focused Wasp timing, options-flow, bootstrap, translation,
  and simulator-module tests after the corrections.
- [ ] `7.4.11` Run `./scripts/validate.sh` after all Phase 7 corrections and
  record exact Ruff, mypy, snapshot, pytest, and timing results.
- [ ] `7.4.12` Re-evaluate every checked `7.1.x` through `7.4.x` item against
  the corrected committed tree and retained evidence. Do not mark Phase 7
  complete while any implementation, caller, coverage, or auditability gap
  remains.
- [ ] `7.4.13` Commit the completed Phase 7 scrutiny corrections and durable
  evidence as an isolated roadmap scope.

Dead-code audit evidence:

- The reopened audit assigned a unique identity to all 287 baseline CRG
  candidates. The final audit resolved every entry with exact direct-reference
  and quoted-name searches, a framework/dynamic-contract classification, a
  collected behavioral or contract test, a disposition, and a rationale.
- `AggregateKind` is retained because aggregate policy and runtime assembly
  distinguish standard and health definitions through it, with direct tests.
- `ControlActionType` and `ControlRuntimeEffectType` are retained as active
  policy, decision, runtime-effect, and executor contracts across light, fan,
  cover, climate, and media control paths.
- `ControlGroupPolicyId` and `GroupMetadataKey` are retained as serialized
  configuration and registry contracts. Their values are consumed by schemas,
  builders, feature modules, runtime selectors, switches, and tests.
- `FeatureRegistration` is retained. Although CRG reports the class as
  unreferenced, `FEATURE_REGISTRATIONS` constructs it and its records are
  directly consumed by the feature-catalog contract tests.
- `IntentReason`, `ControlTargetKind`, and `ControlTargetPrecision` are retained
  as active pure-engine decision and execution-target contracts with runtime
  consumers and direct behavioral coverage.
- CRG also reports the nested `immediate_call` and `cancel` callbacks in
  `tests/helpers_timing.py` as dead. They are retained because the factory
  returns `immediate_call`, Home Assistant invokes it as a patched callback
  scheduler, and callers receive `cancel` as the cancellation contract.
- The reopened audit removed 16 additional proven-dead candidate definitions:
  the unreachable Wasp timer callback; duplicate `FeatureIcons`; five stale
  options-flow settings/finish routes; two unused control-builder facade
  functions; four obsolete feature protocol/base hooks; unused
  `MockEntity.device_info` and `MockSensor.last_reset` overrides; and one
  unused light edge-case fixture. Exact source and final-graph checks find none
  of those symbols.
- Retained candidates received focused behavioral coverage where framework
  discovery alone was insufficient. Added contracts cover config-entry
  callbacks, migration handlers, HA entity properties/services, timer
  cancellation and expiry callbacks, bootstrap/simulator builders, pytest
  fixtures, mock entity surfaces, scenario IDs, snapshots, and Adaptive
  Lighting service/event callbacks. Direct tests were also added for
  `default_feature_options`, `schema_from_default_options`, and the concrete
  light runtime controller restore hook.
- The completion review found serialized residue from removed options-flow and
  entity contracts in non-English translations. The correction removed the
  obsolete `finish` route and false Save-and-Exit instructions from seven
  locales; the deleted `climate_groups` feature key, configuration step, and
  climate entity translation from affected locales; and parent fan/climate
  form fields superseded by submenu steps. A recursive translation-contract
  test now permits partial locales but rejects every localized key absent from
  the canonical English tree.
- The corrected final CRG rebuild parsed 389 files and produced 3,643 raw nodes
  and 28,673 raw edges. The query graph contains 3,629 indexed nodes and 28,570
  indexed edges on branch `fan-cover-default-automation` at correction commit
  `215dd25faf9a`.
  `find_dead_code` returned 251 candidates. Reconciliation against the
  287-item baseline found zero new candidates: 16 candidate definitions are
  absent, and 20 retained definitions are no longer reported because current
  callers or focused tests make them statically live. The two entries omitted
  from the earlier reconciliation were `default_feature_options` and
  `schema_from_default_options`, made statically live by their committed direct
  contract tests.
- Final `./scripts/validate.sh` passed Ruff, mypy across 377 source files, all
  26 snapshots, and all 1,480 pytest tests in 42.84 seconds.
- Durable rule: CRG dead-code output remains a candidate generator only.
  Home Assistant entry points/entity interfaces, registry-dispatched feature
  modules, callback-return contracts, serialized enums/keys, simulator
  builders, and pytest fixtures require framework-aware reference review and
  behavioral evidence before removal.
- Coverage aggregation, removal-batch reconciliation, serialized-contract
  cleanup, final-tree validation, durable transfer, and temporary-checklist
  retirement are complete. The original Phase 7 work remains in commit
  `b9f5063`; the completion-review correction adds the translation cleanup,
  recursive regression contract, corrected CRG reconciliation, and current
  full-validation evidence in isolated commit `215dd25`.

### 8. Options-Flow Structural Follow-Up

Phase 8 should continue from a clean `options-flow-structure` branch based on
`fan-cover-default-automation`, not from the earlier main-based
`codex/options-flow-structure` scratch branch. The fan-cover branch already
contains the current options-flow surface and tests that must be preserved.
Reapply only useful scratch-branch implementation primitives, keep fan/cover
options-flow behavior as a constraint, and do not redesign fan/cover as part of
this structural extraction.

#### 8.1. Preparation

- `8.1.1` Confirm temporary options-flow behavior plan is retired or closable.
- `8.1.2` Confirm current options-flow contract is documented durably.
- `8.1.3` Identify weakly covered `handle_feature_conf` routes.
- `8.1.4` Add tests for weak routes before extraction.

#### 8.2. Routing Refactor

- `8.2.1` Extract simple feature page builders.
- `8.2.2` Extract light group page builders.
- `8.2.3` Extract fan group page builders.
- `8.2.4` Extract climate control page builders.
- `8.2.5` Extract aggregate page builders.
- `8.2.6` Extract custom control group page builders.
- `8.2.7` Extract persistence-boundary helpers.
- `8.2.8` Extract validation-error normalization.
- `8.2.9` Reduce `handle_feature_conf` to orchestration.

#### 8.3. Options-Flow Validation

- `8.3.1` Run `./scripts/validate.sh` after each extraction batch.
- `8.3.2` Manually verify representative HA UI paths if frontend behavior is touched.
- `8.3.3` Confirm no frontend serializer regressions.
- `8.3.4` Rebuild CRG and confirm `handle_feature_conf` fan-out is reduced.
- [ ] `8.3.5` Run a final `./scripts/validate.sh` at phase exit.

### 9. Control Runtime Pattern Consolidation

#### 9.1. Pattern Inventory

- `9.1.1` Inventory control switch gating across domains.
- `9.1.2` Inventory policy input assembly across domains.
- `9.1.3` Inventory state/action token parsing across domains.
- `9.1.4` Inventory target entity/helper resolution across domains.
- `9.1.5` Inventory service-call execution across domains.
- `9.1.6` Inventory manual/hold/suppression state tracking across domains.
- `9.1.7` Inventory debug attribute publication across domains.
- `9.1.8` Inventory last-decision/last-reason recording across domains.

#### 9.2. Shared Support Extraction

- `9.2.1` Extract only patterns proven in at least two domains.
- `9.2.2` Add common enabled-switch gate helpers if justified.
- `9.2.3` Add target normalization helpers if justified.
- `9.2.4` Add hold-deadline state helpers if justified.
- `9.2.5` Add debug attribute builders if justified.
- `9.2.6` Add shared service-call tracing helpers if justified.
- `9.2.7` Keep domain policy decisions domain-specific.

#### 9.3. Control Runtime Validation

- `9.3.1` Run `./scripts/validate.sh` after each extraction batch.
- `9.3.2` Run relevant live scenarios if light/fan/cover behavior changes.
- `9.3.3` Confirm debug attributes are stable or intentionally versioned.
- [ ] `9.3.4` Run a final `./scripts/validate.sh` at phase exit.

### 10. Future Live Simulation Expansion

#### 10.1. Fan Expansion

- `10.1.1` Add explicit room-state odor fallback live coverage.
- `10.1.2` Add cooling fan occupancy path.
- `10.1.3` Add multiple physical fans with overlapping roles.
- `10.1.4` Add fan reload/restart behavior coverage.

#### 10.2. Cover Expansion

- `10.2.1` Add partial position/tilt coverage.
- `10.2.2` Add cover `opening`/`closing` movement-state coverage.
- `10.2.3` Add richer daylight/time-like context coverage.
- `10.2.4` Add cover reload/restart behavior coverage.
- `10.2.5` Add membership/class reconciliation coverage.

#### 10.3. Cross-Domain Expansion

- `10.3.1` Add combined fan/cover/light/adaptive active room if justified.
- `10.3.2` Add fuller live cover-induced brightness to adaptive-switching path.
- `10.3.3` Add real media-player state coverage.
- `10.3.4` Add helper/entity registry repair scenarios.

#### 10.4. Config-Flow/Manual Setup Expansion

- `10.4.1` Keep Setup Room reserved for config-flow/manual setup validation.
- `10.4.2` Add manual validation instructions for exact room config creation.
- `10.4.3` Add UI automation only if it does not repurpose Setup Room for active simulation.

#### 10.5. Phase Exit Validation

- [ ] `10.5.1` Run `./scripts/validate.sh` after Phase 10 work is complete.

### 11. Documentation Consolidation

#### 11.1. Temporary Plan Retirement

- `11.1.1` Confirm fan/cover temporary plan has no unique knowledge.
- `11.1.2` Confirm options-flow temporary plan has no unique knowledge.
- `11.1.3` Confirm adaptive-switching temporary plan has no unique knowledge.
- `11.1.4` Delete temporary plans only after explicit user agreement.

#### 11.2. Durable Documentation Preservation

- `11.2.1` Keep `CLAUDE.md` current for required commands and project guidance.
- `11.2.2` Keep `dev-simulation-guidance.md` current for simulator behavior.
- `11.2.3` Keep architecture/runtime-boundary docs current for structural changes.
- `11.2.4` Keep this master roadmap current while it remains active.

#### 11.3. Phase Exit Validation

- [ ] `11.3.1` Run `./scripts/validate.sh` after Phase 11 work is complete.

## Current Recommended Next Step

Finish Phase 0 and Phase 1 first. Do not start simulator modularization,
test-helper cleanup, dead-code removal, options-flow routing refactors, or broad
control-runtime consolidation until fan/cover closure is complete and validation
remains green.
