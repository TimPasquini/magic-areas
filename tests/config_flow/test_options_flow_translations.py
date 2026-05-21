"""Translation contracts for the options flow UX."""

import json
from pathlib import Path


TRANSLATIONS_PATH = (
    Path(__file__).parents[2]
    / "custom_components"
    / "magic_areas"
    / "translations"
    / "en.json"
)


def _options_step(step_id: str) -> dict[str, object]:
    """Return an English options-flow translation step."""
    translations = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    step = translations["options"]["step"][step_id]
    assert isinstance(step, dict)
    return step


def test_options_flow_root_menu_uses_task_oriented_labels() -> None:
    """Keep the root menu concise and human-oriented."""
    show_menu = _options_step("show_menu")
    menu_options = show_menu["menu_options"]

    assert isinstance(menu_options, dict)
    assert menu_options == {
        "area_config": "Area behavior",
        "secondary_states": "Area states",
        "presence_tracking": "Presence tracking",
        "select_features": "Features",
        "custom_control_groups": "Custom control groups",
        "finish": "Save & Exit",
        "feature_conf_health": "Health sensors",
        "feature_conf_fan_groups": "Fan automation",
        "feature_conf_climate_control": "Climate automation",
        "feature_conf_light_groups": "Light roles and automation",
        "feature_conf_area_aware_media_player": "Area-aware media player",
        "feature_conf_aggregates": "Aggregate sensors",
        "feature_conf_presence_hold": "Presence hold",
        "feature_conf_ble_trackers": "Bluetooth tracker monitoring",
        "feature_conf_wasp_in_a_box": "Wasp in a Box",
    }


def test_options_flow_root_menu_explains_save_behavior() -> None:
    """The root menu should make staged options explicit."""
    show_menu = _options_step("show_menu")
    description = show_menu["description"]

    assert isinstance(description, str)
    assert "not saved until you select `Save & Exit`" in description


def test_light_group_brightness_mode_uses_classic_label() -> None:
    """Keep the legacy inhibit token hidden behind clearer UI copy."""
    translations = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    selector_options = translations["selector"]["light_brightness_mode"]["options"]
    light_group_step = _options_step("feature_conf_light_groups")
    descriptions = light_group_step["data_description"]

    assert selector_options["inhibit"] == "Classic: bright may block on and turn off"
    assert isinstance(descriptions, dict)
    assert "Classic keeps legacy behavior" in descriptions["brightness_mode"]
    assert "inhibit" not in descriptions["brightness_mode"]
