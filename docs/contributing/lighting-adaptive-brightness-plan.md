# Lighting Adaptive Switching Plan

This file was originally named `lighting-adaptive-brightness-plan.md`, but the
feature is adaptive **switching**, not brightness management. The filename is
kept for continuity; the behavior described here is about deciding whether
Magic Areas light roles should turn on/off from brightness-related signals.

Status: active validation/follow-through plan. The architecture foundation it
depends on (labels, native helpers, control-intent targets, and Adaptive
Lighting coordination) is implemented in the current branch.

## Problem Statement

Current light-group behavior treats `BRIGHT` as a hard inhibitor unless `bright` is explicitly assigned for the group. This can suppress needed turn-on in occupied rooms with low in-room lux (for example when `dark_entity` is `sun.sun` during daytime).

The goal is to preserve existing stability while enabling adaptive switching based on
brightness signals without future architecture churn. This is not brightness management:
Magic Areas decides whether light roles should turn on/off, while other systems such as
Adaptive Lighting may still own brightness/color temperature behavior for lights that are
on.

## Goals

- Allow occupied rooms to turn lights on when in-room brightness is low, even during daytime.
- Preserve reliable off behavior for clear/timeout/profile transitions.
- Support users without an outside lux sensor.
- Add an optional path for outside/inside contrast when outside lux exists.
- Avoid feedback-loop oscillation when controlled lights influence in-room lux.

## Non-Goals

- No broad refactor of coordinator/runtime architecture.
- No mandatory new sensors/entities for existing users.
- No breaking default behavior during initial rollout.

## Proposed Switching Model

Current foundation available to this work:

- Light role membership is label-backed (`ma:overhead`, `ma:task`,
  `ma:sleep`, `ma:accent`) with exact native helper targets where available.
- The light intent adapter already handles member-level sleep/accent
  suppression and explicit entity subsets.
- Adaptive Lighting coordination is optional and separate. Adaptive Lighting may
  manage brightness/color/sleep appearance for lights that are on; this plan
  remains responsible only for Magic Areas on/off switching policy.
- Managed HA signal helpers are available through the managed-surface
  reconciler. The first adaptive-switching signal helper is a managed Trend
  helper for ambient-rise evidence.

### Signal Boundary

Adaptive switching should use Home Assistant entities and native helpers as a signal API,
not as the policy engine.

Home Assistant/native helpers answer measured-condition questions:

- Is the room bright according to the selected in-room signal?
- Is lux rising, falling, or stable over a configured helper window?
- Is outside/daylight context available?
- Is the helper warming up, unavailable, or producing a valid signal?

Magic Areas answers room-policy questions:

- Given the active area states, should this light role turn on, stay on, turn off, or do
  nothing?
- Should a bright signal be advisory, inhibiting, or adaptive-off eligible?
- Does sleep/accent/manual override suppress or reshape the target?
- Which role/helper/entity target should receive the command?

This boundary prevents Magic Areas from rebuilding generic rolling-window, trend, and
rate-of-change machinery while keeping the human room-behavior model inside Magic Areas.
Native helpers produce visible, reusable signal entities; Magic Areas consumes those
signals through policy inputs.

### 1) Modes

- `inhibit`:
  - Current behavior; `BRIGHT` may block/turn off.
- `advisory`:
  - `BRIGHT` never directly forces off.
- `adaptive`:
  - `BRIGHT` may force off only after safety checks.

### 2) Signal Inputs

- `inside_brightness`:
  - Prefer threshold binary sensor derived from in-room lux.
- `outside_context`:
  - `sun.sun` (default fallback), optional outside lux sensor, or none.
- `ambient_rise`:
  - Prefer a selected or Magic Areas-managed helper-backed signal, starting with a managed
    Trend helper that indicates inside lux is rising enough.
  - Magic Areas may reconcile the helper bundle itself when the user opts into managed
    adaptive signals, using the same managed-helper ownership and exclusion rules as
    native group/threshold helpers.
  - The existing in-runtime detector is transitional compatibility only and should not be
    expanded before helper-backed signal suitability is decided.

### 3) Adaptive Off Safeguards

- Minimum on-time before bright-driven off.
- Bright dwell/debounce duration.
- Optional outside-inside contrast gating (delta/ratio) when outside lux exists.
- Attribution guard to suppress off decisions after recent controlled-light on/off or brightness/CT changes.

## Fallback Matrix

- Outside lux configured:
  - Use inside brightness + outside/inside contrast rules.
- No outside lux, `sun.sun` available:
  - Use inside brightness + daytime context + dwell/min-on-time.
- Neither outside lux nor sun context:
  - Degrade to advisory-like behavior.

## CRG-Mapped Code Touchpoints

### Primary policy/runtime path

- `custom_components/magic_areas/light_groups/policy.py`
  - `LightGroupPolicy.evaluate` (bright gate and decision logic)
  - `LightGroupPolicy.evaluate_control_context`
  - `LightControlGroupPolicy._evaluate_light_decision`
- `custom_components/magic_areas/light_groups/runtime.py`
  - `evaluate_state_change`
  - `handle_area_state_change`
- `custom_components/magic_areas/light_groups/entities.py`
  - `AreaLightGroup.__init__` policy construction

### Secondary-state and light-context derivation

- `custom_components/magic_areas/binary_sensor/presence.py`
  - `AreaStateTrackerEntity._get_secondary_states`
- `custom_components/magic_areas/core/presence_tracker.py`
  - `compute_secondary_states`

### Lux threshold production

- `custom_components/magic_areas/features/modules/aggregates.py`
  - native aggregate helper and threshold helper desired-surface declaration
- `custom_components/magic_areas/core/aggregates/runtime.py`
  - illuminance aggregate/threshold source calculation
- `custom_components/magic_areas/coordinator/managed_surfaces.py`
  - managed native `threshold` helper reconciliation

### Config and schema surfaces

- `custom_components/magic_areas/light_groups/config.py`
  - light-group feature schema + config constants
- `custom_components/magic_areas/config_flows/steps/feature_config.py`
  - options-flow selectors/form wiring
- `custom_components/magic_areas/translations/en.json`
  - new options labels/descriptions
- `custom_components/magic_areas/option_defaults.py`
  - defaults for added options
- `custom_components/magic_areas/config_keys/area.py`
  - new config keys
- `custom_components/magic_areas/migrations.py`
  - config-entry migration/backfill for new options

### Test surfaces

- `tests/unit/test_core_light_control.py`
  - extend for mode matrix and adaptive safeguards
- `tests/unit/test_light_group_runtime_adaptive_guards.py`
  - runtime guard derivation, outside context, inside brightness, and
    ambient-rise handling
- `tests/unit/test_light_group_runtime_state_change_observability.py`
  - adaptive guard/debug attribute visibility
- `tests/unit/test_signal_helper_surfaces.py`
  - managed ambient-rise signal helper surface construction
- `tests/config_flow/test_config_flow_features_e2e.py`
  - options-flow persistence for new config fields
- `tests/config_flow/test_config_flow_options_runtime.py`
  - mode-specific selector/entity filtering
- `tests/integration/test_native_group_helper_lifecycle.py`
  - managed signal-helper lifecycle and area/registry metadata

## Implementation Phases

### Phase 1: Policy extension (no UI changes yet)

Status: implemented.

- Add mode-aware policy logic in light-group policy.
- Keep default mode = `inhibit`.
- Add tests proving no regressions for current mode.

Exit criteria:
- Existing tests pass unchanged under default mode.
- New tests pass for `advisory` and `adaptive` policy behavior.

Current implementation:

- `LightGroupPolicy` supports `inhibit`, `advisory`, and `adaptive`.
- Default mode remains `inhibit`.
- Unit tests cover advisory turn-on blocking, advisory no-force-off behavior, adaptive
  bright-off gating, and legacy/default bright behavior.

### Phase 2: Adaptive guards

Status: implemented.

- Add min-on-time and bright dwell safeguards.
- Add ambient-rise signal contract and guard hooks.
- Treat helper-backed ambient-rise evidence as input data; keep adaptive on/off policy in
  Magic Areas.

Exit criteria:
- Deterministic tests for dwell/min-on-time.
- No bright-driven off until safeguards are satisfied.

Current implementation:

- Runtime derives min-on, bright-dwell, attribution-hold, outside-context,
  inside-bright, and ambient-rise guard values before calling policy.
- Guard values are passed through `LightPolicySignals`.
- Runtime exposes `adaptive_guards` attributes for observability.
- Ambient-rise now prefers the managed Trend helper when available and valid, with the
  transitional in-runtime detector retained as fallback for helper warm-up/missing state.

### Phase 3: Config + options-flow

Status: implemented.

- Add mode and adaptive settings to light-group config schema.
- Expose selectors in options flow.
- Add translations and defaults.

Exit criteria:
- Options form renders without serializer errors.
- Saved options round-trip correctly.

Current implementation:

- Light-group schema/defaults include brightness mode, adaptive guard durations,
  inside/outside brightness sources, contrast settings, and ambient-rise settings.
- Options flow conditionally exposes advisory/adaptive fields by selected mode.
- Options flow tests cover mode-specific field visibility and saved option preservation.

### Phase 4: Fallback tiers and outside context

Status: implemented.

- Add outside-context source handling (`sun|outside_lux|none`).
- Add optional contrast gating when outside lux exists.

Exit criteria:
- Behavior matches fallback matrix in tests.
- No hard dependency on outside lux sensor.

Current implementation:

- `sun`, `outside_lux`, and `none` outside-context sources are supported.
- Optional outside-bright binary can override source-based checks.
- Outside-lux mode supports minimum lux, outside-inside delta, and outside/inside ratio
  gates.
- Tests cover sun fallback, outside-lux minimums, delta/ratio gates, and binary override.

### Phase 5: Migration and release hardening

Status: implemented for current config version.

- Add minor-version migration for new option keys.
- Validate upgrade from current configs.

Exit criteria:
- Migration tests pass.
- Existing configs preserve behavior unless user opts into new modes.

Current implementation:

- Migration `2.2 -> 2.3` backfills adaptive-switching keys into existing light-group
  feature options.
- Canonical defaults preserve existing behavior with `brightness_mode = inhibit`.
- Managed signal-helper work introduced no additional user option keys, so no new
  migration beyond `2.3` is required for the Trend-helper pilot.

## Known Risks

- Feedback-loop/hunting when in-room sensor is affected by controlled lights.
- Overfitting to one sensor topology (must keep guards configurable).
- Excessive state churn if ambient-rise thresholds are too sensitive.
- Blurring the helper/policy boundary. Native helpers should condition generic signals;
  Magic Areas should not delegate room-specific behavior policy to helper combinations.

## Resolved Questions

- Default mode remains `inhibit`; `advisory` and `adaptive` are opt-in.
- V1 keeps brightness mode at the light-groups feature configuration level rather than a
  per-role override.
- Observability is exposed through `adaptive_guards`, `brightness_mode`, and
  `last_policy_reason` attributes.
- The first Magic Areas-built ambient-rise signal is a managed Trend helper.
- Derivative/statistics helper bundles remain deferred for richer future signals, such as
  numeric lux rate or fan humidity/odor control.

## Initial Recommendation

- Implement mode plumbing and guards first, defaulting to `inhibit`.
- Ship `advisory` and `adaptive` as opt-in.
- Add debug attributes for decision transparency before changing defaults.
- Use the managed Trend helper as the first MA-built adaptive ambient-rise signal. Keep
  derivative/statistics helper bundles available for later richer signal needs rather
  than making the first adaptive pass more complex.

## Current Next Step

The adaptive-switching plan is ready for live validation under opt-in settings
on top of the current intent/label/helper foundation. The next engineering pass
should be bug-fix driven from HA runtime observations, not additional
architecture work, unless testing shows the Trend-helper signal shape is
insufficient.
