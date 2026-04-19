# Commit Models

This folder tracks codebase file-count checkpoints for
`custom_components/magic_areas`.

It keeps:
- exactly 5 fixed reference commits
- the 3 most recent non-reference commits (rolling window)

## Files

- `reference_models.json`: reference commit config (5 required)
- `update_commit_models.py`: refresh script
- `records/*.json`: generated census records
- `INDEX.md`: generated summary table

## Usage

```bash
uv run python docs/metrics/commit_models/update_commit_models.py
```

## Updating the 5th reference

Edit `reference_models.json` and replace the commit/label for
`reference_pending_update` when you provide the final reference commit.
