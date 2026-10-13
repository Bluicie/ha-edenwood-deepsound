"""Short-lived BLE sessions with the Edenwood Deep Sound dongle."""

from __future__ import annotations

import asyncio
import logging
import time

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from . import protocol
from .protocol import CHAR_UUID, MSG_STATUS, DeepSoundState, ProtocolError

_LOGGER = logging.getLogger(__name__)

STATUS_TIMEOUT = 3.0  # the dongle sends its full status right after we subscribe
REPLY_WAIT = 0.6  # time to collect the single-byte reports that follow a command


class DeepSoundError(Exception):
    """Communication with the dongle failed."""


class DeepSoundStandbyError(DeepSoundError):
    """The dongle ignores commands in standby."""


class DeepSoundDevice:
    """One dongle. Every call connects, reads the status, sends, and disconnects again."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._lock = asyncio.Lock()
        self._connected = False
        self.last_disconnect = 0.0
        self.state = DeepSoundState()

    @property
    def address(self) -> str:
        return self._ble_device.address

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Use the latest BLEDevice, so HA can route through the best adapter or proxy."""
        self._ble_device = ble_device

    def recently_connected(self, now: float, margin: float) -> bool:
        """True while our own connection could explain the dongle not advertising."""
        return self._connected or now - self.last_disconnect < margin

    async def async_update(self) -> None:
        await self._session(())

    async def async_set_power(self, on: bool) -> None:
        """The dongle only has a power toggle, so send it only when the state differs."""
        await self._session((protocol.power_toggle(), protocol.get_status()), want_on=on)

    async def async_set_source(self, source: int) -> None:
        await self._command(protocol.set_source(source))

    async def async_set_volume(self, volume: int) -> None:
        await self._command(protocol.set_volume(volume))

    async def async_set_mute(self, mute: bool) -> None:
        await self._command(protocol.set_mute(mute))

    async def async_set_mode(self, mode: int) -> None:
        await self._command(protocol.set_mode(mode))

    async def async_set_bass(self, level: int) -> None:
        await self._command(protocol.set_bass(level))

    async def async_set_surround(self, level: int) -> None:
        await self._command(protocol.set_surround(level))

    async def _command(self, frame: bytes) -> None:
        # Not every setting reports its own status byte back (MODE doesn't), so finish with a full status.
        await self._session((frame, protocol.get_status()), require_on=True)

    async def _session(
        self, frames: tuple[bytes, ...], require_on: bool = False, want_on: bool | None = None
    ) -> None:
        """Connect, wait for the status, send frames, disconnect."""
        async with self._lock:
            got_status = asyncio.Event()

            def on_notify(_char: object, data: bytearray) -> None:
                try:
                    self.state.apply(bytes(data))
                except ProtocolError as err:
                    _LOGGER.debug("Ignoring notification: %s", err)
                    return
                if data[2] == MSG_STATUS:
                    got_status.set()

            try:
                self._connected = True
                client = await establish_connection(
                    BleakClientWithServiceCache, self._ble_device, self.address, max_attempts=3
                )
                try:
                    await client.start_notify(CHAR_UUID, on_notify)
                    async with asyncio.timeout(STATUS_TIMEOUT):
                        await got_status.wait()
                    if want_on is not None and self.state.is_on == want_on:
                        frames = ()  # already in the requested power state
                    if frames and require_on and not self.state.is_on:
                        raise DeepSoundStandbyError(
                            "The Edenwood Deep Sound is in standby; turn it on first"
                        )
                    for frame in frames:
                        _LOGGER.debug("Sending %s", frame.hex(" "))
                        await client.write_gatt_char(CHAR_UUID, frame, response=True)
                    if frames:
                        await asyncio.sleep(REPLY_WAIT)
                finally:
                    await client.disconnect()
            except (BleakError, TimeoutError) as err:
                raise DeepSoundError(
                    f"Could not talk to the Edenwood Deep Sound ({type(err).__name__}: {err}); "
                    "the remote may be connected right now"
                ) from err
            finally:
                self._connected = False
                self.last_disconnect = time.monotonic()
