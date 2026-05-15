# Simulation Scenario Testing Plan

Status: active plan.

Current executable coverage:

- `tests/scenarios/light_scenario_testkit.py` provides the first one-room pytest
  harness.
- `tests/scenarios/test_light_advisory_brightness.py` covers advisory brightness
  behavior for bright, not-bright, invalid startup, and recovery.
- `tests/scenarios/test_light_adaptive_switching.py` covers adaptive bright-off
  gates for dwell, minimum on-time, outside context, outside lux contrast, and
  ambient-rise evidence, plus attribution hold after Magic Areas-controlled
  light output.
- `tests/scenarios/test_light_adaptive_lighting_coordination.py` covers
  room-state-driven Adaptive Lighting switch coordination for sleep and accent
  transitions.

## Purpose

Build a testing and simulation capability for Magic Areas room behavior that supports both automated regression testing and human inspection of complex room-control decisions.

The goal is not only to add more pytest coverage. The goal is to create a development environment where adaptive switching, Adaptive Lighting coordination, covers, fans, labels, native helpers, and future intent-engine behavior can be exercised as room-level scenarios instead of guessed from isolated functions.

The intended direction has two complementary tracks:

1. Executable pytest scenario tests for repeatable CI-friendly regression coverage.
2. A higher-fidelity simulated Home Assistant/fake-house environment for interactive human evaluation when automated assertions are too narrow to define behavior quickly.

The pytest harness should come first because it is fast to build and immediately useful, but it is not a replacement for the richer simulation goal.

## Why This Exists

Magic Areas is moving from simple entity reactions toward room-level intent resolution. Correctness now depends on multiple signals changing over time:

- occupancy
- area states
- indoor brightness
- outdoor brightness or sun context
- controlled light output
- manual override state
- sleep and accent suppression
- Adaptive Lighting switch/control state
- native HA helper output
- future cover/fan domain signals

Many failures only become obvious when these signals interact in a realistic sequence. A human can often understand the desired behavior quickly by watching a simulated room, while an assistant may waste time trying to pre-solve every permutation from code alone. The testing strategy should support both modes.

## Desired End State

Magic Areas should eventually have a practical fake-house/simulation environment where a developer or user can manipulate room conditions and observe Magic Areas behavior without installing into a real house or waiting for real-world conditions.

Desired capabilities include:

- Simulated rooms with Magic Areas config entries.
- Simulated entities assigned to areas through Home Assistant registries.
- Controllable occupancy, lux, binary brightness, time, outdoor context, and domain states.
- Magic Areas-created entities visible in the simulated environment.
- Adaptive Lighting coordination represented well enough to inspect interaction behavior.
- Scenario timelines that can be replayed automatically.
- Human-readable room state displays or traces.
- Ability to extend beyond lights to covers, fans, and future intent-engine behavior.

This does not need to exist all at once. The plan should move toward it deliberately.

## Testing Layers

### Unit Tests

Unit tests remain responsible for pure policy and helper correctness.

Examples:

- policy decision tables
- signal parsing
- label/helper reconciliation primitives
- control-intent resolution functions

### Platform/Integration Tests

Existing Home Assistant integration tests remain responsible for setup and entity/platform behavior.

Examples:

- config-entry setup
- entity registration
- service calls
- native helper creation
- registry metadata
- unload/reload behavior

### Scenario Tests

Scenario tests are room-level behavior tests.

They answer questions like:

- What happens when the room becomes occupied while the brightness helper is unavailable?
- What happens when daylight increases after Magic Areas turns lights on?
- What happens when sleep and accent states overlap?
- What happens when Adaptive Lighting changes brightness while Magic Areas is evaluating ambient rise?

Initial location:

```text
tests/scenarios/
```

This is a distinct category because these tests are not narrow unit tests and should not be blurred into existing integration tests unless a specific scenario is only testing one integration boundary.

### Interactive Simulation

Interactive simulation is the human-inspection layer.

This may eventually be a full fake Home Assistant instance, a scripted HA test instance, a local dashboard-like harness, or another practical environment that lets a human manipulate room conditions and inspect Magic Areas behavior.

This is not optional conceptually. It is part of the desired development capability. The implementation path is open, but the plan should not treat it as something to avoid.

## First Implementation Target

Build a one-room pytest scenario harness first.

This is the first executable step toward the larger simulation capability. It should use the real Home Assistant pytest runtime and existing Magic Areas setup helpers where practical.

The first harness should provide:

- one fake HA area
- one Magic Areas config entry
- mock entities assigned to the room through HA registries
- configurable light-group options
- controllable occupancy and brightness signals
- readable room-level event steps
- structured trace output on failure

This first harness should prove the shape of executable scenarios while producing immediate coverage for adaptive switching work.

## First Room Model

Minimum initial room surface:

- one presence/occupancy signal
- one in-room bright binary signal
- at least one controlled light role, starting with overhead lights
- light-control switch state when relevant
- Magic Areas area-state output
- target member light state
- control/manual ownership state where relevant
- trace state captured at each step

Next additions:

- indoor lux sensor
- outdoor binary bright signal
- outdoor lux sensor
- sleep state
- accent state
- Adaptive Lighting switch set
- deterministic time progression

The first room should be small, but it should be structured as the seed of a fake-house model rather than a throwaway test fixture.

## Scenario Style

Scenarios should read as room stories backed by executable assertions.

A scenario should have:

- a named room setup
- explicit initial conditions
- ordered events
- trace snapshots after meaningful transitions
- assertions phrased around room behavior

Example:

```text
Given Living Room is occupied=false, bright=false, overhead=off
And Magic Areas light control is enabled
When occupancy becomes true
Then overhead lights turn on
And the trace shows occupied + not bright + controlled-on
```

The implementation can use pytest functions, but the scenario code should avoid burying the behavior under setup noise.

## Trace Requirements

Scenario traces are a core part of this work, not decorative output.

A trace should make failures understandable without requiring raw HA log reconstruction.

Initial trace fields:

- step name
- occupancy state
- area states attribute
- in-room bright signal state
- outdoor context state when present
- Magic Areas light-control switch state when present
- light-group state
- target light member states
- manual/control ownership state when present
- policy or decision reason when exposed through a stable surface

Preferred representation:

- structured dataclasses or dictionaries with useful pytest diffs
- inline pytest failure output first
- optional artifacts later if inline traces become too large

## First Scenario Set: Advisory Brightness

The first executable scenario tests should cover advisory brightness because it already produced real-world confusion during HA startup and directly affects whether lights unexpectedly turn on.

Required cases:

1. In-room bright signal is explicitly not bright:
   - Occupancy should allow the configured light role to turn on.

2. In-room bright signal is explicitly bright:
   - Occupancy should not turn on the configured light role.

3. In-room bright signal is `unknown` or `unavailable` during startup:
   - Magic Areas should not treat invalid brightness as affirmative brightness.
   - If the room brightness cannot be determined, advisory mode should fall back to
     ordinary room cues and allow occupied/extended/sleep/accent behavior to proceed.

4. Brightness signal recovers after startup:
   - Once the signal becomes valid and not-bright, normal occupancy behavior should work again.

These cases should run under pytest and provide immediate regression coverage.

## Adaptive Switching Scenario Set

After the first advisory harness works, extend it for adaptive switching.

Required cases:

- bright transition does not immediately turn lights off unless configured adaptive gates are met
- bright dwell gate is respected
- minimum-on gate is respected
- outdoor context gate is respected
- outdoor lux contrast can permit adaptive off when sufficiently strong
- ambient/daylight rise evidence can be required
- Magic Areas-controlled light output is not mistaken for daylight rise
- Adaptive Lighting-driven brightness changes are not mistaken for daylight rise where the system has enough information to distinguish them

The Adaptive Lighting distinction is important because Adaptive Lighting manages brightness/color behavior while Magic Areas manages room role/state intent. The simulation strategy must support observing this boundary.

## Adaptive Lighting Simulation Direction

Adaptive Lighting should be represented in phases.

First phase:

- Use the existing Adaptive Lighting testkit for switch-set coordination where sufficient.
- Verify that Magic Areas can coordinate AL switch/manual-control behavior without needing AL to actually calculate brightness.

Status: partially implemented. Scenario coverage now verifies that a real
one-room light group with an adopted Adaptive Lighting switch set schedules sleep
and accent coordination intents when the Magic Areas light-control switch is
enabled.

Second phase:

- Add enough fake AL behavior to model AL-driven brightness changes over time.
- Use that to test whether Magic Areas can distinguish AL brightness increases from true daylight/ambient rise.

Third phase, if useful:

- Include AL-managed groups in the interactive fake-house environment so a human can inspect the combined behavior.

Magic Areas should not take over Adaptive Lighting’s brightness/color algorithm. The point is to coordinate with it and avoid misinterpreting its effects.

## Future Cross-Domain Simulation

The scenario/simulation model should remain extensible beyond lights.

### Covers / Blinds

Covers are a strong future target because they depend on overlapping room intent:

- daylight use
- privacy
- occupancy
- indoor brightness
- outdoor brightness
- time of day

Example: opening blinds on occupancy may be desirable during bright daytime and wrong at night.

### Fans

Fans are another future target because bathroom behavior can have multiple intents:

- humidity control
- odor/smell control
- timed holds
- threshold or trend triggers
- binary triggers

The scenario harness should not solve fan behavior now, but the structure should not prevent adding it.

### Native Helpers

Magic Areas is increasingly using Home Assistant native helpers as signal/data APIs. Scenario tests should eventually cover the behavior of Magic Areas consuming those helper outputs rather than reimplementing every calculation internally.

## Interactive Simulation Track

The interactive simulation track should be investigated after the first pytest scenario harness exists, not dismissed.

Questions to answer with implementation evidence:

- Can pytest scenario traces provide enough feedback for most behavior design?
- What decisions still require human visual/manual inspection?
- Is a real HA test instance with a fake house practical for this repo?
- Can the fake house reuse the same scenario definitions as pytest tests?
- What UI or dashboard surface would make room state understandable quickly?

Potential direction:

- A scripted HA test configuration with one or more fake rooms.
- Fake entities for lights, sensors, covers, fans, and Adaptive Lighting surfaces.
- Scenario scripts that can drive entity states over time.
- A Lovelace/dashboard view or simple debug surface for room state.
- Reuse of scenario fixtures or data definitions where possible.

The goal is faster behavioral assessment, especially for cases where a human can decide expected behavior more quickly by observing the simulation.

## Implementation Plan

### Stage 1: Create Scenario Test Package

Create:

```text
tests/scenarios/__init__.py
tests/scenarios/light_scenario_testkit.py
tests/scenarios/test_light_advisory_brightness.py
```

The testkit should be small and focused on one-room setup.

Status: implemented for the first light scenario slice.

### Stage 2: Build One-Room Pytest Harness

Use existing Home Assistant pytest helpers and Magic Areas setup paths.

The harness should support:

- room creation
- mock entity registration
- Magic Areas config-entry setup
- light-group feature config
- brightness mode configuration
- event application
- state snapshots
- trace recording

Status: implemented for one Magic Areas room with one occupancy signal, one
inside-bright signal, one controlled overhead light, light-control switch
handling, area-state transition emission, and structured trace snapshots.

### Stage 3: Implement Advisory Brightness Scenarios

Implement the four advisory brightness cases.

This is the first real behavioral value and should not be delayed by designing the entire fake-house environment.

Status: implemented.

### Stage 4: Add Time Control

Add deterministic time support when adaptive switching scenarios need dwell/min-on timing.

Prefer existing timing helpers before inventing a new time system.

Status: implemented for adaptive light-group runtime guard checks by patching
the runtime monotonic clock in scenario tests.

### Stage 5: Implement Adaptive Switching Scenarios

Add adaptive gate scenarios one behavior at a time.

Start with gates that can be modeled with current signals, then add richer AL/daylight attribution when the harness supports it.

Status: partially implemented. Current coverage includes dwell, minimum on-time,
outside context, outside-lux contrast, ambient-rise gating, and attribution hold
after Magic Areas-controlled light output. Remaining richer attribution work:
Adaptive Lighting-driven brightness changes must not be mistaken for daylight
rise.

### Stage 6: Prototype Interactive Fake-House Simulation

After pytest scenarios prove the basic model, prototype a human-inspectable fake-house environment.

This stage should explicitly evaluate whether it can reduce iteration time for behavior design.

It should not be blocked by a requirement to perfectly simulate every HA feature.

## Acceptance Criteria For First Pytest Harness

- `tests/scenarios/` exists.
- A first scenario test file runs directly with pytest.
- The harness creates one room using real Magic Areas setup paths where practical.
- Tests use named room events rather than opaque direct policy calls.
- Advisory brightness behavior is covered for not-bright, bright, invalid startup state, and recovery.
- Failure output identifies the failing step and relevant room state.
- The harness does not require real sun, real weather, real outdoor lux, or real time of day.
- The design can be extended toward adaptive switching, covers, fans, and interactive fake-house simulation.

## Acceptance Criteria For Interactive Simulation Track

The interactive track becomes useful when:

- A fake room can be launched without installing Magic Areas into the user’s real house.
- A human can change occupancy/brightness/outdoor context/time-like inputs.
- Magic Areas behavior can be observed through HA state or a simple debug surface.
- Scenario timelines can be replayed or approximated.
- The environment helps define behavior faster than reading code or logs alone.

## Current Open Questions

- What is the smallest one-room pytest harness that exercises real runtime behavior without bypassing important Magic Areas paths?
- How much Adaptive Lighting behavior needs to be faked before AL-vs-daylight attribution can be tested meaningfully?
- Which trace fields should become mandatory because they actually help diagnose failures?
- Can pytest scenario definitions be reused later by an interactive fake-house environment?
- What form should the interactive fake-house take: HA test instance, scripted local HA config, dashboard-oriented harness, or something else?

## Non-Negotiable Direction

The project should move toward better executable simulation, not away from it.

The first pytest harness is a stepping stone. The richer fake-house/human-inspection environment remains a valid and desired target if it proves useful for behavior design.
