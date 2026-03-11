# Layer 3 Policy Completion Plan

## Objective
Complete Layer 3 (Policy Layer) so all control features use one canonical, pure,
typed policy-evaluation contract with no feature-specific side channels.

Layer 3 done means:
- every feature policy evaluates `ControlGroupContext` and returns
  `ControlGroupDecision`;
- policy inputs are typed payloads rather than ad-hoc signal dict-key lookups;
- runtime transitions (for example, light command-echo state updates) are
  represented in canonical decision metadata;
- policies remain pure and side-effect free (no service calls, no HA writes);
- existing behavior parity is preserved.

## Current State
- Canonical base contracts exist in `custom_components/magic_areas/core/control_group.py`.
- Fan/climate/media/light provide canonical policy adapters using typed signal
  payloads at runtime boundaries.
- Light command-echo transitions are represented as canonical runtime effects
  on `ControlGroupDecision` rather than policy side-channel methods.
- Layer status in `docs/notes/theoretical_architecture_map.md` is `Partial`.

## Decisions (Locked)
1. Canonical policy interface stays in `core/control_group.py`.
2. Policy signals become typed feature payloads (dataclasses).
3. Action mapping remains feature-local (no monolithic global translator).
4. Light control-state transitions are encoded in canonical decision metadata.
5. Policy modules stay pure; execution remains in Layer 4.

## Scope
### In scope
- Contract evolution in `core/control_group.py`.
- Typed signal payload models and parsing at adapter boundaries.
- Policy adapter normalization for light/fan/climate/media.
- Contract and parity tests for Layer 3 behavior.
- Cleanup of now-obsolete policy-side shims/side-channel methods.
- Documentation updates to reflect completion.

### Out of scope
- New end-user behavior/features.
- Config-flow redesign.
- Registry/group-model redesign beyond what Layer 3 requires.

## Implementation Plan

### Workstream A: Canonical contract completion
1. Extend `ControlGroupDecision` with explicit optional runtime-effect metadata.
2. Add a generic runtime-transition model (focused on command-echo transitions,
   but not hardcoded to light domains/services).
3. Keep existing `ControlAction` unchanged unless a hard gap appears.
4. Document purity and determinism requirements in contract docstrings.

Deliverable:
- A single canonical decision model that can express all currently needed policy
  outcomes, including runtime transition instructions.

### Workstream B: Typed policy signals
1. Add feature payload dataclasses:
   - `LightPolicySignals`
   - `FanPolicySignals`
   - `ClimatePolicySignals`
   - `MediaPolicySignals`
2. Parse/normalize runtime inputs into these payloads at adapter boundaries.
3. Remove direct dict-key policy lookups from feature adapter internals.

Deliverable:
- No ad-hoc string-key signal reads in policy evaluation logic.

### Workstream C: Feature policy normalization
1. Fan/climate/media:
   - Ensure adapters consume typed payloads.
   - Ensure adapters return canonical `ControlGroupDecision` only.
2. Light:
   - Keep existing decision semantics.
   - Encode next command-echo transition via decision runtime metadata.
   - Remove side-channel API usage (`next_control_state`) once all call sites
     consume canonical metadata.

Deliverable:
- Uniform policy adapter behavior across all control features.

### Workstream D: Decision/execution boundary hardening
1. Confirm policy modules have no HA service execution paths.
2. Ensure executor/runtime applies all service actions and runtime effects.
3. Ensure no policy module mutates runtime state directly.

Deliverable:
- Clear Layer 3 (decision) / Layer 4 (execution) separation.

### Workstream E: Test suite completion
1. Canonical contract tests:
   - adapter input/output shape and determinism.
2. Light runtime-transition metadata tests:
   - clear, turn_on/turn_off, noop transition handling.
3. Purity tests:
   - no HA side-effects emitted from policy evaluation.
4. Parity tests:
   - fan/climate/media/light behavior remains unchanged.

Deliverable:
- Contract-first unit coverage proving Layer 3 behavior.

### Workstream F: Cleanup and docs
1. Remove obsolete Layer 3 compatibility paths and side channels.
2. Update:
   - `docs/notes/theoretical_architecture_map.md` (`Layer 3` to `Implemented`)
   - `docs/architecture.md` (policy flow)
   - `CLAUDE.md` contributor guidance if needed.

Deliverable:
- No dead/shim policy paths; docs reflect actual architecture.

## Order of Execution
1. Workstream A (contract)
2. Workstream E (contract tests for A)
3. Workstream B (typed signals)
4. Workstream C fan/climate/media
5. Workstream C light
6. Workstream D (boundary hardening)
7. Workstream E parity/purity completion
8. Workstream F cleanup/docs

## Acceptance Criteria
Layer 3 is complete when all are true:
1. All control feature policies evaluate the same canonical context and return
   canonical decision objects.
2. Typed payloads are used for feature signals; no policy-internal string-key
   signal lookups remain.
3. Runtime transition metadata (including light command-echo transitions) is
   represented in canonical decisions and consumed by runtime/execution layer.
4. Policies remain pure and deterministic.
5. Full validation passes on current code:
   - `uv run ruff check custom_components/magic_areas tests`
   - `uv run mypy custom_components/magic_areas tests`
   - `uv run pytest ./tests --numprocesses=auto -q`
6. `docs/notes/theoretical_architecture_map.md` marks Layer 3 `Implemented`.

## Risks and Mitigations
- Risk: behavior regressions in light state transitions.
  - Mitigation: lock parity via focused unit tests before replacing side-channel
    methods.
- Risk: type churn across many call-sites.
  - Mitigation: introduce typed payloads with small adapters and migrate one
    feature at a time.
- Risk: contract overfitting to light-only needs.
  - Mitigation: keep runtime-effect metadata generic and optional.

## Progress Tracking
- [x] Workstream A complete
- [x] Workstream B complete
- [x] Workstream C complete
- [x] Workstream D complete
- [x] Workstream E complete
- [x] Workstream F complete
