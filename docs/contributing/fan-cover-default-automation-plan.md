# Fan And Cover Default Automation Plan

Status: in progress. Fan controller policy, multi-role runtime consumption,
controller-role options-flow pages, fan-derived area states, and fan
threshold+trend helper support are implemented. Sensor-driven odor control and
explicit room-state odor fallback are implemented. Cover preset configuration is
implemented. Cover runtime automation remains open.

Target branch: `fan-cover-default-automation`

## Purpose

This plan defines the next default-automation expansion for Magic Areas after the
light/adaptive-switching and options-flow architecture work. The goal is to add
first-class, guided automation for fans and covers without inventing a separate
automation framework.

The implementation should reuse the architecture that now exists in the fork:

- Native Home Assistant helpers as durable control surfaces where practical.
- Magic Areas control groups as the membership and policy boundary.
- Magic Areas control switches as master opt-ins for automatic action.
- Area states as the shared room-condition language.
- Policy adapters and intent-style evaluation for conflict handling.
- Options-flow submenus for multi-part configuration.
- Scenario/dev-house tests for behavior that depends on real HA event ordering.

This is not a progress log. It is the branch plan for the work that should happen
next.

## Current Baseline

### Fan Groups

Current fan behavior is narrow:

- One native HA fan group helper is created for all fan entities in the area.
- One Magic Areas fan control switch enables or disables fan automation.
- One threshold-style rule evaluates an aggregate sensor device class, a setpoint,
  and a required area state.
- The existing logic is useful for temperature cooling fans and basic humidity
  cases, but it is too narrow for real bathroom and ventilation use.

The current implementation should be treated as the first concrete fan controller,
not as the final fan model.

### Cover Groups

Current cover behavior is mostly control-surface oriented:

- Native HA cover group helpers are created by cover device class.
- One Magic Areas cover control switch exists.
- Runtime cover movement policy is not meaningfully implemented.

The cover feature already has useful helper surfaces. This branch should add the
policy layer needed to make those helpers useful for daylight, privacy, and
media/accent behavior.

### Adaptive Switching

Adaptive light switching is already light-policy focused:

- Lights own light on/off policy.
- Adaptive Lighting owns light appearance for lights that are on.
- Native helpers expose signal data.
- Magic Areas interprets those signals in room-policy context.

Cover automation should follow the same boundary. Covers can change daylight
conditions; light policy reacts to the changed room brightness/context. Covers do
not directly command lights, and lights do not directly command covers.

## Architectural Principles

- Reuse existing control-group and intent patterns before adding new machinery.
- Native HA helpers remain authoritative control targets where they are exact.
- Magic Areas owns room intent, policy, conflict resolution, and setup guidance.
- Control switches remain the master opt-in for automatic movement/action.
- Visible area states should describe room conditions, not merely device states.
- Domain policies may share signals, but one domain should not directly command
  another domain.
- Configured role membership should parallel light groups: users think in terms
  of jobs in a room, then assign devices to those jobs.
- Reconciled/native helpers must stay protected from self-enumeration.
- Options-flow pages should follow the current persistence contract: complete
  pages save on submit, invalid pages stay open, and multi-part domains use
  intentional submenus.

## Fan Automation Model

Fan automation should become a reusable controller/reason model.

Built-in controller roles:

- `cooling`
- `humidity`
- `odor`

Each controller role represents a reason a fan should run. The controller owns a
fan membership list, a signal source, activation logic, clear behavior, and
unavailable handling. The same fan may belong to multiple controller roles.

Example: an upstairs bathroom fan can be assigned to both `humidity` and `odor`,
while `cooling` is left empty. The fan runs when the room is humid or odor/VOC is
high. It turns off only after both reasons clear and any configured holds expire.

### Fan On/Off Contract

- A fan turns on when at least one controller reason targeting that fan is active.
- A fan turns off only when no controller reason targeting that fan remains active
  and all applicable holds have expired.
- No individual controller may turn off a fan still required by another active
  controller.
- Area-state gating and suppression are evaluated per controller.
- The existing fan control switch remains the master automation enable.

### Fan Controller Config Contract

Each controller config should have a normalized internal shape. The user-facing UI
can present role-specific labels, but runtime should consume one controller
contract.

Required fields:

- `controller_id`: stable controller role ID, initially `cooling`, `humidity`, or
  `odor`.
- `members`: fan entities controlled by this controller.
- `sensor_entity_id`: selected sensor or managed/aggregate signal source.
- `detection_mode`: initially `threshold`; `threshold_trend` should be added early
  in this branch.
- `on_threshold`: value that activates the controller.
- `hysteresis` or `off_threshold`: value separation that clears the controller.
- `active_states`: area states allowed to activate the controller.
- `suppress_states`: area states that block activation.
- `clear_behavior`: what happens when occupancy/state clears while the controller
  is active.
- `post_clear_hold_seconds`: hold time after occupancy/state clear where relevant.
- `sensor_unavailable_behavior`: per-controller unavailable policy.

Recommended `clear_behavior` values:

- `run_until_clear`: keep running until the sensor condition clears.
- `occupancy_only`: clear as soon as the required occupancy/state condition clears.
- `post_clear_hold`: run for a fixed time after occupancy/state clears.

Recommended `sensor_unavailable_behavior` values:

- `clear_reason`: clear the controller reason immediately.
- `hold_then_clear`: keep the prior reason briefly, then clear if the sensor does
  not recover.
- `hold_until_restored`: keep the prior reason active until the sensor returns or
  automation is disabled.

### Built-In Fan Controller Defaults

Cooling controller:

- Maps the current fan-group threshold behavior into the controller model.
- Default sensor class: temperature.
- Default detection: threshold + hysteresis.
- Default active states: occupied/extended.
- Default clear behavior: occupancy/state gated.
- Sleep suppression should be supported so users can prevent cooling fans during
  quick night trips.
- Existing fan config should reopen as Cooling settings.

Humidity controller:

- Default sensor class: humidity.
- Default detection: threshold + hysteresis.
- Threshold-only behavior is the first proof of concept.
- Threshold + trend/rate behavior must be designed and implemented early because
  the pattern will recur in other sensor-driven controllers.
- Default clear behavior: run until humidity clears, then apply post-clear hold.
- Default unavailable behavior: hold briefly, then clear unless configured
  otherwise.

Odor controller:

- Preferred sensor sources: VOC, particulate, air quality, gas, or comparable
  smell/air-quality signals available in HA.
- Default detection: threshold + hysteresis when a sensor is configured.
- If no odor/VOC sensor is configured, fallback behavior must be explicit. It can
  use post-occupancy runtime, but it should not be hidden or implied.
- Default clear behavior for sensor mode: run until the sensor condition clears.
- Default unavailable behavior: configurable; no hardcoded global assumption.

### Fan Visible Area States

Fan controllers should publish canonical visible area states. These states should
represent room conditions/reasons, not fan device state alone.

Initial states:

- `humid`
- `odor`
- `hot`

Rules:

- `humid` is active when the humidity controller reason is active.
- `odor` is active when the odor controller reason is active.
- `hot` is active when the cooling controller reason is active.
- A fan being on does not automatically imply all states are active.
- A state can be active even if the fan has not yet changed state, as long as the
  controller condition is active.
- Area state attributes should expose active fan reasons, suppressed fan reasons,
  and target fan entities for debug clarity.

## Cover Automation Model

Cover automation should focus first on light/daylight management. It should not
start by attempting full solar heat gain, glare, security, garage-door, or climate
optimization.

Automatic cover movement is opt-in. Creating cover groups should create useful
native helper/control surfaces, but covers should not begin moving automatically
until cover automation is configured and the cover control switch is enabled.

### Eligible Cover Classes

Default eligible classes for light/daylight automation:

- `blind`
- `shade`
- `curtain`
- `shutter`
- `window`

Default excluded classes for automatic movement:

- `garage`
- `gate`
- `door`
- `damper`
- `awning`

Excluded classes may still receive helper groups and be controlled manually or by
future explicit policy. They should not be included in default daylight/privacy
movement.

### Cover Presets

Cover automation should use editable presets, not a raw state/action matrix as
the first user-facing surface. Presets provide understandable defaults while
still allowing policy adjustment.

Initial presets:

- Daylight.
- Privacy/Sleep.
- Media/Accent.

Daylight preset:

- Purpose: use natural light when appropriate.
- Can open eligible covers in morning/daytime or when occupied/daylight context
  indicates the room should use daylight.
- Must not open covers at night.
- Must not open covers while Privacy/Sleep or Media/Accent is actively blocking.

Privacy/Sleep preset:

- Purpose: preserve privacy or sleep behavior.
- Default related state: sleep.
- May close covers or only block opening, depending on user configuration.
- Wins over Daylight.

Media/Accent preset:

- Purpose: support TV/media/accent use.
- Default related state: accent.
- Can close covers while the state is active.
- Releases when the state clears.
- After release, covers may reopen only if Daylight context allows it and no
  higher-priority block is active.

### Cover Manual Override

Manual cover movement should create a temporary automation hold.

Rules:

- During hold, Magic Areas must not immediately reverse the user action.
- Hold duration should be configurable.
- Manual hold should be visible in debug attributes.
- Manual hold applies to the cover group or member set that was manually changed.

## Adaptive Switching Interaction

Cover movement should be part of the room signal model.

Rules:

- Covers do not directly command lights.
- Lights do not directly command covers.
- Room state and cover policy decide cover movement.
- Light policy reacts to brightness/context changes caused by cover movement.
- Opening covers can be valid daylight/ambient-rise evidence for adaptive
  light-off.
- Closing covers can darken a room and allow advisory/adaptive light-on when the
  light policy says lights should be on.
- Adaptive Lighting remains the owner of brightness/color/sleep appearance for
  lights that are on.
- Cover movement should appear in adaptive-switching debug context so decisions
  are explainable.

Example interaction:

- Accent state turns on for TV viewing.
- Media/Accent cover preset closes covers.
- The room becomes dark.
- Light policy sees accent state and dark room.
- Overhead lights remain suppressed by accent rules.
- Accent lights may turn on if configured for accent.

Example daylight release:

- Accent state clears during the day.
- Media/Accent preset releases the cover block.
- Daylight preset opens covers if daylight context is valid.
- Room lux rises.
- Adaptive light policy may turn off overhead lights after its dwell/min-on and
  attribution rules pass.

## Conflict Resolution

### Fan Conflicts

Multiple controllers target the same fan:

- Use active-reason aggregation.
- Turn on if any targeting reason is active.
- Turn off only when all targeting reasons clear and holds expire.

Cooling active but sleep suppresses cooling:

- Cooling reason becomes inactive or suppressed.
- Fan may still run for humidity or odor if those controllers allow sleep.

Humidity active after area clears:

- If configured `run_until_clear`, keep fan on until humidity clears and hold
  expires.
- If configured `occupancy_only`, clear when occupancy/state clears.
- If configured `post_clear_hold`, run for the configured hold, then clear unless
  the sensor condition remains active and the controller allows continued run.

Odor active without sensor:

- Use explicit post-occupancy/runtime fallback only when configured.
- Do not infer odor without either a signal source or explicit fallback behavior.

Sensor unavailable:

- Apply the controller's unavailable behavior independently.
- Do not let one controller's unavailable sensor turn off a fan needed by another
  active controller.

Manual fan changes:

- This branch should document current behavior first.
- Add a manual override only if tests or live behavior show Magic Areas fighting
  user intent.

### Cover Conflicts

Daylight wants open, Privacy/Sleep wants closed or blocked:

- Privacy/Sleep wins.

Daylight wants open, Media/Accent wants closed:

- Media/Accent wins while active.

Media/Accent clears during valid daylight context:

- Daylight may reopen covers after release if manual hold is not active.

Media/Accent clears at night or during privacy/sleep:

- No automatic reopen.

User manually moves covers:

- Manual hold wins over automation.

Cover opens and room becomes bright:

- Adaptive light policy may turn lights off if its own guards pass.

Cover closes and room becomes dark:

- Advisory/adaptive light policy may turn lights on if occupied/state rules call
  for it.

Physical/security-sensitive cover class:

- No default automatic movement.

## Implementation Stages

### Stage 1: Branch And Plan Baseline

Tasks:

- [x] Create branch `fan-cover-default-automation` from local `main`.
- [x] Keep this plan as the branch's temporary contributor plan.
- [x] Record current fan/cover architecture and intended touchpoints.

Acceptance:

- Plan exists and is decision-complete enough for staged implementation.
- No runtime behavior changes are included in the planning commit.

### Stage 2: Fan Controller Data Model And Pure Policy

Tasks:

- [x] Introduce internal fan controller config/value objects.
- [x] Add pure fan policy evaluation for controller lists.
- [x] Produce active reasons, suppressed reasons, target fan entities, and service
  intent information.
- [x] Map existing single fan threshold config into a generated Cooling controller.

Acceptance:

- [x] Pure unit tests cover cooling, humidity, and odor controller evaluation.
- [x] Multi-reason aggregation prevents premature off.
- [x] Existing cooling behavior is preserved through the new model.

Notes:

- Runtime still uses the legacy single-threshold adapter. Stage 3 is where the
  switch runtime should consume controller-list evaluation.
- The initial pure model supports threshold + hysteresis. Threshold + trend is
  implemented in Stage 6.

### Stage 3: Fan Runtime Integration

Tasks:

- [x] Update fan runtime/control switch to evaluate controller lists.
- [x] Resolve per-controller fan targets.
- [x] Use exact native helper targets where possible.
- [x] Fall back to explicit entity lists where per-controller membership requires
  subsets.
- [x] Preserve the master fan control switch.

Notes:

- The current runtime adapter now evaluates a generated Cooling controller list
  while still targeting the existing native fan helper group. Per-controller
  subset targeting is not complete until multi-role fan config exists.
- Fan control switch debug attributes now expose active, suppressed, inactive,
  and target fan controller details.

Acceptance:

- [x] Existing fan tests pass or are intentionally updated to Cooling semantics.
- [x] Same fan in humidity and odor stays on until both reasons clear.
- [x] Runtime same-fan overlap requires Stage 4 config surfaces or direct runtime
  controller-list injection before it can be fully asserted.
- [x] Runtime debug attributes show active/suppressed reasons.

Notes:

- Runtime now consumes persisted Cooling/Humidity/Odor role configs directly when
  they exist. Legacy Cooling generation remains only as the fallback when no role
  controller config has been saved.
- Per-controller role members are explicit service targets when targeting the
  native all-fan helper would overreach.

### Stage 4: Fan Config Flow

Tasks:

- [x] Keep Fan automation as an intentional submenu.
- [x] Add Cooling, Humidity, and Odor pages.
- [x] Each page configures the same controller schema with role-specific labels and
  defaults.
- [x] Allow the same fan to be assigned to multiple controller roles.
- [x] Reopen existing fan config as Cooling.

Notes:

- Role pages persist under `features.fan_groups.controllers.<role>`.
- Cooling submissions also synchronize the existing legacy fan-group keys so the
  current Cooling runtime adapter remains compatible until runtime consumes the
  multi-role controller configs directly.
- Detection mode now supports `threshold` and `threshold_trend`.

Acceptance:

- [x] Config-flow tests cover selectors, persistence, reopen values, and independent
  role edits.
- [x] Incomplete/invalid controller pages do not persist invalid values.
- [x] Submitted controller pages persist immediately under the current options-flow
  contract.

### Stage 5: Fan Visible Area States

Tasks:

- [x] Add canonical area states `humid`, `odor`, and `hot`.
- [x] Emit these states from active fan controller reasons.
- [x] Ensure state attributes and translated/detail display are consistent.
- [x] Expose active/suppressed fan reasons and target fans in debug attributes.

Notes:

- Fan-derived states are published through a runtime-state dispatcher and merged
  into the canonical area-state entity attributes.
- Fan-derived states represent active controller reasons, not raw fan on/off
  state.
- The area-state entity keeps presence/secondary states as the base state set and
  overlays feature-published runtime states by source.

Acceptance:

- [x] Area-state tests prove fan-derived states appear and clear.
- [x] States reflect controller condition rather than raw fan on/off state.

### Stage 6: Threshold + Trend Helper Support

Tasks:

- [x] Design reusable threshold/trend signal support for sensor-controller
  features.
- [x] Use humidity as the first concrete case.
- [x] Prefer native HA helpers where they can provide trend/rate evidence.
- [x] Keep Magic Areas responsible for interpreting the helper signal.
- [x] Expose `threshold_trend` in the fan controller options-flow detection-mode
  selector.

Notes:

- Fan controllers that select `threshold_trend` declare a Magic Areas-managed
  native Trend helper for the controller sensor.
- Runtime resolves the managed Trend helper by managed-surface unique ID and
  passes the helper's binary state into fan policy evaluation.
- The trend signal supplements threshold/hysteresis. It can activate or hold a
  controller only when the sensor is already inside the hysteresis band; it does
  not activate a fan from below the clear threshold.
- Magic Areas interprets the native helper signal. Home Assistant owns trend
  calculation and helper lifecycle.

Acceptance:

- [x] Humidity threshold-only mode is tested.
- [x] Humidity threshold+trend mode is tested.
- [x] Trend/rate signal supplements threshold/hysteresis rather than replacing
  it.

### Stage 7: Odor/VOC Fallback Runtime

Tasks:

- [x] Add odor sensor threshold behavior.
- [x] Add explicit fallback runtime behavior for rooms without odor/VOC sensors.
- [x] Keep fallback mode opt-in and visible in config.

Notes:

- Sensor-driven odor uses the same controller contract as cooling and humidity:
  selected members, selected signal, detection mode, thresholds, room-state gates,
  clear behavior, and suppression.
- Rooms without an odor/VOC sensor can select `room_state` detection. This mode
  intentionally ignores sensor threshold fields and runs from configured room
  states only.
- Runtime now feeds previous active controller IDs back into policy evaluation so
  hysteresis holds work in the switch path, not only in pure policy tests.

Acceptance:

- [x] Sensor-driven odor and fallback odor runtime are independently tested.
- [x] Odor reason coexists with humidity and cooling.

### Stage 8: Cover Preset Config Model

Tasks:

- [x] Define editable cover presets: Daylight, Privacy/Sleep, Media/Accent.
- [x] Add config readers/defaults.
- [x] Restrict default eligible automation classes to window-light-management
  covers.
- [x] Add manual-hold config.

Notes:

- Cover preset config is intentionally model/config only. Runtime cover movement
  belongs to Stage 9.
- Cover helpers still create the existing native control surfaces; default
  automation eligibility is narrower than helper creation.
- Default automatic cover classes are `blind`, `curtain`, `shade`, `shutter`,
  and `window`.
- `awning`, `garage`, `gate`, `door`, and `damper` are not default automation
  targets.
- Preset state tokens use canonical Magic Areas area-state values, including
  `accented`.

Acceptance:

- [x] Config tests prove presets save and reopen.
- [x] Excluded cover classes are not default automation targets.
- [x] Cover helper surfaces remain unchanged unless needed for policy metadata.

### Stage 9: Cover Runtime Policy

Tasks:

- Implement policy evaluation for cover presets.
- Use existing native cover helper groups as targets.
- Add manual movement detection and hold.
- Keep cover policy from directly commanding lights.

Acceptance:

- Unit tests cover daylight open, privacy block, media close, release behavior,
  and manual hold.
- Cover control switch gates automatic movement.

### Stage 10: Cover + Adaptive Switching Scenario Coverage

Tasks:

- Extend scenario/dev-house tests for cover movement affecting lux.
- Capture traces for cover state, lux state, area states, adaptive guards, and
  light decisions.

Acceptance:

- Cover opening can support adaptive light-off.
- Cover closing can support light-on if occupied/dark.
- Media/Accent cover close does not directly command lights.
- Manual cover movement is not immediately reversed.

## Test Plan

### Fan Unit Tests

- Cooling controller activates above threshold.
- Cooling controller clears below threshold/hysteresis.
- Humidity controller can remain active after occupancy clears.
- Odor controller activates from VOC/air-quality threshold.
- Same fan assigned to humidity and odor stays on until both reasons clear.
- Suppress states block only the configured controller.
- Sensor unavailable behavior is applied per controller.
- Fan decisions never turn off a fan still needed by another active reason.

### Fan Config-Flow Tests

- Fan automation submenu exposes Cooling, Humidity, and Odor pages.
- Controller pages use appropriate selectors.
- Same fan can be selected in multiple controller roles.
- Existing single fan config reopens as Cooling settings.
- Each controller page persists independently.
- Invalid values remain on the form and do not persist.

### Fan Runtime/Platform Tests

- Runtime commands the correct fan helper or entity subset.
- Master fan control switch disables automatic action.
- Runtime debug attributes expose active reasons, suppressed reasons, and target
  fans.
- Managed helper/self-enumeration protections still hold.

### Fan State Tests

- `humid` appears when humidity reason is active and clears when the reason
  clears.
- `odor` appears when odor reason is active and clears when the reason clears.
- `hot` appears when cooling reason is active and clears when the reason clears.
- Fan on/off state alone does not create false room-condition states.

### Cover Unit Tests

- Eligible cover classes are selected for automation.
- Excluded cover classes remain helper/control surfaces only.
- Privacy/Sleep wins over Daylight.
- Media/Accent wins over Daylight while active.
- Media/Accent release can reopen only when Daylight context allows it.
- Manual hold prevents immediate reversal.
- Cover policy emits no light service calls.

### Cover Config-Flow Tests

- Cover preset config saves and reopens.
- Editable presets expose meaningful defaults.
- Manual hold duration saves and reopens.
- Cover automation remains opt-in.

### Scenario Tests

- Bathroom humidity shower run.
- Bathroom odor/VOC run.
- Humidity + odor overlap.
- Cooling fan occupancy run.
- Sleep suppresses configured fan reason.
- Morning/daylight cover open.
- Evening/night no-open or close.
- Accent/media cover close and release.
- Cover open contributes to adaptive light-off.
- Cover close contributes to adaptive light-on.

## Branch Exit Criteria

- Fan controller model replaces current single-threshold fan runtime.
- Cooling preserves current default behavior.
- Humidity and odor controllers are implemented with threshold + hysteresis.
- Threshold + trend path is implemented for humidity.
- Fan-derived visible area states are implemented.
- Fan config-flow exposes role/controller pages.
- Cover presets are implemented for eligible window-light cover classes.
- Cover movement is opt-in and manual-hold protected.
- Cover/adaptive-switching scenario coverage exists.
- Full `pytest`, `ruff`, and `mypy` gates pass.
- Temporary plan is updated to closure state before deletion.
- Durable docs are updated only for completed behavior.

## Explicit Non-Goals For This Branch

- Full solar heat gain optimization.
- Sun azimuth/elevation and room-orientation modeling.
- Garage/gate/door automation defaults.
- A global cross-domain arbitration engine replacing domain policies.
- Adaptive Lighting brightness/color changes beyond existing coordination.
- Hidden odor inference without a sensor or explicit fallback config.
