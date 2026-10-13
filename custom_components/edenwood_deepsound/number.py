"""Bass and surround level for the Edenwood Deep Sound."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeepSoundConfigEntry, DeepSoundCoordinator
from .device import DeepSoundDevice
from .entity import DeepSoundEntity
from .protocol import LEVEL_MAX, LEVEL_MIN, DeepSoundState


@dataclass(frozen=True, kw_only=True)
class DeepSoundNumberDescription(NumberEntityDescription):
    value_fn: Callable[[DeepSoundState], int]
    set_fn: Callable[[DeepSoundDevice, int], Awaitable[None]]


NUMBERS = (
    DeepSoundNumberDescription(
        key="bass",
        translation_key="bass",
        value_fn=lambda s: s.bass,
        set_fn=lambda d, v: d.async_set_bass(v),
    ),
    DeepSoundNumberDescription(
        key="surround",
        translation_key="surround",
        value_fn=lambda s: s.surround,
        set_fn=lambda d, v: d.async_set_surround(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeepSoundConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(DeepSoundNumber(entry.runtime_data, d) for d in NUMBERS)


class DeepSoundNumber(DeepSoundEntity, NumberEntity):
    entity_description: DeepSoundNumberDescription
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = LEVEL_MIN
    _attr_native_max_value = LEVEL_MAX
    _attr_native_step = 1

    def __init__(self, coordinator: DeepSoundCoordinator, description: DeepSoundNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int:
        return self.entity_description.value_fn(self.deepsound)

    async def async_set_native_value(self, value: float) -> None:
        await self._send(self.entity_description.set_fn(self.coordinator.device, int(value)))
