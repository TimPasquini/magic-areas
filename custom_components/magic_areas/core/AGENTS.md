# Core Guidance

This directory contains HA-free helpers and policy logic.

Key rules:
- Keep logic pure and deterministic; no Home Assistant imports.
- Policies should return decisions, not perform side effects.
- Prefer data structures over direct entity access (use snapshot inputs).
- Avoid direct coupling to platforms; platform code should call core helpers.

When refactoring:
- Move decision logic from entities into core policies.
- Keep entity code focused on wiring and HA service calls.
