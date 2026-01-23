Technical primer: Home Assistant integrations (philosophy, practices, expectations)
1) Architectural philosophy

Home Assistant Core is built around Python’s asyncio event loop: integrations schedule work as tasks on the loop, and core APIs are designed so the event loop remains responsive.
As a consequence, integration design emphasizes:

Non-blocking I/O (network/disk/CPU-heavy work must not run in the event loop).

Clear separation between “fetch/update state” and “expose properties” so entity properties are cheap, memory-only reads.

2) Integration packaging model (domain, file structure, discovery locations)

An integration is a Python package under a unique domain directory. The minimal structure is manifest.json and __init__.py, with platform files like light.py, sensor.py, etc.
Home Assistant loads integrations from:

<config directory>/custom_components/<domain>

homeassistant/components/<domain> (built-in/core)

3) manifest.json as the contract surface

Each integration declares metadata and dependencies in manifest.json.
Common fields include domain/name, dependencies, Python package requirements, issue tracker, IoT class, and (for graded integrations) quality_scale.

4) Configuration philosophy: UI-driven config entries + flows
Config entries (persistent config)

Home Assistant expects integrations to store configuration as config entries created via the UI, with defined lifecycle behavior (loaded/setup retry/setup error/unload, etc.).
Core setup calls async_setup_entry(hass, entry) for each entry; integrations may also implement async_unload_entry for cleanup.

Config flows (user setup UX + migration boundary)

A config flow handler creates config entries via the UI and controls what data is stored. This reduces the need to “re-validate YAML on startup” and supports migrations when entry versions change.
The config flow is implemented in config_flow.py using the data entry flow framework.

5) Async and threading expectations

When called from coroutines/callbacks, integrations are expected to use hass.async_* APIs and keep work async-native.

Blocking operations must be moved off the event loop (commonly via await hass.async_add_executor_job(...)). Home Assistant has increased detection/reporting of blocking calls (noted in docs as beginning in 2024.7.0).

6) Data acquisition patterns: push vs poll, and coordinators

Home Assistant distinguishes push and poll APIs and provides guidance for each:

For push, subscribe in async_added_to_hass and unsubscribe on remove; disable polling via Entity.should_poll = False.

For polling, implement update() / async_update() (or a coordinator-driven approach) and cache results for property reads.

For multi-entity integrations, the recommended pattern is a single, coordinated fetch using DataUpdateCoordinator so entities share one poll and read from shared cached data.

7) Entities, registries, and stable identity
Entities: “properties don’t do I/O”

Entity properties are expected to return in-memory state only; I/O belongs in update()/async_update() or coordinator refresh logic.

Entity registry: unique_id is durable and scoped correctly

Entities that define unique_id are stored in the entity registry, which stabilizes entity IDs and preserves user customization.
Guidance includes:

unique_id must not be user-changeable.

Do not include the integration domain or platform in the unique_id (HA already scopes by those).

Device registry: devices are composed of entities

Devices are tracked in the device registry; a device is represented by one or more entities and can be modeled as parent/child via via_device when appropriate.
Entities link to devices via device_info during config-entry-based setup, matched by identifiers/connections.

8) Availability and failure semantics

When data cannot be fetched, integrations are expected to reflect that by marking entities unavailable (vs. leaving stale last-known state), and use “unknown” for temporary missing attributes when the device/service is otherwise reachable.
At the config-entry level, Home Assistant distinguishes setup error vs setup retry and will retry with backoff when dependencies are not ready.

9) Service actions and their schema surface

If an integration registers service actions, it is expected to define them in services.yaml (for documentation/validation and UI).
Developer documentation describes registering services via the service registry APIs.

10) Internationalization expectations

User-facing strings are expected to be translatable; custom integration localization follows backend translation file conventions and language codes follow BCP47. Validation is commonly done via Hassfest.

11) Tooling and contribution hygiene expected by the project

Home Assistant enforces strict style and docstring conventions and uses Ruff in its lint/format checks for submitted code.
Testing is an explicit part of the workflow; the developer docs emphasize running relevant pytest tests and note CI runs the full suite.
Hassfest is used to validate integration metadata and related files (and is available as a validator for custom integrations as well).

12) External library expectation for device/service communication

The developer checklist states that communication to external devices/services must be encapsulated in an external Python library hosted on PyPI, with source distributions available and issue trackers enabled for such libraries.
This is a core maintainability expectation (versioning, reuse, reviewability, supply chain hygiene) rather than a runtime technical constraint.

13) Strict typing in the Home Assistant codebase

Home Assistant’s “strict typing” rule enables strict type checks by adding the integration to .strict-typing. If the integration uses runtime-data, a custom typed config entry (e.g., MyIntegrationConfigEntry) is required and must be used throughout.

14) Quality scale tiers as “enforced expectations” (where they intersect technical design)

The integration quality scale is a framework grading integrations across user experience, features, code quality, and developer experience, with tiers bronze/silver/gold/platinum.
Bronze is explicitly described as the baseline standard for new integrations and includes (among other criteria) automated tests for setting up the integration.
In practice, many tier rules are implemented as technical constraints (async behavior, availability semantics, registries, strict typing, dependency design), even when they are presented as “quality” requirements.