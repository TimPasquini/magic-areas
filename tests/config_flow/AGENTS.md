# Config Flow Tests Guidance

These tests cover schema-driven options flow behavior.

Key rules:
- Favor integration-style flow tests using `async_init` / `async_configure`.
- If a feature step is schema-driven, assert on the resulting form schema.
- Avoid stubbing config flow internals unless testing an error path.
- Keep snapshot tests focused on structure rather than full HA state.
