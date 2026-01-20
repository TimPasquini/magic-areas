# Config flow refactor

This document explains the config flow changes and why feature configuration is now registry-driven.

## Motivation

The previous options flow was a single, long class with many feature-specific branches. Adding or updating a feature required editing multiple steps, which increased risk and duplicated validation logic.

## What changed

- Added `config_flows/feature_registry.py` to describe each feature in one place.
- Consolidated feature configuration into `async_step_feature_conf`.
- Added consistent schema handling with selectors and validators.
- Reduced feature-specific step methods to thin wrappers.

## Feature registry structure

Each feature entry provides:

- `name`: feature key
- `options`: list of options for schema generation
- `schema`: optional explicit schema
- `merge_options`: whether to merge or replace feature config
- `next_step`: optional follow-up step ID

This keeps per-feature logic declarative and minimal.

## Benefits

- smaller options flow surface area
- fewer branches to test
- clearer separation between feature metadata and flow mechanics

## Reviewer notes

Behavior is unchanged from the user perspective. The refactor is internal only, with tests focused on preserving results rather than step ordering.
