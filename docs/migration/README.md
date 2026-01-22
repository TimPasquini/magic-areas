# Migration guide

This folder documents how the current integration differs from the original
version we forked. The goal is to make upstream review straightforward by
describing what is now different in structure, behavior, and test coverage.

## Scope

These documents describe the current system and its deltas from the original
fork baseline:

- coordinator-based data flow and runtime snapshot usage
- config flow organization and feature metadata structure
- test coverage scope across setup, options, and platform behavior
- high-level runtime architecture in the current state

## Bronze tier context

The current version is written with the HA Bronze tier in mind:

- UI setup and options flows have end-to-end tests
- baseline coding standards are enforced
- documentation focuses on step-by-step setup and expected behavior

## How to use these notes

- Read `architecture.md` for a side-by-side view of original vs current data flow.
- Read `coordinator.md` for the current snapshot model and lifecycle.
- Read `config-flow.md` for how feature configuration is now organized.
- Read `tests.md` for what test coverage looks like in the current state.

## Reviewer checklist

- The coordinator centralizes state, keeping user-facing behavior stable.
- Platforms prefer coordinator snapshots, with fallbacks where needed.
- Config flow remains stable for users while internal structure is simplified.
- Tests emphasize observable behavior across setup and options flows.
