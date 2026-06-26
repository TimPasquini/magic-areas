"""Mock entity registration and area-assignment helpers."""

from collections.abc import Mapping, Sequence

from homeassistant.const import CONF_PLATFORM
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.setup import async_setup_component

from tests.const import MockAreaIds
from tests.helpers.platforms import setup_test_component_platform


async def setup_mock_entities(
    hass: HomeAssistant,
    domain: str,
    area_entity_map: Mapping[MockAreaIds, Sequence[Entity]],
) -> None:
    """Set up multiple mock entities and assign them to areas.

    Creates a mock component platform, registers entities with it, and assigns
    each entity to a specific area in the entity registry. This is the primary
    function for creating test entities that are aware of areas.

    Args:
        hass: The Home Assistant instance.
        domain: The component domain for entities (e.g., 'light', 'switch',
            'binary_sensor', 'sensor').
        area_entity_map: Mapping of area IDs to lists of Entity objects.
            Each entity in the lists will be assigned to the corresponding area.

    Raises:
        AssertionError: If component setup fails, entities don't get entity_ids,
            or area assignment fails.

    Note:
        The function performs these steps:
        1. Creates a mock platform for the domain using all entities
        2. Sets up the component with the mock platform
        3. Waits for all entities to receive entity_ids
        4. Updates the entity registry to assign each entity to its area
        5. Verifies all assignments completed successfully

    Example:
        Create lights in kitchen and living room areas:

        >>> light_kitchen = MockLight(name="Kitchen", unique_id="light_k1")
        >>> light_living = MockLight(name="Living", unique_id="light_l1")
        >>> await setup_mock_entities(
        ...     hass, "light",
        ...     {
        ...         MockAreaIds.KITCHEN: [light_kitchen],
        ...         MockAreaIds.LIVING_ROOM: [light_living],
        ...     }
        ... )

    """

    all_entities: list[Entity] = []
    entity_area_map: dict[str, MockAreaIds] = {}
    seen_unique_ids: set[str] = set()

    for area_id, entity_list in area_entity_map.items():
        for entity in entity_list:
            all_entities.append(entity)
            assert entity.unique_id is not None
            if entity.unique_id in seen_unique_ids:
                raise AssertionError(f"Duplicate entity unique_id {entity.unique_id!r}")
            seen_unique_ids.add(entity.unique_id)
            entity_area_map[entity.unique_id] = area_id

    # Setup entities
    setup_test_component_platform(hass, domain, all_entities)
    assert await async_setup_component(hass, domain, {domain: {CONF_PLATFORM: "test"}})
    await hass.async_block_till_done()

    # Update area IDs
    entity_registry = async_get_er(hass)
    for entity in all_entities:
        assert entity is not None

        # Wait for entity_id to be set
        if entity.entity_id is None:
            for _ in range(10):
                if entity.entity_id is not None:
                    break
                await hass.async_block_till_done()

        if entity.entity_id is None:
            raise AssertionError(
                f"Entity {entity.unique_id} did not get an entity_id assigned"
            )
        assert entity.unique_id is not None

        entity_entry = entity_registry.async_get(entity.entity_id)
        if not entity_entry:
            raise AssertionError(
                f"Entity registry entry {entity.entity_id} was not created"
            )
        expected_area_id = entity_area_map[entity.unique_id].value
        entity_registry.async_update_entity(
            entity.entity_id,
            area_id=expected_area_id,
        )
        updated_entry = entity_registry.async_get(entity.entity_id)
        assert updated_entry is not None
        if updated_entry.area_id != expected_area_id:
            raise AssertionError(
                f"Entity {entity.entity_id} area assignment failed: "
                f"expected {expected_area_id!r}, got {updated_entry.area_id!r}"
            )
    await hass.async_block_till_done()
