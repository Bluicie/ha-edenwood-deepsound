"""The Edenwood Deep Sound integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval

from .const import PRESENCE_INTERVAL
from .coordinator import DeepSoundConfigEntry, DeepSoundCoordinator
from .device import DeepSoundDevice

PLATFORMS = [Platform.BINARY_SENSOR, Platform.MEDIA_PLAYER, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: DeepSoundConfigEntry) -> bool:
    address: str = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(hass, address.upper(), connectable=True)
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Edenwood Deep Sound {address} not found; it needs a Bluetooth adapter or an ESPHome "
            "Bluetooth proxy with active connections in range"
        )

    coordinator = DeepSoundCoordinator(hass, entry, DeepSoundDevice(ble_device))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(
        async_track_time_interval(hass, coordinator.async_check_presence, PRESENCE_INTERVAL)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DeepSoundConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
