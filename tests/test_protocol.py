"""Protocol tests using frames captured from a real Edenwood Deep Sound dongle (2026-10-13)."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Load protocol.py directly so the tests don't need Home Assistant installed.
_spec = importlib.util.spec_from_file_location(
    "deepsound_protocol", Path(__file__).parents[1] / "custom_components/edenwood_deepsound/protocol.py"
)
p = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = p
_spec.loader.exec_module(p)

H = bytes.fromhex

STATUS_LINE_IN = H("5a1b40 00050000030900000501000500050505050505000000000000 ef")
STATUS_STANDBY = H("5a1b40 00020000 0b0900000501000500050505050505000000000000 f4")
STATUS_BT_CONNECTED = H("5a1b40 00030100 0b0900000501000500050505050505000000000000 f6")


@pytest.mark.parametrize(
    ("built", "captured"),
    [
        (p.get_status(), "5a 02 10 6c"),
        (p.power_toggle(), "5a 04 11 03 08 7a"),
        (p.set_source(0x07), "5a 03 12 07 76"),
        (p.set_source(0x03), "5a 03 12 03 72"),
        (p.set_volume(10), "5a 04 13 01 05 77"),
        (p.set_volume(6), "5a 04 13 01 03 75"),
        (p.set_mute(False), "5a 04 13 02 00 73"),
        (p.set_bass(4), "5a 04 13 04 09 7e"),
    ],
)
def test_build_matches_captured(built, captured):
    assert built.hex(" ") == captured


def test_parse_rejects_bad_checksum():
    with pytest.raises(p.ProtocolError):
        p.parse_frame(H("5a0344 03 a5"))


def test_status_line_in():
    s = p.DeepSoundState()
    assert s.apply(STATUS_LINE_IN)
    assert s.valid and s.is_on
    assert s.source_name == "Line in"
    assert s.volume == 6
    assert s.bass == 4
    assert s.surround == 0
    assert s.mode_name == "Music"
    assert not s.muted
    assert not s.bt_connected


def test_status_standby_and_bt():
    s = p.DeepSoundState()
    s.apply(STATUS_STANDBY)
    assert not s.is_on
    assert s.volume == 22
    s.apply(STATUS_BT_CONNECTED)
    assert s.is_on and s.source_name == "Bluetooth" and s.bt_connected


def test_single_byte_reports():
    s = p.DeepSoundState()
    s.apply(STATUS_LINE_IN)
    assert s.apply(H("5a0344 05 a6"))  # volume -> VOL10
    assert s.volume == 10
    assert s.apply(H("5a0341 07 a5"))  # source -> HDMI
    assert s.source_name == "HDMI"
    assert s.apply(H("5a0349 03 a9"))  # mode partner byte (status byte 12)
    assert not s.apply(H("5a0344 05 a6"))  # unchanged
    assert not s.apply(H("5a0460 0305 c6"))  # channel level echo is ignored


def test_value_checks():
    with pytest.raises(ValueError):
        p.set_source(0x02)  # standby is not a selectable source
    with pytest.raises(ValueError):
        p.set_bass(6)
    assert p.set_volume(150) == p.set_volume(100)
