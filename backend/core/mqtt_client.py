import paho.mqtt.client as mqtt
import json
import logging
from typing import Callable

logger = logging.getLogger("petroflow.mqtt")

class PetroFlowMQTTClient:
    """
    Industrial MQTT Client for high-frequency, low-bandwidth telemetry ingestion.
    Designed to handle unstable offshore satellite connections.
    """
    def __init__(self, broker_address: str = "localhost", port: int = 1883, client_id: str = "petroflow_edge_01"):
        self.broker_address = broker_address
        self.port = port
        self.client_id = client_id
        
        # Configure client with Clean Session = False for persistent offline queuing (QoS 1/2)
        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.on_telemetry_received: Callable[[str, dict], None] = None
        
    def connect(self):
        """Connects to the MQTT broker and starts the background loop."""
        try:
            logger.info(f"Connecting to MQTT Broker at {self.broker_address}:{self.port}")
            # Keepalive of 60 seconds
            self.client.connect(self.broker_address, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT Connection Failed: {e}")
            raise
            
    def disconnect(self):
        """Stops the loop and gracefully disconnects."""
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server."""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker.")
            # Subscribe to the main industrial telemetry topic wildcard
            self.client.subscribe("petroflow/telemetry/#", qos=1)
        else:
            logger.error(f"Bad connection returned code={rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the server."""
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection. Auto-reconnect enabled by Paho.")
        else:
            logger.info("Disconnected successfully from MQTT broker.")

    def _on_message(self, client, userdata, msg):
        """Callback for when a PUBLISH message is received from the server."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic
            
            if self.on_telemetry_received:
                self.on_telemetry_received(topic, payload)
                
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON payload on topic {msg.topic}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
