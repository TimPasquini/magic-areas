# Phase 10 Live Simulation Expansion Plan

This temporary planning document scopes live fake-house simulator expansion.
Do not delete it while this work is active. Before removal, transfer any still
useful decisions, evidence, scenario contracts, or deferred simulator gaps into
`docs/contributing/master-architecture-roadmap-plan.md` or durable simulator
guidance.

## Goal

Expand live Home Assistant fake-house coverage only where it proves behavior
that unit, integration, platform, or snapshot tests cannot adequately prove.

Phase 10 implementation primarily belongs to the external simulator repository:

```text
/home/tim/python_repos/magic-areas-test-simulator
```

The simulator mounts the current Magic Areas working tree from the sibling
checkout by default:

```text
../magic-areas/custom_components/magic_areas
```

That means simulator scenarios should validate the active Magic Areas working
tree without copying integration code into the simulator repository.

## Current simulator state

Simulator repository:

- branch: `phase-10-fan-overlap`
- status at latest update: simulator implementation commits are local and should
  be pushed/protected before branch cleanup
- run commands:
  - `./run.sh`
  - `./run.sh <scenario>`
  - `./run.sh all`

Existing scenario registry in `run.sh`:

- `living-room-demo`
- `control-matrix`
- `disabled-light-controls`
- `adaptive-negative-context`
- `manual-override`
- `presence-hold`
- `adaptive-lighting-manual-release`
- `fan-cover-matrix`
- `cover-brightness-interaction`

Existing fan/cover scenario implementation:

- `scripts/ha_dev_simulation/scenarios/fan_cover.py`

Existing light scenario implementation:

- `scripts/ha_dev_simulation/scenarios/lights.py`

Existing fake-house fixture:

- `dev/ha/seed/packages/fake_house.yaml`
- mirrored historical root package: `packages/fake_house.yaml`

Existing bootstrap/options setup:

- `scripts/ha_dev_bootstrap.py`
- Fan Room and Cover Room are configured through options-flow automation.
- Setup Room is configured as a manual/config-flow validation room and must not
  be repurposed for active simulation scenarios.

Existing timing helpers:

- `scripts/ha_dev_simulation/timing.py`
- New scenarios must use named timing helpers, not ad hoc sleeps.

## Working rules

- Do not add live scenarios merely to duplicate unit or platform tests.
- Every new scenario must name the real Home Assistant behavior it proves.
- Every new scenario must define both positive expected behavior and at least
  one protection against an incorrect outcome.
- Keep active scenarios out of Setup Room.
- Keep simulator implementation in the simulator repository.
- Keep roadmap status and durable simulator guidance in the main Magic Areas
  repository when the scenario changes expected coverage or known gaps.
- Do not run `./run.sh all` automatically; it is long-running. Recommend it to
  the user when full live validation is warranted.

## Candidate assessment summary

| Candidate | Current assessment | Reason |
| --- | --- | --- |
| Explicit room-state odor fallback | Mostly covered; add only if a distinct fallback contract exists | `fan-cover-matrix` already validates odor overlap, humidity clearing while odor remains, VOC unavailable hold, and restore. |
| Cooling fan occupancy path | Implemented in simulator; focused live validation pending | Simulator commit `0139a24` adds Fan Room temperature and cooling fan fixtures, configures a cooling controller, and asserts occupied/hot activation plus hot/unoccupied suppression. |
| Multiple physical fans with overlapping roles | Implemented in simulator; focused live validation passed | Simulator commit `64d6230` adds `fan.fan_room_booster`, maps odor to exhaust+booster, and asserts humidity-only vs odor-overlap behavior. |
| Fan reload/restart behavior | Valid but high-cost candidate | Fan Room options set `reload_on_registry_change`; scenario needs restart/reload mechanics and stable post-reload assertions. |
| Partial position/tilt cover behavior | Not valid until fixture supports position/tilt | Current cover templates expose open/closed booleans only. |
| Cover opening/closing movement states | Not valid until fixture supports transitional states | Current cover templates expose open/closed only; `stop_cover` maps to a boolean state. |
| Richer daylight/time-like cover context | Potentially valid, but clarify policy contract first | Current cover automation uses `cover_room_lux` and secondary dark state, not a richer daylight/time model. |
| Cover reload/restart behavior | Valid but high-cost candidate | Cover Room options set `reload_on_registry_change`; scenario needs restart/reload mechanics and stable post-reload assertions. |
| Membership/class reconciliation | Valid candidate, likely high value | Current Cover Room has eligible and excluded cover device classes, but does not exercise removal/rename/reclassification repair. |
| Combined fan/cover/light/adaptive active room | Defer until a specific cross-domain failure mode exists | Current scenarios already cover each domain separately; a combined room risks becoming a monolithic scenario. |
| Cover-induced brightness affecting adaptive switching | Implemented in simulator; focused live validation passed | Simulator commits `a5b3f0f` and `6116bc1` add a dedicated Cover Brightness Room and fix area assignment for newly registered fake-house entities. |
| Real media-player state | Valid candidate, but do not use Setup Room active scenario | Existing real media player fixture is Setup Room only, which is reserved. Needs a new active scenario room or fixture role. |
| Helper/entity registry repair | Valid candidate, high value, high risk | Needs controlled entity removal/rename/reclassification and deterministic recovery expectations. |
| Config-flow/manual setup validation | Valid as instructions first | Setup Room is reserved for this; start with explicit manual validation instructions before UI automation. |

## Candidate details

### 10.1.1 Explicit room-state odor fallback

Evidence:

- `fan-cover-matrix` raises `input_number.fan_room_voc` while humidity is also
  active and expects `odor` in Fan Room area state.
- It then clears humidity while VOC remains high and expects odor alone to keep
  `fan.fan_room_exhaust` on.
- It also covers VOC unavailable/restored behavior.
- Fan Room options configure an `odor` controller using
  `sensor.fan_room_voc`, `threshold` detection, `run_until_clear`, and
  `hold_until_restored`.

Assessment:

- Mostly covered by the existing live matrix.
- Do not add a new scenario unless the intended "fallback" means a different
  production contract than the existing VOC-overlap and VOC-unavailable paths.

If reopened:

1. Define the exact missing fallback behavior.
2. Add a checkpoint to `fan-cover-matrix` only if the behavior fits the current
   Fan Room model.
3. Otherwise, create a narrow new room/controller fixture only for that missing
   contract.

### 10.1.2 Cooling fan occupancy path

Evidence:

- Current Fan Room fixture has:
  - `sensor.fan_room_humidity`
  - `sensor.fan_room_voc`
  - `fan.fan_room_exhaust`
- Simulator commit `64d6230` added `fan.fan_room_booster` for odor overlap.
- Simulator commit `0139a24` added:
  - `input_number.fan_room_temperature`
  - `sensor.fan_room_temperature`
  - `input_boolean.fan_room_cooling_power`
  - `fan.fan_room_cooling`
  - a Fan Room `cooling` controller using threshold detection and
    `occupancy_only` clear behavior.
- Setup Room has temperature and fan fixtures, but Setup Room is reserved for
  manual/config-flow validation.

Assessment:

- Implemented in simulator commit `0139a24`
  (`feat: add cooling fan simulator coverage`).
- The implementation extends Fan Room rather than using Setup Room.
- Focused live validation is still pending.

Scenario contract:

- Hot while Magic Areas reports the room clear does not activate `fan.fan_room_cooling`.
- Occupied + temperature above threshold activates `fan.fan_room_cooling`.
- Temperature below the hysteresis clear point turns `fan.fan_room_cooling` off.
- Humidity and odor controllers continue to target their existing fans without
  turning on the cooling fan.

Implementation plan:

1. Add fake-house input/sensor/fan entities for the cooling path. Complete in
   simulator commit `0139a24`.
2. Add bootstrap options for a cooling controller. Complete in simulator commit
   `0139a24`.
3. Add trace entities and reset defaults. Complete in simulator commit
   `0139a24`.
4. Add a clearly separated cooling section in `fan-cover-matrix`. Complete in
   simulator commit `0139a24`.
5. Add simulator unit coverage for fixture, options, trace, and reset changes.
   Complete in simulator commit `0139a24`.
6. Run focused live scenario:

   ```bash
   cd /home/tim/python_repos/magic-areas-test-simulator
   ./run.sh fan-cover-matrix
   ```

Validation evidence:

- Simulator unit tests passed:

  ```bash
  uv run --extra test pytest tests/unit -q
  ```

  Result: `29 passed`.
- Simulator Ruff passed:

  ```bash
  uv run ruff check .
  ```

  Result: `All checks passed!`.
- Shell syntax check passed:

  ```bash
  bash -n scripts/ha_dev_init.sh scripts/ha_dev_bootstrap.sh scripts/ha_dev_simulate.sh run.sh
  ```

- Focused live simulator validation has not been run for this cooling slice yet.

### 10.1.3 Multiple physical fans with overlapping roles

Evidence:

- Current Fan Room has two controllers, humidity and odor, but both target
  `fan.fan_room_exhaust`.
- No second Fan Room physical fan exists in the current fixture.

Assessment:

- Implemented in simulator commit `64d6230`
  (`feat: cover overlapping fan targets in simulator`).
- The simulator now adds `fan.fan_room_booster` backed by
  `input_boolean.fan_room_booster_power`.
- Fan Room odor control targets both `fan.fan_room_exhaust` and
  `fan.fan_room_booster`.
- Fan Room humidity control remains scoped to `fan.fan_room_exhaust`.
- Simulator init now refreshes seeded package YAML into an existing runtime
  config before bootstrap, so newly added fake-house entities are available to
  Home Assistant before options-flow automation runs.
- Focused live validation passed after rerun.

Scenario contract:

- Controller A can target fan A.
- Controller B can target fan B.
- Overlap can target both fans or a shared subset without incorrectly toggling
  excluded fans.
- Clearing one controller does not shut off a fan still required by another
  active controller.

Implementation plan:

1. Add second physical fan fixture and trace entity. Complete in simulator
   commit `64d6230`.
2. Extend Fan Room options with overlapping controller members. Complete in
   simulator commit `64d6230`.
3. Add checkpoints for independent activation, overlapping activation, and
   partial clear. Complete in simulator commit `64d6230`.
4. Assert both target fans and non-target fans. Complete in simulator commit
   `64d6230`.
5. Refresh existing runtime package fixtures before bootstrap. Complete in
   simulator commit `64d6230`.
6. Run focused live scenario:

   ```bash
   cd /home/tim/python_repos/magic-areas-test-simulator
   ./run.sh fan-cover-matrix
   ```

Validation evidence:

- Simulator unit tests passed:

  ```bash
  uv run --extra test pytest tests/unit -q
  ```

  Result: `27 passed`.
- Simulator Ruff passed:

  ```bash
  uv run ruff check .
  ```

  Result: `All checks passed!`.
- Focused live simulator validation passed: `./run.sh fan-cover-matrix` completed after bootstrap refreshed seed packages and stored options converged.

### 10.1.4 Fan reload/restart behavior

Evidence:

- Fan Room bootstrap options set `reload_on_registry_change` to `True`.
- Current live scenario does not restart Home Assistant or reload Magic Areas.
- `./run.sh` recreates the HA container for scenario setup, but in-scenario
  restart/reload assertions need explicit mechanics.

Assessment:

- Valid but higher cost.
- Do after lower-risk fixture expansion unless reload/restart is the defect
  being investigated.

Scenario contract:

- Fan Room control surfaces exist after reload/restart.
- Fan controller options persist.
- A post-reload fan trigger still produces the expected fan action.
- No stale duplicate helpers remain.

Implementation plan:

1. Identify the least disruptive reload primitive available through HA service
   calls or simulator scripts.
2. Add a scenario-specific helper rather than embedding Docker calls in a
   scenario body.
3. Assert control surfaces, options-sensitive behavior, and absence of obvious
   duplicate/stale helpers.

### 10.2.1 Partial position and tilt cover behavior

Evidence:

- Current cover fixtures are template covers backed by boolean
  `input_boolean.cover_room_*_open`.
- Current template cover states are only `open` or `closed`.
- No position or tilt input helpers were found in the fixture.

Assessment:

- Not valid to implement as behavior coverage until the simulator supports
  position/tilt-capable cover fixtures.

Implementation plan:

1. Research HA template-cover support for position and tilt in the simulator
   context.
2. Add one position-capable cover fixture and one tilt-capable cover fixture if
   the integration has production behavior to validate.
3. Update bootstrap options and trace/reset entities.
4. Add live assertions only after the fixture exposes real HA position/tilt
   state.

### 10.2.2 Cover `opening` and `closing` movement states

Evidence:

- Current cover fixtures immediately map service calls to boolean open/closed
  helper state.
- `stop_cover` exists but does not create a durable `opening` or `closing`
  runtime state.

Assessment:

- Not valid until the fixture can represent transitional movement states.

Implementation plan:

1. Add movement-state-capable cover fixture support.
2. Add timing helpers for movement windows if real elapsed time is needed.
3. Assert Magic Areas does not misclassify transitional movement as completed
   manual state.

### 10.2.3 Richer daylight/time-like policy context

Evidence:

- Current Cover Room uses `binary_sensor.cover_room_light`, derived from
  `input_number.cover_room_lux`, as the dark/bright secondary state.
- `input_number.outdoor_lux` exists and drives `binary_sensor.outdoor_bright`
  for light-control rooms, but Cover Room does not currently use a richer
  daylight/time context.

Assessment:

- Potential candidate, but the production policy contract must be clarified
  before simulator work.
- Do not add fake time/daylight scaffolding without a specific integration
  behavior to validate.

Implementation plan:

1. Inspect cover policy support for daylight/time inputs.
2. If production behavior exists, add fixture state that drives that policy.
3. Add live assertions for daylight allowed, daylight blocked, and privacy
   override precedence.

### 10.2.4 Cover reload/restart behavior

Evidence:

- Cover Room bootstrap options set `reload_on_registry_change` to `True`.
- Current live scenario does not restart HA or reload Magic Areas.

Assessment:

- Valid but higher cost, similar to Fan Room reload/restart.

Scenario contract:

- Cover control surfaces and native cover groups exist after reload/restart.
- Cover group class membership is preserved.
- Post-reload daylight/privacy/accent action still works.
- No stale duplicate helpers remain.

Implementation plan:

1. Share any reload helper created for fan reload coverage.
2. Assert cover helpers by device class after reload.
3. Run a minimal post-reload cover action.

### 10.2.5 Membership/class reconciliation

Evidence:

- Current Cover Room fixture has eligible classes:
  - blind
  - curtain
  - shade
  - shutter
  - window
- It also has excluded covers:
  - garage
  - door
- Current `fan-cover-matrix` asserts eligible groups move and excluded covers
  remain closed.
- It does not mutate entity registry classifications or remove/rename members.

Assessment:

- Valid and likely high value.
- This should be scoped carefully because registry mutation can make simulator
  state nondeterministic if cleanup is weak.

Scenario contract:

- Helper membership is repaired after member removal, rename, or class
  reclassification.
- Excluded classes stay excluded.
- Repaired groups still execute policy actions.

Implementation plan:

1. Start with a reversible, deterministic membership change.
2. Add cleanup/reset logic before scenario assertions.
3. Assert group membership and behavior after reconciliation.
4. Avoid combining this with reload/restart until simple reconciliation is
   reliable.

### 10.3.1 Combined fan/cover/light/adaptive active room

Evidence:

- Current simulator uses separate rooms for fan, cover, and light/adaptive
  scenarios.
- Existing scenarios already cover each domain independently.

Assessment:

- Defer unless a specific cross-domain defect appears.
- A combined room would be expensive and risks becoming a monolithic scenario
  hub.

If reopened:

1. Define the cross-domain interaction that cannot be proven separately.
2. Add only the minimum fixture needed for that interaction.
3. Keep assertions focused on the cross-domain boundary.

### 10.3.2 Cover-induced brightness affecting adaptive switching

Evidence:

- Current cover state does not feed illuminance into an adaptive-light room.
- Current adaptive-light scenarios already validate ambient rise and direct
  light contamination in light-specific rooms.
- Simulator commit `a5b3f0f` added a dedicated Cover Brightness Room:
  - `cover.cover_brightness_room_blinds`;
  - `sensor.cover_brightness_room_illuminance`;
  - `binary_sensor.cover_brightness_room_light`;
  - managed light-control entities for overhead and all-lights groups;
  - scenario entrypoint `./run.sh cover-brightness-interaction`.
- First focused live run failed because HA had created the new fake-house
  template entities, but simulator bootstrap assigned areas before those
  registry entries were ready. The room therefore had no physical occupancy
  source and no native light group helper.
- Simulator commit `6116bc1` fixes bootstrap by waiting for expected
  fake-house registry entities before assigning them to areas.

Assessment:

- Implemented in simulator commit `a5b3f0f`
  (`feat: add cover brightness interaction simulator`).
- The implementation keeps this separate from the broad cover matrix and models
  the physical interaction directly: opening a cover increases room brightness,
  which lets adaptive light control turn artificial light off.
- Focused live validation passed after the bootstrap fix.

Scenario contract:

- Opening covers increases room brightness through the fake-house pipeline.
- Adaptive light control responds to the resulting brightness only when the
  policy context allows it.
- The cover state, brightness sensor, area-state brightness token, physical
  light, and Magic Areas native light group agree at each checkpoint.

Implementation plan:

1. Add a room or fixture link where cover open state contributes to room lux.
   Complete in simulator commit `a5b3f0f`.
2. Keep it separate from the existing broad cover matrix. Complete in simulator
   commit `a5b3f0f`.
3. Reuse existing adaptive timing helpers and expectation patterns. Complete in
   simulator commit `a5b3f0f`.
4. Assert both cover state and adaptive light result. Complete in simulator
   commit `a5b3f0f`.
5. Wait for newly registered fake-house entities before area assignment.
   Complete in simulator commit `6116bc1`.
6. Run focused live scenario. Passed after simulator commit `6116bc1`:

   ```bash
   cd /home/tim/python_repos/magic-areas-test-simulator
   ./run.sh cover-brightness-interaction
   ```

Validation evidence:

- Simulator unit tests passed:

  ```bash
  uv run --extra test pytest tests/unit -q
  ```

  Result: `30 passed`.
- Simulator Ruff passed:

  ```bash
  uv run ruff check .
  ```

  Result: `All checks passed!`.
- Shell syntax check passed:

  ```bash
  bash -n scripts/ha_dev_init.sh scripts/ha_dev_bootstrap.sh scripts/ha_dev_simulate.sh run.sh
  ```

- First focused live simulator validation failed before commit `6116bc1`:
  Cover Brightness Room remained clear after occupancy input changed, and
  `light.magic_areas_native_light_groups_cover_brightness_room_overhead_lights`
  was missing.
- Focused live simulator validation passed after commit `6116bc1`:
  `./run.sh cover-brightness-interaction` wrote
  `dev/ha/runtime/traces/latest-evaluation.json` and
  `dev/ha/runtime/traces/latest.jsonl` without reporting scenario expectation
  failures.

### 10.3.3 Real media-player state

Evidence:

- A real fake media player exists only as `media_player.setup_room_speaker`.
- Setup Room is reserved for config-flow/manual setup validation.
- Current live scenarios use accent-like state as a stand-in for media/activity.

Assessment:

- Valid candidate, but do not use Setup Room for active simulation.
- Requires a new active media room or an active media fixture in an existing
  scenario room.

Scenario contract:

- Media player on/play state produces the expected area/media state.
- Media player off/idle clears that state.
- The media path does not incorrectly affect unrelated rooms.

Implementation plan:

1. Add an active-room media player fixture outside Setup Room.
2. Add bootstrap/options configuration for media-player groups if needed.
3. Add a narrow scenario or a separate section in a non-Setup active room.

### 10.3.4 Helper/entity registry repair

Evidence:

- Existing simulator bootstrap creates and reconciles many helper surfaces.
- Current scenarios do not intentionally remove, rename, or reclassify helpers
  during a run.

Assessment:

- Valid and high value, but risky.
- Should be implemented after the simpler Phase 10 scenario mechanics are
  stable.

Scenario contract:

- Removing/renaming/reclassifying a managed helper is detected.
- Reconciliation restores the intended helper surface.
- Existing room behavior continues after repair.

Implementation plan:

1. Start with one low-risk helper class.
2. Snapshot pre-change entity IDs and unique IDs.
3. Mutate the registry through HA-supported APIs or deterministic storage
   setup, not ad hoc file edits during a running scenario.
4. Assert repaired surface and behavior.

### 10.4.1 Setup Room reservation

Evidence:

- Setup Room includes broad fixtures: binary sensors, lights, fan, cover,
  climate, media player.
- Roadmap and simulator guidance reserve it for config-flow/manual setup
  validation.

Assessment:

- Already a rule; keep enforcing it.
- Any Phase 10 active scenario that needs fan/cover/media/climate fixtures must
  add or use an active room outside Setup Room.

### 10.4.2 Manual validation instructions

Assessment:

- Valid first step for config-flow/manual setup expansion.
- Lower risk than UI automation and useful for repeatability.

Implementation plan:

1. Document exact Setup Room manual validation steps.
2. Include expected created helpers and control surfaces.
3. Include reset/cleanup expectations.
4. Keep active scenario commands separate from manual setup instructions.

### 10.4.3 UI automation

Assessment:

- Defer until manual instructions are stable.
- Only implement if it does not repurpose Setup Room for active simulation and
  does not add a fragile browser automation burden.

## Recommended implementation order

1. Add simulator-side plan/guidance files or mirror this inventory into the
   simulator repository once write access is available.
2. Add the smallest immediately valid scenario slice:
   - either cooling fan occupancy path;
   - or multiple physical fans with overlapping roles.
3. Add or update simulator unit tests for scenario registry, trace entities,
   reset defaults, and expected options.
4. Run simulator unit tests:

   ```bash
   uv run --extra test pytest
   ```

5. Ask the user to run the focused live scenario, or run it only when explicitly
   approved:

   ```bash
   ./run.sh fan-cover-matrix
   ```

6. Do not run the full live suite automatically. Recommend this command only
   for full live validation:

   ```bash
   ./run.sh all
   ```

## Exit criteria

- Each added live scenario states the real HA behavior it proves.
- Each added scenario uses named timing helpers.
- Setup Room remains excluded from active simulation.
- Simulator unit tests pass.
- Main-repo validation passes when Magic Areas docs or code change.
- Focused live simulator scenario passes with the current Magic Areas working
  tree.
- Full live suite is recommended to the user when the accumulated simulator
  changes justify it.
