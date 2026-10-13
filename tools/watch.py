"""Whenever the dongle is free (advertising), connect briefly, read the status frame and print it if it changed.
Read-only. Runs for the given number of seconds (default 240).
"""
import asyncio
import sys
import time

from bleak import BleakClient, BleakScanner

ADDR = "73:E2:DD:33:2A:9C"
CHAR = "82838219-9293-6465-6667-738350524951"
RUN = float(sys.argv[1]) if len(sys.argv) > 1 else 240


async def read_status() -> bytes | None:
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=4)
    if not dev:
        return None
    got = asyncio.get_running_loop().create_future()

    def on_notify(_, data: bytearray):
        if len(data) > 2 and data[2] == 0x40 and not got.done():
            got.set_result(bytes(data))

    async with BleakClient(dev, timeout=10) as client:
        await client.start_notify(CHAR, on_notify)
        return await asyncio.wait_for(got, 2)


async def main():
    t0 = time.monotonic()
    last = None
    print(f"watching {RUN:.0f}s", flush=True)
    while time.monotonic() - t0 < RUN:
        try:
            st = await read_status()
        except (Exception, asyncio.CancelledError) as e:  # remote grabbed it, timeout, etc.
            st = None
            print(f"{time.monotonic() - t0:6.1f}s  ({type(e).__name__})", flush=True)
        if st and st != last:
            diff = ""
            if last:
                diff = "  changed " + ",".join(
                    f"idx{i}:{last[i]:02x}->{st[i]:02x}" for i in range(min(len(st), len(last))) if st[i] != last[i])
            print(f"{time.monotonic() - t0:6.1f}s  {st.hex(' ')}{diff}", flush=True)
            last = st
        await asyncio.sleep(6)
    print("done", flush=True)


asyncio.run(main())
