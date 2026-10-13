"""Connect to the Edenwood dongle, subscribe to its notify characteristic and print everything it sends. Never writes data."""
import asyncio
import sys
import time

from bleak import BleakClient, BleakScanner

ADDR = "73:E2:DD:33:2A:9C"
CHAR = "82838219-9293-6465-6667-738350524951"
SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 20


async def main():
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=15)
    if not dev:
        print("Not found (out of range, or the remote is connected right now).")
        return
    t0 = time.monotonic()

    def on_notify(_, data: bytearray):
        print(f"{time.monotonic() - t0:6.2f}s  len={len(data)}  {data.hex(' ')}", flush=True)
        print(f"         ascii={bytes(data).decode('ascii', 'backslashreplace')}", flush=True)

    gone = asyncio.Event()

    def on_disconnect(_):
        print(f"{time.monotonic() - t0:6.2f}s  disconnected", flush=True)
        gone.set()

    async with BleakClient(dev, timeout=20, disconnected_callback=on_disconnect) as client:
        print(f"{time.monotonic() - t0:6.2f}s  connected", flush=True)
        await client.start_notify(CHAR, on_notify)
        print(f"{time.monotonic() - t0:6.2f}s  subscribed, listening {SECONDS:.0f}s ...", flush=True)
        try:
            await asyncio.wait_for(gone.wait(), SECONDS)
        except asyncio.TimeoutError:
            await client.stop_notify(CHAR)
    print("Done.")


asyncio.run(main())
