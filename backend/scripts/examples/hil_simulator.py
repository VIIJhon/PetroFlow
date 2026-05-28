import time
import json
import random
import paho.mqtt.client as mqtt

BROKER_ADDRESS = "localhost"
PORT = 1883
TOPIC = "petroflow/telemetry/rig-01/pump-A"

def generate_telemetry(fault_mode: str = "normal"):
    """
    Generates realistic sensor data including physical noise.
    """
    data = {
        "equipment_id": "PUMP-A",
        "timestamp": time.time(),
        "temperature": 75.0 + random.normalvariate(0, 0.5),
        "pressure": 25.0 + random.normalvariate(0, 0.2),
        "vibration": 2.5 + random.normalvariate(0, 0.1),
        "rpm": 3000 + random.normalvariate(0, 10.0)
    }
    
    # Hardware-in-the-Loop Fault Injection
    if fault_mode == "bearing_seizure":
        data["vibration"] += 5.0 # Sudden severe vibration
        data["temperature"] += 20.0 # Extreme heat
    elif fault_mode == "sensor_drop":
        data["pressure"] = 0.0 # Simulates a disconnected transducer
        
    return data

def run_simulator():
    """Starts the HIL physical simulator and blasts data to MQTT."""
    client = mqtt.Client(client_id="hil_simulator_edge")
    
    try:
        client.connect(BROKER_ADDRESS, PORT)
        print(f"HIL Simulator connected to {BROKER_ADDRESS}:{PORT}")
    except Exception as e:
        print(f"Make sure Mosquitto or an MQTT Broker is running locally. Error: {e}")
        return
        
    print("Beginning telemetry broadcast (1Hz)... Press Ctrl+C to stop.")
    
    tick = 0
    try:
        while True:
            # Inject a sudden fault every 15 ticks
            mode = "normal"
            if tick > 0 and tick % 15 == 0:
                mode = "bearing_seizure"
                print(">>> INJECTING HARDWARE FAULT: BEARING SEIZURE <<<")
            elif tick > 0 and tick % 25 == 0:
                mode = "sensor_drop"
                print(">>> INJECTING HARDWARE FAULT: SENSOR DROP <<<")
                
            payload = generate_telemetry(mode)
            
            # QoS 1 ensures message is delivered at least once (critical for ICS)
            client.publish(TOPIC, json.dumps(payload), qos=1)
            print(f"Published to {TOPIC}: T={payload['temperature']:.1f} V={payload['vibration']:.2f}")
            
            tick += 1
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nHIL Simulator shutting down.")
    finally:
        client.disconnect()

if __name__ == "__main__":
    run_simulator()
