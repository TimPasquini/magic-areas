# Dev Simulation Guidance

This document describes Magic Areas' executable scenario tests and local Home
Assistant fake-house environment. Keep it current when changing simulation
coverage, fake-house setup, scenario scripts, or room-control behavior that needs
human inspection.

This is durable contributor guidance, not a temporary feature plan. The active
adaptive switching feature work is tracked separately in
`docs/contributing/lighting-adaptive-switching-plan.md`.

## Purpose

Magic Areas behavior is increasingly room-level instead of entity-level. Correct
behavior depends on signals changing together over time:

- occupancy and clear timing
- area states such as occupied, extended, sleep, accent, dark, and bright
- indoor brightness and outdoor/daylight context
- controlled light output versus manual light output
- Adaptive Lighting switch/control state
- native HA helper output
- labels, groups, and reconciled helper membership
- future cover, fan, media, and cross-domain control signals

Many defects only show up when those signals interact in sequence. The project
therefore uses two complementary simulation layers:

- `tests/scenarios/` for deterministic pytest regression coverage.
- `dev/ha/` for a real local Home Assistant fake-house instance that supports
  human inspection and timed live simulation.

Neither layer replaces normal unit, platform, or integration tests. Scenario and
fake-house coverage exists to catch behavior that is too broad for isolated unit
checks and too user-facing to reason about from code alone.

## Commit Readiness Requirement

Treat this guidance as part of the normal pre-commit checklist.

When a change affects room-control behavior, fake-house entities, scenario
scripts, Adaptive Lighting coordination, native helper reconciliation, or the
expected interpretation of simulation results, update this document with the
same priority as updating tests, `mypy`, and `ruff`.

Before committing relevant changes, check:

```bash
uv run --extra dev ruff check custom_components/magic_areas tests scripts
MYPYPATH=scripts uv run --extra dev mypy custom_components tests scripts
uv run --extra dev pytest tests/scenarios -q
```

For changes to live HA simulation scripts, also run the applicable fake-house
scenario with:

```bash
./scripts/ha_dev_bootstrap.sh
./scripts/ha_dev_simulate.sh --scenario <scenario-name>
```

Do not leave this document describing old behavior after changing the simulation
surface. If a scenario gap is discovered but not closed, record it in the
coverage gaps section below.

## Test Layers

### Unit Tests

Unit tests cover pure policy and helper correctness.

Examples:

- decision tables
- signal parsing
- label/helper reconciliation primitives
- control-intent resolution functions

### Platform And Integration Tests

Platform and integration tests cover Home Assistant setup and entity behavior.

Examples:

- config-entry setup
- entity registration
- service calls
- native helper creation
- registry metadata
- unload/reload behavior

### Scenario Tests

Scenario tests are room-level behavior tests under pytest.

They answer questions such as:

- What happens when occupancy arrives while brightness is unavailable?
- What happens when daylight rises after Magic Areas turns lights on?
- What happens when sleep and accent states overlap?
- What happens when Adaptive Lighting changes brightness while Magic Areas is
  evaluating daylight rise?

Scenario tests live in:

```text
tests/scenarios/
```

Use this category for timeline/system-behavior tests that are broader than unit
tests. Do not bury scenario behavior inside narrow unit tests just because the
assertion can be written that way.

### Live Fake-House Simulation

The live fake-house environment is the human-inspection layer. It runs a real
Home Assistant container with Magic Areas mounted from this checkout, seeded fake
entities, real registries, real config entries, and the real HA UI.

Use it when behavior depends on real HA runtime ordering, frontend/config-flow
inspection, Adaptive Lighting compatibility, or human judgment about expected
room behavior.

Primary docs and entry points:

- `dev/ha/README.md`
- `dev/ha/AGENTS.md`
- `scripts/ha_dev_start.sh`
- `scripts/ha_dev_bootstrap.sh`
- `scripts/ha_dev_simulate.sh`

## Current Pytest Scenario Coverage

Current executable scenario coverage includes:

- `tests/scenarios/light_scenario_testkit.py`
  - one-room scenario harness
  - Magic Areas config entry setup
  - room events and structured snapshots
- `tests/scenarios/test_light_advisory_brightness.py`
  - advisory brightness behavior for bright, not-bright, invalid startup, and
    recovery
- `tests/scenarios/test_light_adaptive_switching.py`
  - adaptive bright-off gates for dwell, minimum on-time, outside context,
    outside lux contrast, ambient-rise evidence, and attribution hold after
    Magic Areas-controlled light output
- `tests/scenarios/test_light_adaptive_lighting_coordination.py`
  - room-state-driven Adaptive Lighting switch coordination for sleep and accent
    transitions

Scenario tests should read like room stories backed by executable assertions.
Prefer explicit initial conditions, ordered events, named steps, and useful trace
snapshots over opaque direct calls into private implementation details.

## Scenario Trace Expectations

Scenario traces are part of the debugging surface. They should make failures
understandable without reconstructing state from raw HA logs.

Useful trace fields include:

- step name
- occupancy state
- area `states` attribute
- in-room bright signal state
- outdoor context state when present
- Magic Areas light-control switch state when present
- native helper group state
- target member light states
- manual/control ownership state when present
- policy or decision reason when exposed through a stable public/debug surface

Prefer structured dataclasses or dictionaries with useful pytest diffs. Add
artifact files only when inline pytest output becomes too noisy.

## Live Fake-House Model

The live fake house is seeded from `dev/ha/seed/` and configured by
`scripts/ha_dev_bootstrap.py`.

Current room matrix:

- Living Room
- Bathroom
- Classic Sun Room
- Classic Sensor Room
- Advisory Sun Room
- Advisory Sensor Room
- Adaptive Sun Room
- Adaptive Binary Room
- Adaptive Lux Room
- Adaptive Ambient Room
- Adaptive Lighting Room
- Outdoor Test

The fake-house rooms use deterministic input helpers and template entities. The
sun/daylight-style rooms use `binary_sensor.outdoor_bright`, not real `sun.sun`,
so simulation results do not depend on wall-clock time of day.

The live HA config state is ignored by the main repository but tracked locally by
a nested git repo in `dev/ha/config/`. See `dev/ha/README.md` for the local
state-tracking workflow.

## Live Simulation Scenarios

Live scenarios are implemented in `scripts/ha_dev_simulate.py` and driven through
real HA websocket/service calls.

Current scenarios:

```bash
./scripts/ha_dev_simulate.sh --scenario living-room-demo
./scripts/ha_dev_simulate.sh --scenario control-matrix
./scripts/ha_dev_simulate.sh --scenario adaptive-negative-context
./scripts/ha_dev_simulate.sh --scenario manual-override
./scripts/ha_dev_simulate.sh --scenario presence-hold
```

Current live-simulation coverage:

- Dark occupied rooms turn configured overhead lights on.
- Classic brightness behavior turns overhead lights off when the room becomes
  bright.
- Advisory brightness behavior does not force overhead lights off when the room
  becomes bright.
- Advisory daylight-context behavior still allows occupancy-on overhead lighting
  when the advisory in-room brightness signal is not bright.
- Adaptive brightness behavior turns overhead lights off when configured outside
  context and timing gates are satisfied.
- Adaptive outside-context negative cases are asserted for outside binary not
  bright, outside lux below minimum, and outside lux with insufficient contrast.
- Adaptive ambient-rise behavior rejects artificial rise caused by in-room light
  output, then accepts a later daylight-style rise after attribution clears.
- Accent state suppresses overhead lights and turns accent-role lights on.
- Sleep state suppresses overhead lights and turns sleep-role lights on.
- Sleep plus accent overlap preserves lights that belong to both suppressive
  roles.
- Clear/empty behavior is asserted after occupancy, sleep, and accent inputs
  turn off and configured clear timing settles.
- Native HA light helper groups are asserted along with member lights.
- A real Adaptive Lighting integration instance is present, and Magic Areas sleep
  state is asserted to turn on the managed all-lights AL sleep-mode switch.
- Manual light turn-off while occupied releases Magic Areas control and blocks
  automatic reacquire during bright/dark state churn.
- Clear followed by re-occupancy resets manual override and allows Magic Areas
  to reclaim control.
- Presence hold is asserted as an independent occupancy source while the fake
  occupancy sensor is off, and the room is asserted to clear after the
  presence-hold switch turns off.

## Coverage Gaps

Keep this list current. If a gap is closed, remove or rewrite it in the coverage
section above.

Current high-value gaps:

- Extended-state behavior is incidental rather than directly asserted.
- Manual override timeout without room clear is not covered.
- Adaptive Lighting manual-control release is not covered live.
- Adaptive Lighting role-scoped managed groups are created, but live assertions
  currently check only the all-lights sleep-mode switch.
- Adaptive Lighting `adopt_existing` mode is not covered live.
- Startup `unknown`/`unavailable` sensor behavior is not covered live.
- Disabled Magic Areas light-control switch behavior is not asserted live.
- Ambient-rise false positives from Adaptive Lighting brightness changes are not
  covered.
- Ambient-rise false positives from neighboring/spill-over lights are not
  covered.
- Cover, fan, media, and other future control-domain overlap cases are not
  covered.
- Config flow and frontend behavior are not automated by the fake-house
  simulation.
- Reconciliation behavior after entity/helper/group membership changes is not
  covered by fake-house simulation.

## Extending Scenario Tests

When adding a pytest scenario:

1. Put timeline-style behavior under `tests/scenarios/`.
2. Use existing setup helpers from `light_scenario_testkit.py` when practical.
3. Model room events explicitly instead of calling private policy functions
   directly.
4. Add trace fields that would explain failures for the new behavior.
5. Keep assertions about user-visible behavior or stable debug surfaces.
6. Avoid real sun, real weather, real outdoor lux, or real time of day.

Scenario tests can patch deterministic clocks when adaptive gates need dwell or
minimum-on timing. Prefer existing time helpers before inventing another timing
system.

## Extending The Live Fake House

When adding live simulation coverage:

1. Add deterministic fake entities to `dev/ha/seed/packages/fake_house.yaml`.
2. Add room/config definitions to `scripts/ha_dev_bootstrap.py`.
3. Add scenario-driving logic to `scripts/ha_dev_simulate.py`.
4. Add useful trace entities and expected-state evaluations.
5. Run bootstrap before simulation to ensure the real HA instance matches code.
6. Update `dev/ha/README.md` when commands, rooms, scenarios, or local-state
   expectations change.
7. Update this document with new coverage or remaining gaps.

The live fake house should stay close to actual HA usage. Prefer real HA
registries, config entries, service calls, and integration behavior over private
shortcuts.

## Adaptive Lighting Boundary

Adaptive Lighting manages brightness/color behavior. Magic Areas manages room
role/state intent and coordinates AL control switches where configured.

Simulation should preserve that boundary:

- Magic Areas may create, adopt, and coordinate Adaptive Lighting groups.
- Magic Areas should not reimplement AL brightness/color calculations.
- Scenario coverage should verify that AL-driven brightness changes are not
  mistaken for daylight/ambient rise when the system has enough information to
  distinguish them.

## Cross-Domain Direction

The simulation model should remain extensible beyond lights.

Covers/blinds are a strong future target because occupancy behavior depends on
privacy, daylight, indoor brightness, outdoor brightness, and time-like context.
Opening blinds on occupancy may be correct during daytime and wrong at night.

Fans are another future target because bathroom behavior can involve humidity,
odor, timed holds, threshold triggers, trend/rate triggers, and binary triggers.

Native helpers are part of the intended architecture. Scenario tests should
cover Magic Areas consuming helper outputs rather than recreating every helper
calculation internally.
