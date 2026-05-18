# Magic Areas Home Assistant Dev Instance

This is a production-like Home Assistant dev instance for checking Magic Areas
in the real HA frontend.

It uses the official Home Assistant container, persistent `/config` storage, the
normal onboarding flow, real config entries, real registries, and the real HA UI.
The only unusual part is that this checkout's `custom_components/magic_areas`
directory is mounted into the container as `/config/custom_components/magic_areas`.

## Requirements

- Docker with the Compose plugin.
- Git, for the dev-only Adaptive Lighting component checkout.

## Start

From the repository root:

```bash
./scripts/ha_dev_start.sh
```

Starting through this script always returns the HA dev instance to a clean state:
the current container is stopped, `dev/ha/config/` is deleted, and the config is
recreated from `dev/ha/seed/`. Treat frontend/UI changes as disposable. Any state
needed for repeatable testing belongs in seed YAML, bootstrap code, or another
explicit template under `dev/ha/`.

Then open:

```text
http://localhost:8123
```

On first launch after each clean start, Home Assistant will run onboarding and
ask you to create a local user. Runtime data is written to `dev/ha/config/` and
is ignored by git.

## Stop

```bash
./scripts/ha_dev_stop.sh
```

## Reset

This performs the same clean-state reset used by `ha_dev_start.sh` without
leaving the container running:

```bash
./scripts/ha_dev_reset.sh
```

The next start recreates `dev/ha/config/` from `dev/ha/seed/`.

## Bootstrap Fake House

Bootstrap and simulation scripts use the canonical hardcoded long-lived token in
`scripts/ha_dev_token.py`:

```bash
./scripts/ha_dev_bootstrap.sh
./scripts/ha_dev_simulate.sh
```

This dev environment intentionally does not use session-token generation,
environment-token fallback, token files, or stdin token plumbing. If the local
dev token is revoked, update `scripts/ha_dev_token.py` with the replacement
long-lived token.

The bootstrap uses Home Assistant's real websocket and REST APIs. It creates
these areas if missing:

- Living Room
- Bathroom
- Classic Sun Room
- Classic Sensor Room
- Advisory Sun Room
- Advisory Sensor Room
- Adaptive Sun Room
- Adaptive Binary Room
- Adaptive Lux Room
- Adaptive Ambient Room
- Adaptive Lighting Room
- Outdoor Test

It then assigns the seeded fake entities to those areas, creates the default
Magic Areas config entries, configures the room entries for light-group testing,
and sets deterministic initial fake-house states. The room matrix intentionally
covers classic/inhibit behavior, advisory behavior, adaptive behavior with
deterministic fake daylight, explicit outside binary, outside lux contrast,
ambient-rise gating, and a room that uses Magic Areas-managed Adaptive Lighting
configs.

The bootstrap is idempotent. Re-running it should update missing/stale area
assignments and create missing Magic Areas entries without destroying the rest of
the dev instance. Existing Magic Areas options are not overwritten unless you
explicitly pass:

```bash
./scripts/ha_dev_bootstrap.sh --force-magic-area-options
```

If you only want HA area/entity assignment and fake-state reset, skip Magic Areas
entry creation:

```bash
./scripts/ha_dev_bootstrap.sh --skip-magic-areas
```


## Adaptive Lighting

The dev instance installs the real Adaptive Lighting custom integration into an
ignored vendor checkout at startup:

```text
dev/ha/vendor/adaptive-lighting/
```

`ha_dev_start.sh` and `ha_dev_reset.sh` call
`./scripts/ha_dev_install_adaptive_lighting.sh` through `ha_dev_init.sh`. The
component is mounted into the HA container as
`/config/custom_components/adaptive_lighting`, alongside Magic Areas. Override
the checkout ref with `ADAPTIVE_LIGHTING_REF` if a specific upstream commit or
branch needs to be tested.

The `Adaptive Lighting Room` is configured with Magic Areas light groups in
Adaptive Lighting `manage` mode. Magic Areas should create/update the associated
Adaptive Lighting config entries and keep their light membership aligned with
the MA light roles.

## What Is Seeded

The seed config intentionally keeps `default_config:` enabled so the dev instance
behaves like normal Home Assistant.

It also creates fake entities useful for Magic Areas setup:

- fake occupancy toggles
- fake sleep/accent toggles
- fake indoor/outdoor lux controls
- template sensors/binary sensors derived from those controls
- template lights backed by input booleans

Run the bootstrap after onboarding to create HA areas, assign the fake entities,
and install/configure the default Magic Areas rooms. This keeps the dev instance
close to real HA usage instead of depending on committed `.storage` registry
internals.

## Development Loop

1. Start the dev instance.
2. Complete HA onboarding.
3. Run `./scripts/ha_dev_bootstrap.sh`.
4. Use the fake controls/entities to inspect behavior.
5. Restart the container after Python code changes.

This environment is for frontend/config-flow/manual behavior validation. Pytest
scenario tests still cover deterministic regression cases.

## Timed Fake-House Simulation

After bootstrap, run a timed simulation against the real HA dev instance:

```bash
./scripts/ha_dev_simulate.sh
```

The default `living-room-demo` scenario uses a 30-second base cycle. Lux ramps
last 10 seconds, and each ramp midpoint is aligned to a `:00` or `:30` wall-clock
boundary. Seeded one-minute Magic Areas timing fields such as `extended_time`
and `extended_timeout` are treated as a two-cycle simulation period. The runner
drives the seeded fake input helpers through real HA services and traces
relevant fake inputs, template sensors, Magic Areas entities, native helper
groups, and lights.

Trace output is printed and also written as JSONL:

```text
dev/ha/runtime/traces/latest.jsonl
```

Useful options:

```bash
./scripts/ha_dev_simulate.sh --cycle-seconds 30 \
  --ramp-seconds 10 \
  --state-period-cycles 2 \
  --include-bathroom \
  --trace-entity binary_sensor.some_extra_entity
```

Most Magic Areas dev options that are minute-based are set to one minute by the
bootstrap, which is the shortest practical value for those fields. That maps to
roughly two 30-second simulation cycles.
