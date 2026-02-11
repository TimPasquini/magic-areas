"""Options flow for Magic Area configuration."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import ATTR_ENTITY_ID

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
from custom_components.magic_areas.config_flows.base import ConfigBase
from custom_components.magic_areas.config_flows.feature_registry import (
    FEATURE_REGISTRY,
    FeatureConfig,
)
from custom_components.magic_areas.config_flows.entity_gatherer import (
    ConfigFlowEntityGatherer,
)
from custom_components.magic_areas.config_flows.helpers import (
    handle_step_validation,
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
    CalculationMode,
)
from custom_components.magic_areas.enums import (
    SelectorTranslationKeys,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
)
from custom_components.magic_areas.models import MagicAreasConfigEntry
from custom_components.magic_areas.policy import (
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.schemas.area import (
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
from custom_components.magic_areas.schemas.feature_builders import (
    build_climate_preset_selectors_and_validators,
    InvalidEntityError,
    NoEntitySelectedError,
    NoPresetSupportError,
)
from custom_components.magic_areas.schemas.selectors import (
    build_selector_boolean,
    build_selector_entity_simple,
    build_selector_number,
    build_selector_select,
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


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigBase):
    """Handle an option flow for Magic Areas."""

    area: MagicArea
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

    async def async_step_feature_conf(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure a specific feature."""
        step_id = self._feature_step_id or str(self.context.get("step_id", ""))
        feature_key = step_id.replace("feature_conf_", "")

        if feature_key not in FEATURE_REGISTRY:
            # noinspection PyTypeChecker
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
                # noinspection PyTypeChecker
                return await self.async_step_show_menu()

        # noinspection PyTypeChecker
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
        # noinspection PyTypeChecker
        return self.async_create_entry(title="", data=dict(self.area_options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Initialize the options flow."""
        del user_input

        self.area = self.config_entry.runtime_data.area

        _LOGGER.debug(
            "OptionsFlow: Initializing options flow for area %s", self.area.name
        )
        _LOGGER.debug(
            "OptionsFlow: Options in config entry for area %s: %s",
            self.area.name,
            str(self.config_entry.options),
        )

        # Gather all entities using helper class
        gatherer = ConfigFlowEntityGatherer(
            hass=self.hass,
            area=self.area,
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

        area_schema = META_AREA_SCHEMA if self.area.is_meta() else REGULAR_AREA_SCHEMA
        self.area_options = area_schema(dict(self.config_entry.options))

        _LOGGER.debug(
            "%s: Loaded area options: %s", self.area.name, str(self.area_options)
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
        # Handle validation and saving
        options_schema = (
            META_AREA_BASIC_OPTIONS_SCHEMA
            if self.area.is_meta()
            else REGULAR_AREA_BASIC_OPTIONS_SCHEMA
        )

        errors, validated = await handle_step_validation(
            user_input=user_input,
            schema=options_schema,
            area_name=self.area.name,
            step_name="area_config",
            area_options=self.area_options,
            on_success=self.async_step_show_menu,
        )

        if validated:
            # noinspection PyTypeChecker
            return await self.async_step_show_menu()

        all_selectors = {
            CONF_TYPE: build_selector_select(
                sorted([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR]),
                translation_key=SelectorTranslationKeys.AREA_TYPE,
            ),
            CONF_INCLUDE_ENTITIES: build_selector_entity_simple(
                self.all_entities, multiple=True
            ),
            CONF_EXCLUDE_ENTITIES: build_selector_entity_simple(
                self.all_area_entities, multiple=True
            ),
            CONF_RELOAD_ON_REGISTRY_CHANGE: build_selector_boolean(),  # type: ignore[no-untyped-call]
            CONF_IGNORE_DIAGNOSTIC_ENTITIES: build_selector_boolean(),  # type: ignore[no-untyped-call]
        }

        options = OPTIONS_AREA_META if self.area.is_meta() else OPTIONS_AREA

        # Filter selectors to match area type options
        selectors = {opt[0]: all_selectors[opt[0]] for opt in options}

        data_schema = self._build_options_schema(
            options=options, saved_options=self.area_options, selectors=selectors
        )

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="area_config",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_presence_tracking(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather basic settings for the area."""
        # Handle validation and saving
        options_schema = (
            META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
            if self.area.is_meta()
            else REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
        )

        errors, validated = await handle_step_validation(
            user_input=user_input,
            schema=options_schema,
            area_name=self.area.name,
            step_name="presence_tracking",
            area_options=self.area_options,
            on_success=self.async_step_show_menu,
        )

        if validated:
            # noinspection PyTypeChecker
            return await self.async_step_show_menu()

        all_selectors = {
            CONF_PRESENCE_DEVICE_PLATFORMS: build_selector_select(
                sorted(ALL_PRESENCE_DEVICE_PLATFORMS), multiple=True
            ),
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: build_selector_select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            CONF_KEEP_ONLY_ENTITIES: build_selector_entity_simple(
                sorted(self.area.get_presence_sensors()), multiple=True
            ),
            CONF_CLEAR_TIMEOUT: build_selector_number(
                unit_of_measurement="minutes"
            ),
        }

        options = (
            OPTIONS_PRESENCE_TRACKING_META
            if self.area.is_meta()
            else OPTIONS_PRESENCE_TRACKING
        )

        # Filter selectors to match area type options
        selectors = {opt[0]: all_selectors[opt[0]] for opt in options}

        data_schema = self._build_options_schema(
            options=options, saved_options=self.area_options, selectors=selectors
        )

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="presence_tracking",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_secondary_states(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Gather secondary states settings for the area."""
        # Handle validation and saving
        area_state_schema = (
            META_AREA_SECONDARY_STATES_SCHEMA
            if self.area.is_meta()
            else SECONDARY_STATES_SCHEMA
        )

        errors, validated = await handle_step_validation(
            user_input=user_input,
            schema=area_state_schema,
            area_name=self.area.name,
            step_name="secondary_states",
            area_options=self.area_options,
            config_key=CONF_SECONDARY_STATES,
            on_success=self.async_step_show_menu,
        )

        if validated:
            # noinspection PyTypeChecker
            return await self.async_step_show_menu()

        # noinspection PyTypeChecker
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
                    CONF_DARK_ENTITY: build_selector_entity_simple(
                        self.all_light_tracking_entities
                    ),
                    CONF_SLEEP_ENTITY: build_selector_entity_simple(
                        self.all_binary_entities
                    ),
                    CONF_ACCENT_ENTITY: build_selector_entity_simple(
                        self.all_binary_entities
                    ),
                    CONF_SLEEP_TIMEOUT: build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_EXTENDED_TIME: build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_EXTENDED_TIMEOUT: build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_SECONDARY_STATES_CALCULATION_MODE: build_selector_select(
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

            # noinspection PyTypeChecker
            return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Selecting features for area %s from %s",
            self.area.name,
            feature_list,
        )

        # noinspection PyTypeChecker
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
    ) -> config_entries.ConfigFlowResult:
        """Save options and exit options flow."""
        _LOGGER.debug(
            "OptionsFlow: All features configured for area %s, saving config: %s",
            self.area.name,
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
                errors = dict.fromkeys(
                    self._errors_from_validation(validation), "malformed_input"
                )
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
                    # noinspection PyTypeChecker
                    return await return_to()

                # noinspection PyTypeChecker
                return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Config entry options for area %s: %s",
            self.area.name,
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

                # noinspection PyTypeChecker
                return await self.async_step_show_menu()

        selectors: dict[str, Any] = {}

        # Wasp in a Box: UI submits a list for wasp_device_classes, but OPTIONS_WASP_IN_A_BOX
        # uses vol.In(...) (single value). Override with a multi-select selector.
        if feature_key == CONF_FEATURE_WASP_IN_A_BOX:
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

        # The first climate step stores the selected entity id under the climate feature config.
        climate_cfg = self.area_options.get(CONF_ENABLED_FEATURES, {}).get(
            CONF_FEATURE_CLIMATE_CONTROL, {}
        )

        climate_entity_id: str | None = climate_cfg.get(
            CONF_CLIMATE_CONTROL_ENTITY_ID
        ) or climate_cfg.get(ATTR_ENTITY_ID)  # backward/alternate storage

        # Build dynamic selectors and validators based on climate entity capabilities
        try:
            selectors, dynamic_validators = (
                build_climate_preset_selectors_and_validators(
                    self.hass,
                    climate_entity_id,
                    build_selector_select,
                    preset_config_keys=(
                        CONF_CLIMATE_CONTROL_PRESET_CLEAR,
                        CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
                        CONF_CLIMATE_CONTROL_PRESET_SLEEP,
                        CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
                    ),
                )
            )
        except NoEntitySelectedError:
            # noinspection PyTypeChecker
            return self.async_abort(reason="no_entity_selected")
        except InvalidEntityError:
            # noinspection PyTypeChecker
            return self.async_abort(reason="invalid_entity")
        except NoPresetSupportError:
            # noinspection PyTypeChecker
            return self.async_abort(reason="climate_no_preset_support")

        # noinspection PyTypeChecker
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

    async def async_step_feature_conf_light_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure light group settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            CONF_FEATURE_LIGHT_GROUPS, user_input
        )

    async def async_step_feature_conf_climate_control(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure climate control settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            CONF_FEATURE_CLIMATE_CONTROL, user_input
        )

    async def async_step_feature_conf_fan_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure fan group settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(CONF_FEATURE_FAN_GROUPS, user_input)

    async def async_step_feature_conf_area_aware_media_player(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure area-aware media player settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER, user_input
        )

    async def async_step_feature_conf_aggregates(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure aggregation settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(CONF_FEATURE_AGGREGATION, user_input)

    async def async_step_feature_conf_presence_hold(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure presence hold settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            CONF_FEATURE_PRESENCE_HOLD, user_input
        )

    async def async_step_feature_conf_ble_trackers(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure BLE tracker settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            CONF_FEATURE_BLE_TRACKERS, user_input
        )

    async def async_step_feature_conf_wasp_in_a_box(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure Wasp in a Box settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(
            CONF_FEATURE_WASP_IN_A_BOX, user_input
        )

    async def async_step_feature_conf_health(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure health feature settings."""
        # noinspection PyTypeChecker
        return await self._async_step_feature_conf(CONF_FEATURE_HEALTH, user_input)
