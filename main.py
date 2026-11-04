import asyncio
import json
import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import paho.mqtt.client as mqtt

app = FastAPI(title="IoT Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
db = client.iot_db

mqtt_global_client: Optional[mqtt.Client] = None


def on_connect(mqtt_client, userdata, flags, rc):
    mqtt_client.subscribe("zigbee2mqtt/#")

def on_message(mqtt_client, userdata, msg):
    try:
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")
        data = json.loads(payload_str)

        if topic.endswith("/bridge/state") or "/set" in topic:
            return

        doc = {
            "topic": topic,
            "device_friendly_name": topic.replace("zigbee2mqtt/", ""),
            "payload": data,
            "timestamp": datetime.utcnow()
        }

        loop = userdata['loop']
        asyncio.run_coroutine_threadsafe(db.telemetry.insert_one(doc), loop)
    except Exception:
        pass

@app.on_event("startup")
async def startup_event():
    global mqtt_global_client
    loop = asyncio.get_running_loop()
    mqtt_client = mqtt.Client(userdata={'loop': loop})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        mqtt_global_client = mqtt_client
    except Exception:
        pass


async def get_latest_payload(topic_part: str):
    try:
        doc = await db.telemetry.find_one(
            {"topic": {"$regex": topic_part}}, 
            sort=[("timestamp", -1)]
        )
        if doc and "payload" in doc:
            return doc["payload"], doc.get("timestamp")
    except Exception:
        pass
    return None, None


# --- 1. Nous E5 ---
@app.get("/api/devices/nous-e5", tags=["Zigbee Devices"])
async def get_nous_e5():
    payload, ts = await get_latest_payload("nous_e5")
    if not payload:
        raise HTTPException(status_code=404, detail="No data available for Nous E5 sensor")
    return {
        "device": "Nous E5",
        "temperature": payload.get("temperature"),
        "humidity": payload.get("humidity"),
        "battery": payload.get("battery"),
        "timestamp": ts
    }

# --- 2. Nous A11Z (3 Channels + Power Metering) ---
@app.get("/api/devices/nous-a11z", tags=["Zigbee Devices"])
async def get_nous_a11z():
    payload, ts = await get_latest_payload("nous_a11z")
    if not payload:
        raise HTTPException(status_code=404, detail="No data available for Nous A11Z power strip")
    return {
        "device": "Nous A11Z",
        "state_l1": payload.get("state_l1"),
        "state_l2": payload.get("state_l2"),
        "state_l3": payload.get("state_l3"),
        "power_watts": payload.get("power"),
        "voltage_volts": payload.get("voltage"),
        "current_amperes": payload.get("current"),
        "energy_kwh": payload.get("energy"),
        "timestamp": ts
    }

@app.post("/api/actuators/nous-a11z/control", tags=["Actuators Control"])
async def control_nous_a11z(channel: str = "l1", state: str = "ON"):
    """
    Socket control: channel ('l1', 'l2', 'l3'), state ('ON', 'OFF', 'TOGGLE')
    """
    field_name = f"state_{channel.lower()}"
    payload = {field_name: state.upper()}
    if mqtt_global_client:
        try:
            mqtt_global_client.publish("zigbee2mqtt/nous_a11z/set", json.dumps(payload))
        except Exception:
            pass
    return {"status": "command_sent", "topic": "zigbee2mqtt/nous_a11z/set", "payload": payload}

# --- 3. Tuya TS0601 (Vibration Alarm) ---
@app.get("/api/devices/vibration-alarm", tags=["Zigbee Devices"])
async def get_vibration_alarm():
    payload, ts = await get_latest_payload("vibration")
    if not payload:
        raise HTTPException(status_code=404, detail="No data available for Tuya TS0601 vibration sensor")
    return {
        "device": "Tuya TS0601",
        "alarm_status": payload.get("alarm_status"),
        "battery_state": payload.get("battery_state"),
        "sensitivity": payload.get("sensitivity"),
        "silent_mode": payload.get("silent_mode"),
        "timestamp": ts
    }

# --- 4. Moes XH-SY-04Z (4-Button Remote) ---
@app.get("/api/devices/moes-remote", tags=["Zigbee Devices"])
async def get_moes_remote():
    payload, ts = await get_latest_payload("moes_remote")
    if not payload:
        raise HTTPException(status_code=404, detail="No data available for Moes XH-SY-04Z remote")
    return {
        "device": "Moes XH-SY-04Z",
        "last_action": payload.get("action"),
        "battery": payload.get("battery"),
        "voltage_mv": payload.get("voltage"),
        "timestamp": ts
    }

# --- 5. SONOFF SNZB-06P (mmWave Presence) ---
@app.get("/api/devices/sonoff-presence", tags=["Zigbee Devices"])
async def get_sonoff_presence():
    payload, ts = await get_latest_payload("snzb_06p")
    if not payload:
        raise HTTPException(status_code=404, detail="No data available for SONOFF presence sensor")
    return {
        "device": "SONOFF SNZB-06P",
        "occupancy": payload.get("occupancy"),
        "illumination": payload.get("illumination"),
        "timestamp": ts
    }

# --- 6. SONOFF SNZB-01P (Wireless Button) ---
@app.get("/api/devices/sonoff-button", tags=["Zigbee Devices"])
async def get_sonoff_button():
    payload, ts = await get_latest_payload("snzb_01p")
    if not payload:
        raise HTTPException(status_code=404, detail="No data available for SONOFF button")
    return {
        "device": "SONOFF SNZB-01P",
        "action": payload.get("action"),
        "battery": payload.get("battery"),
        "timestamp": ts
    }

# --- 7. Nous P3Z (RGB Bulb) ---
@app.post("/api/actuators/nous-p3z/light", tags=["Actuators Control"])
async def control_nous_p3z(state: str = "ON", color_hex: str = "#FF0000", brightness: int = 254):
    payload = {
        "state": state.upper(),
        "brightness": brightness,
        "color": {"hex": color_hex}
    }
    if mqtt_global_client:
        try:
            mqtt_global_client.publish("zigbee2mqtt/nous_p3z/set", json.dumps(payload))
        except Exception:
            pass
    return {"status": "command_sent", "topic": "zigbee2mqtt/nous_p3z/set", "payload": payload}