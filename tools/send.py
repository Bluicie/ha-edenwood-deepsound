"""Send one framed command to the Edenwood dongle and print the notifications before and after.

Usage: send.py "<type> <payload hex...>"   e.g. send.py "40 00 03 00 00 04 09 ..."
The frame becomes: 5a LEN <type> <payload> SUM, where LEN counts the bytes after LEN and
SUM is the sum of all preceding bytes & 0xFF.
"""
import asyncio
import sys
import time

from bleak import BleakClient, BleakScanner

ADDR = "73:E2:DD:33:2A:9C"
CHAR = "82838219-9293-6465-6667-738350524951"


def frame(body: bytes) -> bytes:
    head = bytes([0x5A, len(body) + 1]) + body
    return head + bytes([sum(head) & 0xFF])


async def main():
    out = frame(bytes.fromhex(sys.argv[1]))
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=15)
    if not dev:
        print("Not found (out of range, or the remote is connected right now).")
        return
    t0 = time.monotonic()

    def on_notify(_, data: bytearray):
        print(f"{time.monotonic() - t0:6.2f}s  rx {data.hex(' ')}", flush=True)

    async with BleakClient(dev, timeout=20) as client:
        await client.start_notify(CHAR, on_notify)
        await asyncio.sleep(1.5)
        print(f"{time.monotonic() - t0:6.2f}s  tx {out.hex(' ')}", flush=True)
        await client.write_gatt_char(CHAR, out, response=True)
        await asyncio.sleep(3)
    print("Done.")


asyncio.run(main())
