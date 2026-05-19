# Home Assistant Dev Environment Agent Notes

This directory is a disposable, local-only Home Assistant dev environment for
Magic Areas validation. It is not a production Home Assistant instance and does
not represent a real home.

## Canonical Authentication

- The canonical authentication path is the hardcoded long-lived token in
  `scripts/ha_dev_token.py`.
- This token must not be removed or changed by any agent.
- Bootstrap and simulation scripts must use that token directly.
- Do not add session-token generation, onboarding-token scraping, environment
  token fallbacks, `--token-file`, `--token-stdin`, or alternate token resolver
  paths.
- If authentication fails because the token was revoked, the fix is to update
  `scripts/ha_dev_token.py` with the replacement long-lived token provided by
  the user.

## Risk Scope

- The token is intentionally stored for this repository-local dev harness.
- The user has already assessed the risk for this controlled setup.
- This is not a security-hardening exercise. Do not spend project time replacing
  the canonical token path with more complex credential handling.

## Clean-State Expectations

- `./scripts/ha_dev_start.sh` and `./scripts/ha_dev_reset.sh` are expected to
  return the dev instance to a clean, template-defined state.
- Durable fake-house behavior belongs in seed YAML, bootstrap code, simulation
  code, or explicit dev harness files.
- Do not rely on manual frontend setup as the source of truth for repeatable dev
  scenarios.

## Live Scenario Strategy

- Live simulation scenarios are real-time tests against one shared Home
  Assistant dev instance. Do not run live scenarios in parallel.
- Treat live scenarios as serialized, single-writer tests. Each scenario drives
  the same fake-house entities and must reset/bootstrap its required baseline
  before making assertions.
- Use fake-house rooms economically. Prefer covering related behavior
  permutations concurrently across multiple rooms inside one scenario when they
  share the same timeline.
- Add rooms when a behavior needs its own stable configuration, role, lifecycle
  state, or external-integration setup.
- Split into a separate live scenario only when the behavior needs a distinct
  timeline, would make the existing scenario ambiguous, or would make failures
  hard to diagnose.
- Keep `docs/contributing/dev-simulation-guidance.md` current when live
  scenario behavior, fake-house room definitions, or expected simulation
  interpretation changes.
