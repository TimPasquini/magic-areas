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
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.enums import MagicAreasFeatures

_LOGGER = logging.getLogger(__name__)

_ROOT_FEATURE_MENU_ORDER = (
    MagicAreasFeatures.LIGHT_GROUPS.value,
    MagicAreasFeatures.FAN_GROUPS.value,
    MagicAreasFeatures.COVER_GROUPS.value,
    MagicAreasFeatures.CLIMATE_CONTROL.value,
    MagicAreasFeatures.MEDIA_PLAYER_GROUPS.value,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER.value,
    MagicAreasFeatures.AGGREGATES.value,
    MagicAreasFeatures.HEALTH.value,
    MagicAreasFeatures.PRESENCE_HOLD.value,
    MagicAreasFeatures.BLE_TRACKER.value,
    MagicAreasFeatures.WASP_IN_A_BOX.value,
)

def _coordinator_data_from_entry(
    config_entry: MagicAreasConfigEntry,
) -> MagicAreasData | None:
    """Return loaded coordinator data for an options-flow entry."""
    runtime_data = getattr(config_entry, "runtime_data", None)
    if runtime_data is None:
        return None
    coordinator = getattr(runtime_data, "coordinator", None)
    if coordinator is None:
        return None
    data = coordinator.data
    return data if isinstance(data, MagicAreasData) else None


def _ordered_feature_menu_options(
    enabled_features: Mapping[str, object],
) -> list[str]:
    """Return enabled configurable feature steps in task-oriented order."""
    feature_registry = get_feature_config_steps()
    enabled_configurable = {
        feature
        for feature in enabled_features
        if feature in feature_registry
    }

    ordered = [
        f"feature_conf_{feature}"
        for feature in _ROOT_FEATURE_MENU_ORDER
        if feature in enabled_configurable
    ]
    ordered.extend(
        f"feature_conf_{feature}"
        for feature in sorted(enabled_configurable - set(_ROOT_FEATURE_MENU_ORDER))
    )
    return ordered


def _copy_option_value(value: object) -> object:
    """Deep-copy option containers without requiring pickle support."""
    if isinstance(value, Mapping):
        return {key: _copy_option_value(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_copy_option_value(nested) for nested in value]
    if isinstance(value, tuple):
        return tuple(_copy_option_value(nested) for nested in value)
    return value


def _copy_options(options: Mapping[str, object]) -> dict[str, object]:
    """Return a mutable, recursively copied options mapping."""
    return {
        str(key): _copy_option_value(value)
        for key, value in options.items()
        if isinstance(key, str)
    }


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

    async def _persist_options(self) -> None:
        """Persist the current staged options onto the config entry."""
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options=_copy_options(self.area_options),
        )
        await self.hass.async_block_till_done()

    async def _persist_options_and_show_menu(
        self,
    ) -> config_entries.ConfigFlowResult:
        """Persist a complete page and return to the root options menu."""
        await self._persist_options()
        return await self.async_step_show_menu()

    async def async_step_init(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initialize the options flow."""
        del user_input

        # Cache area_config and coordinator data for use throughout the flow.
        # Options forms depend on runtime entity catalogs; abort cleanly when the
        # entry is not loaded instead of raising an attribute error in the UI.
        coordinator_data = _coordinator_data_from_entry(self.config_entry)
        if coordinator_data is None:
            _LOGGER.warning(
                "OptionsFlow: Cannot initialize options flow for unloaded entry %s",
                self.config_entry.entry_id,
            )
            return self.async_abort(reason="entry_not_loaded")

        self._area_config = coordinator_data.area_config
        self._coordinator_data = coordinator_data

        area_name = self._area_config.name
        _LOGGER.debug(
            "OptionsFlow: Initializing options flow for area %s", area_name
        )
        _LOGGER.debug(
            "OptionsFlow: Options in config entry for area %s: %s",
            area_name,
            str(self.config_entry.options),
        )

        # Gather all entities using helper class
        entities_by_domain = coordinator_data.entities
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

        area_schema = META_AREA_SCHEMA if (self._area_config and self._area_config.is_meta()) else REGULAR_AREA_SCHEMA
        self.area_options = area_schema(_copy_options(self.config_entry.options))

        _LOGGER.debug(
            "%s: Loaded area options: %s", area_name, str(self.area_options)
        )
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
        ]

        menu_options.extend(
            _ordered_feature_menu_options(enabled_feature_map(self.area_options))
        )
        menu_options.extend(["custom_control_groups", "select_features"])

        # noinspection PyTypeChecker
        return self.async_show_menu(step_id="show_menu", menu_options=menu_options)

    async def async_step_area_config(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather basic settings for the area."""
        return await handle_area_config(
            self,
            user_input,
            step_id="area_config",
            on_success=self._persist_options_and_show_menu,
        )

    async def async_step_presence_tracking(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather presence tracking settings for the area."""
        return await handle_presence_tracking(
            self,
            user_input,
            step_id="presence_tracking",
            on_success=self._persist_options_and_show_menu,
        )

    async def async_step_secondary_states(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather secondary states settings for the area."""
        return await handle_secondary_states(
            self,
            user_input,
            step_id="secondary_states",
            on_success=self._persist_options_and_show_menu,
        )

    async def async_step_custom_control_groups(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure custom control groups for this area."""
        return await handle_custom_control_groups(
            self,
            user_input,
            step_id="custom_control_groups",
            on_success=self._persist_options_and_show_menu,
        )

    async def async_step_select_features(
        self, user_input: Mapping[str, object] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask the user to select features to enable for the area."""
        return await handle_feature_selection(self, user_input)

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
