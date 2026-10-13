"""Print the advertising details (incl. address type) of the Edenwood dongle as seen by Windows."""
import asyncio

from bleak import BleakScanner

ADDR = "73:E2:DD:33:2A:9C"


async def main():
    seen = {}

    def cb(dev, adv):
        if dev.address.upper() == ADDR and "done" not in seen:
            a = dev.details.adv
            seen["done"] = True
            print("name:", adv.local_name, "rssi:", adv.rssi)
            print("address type:", getattr(a, "bluetooth_address_type", "?"))
            print("adv type:", a.advertisement_type)
            print("mfr:", {k: v.hex(" ") for k, v in adv.manufacturer_data.items()})

    async with BleakScanner(cb, scanning_mode="active"):
        for _ in range(100):
            await asyncio.sleep(0.1)
            if "done" in seen:
                break
    if "done" not in seen:
        print("not seen")


asyncio.run(main())
