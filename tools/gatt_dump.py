"""Scan for the Edenwood dongle (RC-B), connect, and dump its GATT table. Read-only: never writes."""
import asyncio
import sys

from bleak import BleakClient, BleakScanner

ADDR = sys.argv[1] if len(sys.argv) > 1 else "73:E2:DD:33:2A:9C"


async def main():
    print(f"Scanning for {ADDR} ...")
    dev = await BleakScanner.find_device_by_address(ADDR, timeout=15)
    if not dev:
        print("Not found (out of range, or the remote is connected right now).")
        return
    print(f"Found: {dev.name} {dev.address}")
    async with BleakClient(dev, timeout=20) as client:
        print(f"Connected. MTU={client.mtu_size}")
        for svc in client.services:
            print(f"\n[Service] {svc.uuid}  ({svc.description})")
            for ch in svc.characteristics:
                props = ",".join(ch.properties)
                line = f"  [Char] {ch.uuid}  handle={ch.handle}  props={props}  ({ch.description})"
                if "read" in ch.properties:
                    try:
                        val = await client.read_gatt_char(ch)
                        line += f"\n         value={val.hex(' ')}  ascii={val.decode('ascii', 'replace')!r}"
                    except Exception as e:
                        line += f"\n         read failed: {e}"
                print(line)
                for d in ch.descriptors:
                    print(f"     [Desc] {d.uuid}  handle={d.handle}  ({d.description})")
    print("\nDisconnected.")


asyncio.run(main())
