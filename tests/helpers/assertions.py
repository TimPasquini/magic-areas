"""Assertions shared across Magic Areas tests."""

from homeassistant.core import State


def assert_state(entity_state: State | None, expected_value: str) -> None:
    """Assert that an entity exists and has the expected state."""
    assert entity_state is not None
    assert entity_state.state == expected_value


def assert_attribute(
    entity_state: State | None, attribute_key: str, expected_value: str
) -> None:
    """Assert that an entity attribute equals the expected string value."""
    assert entity_state is not None
    assert attribute_key in entity_state.attributes
    assert str(entity_state.attributes[attribute_key]) == expected_value


def assert_in_attribute(
    entity_state: State | None,
    attribute_key: str,
    expected_value: str,
    negate: bool = False,
) -> None:
    """Assert that an entity attribute includes or excludes a value."""
    assert entity_state is not None
    assert attribute_key in entity_state.attributes

    if negate:
        assert expected_value not in entity_state.attributes[attribute_key]
    else:
        assert expected_value in entity_state.attributes[attribute_key]
