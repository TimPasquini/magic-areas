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

To avoid putting the token in shell history or process arguments, store it in an
ignored runtime file and use `--token-file`:

```bash
mkdir -p dev/ha/runtime
printf '%s' 'paste-token-here' > dev/ha/runtime/token
./scripts/ha_dev_bootstrap.sh --token-file dev/ha/runtime/token
```

The bootstrap uses Home Assistant's real websocket and REST APIs. It creates
these areas if missing:

- Living Room
- Bathroom
- Outdoor Test

It then assigns the seeded fake entities to those areas, creates the default
Magic Areas config entries, configures the two room entries for light-group
testing, and sets deterministic initial fake-house states.

The bootstrap is idempotent. Re-running it should update missing/stale area
assignments and create missing Magic Areas entries without destroying the rest of
the dev instance. Existing Magic Areas options are not overwritten unless you
explicitly pass:

```bash
HA_TOKEN="paste-token-here" ./scripts/ha_dev_bootstrap.sh --force-magic-area-options
```

If you only want HA area/entity assignment and fake-state reset, skip Magic Areas
entry creation:

```bash
HA_TOKEN="paste-token-here" ./scripts/ha_dev_bootstrap.sh --skip-magic-areas
```

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
3. Create a long-lived token.
4. Run `./scripts/ha_dev_bootstrap.sh`.
5. Use the fake controls/entities to inspect behavior.
6. Restart the container after Python code changes.

This environment is for frontend/config-flow/manual behavior validation. Pytest
scenario tests still cover deterministic regression cases.
