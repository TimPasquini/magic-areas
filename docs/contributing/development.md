# Development Guide

This guide covers local setup and the repo-standard commands for development.

## Prerequisites

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/)
- Git

## Initial setup

```bash
git clone <your-fork-or-origin>
cd magic-areas
uv sync --extra dev --extra test
```

## Required quality gates

Run these before committing:

```bash
uv run --extra dev --extra test ruff check custom_components tests scripts
uv run --extra dev --extra test mypy custom_components tests scripts
uv run --extra dev --extra test pytest tests -q
```

Also review `docs/contributing/dev-simulation-guidance.md` before committing
changes that affect room-control behavior, fake-house simulation, scenario
scripts, Adaptive Lighting coordination, native helper reconciliation, or the
expected interpretation of simulation results. Updating that guidance is part of
the quality gate for this class of work, not optional cleanup.

Optional formatting check:

```bash
uv run --extra dev ruff format --check custom_components/magic_areas tests
```

## Common test commands

```bash
# Full suite
uv run --extra test pytest tests -q

# Scenario behavior suite
uv run --extra dev pytest tests/scenarios -q

# Single test file
uv run --extra test pytest tests/unit/test_control_group_executor.py -q

# Snapshot updates (when intentionally changing snapshots)
uv run --extra test pytest tests/snapshots --snapshot-update

# Slowest tests
uv run --extra test pytest tests --durations=10
```

## Working in Home Assistant locally

1. Symlink integration into your HA config:

```bash
ln -s /path/to/magic-areas/custom_components/magic_areas \
      /path/to/ha-config/custom_components/magic_areas
```

2. Restart Home Assistant.

3. Enable debug logs:

```yaml
logger:
  default: info
  logs:
    custom_components.magic_areas: debug
```

## Current project layout (high level)

```text
custom_components/magic_areas/
├── coordinator/          # Snapshot + ingestion lifecycle
├── core/                 # Domain logic and shared runtime abstractions
├── features/             # Feature registry/dispatch/modules
├── config_flows/         # Config/options flow steps and helpers
├── schemas/              # Voluptuous/schema definitions
├── light_groups/         # Light vertical slice (policy/events/entities)
├── core/control_intents/ # Intent/target contracts and Adaptive Lighting helpers
├── binary_sensor/        # Platform adapters
├── sensor/               # Platform adapters
├── switch/               # Platform adapters
└── ...

tests/
├── unit/
├── integration/
├── platforms/
├── snapshots/
└── ...
```

## Development workflow

1. Create a branch.
2. Make a focused change.
3. Add/adjust tests for boundary/behavior contracts.
4. Run required quality gates.
5. Commit with descriptive, scoped message.

## Working with managed HA surfaces

Some Magic Areas features now reconcile Home Assistant-native helper and label
surfaces instead of storing every control surface as a Magic Areas-only entity.

- Feature modules declare desired surfaces through `desired_managed_surfaces`.
- The coordinator applies those surfaces through managed-surface reconciliation.
- Managed helper entities should be edited through Magic Areas configuration,
  not by hand-editing generated HA helper config entries.
- Generated helper entities must stay excluded from source enumeration to avoid
  recursive grouping/aggregation.
- Broad HA label targets are safe only for intentionally broad semantic actions.
  Exact room/role control should prefer native helper targets or explicit entity
  subsets.

## Commit message guidance

Recommended prefixes:
- `refactor:` internal structure or boundary changes
- `fix:` behavior correction
- `test:` test additions/updates
- `docs:` documentation updates
- `chore:` non-functional maintenance

## Troubleshooting

### Dependency issues

```bash
uv cache clean
uv sync --reinstall
```

### Stale test caches

```bash
rm -rf .pytest_cache
find . -type d -name '__pycache__' -prune -exec rm -rf {} +
```

### Type-check cache reset

```bash
uv run --extra dev --extra test mypy --clear-cache custom_components tests scripts
```

### Diagram artifacts

`docs/diagrams/` artifacts are intentionally untracked locally. Generate and
inspect them as needed, but do not commit generated diagram files.

## References

- `CLAUDE.md` (repo workflow + standards)
- `docs/contributing/architecture.md`
- `docs/contributing/dev-simulation-guidance.md`
- `docs/contributing/runtime-boundaries.md`
- `docs/contributing/refactoring-guide.md`
- `docs/contributing/repository-control-contract.md`
