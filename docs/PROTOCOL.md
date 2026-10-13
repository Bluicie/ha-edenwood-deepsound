# Edenwood Deep Sound – BLE protocol notes

Goal: control the Edenwood Deep Sound home cinema (wireless speakers + subwoofer + HDMI "dongle")
from Home Assistant by talking to the dongle the same way the screen remote does.

## Devices

| What | Address | Notes |
|---|---|---|
| Dongle (BLE name `RC-B`) | `73:E2:DD:33:2A:9C` | Connectable advert, flags `0x0A`, mfr data `RS` + `RRC2405` (company id 0x5352, not a SIG id) |
| Classic BT audio sink | ? | Shows as `EDENWOOD DEEP SOUND` when pairing a phone (A2DP) |
| Remote | (own address) | Has a screen (VOL, SEARCHING, CONNECTED, HELLO, OFF). Acts as BLE central. Pairs to a dongle with + and − held 3 s. |
| ESPHome Bluetooth proxy | – | `bluetooth_proxy: active: true` near the dongle; used for Home Assistant access |

The addresses above are from one unit; yours will differ. Don't point an ESPHome `ble_client` with
auto-connect at the dongle: it would hold the dongle's only connection and lock out the remote.

## Connection behaviour (verified 2026-10-13)

- The remote connects to the dongle only while in use; RC-B stops advertising during that time.
- When the remote screen turns off it disconnects, and RC-B advertises again.
- No pairing/bonding needed: a plain connect from a Windows laptop (bleak) works.
- While something else is connected, the remote can't connect.

## GATT

```
Service  8283822d-1992-9364-6566-2d6676698267
  Char   82838219-9293-6465-6667-738350524951  handle=2  write, write-without-response, notify
         CCCD 0x2902 handle=4
```

## Frame format

```
5a  LEN  TYPE  payload...  SUM
```

- `5a` start marker
- `LEN` = number of bytes after LEN (TYPE + payload + SUM)
- `SUM` = (sum of all preceding bytes, including 5a and LEN) & 0xFF

### Type 0x40 – status (dongle → client), sent right after subscribing

```
idx: 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28
     5a 1b 40 00 07 00 00 00 07 00 00 05 01 00 05 00 05 05 05 05 05 05 00 00 00 00 00 00 ec
```

Known/suspected fields (to be confirmed by diffing after remote changes):

| idx | value | guess |
|---|---|---|
| 4 | 07 → 03 | **Source** (confirmed by cycling with the remote): 03 = BT, 05 = LINE IN, 06 = USB, 07 = HDMI. 04 unused here (optical on a sister model?) |
| 6 + 12 | pair | **MODE**: set with `13 08 <byte12>`: 00 Cinema, 01 Music, 03 Standard (02 = unnamed preset). `13 03 03` is ignored, so don't use setting 03. Original notes (confirmed by cycling): MUSIC = 00/01, CINEMA = 03/00, STANDARD = 05/03. Our `13 03 04` gave 04/00 (unknown preset) |
| 7 | 00 → 03 | **Volume / 2** (confirmed: VOL00 → 3× VOL+ → VOL06 gave 03) |
| 8 | 07 → 09 | **BASS + 5** (confirmed: +2 → +4 gave 07 → 09) |
| 11 + 19 | 05 | **SUR / SAT VOL + 5** (confirmed: always move together; `14 04 <v>` sets both) |
| 14, 16–18, 20, 21 | 05 | other -5..+5 settings stored as value+5? |

## Commands (client → dongle)

Same framing as status. Results of probe scans (2026-10-13), types 00–3F:

| Type | Payload | Effect |
|---|---|---|
| 10 | none | **Get status** → dongle answers with a 0x40 status frame (confirmed twice) |
| 40 | full status | ignored (sending status back does not set anything) |
| 13 | `04` (+ our checksum 74 read as 2nd byte) | status idx 8 (bass) 09 → **2e**; replies `5a 03 45 63 05` and `5a 03 44 03 a4` |
| 14 | `04` (+ checksum 75 read as 2nd byte) | status idx 11 and 19 → 75; reply `5a 04 60 04 75 37` (echo) |
| 15 | `04` (+ checksum 76 read as 2nd byte) | status idx 25 → 76; reply `5a 04 61 04 76 39` (echo) |
| others 00–3F | none or `04` | no reply, no status change |

Types 13/14/15 take **2 payload bytes: setting id + value**. In the scan the dongle read our checksum as
the second byte, which left out-of-range values. Restored the same evening with proper frames, status back to
the original (`... 09 00 00 05 01 ... ed`):

| Sent | Reply | Effect |
|---|---|---|
| `5a 04 14 04 05 7b` | `5a 04 60 04 05 c7` | idx 11 and 19 → 05 |
| `5a 04 15 04 00 77` | `5a 04 61 04 00 c3` | idx 25 → 00 |
| `5a 04 13 04 09 7e` | `5a 03 45 09 ab`, `5a 03 44 03 a4` | idx 8 (bass) → 09 |

So: `13 <id> <value>` with id 04 = bass (idx 8). Reply 0x45 echoes the bass value; reply 0x44 03 is volume or source (both 03).
Hypothesis to test: `13` ids map to status idx 4 + id → id 00 = source, id 03 = volume.

Safety: a blinking LED on one speaker was seen during the scan (speaker settings being changed). Keep the
system on BT with nothing playing while testing.

### Command 13 = set sound setting: `5a 04 13 <id> <value> SUM` (scan 13 XX 05, 2026-10-13)

The dongle answers with one or more reports `5a 03 <40+k> <value> SUM`, where 40+k reports status byte 3+k.

| id | Setting | Status byte | Value encoding | Confirmed |
|---|---|---|---|---|
| 01 | **Volume** | 7 | VOL / 2 (0–50) | yes: `13 01 05` → VOL10, `13 01 03` → VOL06 |
| 02 | **Mute** | 10 | 0 = off, 1 = on (05 was stored as 01). Setting volume also clears it | likely |
| 03 | **MODE** | 6 (+12) | 00 MUSIC, 03 CINEMA, 05 STANDARD (04 = unknown hidden preset) | yes |
| 04 | **BASS** | 8 | value + 5 | yes |
| 05 | ? | 14 | probably value + 5 | reply only |
| 07 | **SUR / SAT VOL** | 11 + 19 | value + 5 | yes |
| 08 | ? (changes MODE pair; 05 gave MUSIC) | 6 + 12 | ? | |
| 09 | ? | 15 | ? (was 00) | |
| 00, 06, 0a–0f | no reply | | | |

Source and power are not in command 13. All scan side effects were undone; status after restore:
`5a 1b 40 00 05 00 00 03 09 00 00 05 01 00 05 00 05 05 05 05 05 05 00 00 00 00 00 00 ef` (LINE IN, VOL06, BASS +4, MUSIC).

### Command 12 = set source / power (likely): `5a 03 12 <source> SUM`

Scan with 1-byte payload `03` (2026-10-13, system on BT): `5a 03 12 03 72` got reply `5a 03 41 03 a1`
(= status byte 4, source, is 03). With payload 04 (unused source) there was no reply, and the 2-byte form
`12 XX 03` (LEN 4) was ignored, so 12 expects exactly 1 data byte.

Source byte values: 02 = **standby** (dongle LED red, confirmed), 03 = BT, 05 = LINE IN, 06 = USB, 07 = HDMI.
Verified 2026-10-13 22:22:
- `5a 03 12 07 76` → **HDMI** (replies 41 07, 44 0b volume, 47 00 mute off). Confirmed in status.
- `5a 03 12 02 71` → ignored (no reply, stays on HDMI). Standby needs another command.
- `5a 03 12 03 72` → **BT** (replies 41 03 …, then `5a 03 42 00 9f`). Status afterwards has byte 5 = 01:
  byte 5 is the **BT link state** (01 = a device is connected). Confirmed: LED solid blue and the paired
  paired Nest Hub played its connect sound ~2 s after switching to BT, so the Hub reconnects by itself.
- `12 03` while in **standby** → ignored. Source changes only work while the system is on.

### Power on / off: FOUND (2026-10-14) — `5a 04 11 03 08 7a`

Captured by pairing the remote to a fake dongle: Android phone running nRF Connect (GATT server with the
service/characteristic above, advertiser with manufacturer data 0x5352 `RRC2405`), real dongle unplugged,
remote re-paired with **+ and − held 3 s** (screen shows the firmware version, e.g. `EDWOD VER 0203`, then
connects). The remote bonds, subscribes to notifications and shows a spinner while waiting for the dongle's
status. Writes seen: `5a 04 11 03 08 7a` (power button), `5a 04 13 01 02 74` / `5a 04 13 01 03 75` (volume).

Verified on the real dongle: `11 03 08` while on (HDMI) → standby (byte 4 = 02, replies 47 00, 44 0b, 41 02);
`11 03 08` in standby → on again with the last source (replies 41 07 …, speakers play their connect sound).
So it is a **toggle**. Type 11 looks like "remote key" with two bytes; other keys are still unknown.

Note: a dongle that is unplugged and plugged back in comes up **on** (last source), not in standby.

Earlier blind search (kept for reference; none of these could work because 11 needs exactly `03 08`):

- 1-byte payload `01` and `00` on all types 00–3F (incl. 11, 12), and `12 00`, `12 01`.
- `11 XX 03` (2-byte, XX 00–0F).
- Complete re-run 23:09–23:23 with resend of dropped commands, all delivered: no payload on types 00–FF,
  payload `01` on types 40–FF. Only `10` (status) answered; nothing woke the dongle.
- `13 XX 01` and `13 XX 00` (XX 00–0F) in standby: no wake, but **command 13 works in standby** (settings
  change and are reported). Ids 00, 01 (with 00/01), 06, 0a–0f gave no reply. `13 08 01` → MODE pair 00/01
  (MUSIC), `13 08 00` → 03/00 (CINEMA). All settings restored afterwards (status `... f4` again).
- `12 02` while on does not switch to standby.
- In standby the dongle still answers `10` (status), so it does read commands.
- In standby the dongle drops BLE connections every ~5–10 s (scan script reconnects).
- Dongle advertises with a **public** address (Windows address type 0), adv type 0 (connectable undirected).

### Commands 14 / 15 = per-channel levels: `5a 04 14|15 <ch> <value> SUM`

| Command | ch 03 | ch 04 |
|---|---|---|
| 14 | status byte 18 | status bytes 11 + 19 (SUR) |
| 15 | status byte 24 | status byte 25 |

Values look like level + 5 for 14 and 00 for 15. Scan side effects restored (`14 03 05`, `15 03 00`).

Options to learn the rest:
1. Diff status frames to map fields, then try careful writes (ask first).
2. Emulate the dongle (ESP32 advertising as RC-B) so the remote connects to us and reveals its writes.
3. nRF52840 dongle + nRF Sniffer + Wireshark to capture remote → dongle traffic.

## Tools

Standalone scripts in `tools/` (need `pip install bleak`; tested with bleak 3.0.2 on Windows):
- `gatt_dump.py` – scan, connect, dump GATT (read-only)
- `listen.py [seconds]` – subscribe and print notifications (read-only)
- `watch.py [seconds]` – read the status whenever the dongle is free and print what changed (read-only)
- `send.py "<type> <payload>"` – frame and send one command, print notifications before and after
- `scan.py <first> <last> [payload | "13 XX 05"]` – probe a range of types/values and diff the status
- `addrtype.py` – print the dongle's advertisement details (address type)
