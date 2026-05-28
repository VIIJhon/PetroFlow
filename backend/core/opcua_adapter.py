import time
import random

class OpcUaAdapter:
    """A simulated client that mimics connecting to an industrial DCS via OPC-UA."""
    def __init__(self, endpoint_url: str = "opc.tcp://dcs-server:4840"):
        self.endpoint_url = endpoint_url
        self.connected = False
        
    def connect(self) -> bool:
        """Simulates establishing an OPC-UA connection."""
        time.sleep(0.5) # Simulate network delay
        self.connected = True
        return True
        
    def disconnect(self):
        """Simulates disconnecting."""
        self.connected = False
        
    def read_tags(self, tag_ids: list) -> dict:
        """Simulates reading real-time tags from the DCS."""
        if not self.connected:
            raise ConnectionError("OPC-UA Client not connected.")
            
        # Generate mock telemetry values around nominal ranges
        data = {}
        for tag in tag_ids:
            if "TEMP" in tag:
                data[tag] = 75.0 + random.uniform(-2.0, 2.0)
            elif "PRESS" in tag:
                data[tag] = 25.0 + random.uniform(-1.0, 1.0)
            elif "VIB" in tag:
                data[tag] = 2.5 + random.uniform(-0.5, 0.5)
            else:
                data[tag] = random.uniform(0, 100)
                
        return data
