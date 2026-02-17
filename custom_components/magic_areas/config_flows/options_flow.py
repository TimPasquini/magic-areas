"""Options flow for Magic Area configuration."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from custom_components.magic_areas.config_flows.base import ConfigBase
from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
)
from custom_components.magic_areas.config_flows.entity_gatherer import (
    ConfigFlowEntityGatherer,
)
from custom_components.magic_areas.config_flows.steps.area_steps import (
    handle_area_config,
    handle_presence_tracking,
    handle_secondary_states,
)
from custom_components.magic_areas.config_flows.steps.feature_selection import (
    handle_feature_selection,
)
from custom_components.magic_areas.config_flows.steps.feature_config import (
    handle_feature_conf,
)
from custom_components.magic_areas.config_flows.steps.feature_config_climate import (
    handle_climate_preset_selection,
)
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.models import MagicAreasConfigEntry
from custom_components.magic_areas.policy import (
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.schemas.area import (
    META_AREA_SCHEMA,
    REGULAR_AREA_SCHEMA,
)
from custom_components.magic_areas.schemas.features import (
    CONFIGURABLE_FEATURES,
)
from custom_components.magic_areas.schemas.selectors import (
    build_selector_select,
)

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigBase):
    """Handle an option flow for Magic Areas."""

    config_entry: MagicAreasConfigEntry

    def __init__(self, config_entry: MagicAreasConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self.handler = config_entry.entry_id
        self.data: dict[str, Any] = {}
        self.all_entities: list[str] = []
        self.area_entities: list[str] = []
        self.all_area_entities: list[str] = []
        self.all_lights: list[str] = []
        self.all_media_players: list[str] = []
        self.all_binary_entities: list[str] = []
        self.all_light_tracking_entities: list[str] = []
        self.area_options: dict[str, Any] = {}
        self._feature_step_id: str | None = None
        super().__init__()


    async def async_step_feature_conf(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure a specific feature."""
        return await handle_feature_conf(self, user_input)

    async def _update_options(self) -> config_entries.ConfigFlowResult:
        """Update config entry options."""
        # noinspection PyTypeChecker
        return self.async_create_entry(title="", data=dict(self.area_options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initialize the options flow."""
        del user_input

        # Cache area_config and coordinator data for use throughout the flow
        coordinator_data = self.config_entry.runtime_data.coordinator.data
        self._area_config = coordinator_data.area_config if coordinator_data else None
        self._coordinator_data = coordinator_data

        area_name = self._area_config.name if self._area_config else "Unknown"
        _LOGGER.debug(
            "OptionsFlow: Initializing options flow for area %s", area_name
        )
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

        area_schema = META_AREA_SCHEMA if (self._area_config and self._area_config.is_meta()) else REGULAR_AREA_SCHEMA
        self.area_options = area_schema(dict(self.config_entry.options))

        _LOGGER.debug(
            "%s: Loaded area options: %s", area_name, str(self.area_options)
        )
        # noinspection PyTypeChecker
        return await self.async_step_show_menu()

    async def async_step_show_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show options selection menu."""
        del user_input
        # Show options menu
        menu_options: list = [
            "area_config",
            "presence_tracking",
            "secondary_states",
            "select_features",
        ]

        # Add entries for features
        menu_options_features = []
        for feature in self.area_options.get(CONF_ENABLED_FEATURES, {}):
            if feature in FEATURE_REGISTRY:
                menu_options_features.append(f"feature_conf_{feature}")

        menu_options.extend(sorted(menu_options_features))
        menu_options.append("finish")

        # noinspection PyTypeChecker
        return self.async_show_menu(step_id="show_menu", menu_options=menu_options)

    async def async_step_area_config(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather basic settings for the area."""
        return await handle_area_config(self, user_input)

    async def async_step_presence_tracking(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather presence tracking settings for the area."""
        return await handle_presence_tracking(self, user_input)

    async def async_step_secondary_states(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather secondary states settings for the area."""
        return await handle_secondary_states(self, user_input)

    async def async_step_select_features(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask the user to select features to enable for the area."""
        return await handle_feature_selection(self, user_input)

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Save options and exit options flow."""
        _LOGGER.debug(
            "OptionsFlow: All features configured for area %s, saving config: %s",
            self._area_config.name if self._area_config else "Unknown",
            str(self.area_options),
        )
        # noinspection PyTypeChecker
        return await self._update_options()

    async def do_feature_config(
        self,
        *,
        name: str,
        options: list,
        dynamic_validators: dict | None = None,
        selectors: dict | None = None,
        user_input: dict[str, Any] | None = None,
        custom_schema: vol.Schema | None = None,
        return_to: (
            Callable[[], Coroutine[Any, Any, config_entries.ConfigFlowResult]] | None
        ) = None,
        merge_options: bool = False,
        step_name: str | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Execute step for a generic feature."""
        errors: dict[str, str] = {}

        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating %s feature config for area %s: %s",
                name,
                self._area_config.name if self._area_config else "Unknown",
                str(user_input),
            )
            try:
                if custom_schema:
                    validated_input = custom_schema(user_input)
                else:
                    if not CONFIGURABLE_FEATURES[MagicAreasFeatures(name)]:
                        raise ValueError(f"No schema found for {name}")
                    validated_input = CONFIGURABLE_FEATURES[MagicAreasFeatures(name)](user_input)
            except vol.MultipleInvalid as validation:
                errors = dict.fromkeys(
                    self._errors_from_validation(validation), "malformed_input"
                )
                _LOGGER.debug("OptionsFlow: Found the following errors: %s", errors)
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught on area %s: %s",
                    self._area_config.name if self._area_config else "Unknown",
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving %s feature config for area %s: %s",
                    name,
                    self._area_config.name if self._area_config else "Unknown",
                    str(validated_input),
                )
                if merge_options:
                    if name not in self.area_options[CONF_ENABLED_FEATURES]:
                        self.area_options[CONF_ENABLED_FEATURES][name] = {}

                    self.area_options[CONF_ENABLED_FEATURES][name].update(
                        validated_input
                    )
                else:
                    self.area_options[CONF_ENABLED_FEATURES][name] = validated_input

                _LOGGER.debug(
                    "%s: Area options for %s: %s",
                    self._area_config.name if self._area_config else "Unknown",
                    name,
                    self.area_options[CONF_ENABLED_FEATURES][name],
                )

                if return_to:
                    # noinspection PyTypeChecker
                    return await return_to()

                # noinspection PyTypeChecker
                return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Config entry options for area %s: %s",
            self._area_config.name if self._area_config else "Unknown",
            str(self.config_entry.options),
        )

        saved_options = self.area_options.get(CONF_ENABLED_FEATURES, {})

        if not step_name:
            step_name = f"feature_conf_{name}"

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id=step_name,
            data_schema=self._build_options_schema(
                options=options,
                saved_options=saved_options.get(name, {}),
                dynamic_validators=dynamic_validators,
                selectors=selectors,
            ),
            errors=errors,
        )

    async def async_step(
        self, step_id: str, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Route dynamic steps for feature configuration."""
        if step_id.startswith("feature_conf_"):
            self._feature_step_id = step_id
            # noinspection PyTypeChecker
            return await self.async_step_feature_conf(user_input)

        raise ValueError(f"Unknown step {step_id}")

    async def _async_step_feature_conf(
        self,
        feature_key: str,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle configuration for a single feature.

        Returns:
            config_entries.ConfigFlowResult

        """
        if feature_key not in FEATURE_REGISTRY:
            # noinspection PyTypeChecker
            return self.async_abort(reason="unknown_feature")

        feature = FEATURE_REGISTRY[feature_key]
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                if feature.schema:
                    validated = feature.schema(user_input)
                else:
                    validated = CONFIGURABLE_FEATURES[MagicAreasFeatures(feature.name)](user_input)
            except vol.MultipleInvalid:
                errors = {"base": "invalid_input"}
            else:
                features = self.area_options.setdefault(CONF_ENABLED_FEATURES, {})
                if feature.merge_options:
                    features.setdefault(feature.name, {}).update(validated)
                else:
                    features[feature.name] = validated

                if feature.next_step:
                    # feature.next_step is a *step_id* (e.g. "feature_conf_climate_control_select_presets")
                    return await getattr(self, f"async_step_{feature.next_step}")()

                # noinspection PyTypeChecker
                return await self.async_step_show_menu()

        selectors: dict[str, Any] = {}

        # Wasp in a Box: UI submits a list for wasp_device_classes, but OPTIONS_WASP_IN_A_BOX
        # uses vol.In(...) (single value). Override with a multi-select selector.
        if feature_key == MagicAreasFeatures.WASP_IN_A_BOX:
            selectors[CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES] = (
                build_selector_select(
                    options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
                    multiple=True,
                )
            )

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id=f"feature_conf_{feature_key}",
            data_schema=self._build_options_schema(
                options=feature.options,
                saved_options=self.area_options.get(CONF_ENABLED_FEATURES, {}).get(
                    feature.name, {}
                ),
                selectors=selectors,
            ),
            errors=errors,
        )

    async def async_step_feature_conf_climate_control_select_presets(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Second climate step: select presets based on chosen climate entity."""
        return await handle_climate_preset_selection(self, user_input)

    async def async_step_feature_conf_light_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure light group settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            MagicAreasFeatures.LIGHT_GROUPS, user_input
        )

    async def async_step_feature_conf_climate_control(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure climate control settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            MagicAreasFeatures.CLIMATE_CONTROL , user_input
        )

    async def async_step_feature_conf_fan_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure fan group settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(MagicAreasFeatures.FAN_GROUPS, user_input)

    async def async_step_feature_conf_area_aware_media_player(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure area-aware media player settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER, user_input
        )

    async def async_step_feature_conf_aggregates(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure aggregation settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(MagicAreasFeatures.AGGREGATES, user_input)

    async def async_step_feature_conf_presence_hold(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure presence hold settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            MagicAreasFeatures.PRESENCE_HOLD, user_input
        )

    async def async_step_feature_conf_ble_trackers(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure BLE tracker settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            MagicAreasFeatures.BLE_TRACKER, user_input
        )

    async def async_step_feature_conf_wasp_in_a_box(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure Wasp in a Box settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            MagicAreasFeatures.WASP_IN_A_BOX, user_input
        )

    async def async_step_feature_conf_health(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure health feature settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(MagicAreasFeatures.HEALTH, user_input)
