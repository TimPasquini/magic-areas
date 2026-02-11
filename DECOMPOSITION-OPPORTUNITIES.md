# Decomposition Opportunities

**Date**: 2026-02-11
**Updated**: 2026-02-11
**Status**: In progress
**Context**: Post-Phase 5 refactoring analysis

## Current State

- Phases 1-5 complete
- 393 tests passing, 95% coverage
- Repository HACS/HA compliant
- Core domain logic extracted
- Platform adapters simplified

## Statefulness Classification

Not all targets can be decomposed into stateless functions. Targets that manage temporal state (timeouts, accumulated sensor readings, transition tracking) are **inherently stateful** and should be extracted as **class-based state machines** following the `AreaOccupancyTracker` pattern — not forced into pure functions.

| Target | Statefulness | Approach |
|--------|-------------|----------|
| #1 presence.py | **Stateful** | ✅ Class-based state machine (DONE) |
| #2 wasp_in_a_box.py | **Stateful** | Class-based state machine |
| #3 base/magic.py | Stateless | Pure functions |
| #4 media_player | Stateless | Stateless policy |
| #5 base/entities.py | **Stateful** | Standalone class |
| #6 config_flow.py | Stateless | Pure functions |
| #7 light.py | Stateless | Extend existing policy |

---

## Completed

### 1. binary_sensor/presence.py — AreaOccupancyTracker ✅

**Completed**: 2026-02-11
**Approach**: Class-based state machine (inherently stateful)
**Result**: `core/occupancy.py` — 100% coverage, 53 unit tests
**Key insight**: Presence = what sensors detect. Occupancy = room state (persists through timeouts). The timeout management, sensor tracking, and occupancy decisions are deeply intertwined with accumulated state. Attempts to extract as pure functions failed; succeeded as a cohesive state machine class.

**Files changed**:
- `core/occupancy.py` (new, 126 statements)
- `binary_sensor/presence.py` (817 → 619 lines)
- `tests/unit/test_core_occupancy.py` (new, 53 tests)

---

## Stateful Targets (class-based recomposition)

### 2. binary_sensor/wasp_in_a_box.py — WaspStateMachine

**File**: `custom_components/magic_areas/binary_sensor/wasp_in_a_box.py`
**Primary Class**: `AreaWaspInABoxBinarySensor` (268 lines)

**Why stateful**: Tracks temporal state across door open/close and motion detection events. Manages wasp timers, delay windows, and multi-sensor coordination. State transitions depend on accumulated history (was motion detected while door was open?).

**State owned**:
- `wasp: bool` — motion detected
- `_wasp_timer: ReusableTimer` — timeout state
- `_attr_is_on: bool` — overall presence result
- `_wasp_sensors` / `_box_sensors` — configured sensor lists

**Approach**: Class-based state machine following `AreaOccupancyTracker` pattern

```python
# core/wasp_state_machine.py
@dataclass(slots=True)
class WaspStateUpdate:
    is_present: bool
    wasp_active: bool
    box_open: bool
    request_timer: float | None = None
    cancel_timer: bool = False

class WaspStateMachine:
    """State machine for door+motion presence coordination."""

    def update_wasp(self, wasp_states: dict[str, str]) -> WaspStateUpdate: ...
    def update_box(self, box_states: dict[str, str]) -> WaspStateUpdate: ...
    def update_all(self, wasp_states: dict[str, str], box_states: dict[str, str]) -> WaspStateUpdate: ...
    def on_wasp_timeout(self) -> WaspStateUpdate: ...
    def on_delay_complete(self, box_states: dict[str, str]) -> WaspStateUpdate: ...
```

---

### 5. base/entities.py — ListenerRegistry

**File**: `custom_components/magic_areas/base/entities.py`
**Primary Class**: `MagicGroupEntity` (136 lines)

**Why stateful**: Accumulates listener registrations over the entity lifecycle. The `_group_listeners` list grows during setup and must be drained during teardown. This is lifecycle state management.

**Current problem**: Listener lifecycle management is embedded inside `MagicGroupEntity`, but the need for named, tracked, safely-cleaned-up listeners is not unique to group entities. Currently:

- `MagicGroupEntity` has its own `_group_listeners` list with `track_group_listener()` / cleanup loop — provides named tracking, debug logging, and error-safe removal
- **10+ other entities** across `switch/`, `binary_sensor/`, and `light.py` all register listeners via bare `self.async_on_remove()` calls — no naming, no debug logging, no error handling on removal

**Approach**: Standalone class — `ListenerRegistry` is the authoritative owner of listener lifecycle. `MagicGroupEntity` becomes a consumer, and other entities across the codebase can adopt it too.

```python
# core/listener_registry.py
class ListenerRegistry:
    """Track and clean up event listeners with named debugging."""

    def track(self, name: str, remove_fn: Callable[[], None]) -> None: ...
    def cleanup(self) -> None: ...

    @property
    def count(self) -> int: ...
```

**Consumers** (entities currently using bare `async_on_remove()`):
- `switch/media_player_control.py` — 1 listener
- `switch/climate_control.py` — 2 listeners
- `switch/fan_control.py` — 3 listeners
- `switch/base.py` — 1 listener
- `binary_sensor/presence.py` — 5 listeners
- `binary_sensor/ble_tracker.py` — 1 listener
- `binary_sensor/wasp_in_a_box.py` — 2 listeners
- `light.py` — 1 listener

---

## Stateless Targets (pure function decomposition)

### 3. base/magic.py — Entity loading and feature queries

**File**: `custom_components/magic_areas/base/magic.py`
**Primary Class**: `MagicArea` (436 lines)

**Entity Loading Cluster** (~150 lines, 5 methods):
- `load_entities()`, `load_magic_entities()`, `load_entity_list()`
- `_is_magic_area_entity()`, `_should_exclude_entity()`
- Stateless: registry reads → filtered entity lists (caching is optimization only)

**Feature Query Cluster** (~40 lines, 4 methods):
- `has_feature()`, `feature_config()`, `available_platforms()`, `has_configured_state()`
- Stateless: pure config dict reads (partially already in `core/config.py`)

**Approach**: Pure functions

```python
# core/entity_loader.py
def load_area_entities(area_id, registry, config) -> list[str]: ...
def should_exclude_entity(entry, config) -> bool: ...
def is_magic_area_entity(entity_config_entry_id, area_config_entry_id) -> bool: ...
```

---

### 4. media_player/area_aware_media_player.py — Media routing

**File**: `custom_components/magic_areas/media_player/area_aware_media_player.py`

**Media Routing Logic**:
- Determines which areas are occupied
- Routes media/TTS to appropriate areas
- Each routing decision is independent (no accumulated state)

**Approach**: Stateless policy class (like `LightGroupPolicy`)

```python
# core/media_routing.py
@dataclass(slots=True)
class AreaRoutingInfo:
    area_id: str
    is_occupied: bool
    current_states: list[str]
    notification_states: list[str]
    media_players: list[str]

@dataclass(slots=True)
class MediaRoutingDecision:
    target_areas: list[str]
    target_media_players: list[str]

def route_media(areas: list[AreaRoutingInfo]) -> MediaRoutingDecision: ...
```

---

### 6. config_flow.py — Schema helpers

**File**: `custom_components/magic_areas/config_flow.py`

**What was done in Phase 4**:
- Extracted selector builders → `schemas/selectors.py`
- Extracted climate preset builder → `schemas/feature_builders.py`
- Extracted validation helpers → `config_flows/helpers.py`
- Config flow reduced from 1319 → 1209 lines

**Remaining Selector Builder Cluster** (~60 lines, 4 methods):
- `_build_selector_boolean()`, `_build_selector_select()`, etc.
- Stateless: config → voluptuous schema

**Approach**: Extend existing `schemas/selectors.py` with remaining selector builder functions.

---

### 7. light.py — Scene selection

**File**: `custom_components/magic_areas/light.py`

**What was done in Phase 3**:
- Extracted light group control policy → `core/light_control.py`
- Extracted state priority logic → `core/state_priority.py`

**Remaining Scene/Mode Selection** (~50 lines):
- `assigned_states` and `act_on` resolution from feature config
- State-to-category mapping (which light category activates for which area state)
- Currently embedded in `AreaLightGroup.__init__()` via `LIGHT_GROUP_STATES` lookup

**Approach**: Extend existing `core/light_control.py` with category config resolution.

```python
# core/light_control.py (extend existing)
def resolve_light_category_config(
    category: str,
    feature_config: dict,
) -> tuple[list[str], list[str]]:
    """Resolve assigned states and act-on modes for a light category."""
    ...
```

---

## Execution Order

1. ✅ ~~AreaOccupancyTracker~~ (DONE)
2. **WaspStateMachine** (same proven pattern as #1)
3. **EntityLoader** (stateless, clean filter predicates)
4. **MediaRoutingPolicy** (stateless, focused routing logic)
5. **ListenerRegistry** (stateful, benefits 10+ entities across codebase)
6. **SchemaBuilder** (stateless, extends existing `schemas/` module)
7. **LightSceneSelector** (stateless, extends existing `core/light_control.py`)

---

**Note**: All targets maintain current behavior. These are refactoring opportunities, not feature changes.
