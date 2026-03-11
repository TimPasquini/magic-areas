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
uv sync
```

## Required quality gates

Run these before committing:

```bash
uv run ruff check custom_components/magic_areas tests
uv run mypy custom_components/magic_areas tests
uv run pytest ./tests --numprocesses=auto -q
```

Optional formatting check:

```bash
uv run ruff format --check custom_components/magic_areas tests
```

## Common test commands

```bash
# Full suite (parallel)
uv run pytest ./tests --numprocesses=auto -q

# Single test file
uv run pytest tests/unit/test_control_group_executor.py -q

# Snapshot updates (when intentionally changing snapshots)
uv run pytest ./tests --snapshot-update

# Slowest tests
uv run pytest ./tests --durations=10
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
uv run mypy --clear-cache custom_components/magic_areas tests
```

## References

- `CLAUDE.md` (repo workflow + standards)
- `docs/contributing/runtime-boundaries.md`
- `docs/contributing/refactoring-guide.md`
- `docs/notes/theoretical_architecture_map.md`
