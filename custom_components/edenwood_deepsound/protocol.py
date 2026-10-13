"""Edenwood Deep Sound BLE protocol (no Home Assistant imports, so it can be unit tested).

Every message, in both directions, is one GATT write/notification on a single characteristic:

    5a  LEN  TYPE  payload...  SUM

LEN counts the bytes after itself (TYPE + payload + SUM) and SUM is the sum of all preceding bytes & 0xFF.
See docs/PROTOCOL.md for how this was worked out.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SERVICE_UUID = "8283822d-1992-9364-6566-2d6676698267"
CHAR_UUID = "82838219-9293-6465-6667-738350524951"
MANUFACTURER_ID = 0x5352  # "RS", not an official Bluetooth SIG id

START = 0x5A

# Message types, client -> dongle
CMD_GET_STATUS = 0x10
CMD_KEY = 0x11  # remote key; 03 08 is the power button (toggles standby/on)
CMD_SET_SOURCE = 0x12
CMD_SET_SETTING = 0x13

# Message types, dongle -> client
MSG_STATUS = 0x40  # full status; 0x41..0x5f report a single status byte (0x40 + index)
MSG_REPORT_LAST = 0x5F

# Setting ids for CMD_SET_SETTING
SETTING_VOLUME = 0x01
SETTING_MUTE = 0x02
SETTING_MODE = 0x03
SETTING_BASS = 0x04
SETTING_SURROUND = 0x07

# Indexes into the 25-byte status payload (status frame byte = index + 3)
IDX_SOURCE = 1
IDX_BT_CONNECTED = 2
IDX_MODE = 3
IDX_VOLUME = 4
IDX_BASS = 5
IDX_MUTE = 7
IDX_SURROUND = 8
STATUS_LEN = 25

SOURCE_STANDBY = 0x02
SOURCES: dict[int, str] = {0x03: "Bluetooth", 0x05: "Line in", 0x06: "USB", 0x07: "HDMI"}
MODES: dict[int, str] = {0x00: "Music", 0x05: "Standard", 0x03: "Cinema"}

VOLUME_MAX = 100  # as shown on the remote, VOL00..VOL100 in steps of 2
LEVEL_OFFSET = 5  # bass and surround are -5..+5, stored as value + 5
LEVEL_MIN, LEVEL_MAX = -5, 5


class ProtocolError(ValueError):
    """Raised for a malformed frame."""


def build_frame(body: bytes) -> bytes:
    """Wrap TYPE + payload into a complete frame."""
    head = bytes((START, len(body) + 1)) + body
    return head + bytes((sum(head) & 0xFF,))


def parse_frame(data: bytes) -> tuple[int, bytes]:
    """Validate a frame and return (type, payload)."""
    if len(data) < 4 or data[0] != START:
        raise ProtocolError(f"not a frame: {data.hex(' ')}")
    if data[1] != len(data) - 2:
        raise ProtocolError(f"bad length: {data.hex(' ')}")
    if sum(data[:-1]) & 0xFF != data[-1]:
        raise ProtocolError(f"bad checksum: {data.hex(' ')}")
    return data[2], bytes(data[3:-1])


def get_status() -> bytes:
    return build_frame(bytes((CMD_GET_STATUS,)))


def power_toggle() -> bytes:
    """The remote's power button: standby -> on (last source), on -> standby."""
    return build_frame(bytes((CMD_KEY, 0x03, 0x08)))


def set_source(source: int) -> bytes:
    if source not in SOURCES:
        raise ValueError(f"unknown source {source:#04x}")
    return build_frame(bytes((CMD_SET_SOURCE, source)))


def set_volume(volume: int) -> bytes:
    """Volume as shown on the remote, 0..100 (odd values round down)."""
    volume = max(0, min(VOLUME_MAX, volume))
    return build_frame(bytes((CMD_SET_SETTING, SETTING_VOLUME, volume // 2)))


def set_mute(mute: bool) -> bytes:
    return build_frame(bytes((CMD_SET_SETTING, SETTING_MUTE, int(mute))))


def set_mode(mode: int) -> bytes:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode:#04x}")
    return build_frame(bytes((CMD_SET_SETTING, SETTING_MODE, mode)))


def _set_level(setting: int, level: int) -> bytes:
    if not LEVEL_MIN <= level <= LEVEL_MAX:
        raise ValueError(f"level {level} out of range")
    return build_frame(bytes((CMD_SET_SETTING, setting, level + LEVEL_OFFSET)))


def set_bass(level: int) -> bytes:
    return _set_level(SETTING_BASS, level)


def set_surround(level: int) -> bytes:
    return _set_level(SETTING_SURROUND, level)


@dataclass
class DeepSoundState:
    """Decoded status of the dongle."""

    payload: bytearray = field(default_factory=lambda: bytearray(STATUS_LEN))
    valid: bool = False

    def apply(self, data: bytes) -> bool:
        """Apply a notification. Returns True when it changed something we track."""
        msg_type, payload = parse_frame(data)
        if msg_type == MSG_STATUS and len(payload) == STATUS_LEN:
            changed = not self.valid or payload != self.payload
            self.payload[:] = payload
            self.valid = True
            return changed
        if MSG_STATUS < msg_type <= MSG_REPORT_LAST and len(payload) == 1:
            index = msg_type - MSG_STATUS
            changed = self.payload[index] != payload[0]
            self.payload[index] = payload[0]
            return changed
        return False  # e.g. 0x60/0x61 echoes of channel level commands

    @property
    def source(self) -> int:
        return self.payload[IDX_SOURCE]

    @property
    def is_on(self) -> bool:
        return self.source != SOURCE_STANDBY

    @property
    def source_name(self) -> str | None:
        return SOURCES.get(self.source)

    @property
    def bt_connected(self) -> bool:
        return bool(self.payload[IDX_BT_CONNECTED])

    @property
    def volume(self) -> int:
        """0..100 as shown on the remote."""
        return self.payload[IDX_VOLUME] * 2

    @property
    def muted(self) -> bool:
        return bool(self.payload[IDX_MUTE])

    @property
    def mode(self) -> int:
        return self.payload[IDX_MODE]

    @property
    def mode_name(self) -> str | None:
        return MODES.get(self.mode)

    @property
    def bass(self) -> int:
        return self.payload[IDX_BASS] - LEVEL_OFFSET

    @property
    def surround(self) -> int:
        return self.payload[IDX_SURROUND] - LEVEL_OFFSET
