import time
import json
import random
import paho.mqtt.client as mqtt

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883

try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()  # <-- Kluczowa linia: uruchamia wątek wysyłania/odbierania wiadomości
    print(f"--> [MOCK PUBLISHER] Connected to MQTT broker ({MQTT_BROKER}:{MQTT_PORT})")
except Exception as e:
    print(f"--> [ERROR] Cannot connect to MQTT broker: {e}")
    exit(1)

print("--> [MOCK PUBLISHER] Publishing simulated Z2M frames for 7 devices...\n")

while True:
    # 1. Nous E5
    client.publish("zigbee2mqtt/nous_e5", json.dumps({
        "temperature": round(random.uniform(20.0, 24.5), 1),
        "humidity": round(random.uniform(45.0, 58.0), 1),
        "battery": random.randint(85, 100)
    }))

    # 2. Nous A11Z
    client.publish("zigbee2mqtt/nous_a11z", json.dumps({
        "state_l1": "ON",
        "state_l2": "OFF",
        "state_l3": "ON",
        "power": round(random.uniform(15.0, 85.0), 1),
        "voltage": 230.1,
        "current": 0.25,
        "energy": 12.45
    }))

    # 3. Tuya TS0601
    client.publish("zigbee2mqtt/vibration", json.dumps({
        "alarm_status": random.choice(["normal", "alarm"]),
        "battery_state": random.choice(["medium", "high"]),
        "sensitivity": "middle",
        "silent_mode": "OFF"
    }))

    # 4. Moes XH-SY-04Z
    client.publish("zigbee2mqtt/moes_remote", json.dumps({
        "action": random.choice(["1_single", "2_double", "3_hold", "4_single"]),
        "battery": 95,
        "voltage": 3000
    }))

    # 5. SONOFF SNZB-06P
    client.publish("zigbee2mqtt/snzb_06p", json.dumps({
        "occupancy": random.choice([True, False]),
        "illumination": random.choice(["dim", "bright"]),
        "occupancy_sensitivity": "high"
    }))

    # 6. SONOFF SNZB-01P
    client.publish("zigbee2mqtt/snzb_01p", json.dumps({
        "action": random.choice(["single", "double", "long"]),
        "battery": 92,
        "voltage": 2950
    }))

    # 7. Nous P3Z
    client.publish("zigbee2mqtt/nous_p3z", json.dumps({
        "state": "ON",
        "brightness": 200,
        "color_temp": 300,
        "color": {"hex": "#FF5733"}
    }))

    print("--> Telemetry packet published to MQTT. Waiting 5 seconds...")
    time.sleep(5)