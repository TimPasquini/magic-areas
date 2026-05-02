"""Import-boundary guardrails for recomposition streams."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest


SOURCE_ROOT = Path("custom_components/magic_areas")
TEST_ROOT = Path("tests")
ROOT_CORE_FACADE = "custom_components.magic_areas.core"
FEATURE_MODULES_PREFIX = "custom_components.magic_areas.features.modules"


@dataclass(frozen=True, slots=True)
class BoundaryRule:
    """Protected import prefix and allowlist for temporary exceptions."""

    name: str
    prefix: str
    allowlist: set[tuple[str, str]]
    allowed_targets: set[str] | None = None


@dataclass(frozen=True, slots=True)
class OwnershipImportRule:
    """Direct module ownership rule for import semantics."""

    module_path: Path
    disallowed_prefixes: tuple[str, ...]


ALLOWLIST_OVERRIDES: dict[str, set[tuple[str, str]]] = {
    # Intentional adapter seam: config-flow step modules must not import schema
    # selector internals directly. selector_builders is the single owned bridge.
    "runtime_schemas": {
        (
            "custom_components.magic_areas.config_flows.selector_builders",
            "custom_components.magic_areas.schemas.selectors",
        ),
    },
    # Intentional test-only implementation seams: these tests assert write-path
    # and parity behavior at light_groups implementation boundaries.
    "test_light_groups": {
        (
            "tests/unit/test_listener_entity_write_contracts",
            "custom_components.magic_areas.light_groups.entities",
        ),
        (
            "tests/unit/test_listener_entity_write_contracts",
            "custom_components.magic_areas.light_groups.runtime",
        ),
        (
            "tests/unit/test_light_control_group_parity",
            "custom_components.magic_areas.light_groups.runtime",
        ),
        (
            "tests/unit/test_light_group_runtime_adaptive_guards",
            "custom_components.magic_areas.light_groups.runtime",
        ),
        (
            "tests/unit/test_light_group_runtime_state_change_observability",
            "custom_components.magic_areas.light_groups.runtime",
        ),
    },
    # Intentional test-only implementation seam: switch base lifecycle/write
    # contracts are validated at the base class implementation layer.
    "test_switch": {
        (
            "tests/unit/test_listener_entity_lifecycle_contracts",
            "custom_components.magic_areas.switch.base",
        ),
        (
            "tests/unit/test_switch_base_write_contract",
            "custom_components.magic_areas.switch.base",
        ),
    },
}


def _allowlist(name: str) -> set[tuple[str, str]]:
    """Return configured allowlist set by semantic name."""
    return ALLOWLISTS[name]


def _assert_allowlist_exact(
    *,
    observed: set[tuple[str, str]],
    allowlist: set[tuple[str, str]],
    unexpected_message: str,
    stale_message: str,
) -> None:
    """Assert observed imports exactly match the allowlist contract."""
    unexpected = sorted(observed - allowlist)
    stale_allowlist_entries = sorted(allowlist - observed)

    assert not unexpected, (
        unexpected_message
        + "\n".join(f"{consumer} -> {target}" for consumer, target in unexpected)
    )
    assert not stale_allowlist_entries, (
        stale_message
        + "\n".join(
            f"{consumer} -> {target}" for consumer, target in stale_allowlist_entries
        )
    )


CORE_PUBLIC_API_SURFACES: set[str] = {
    "custom_components.magic_areas.core.aggregates",
    "custom_components.magic_areas.core.config",
    "custom_components.magic_areas.core.controls",
    "custom_components.magic_areas.core.controls.builders",
    "custom_components.magic_areas.core.controls.policies",
    "custom_components.magic_areas.core.controls.policies.climate",
    "custom_components.magic_areas.core.controls.policies.fan",
    "custom_components.magic_areas.core.controls.policies.media",
    "custom_components.magic_areas.core.discovery",
    "custom_components.magic_areas.core.listener_registry",
    "custom_components.magic_areas.core.meta",
    "custom_components.magic_areas.core.meta_reload",
    "custom_components.magic_areas.core.presence_tracker",
    "custom_components.magic_areas.core.runtime_model",
    "custom_components.magic_areas.core.runtime_model.feature_ids",
    "custom_components.magic_areas.core.state_priority",
    "custom_components.magic_areas.core.wasp_state_machine",
}

CORE_CONTROLS_PUBLIC_API_SURFACES: set[str] = {
    "custom_components.magic_areas.core.controls.builders",
    "custom_components.magic_areas.core.controls.policies",
    "custom_components.magic_areas.core.controls.policies.climate",
    "custom_components.magic_areas.core.controls.policies.fan",
    "custom_components.magic_areas.core.controls.policies.media",
}

FEATURES_PUBLIC_API_SURFACES: set[str] = {
    "custom_components.magic_areas.features.base",
    "custom_components.magic_areas.features.config",
    "custom_components.magic_areas.features.config.readers",
    "custom_components.magic_areas.features.dispatch",
    "custom_components.magic_areas.features.registry",
}

ENTRYPOINT_IMPORT_OWNERSHIP: dict[str, set[str]] = {
    "custom_components.magic_areas.core.aggregates": {
        "custom_components.magic_areas.core.aggregates.policy",
        "custom_components.magic_areas.core.aggregates.runtime",
        "custom_components.magic_areas.core.aggregates.selection",
    },
    "custom_components.magic_areas.core.runtime_model": {
        "custom_components.magic_areas.core.runtime_model.area",
        "custom_components.magic_areas.core.runtime_model.groups",
        "custom_components.magic_areas.core.runtime_model.identity",
        "custom_components.magic_areas.core.runtime_model.references",
        "custom_components.magic_areas.core.runtime_model.migration",
    },
}

OWNERSHIP_IMPORT_RULES: tuple[OwnershipImportRule, ...] = (
    # Core aggregate runtime/selection are domain primitives. They must not
    # reach into feature-layer config adapters.
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "core" / "aggregates" / "runtime.py",
        disallowed_prefixes=("custom_components.magic_areas.features.config",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "core" / "aggregates" / "selection.py",
        disallowed_prefixes=("custom_components.magic_areas.features.config",),
    ),
    # Control policy evaluation belongs to core and must not depend on
    # feature adapter readers.
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "core" / "controls" / "policies" / "climate.py",
        disallowed_prefixes=("custom_components.magic_areas.features.config",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "core" / "controls" / "policies" / "fan.py",
        disallowed_prefixes=("custom_components.magic_areas.features.config",),
    ),
    # Runtime model modules are intentionally generic and may not import
    # platform/feature slices.
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "core" / "runtime_model" / "references.py",
        disallowed_prefixes=(
            "custom_components.magic_areas.features.",
            "custom_components.magic_areas.light_groups",
            "custom_components.magic_areas.switch",
            "custom_components.magic_areas.sensor",
            "custom_components.magic_areas.binary_sensor",
            "custom_components.magic_areas.media_player",
            "custom_components.magic_areas.config_keys",
        ),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "core" / "runtime_model" / "groups.py",
        disallowed_prefixes=(
            "custom_components.magic_areas.features.",
            "custom_components.magic_areas.light_groups",
            "custom_components.magic_areas.switch",
            "custom_components.magic_areas.sensor",
            "custom_components.magic_areas.binary_sensor",
            "custom_components.magic_areas.media_player",
            "custom_components.magic_areas.config_keys",
            "custom_components.magic_areas.core.aggregates",
        ),
    ),
    # Platform modules should depend on local dispatch facade, not feature
    # internals directly.
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "light.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "cover.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "fan.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "sensor" / "__init__.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "binary_sensor" / "__init__.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "media_player" / "__init__.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
    OwnershipImportRule(
        module_path=SOURCE_ROOT / "switch" / "__init__.py",
        disallowed_prefixes=("custom_components.magic_areas.features.dispatch",),
    ),
)


_BOUNDARY_RULE_DEFINITIONS: tuple[tuple[str, str, str, set[str] | None], ...] = (
    (
        "core internals",
        "custom_components.magic_areas.core",
        "runtime_core",
        CORE_PUBLIC_API_SURFACES,
    ),
    ("helpers internals", "custom_components.magic_areas.helpers", "runtime_helpers", None),
    ("feature-module internals", FEATURE_MODULES_PREFIX, "runtime_feature_modules", None),
    (
        "feature package internals",
        "custom_components.magic_areas.features",
        "runtime_features",
        FEATURES_PUBLIC_API_SURFACES,
    ),
    ("schema internals", "custom_components.magic_areas.schemas", "runtime_schemas", None),
    (
        "coordinator internals",
        "custom_components.magic_areas.coordinator",
        "runtime_coordinator",
        None,
    ),
    (
        "entity-ingestion internals",
        "custom_components.magic_areas.coordinator.pipeline.entity_ingestion",
        "runtime_entity_ingestion",
        None,
    ),
    ("light-group internals", "custom_components.magic_areas.light_groups", "runtime_light_groups", None),
    ("media-player internals", "custom_components.magic_areas.media_player", "runtime_media_player", None),
    (
        "config-flow internals",
        "custom_components.magic_areas.config_flows",
        "runtime_config_flows",
        None,
    ),
    (
        "config-flow-step internals",
        "custom_components.magic_areas.config_flows.steps",
        "runtime_config_flow_steps",
        None,
    ),
    (
        "core-controls internals",
        "custom_components.magic_areas.core.controls",
        "runtime_core_controls",
        CORE_CONTROLS_PUBLIC_API_SURFACES,
    ),
    (
        "core-occupancy internals",
        "custom_components.magic_areas.core.occupancy",
        "runtime_core_occupancy",
        None,
    ),
    (
        "core-aggregates internals",
        "custom_components.magic_areas.core.aggregates",
        "runtime_core_aggregates",
        None,
    ),
    ("switch internals", "custom_components.magic_areas.switch", "runtime_switch", None),
    (
        "binary-sensor internals",
        "custom_components.magic_areas.binary_sensor",
        "runtime_binary_sensor",
        None,
    ),
    ("sensor internals", "custom_components.magic_areas.sensor", "runtime_sensor", None),
)

TEST_SIDE_DOOR_RULES: tuple[tuple[str, str, str], ...] = (
    ("light-group internals", "custom_components.magic_areas.light_groups", "test_light_groups"),
    (
        "entity-ingestion internals",
        "custom_components.magic_areas.coordinator.pipeline.entity_ingestion",
        "test_entity_ingestion",
    ),
    (
        "feature-module internals",
        "custom_components.magic_areas.features.modules",
        "test_feature_modules",
    ),
    (
        "config-flow-step internals",
        "custom_components.magic_areas.config_flows.steps",
        "test_config_flow_steps",
    ),
    (
        "config-flow options internals",
        "custom_components.magic_areas.config_flows.options_flow",
        "test_config_flow_options",
    ),
    (
        "config-flow entity-gatherer internals",
        "custom_components.magic_areas.config_flows.entity_gatherer",
        "test_config_flow_entity_gatherer",
    ),
    ("switch internals", "custom_components.magic_areas.switch", "test_switch"),
    (
        "media-player internals",
        "custom_components.magic_areas.media_player",
        "test_media_player",
    ),
)

ALLOWLIST_KEYS = {
    *(allowlist_key for _, _, allowlist_key, _ in _BOUNDARY_RULE_DEFINITIONS),
    *(allowlist_key for _, _, allowlist_key in TEST_SIDE_DOOR_RULES),
}
ALLOWLISTS: dict[str, set[tuple[str, str]]] = {
    key: set(ALLOWLIST_OVERRIDES.get(key, set())) for key in ALLOWLIST_KEYS
}
_UNKNOWN_ALLOWLIST_OVERRIDES = set(ALLOWLIST_OVERRIDES) - ALLOWLIST_KEYS
assert not _UNKNOWN_ALLOWLIST_OVERRIDES, (
    "Unknown allowlist override keys: " + ", ".join(sorted(_UNKNOWN_ALLOWLIST_OVERRIDES))
)

BOUNDARY_RULES: tuple[BoundaryRule, ...] = tuple(
    BoundaryRule(
        name=name,
        prefix=prefix,
        allowlist=_allowlist(allowlist_key),
        allowed_targets=allowed_targets,
    )
    for name, prefix, allowlist_key, allowed_targets in _BOUNDARY_RULE_DEFINITIONS
)



def _module_name(path: Path) -> str:
    rel = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return "custom_components.magic_areas" + ("." + ".".join(parts) if parts else "")


def _resolve_import_target(*, consumer: str, node: ast.ImportFrom) -> str | None:
    """Resolve absolute module path for an ImportFrom node."""
    if node.level == 0:
        return node.module

    base = consumer.split(".")[:-1]
    up = node.level - 1
    if up:
        base = base[:-up]
    return ".".join(base + ([node.module] if node.module else []))


def _collect_side_door_imports(prefix: str) -> set[tuple[str, str]]:
    """Collect imports into prefix internals from outside the prefix namespace."""
    imports: set[tuple[str, str]] = set()

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        consumer = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target.startswith(f"{prefix}.") and not consumer.startswith(prefix):
                        imports.add((consumer, target))
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import_target(consumer=consumer, node=node)
                if target and target.startswith(f"{prefix}.") and not consumer.startswith(prefix):
                    imports.add((consumer, target))

    return imports


def _collect_entry_imports(target_module: str) -> set[tuple[str, str]]:
    """Collect imports of a module entry point from outside that module namespace."""
    imports: set[tuple[str, str]] = set()
    target_prefix = f"{target_module}."

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        consumer = _module_name(path)
        if consumer == target_module or consumer.startswith(target_prefix):
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == target_module:
                        imports.add((consumer, target_module))
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import_target(consumer=consumer, node=node)
                if target == target_module:
                    imports.add((consumer, target_module))

    return imports


def _collect_test_root_core_imports() -> set[tuple[str, str]]:
    imports: set[tuple[str, str]] = set()
    for path in sorted(TEST_ROOT.rglob("test_*.py")):
        consumer = str(path.with_suffix(""))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == ROOT_CORE_FACADE:
                imports.add((consumer, ROOT_CORE_FACADE))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == ROOT_CORE_FACADE:
                        imports.add((consumer, ROOT_CORE_FACADE))
    return imports


def _collect_test_side_door_imports(prefix: str) -> set[tuple[str, str]]:
    """Collect test imports of internal modules below a prefix."""
    imports: set[tuple[str, str]] = set()
    for path in sorted(TEST_ROOT.rglob("test_*.py")):
        consumer = str(path.with_suffix(""))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target.startswith(f"{prefix}."):
                        imports.add((consumer, target))
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    continue
                target = node.module
                if target and target.startswith(f"{prefix}."):
                    imports.add((consumer, target))
    return imports


def _collect_disallowed_imports_for_module(
    module_path: Path, disallowed_prefixes: tuple[str, ...]
) -> set[str]:
    """Collect disallowed absolute import targets for one module."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    consumer = _module_name(module_path)
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                if target.startswith(disallowed_prefixes):
                    imports.add(target)
        elif isinstance(node, ast.ImportFrom):
            target_from = _resolve_import_target(consumer=consumer, node=node)
            if target_from and target_from.startswith(disallowed_prefixes):
                imports.add(target_from)

    return imports


def _collect_disallowed_imports_for_package(
    *,
    package_root: Path,
    disallowed_prefixes: tuple[str, ...],
) -> set[str]:
    """Collect disallowed import targets across every module in a package."""
    imports: set[str] = set()
    for module_path in sorted(package_root.rglob("*.py")):
        imports.update(
            _collect_disallowed_imports_for_module(
                module_path=module_path,
                disallowed_prefixes=disallowed_prefixes,
            )
        )
    return imports


def _collect_entrypoint_bypass_imports(
    *,
    entrypoint: str,
    internals: set[str],
) -> set[tuple[str, str]]:
    """Collect imports that bypass an entrypoint in favor of its internals."""
    imports: set[tuple[str, str]] = set()
    entrypoint_prefix = f"{entrypoint}."

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        consumer = _module_name(path)
        if consumer == entrypoint or consumer.startswith(entrypoint_prefix):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in internals:
                        imports.add((consumer, alias.name))
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import_target(consumer=consumer, node=node)
                if target in internals:
                    imports.add((consumer, target))

    return imports


@pytest.mark.parametrize("rule", BOUNDARY_RULES, ids=lambda rule: rule.name)
def test_no_new_side_door_imports(rule: BoundaryRule) -> None:
    """Prevent cross-slice side-door imports into protected namespaces."""
    observed = _collect_side_door_imports(rule.prefix)
    if rule.allowed_targets:
        observed = {pair for pair in observed if pair[1] not in rule.allowed_targets}

    _assert_allowlist_exact(
        observed=observed,
        allowlist=rule.allowlist,
        unexpected_message=f"Unexpected side-door imports into {rule.name}:\n",
        stale_message=(
            f"Allowlist contains entries no longer present for {rule.name}. "
            "Remove these:\n"
        ),
    )


def test_no_root_core_facade_imports() -> None:
    """Enforce explicit core sub-surface imports over root core facade."""
    observed = _collect_entry_imports(ROOT_CORE_FACADE)
    assert not observed, (
        "Root core facade imports are disallowed; use explicit core sub-surfaces:\n"
        + "\n".join(f"{consumer} -> {target}" for consumer, target in sorted(observed))
    )


def test_no_root_core_facade_imports_in_tests() -> None:
    """Keep tests aligned to explicit core sub-surface boundaries."""
    observed = _collect_test_root_core_imports()
    assert not observed, (
        "Tests importing root core facade are disallowed:\n"
        + "\n".join(f"{consumer} -> {target}" for consumer, target in sorted(observed))
    )


def test_config_keys_imports_stay_scoped() -> None:
    """Keep config key usage on explicit submodules, not root re-export surface."""
    root_imports = sorted(
        _collect_entry_imports("custom_components.magic_areas.config_keys")
    )

    assert not root_imports, (
        "Import config keys from explicit submodules instead of package root:\n"
        + "\n".join(f"{consumer} -> {target}" for consumer, target in root_imports)
    )


def test_feature_modules_do_not_cross_import_other_feature_modules() -> None:
    """Keep feature module implementations isolated behind registry wiring."""
    unexpected: set[tuple[str, str]] = set()
    allowed_target = "custom_components.magic_areas.core.controls.builders"

    for path in sorted((SOURCE_ROOT / "features" / "modules").glob("*.py")):
        module_name = _module_name(path)
        if module_name in {
            f"{FEATURE_MODULES_PREFIX}",
            allowed_target,
        }:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target.startswith(f"{FEATURE_MODULES_PREFIX}."):
                        if target not in {module_name, allowed_target}:
                            unexpected.add((module_name, target))
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import_target(consumer=module_name, node=node)
                if target and target.startswith(f"{FEATURE_MODULES_PREFIX}."):
                    if target not in {module_name, allowed_target}:
                        unexpected.add((module_name, target))

    assert not unexpected, (
        "Feature module implementations should not import sibling modules directly:\n"
        + "\n".join(
            f"{consumer} -> {target}" for consumer, target in sorted(unexpected)
        )
    )


def test_feature_modules_do_not_import_config_keys_directly() -> None:
    """Feature modules should consume config readers/helpers, not raw config keys."""
    offenders: list[str] = []
    forbidden_prefix = "custom_components.magic_areas.config_keys.area"

    for path in sorted((SOURCE_ROOT / "features" / "modules").glob("*.py")):
        module_name = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target.startswith(forbidden_prefix):
                        offenders.append(f"{module_name}:{node.lineno} -> {target}")
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_import_target(consumer=module_name, node=node)
                if target and target.startswith(forbidden_prefix):
                    offenders.append(f"{module_name}:{node.lineno} -> {target}")

    assert not offenders, (
        "Feature modules import config keys directly; use feature readers instead:\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize(
    ("name", "prefix", "allowlist"),
    tuple(
        (name, prefix, _allowlist(allowlist_key))
        for name, prefix, allowlist_key in TEST_SIDE_DOOR_RULES
    ),
)
def test_test_side_door_imports_do_not_expand(
    name: str,
    prefix: str,
    allowlist: set[tuple[str, str]],
) -> None:
    """Keep test-only side-door imports stable while runtime boundaries tighten."""
    observed = _collect_test_side_door_imports(prefix)
    _assert_allowlist_exact(
        observed=observed,
        allowlist=allowlist,
        unexpected_message=f"Unexpected test side-door imports into {name}:\n",
        stale_message=(
            f"Test allowlist contains entries no longer present for {name}. Remove:\n"
        ),
    )


@pytest.mark.parametrize("rule", OWNERSHIP_IMPORT_RULES, ids=lambda rule: str(rule.module_path))
def test_central_modules_do_not_import_feature_semantics(
    rule: OwnershipImportRule,
) -> None:
    """Central generic modules should not import feature-slice semantics."""
    observed = sorted(
        _collect_disallowed_imports_for_module(
            module_path=rule.module_path,
            disallowed_prefixes=rule.disallowed_prefixes,
        )
    )
    assert not observed, (
        f"{rule.module_path} imports feature semantics that should be slice-owned:\n"
        + "\n".join(observed)
    )


def test_core_package_does_not_import_feature_config_adapters() -> None:
    """Core domain package must never depend on feature config adapter layer."""
    observed = sorted(
        _collect_disallowed_imports_for_package(
            package_root=SOURCE_ROOT / "core",
            disallowed_prefixes=("custom_components.magic_areas.features.config",),
        )
    )
    assert not observed, (
        "core package imports feature config adapters, violating ownership:\n"
        + "\n".join(observed)
    )


def test_feature_modules_do_not_import_core_controls_directly() -> None:
    """Feature modules should depend on features-local control adapter seams."""
    observed = sorted(
        _collect_disallowed_imports_for_package(
            package_root=SOURCE_ROOT / "features" / "modules",
            disallowed_prefixes=("custom_components.magic_areas.core.controls",),
        )
    )
    assert not observed, (
        "feature modules import core.controls directly; use features adapters:\n"
        + "\n".join(observed)
    )


@pytest.mark.parametrize(
    ("entrypoint", "internals"),
    tuple(ENTRYPOINT_IMPORT_OWNERSHIP.items()),
    ids=tuple(ENTRYPOINT_IMPORT_OWNERSHIP.keys()),
)
def test_runtime_imports_use_entrypoints_not_internal_modules(
    entrypoint: str,
    internals: set[str],
) -> None:
    """Runtime modules should import entrypoints, not internal implementation modules."""
    bypasses = sorted(
        _collect_entrypoint_bypass_imports(
            entrypoint=entrypoint,
            internals=internals,
        )
    )
    assert not bypasses, (
        f"Runtime modules bypass {entrypoint} and import internals directly:\n"
        + "\n".join(f"{consumer} -> {target}" for consumer, target in bypasses)
    )


def test_core_config_feature_surface_stays_generic() -> None:
    """core.config.feature should remain a small generic primitive surface."""
    module = SOURCE_ROOT / "core" / "config" / "feature.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    function_names = sorted(
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    )
    assert function_names == [
        "coerce_float",
        "coerce_int",
        "enum_string_list",
        "feature_config_slice",
        "normalize_feature_config",
        "normalize_feature_key",
        "string_list",
    ]


def test_central_facades_do_not_reexport_feature_semantics() -> None:
    """Central facades should not expose feature-specific semantic helpers."""
    import custom_components.magic_areas.core.config as core_config
    import custom_components.magic_areas.core.runtime_model as core_groups
    import custom_components.magic_areas.core.runtime_model as core_identity
    import custom_components.magic_areas.feature_info as feature_info

    config_exports = set(getattr(core_config, "__all__", []))
    identity_exports = set(getattr(core_identity, "__all__", []))
    groups_exports = set(getattr(core_groups, "__all__", []))

    forbidden_config_tokens = {
        "fan",
        "climate",
        "ble",
        "media",
        "wasp",
        "health",
        "aggregate",
        "presence_hold",
    }

    leaked_config_symbols = sorted(
        symbol
        for symbol in config_exports
        if any(token in symbol for token in forbidden_config_tokens)
    )
    assert not leaked_config_symbols, (
        "core.config exports feature-semantic helpers unexpectedly:\n"
        + "\n".join(leaked_config_symbols)
    )

    assert "build_fan_group_id" not in groups_exports
    assert "build_media_player_group_id" not in groups_exports
    assert "build_light_group_id" not in groups_exports
    assert "build_climate_control_group_id" not in groups_exports

    assert "build_fan_control_switch_unique_id" not in identity_exports
    assert "build_media_player_control_switch_unique_id" not in identity_exports
    assert "build_light_control_switch_unique_id" not in identity_exports
    assert "build_climate_control_switch_unique_id" not in identity_exports

    feature_info_exports = {
        name
        for name in vars(feature_info)
        if not name.startswith("_")
    }
    leaked_feature_info_builders = sorted(
        name for name in feature_info_exports if name.startswith("build_")
    )
    assert not leaked_feature_info_builders, (
        "feature_info should remain metadata-only and not host ID builders:\n"
        + "\n".join(leaked_feature_info_builders)
    )


def test_runtime_code_avoids_broad_exception_handlers() -> None:
    """Runtime code should catch explicit expected exceptions only."""
    offenders: list[str] = []

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue

            exc_type = node.type
            if exc_type is None:
                offenders.append(f"{module}:{node.lineno} catches bare exception")
                continue

            names: set[str] = set()
            if isinstance(exc_type, ast.Name):
                names.add(exc_type.id)
            elif isinstance(exc_type, ast.Tuple):
                for item in exc_type.elts:
                    if isinstance(item, ast.Name):
                        names.add(item.id)

            if {"Exception", "BaseException"} & names:
                offenders.append(
                    f"{module}:{node.lineno} catches broad exception {sorted(names)}"
                )

    assert not offenders, (
        "Runtime code must not use broad exception handlers; narrow to expected types:\n"
        + "\n".join(offenders)
    )
