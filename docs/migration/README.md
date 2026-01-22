# Migration guide

This folder documents the recent refactor work and explains how to review or adopt it. The goal is to make upstream review straightforward by describing intent, impact, and the main structural shifts.

## Scope

The documents cover:

- the new coordinator-based data flow
- changes to config flow structure and feature metadata
- testing strategy and coverage improvements
- high-level architecture before and after the refactor

## Bronze tier context

The refactor is written with the HA Bronze tier in mind:

- UI setup and options flows are tested end-to-end
- baseline coding standards are reinforced
- documentation focuses on step-by-step setup and behavior

## How to use these notes

- Start with `architecture.md` to understand current data flow.
- Read `coordinator.md` to see the purpose and usage of the new snapshot.
- Read `config-flow.md` to understand why feature configuration moved into a registry.
- Read `tests.md` to understand test changes and validation approach.

## Reviewer checklist

- The coordinator does not change external behavior; it centralizes state.
- Platform setup uses coordinator snapshots where available.
- Config flow remains user-facing stable, but internal structure is simplified.
- Tests emphasize observable behavior instead of implementation details.
