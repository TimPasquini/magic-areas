"""Translation contracts for the options flow UX."""

import json
from pathlib import Path

import pytest


TRANSLATIONS_DIR = (
    Path(__file__).parents[2]
    / "custom_components"
    / "magic_areas"
    / "translations"
)
TRANSLATIONS_PATH = TRANSLATIONS_DIR / "en.json"


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
        "presence_tracking": "Presence tracking",
        "secondary_states": "Area states",
        "select_features": "Features",
        "custom_control_groups": "Custom control groups",
        "feature_conf_health": "Health sensors",
        "feature_conf_fan_groups": "Fan automation",
        "feature_conf_cover_groups": "Cover automation",
        "feature_conf_climate_control": "Climate automation",
        "feature_conf_light_groups": "Light roles and automation",
        "feature_conf_area_aware_media_player": "Area-aware media player",
        "feature_conf_aggregates": "Aggregate sensors",
        "feature_conf_presence_hold": "Presence hold",
        "feature_conf_ble_trackers": "Bluetooth tracker monitoring",
        "feature_conf_wasp_in_a_box": "Wasp in a Box",
    }


def test_options_flow_root_menu_explains_save_behavior() -> None:
    """Root copy should describe incremental page-level saves."""
    show_menu = _options_step("show_menu")
    description = show_menu["description"]

    assert isinstance(description, str)
    assert "saved when you submit" in description
    assert "close button" in description
    assert "Save & Exit" not in description


def test_root_menu_does_not_expose_final_save_action() -> None:
    """Root menu should not show a misleading final save or done action."""
    show_menu = _options_step("show_menu")
    menu_options = show_menu["menu_options"]

    assert isinstance(menu_options, dict)
    assert "finish" not in menu_options
    assert "Done" not in menu_options.values()
    assert all("Save" not in label for label in menu_options.values())


def _find_extra_translation_keys(
    english: object,
    localized: object,
    *,
    path: str,
    extra_paths: list[str],
) -> None:
    """Collect localized translation keys absent from the canonical English tree."""
    if not isinstance(localized, dict):
        return

    if not isinstance(english, dict):
        extra_paths.append(path)
        return

    for key in sorted(set(localized) - set(english)):
        extra_paths.append(f"{path}.{key}")

    for key, value in localized.items():
        if key not in english:
            continue
        _find_extra_translation_keys(
            english[key],
            value,
            path=f"{path}.{key}",
            extra_paths=extra_paths,
        )


@pytest.mark.parametrize(
    "translation_path",
    sorted(
        path
        for path in TRANSLATIONS_DIR.glob("*.json")
        if path != TRANSLATIONS_PATH
    ),
    ids=lambda path: path.name,
)
def test_localized_translations_do_not_reference_removed_contracts(
    translation_path: Path,
) -> None:
    """Localized files may be partial, but cannot retain keys removed from English."""
    english = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    localized = json.loads(translation_path.read_text(encoding="utf-8"))
    extra_paths: list[str] = []
    _find_extra_translation_keys(
        english,
        localized,
        path="<root>",
        extra_paths=extra_paths,
    )
    assert not extra_paths, (
        f"{translation_path.name} defines obsolete translation keys: {extra_paths}"
    )


def test_single_page_forms_explain_submit_saves_immediately() -> None:
    """Common single-page forms should tell users Submit saves that page."""
    for step_id in (
        "area_config",
        "presence_tracking",
        "secondary_states",
        "custom_control_groups",
        "feature_conf_health",
        "feature_conf_aggregates",
        "feature_conf_presence_hold",
        "feature_conf_ble_trackers",
        "feature_conf_wasp_in_a_box",
        "feature_conf_area_aware_media_player",
    ):
        description = _options_step(step_id)["description"]
        assert isinstance(description, str)
        assert "saved when you submit" in description


def test_area_states_light_source_copy_distinguishes_area_and_light_group_brightness() -> None:
    """The area-level bright/dark source should not imply it is the only light signal."""
    secondary_states = _options_step("secondary_states")
    data_description = secondary_states["data_description"]

    assert isinstance(data_description, dict)
    dark_entity = data_description["dark_entity"]
    assert isinstance(dark_entity, str)
    assert "daylight-style signal" in dark_entity
    assert "separate in-room brightness sensors" in dark_entity
    assert "Advisory" in dark_entity
    assert "Adaptive" in dark_entity


def test_feature_selection_distinguishes_configurable_features() -> None:
    """Feature selection should explain which choices add follow-up menu pages."""
    select_features = _options_step("select_features")
    description = select_features["description"]
    data_description = select_features["data_description"]

    assert isinstance(description, str)
    assert "convenient room-level groups" in description
    assert isinstance(data_description, dict)
    assert "turn those roles on and off" in data_description["light_groups"]
    assert "room-level cover targets" in (
        data_description["cover_groups"]
    )
    assert "room-level media-player target" in (
        data_description["media_player_groups"]
    )


def test_light_group_brightness_mode_uses_classic_label() -> None:
    """Keep the legacy inhibit token hidden behind clearer UI copy."""
    translations = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    selector_options = translations["selector"]["light_brightness_mode"]["options"]
    light_group_step = _options_step("feature_conf_light_groups_brightness")
    descriptions = light_group_step["data_description"]

    assert selector_options["inhibit"] == "Classic: bright may block on and turn off"
    assert isinstance(descriptions, dict)
    assert "Classic can keep lights off" in descriptions["brightness_mode"]
    assert "inhibit" not in descriptions["brightness_mode"]


def test_light_group_submenu_uses_task_oriented_labels() -> None:
    """Keep the light-group submenu split into human-scale tasks."""
    light_group_menu = _options_step("feature_conf_light_groups")
    menu_options = light_group_menu["menu_options"]

    assert isinstance(menu_options, dict)
    assert menu_options == {
        "feature_conf_light_groups_roles": "Light roles",
        "feature_conf_light_groups_brightness": "Brightness behavior",
        "feature_conf_light_groups_adaptive_lighting": "Adaptive Lighting",
        "show_menu": "Back",
    }


def test_light_group_substeps_explain_their_scope() -> None:
    """Each light-group substep should tell users what job it configures."""
    expected_descriptions = {
        "feature_conf_light_groups_roles": "Assign this room's lights to roles",
        "feature_conf_light_groups_brightness": "Choose a brightness behavior mode first",
        "feature_conf_light_groups_adaptive_lighting": "works with Adaptive Lighting",
    }

    for step_id, expected_text in expected_descriptions.items():
        description = _options_step(step_id)["description"]
        assert isinstance(description, str)
        assert expected_text in description


def test_intentional_feature_submenus_expose_settings_and_back() -> None:
    """Only intentional multi-page/domain feature sections should expose submenus."""
    expected = {
        "feature_conf_fan_groups": {
            "feature_conf_fan_groups_cooling",
            "feature_conf_fan_groups_humidity",
            "feature_conf_fan_groups_odor",
            "show_menu",
        },
        "feature_conf_climate_control": {
            "feature_conf_climate_control_settings",
            "feature_conf_climate_control_select_presets",
            "show_menu",
        },
    }
    for step_id, expected_options in expected.items():
        step = _options_step(step_id)
        menu_options = step.get("menu_options")
        assert isinstance(menu_options, dict)
        assert set(menu_options) == expected_options

    simple_feature_steps = {
        "feature_conf_health",
        "feature_conf_area_aware_media_player",
        "feature_conf_aggregates",
        "feature_conf_presence_hold",
        "feature_conf_ble_trackers",
        "feature_conf_wasp_in_a_box",
    }
    for step_id in simple_feature_steps:
        step = _options_step(step_id)
        assert "menu_options" not in step
        assert "data" in step


def test_custom_control_groups_step_has_guidance() -> None:
    """The advanced custom-control editor should not render as a blank form."""
    step = _options_step("custom_control_groups")

    assert step["title"] == "Custom control groups"
    description = step["description"]
    data = step["data"]
    data_description = step["data_description"]

    assert isinstance(description, str)
    assert "advanced room control groups" in description
    assert isinstance(data, dict)
    assert data["custom_control_groups"] == "Custom control groups"
    assert isinstance(data_description, dict)
    assert "stable ID" in data_description["custom_control_groups"]
