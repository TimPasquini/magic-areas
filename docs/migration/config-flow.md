# Config flow differences

This document describes how config and options flow behavior is organized in
the current integration compared to the original fork baseline.

## Original behavior

The options flow used a single, long class with many feature-specific branches.
Adding or updating a feature required touching multiple methods and duplicating
validation logic across steps.

## Current behavior

Feature configuration is registry-driven:

- `config_flows/feature_registry.py` declares each feature in one place.
- `async_step_feature_conf` handles feature configuration generically.
- schemas, selectors, and validators are built consistently.
- feature-specific step methods remain thin wrappers when needed.

## Feature registry structure

Each feature entry provides:

- `name`: feature key
- `options`: list of options for schema generation
- `schema`: optional explicit schema
- `merge_options`: whether to merge or replace feature config
- `next_step`: optional follow-up step ID

This keeps per-feature logic declarative and easier to maintain.

## User-facing behavior

From the user perspective, UI setup and options flow remain stable. The
differences are internal: feature metadata is centralized and the flow logic is
less error-prone.
