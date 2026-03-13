"""Platform contract tests for push-driven parallel update settings."""

from custom_components.magic_areas import binary_sensor
from custom_components.magic_areas import cover
from custom_components.magic_areas import fan
from custom_components.magic_areas import light
from custom_components.magic_areas import media_player
from custom_components.magic_areas import sensor
from custom_components.magic_areas import switch


def test_push_platforms_disable_parallel_updates() -> None:
    """Push-driven Magic Areas platforms should explicitly disable polling concurrency."""
    assert binary_sensor.PARALLEL_UPDATES == 0
    assert sensor.PARALLEL_UPDATES == 0
    assert switch.PARALLEL_UPDATES == 0
    assert light.PARALLEL_UPDATES == 0
    assert fan.PARALLEL_UPDATES == 0
    assert cover.PARALLEL_UPDATES == 0
    assert media_player.PARALLEL_UPDATES == 0
