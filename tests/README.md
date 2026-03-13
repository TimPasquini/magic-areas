# Tests Overview

This directory contains the integration's automated test suite.

## Layout

```text
tests/
├── conftest.py            # Shared fixtures and integration setup helpers
├── const.py               # Test constants and common area definitions
├── helpers.py             # Test utilities used across suites
├── mocks.py               # Mock entity implementations
├── unit/                  # Pure/core contract tests
├── integration/           # Config-entry, coordinator, lifecycle tests
├── platforms/             # Platform and feature behavior tests
├── config_flow/           # Config/options flow tests
└── snapshots/             # Syrupy snapshot contract tests
```

## Run Commands

Use repository-standard commands:

```bash
uv run pytest tests -q
uv run ruff check custom_components/magic_areas tests
uv run mypy custom_components/magic_areas tests
```

Optional focused runs:

```bash
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/platforms -q
uv run pytest tests/config_flow -q
uv run pytest tests/snapshots -q
```

Update snapshots intentionally:

```bash
uv run pytest tests/snapshots --snapshot-update
```

## Test Expectations

- Prefer behavior-based assertions over private-method assertions.
- Use coordinator snapshot data as the runtime contract.
- Keep fixtures realistic and avoid direct mutation of immutable HA objects
  (ConfigEntry fields, slotted HA internals).
- Treat warnings and flaky behavior as defects; stabilize tests before merge.
