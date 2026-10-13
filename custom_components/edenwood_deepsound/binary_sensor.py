"""Bluetooth audio link sensor for the Edenwood Deep Sound."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeepSoundConfigEntry, DeepSoundCoordinator
from .entity import DeepSoundEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeepSoundConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DeepSoundBluetoothAudio(entry.runtime_data)])


class DeepSoundBluetoothAudio(DeepSoundEntity, BinarySensorEntity):
    """On while a phone or speaker source (e.g. a Nest Hub) is connected for Bluetooth audio."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "bluetooth_audio"

    def __init__(self, coordinator: DeepSoundCoordinator) -> None:
        super().__init__(coordinator, "bluetooth_audio")

    @property
    def is_on(self) -> bool:
        return self.deepsound.bt_connected
