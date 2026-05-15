# Design Philosophy

This document captures the architectural principles used when evolving
Magic Areas.

## Core premise

Magic Areas is an abstraction layer on top of Home Assistant that reduces
boilerplate automations by organizing behavior around area state, policies,
and grouped control.

## Architectural priorities

1. **Deterministic policy layer**
   - Decision logic should be pure and testable.
   - Policy adapters evaluate canonical context and return canonical decisions.

2. **Coordinator-owned snapshot model**
   - Runtime shaping and ingestion happen under coordinator ownership.
   - Platforms/entities consume snapshot data, not raw registry traversal.

3. **Thin Home Assistant adapters**
   - Platforms/entities should wire HA lifecycle/events.
   - Domain decisions and mapping logic should not live in adapter setup paths.

4. **Single execution boundary**
   - Service calls and runtime side effects are applied by shared executor/runtime
     helpers, not policy modules.

5. **Explicit feature composition**
   - Feature modules are the composition entry points.
   - New behavior should be integrated through module + policy + registry,
     not ad-hoc cross-imports.

6. **Use HA-native primitives where they fit**
   - Home Assistant helpers and labels should own durable storage/display/target
     surfaces when they already model the primitive Magic Areas needs.
   - Magic Areas should own the human abstraction layer: enumeration, guided
     role assignment, desired-surface calculation, reconciliation, and policy.
   - Managed HA surfaces must not become a second independent source of truth.

## Home Assistant-aligned rules

- Keep event loop responsive; no blocking behavior in async paths.
- Keep entity properties in-memory only; avoid property-time I/O.
- Use stable unique identities and registry-driven lookups.
- Reflect availability through coordinator/update outcomes.
- Assign generated helper entities to the appropriate HA area and exclude them
  from Magic Areas source enumeration.

## Refactoring principles

- Preserve behavior while improving structure.
- Prefer removing shims once replacement paths are proven.
- Avoid dual-path runtime behavior except during narrow migrations.
- Favor vertical ownership (clear module boundaries) over convenience imports.

## Testing philosophy

- Contract tests first for boundary changes.
- Parity tests when replacing existing behavior.
- Purity tests for policy layer (no execution-side effects).
- Full suite validation required for structural refactors.

## Decision heuristic

When evaluating a change, ask:

1. Does this reduce cross-module coupling?
2. Does this make ownership clearer?
3. Does this keep policy pure and execution centralized?
4. Can this be validated with focused contract tests?
5. Can Home Assistant already own this storage/display/helper responsibility?

If answers are mostly “no”, redesign the change before merging.
