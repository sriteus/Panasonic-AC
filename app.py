from fastapi import FastAPI, HTTPException, Query
import asyncio
from miraie_ac import MirAIeHub, MirAIeBroker
from miraie_ac.device import Device, DeviceDetails
from miraie_ac.topic import MirAIeTopic
from miraie_ac.home import Home

app = FastAPI()

# ==========================================
# MONKEY PATCH to fix KeyError: 'modelName'
# ==========================================
async def patched_process_home_details(self, json_data):
    devices = []
    for space in json_data["spaces"]:
        for device in space["devices"]:
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
            self.topics_map[item.id] = MirAIeTopic(
                control_topic=item.control_topic,
                status_topic=item.status_topic,
                connection_status_topic=item.connection_status_topic,
            )

    if not devices:
        self.home = Home(id=json_data["homeId"], devices=[])
        return self.home

    device_ids = ",".join([d.id for d in devices])
    device_details = await self._get_device_details(device_ids)

    for dd in device_details:
        matching = [d for d in devices if d.id == dd["deviceId"]]
        if not matching: continue
        device = matching[0]
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

MirAIeHub._process_home_details = patched_process_home_details

# ==========================================
# CORE LOGIC
# ==========================================
async def run_command(command: str, phone: str, password: str, ac_name: str):
    broker = MirAIeBroker()
    hub = MirAIeHub()
    try:
        await hub.init(phone, password, broker)
        
        # Wait for MQTT connection
        for _ in range(20): 
            if hasattr(broker, 'client') and broker.client is not None:
                break
            await asyncio.sleep(0.5)
        else:
            raise Exception("MQTT Connection Timeout")

        # Find the AC (supports fuzzy matching or exact)
        target = ac_name.lower().replace(" ", "-")
        ac = next((d for d in hub.home.devices if d.name == target), None)
        
        if not ac:
            raise Exception(f"AC '{ac_name}' not found. Available: {[d.name for d in hub.home.devices]}")

        if command == "on":
            await ac.turn_on()
        else:
            await ac.turn_off()
        
        await asyncio.sleep(2)
        return True
    finally:
        await hub.http.close()

@app.get("/ac/{command}")
async def control_ac(
    command: str, 
    phone: str = Query(..., description="Registered mobile number with country code"), 
    password: str = Query(..., description="MirAIe password"), 
    name: str = Query("sarthak-ac", description="Name of the AC to control")
):
    if command not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="Invalid command. Use 'on' or 'off'.")
    
    try:
        await run_command(command, phone, password, name)
        return {"status": "success", "device": name, "command": command}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Generic MirAIe AC API is live. Usage: /ac/on?phone=...&password=...&name=..."}
