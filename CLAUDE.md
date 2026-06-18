# CLAUDE.md

Repository guidance for coding agents and contributors.

Read `REPOSITORY_WORK_NOTES.md` for the repository's execution, completion,
validation, simulator, and plan-preservation contract.

On a new workstation, follow
`docs/contributing/workstation-bootstrap.md` to restore the Python environment,
private fake-house state, Home Assistant container, and CRG/MCP integration.

## Project overview

Magic Areas is a Home Assistant custom integration that builds presence-aware
area automation on top of HA area concepts.

- Baseline fork point: `d7b5779`
- Runtime architecture is coordinator/snapshot based
- Integration quality target: Bronze
- Python: 3.13+
- Package/dependency manager: `uv`

For baseline deltas, use:

- `docs/migration/README.md`
- `docs/migration/architecture.md`
- `docs/migration/coordinator.md`
- `docs/migration/config-flow.md`
- `docs/migration/tests.md`

For current implementation state, use:

- `docs/contributing/workstation-bootstrap.md`
- `docs/contributing/architecture.md`
- `docs/contributing/runtime-boundaries.md`
- `docs/contributing/development.md`
- `docs/contributing/dev-simulation-guidance.md`
- `docs/contributing/refactoring-guide.md`

## Required commands

Run the full Python validation before commit:

```bash
./scripts/validate.sh
```

Use the basic validation path for a quick static pass:

```bash
./scripts/validate_basic.sh
```

If a change affects room-control behavior, fake-house simulation, scenario
scripts, Adaptive Lighting coordination, native helper reconciliation, or the
expected interpretation of simulation results, update
`docs/contributing/dev-simulation-guidance.md` before committing. Treat that
documentation update with the same importance as tests, `mypy`, and `ruff`.

Useful focused commands:

```bash
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/platforms -q
uv run pytest tests/config_flow -q
uv run pytest tests/snapshots -q
uv run pytest tests/snapshots --snapshot-update
```

## Runtime architecture (current)

### Core flow

1. `custom_components/magic_areas/__init__.py`
   - config entry lifecycle
   - coordinator setup
   - platform forwarding
   - migration entrypoint
2. `custom_components/magic_areas/coordinator/`
   - snapshot creation and refresh cadence
   - lifecycle orchestration (meta-area reload policy/scheduling)
   - entity/presence ingestion
3. `MagicAreasData` snapshot
   - authoritative read model for platforms and entities
4. `custom_components/magic_areas/features/`
   - feature registry + dispatch
   - module-level entity construction contracts
5. platform adapters (`sensor`, `binary_sensor`, `switch`, `light`, etc.)
   - thin HA-facing setup and entity registration

### Boundary model

- `core/`: policy + shared runtime contracts (HA-side effects excluded)
- `coordinator/`: snapshot and lifecycle orchestration
- `features/modules/`: per-feature assembly and dependency declarations
- platform packages: adapter-thin wiring only
- `light_groups/`: light-specific vertical slice built on shared control/group contracts

Do not bypass entry-point APIs with deep side-door imports.

## Configuration architecture

- Options flow is schema-driven and registry-backed.
- Feature schemas/options are module-local in `features/modules/*.py`.
- Generic step routing lives in `config_flows/options_flow.py` and
  `config_flows/steps/feature_config.py`.
- Runtime config access uses:
  - `core.config` for generic area/normalization helpers
  - `features.config` for feature-owned option semantics
- `option_defaults.py` is the default-source surface.

## Testing expectations

- Prefer behavior and contract assertions over private implementation checks.
- Keep snapshot tests meaningful (realistic fixtures, non-empty behavior cases).
- Respect HA immutability and lifecycle constraints in tests.
- Treat warnings and flaky tests as defects.

See also:

- `tests/AGENTS.md`
- `tests/config_flow/AGENTS.md`
- `tests/README.md`

## Coding rules

- Preserve behavior unless the change is explicitly scoped as behavioral.
- Keep policy logic pure and deterministic.
- Route HA side effects through existing runtime executor/helper pathways.
- Avoid long-lived compatibility shims once parity is proven.
- Prefer explicit module boundaries and typed contracts over convenience imports.
- Central modules may contain only shared generic primitives.
- Feature-specific semantics must live in the owning feature slice.
- Add/maintain boundary tests that block imports bypassing module entry points.

## Important files

- `custom_components/magic_areas/__init__.py`
- `custom_components/magic_areas/coordinator/__init__.py`
- `custom_components/magic_areas/coordinator/pipeline/lifecycle.py`
- `custom_components/magic_areas/coordinator/pipeline/snapshot.py`
- `custom_components/magic_areas/features/registry.py`
- `custom_components/magic_areas/features/dispatch.py`
- `custom_components/magic_areas/core/config/__init__.py`
- `custom_components/magic_areas/core/controls/__init__.py`
- `custom_components/magic_areas/core/runtime_model/__init__.py`
- `custom_components/magic_areas/light_groups/__init__.py`

## Documentation intent

- `docs/contributing/*`: explain current code and contribution constraints.
- `docs/migration/*`: explain how current code differs from baseline fork.
- Planning docs are temporary working artifacts and should not be treated as
  reference docs after closure.
