"""Feature modules package API."""

from custom_components.magic_areas.features.modules.aggregates import (
    AggregatesFeatureModule,
)
from custom_components.magic_areas.features.modules.area_aware_media_player import (
    AreaAwareMediaPlayerFeatureModule,
)
from custom_components.magic_areas.features.modules.ble_trackers import (
    BLETrackersFeatureModule,
)
from custom_components.magic_areas.features.modules.climate_control import (
    ClimateControlFeatureModule,
)
from custom_components.magic_areas.features.modules.cover_groups import (
    CoverGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.fan_groups import (
    FanGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.health import (
    HealthFeatureModule,
)
from custom_components.magic_areas.features.modules.light_groups import (
    LightGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.media_player_groups import (
    MediaPlayerGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.presence_hold import (
    PresenceHoldFeatureModule,
)
from custom_components.magic_areas.features.modules.wasp_in_a_box import (
    WaspInABoxFeatureModule,
)

__all__ = [
    "AggregatesFeatureModule",
    "AreaAwareMediaPlayerFeatureModule",
    "BLETrackersFeatureModule",
    "ClimateControlFeatureModule",
    "CoverGroupsFeatureModule",
    "FanGroupsFeatureModule",
    "HealthFeatureModule",
    "LightGroupsFeatureModule",
    "MediaPlayerGroupsFeatureModule",
    "PresenceHoldFeatureModule",
    "WaspInABoxFeatureModule",
]
