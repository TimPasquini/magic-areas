# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Helping with translation

## GitHub is used for (almost) everything

GitHub is used to host code, to track issues and feature requests, as well as accept pull requests. We use [Hosted Weblate](https://hosted.weblate.org/engage/magic-areas/) for translations but old-school pull requests for those are accepted as well.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed (or added) something, update the documentation.
3. Make sure your code lints (see [Development Guide](docs/contributing/development.md) for commands).
4. Test your contribution with `uv run pytest tests/`. Contributions that don't provide tests may take longer to be incorporated.
5. Issue that pull request!

See [docs/contributing/development.md](docs/contributing/development.md) for detailed setup and development instructions.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issues](https://github.com/jseidl/hass-magic_areas/issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](https://github.com/jseidl/hass-magic_areas/issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check formatting and linting
uv run ruff check custom_components/magic_areas/
uv run ruff format --check custom_components/magic_areas/

# Auto-fix issues
uv run ruff check --fix custom_components/magic_areas/
uv run ruff format custom_components/magic_areas/
```

## Development Setup

### Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# Clone and install dependencies
git clone https://github.com/jseidl/hass-magic_areas.git
cd hass-magic_areas
uv sync
```

### Running Tests

```bash
# Full test suite with coverage
uv run pytest tests/ --cov=custom_components.magic_areas

# Run specific tests
uv run pytest tests/integration/test_init.py -v

# Type checking
uv run mypy custom_components/magic_areas/
```

See [docs/contributing/development.md](docs/contributing/development.md) for complete development guide including integration testing with Home Assistant.

If you need help with your environment or understanding the code, join us at our [Discord #developers channel](https://discord.com/channels/928386239789400065/928386308324335666).

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
