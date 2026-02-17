# Next Steps After Phase 8: Domain Logic Extraction

## Current State (After Phase 8)

Phase 8 successfully removes MagicArea from the platform layer and snapshot:
- ✅ Platforms decouple from the god object
- ✅ MagicArea becomes coordinator-internal (`_area` private)
- ✅ Snapshot API clean (area_config, area_runtime only)

**However**: The god object still exists. It's just relocated to the coordinator.

## The Problem

MagicAreasCoordinator now owns:
```python
coordinator._area.initialize()        # Domain logic (state machine)
coordinator._area.load_entities()     # Domain logic (registry operations)
coordinator._area.get_current_states()# Domain logic (state computation)
```

This violates separation of concerns:
- Coordinator's responsibility: Data fetching and snapshot orchestration
- But it also manages: State transitions, timeouts, listener registration, event dispatch

## The Solution: Phase 9 (Not Yet Planned)

Extract MagicArea logic into **pure functions**:

```python
# Before (stateful object):
coordinator._area.initialize()
coordinator._area.get_current_states()

# After (pure functions):
await initialize_area_state(config, entity_list)
states = compute_area_states(presence_data, occupancy_data)
```

This would make:
- **Coordinator**: True orchestrator (100-120 lines) - orchestrates pure functions
- **core/**: Pure domain functions (state machine, timeouts, presence logic)
- **Tests**: Much easier to test isolated logic without coordinator

## Why It Matters

1. **Testability**: Can test state logic without mocking the entire coordinator
2. **Clarity**: Clear inputs/outputs, no hidden state mutations
3. **Reusability**: State logic can be used outside coordinator context
4. **Maintainability**: No implicit coupling between phases

## Effort Estimate

~3-4 hours to extract:
- State machine (OCCUPIED → EXTENDED → CLEAR transitions)
- Timeout scheduling logic
- Presence sensor selection
- Event payload construction
- Listener lifecycle

This would complete the true decomposition of the god object.
