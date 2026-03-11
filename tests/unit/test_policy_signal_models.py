"""Tests for typed policy signal payload parsing."""

from custom_components.magic_areas.core.climate_control import ClimatePolicySignals
from custom_components.magic_areas.core.fan_control import FanPolicySignals
from custom_components.magic_areas.core.media_control import MediaPolicySignals
from custom_components.magic_areas.light_groups.policy import LightPolicySignals


def test_fan_policy_signal_payload_fields() -> None:
    """Fan payload should preserve typed signal values."""
    parsed = FanPolicySignals(
        sensor_value=45.0,
        fan_group_entity_id="fan.bathroom",
        fan_group_state="on",
    )

    assert parsed.sensor_value == 45.0
    assert parsed.fan_group_entity_id == "fan.bathroom"
    assert parsed.fan_group_state == "on"


def test_climate_policy_signal_payload_fields() -> None:
    """Climate payload should preserve optional string values."""
    parsed = ClimatePolicySignals(
        climate_entity_id="climate.office",
        preset_name="sleep",
    )

    assert parsed.climate_entity_id == "climate.office"
    assert parsed.preset_name == "sleep"


def test_media_policy_signal_payload_fields() -> None:
    """Media payload should preserve media-player group id."""
    parsed = MediaPolicySignals(media_player_group_id="media_player.room_group")

    assert parsed.media_player_group_id == "media_player.room_group"


def test_light_policy_signals_defaults_when_missing() -> None:
    """Light signal parser should default for unsupported signal payloads."""
    parsed = LightPolicySignals.from_signals(None)

    assert parsed.is_primary is False
    assert parsed.control_state.controlling is True
    assert parsed.control_state.awaiting_echo is False


def test_policy_signal_parsers_accept_payload_instances() -> None:
    """Parser helpers should pass through pre-built typed payloads."""
    fan_payload = FanPolicySignals(1.0, "fan.room", "off")
    climate_payload = ClimatePolicySignals("climate.room", "sleep")
    media_payload = MediaPolicySignals("media_player.room")
    light_payload = LightPolicySignals.from_signals({})

    assert FanPolicySignals.from_signals(fan_payload) is fan_payload
    assert ClimatePolicySignals.from_signals(climate_payload) is climate_payload
    assert MediaPolicySignals.from_signals(media_payload) is media_payload
    assert LightPolicySignals.from_signals(light_payload) is light_payload


def test_non_payload_signal_inputs_default_deterministically() -> None:
    """Parsers should default when context provides unsupported signal objects."""
    assert FanPolicySignals.from_signals({}).sensor_value is None
    assert ClimatePolicySignals.from_signals({}).climate_entity_id is None
    assert MediaPolicySignals.from_signals({}).media_player_group_id is None
