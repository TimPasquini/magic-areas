"""Contract tests for shared feature schema builders."""

import pytest
import voluptuous as vol

from custom_components.magic_areas.config_keys.area import (
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_PRESENCE_HOLD_TIMEOUT,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    default_feature_options,
    schema_from_default_options,
)
from custom_components.magic_areas.option_defaults import feature_option_default


def test_default_feature_options_resolve_each_canonical_default() -> None:
    """Each generated option should retain its key, validator, and default."""
    keys = (
        CONF_CLIMATE_CONTROL_PRESET_CLEAR,
        CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    )

    options = default_feature_options(
        feature=MagicAreasFeatures.CLIMATE_CONTROL,
        keys=keys,
        validator=str,
    )

    assert [option.key for option in options] == list(keys)
    assert all(option.validator is str for option in options)
    assert [option.default for option in options] == [
        feature_option_default(MagicAreasFeatures.CLIMATE_CONTROL, key)
        for key in keys
    ]


def test_schema_from_default_options_applies_required_filter_and_validation() -> None:
    """The schema should honor inclusion, validation, and extra-key removal."""
    schema = schema_from_default_options(
        feature=MagicAreasFeatures.PRESENCE_HOLD,
        keys_and_validators=((CONF_PRESENCE_HOLD_TIMEOUT, vol.Coerce(int)),),
        required_keys={CONF_PRESENCE_HOLD_TIMEOUT},
        include_keys={CONF_PRESENCE_HOLD_TIMEOUT},
    )

    assert schema(
        {
            CONF_PRESENCE_HOLD_TIMEOUT: "12",
            "unrelated": "removed",
        }
    ) == {CONF_PRESENCE_HOLD_TIMEOUT: 12}
    with pytest.raises(vol.MultipleInvalid):
        schema({})
