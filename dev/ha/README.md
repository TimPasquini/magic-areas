# Magic Areas Home Assistant Dev Instance

This is a production-like Home Assistant dev instance for checking Magic Areas
in the real HA frontend.

It uses the official Home Assistant container, persistent `/config` storage, the
normal onboarding flow, real config entries, real registries, and the real HA UI.
The only unusual part is that this checkout's `custom_components/magic_areas`
directory is mounted into the container as `/config/custom_components/magic_areas`.

## Requirements

- Docker with the Compose plugin.

## Start

From the repository root:

```bash
./scripts/ha_dev_start.sh
```

Then open:

```text
http://localhost:8123
```

On first launch, Home Assistant will run onboarding and ask you to create a local
user. Runtime data is written to `dev/ha/config/` and is ignored by git.

## Stop

```bash
./scripts/ha_dev_stop.sh
```

## Reset

This destroys the dev HA config, including onboarding/user/config-entry state:

```bash
./scripts/ha_dev_reset.sh
```

The next start recreates `dev/ha/config/` from `dev/ha/seed/`.

## Bootstrap Fake House

After first onboarding, create a long-lived access token in the HA UI:

```text
User profile -> Security -> Long-lived access tokens
```

Then run:

```bash
HA_TOKEN="paste-token-here" ./scripts/ha_dev_bootstrap.sh
```

The bootstrap uses Home Assistant's real websocket API. It creates these areas if
missing:

- Living Room
- Bathroom
- Outside

It then assigns the seeded fake entities to those areas and sets deterministic
initial fake-house states.

The bootstrap is idempotent. Re-running it should update missing/stale area
assignments without destroying the rest of the dev instance.

## What Is Seeded

The seed config intentionally keeps `default_config:` enabled so the dev instance
behaves like normal Home Assistant.

It also creates fake entities useful for Magic Areas setup:

- fake occupancy toggles
- fake sleep/accent toggles
- fake indoor/outdoor lux controls
- template sensors/binary sensors derived from those controls
- template lights backed by input booleans

Create HA areas from the frontend and assign these fake entities/devices to the
areas you want to test. This keeps the dev instance close to real HA usage
instead of depending on committed `.storage` registry internals.

## Development Loop

1. Start the dev instance.
2. Complete HA onboarding.
3. Create a long-lived token.
4. Run `./scripts/ha_dev_bootstrap.sh`.
5. Add/configure Magic Areas through the frontend.
6. Use the fake controls/entities to inspect behavior.
7. Restart the container after Python code changes.

This environment is for frontend/config-flow/manual behavior validation. Pytest
scenario tests still cover deterministic regression cases.
