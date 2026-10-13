"""Base entity for the Edenwood Deep Sound integration."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DeepSoundCoordinator
from .device import DeepSoundError
from .protocol import DeepSoundState


class DeepSoundEntity(CoordinatorEntity[DeepSoundCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DeepSoundCoordinator, key: str) -> None:
        super().__init__(coordinator)
        address = coordinator.device.address
        self._attr_unique_id = f"{address}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            manufacturer="Edenwood",
            model="Deep Sound",
            name="Edenwood Deep Sound",
        )

    @property
    def deepsound(self) -> DeepSoundState:
        return self.coordinator.device.state

    async def _send(self, command: Awaitable[None]) -> None:
        try:
            await command
        except DeepSoundError as err:
            raise HomeAssistantError(str(err)) from err
        finally:
            self.coordinator.async_set_updated_data(self.coordinator.device.state)
