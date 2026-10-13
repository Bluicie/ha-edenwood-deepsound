# Edenwood Deep Sound for Home Assistant

Control the **Edenwood Deep Sound** wireless home cinema (speakers + subwoofer + HDMI "dongle") from
Home Assistant over Bluetooth Low Energy, the same way its remote with the little screen does.

Unofficial; not affiliated with Edenwood or Electro Dépôt. The protocol was worked out by observation,
see [docs/PROTOCOL.md](docs/PROTOCOL.md).

## What you get

| Entity | What it does |
|---|---|
| Media player | On/off, source (Bluetooth, Line in, USB, HDMI), volume (VOL00–VOL100), mute, sound mode (Music, Standard, Cinema). State is *off* while the system is in standby. |
| Number: Bass | -5 … +5 |
| Number: Surround level | -5 … +5 (SUR / SAT VOL on the remote) |
| Binary sensor: Bluetooth audio connected | On while a phone or e.g. a Google Nest Hub is connected to the dongle for Bluetooth audio |

On/off uses the remote's power command, which toggles; the integration reads the status first and only
sends it when the state needs to change. Turning on resumes the last used source.

## Requirements

- Home Assistant with Bluetooth: a Bluetooth adapter on the HA host, or an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) **with active connections**
  (`bluetooth_proxy: active: true`) within range of the dongle. The dongle shows up as `RC-B`.
- The dongle accepts only one Bluetooth LE connection at a time, and the remote needs it. This integration
  therefore connects only for a second or two to read the status or send a command, and it backs off while
  the remote is in use. If a command fails with "the remote may be connected right now", try again a few
  seconds later.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → Custom repositories → add this repository's URL, type *Integration*.
2. Install **Edenwood Deep Sound** and restart Home Assistant.

### Manual

Copy `custom_components/edenwood_deepsound` to `/config/custom_components/` and restart Home Assistant.

## Setup

The dongle is discovered automatically (Settings → Devices & services → Discovered). You can also add it
via *Add integration → Edenwood Deep Sound*.

## Example: cast to a Nest Hub that plays through the Deep Sound

Pair the Nest Hub with the dongle once (Google Home app → Hub → Settings → Audio → Default music speaker →
*EDENWOOD DEEP SOUND*). The Hub reconnects by itself whenever the dongle switches to Bluetooth, so an
automation only has to turn the system on and select the source before playing:

```yaml
action: media_player.turn_on
target:
  entity_id: media_player.edenwood_deep_sound
```

```yaml
action: media_player.select_source
target:
  entity_id: media_player.edenwood_deep_sound
data:
  source: Bluetooth
```

## Development

The protocol code has no Home Assistant dependency and is tested with frames captured from a real dongle:

```bash
python -m pytest tests
```

`tools/` contains the standalone [bleak](https://github.com/hbldh/bleak) scripts used to explore the
protocol (GATT dump, listen, send, scan).
