# Features Guidance

This directory defines the feature module system.

Key rules:
- Each feature lives in `features/modules/` and implements `FeatureModule`.
- Feature metadata (translation keys, icons) lives in `feature_info.py`.
- Feature modules should be thin: build entities, declare domains, and expose
  config flow steps when needed.
- The runtime source of truth is `features/registry.py`.

When adding a new feature:
1) Add the `MagicAreasFeatures` enum value.
2) Add metadata in `feature_info.py`.
3) Implement the module in `features/modules/`.
4) Register it in `features/registry.py`.
5) Add schemas under `schemas/features/` if configurable.
