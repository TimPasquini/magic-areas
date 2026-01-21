"""Config Flow for Magic Area."""

import logging
from collections.abc import Callable, Coroutine, Mapping
from typing import Any, cast

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.area_registry import async_get as areareg_async_get
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get
from homeassistant.helpers.floor_registry import async_get as floorreg_async_get
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import slugify

from custom_components.magic_areas.area_constants import (
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.area_maps import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
)
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.config_flow_filters import (
    CONFIG_FLOW_ENTITY_FILTER_BOOL,
    CONFIG_FLOW_ENTITY_FILTER_EXT,
)
from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
    FeatureConfig,
)
from custom_components.magic_areas.config_keys import (
    ALL_PRESENCE_DEVICE_PLATFORMS,
    CONF_CLEAR_TIMEOUT,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    CONF_SECONDARY_STATES,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    EMPTY_STRING,
    CalculationMode,
)
from custom_components.magic_areas.core_constants import (
    ADDITIONAL_LIGHT_TRACKING_ENTITIES,
    DOMAIN,
)
from custom_components.magic_areas.enums import (
    MagicConfigEntryVersion,
    MetaAreaType,
    SelectorTranslationKeys,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_PRESENCE_HOLD,
)
from custom_components.magic_areas.helpers.area import (
    basic_area_from_floor,
    basic_area_from_meta,
    basic_area_from_object,
)
from custom_components.magic_areas.models import MagicAreasConfigEntry
from custom_components.magic_areas.policy import (
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.schemas.area import (
    _DOMAIN_SCHEMA,
    META_AREA_BASIC_OPTIONS_SCHEMA,
    META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    META_AREA_SCHEMA,
    META_AREA_SECONDARY_STATES_SCHEMA,
    REGULAR_AREA_BASIC_OPTIONS_SCHEMA,
    REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    REGULAR_AREA_SCHEMA,
    SECONDARY_STATES_SCHEMA,
)
from custom_components.magic_areas.schemas.features import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
    CONF_FEATURE_WASP_IN_A_BOX,
    CONFIGURABLE_FEATURES,
    NON_CONFIGURABLE_FEATURES_META,
)
from custom_components.magic_areas.schemas.validation import (
    OPTIONS_AREA,
    OPTIONS_AREA_META,
    OPTIONS_CLIMATE_CONTROL,
    OPTIONS_PRESENCE_TRACKING,
    OPTIONS_PRESENCE_TRACKING_META,
    OPTIONS_SECONDARY_STATES,
    OPTIONS_SECONDARY_STATES_META,
)

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]


class ConfigBase:
    """Base class for config flow."""

    config_entry: MagicAreasConfigEntry | None = None

    # Selector builder
    @staticmethod
    def _build_selector_boolean() -> BooleanSelector:
        """Build a boolean toggle selector."""
        return BooleanSelector(BooleanSelectorConfig())

    @staticmethod
    def _build_selector_select(
            options: list | None = None,
        multiple: bool = False,
        translation_key: str = EMPTY_STRING,
    ) -> SelectSelector:
        """Build a <select> selector."""
        if not options:
            options = []

        return SelectSelector(
            SelectSelectorConfig(
                options=options,
                multiple=multiple,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=translation_key,
            )
        )

    @staticmethod
    def _build_selector_entity_simple(
            options: list | None = None,
        multiple: bool = False,
        force_include: bool = False,
    ) -> "NullableEntitySelector":
        """Build a <select> selector with predefined settings."""
        if not options:
            options = []
        return NullableEntitySelector(
            EntitySelectorConfig(include_entities=options, multiple=multiple)
        )

    @staticmethod
    def _build_selector_number(
            *,
        min_value: float = 0,
        max_value: float = 9999,
        mode: NumberSelectorMode = NumberSelectorMode.BOX,
        step: float = 1,
        unit_of_measurement: str = "seconds",
    ) -> NumberSelector:
        """Build a number selector."""
        return NumberSelector(
            NumberSelectorConfig(
                min=min_value,
                max=max_value,
                mode=mode,
                step=step,
                unit_of_measurement=unit_of_measurement,
            )
        )

    def _build_options_schema(
        self,
        options: list,
        *,
        saved_options: Mapping[str, Any] | None = None,
        dynamic_validators: dict | None = None,
        selectors: dict | None = None,
    ) -> vol.Schema:
        """Build schema for configuration options."""
        _LOGGER.debug(
            "ConfigFlow: Building schema from options: %s - dynamic_validators: %s",
            str(options),
            str(dynamic_validators),
        )

        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if saved_options is None and self.config_entry:
            saved_options = self.config_entry.options

        _LOGGER.debug(
            "ConfigFlow: Data for pre-populating fields: %s", str(saved_options)
        )

        schema = {
            vol.Optional(
                name,
                description={
                    "suggested_value": (
                        saved_options.get(name)
                        if saved_options and saved_options.get(name) is not None
                        else default
                    )
                },
                default=default,
            ): (
                selectors[name]
                if name in selectors
                else dynamic_validators.get(name, validation)
            )
            for name, default, validation in options
        }

        _LOGGER.debug("ConfigFlow: Built schema: %s", str(schema))

        return vol.Schema(schema)


class NullableEntitySelector(EntitySelector):
    """Entity selector that supports null values."""

    def __call__(self, data: Any) -> Any:
        """Validate the passed selection, if passed."""

        if data in (None, ""):
            return data

        return super().__call__(data)  # type: ignore


class ConfigFlow(config_entries.ConfigFlow, ConfigBase, domain=DOMAIN):
    """Handle a config flow for Magic Areas."""

    VERSION = MagicConfigEntryVersion.MAJOR
    MINOR_VERSION = MagicConfigEntryVersion.MINOR

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        reserved_names = []
        non_floor_meta_areas = [
            meta_area_type
            for meta_area_type in MetaAreaType
            if meta_area_type != MetaAreaType.FLOOR
        ]

        # Load registries
        area_registry = areareg_async_get(self.hass)
        floor_registry = floorreg_async_get(self.hass)
        areas = [
            basic_area_from_object(area) for area in area_registry.async_list_areas()
        ]
        area_ids = [area.id for area in areas]

        # Load floors meta-aras
        floors = floor_registry.async_list_floors()

        for floor in floors:
            # Prevent conflicts between meta areas and existing areas
            if floor.floor_id in area_ids:
                _LOGGER.warning(
                    "ConfigFlow: You have an area with a reserved name '%s'. This will prevent from using the %s Meta area.",
                    floor.floor_id,
                    floor.floor_id,
                )
                continue

            _LOGGER.debug(
                "ConfigFlow: Appending Meta Area %s to the list of areas",
                floor.floor_id,
            )
            area = basic_area_from_floor(floor)
            reserved_names.append(area.id)
            areas.append(area)

        # Add standard meta areas to area list
        for meta_area in non_floor_meta_areas:
            # Prevent conflicts between meta areas and existing areas
            if meta_area in area_ids:
                _LOGGER.warning(
                    "ConfigFlow: You have an area with a reserved name '%s'. This will prevent from using the %s Meta area.",
                    meta_area,
                    meta_area,
                )
                continue

            _LOGGER.debug(
                "ConfigFlow: Appending Meta Area %s to the list of areas", meta_area
            )
            area = basic_area_from_meta(meta_area)
            reserved_names.append(area.id)
            areas.append(area)

        if user_input is not None:
            # Look up area object by name
            area_object = None

            for area in areas:
                area_name = user_input[CONF_NAME]

                # Handle meta area name append
                if area_name.startswith("(Meta)"):
                    area_name = " ".join(area_name.split(" ")[1:])

                if area.name == area_name:
                    area_object = area
                    break

            # Fail if area name not found,
            # this should never happen in ideal conditions.
            if not area_object:
                return self.async_abort(reason="invalid_area")

            # Reserve unique name / already configured check
            await self.async_set_unique_id(area_object.id)
            self._abort_if_unique_id_configured()

            # Create area entry with default config
            config_entry = _DOMAIN_SCHEMA({f"{area_object.id}": {}})[area_object.id]
            extra_opts = {CONF_NAME: area_object.name, CONF_ID: area_object.id}
            config_entry.update(extra_opts)

            # Handle Meta area
            if slugify(area_object.id) in reserved_names:
                _LOGGER.debug(
                    "ConfigFlow: Meta area %s found, setting correct type.",
                    area_object.id,
                )
                config_entry.update({CONF_TYPE: AREA_TYPE_META})

            return self.async_create_entry(title=area_object.name, data=config_entry)  # type: ignore[arg-type]

        # Filter out already-configured areas
        configured_areas = []
        entries = self._async_current_entries()
        for entry in entries:
            if entry.data.get(CONF_ID):
                configured_areas.append(entry.data.get(CONF_ID))

        available_areas = [area for area in areas if area.id not in configured_areas]

        if not available_areas:
            return self.async_abort(reason="no_more_areas")

        # Slight ordering trick so Meta areas are at the bottom
        available_area_names = sorted(
            [area.name for area in available_areas if area.id not in reserved_names]
        )
        available_area_names.extend(
            sorted(
                [
                    f"(Meta) {area.name}"
                    for area in available_areas
                    if area.id in reserved_names
                ]
            )
        )

        schema = vol.Schema({vol.Required(CONF_NAME): vol.In(available_area_names)})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: MagicAreasConfigEntry,
    ) -> "OptionsFlowHandler":
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigBase):
    """Handle an option flow for Adaptive Lighting."""

    area: MagicArea
    config_entry: MagicAreasConfigEntry

    def __init__(self, config_entry: MagicAreasConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.data: dict[str, Any] = {}
        self.all_entities: list[str] = []
        self.area_entities: list[str] = []
        self.all_area_entities: list[str] = []
        self.all_lights: list[str] = []
        self.all_media_players: list[str] = []
        self.all_binary_entities: list[str] = []
        self.all_light_tracking_entities: list[str] = []
        self.area_options: dict[str, Any] = {}
        super().__init__()

    def _get_feature_list(self) -> list[str]:
        """Return list of available features for area type."""

        feature_list = CONF_FEATURE_LIST
        area_type = self.area.config.get(CONF_TYPE)
        if area_type == AREA_TYPE_META:
            feature_list = CONF_FEATURE_LIST_META
        if self.area.id == META_AREA_GLOBAL.lower():
            feature_list = CONF_FEATURE_LIST_GLOBAL

        return feature_list

    def _get_configurable_features(self) -> list[str]:
        """Return configurable features for area type."""
        filtered_configurable_features = list(CONFIGURABLE_FEATURES.keys())
        if self.area.is_meta():
            for feature in NON_CONFIGURABLE_FEATURES_META:
                if feature in filtered_configurable_features:
                    filtered_configurable_features.remove(feature)

        return filtered_configurable_features

    async def async_step_feature_conf(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        step_id = str(self.context.get("step_id", ""))
        feature_key = step_id.replace("feature_conf_", "")

        if feature_key not in FEATURE_REGISTRY:
            return self.async_abort(reason="unknown_feature")

        feature: FeatureConfig = FEATURE_REGISTRY[feature_key]
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                if feature.schema:
                    validated = feature.schema(user_input)
                else:
                    validated = CONFIGURABLE_FEATURES[feature.name](user_input)
            except vol.MultipleInvalid:
                errors = {"base": "invalid_input"}
            else:
                features = self.area_options.setdefault(CONF_ENABLED_FEATURES, {})
                if feature.merge_options:
                    features.setdefault(feature.name, {}).update(validated)
                else:
                    features[feature.name] = validated

                if feature.next_step:
                    return await getattr(self, feature.next_step)()

                return await self.async_step_show_menu()

        return self.async_show_form(
            step_id=step_id,
            data_schema=self._build_options_schema(
                options=feature.options,
                saved_options=self.area_options.get(CONF_ENABLED_FEATURES, {}).get(
                    feature.name, {}
                ),
            ),
            errors=errors,
        )

    async def _update_options(self) -> config_entries.ConfigFlowResult:
        """Update config entry options."""
        return self.async_create_entry(title="", data=dict(self.area_options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initialize the options flow."""

        self.area = self.config_entry.runtime_data.area

        _LOGGER.debug(
            "OptionsFlow: Initializing options flow for area %s", self.area.name
        )
        _LOGGER.debug(
            "OptionsFlow: Options in config entry for area %s: %s",
            self.area.name,
            str(self.config_entry.options),
        )

        # Return all relevant entities
        self.all_entities = sorted(
            self.resolve_groups(
                [
                    entity_id
                    for entity_id in self.hass.states.async_entity_ids()
                    if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_EXT
                ]
            )
        )

        # Return all relevant area entities that exists
        # in self.all_entities
        filtered_area_entities = []
        for domain in CONFIG_FLOW_ENTITY_FILTER_EXT:
            filtered_area_entities.extend(
                [
                    entity["entity_id"]
                    for entity in self.area.entities.get(domain, [])
                    if entity["entity_id"] in self.all_entities
                ]
            )

        self.area_entities = sorted(self.resolve_groups(filtered_area_entities))

        # All binary entities
        self.all_binary_entities = sorted(
            self.resolve_groups(
                [
                    entity_id
                    for entity_id in self.all_entities
                    if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_BOOL
                ]
            )
        )

        self.all_area_entities = sorted(
            self.area_entities
            + self.config_entry.options.get(CONF_EXCLUDE_ENTITIES, [])
        )

        self.all_lights = sorted(
            self.resolve_groups(
                [
                    entity["entity_id"]
                    for entity in self.area.entities.get(LIGHT_DOMAIN, [])
                    if entity["entity_id"] in self.all_entities
                ]
            )
        )
        self.all_media_players = sorted(
            self.resolve_groups(
                [
                    entity["entity_id"]
                    for entity in self.area.entities.get(MEDIA_PLAYER_DOMAIN, [])
                    if entity["entity_id"] in self.all_entities
                ]
            )
        )

        # Compile all binary sensors of light device class
        eligible_light_tracking_entities = []
        for entity in self.all_entities:
            e_component = entity.split(".")[0]

            if e_component == BINARY_SENSOR_DOMAIN:
                entity_object = self.hass.states.get(entity)
                if not entity_object:
                    continue
                entity_object_attributes = entity_object.attributes
                if (
                    ATTR_DEVICE_CLASS in entity_object_attributes
                    and entity_object_attributes[ATTR_DEVICE_CLASS]
                    == BinarySensorDeviceClass.LIGHT
                ):
                    eligible_light_tracking_entities.append(entity)

        # Add additional entities to eligible entities
        eligible_light_tracking_entities.extend(ADDITIONAL_LIGHT_TRACKING_ENTITIES)

        self.all_light_tracking_entities = sorted(
            self.resolve_groups(eligible_light_tracking_entities)
        )

        area_schema = META_AREA_SCHEMA if self.area.is_meta() else REGULAR_AREA_SCHEMA
        self.area_options = area_schema(dict(self.config_entry.options))

        _LOGGER.debug(
            "%s: Loaded area options: %s", self.area.name, str(self.area_options)
        )

        return await self.async_step_show_menu()

    async def async_step_show_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show options selection menu."""
        # Show options menu
        menu_options: list = [
            "area_config",
            "presence_tracking",
            "secondary_states",
            "select_features",
        ]

        # Add entries for features
        menu_options_features = []
        configurable_features = self._get_configurable_features()
        for feature in self.area_options.get(CONF_ENABLED_FEATURES, {}):
            if feature in FEATURE_REGISTRY:
                menu_options_features.append(f"feature_conf_{feature}")

        menu_options.extend(sorted(menu_options_features))
        menu_options.append("finish")

        return self.async_show_menu(step_id="show_menu", menu_options=menu_options)

    @staticmethod
    def resolve_groups(raw_list: list) -> list:
        """Resolve entities from groups."""
        resolved_list = []
        for item in raw_list:
            if isinstance(item, list):
                for item_child in item:
                    resolved_list.append(item_child)
                continue
            resolved_list.append(item)

        return list(dict.fromkeys(resolved_list))

    async def async_step_area_config(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather basic settings for the area."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating area %s base config: %s",
                self.area.name,
                str(user_input),
            )
            options_schema = (
                META_AREA_BASIC_OPTIONS_SCHEMA
                if self.area.is_meta()
                else REGULAR_AREA_BASIC_OPTIONS_SCHEMA
            )
            try:
                self.area_options.update(options_schema(user_input))
            except vol.MultipleInvalid as validation:
                errors = {
                    str(error.path[0]): str(error.msg) for error in validation.errors
                }
                _LOGGER.debug(
                    "OptionsFlow: Found the following errors for area %s: %s",
                    self.area.name,
                    str(errors),
                )
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught on area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving area %s base config: %s",
                    self.area.name,
                    str(self.area_options),
                )

                return await self.async_step_show_menu()

        all_selectors = {
            CONF_TYPE: self._build_selector_select(
                sorted([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR]),
                translation_key=SelectorTranslationKeys.AREA_TYPE,
            ),
            CONF_INCLUDE_ENTITIES: self._build_selector_entity_simple(
                self.all_entities, multiple=True
            ),
            CONF_EXCLUDE_ENTITIES: self._build_selector_entity_simple(
                self.all_area_entities, multiple=True
            ),
            CONF_RELOAD_ON_REGISTRY_CHANGE: self._build_selector_boolean(),
            CONF_IGNORE_DIAGNOSTIC_ENTITIES: self._build_selector_boolean(),
        }

        options = OPTIONS_AREA_META if self.area.is_meta() else OPTIONS_AREA
        selectors = {}

        # Apply options for given area type (regular/meta)
        option_keys = [option[0] for option in options]
        for option_key in option_keys:
            selectors[option_key] = all_selectors[option_key]

        data_schema = self._build_options_schema(
            options=options, saved_options=self.area_options, selectors=selectors
        )

        return self.async_show_form(
            step_id="area_config",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_presence_tracking(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather basic settings for the area."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating area %s presence tracking config: %s",
                self.area.name,
                str(user_input),
            )
            options_schema = (
                META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
                if self.area.is_meta()
                else REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
            )
            try:
                self.area_options.update(options_schema(user_input))
            except vol.MultipleInvalid as validation:
                errors = {
                    str(error.path[0]): str(error.msg) for error in validation.errors
                }
                _LOGGER.debug(
                    "OptionsFlow: Found the following errors for area %s: %s",
                    self.area.name,
                    str(errors),
                )
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught on area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving area %s base config: %s",
                    self.area.name,
                    str(self.area_options),
                )

                return await self.async_step_show_menu()

        all_selectors = {
            CONF_PRESENCE_DEVICE_PLATFORMS: self._build_selector_select(
                sorted(ALL_PRESENCE_DEVICE_PLATFORMS), multiple=True
            ),
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: self._build_selector_select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            CONF_KEEP_ONLY_ENTITIES: self._build_selector_entity_simple(
                sorted(self.area.get_presence_sensors()), multiple=True
            ),
            CONF_CLEAR_TIMEOUT: self._build_selector_number(
                unit_of_measurement="minutes"
            ),
        }

        options = (
            OPTIONS_PRESENCE_TRACKING_META
            if self.area.is_meta()
            else OPTIONS_PRESENCE_TRACKING
        )
        selectors = {}

        # Apply options for given area type (regular/meta)
        option_keys = [option[0] for option in options]
        for option_key in option_keys:
            selectors[option_key] = all_selectors[option_key]

        data_schema = self._build_options_schema(
            options=options, saved_options=self.area_options, selectors=selectors
        )

        return self.async_show_form(
            step_id="presence_tracking",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_secondary_states(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather secondary states settings for the area."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating area %s secondary states config: %s",
                self.area.name,
                str(user_input),
            )
            area_state_schema = (
                META_AREA_SECONDARY_STATES_SCHEMA
                if self.area.is_meta()
                else SECONDARY_STATES_SCHEMA
            )
            try:
                self.area_options[CONF_SECONDARY_STATES].update(
                    area_state_schema(user_input)
                )
            except vol.MultipleInvalid as validation:
                errors = {
                    str(error.path[0]): str(error.msg) for error in validation.errors
                }
                _LOGGER.debug(
                    "OptionsFlow: Found the following errors for area %s: %s",
                    self.area.name,
                    str(errors),
                )
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught for area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving area secondary state config for area %s: %s",
                    self.area.name,
                    str(self.area_options),
                )
                return await self.async_step_show_menu()

        return self.async_show_form(
            step_id="secondary_states",
            data_schema=self._build_options_schema(
                options=(
                    OPTIONS_SECONDARY_STATES_META
                    if self.area.is_meta()
                    else OPTIONS_SECONDARY_STATES
                ),
                saved_options=self.area_options.get(CONF_SECONDARY_STATES, {}),
                dynamic_validators={
                    CONF_DARK_ENTITY: vol.In(
                        EMPTY_ENTRY + self.all_light_tracking_entities
                    ),
                    CONF_SLEEP_ENTITY: vol.In(EMPTY_ENTRY + self.all_binary_entities),
                    CONF_ACCENT_ENTITY: vol.In(EMPTY_ENTRY + self.all_binary_entities),
                    CONF_SECONDARY_STATES_CALCULATION_MODE: vol.In(CalculationMode),
                },
                selectors={
                    CONF_DARK_ENTITY: self._build_selector_entity_simple(
                        self.all_light_tracking_entities
                    ),
                    CONF_SLEEP_ENTITY: self._build_selector_entity_simple(
                        self.all_binary_entities
                    ),
                    CONF_ACCENT_ENTITY: self._build_selector_entity_simple(
                        self.all_binary_entities
                    ),
                    CONF_SLEEP_TIMEOUT: self._build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_EXTENDED_TIME: self._build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_EXTENDED_TIMEOUT: self._build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_SECONDARY_STATES_CALCULATION_MODE: self._build_selector_select(
                        options=list(CalculationMode),
                        translation_key=SelectorTranslationKeys.CALCULATION_MODE,
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_select_features(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask the user to select features to enable for the area."""

        feature_list = self._get_feature_list()

        if user_input is not None:
            selected_features = [
                feature for feature, is_selected in user_input.items() if is_selected
            ]

            _LOGGER.debug(
                "OptionsFlow: Selected features for area %s: %s",
                self.area.name,
                str(selected_features),
            )

            if CONF_ENABLED_FEATURES not in self.area_options:
                self.area_options[CONF_ENABLED_FEATURES] = {}

            for c_feature in feature_list:
                if c_feature in selected_features:
                    if c_feature not in self.area_options.get(
                        CONF_ENABLED_FEATURES, {}
                    ):
                        self.area_options[CONF_ENABLED_FEATURES][c_feature] = {}
                else:
                    # Remove feature if we had previously enabled
                    if c_feature in self.area_options.get(CONF_ENABLED_FEATURES, {}):
                        self.area_options[CONF_ENABLED_FEATURES].pop(c_feature)

            return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Selecting features for area %s from %s",
            self.area.name,
            feature_list,
        )

        return self.async_show_form(
            step_id="select_features",
            data_schema=self._build_options_schema(
                options=[(feature, False, bool) for feature in feature_list],
                saved_options={
                    feature: (
                        feature in self.area_options.get(CONF_ENABLED_FEATURES, {})
                    )
                    for feature in feature_list
                },
            ),
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save options and exit options flow."""
        _LOGGER.debug(
            "OptionsFlow: All features configured for area %s, saving config: %s",
            self.area.name,
            str(self.area_options),
        )
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
        return_to: Callable[[], Coroutine[Any, Any, ConfigFlowResult]] | None = None,
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
                self.area.name,
                str(user_input),
            )
            try:
                if custom_schema:
                    validated_input = custom_schema(user_input)
                else:
                    if not CONFIGURABLE_FEATURES[name]:
                        raise ValueError(f"No schema found for {name}")
                    validated_input = CONFIGURABLE_FEATURES[name](user_input)
            except vol.MultipleInvalid as validation:
                errors = {
                    str(error.path[0]): "malformed_input" for error in validation.errors
                }
                _LOGGER.debug("OptionsFlow: Found the following errors: %s", errors)
            except Exception as e:  # pylint: disable=broad-exception-caught
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught on area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving %s feature config for area %s: %s",
                    name,
                    self.area.name,
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
                    self.area.name,
                    name,
                    self.area_options[CONF_ENABLED_FEATURES][name],
                )

                if return_to:
                    return await return_to()

                return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Config entry options for area %s: %s",
            self.area.name,
            str(self.config_entry.options),
        )

        saved_options = self.area_options.get(CONF_ENABLED_FEATURES, {})

        if not step_name:
            step_name = f"feature_conf_{name}"

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
    async def async_step(self, step_id: str, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if step_id.startswith("feature_conf_"):
            cast(dict[str, Any], self.context)["step_id"] = step_id
            return await self.async_step_feature_conf(user_input)

        raise ValueError(f"Unknown step {step_id}")

    async def _async_step_feature_conf(
        self,
        feature_key: str,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if feature_key not in FEATURE_REGISTRY:
            return self.async_abort(reason="unknown_feature")

        feature = FEATURE_REGISTRY[feature_key]
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                if feature.schema:
                    validated = feature.schema(user_input)
                else:
                    validated = CONFIGURABLE_FEATURES[feature.name](user_input)
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

                return await self.async_step_show_menu()

        selectors: dict[str, Any] = {}

        # Wasp in a Box: UI submits a list for wasp_device_classes, but OPTIONS_WASP_IN_A_BOX
        # uses vol.In(...) (single value). Override with a multi-select selector.
        if feature_key == CONF_FEATURE_WASP_IN_A_BOX:
            selectors[CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES] = (
                self._build_selector_select(
                    options=sorted(WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
                    multiple=True,
                )
            )

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
    ) -> ConfigFlowResult:
        """Second climate step: select presets based on chosen climate entity."""

        # The first climate step stores the selected entity id under the climate feature config.
        climate_cfg = (
            self.area_options.get(CONF_ENABLED_FEATURES, {})
            .get(CONF_FEATURE_CLIMATE_CONTROL, {})
        )

        climate_entity_id: str | None = (
            climate_cfg.get(CONF_CLIMATE_CONTROL_ENTITY_ID)
            or climate_cfg.get(ATTR_ENTITY_ID)  # backward/alternate storage
        )

        if not climate_entity_id:
            return self.async_abort(reason="no_entity_selected")

        entity_registry = entityreg_async_get(self.hass)
        entity_object = entity_registry.async_get(climate_entity_id)

        if not entity_object:
            return self.async_abort(reason="invalid_entity")

        caps = entity_object.capabilities or {}
        preset_modes = caps.get(ATTR_PRESET_MODES)

        if not preset_modes:
            return self.async_abort(reason="climate_no_preset_support")

        available_preset_modes = EMPTY_ENTRY + list(preset_modes)

        selectors = {
            CONF_CLIMATE_CONTROL_PRESET_CLEAR: self._build_selector_select(
                available_preset_modes,
                translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
            ),
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: self._build_selector_select(
                available_preset_modes,
                translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
            ),
            CONF_CLIMATE_CONTROL_PRESET_SLEEP: self._build_selector_select(
                available_preset_modes,
                translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
            ),
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED: self._build_selector_select(
                available_preset_modes,
                translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
            ),
        }

        dynamic_validators = {
            CONF_CLIMATE_CONTROL_PRESET_CLEAR: vol.In(available_preset_modes),
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: vol.In(available_preset_modes),
            CONF_CLIMATE_CONTROL_PRESET_SLEEP: vol.In(available_preset_modes),
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED: vol.In(available_preset_modes),
        }

        return await self.do_feature_config(
            name=CONF_FEATURE_CLIMATE_CONTROL,
            step_name="feature_conf_climate_control_select_presets",
            options=OPTIONS_CLIMATE_CONTROL,
            custom_schema=CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
            merge_options=True,
            dynamic_validators=dynamic_validators,
            selectors=selectors,
            user_input=user_input,
        )


    async def async_step_feature_conf_light_groups(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_LIGHT_GROUPS, user_input)

    async def async_step_feature_conf_climate_control(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_CLIMATE_CONTROL, user_input)

    async def async_step_feature_conf_fan_groups(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_FAN_GROUPS, user_input)

    async def async_step_feature_conf_area_aware_media_player(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER, user_input)

    async def async_step_feature_conf_aggregates(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_AGGREGATION, user_input)

    async def async_step_feature_conf_presence_hold(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_PRESENCE_HOLD, user_input)

    async def async_step_feature_conf_ble_trackers(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_BLE_TRACKERS, user_input)

    async def async_step_feature_conf_wasp_in_a_box(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_WASP_IN_A_BOX, user_input)

    async def async_step_feature_conf_health(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._async_step_feature_conf(CONF_FEATURE_HEALTH, user_input)
