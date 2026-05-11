# Lighting Adaptive Brightness Plan

## Problem Statement

Current light-group behavior treats `BRIGHT` as a hard inhibitor unless `bright` is explicitly assigned for the group. This can suppress needed turn-on in occupied rooms with low in-room lux (for example when `dark_entity` is `sun.sun` during daytime).

The goal is to preserve existing stability while enabling richer behavior without future architecture churn.

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

## Proposed Behavior Model

### Signal Boundary

Adaptive brightness should use Home Assistant entities and native helpers as a signal
API, not as the policy engine.

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
  - Prefer a selected or Magic Areas-managed helper-backed signal, such as a trend helper
    or derivative+threshold helper bundle, indicating inside lux is rising enough.
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
  - threshold entity creation path
- `custom_components/magic_areas/binary_sensor/threshold.py`
  - in-room threshold binary sensor behavior

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
  - minor-version migration for new options

### Test surfaces

- `tests/unit/test_core_light_control.py`
  - extend for mode matrix and adaptive safeguards
- `tests/unit/test_core_presence.py`
  - secondary-state behavior and mapping constraints
- `tests/config_flow/test_config_flow_features_e2e.py`
  - options-flow persistence for new config fields
- `tests/integration/test_error_recovery_paths.py`
  - runtime behavior under state/event edge conditions

## Implementation Phases

### Phase 1: Policy extension (no UI changes yet)

- Add mode-aware policy logic in light-group policy.
- Keep default mode = `inhibit`.
- Add tests proving no regressions for current mode.

Exit criteria:
- Existing tests pass unchanged under default mode.
- New tests pass for `advisory` and `adaptive` policy behavior.

### Phase 2: Adaptive guards

- Add min-on-time and bright dwell safeguards.
- Add ambient-rise signal contract and guard hooks.
- Treat helper-backed ambient-rise evidence as input data; keep adaptive on/off policy in
  Magic Areas.

Exit criteria:
- Deterministic tests for dwell/min-on-time.
- No bright-driven off until safeguards are satisfied.

### Phase 3: Config + options-flow

- Add mode and adaptive settings to light-group config schema.
- Expose selectors in options flow.
- Add translations and defaults.

Exit criteria:
- Options form renders without serializer errors.
- Saved options round-trip correctly.

### Phase 4: Fallback tiers and outside context

- Add outside-context source handling (`sun|outside_lux|none`).
- Add optional contrast gating when outside lux exists.

Exit criteria:
- Behavior matches fallback matrix in tests.
- No hard dependency on outside lux sensor.

### Phase 5: Migration and release hardening

- Add minor-version migration for new option keys.
- Validate upgrade from current configs.

Exit criteria:
- Migration tests pass.
- Existing configs preserve behavior unless user opts into new modes.

## Known Risks

- Feedback-loop/hunting when in-room sensor is affected by controlled lights.
- Overfitting to one sensor topology (must keep guards configurable).
- Excessive state churn if ambient-rise thresholds are too sensitive.
- Blurring the helper/policy boundary. Native helpers should condition generic signals;
  Magic Areas should not delegate room-specific behavior policy to helper combinations.

## Open Questions Before Build Start

- Should `adaptive` become the default after validation, or remain opt-in long-term?
- Should we support per-light-group override vs feature-global mode in v1?
- Do we need explicit observability attributes for debugging (mode, dwell timer, last suppression reason)?
- Which helper-backed ambient-rise signal shape should be used first: trend helper,
  derivative helper plus threshold, statistics helper plus threshold, or user-selected
  helper entity?

## Initial Recommendation

- Implement mode plumbing and guards first, defaulting to `inhibit`.
- Ship `advisory` and `adaptive` as opt-in.
- Add debug attributes for decision transparency before changing defaults.
