"""Coordinator for the Edenwood Deep Sound integration."""

from __future__ import annotations

from datetime import datetime
import logging
import time

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, POLL_INTERVAL, REMOTE_ACTIVE_AFTER
from .device import DeepSoundDevice, DeepSoundError
from .protocol import DeepSoundState

_LOGGER = logging.getLogger(__name__)

type DeepSoundConfigEntry = ConfigEntry[DeepSoundCoordinator]


class DeepSoundCoordinator(DataUpdateCoordinator[DeepSoundState]):
    """Polls the dongle now and then, and right after the remote has used it."""

    config_entry: DeepSoundConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DeepSoundConfigEntry, device: DeepSoundDevice) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {device.address}",
            update_interval=POLL_INTERVAL,
        )
        self.device = device
        self.remote_active = False

    async def _async_update_data(self) -> DeepSoundState:
        try:
            await self.device.async_update()
        except DeepSoundError as err:
            if self.device.state.valid:
                # Usually the remote holding the only connection; keep the last known state.
                _LOGGER.debug("Status refresh skipped: %s", err)
                return self.device.state
            raise UpdateFailed(str(err)) from err
        return self.device.state

    @callback
    def async_check_presence(self, _now: datetime | None = None) -> None:
        """Watch the advertisements: they stop while the remote is connected."""
        info = bluetooth.async_last_service_info(self.hass, self.device.address, connectable=True)
        if info is None:
            return
        self.device.set_ble_device(info.device)
        now = time.monotonic()
        if self.device.recently_connected(now, REMOTE_ACTIVE_AFTER):
            return
        if now - info.time > REMOTE_ACTIVE_AFTER:
            self.remote_active = True
        elif self.remote_active:
            self.remote_active = False
            _LOGGER.debug("Remote released the dongle, refreshing")
            self.hass.async_create_task(self.async_request_refresh())
