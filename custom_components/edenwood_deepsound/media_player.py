"""Media player for the Edenwood Deep Sound."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeepSoundConfigEntry, DeepSoundCoordinator
from .entity import DeepSoundEntity
from .protocol import MODES, SOURCES

SOURCE_CODES = {name: code for code, name in SOURCES.items()}
MODE_CODES = {name: code for code, name in MODES.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeepSoundConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DeepSoundMediaPlayer(entry.runtime_data)])


class DeepSoundMediaPlayer(DeepSoundEntity, MediaPlayerEntity):
    """The dongle as a media player."""

    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )
    _attr_source_list = list(SOURCE_CODES)
    _attr_sound_mode_list = list(MODE_CODES)
    _attr_volume_step = 0.02  # the remote steps VOL00..VOL100 by 2

    def __init__(self, coordinator: DeepSoundCoordinator) -> None:
        super().__init__(coordinator, "media_player")

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.ON if self.deepsound.is_on else MediaPlayerState.OFF

    @property
    def volume_level(self) -> float:
        return self.deepsound.volume / 100

    @property
    def is_volume_muted(self) -> bool:
        return self.deepsound.muted

    @property
    def source(self) -> str | None:
        return self.deepsound.source_name

    @property
    def sound_mode(self) -> str | None:
        return self.deepsound.mode_name

    async def async_turn_on(self) -> None:
        await self._send(self.coordinator.device.async_set_power(True))

    async def async_turn_off(self) -> None:
        await self._send(self.coordinator.device.async_set_power(False))

    async def async_set_volume_level(self, volume: float) -> None:
        await self._send(self.coordinator.device.async_set_volume(round(volume * 50) * 2))

    async def async_mute_volume(self, mute: bool) -> None:
        await self._send(self.coordinator.device.async_set_mute(mute))

    async def async_select_source(self, source: str) -> None:
        await self._send(self.coordinator.device.async_set_source(SOURCE_CODES[source]))

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._send(self.coordinator.device.async_set_mode(MODE_CODES[sound_mode]))
