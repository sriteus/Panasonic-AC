import sys
import asyncio
from miraie_ac import MirAIeHub, MirAIeBroker
from miraie_ac.device import Device, DeviceDetails
from miraie_ac.topic import MirAIeTopic
from miraie_ac.home import Home

# ==========================================
# MONKEY PATCH to fix KeyError: 'modelName'
# ==========================================
async def patched_process_home_details(self, json_data):
    devices = []
    for space in json_data["spaces"]:
        for device in space["devices"]:
            # Only include ACs for this control script
            if device.get("category") != "AC":
                continue
                
            item = Device(
                id=device["deviceId"],
                name=str(device["deviceName"]).lower().replace(" ", "-"),
                friendly_name=device["deviceName"],
                control_topic=str(device["topic"][0]) + "/control",
                status_topic=str(device["topic"][0]) + "/status",
                connection_status_topic=str(device["topic"][0]) + "/connectionStatus",
                broker=self._broker,
            )
            devices.append(item)
            topic = MirAIeTopic(
                control_topic=item.control_topic,
                status_topic=item.status_topic,
                connection_status_topic=item.connection_status_topic,
            )
            self.topics_map[item.id] = topic

    if not devices:
        self.home = Home(id=json_data["homeId"], devices=[])
        return self.home

    device_ids = ",".join(list(map(lambda device: device.id, devices)))
    device_details = await self._get_device_details(device_ids)

    for dd in device_details:
        matching_devices = [d for d in devices if d.id == dd["deviceId"]]
        if not matching_devices:
            continue
        device = matching_devices[0]

        details = DeviceDetails(
            model_name=dd.get("modelName", "Unknown"),
            mac_address=dd.get("macAddress", ""),
            category=dd.get("category", "AC"),
            brand=dd.get("brand", "Panasonic"),
            firmware_version=dd.get("firmwareVersion", ""),
            serial_number=dd.get("serialNumber", ""),
            model_number=dd.get("modelNumber", ""),
            product_serial_number=dd.get("productSerialNumber", ""),
        )
        device.set_details(details)

    self.home = Home(id=json_data["homeId"], devices=devices)
    return self.home

# Apply the patch
MirAIeHub._process_home_details = patched_process_home_details

async def control_ac(command):
    # ==========================================
    # UPDATE THESE WITH YOUR MIRAIE CREDENTIALS
    # ==========================================
    mobile = "+919560997802" # Replace with your registered mobile number (include country code)
    password = "Sanjaygarg4s" # Replace with your Miraie app password

    # Instantiate the broker and hub
    broker = MirAIeBroker()
    hub = MirAIeHub()
    
    print("Initializing connection to MirAIe...")
    await hub.init(mobile, password, broker)
    
    # Wait till connection has been established
    async def waitForClient():
        while not hasattr(broker, 'client') or getattr(broker, 'client') is None:
            await asyncio.sleep(0.5)
            
    await waitForClient()
    print("Connected successfully!")
    
    if not hub.home.devices:
        print("No devices found on this account!")
        # We might need to sleep slightly and wait or terminate
        return

    # Find the specific AC
    target_name = "sarthak-ac" 
    ac = next((d for d in hub.home.devices if d.name == target_name), None)
    
    if not ac:
        print(f"Device '{target_name}' not found!")
        print("Available ACs:")
        for d in hub.home.devices:
            print(f" - {d.name} ({d.friendly_name})")
        return

    if command == "on":
        print(f"Turning ON: {ac.friendly_name}")
        await ac.turn_on()
        print("AC turned ON!")
    elif command == "off":
        print(f"Turning OFF: {ac.friendly_name}")
        await ac.turn_off()
        print("AC turned OFF!")
    else:
        print(f"Unknown command: {command}")
        
    # Brief pause to ensure the broker sends the message
    await asyncio.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ac_control.py [on|off]")
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    if cmd not in ["on", "off"]:
        print("Command must be 'on' or 'off'. Example: `python ac_control.py on`")
        sys.exit(1)
        
    asyncio.run(control_ac(cmd))
