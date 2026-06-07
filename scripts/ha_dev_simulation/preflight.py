"""Local Home Assistant storage preflight checks for simulation."""
# ruff: noqa: T201

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path

from scripts.ha_dev_simulation.entities import (
    COVER_ROOM_EXPECTED_OPTIONS,
    FAN_ROOM_EXPECTED_OPTIONS,
)


def _numeric_equal(actual: object, expected: object) -> bool:
    """Return whether two scalar values are numerically equivalent."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False
    if isinstance(actual, int | float) and isinstance(expected, int | float):
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=0.001)
    return False


def _list_equal(actual: object, expected: object) -> bool:
    """Return whether two simple lists match without depending on order."""
    if not isinstance(actual, list) or not isinstance(expected, list):
        return False
    return sorted(str(item) for item in actual) == sorted(str(item) for item in expected)


def _preflight_subset_errors(
    actual: object,
    expected: Mapping[str, object],
    *,
    prefix: str,
) -> list[str]:
    """Return missing/mismatched option paths for an expected mapping subset."""
    if not isinstance(actual, Mapping):
        return [f"{prefix}: expected mapping, got {type(actual).__name__}"]

    errors: list[str] = []
    for key, expected_value in expected.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if key not in actual:
            errors.append(f"{path}: missing")
            continue
        actual_value = actual[key]
        if isinstance(expected_value, Mapping):
            errors.extend(
                _preflight_subset_errors(
                    actual_value,
                    expected_value,
                    prefix=path,
                )
            )
        elif isinstance(expected_value, list):
            if not _list_equal(actual_value, expected_value):
                errors.append(
                    f"{path}: expected {expected_value!r}, got {actual_value!r}"
                )
        elif actual_value != expected_value and not _numeric_equal(
            actual_value, expected_value
        ):
            errors.append(f"{path}: expected {expected_value!r}, got {actual_value!r}")
    return errors


def _load_magic_area_options_from_storage(
    config_entries_path: Path,
) -> dict[str, Mapping[str, object]]:
    """Load Magic Areas options from the local dev HA config-entry storage file."""
    try:
        data = json.loads(config_entries_path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise RuntimeError(
            "Fan/Cover preflight could not find HA config-entry storage at "
            f"{config_entries_path}. Run against the local dev container or pass "
            "--config-entries-file."
        ) from err
    except json.JSONDecodeError as err:
        raise RuntimeError(
            f"Fan/Cover preflight could not parse {config_entries_path}: {err}"
        ) from err

    entries = data.get("data", {}).get("entries") if isinstance(data, Mapping) else None
    if not isinstance(entries, list):
        raise TypeError(
            f"Fan/Cover preflight found unexpected config-entry storage shape in "
            f"{config_entries_path}"
        )

    options_by_title: dict[str, Mapping[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("domain") != "magic_areas":
            continue
        title = entry.get("title")
        options = entry.get("options")
        if isinstance(title, str) and isinstance(options, Mapping):
            options_by_title[title] = options
    return options_by_title


def preflight_fan_cover_options(config_entries_path: Path) -> None:
    """Fail fast if Fan Room/Cover Room options do not match scenario needs."""
    options_by_title = _load_magic_area_options_from_storage(config_entries_path)
    expected_by_title = {
        "Fan Room": FAN_ROOM_EXPECTED_OPTIONS,
        "Cover Room": COVER_ROOM_EXPECTED_OPTIONS,
    }
    errors: list[str] = []
    for title, expected_options in expected_by_title.items():
        options = options_by_title.get(title)
        if options is None:
            errors.append(f"{title}: missing Magic Areas config entry/options")
            continue
        errors.extend(
            _preflight_subset_errors(
                options,
                expected_options,
                prefix=title,
            )
        )

    if errors:
        detail = "\n  - ".join(errors)
        raise RuntimeError(
            "Fan/Cover scenario preflight failed. Rerun "
            "`./scripts/ha_dev_bootstrap.sh --force-magic-area-options` before "
            f"simulation.\n  - {detail}"
        )
    print("preflight: Fan Room and Cover Room options match scenario contract")
