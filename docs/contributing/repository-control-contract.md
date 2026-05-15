# Repository Control Contract and Work Plan

This document is the active contract for reducing repository bloat and
improving human maintainability without re-fragmenting the codebase.

## Scope and fixed decisions (from current code/docs)

These are not open questions for this stream.

- **Compatibility policy**: immediate removal only; no deprecation shims.
- **Enforcement scope**: runtime (`custom_components/magic_areas`) and tests
  (`tests`) both stay in scope for boundary enforcement.
- **Boundary source of truth**:
  - `docs/contributing/runtime-boundaries.md`
  - `docs/contributing/architecture.md`
  - `tests/unit/test_import_boundaries.py`
- **Quality gates**:
  - `uv run ruff check custom_components/magic_areas tests`
  - `uv run mypy custom_components/magic_areas tests`
  - `uv run pytest tests -q`
- **Commit workflow**: run diagram regeneration after each code commit with
  `uv run python docs/diagrams/generate_reference_gexf.py`.

## Control contract (non-negotiable)

1. **No decomposition-first work**
   - Do not add new runtime layers/facades unless the same change deletes a
     larger amount of equivalent complexity.

2. **Net reduction required**
   - Every structural commit stream must reduce at least two of:
     - runtime file count
     - exported symbols (`__all__` and package-root re-exports)
     - boundary-test maintenance surface (LOC + allowlist entries)
     - files touched for a representative feature change

3. **Single ownership**
   - Central modules only hold generic primitives.
   - Feature semantics stay in feature-owned slices.
   - Cross-slice access goes through explicit entry surfaces.

4. **No long-lived compatibility shims**
   - Temporary compatibility paths are allowed only with an explicit removal
     task in the same stream.

5. **Behavior parity gates are mandatory**
   - `uv run ruff check custom_components/magic_areas tests`
   - `uv run mypy custom_components/magic_areas tests`
   - `uv run pytest tests -q`

## Success metrics

### Repository-level

- Lower median files touched for routine changes (target: <= 4 runtime files).
- Declining runtime file count over time (not just movement/churn).
- Reduced high-fanout import hotspots.

### Boundary-level

- No growth in side-door import allowlists.
- No new central re-exports of feature semantics.
- No new direct imports of implementation internals when entry surfaces exist.

### Test-level

- Boundary guard tests remain strict while shrinking maintenance burden.
- Flaky timing-dependent assertions are converted to deterministic intent
  assertions where practical.

## Work plan

## WP-1: Baseline and visibility

Status: **done**

Baseline captured from current tree:
- Runtime `.py` files (`custom_components/magic_areas`): **154**
- `__init__.py` files: **26**
- Exported symbols in `__all__` across `__init__.py`: **189**
- Boundary guard allowlist buckets: **29**
- Boundary guard allowlist entries: **1** (`test_feature_modules`)

Baseline usage note:
- Every structural stream reports delta vs this baseline (or resets baseline if
  a stream achieves net repository reduction and is committed).

## WP-2: Configuration surface compaction

Objective:
- Reduce repeated config accessor/preset wiring while preserving current runtime
  contracts and feature ownership.

Status: **done**

Actions:
- Collapse redundant accessor patterns into shared generic primitives where this
  does not re-centralize feature semantics.
- Remove unused/duplicate config re-exports.

Done when:
- Fewer config helper entrypoints are required for equivalent behavior.
- No feature semantics are moved back into central generic modules.

## WP-3: API/export surface pruning

Objective:
- Make entrypoints small and intentional.

Status: **done**

Actions:
- Audit `__all__` and package-root exports for `core`, `features`, `schemas`,
  platform packages.
- Remove re-exports not required by runtime consumers or tests.
- Keep imports on explicit entry surfaces defined in runtime-boundaries.

Done when:
- Export count decreases with no behavior regression.
- Runtime imports continue to use explicit entry surfaces.

## WP-4: Boundary guard compaction

Objective:
- Keep strict enforcement while reducing guardrail maintenance overhead.

Status: **done**

Actions:
- Continue consolidating repetitive guardrail declarations into compact,
  data-driven structures.
- Remove stale allowlist entries immediately.
- Keep ownership guards aligned with current boundary model:
  - central modules expose only generic primitives
  - feature semantics stay in feature slices
  - side-door imports are blocked in source and tests

Done when:
- Boundary tests remain strict and easier to update safely.

## WP-5: Targeted file collapse

Objective:
- Reduce low-value file fragmentation inside already-stable slices.

Status: **done**

Actions:
- Merge tiny internal-only files that do not provide meaningful ownership
  boundaries.
- Avoid collapsing true entrypoint/API modules.

Done when:
- Runtime file count decreases with unchanged behavior and clearer ownership.

Outcome:
- Completed collapses removed internal-only splits in:
  - `custom_components/magic_areas/core/command_echo.py`
  - `custom_components/magic_areas/binary_sensor/base.py`
  - `custom_components/magic_areas/core/controls/control_group_executor.py`
  - `custom_components/magic_areas/light_groups/lifecycle.py`
  - `custom_components/magic_areas/core/area/area_config.py`
  - `custom_components/magic_areas/core/occupancy/transitions.py`

## WP-5.5: Hotspot recomposition + refactor pass

Objective:
- Recompose and refactor remaining dense hotspots before WP-6 reliability
  hardening, without re-expanding repository sprawl.

Status: **done**

Target files/slices:
- `custom_components/magic_areas/binary_sensor/presence.py`
- `custom_components/magic_areas/coordinator/lifecycle.py`
- `custom_components/magic_areas/light_groups/{entities.py,runtime.py,policy.py}`

Actions:
1. **Presence tracker slice (`binary_sensor/presence.py`)**
   - Separate entity lifecycle/wiring from state-evaluation orchestration.
   - Keep core occupancy/state logic in core modules; keep HA callbacks/entity
     concerns in platform slice.
   - Extract repeated event normalization and timeout wiring into local helpers
     in the same slice (no new global facades).
2. **Coordinator lifecycle slice (`coordinator/lifecycle.py`)**
   - Isolate retry/scheduling policy decisions from side-effecting coordinator
     actions (reload, listener registration, task scheduling).
   - Reduce branch density by moving pure decision paths into deterministic
     helper functions co-located in coordinator slice.
   - Keep public coordinator behavior and callback contracts unchanged.
3. **Light groups slice (`light_groups`)**
   - Tighten ownership split:
     - `policy.py`: policy and runtime effect modeling only
     - `runtime.py`: event parsing, decision execution, listener/setup helpers
     - `entities.py`: thin HA entity adapter surface
   - Eliminate duplicated state-transition glue by funneling through shared
     runtime helpers within the light-groups slice.
4. **Boundary and API guard updates**
   - Update import-boundary tests if entry surfaces change.
   - Do not add convenience re-exports unless runtime consumers require them.

Progress:
- Coordinator lifecycle scheduling path simplified:
  - removed indirection-only `_schedule_policy_callback`
  - removed unused `config_entry_id` parameter from registry filter factories
- Light-group runtime/entity indirection reduced:
  - removed unused entity proxy wrappers around runtime helpers
  - secondary origin-event validation now uses one direct runtime validator path
- Presence tracker slice tightened:
  - centralized coordinator sensor reads in one helper
  - de-duplicated presence sensor listener wiring through one tracking helper
  - centralized meta child-area reads for active/all snapshot paths
  - removed now-redundant loading wrapper and stale no-op returns
  - simplified secondary-state listener input to tracked entity-id list only
  - removed cleanup-only wrapper and wired timer cleanup directly
  - removed redundant meta-area constructor passthrough
  - unified event handling through one tracker-event path
  - split evaluation/apply stages for one internal state-update pipeline
  - consolidated metadata/attribute refresh through one sync path
- Light-group runtime surface narrowed:
  - removed standalone secondary-state handler and folded behavior into
    `process_secondary_group_state_change`
  - removed internal child-control probe helper by inlining parent-state fold
  - inlined parent category-state fold into group event handler path
  - moved turn-on service-data building to entity slice (runtime now policy/event-focused)
  - aligned turn-off command path with turn-on command-echo tracking semantics
- Coordinator lifecycle hardened:
  - `_is_magicareas_entity` now handles malformed IDs defensively
  - config-entry area data merge is localized to registry update handling
  - removed callback-factory indirection; listeners now use local handlers
  - inlined single-use registry relevance helpers into filter closures

Done when:
- No behavior regressions (`ruff`, `mypy`, `pytest -q` all green).
- Hotspot files have lower mixed-responsibility density (fewer unrelated roles
  per file).
- No new side-door allowlist growth in boundary tests.
- No net runtime file-count growth for this workstream.

## WP-6: Reliability hardening tied to compaction

Objective:
- Prevent compactness work from increasing regression risk.

Status: **done**

Actions:
- Convert remaining timing-sensitive behavior assertions to deterministic
  contract assertions where practical.
- Keep broad exception handling narrowed to expected error classes in runtime
  paths.

Progress:
- Broad-exception narrowing is now enforced by boundary guard tests
  (`test_runtime_code_avoids_broad_exception_handlers`).
- Timing-sensitive runtime contract tests were hardened to deterministic waits
  and explicit time jumps in:
  - `tests/integration/test_presence_timeouts.py`
  - `tests/integration/test_area_state_robustness.py`
  - `tests/platforms/test_wasp_in_a_box_logic.py`
  - (reviewed and kept deterministic pattern in)
    `tests/platforms/test_light_complex.py`

Done when:
- Flaky paths are reduced and reliability checks remain green.

## Execution order

1. WP-1 baseline
2. WP-3 API/export pruning (quick wins)
3. WP-4 boundary guard compaction
4. WP-2 config surface compaction
5. WP-5 targeted file collapse
6. WP-5.5 hotspot recomposition + refactor pass
7. WP-6 reliability hardening pass

## Stop conditions

Stop and re-plan if any stream:
- increases runtime file count without a larger same-stream deletion plan,
- increases exported surface area without clear contract justification,
- increases allowlist scope for convenience rather than necessity,
- causes representative blast radius to worsen.

## Commit workflow requirement

After each code commit in this stream:

1. Run quality gates:
   - `uv run ruff check custom_components/magic_areas tests`
   - `uv run mypy custom_components/magic_areas tests`
   - `uv run pytest tests -q`
2. Regenerate rolling diagrams:
   - `uv run python docs/diagrams/generate_reference_gexf.py`
3. Report deltas:
   - file count, export-surface movement, and notable boundary changes.

## Current pre-work assessment

Pre-work is complete enough to execute:
- Baseline metrics are captured.
- Boundary ownership is already codified in docs/tests.
- Immediate-shim-removal policy is fixed.
- No additional design decisions are required before implementation.
