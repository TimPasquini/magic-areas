# MCP Graph Hygiene

This guide defines the minimum workflow to keep `code-review-graph` output
trustworthy for architecture/risk decisions.

## Required Build Workflow

Run from repository root:

```bash
uv run code-review-graph build --repo .
uv run code-review-graph postprocess --repo .
```

Then refresh MCP views:

- `mcp__code_review_graph__list_graph_stats_tool`
- `mcp__code_review_graph__get_architecture_overview_tool`

## Sanity Checklist (Must Pass)

Use `mcp__code_review_graph__list_graph_stats_tool` and verify:

- `last_updated` is current for this working session.
- Test nodes are present in substantial volume.
- `TESTED_BY` edges are present in substantial volume.

Current baseline snapshot:

- files: `302`
- nodes: `2479`
- edges: `18321`
- test nodes: `966`
- `TESTED_BY` edges: `5202`
- `last_updated`: session-dependent; verify current value before analysis

If your numbers are drastically lower (especially tests/`TESTED_BY`), do not
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
