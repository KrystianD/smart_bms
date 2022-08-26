import asyncio

from smart_bms.SmartBMSClient import SmartBMSClient
from smart_bms.TransportBLE import TransportBLE


async def main():
    tr = TransportBLE("xx:xx:xx:xx:xx:xx")
    await tr.start()

    client = SmartBMSClient(tr)

    while True:
        print(await client.read_basic_information())
        print(await client.read_cell_voltages())
        await asyncio.sleep(1)


asyncio.run(main())
