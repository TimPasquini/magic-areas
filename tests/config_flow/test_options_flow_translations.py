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
        "presence_tracking": "Presence tracking",
        "secondary_states": "Area states",
        "select_features": "Features",
        "custom_control_groups": "Custom control groups",
        "finish": "Done",
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
    """Root copy should describe incremental page-level saves."""
    show_menu = _options_step("show_menu")
    description = show_menu["description"]

    assert isinstance(description, str)
    assert "saved when you submit" in description
    assert "Save & Exit" not in description


def test_done_label_does_not_imply_final_save_semantics() -> None:
    """The Done menu label should not suggest it is the only save operation."""
    show_menu = _options_step("show_menu")
    menu_options = show_menu["menu_options"]

    assert isinstance(menu_options, dict)
    assert menu_options["finish"] == "Done"
    assert "Save" not in menu_options["finish"]


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
    secondary_states = _options_step("secondary_states_settings")
    data_description = secondary_states["data_description"]

    assert isinstance(data_description, dict)
    dark_entity = data_description["dark_entity"]
    assert isinstance(dark_entity, str)
    assert "area-level `bright`/`dark` state" in dark_entity
    assert "separate in-room brightness entities" in dark_entity
    assert "Advisory" in dark_entity
    assert "Adaptive" in dark_entity


def test_feature_selection_distinguishes_configurable_features() -> None:
    """Feature selection should explain which choices add follow-up menu pages."""
    select_features = _options_step("select_features")
    description = select_features["description"]
    data_description = select_features["data_description"]

    assert isinstance(description, str)
    assert "without extra menu pages" in description
    assert isinstance(data_description, dict)
    assert "adds a configuration menu" in data_description["light_groups"]
    assert "using default grouping and does not add a configuration menu" in (
        data_description["cover_groups"]
    )
    assert "using default grouping and does not add a configuration menu" in (
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
    assert "Classic keeps legacy behavior" in descriptions["brightness_mode"]
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
        "feature_conf_light_groups_roles": "Assign lights to room roles",
        "feature_conf_light_groups_brightness": "Choose a brightness behavior mode first",
        "feature_conf_light_groups_adaptive_lighting": "Choose whether Magic Areas ignores",
    }

    for step_id, expected_text in expected_descriptions.items():
        description = _options_step(step_id)["description"]
        assert isinstance(description, str)
        assert expected_text in description


def test_intentional_feature_submenus_expose_settings_and_back() -> None:
    """Only intentional multi-page/domain feature sections should expose submenus."""
    expected = {
        "feature_conf_fan_groups": {"feature_conf_fan_groups_settings", "show_menu"},
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
    step = _options_step("custom_control_groups_settings")

    assert step["title"] == "Custom control groups"
    description = step["description"]
    data = step["data"]
    data_description = step["data_description"]

    assert isinstance(description, str)
    assert "advanced role-style groups" in description
    assert isinstance(data, dict)
    assert data["custom_control_groups"] == "Custom control groups"
    assert isinstance(data_description, dict)
    assert "group_id" in data_description["custom_control_groups"]
