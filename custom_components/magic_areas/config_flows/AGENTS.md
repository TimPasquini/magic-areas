# Config Flows Guidance

This directory owns Magic Areas config and options flow behavior.

Key rules:
- Options UI is **schema-driven**. Use `ConfigBase._build_schema_from_vol` and
  `vol.Schema` definitions from `schemas/area.py` and feature-module schema
  surfaces in `features/modules/*.py`.
- Feature config steps are **registry-backed**. See
  `features/registry.py` and `config_flows/helpers.py`
  (`get_feature_config_steps`).
- Avoid per-feature `async_step_feature_conf_*` methods. Dynamic routing is the
  default; only add explicit steps when a feature requires a true multi-step flow
  (e.g., climate presets).
- Config is stored under `CONF_ENABLED_FEATURES` and should use enum keys
  (`MagicAreasFeatures`), not string literals.

When adding a new feature config:
1) Add/extend the module-local `FeatureOption` / `feature_schema` declaration
   in `features/modules/*.py`.
2) Add a `FeatureConfigStep` in the feature module if the feature is configurable.
3) Update selectors in the handler only if the UI needs dynamic choices.
