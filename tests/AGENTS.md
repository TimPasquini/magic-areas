# AGENTS.md — Tests (Home Assistant Custom Integration)

This file defines **rules and mental models for agents working on tests** in this repository.  
Its purpose is to prevent recurring failure patterns caused by **Home Assistant API drift**, **lifecycle misuse**, and **incorrect test isolation**.

This guidance **supplements** (does not replace) the repository-level AGENTS instructions.

---

## Core Principle

**Assume test failures are caused by outdated assumptions about Home Assistant behavior before assuming integration bugs.**

Most failures fall into predictable categories described below. Identify the category first, then apply the correct modern pattern.

---

## 1. ConfigEntry Immutability (Very Common)

### ❌ Bad pattern
```python
mock_config_entry.data = new_data
mock_config_entry.options = new_options
```

### ✅ Correct approach
`ConfigEntry` objects are immutable. Update through HA APIs only.

```python
mock_config_entry.add_to_hass(hass)
hass.config_entries.async_update_entry(
    mock_config_entry,
    data=new_data,
    options=new_options,
)
```

**Never assign to `entry.data`, `entry.options`, or other protected attributes.**

---

## 2. Enum / Constant Drift

### ❌ Bad pattern
```python
CoreState.NOT_RUNNING
```

### ✅ Correct approach
Use **current enum members** and authoritative imports.

```python
from homeassistant.core import CoreState

CoreState.not_running
```

**Recognition clue:** AttributeError or missing enum member.  
**Fix:** Check current HA enums; do not recreate old constants.

---

## 3. Registry API Signature Drift

### ❌ Bad pattern
```python
device_registry.async_get_or_create(..., area_id="kitchen")
```

### ✅ Correct approach
Create first, then update.

```python
device = device_registry.async_get_or_create(...)
device_registry.async_update_device(device.id, area_id="kitchen")
```

**Recognition clue:** `TypeError: unexpected keyword argument`.  
**Fix:** Assume signature drift, not test misuse.

Applies to:
- `DeviceRegistry`
- `EntityRegistry`
- `AreaRegistry`

---

## 3.5. API Export Drift (Removed or Moved Helpers)

Home Assistant may remove or stop exporting helper functions while keeping equivalent class or static methods.

### ❌ Bad pattern
```python
from homeassistant.helpers.storage import async_get_store_manager
```

### ✅ Correct approach
Prefer stable class-based entrypoints.

```python
from homeassistant.helpers.storage import Store

await Store.async_get_manager(hass).async_flush()
```

**Recognition clue:** ImportError from `homeassistant.*`.  
**Fix:** Look for a class with an `async_*` static/class method providing the same behavior.

Do not reintroduce removed helper imports in tests.

---

## 4. Patching Read-Only or Slotted Objects

Home Assistant uses slotted / Cython objects that **cannot be patched on instances**.

### ❌ Bad pattern
```python
patch.object(hass.bus, "async_listen_once")
```

### ✅ Correct approaches
Patch **the class** or **the call site**.

```python
from homeassistant.core import EventBus

patch.object(EventBus, "async_listen_once", autospec=True)
```

or

```python
patch("custom_components.magic_areas.magic.EventBus.async_listen_once")
```

With `autospec=True`, remember:
- the first argument is the instance (`self` / `bus`)

**Recognition clue:** AttributeError: attribute is read-only.

---

## 5. Event Listener Assertions

Home Assistant frequently registers **multiple listeners** internally.

### ❌ Bad pattern
```python
mock.assert_called_with(...)
```

### ✅ Correct approach
```python
mock.assert_any_call(...)
```

**Recognition clue:** Assertion fails because HA added unrelated listeners.  
**Fix:** Assert presence, not exclusivity.

---

## 6. Home Assistant Lifecycle Must Be Respected

### ❌ Bad pattern
- Setting `hass` to `NOT_RUNNING`
- Setting up integrations
- Ending test without starting or shutting down HA

This leaks:
- storage timers
- background tasks
- debouncers

### ✅ Correct approach

If a test sets HA to `NOT_RUNNING`:
1. Assert the expected behavior
2. **Start HA**
3. **Unload the integration**
4. **Flush storage**

```python
await hass.async_start()
await hass.async_block_till_done()

await shutdown_integration(hass, [mock_config_entry])

from homeassistant.helpers.storage import Store
await Store.async_get_manager(hass).async_flush()
await hass.async_block_till_done()
```

**Recognition clue:** teardown failures about lingering tasks or timers.

---

## 7. Store / Storage Timers (Frequent Teardown Failures)

If teardown reports:

```
Store._async_schedule_callback_delayed_write
```

That means:
- HA storage scheduled a delayed write
- the event loop ended before it flushed

### ✅ Required fix
Flush storage **after unloading integrations**.

```python
await Store.async_get_manager(hass).async_flush()
```

Do **not** silence these timers unless the test explicitly opts in.

---

## 7.5. RestoreEntity Timing (Restoration Happens After HA Startup)

### Pattern
Tests mock a restore cache (`mock_restore_cache(...)`) and then set up an integration *before* `await hass.async_start()`. The entity comes up with its default/computed state (often `off`) instead of the restored state.

### Recognition clues
- A restore test fails with: expected restored state `on`, actual `off`
- Logs show entities registered and set up, but restored state never applies
- Common with derived/group entities whose default is computed from member states

### Correct approach
Ensure Home Assistant is started **before** creating entities that rely on restore:

```python
mock_restore_cache(hass, [...])

await hass.async_start()
await hass.async_block_till_done()

await init_integration_helper(hass, [config_entry])
await hass.async_block_till_done()
```

If the entity’s state is derived (e.g., a group), restoration may only apply to attributes; ensure member entities are in the expected states and allow the state machine to settle (e.g., `wait_for_state(...)`) rather than asserting immediately.

---

## 8. Mock Entities Must Publish State

Custom mock entities must interact with the **HA state machine**, not just internal attributes.

### ❌ Bad pattern
- Changing `self._state` only
- Calling entity methods directly without HA state updates
- No initial state published on add

### ✅ Required behaviors
- On add: publish initial state
- On change: publish state updates

```python
async def async_added_to_hass(self) -> None:
    self.async_write_ha_state()

def turn_on(self, **kwargs):
    self._state = STATE_ON
    self.schedule_update_ha_state()
```

### Recognition clues
- Group / aggregate entities never change state
- Restored state appears ignored
- Mock entity “looks on” internally but HA shows `off`

**Fix:** Ensure mocks call `async_write_ha_state()` / `schedule_update_ha_state()`.

---

## 8.5. RestoreEntity / Restored State vs Derived State (Groups, Meta-Entities)

Some entities in this integration (and HA generally) have **derived state**: their on/off state is computed from other entities or framework logic and can overwrite anything coming from the restore cache during startup.

### Recognize this failure pattern
- Tests that call `mock_restore_cache(...)` with `STATE_ON`, then assert the entity state is `on`, repeatedly fail because HA recomputes state after setup.
- Typical examples: **light groups**, meta groups, entities wrapping HA `GroupEntity` behavior.

### Rule
**Do not assert restored `state` for derived-state entities.**  
Only assert restored values for **entity-owned, non-derived attributes**, and assert behavior that is stable.

### Correct testing approach
- Keep restore cache setup (for attributes you care about).
- Assert:
  - entity exists
  - stable attributes (e.g. `controlling`, membership lists like `lights` / `entity_id`)
  - switch/control entities that truly restore their own state
- Do **not** assert the group’s on/off state unless the test explicitly drives member states and waits for recomputation.

### Teardown requirement still applies
Even when focusing on restore behavior, tests must still end with integration unload/cleanup:

```python
await shutdown_integration(hass, [config_entry])
```

---

## 9. Test Through the Integration, Not Internals

### ❌ Bad patterns
```python
hass.data[DOMAIN][entry.entry_id]
direct entity construction
manual coordinator creation
```

### ✅ Correct approach
Always test via:
- `mock_config_entry.add_to_hass(hass)`
- `async_setup_entry`
- registry inspection
- state machine (`hass.states`)

This ensures lifecycle correctness.

## 9.5. Accessing Entity Instances (Unit Testing)

### ❌ Bad pattern
```python
hass.data[DOMAIN][entry.entry_id].entities[...]
```

### ✅ Correct approach
If you must access the entity instance (e.g. for unit testing internal methods), use the Entity Component system.

```python
entity = hass.data["entity_components"]["light"].get_entity("light.my_entity")
```

---

## 10. Prefer Behavior Assertions Over Implementation Assertions

Bad tests often assert:
- exact call order
- exact last call
- internal helper behavior

Prefer asserting:
- entities exist
- states change
- listeners are registered (via `assert_any_call`)
- registries reflect expected state

---

## 11. Integration Architecture Awareness (Tests Must Respect This)

When writing or fixing tests, remember:

- Runtime objects belong in `ConfigEntry.runtime_data`
- Cleanup must happen via `async_unload_entry`
- Entities subscribe in `async_added_to_hass`, not `__init__`
- Event listeners must be unregistered on unload
- Storage writes are delayed by design
- Group state is often **derived**, not authoritative

If a test violates these assumptions, **the test is wrong**.

---

## Summary Heuristic (Use This First)

When a test fails:

1. **Is this API drift?** (signature, enum, immutability, exports)
2. **Is HA lifecycle incomplete?** (not started, not unloaded)
3. **Is this a framework side effect?** (storage, listeners, stop hooks)
4. **Is the mock publishing state correctly?**
5. **Is the test asserting too precisely?**

Only after answering “no” to all should production code be changed.

---

**Goal:**  
Tests should validate *integration behavior under modern Home Assistant*, not freeze old internals in place.

