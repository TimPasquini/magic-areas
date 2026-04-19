"""Boundary tests for entity update contract drift."""

from pathlib import Path


def test_schedule_update_ha_state_callsites_are_whitelisted() -> None:
    """Only approved off-loop entity paths may use scheduler writes."""
    root = Path("custom_components/magic_areas")
    allowed = {
        Path("custom_components/magic_areas/binary_sensor/ble_tracker.py"),
        Path("custom_components/magic_areas/binary_sensor/presence.py"),
    }

    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "schedule_update_ha_state(" not in text:
            continue
        if path not in allowed:
            offenders.append(str(path))

    assert offenders == []
