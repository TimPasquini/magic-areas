# Development Guide

This guide covers setting up your development environment and running common development tasks for Magic Areas.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Git

## Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-username/magic-areas.git
cd magic-areas

# Install dependencies using uv
uv sync

# This creates a virtual environment and installs:
# - Runtime dependencies (from manifest.json)
# - Development dependencies (from pyproject.toml)
# - Test dependencies
```

## Running Tests

```bash
# Full test suite with coverage
uv run pytest tests/ --cov=custom_components.magic_areas --cov-report=term-missing

# Run specific test file
uv run pytest tests/integration/test_init.py -v

# Run with parallel execution (faster)
uv run pytest tests/ --numprocesses=auto

# Update snapshots (for snapshot-based tests)
uv run pytest tests/ --snapshot-update

# Show slowest tests
uv run pytest tests/ --durations=10
```

## Code Quality

### Linting

```bash
# Run ruff linter
uv run ruff check custom_components/magic_areas/

# Auto-fix issues where possible
uv run ruff check --fix custom_components/magic_areas/

# Format code
uv run ruff format custom_components/magic_areas/
```

### Type Checking

```bash
# Run mypy type checker
uv run mypy custom_components/magic_areas/
```

### All Quality Checks

```bash
# Run all checks before committing
uv run ruff check custom_components/magic_areas/ && \
uv run ruff format --check custom_components/magic_areas/ && \
uv run mypy custom_components/magic_areas/ && \
uv run pytest tests/ --cov=custom_components.magic_areas
```

## Development Workflow

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the coding standards in [AGENTS.md](../../AGENTS.md)

3. Write tests for new functionality

4. Run quality checks (see above)

5. Commit with descriptive messages:
   ```bash
   git commit -m "feat: add new feature description"
   ```

### Commit Message Format

Follow conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `docs:` - Documentation updates
- `chore:` - Maintenance tasks

### Running in Home Assistant Dev Environment

1. Create a symbolic link to your development checkout:
   ```bash
   # From your Home Assistant config directory
   ln -s /path/to/magic-areas/custom_components/magic_areas \
         custom_components/magic_areas
   ```

2. Restart Home Assistant

3. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.magic_areas: debug
   ```

## Project Structure

See [CLAUDE.md](../../CLAUDE.md) for detailed architecture documentation.

Key directories:
```
custom_components/magic_areas/
├── core/              # Pure domain logic (HA-free)
├── base/              # Base entity classes
├── config_flows/      # Config flow helpers
├── schemas/           # Validation schemas
├── binary_sensor/     # Binary sensor platform
├── sensor/            # Sensor platform
├── light.py           # Light platform
├── switch/            # Switch platform
└── ...

tests/
├── unit/              # Unit tests (pure logic)
├── integration/       # Integration tests (full HA setup)
├── platforms/         # Platform-specific tests
└── config_flow/       # Config flow tests
```

## Adding New Features

See [adding-features.md](adding-features.md) for detailed guidance on adding new features.

## Troubleshooting

### Dependencies Not Installing

```bash
# Clear uv cache and reinstall
uv cache clean
uv sync --reinstall
```

### Tests Failing Locally

```bash
# Ensure you're using Python 3.13+
python --version

# Re-sync dependencies
uv sync

# Clear pytest cache
rm -rf .pytest_cache __pycache__
```

### Type Errors

```bash
# Regenerate mypy cache
uv run mypy --clear-cache custom_components/magic_areas/
```

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [AGENTS.md](../../AGENTS.md) - Comprehensive HA coding standards
- [CLAUDE.md](../../CLAUDE.md) - Project-specific architecture guide
- [Refactoring Guide](refactoring-guide.md) - Current refactoring philosophy
