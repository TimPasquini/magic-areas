"""Contracts for canonical group metadata keys and values."""

from custom_components.magic_areas.core.runtime_model import GroupMetadataKey, GroupRole


def test_group_metadata_keys_are_stable() -> None:
    """Metadata keys should remain stable for runtime lookup compatibility."""
    assert str(GroupMetadataKey.FEATURE) == "feature"
    assert str(GroupMetadataKey.ROLE) == "role"
    assert str(GroupMetadataKey.CATEGORY) == "category"
    assert str(GroupMetadataKey.AGGREGATE_DOMAIN) == "aggregate_domain"
    assert str(GroupMetadataKey.AGGREGATE_DEVICE_CLASS) == "aggregate_device_class"
    assert str(GroupMetadataKey.AGGREGATE_KIND) == "aggregate_kind"


def test_group_role_values_are_stable() -> None:
    """Role values should remain stable for metadata selection."""
    assert str(GroupRole.PRIMARY) == "primary"
