# Workstation Bootstrap

This guide restores the complete Magic Areas development environment on a new
Linux workstation. It is the canonical machine-migration path for contributors
and coding agents.

The environment has three distinct parts:

1. The main Magic Areas repository.
2. The private nested Home Assistant dev-state repository at
   `dev/ha/config/`.
3. The local `code-review-graph` installation and generated graph database.

Only the first two are transferred through Git. Python environments, the
Adaptive Lighting vendor checkout, containers, and CRG graph data are
reproduced locally.

## 1. Install Host Prerequisites

Required tools:

- Git
- Python 3.13 or newer
- `uv`
- Docker Engine with the Docker Compose plugin
- `code-review-graph`

On Fedora, install Git and basic tooling through `dnf`:

```bash
sudo dnf install git curl
```

Install Docker Engine and the Compose plugin using Docker's current official
Fedora instructions:

<https://docs.docker.com/engine/install/fedora/>

Start Docker and allow the development user to invoke it:

```bash
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in after changing group membership. Verify both Docker and the
Compose plugin before continuing:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Install `uv` using its official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new shell if necessary, then verify:

```bash
uv --version
```

Do not replace the repository's `uv` workflow with a manually managed virtual
environment or ad hoc `pip` installation.

## 2. Restore The Main Repository

Clone the repository and select the branch being worked on. For ordinary
development after fan/cover closeout, start from `main`.

```bash
git clone https://github.com/TimPasquini/magic-areas.git
cd magic-areas
git fetch --all --prune
git switch main
```

Install the locked Python environment:

```bash
uv sync --extra dev --extra test
```

Confirm the checkout before changing anything:

```bash
git status --short --branch
./scripts/validate_basic.sh
```

The handwritten files under `stubs/` are required mypy inputs and must be
present in the clone.

Before changing code, read the repository in this order:

1. `AGENTS.md`, `CLAUDE.md`, and `REPOSITORY_WORK_NOTES.md` for operating rules.
2. `docs/contributing/architecture.md` and
   `docs/contributing/runtime-boundaries.md` for ownership and dependency
   boundaries.
3. `docs/contributing/dev-simulation-guidance.md` and `dev/ha/README.md` before
   changing runtime behavior or the fake house.

At a high level, production policy and runtime abstractions belong under
`custom_components/magic_areas/core/`; feature registration and dispatch belong
under `features/`; Home Assistant platform adapters remain thin; config-flow
code belongs under `config_flows/`; and live fake-house infrastructure belongs
under `scripts/ha_dev_*` and `dev/ha/`. Tests are organized by unit,
integration, platform, scenario, and snapshot responsibilities under `tests/`.
Do not infer finer ownership from directory names alone; verify it against the
architecture documents and CRG.

## 3. Restore The Fake House

`dev/ha/config/` is a private nested Git repository. It preserves the
non-reproducible Home Assistant identity/authentication state needed by the
canonical simulator token as well as selected fake-house configuration state.
It is intentionally not a submodule of the public main repository.

From the main repository root:

```bash
git clone \
  https://github.com/TimPasquini/magic-areas-test-simulator.git \
  dev/ha/config
```

Private-repository authentication must be configured for that clone. Verify the
nested repository independently:

```bash
git -C dev/ha/config status --short --branch
git -C dev/ha/config remote -v
```

The expected branch is `main`, tracking `origin/main`. Do not initialize a new
empty repository at this path and do not copy recorder databases, logs, caches,
or generated container state from the old workstation.

## 4. Start And Bootstrap Home Assistant

First validate the Compose definition and prepare generated/vendor inputs:

```bash
docker compose -f dev/ha/compose.yaml config --quiet
./scripts/ha_dev_prepare.sh
```

The preparation step clones the ignored Adaptive Lighting vendor dependency and
creates seed-backed configuration where needed.

Start the clean fake house in detached mode so an agent does not hold an
interactive terminal open for the lifetime of Home Assistant:

```bash
./scripts/ha_dev_start.sh --detach
```

Inspect readiness without continuously streaming logs:

```bash
docker compose -f dev/ha/compose.yaml ps
docker compose -f dev/ha/compose.yaml logs --tail 100 homeassistant
```

Once Home Assistant is ready at <http://localhost:8123>, bootstrap the
deterministic fake house:

```bash
./scripts/ha_dev_bootstrap.sh
```

The restored nested state should preserve onboarding identity and the canonical
long-lived token used by `scripts/ha_dev_token.py`. If authentication is
rejected, do not invent another token-loading mechanism. Replace the canonical
token only with a user-provided token as documented in `dev/ha/AGENTS.md`.

Run a short infrastructure check before starting a long simulation:

```bash
./scripts/ha_dev_simulate.sh --help
```

Then run only the live scenario required by the task. Live scenarios are
serialized real-time tests and must not run in parallel:

```bash
./scripts/ha_dev_simulate.sh --scenario <scenario-name>
```

Use `./scripts/ha_dev_stop.sh` when the fake house is no longer needed.

## 5. Install And Register CRG

CRG is required infrastructure for architecture work, impact analysis,
structural refactors, and dead-code candidate generation. Agents should install
and use it rather than substituting repeated broad text searches for structural
analysis.

Install it as an isolated `uv` tool:

```bash
uv tool install code-review-graph
code-review-graph --version
```

Register CRG with Codex and register this repository:

```bash
code-review-graph install --platform codex \
  --no-instructions \
  --no-skills \
  --no-hooks
code-review-graph register .
code-review-graph repos
```

The repository already contains its own reviewed CRG and agent instructions, so
the installer must not inject generated replacements into `AGENTS.md` or
`CLAUDE.md`.

Restart Codex after MCP registration if CRG tools are not immediately visible.
The generated `.code-review-graph/` database is local and reproducible; do not
copy or commit it.

## 6. Build The Initial Graph

Run a full build after a fresh clone:

```bash
code-review-graph build --repo .
code-review-graph postprocess --repo .
code-review-graph status --repo .
```

The build parses the repository. Post-processing adds derived flows,
communities, search indexes, and test relationships used by higher-level
queries. A build without post-processing is not a complete architecture
baseline.

Confirm that:

- The update timestamp is current.
- Production and test files are both represented.
- Test relationships are present in meaningful volume.
- Counts are plausible for the current checkout.

Do not encode historical node or edge counts as permanent expected values.

## 7. CRG Working Primer

Use CRG before a structural change to establish context:

- Architecture overview: identify communities, boundaries, hubs, and coupling.
- Symbol callers/callees: verify actual structural relationships before moving
  or deleting code.
- Impact analysis: identify the likely blast radius of a proposed change.
- Dead-code output: generate candidates for direct source investigation.

Use an incremental refresh after a bounded edit:

```bash
code-review-graph update --repo .
code-review-graph postprocess --repo .
code-review-graph status --repo .
```

Use a full rebuild instead of an incremental update when:

- Starting on a newly cloned workstation.
- Changing branches across a large refactor.
- Moving, renaming, or deleting many modules.
- CRG output contradicts known code.
- Closing an architecture phase or producing final structural evidence.

When CRG MCP tools are available, prefer them for:

- Architecture overviews.
- Call-path and dependency questions.
- Change-impact analysis.
- Focused symbol context.
- Comparing structural metrics before and after a refactor.

CRG is not proof that code is dead or safe to remove. Home Assistant callbacks,
entity properties, registries, serialized references, pytest fixtures, and
dynamic dispatch may not appear as ordinary static callers. Every removal
candidate still requires direct `rg` searches, framework-contract review,
serialized-reference checks, tests, and final validation.

Read `docs/contributing/mcp-graph-hygiene.md` before relying on graph results for
an audit or completion claim.

## 8. Final Readiness Check

A migrated workstation is ready only when all of these pass:

```bash
git status --short --branch
git -C dev/ha/config status --short --branch
./scripts/validate.sh
code-review-graph status --repo .
docker compose -f dev/ha/compose.yaml config --quiet
docker compose -f dev/ha/compose.yaml ps
```

The main and nested repositories should each have the intended upstream. The
working trees need not remain permanently clean during active work, but any
pre-existing changes must be identified before an agent begins editing.
