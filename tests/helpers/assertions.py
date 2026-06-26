"""Assertions shared across Magic Areas tests."""

from homeassistant.core import State


def assert_state(entity_state: State | None, expected_value: str) -> None:
    """Assert that an entity's state matches an expected value.

    Verifies that an entity exists and has the exact state specified. Use this
    for immediate state checks after an action.

    Args:
        entity_state: The State object from hass.states.get(entity_id), or None
            if the entity doesn't exist.
        expected_value: The expected state value as a string (e.g., 'on', 'off',
            '20' for temperature, 'unknown').

    Raises:
        AssertionError: If entity_state is None or state doesn't match
            expected_value.

    Example:
        Verify a light is on:

        >>> state = hass.states.get("light.kitchen")
        >>> assert_state(state, "on")

    """

    assert entity_state is not None
    assert entity_state.state == expected_value


def assert_attribute(
    entity_state: State | None, attribute_key: str, expected_value: str
) -> None:
    """Assert that an entity attribute equals an expected value.

    Verifies that an entity has a specific attribute with an exact value. The
    expected value is converted to a string for comparison, allowing type-
    flexible assertions.

    Args:
        entity_state: The State object from hass.states.get(entity_id), or None
            if the entity doesn't exist.
        attribute_key: The name of the attribute to check (e.g., 'brightness',
            'temperature', 'color_mode').
        expected_value: The expected attribute value as a string.

    Raises:
        AssertionError: If entity_state is None, the attribute doesn't exist,
            or the value doesn't match expected_value.

    Example:
        Verify light brightness:

        >>> state = hass.states.get("light.bedroom")
        >>> assert_attribute(state, "brightness", "200")

    """

    assert entity_state is not None
    assert hasattr(entity_state, "attributes")
    assert attribute_key in entity_state.attributes
    assert str(entity_state.attributes[attribute_key]) == expected_value


def assert_in_attribute(
    entity_state: State | None,
    attribute_key: str,
    expected_value: str,
    negate: bool = False,
) -> None:
    """Assert that an attribute contains (or doesn't contain) an expected value.

    Verifies that a specific substring or item exists (or doesn't exist) in an
    entity attribute. Useful for checking if a value is in a list or string
    attribute.

    Args:
        entity_state: The State object from hass.states.get(entity_id), or None
            if the entity doesn't exist.
        attribute_key: The name of the attribute to check (e.g., 'supported_modes',
            'friendly_name').
        expected_value: The value to search for in the attribute.
        negate: If True, assert the value is NOT in the attribute; if False,
            assert it IS in the attribute. Default: False.

    Raises:
        AssertionError: If entity_state is None, the attribute doesn't exist,
            or the value presence doesn't match the assertion.

    Example:
        Verify a device's supported modes:

        >>> state = hass.states.get("climate.living_room")
        >>> assert_in_attribute(state, "supported_modes", "heat")
        >>> assert_in_attribute(state, "supported_modes", "cool")
        >>> # Verify a mode is NOT supported:
        >>> assert_in_attribute(state, "supported_modes", "auto", negate=True)

    """

    assert entity_state is not None
    assert hasattr(entity_state, "attributes")
    assert attribute_key in entity_state.attributes

    if negate:
        assert expected_value not in entity_state.attributes[attribute_key]
    else:
        assert expected_value in entity_state.attributes[attribute_key]
