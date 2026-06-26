"""Options flow for Magic Area configuration."""

from collections.abc import Mapping
import logging
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.base import ConfigBase
from custom_components.magic_areas.config_flows.entity_gatherer import (
    ConfigFlowEntityGatherer,
)
from custom_components.magic_areas.config_flows.base import (
    enabled_feature_map,
    get_feature_config_steps,
)
from custom_components.magic_areas.config_flows.steps import (
    handle_area_config,
    handle_climate_preset_selection,
    handle_custom_control_groups,
    handle_feature_conf,
    handle_feature_selection,
    handle_presence_tracking,
    handle_secondary_states,
)
from custom_components.magic_areas.components import MagicAreasConfigEntry
from custom_components.magic_areas.schemas import (
    META_AREA_SCHEMA,
    REGULAR_AREA_SCHEMA,
)
from custom_components.magic_areas.config_flows.base import MutableConfigMap

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigBase):
    """Handle an option flow for Magic Areas."""

    config_entry: MagicAreasConfigEntry

    def __init__(self, config_entry: MagicAreasConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self.handler = config_entry.entry_id
        self.data: dict[str, object] = {}
        self.all_entities: list[str] = []
        self.area_entities: list[str] = []
        self.all_area_entities: list[str] = []
        self.all_lights: list[str] = []
        self.all_media_players: list[str] = []
        self.all_binary_entities: list[str] = []
        self.all_light_tracking_entities: list[str] = []
        self.all_illuminance_entities: list[str] = []
        self.area_options: MutableConfigMap = {}
        self._feature_step_id: str | None = None
        super().__init__()

    def __getattr__(self, name: str) -> object:
        """Dynamically handle feature configuration steps."""
        if name.startswith("async_step_feature_conf_"):
            step_id = name.replace("async_step_", "")

            async def _dynamic_step(
                user_input: Mapping[str, object] | None = None,
            ) -> config_entries.ConfigFlowResult:
                return await self.async_step(step_id, user_input)

            return _dynamic_step
        raise AttributeError(name)

    async def async_step_feature_conf(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure a specific feature."""
        return await handle_feature_conf(self, user_input)

    async def _update_options(self) -> config_entries.ConfigFlowResult:
        """Update config entry options."""
        # noinspection PyTypeChecker
        return self.async_create_entry(title="", data=dict(self.area_options))

    async def async_step_init(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initialize the options flow."""
        del user_input

        # Cache area_config and coordinator data for use throughout the flow
        coordinator_data = self.config_entry.runtime_data.coordinator.data
        self._area_config = coordinator_data.area_config if coordinator_data else None
        self._coordinator_data = coordinator_data

        area_name = self._area_config.name if self._area_config else "Unknown"
        _LOGGER.debug("OptionsFlow: Initializing options flow for area %s", area_name)
        _LOGGER.debug(
            "OptionsFlow: Options in config entry for area %s: %s",
            area_name,
            str(self.config_entry.options),
        )

        # Gather all entities using helper class
        entities_by_domain = coordinator_data.entities if coordinator_data else {}
        gatherer = ConfigFlowEntityGatherer(
            hass=self.hass,
            entities_by_domain=entities_by_domain,
            config_entry_options=self.config_entry.options,
        )
        entity_collections = gatherer.gather_all()

        self.all_entities = entity_collections["all_entities"]
        self.area_entities = entity_collections["area_entities"]
        self.all_binary_entities = entity_collections["all_binary_entities"]
        self.all_area_entities = entity_collections["all_area_entities"]
        self.all_lights = entity_collections["all_lights"]
        self.all_media_players = entity_collections["all_media_players"]
        self.all_light_tracking_entities = entity_collections[
            "all_light_tracking_entities"
        ]
        self.all_illuminance_entities = entity_collections["all_illuminance_entities"]

        area_schema = (
            META_AREA_SCHEMA
            if (self._area_config and self._area_config.is_meta())
            else REGULAR_AREA_SCHEMA
        )
        self.area_options = area_schema(dict(self.config_entry.options))

        _LOGGER.debug("%s: Loaded area options: %s", area_name, str(self.area_options))
        # noinspection PyTypeChecker
        return await self.async_step_show_menu()

    async def async_step_show_menu(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show options selection menu."""
        del user_input
        # Show options menu
        menu_options: list[str] = [
            "area_config",
            "presence_tracking",
            "secondary_states",
            "custom_control_groups",
            "select_features",
        ]

        # Add entries for features
        feature_registry = get_feature_config_steps()
        menu_options_features = []
        for feature in enabled_feature_map(self.area_options):
            if feature in feature_registry:
                menu_options_features.append(f"feature_conf_{feature}")

        menu_options.extend(sorted(menu_options_features))
        menu_options.append("finish")

        # noinspection PyTypeChecker
        return self.async_show_menu(step_id="show_menu", menu_options=menu_options)

    async def async_step_area_config(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather basic settings for the area."""
        return await handle_area_config(self, user_input)

    async def async_step_presence_tracking(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather presence tracking settings for the area."""
        return await handle_presence_tracking(self, user_input)

    async def async_step_secondary_states(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather secondary states settings for the area."""
        return await handle_secondary_states(self, user_input)

    async def async_step_custom_control_groups(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure custom control groups for this area."""
        return await handle_custom_control_groups(self, user_input)

    async def async_step_select_features(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask the user to select features to enable for the area."""
        return await handle_feature_selection(self, user_input)

    async def async_step_finish(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Save options and exit options flow."""
        _LOGGER.debug(
            "OptionsFlow: All features configured for area %s, saving config: %s",
            self._area_config.name if self._area_config else "Unknown",
            str(self.area_options),
        )
        # noinspection PyTypeChecker
        return await self._update_options()

    async def async_step(
        self, step_id: str, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Route dynamic steps for feature configuration."""
        if step_id.startswith("feature_conf_"):
            self._feature_step_id = step_id
            # noinspection PyTypeChecker
            return await self.async_step_feature_conf(user_input)

        raise ValueError(f"Unknown step {step_id}")

    async def async_step_feature_conf_climate_control_select_presets(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Second climate step: select presets based on chosen climate entity."""
        return await handle_climate_preset_selection(self, user_input)
