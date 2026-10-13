"""Probe command types on the Edenwood dongle.

For each type T in the given range, send the frame 5a 02 T SUM (no payload), log any notification,
then re-subscribe to get a fresh status frame and report which bytes changed.

Usage: scan.py <first_hex> <last_hex> [payload_hex] [delay_s]
       scan.py <first_hex> <last_hex> "13 XX 05"   -> the scanned value replaces XX in the body
"""
import asyncio
import sys
import time

from bleak import BleakClient, BleakScanner

ADDR = "73:E2:DD:33:2A:9C"
CHAR = "82838219-9293-6465-6667-738350524951"
FIRST, LAST = int(sys.argv[1], 16), int(sys.argv[2], 16)
TEMPLATE = sys.argv[3] if len(sys.argv) > 3 and "XX" in sys.argv[3].upper() else None
PAYLOAD = bytes.fromhex(sys.argv[3]) if len(sys.argv) > 3 and not TEMPLATE else b""
DELAY = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0


def frame(body: bytes) -> bytes:
    head = bytes([0x5A, len(body) + 1]) + body
    return head + bytes([sum(head) & 0xFF])


async def main():
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=15)
    if not dev:
        print("Not found (out of range, or the remote is connected right now).")
        return
    t0 = time.monotonic()
    rx: list[bytes] = []
    client = BleakClient(dev, timeout=20)

    def on_notify(_, data: bytearray):
        rx.append(bytes(data))

    async def status() -> bytes | None:
        rx.clear()
        await client.stop_notify(CHAR)
        await client.start_notify(CHAR, on_notify)
        for _ in range(20):
            await asyncio.sleep(0.05)
            for r in rx:
                if len(r) > 2 and r[2] == 0x40:
                    return r
        return None

    await client.connect()
    await client.start_notify(CHAR, on_notify)
    await asyncio.sleep(0.5)
    base = next((r for r in rx if len(r) > 2 and r[2] == 0x40), None)
    print(f"base   {base.hex(' ') if base else None}", flush=True)

    todo = [(t, 0) for t in range(FIRST, LAST + 1)]
    while todo:
        t, attempt = todo.pop(0)
        body = bytes.fromhex(TEMPLATE.upper().replace("XX", f"{t:02x}")) if TEMPLATE else bytes([t]) + PAYLOAD
        out = frame(body)
        try:
            if not client.is_connected:
                print("reconnecting ...", flush=True)
                await asyncio.sleep(1)
                dev2 = await BleakScanner.find_device_by_address(ADDR, timeout=15)
                client = BleakClient(dev2 or dev, timeout=20)
                await client.connect()
                await client.start_notify(CHAR, on_notify)
                await asyncio.sleep(0.5)
            rx.clear()
            await client.write_gatt_char(CHAR, out, response=True)
            await asyncio.sleep(DELAY)
            extra = [r.hex(" ") for r in rx]
            st = await status()
        except (Exception, asyncio.CancelledError) as e:
            print(f"{time.monotonic() - t0:6.1f}s tx {out.hex(' ')}  DROPPED ({type(e).__name__}: {e})", flush=True)
            if attempt < 3:
                todo.insert(0, (t, attempt + 1))  # resend after reconnecting
            continue
        changed = ""
        if st and base and base[4] == 0x02 and st[4] != 0x02:
            print(f"{time.monotonic() - t0:6.1f}s tx {out.hex(' ')}  rx={extra}  *** WOKE UP: {st.hex(' ')}", flush=True)
            break
        if st and base and st != base:
            changed = " CHANGED idx " + ",".join(
                f"{i}:{base[i]:02x}->{st[i]:02x}" for i in range(min(len(st), len(base))) if st[i] != base[i])
            base = st
        print(f"{time.monotonic() - t0:6.1f}s tx {out.hex(' ')}  rx={extra}{changed}", flush=True)

    await client.disconnect()
    print("Done.")


asyncio.run(main())
