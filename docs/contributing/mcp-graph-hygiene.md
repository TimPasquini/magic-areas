# MCP Graph Hygiene

This guide defines the minimum workflow to keep `code-review-graph` output
trustworthy for architecture/risk decisions.

For installation, Codex MCP registration, initial repository registration, and
an explanation of full versus incremental builds, first read
`docs/contributing/workstation-bootstrap.md`.

## Required Build Workflow

Run from repository root:

```bash
code-review-graph build --repo .
code-review-graph postprocess --repo .
code-review-graph status --repo .
```

Then refresh MCP views:

- `mcp__code_review_graph__list_graph_stats_tool`
- `mcp__code_review_graph__get_architecture_overview_tool`

## Sanity Checklist (Must Pass)

Use `mcp__code_review_graph__list_graph_stats_tool` and verify:

- `last_updated` is current for this working session.
- Test nodes are present in substantial volume.
- `TESTED_BY` edges are present in substantial volume.

Do not treat historical graph counts as durable documentation. The expected
numbers change as files, tests, and generated graph schema evolve. If the graph
shows implausibly low counts, especially for tests or `TESTED_BY` edges, do not
trust architecture or impact analysis until graph build/postprocess is rerun.

## Stale-Graph Guard

Treat graph output as stale when any of these are true:

- `last_updated` predates recent structural commits in your current work.
- Architecture output has implausible collapse (for example near-zero
  cross-community edges unexpectedly).
- Query results contradict known code movement from the current branch.

When stale:

1. Re-run build + postprocess commands above.
2. Re-check `list_graph_stats`.
3. Re-run architecture/impact queries only after stats look sane.

## Interpretation Notes

- High warning counts involving `tests-*` communities are commonly
  `test-coupling` signals, not production architecture violations.
- Prioritize production-to-production coupling warnings first.
- Record warning disposition in your active architecture notes as one of:
  - `resolved`
  - `intentional`
  - `deferred`
  - `test-coupling noise`
