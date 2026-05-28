"""
PetroFlow MQTT Telemetry Simulator
Generates realistic industrial sensor data for testing IoT telemetry system.
Simulates multiple equipment sensors publishing to MQTT broker.
"""

import json
import time
import random
import argparse
from datetime import datetime, timezone
from typing import Dict, Any

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("ERROR: paho-mqtt not installed. Install with: pip install paho-mqtt")
    MQTT_AVAILABLE = False
    exit(1)


class SensorSimulator:
    """Simulates industrial equipment sensors."""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883,
                 facility_id: str = "REFINERY-A", equipment_id: str = "PUMP-001"):
        """
        Initialize sensor simulator.
        
        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            facility_id: Facility identifier
            equipment_id: Equipment identifier
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.facility_id = facility_id
        self.equipment_id = equipment_id
        
        # Sensor baseline values
        self.sensors = {
            'temperature': {
                'baseline': 85.0,
                'unit': 'celsius',
                'min': 70.0,
                'max': 100.0,
                'noise': 2.0,
                'drift_rate': 0.1
            },
            'pressure': {
                'baseline': 30.0,
                'unit': 'bar',
                'min': 20.0,
                'max': 40.0,
                'noise': 1.5,
                'drift_rate': 0.05
            },
            'vibration': {
                'baseline': 2.5,
                'unit': 'mm/s',
                'min': 0.5,
                'max': 10.0,
                'noise': 0.5,
                'drift_rate': 0.02,
                'spike_probability': 0.05
            },
            'rpm': {
                'baseline': 2500,
                'unit': 'rpm',
                'min': 1000,
                'max': 3000,
                'noise': 50,
                'drift_rate': 5
            },
            'flow_rate': {
                'baseline': 100.0,
                'unit': 'm3/h',
                'min': 50.0,
                'max': 150.0,
                'noise': 5.0,
                'drift_rate': 0.5
            },
            'power_consumption': {
                'baseline': 75.0,
                'unit': 'kw',
                'min': 50.0,
                'max': 100.0,
                'noise': 3.0,
                'drift_rate': 0.3
            }
        }
        
        # Current sensor values
        self.current_values = {
            sensor: config['baseline'] 
            for sensor, config in self.sensors.items()
        }
        
        # MQTT client
        self.client = None
        self.connected = False
        
        # Statistics
        self.messages_sent = 0
        self.start_time = None
    
    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            client_id = f"simulator_{self.equipment_id}_{int(time.time())}"
            self.client = mqtt.Client(client_id=client_id)
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            
            print(f"Connecting to MQTT broker: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start = time.time()
            while not self.connected and (time.time() - start) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                print(f"✓ Connected to MQTT broker")
                return True
            else:
                print(f"✗ Failed to connect to MQTT broker (timeout)")
                return False
                
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("Disconnected from MQTT broker")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self.connected = True
        else:
            print(f"Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self.connected = False
        if rc != 0:
            print(f"Unexpected disconnection (rc={rc})")
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message published."""
        self.messages_sent += 1
    
    def generate_sensor_value(self, sensor_type: str) -> float:
        """
        Generate realistic sensor value with noise and drift.
        
        Args:
            sensor_type: Type of sensor
        
        Returns:
            float: Simulated sensor value
        """
        config = self.sensors[sensor_type]
        current = self.current_values[sensor_type]
        
        # Add random noise
        noise = random.gauss(0, config['noise'])
        
        # Add slow drift toward baseline
        drift = (config['baseline'] - current) * config['drift_rate']
        
        # Calculate new value
        new_value = current + noise + drift
        
        # Add occasional spikes for vibration
        if sensor_type == 'vibration' and random.random() < config.get('spike_probability', 0):
            new_value += random.uniform(2, 5)
        
        # Clamp to min/max
        new_value = max(config['min'], min(config['max'], new_value))
        
        # Update current value
        self.current_values[sensor_type] = new_value
        
        return round(new_value, 2)
    
    def publish_sensor_data(self, sensor_type: str) -> bool:
        """
        Publish sensor data to MQTT broker.
        
        Args:
            sensor_type: Type of sensor
        
        Returns:
            bool: True if publish successful
        """
        if not self.connected:
            return False
        
        try:
            value = self.generate_sensor_value(sensor_type)
            config = self.sensors[sensor_type]
            
            topic = f"petroflow/{self.facility_id}/equipment/{self.equipment_id}/sensors/{sensor_type}"
            
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "equipment_id": self.equipment_id,
                "sensor_type": sensor_type,
                "value": value,
                "unit": config['unit'],
                "quality": "good",
                "facility_id": self.facility_id,
                "area": "PROCESSING-UNIT-1"
            }
            
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            print(f"Error publishing sensor data: {e}")
            return False
    
    def publish_all_sensors(self):
        """Publish data from all sensors."""
        for sensor_type in self.sensors.keys():
            self.publish_sensor_data(sensor_type)
    
    def publish_alert(self, alert_type: str, severity: str, message: str) -> bool:
        """
        Publish equipment alert.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity (info, warning, critical)
            message: Alert message
        
        Returns:
            bool: True if publish successful
        """
        if not self.connected:
            return False
        
        try:
            topic = f"petroflow/{self.facility_id}/equipment/{self.equipment_id}/alerts"
            
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "equipment_id": self.equipment_id,
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "facility_id": self.facility_id
            }
            
            result = self.client.publish(topic, json.dumps(payload), qos=2, retain=True)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            print(f"Error publishing alert: {e}")
            return False
    
    def simulate_anomaly(self):
        """Simulate equipment anomaly (high vibration)."""
        print("WARNING: Simulating anomaly: High vibration detected")
        
        # Spike vibration
        self.current_values['vibration'] = random.uniform(7.0, 9.5)
        self.publish_sensor_data('vibration')
        
        # Publish alert
        self.publish_alert(
            alert_type="high_vibration",
            severity="warning",
            message=f"Vibration level exceeded threshold: {self.current_values['vibration']:.2f} mm/s"
        )
    
    def run_continuous(self, interval: float = 2.0, duration: int = None):
        """
        Run continuous simulation.
        
        Args:
            interval: Seconds between sensor readings
            duration: Total duration in seconds (None = infinite)
        """
        if not self.connected:
            print("Not connected to broker")
            return
        
        print(f"\n{'='*60}")
        print(f"Starting continuous simulation")
        print(f"Facility: {self.facility_id}")
        print(f"Equipment: {self.equipment_id}")
        print(f"Interval: {interval}s")
        print(f"Duration: {duration}s" if duration else "Duration: Infinite (Ctrl+C to stop)")
        print(f"{'='*60}\n")
        
        self.start_time = time.time()
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Publish all sensor data
                self.publish_all_sensors()
                
                # Occasionally simulate anomaly (5% chance every 10 iterations)
                if iteration % 10 == 0 and random.random() < 0.05:
                    self.simulate_anomaly()
                
                # Print statistics
                elapsed = time.time() - self.start_time
                rate = self.messages_sent / elapsed if elapsed > 0 else 0
                
                print(f"[{iteration:04d}] Published {len(self.sensors)} sensors | "
                      f"Total: {self.messages_sent} msgs | "
                      f"Rate: {rate:.1f} msg/s | "
                      f"Elapsed: {elapsed:.0f}s", end='\r')
                
                # Check duration
                if duration and elapsed >= duration:
                    print(f"\n\nSimulation completed ({duration}s)")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n\nSimulation stopped by user")
        
        # Print final statistics
        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"Simulation Statistics:")
        print(f"  Total messages: {self.messages_sent}")
        print(f"  Duration: {elapsed:.1f}s")
        print(f"  Average rate: {self.messages_sent/elapsed:.2f} msg/s")
        print(f"{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PetroFlow MQTT Telemetry Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with defaults (localhost:1883, PUMP-001)
  python mqtt_simulator.py
  
  # Specify broker and equipment
  python mqtt_simulator.py --broker mqtt.example.com --port 1883 --equipment PUMP-002
  
  # Run for 60 seconds with 1 second interval
  python mqtt_simulator.py --duration 60 --interval 1
  
  # Simulate multiple equipment (run in separate terminals)
  python mqtt_simulator.py --equipment PUMP-001
  python mqtt_simulator.py --equipment PUMP-002
  python mqtt_simulator.py --equipment COMPRESSOR-001
        """
    )
    
    parser.add_argument('--broker', default='localhost',
                       help='MQTT broker hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=1883,
                       help='MQTT broker port (default: 1883)')
    parser.add_argument('--facility', default='REFINERY-A',
                       help='Facility ID (default: REFINERY-A)')
    parser.add_argument('--equipment', default='PUMP-001',
                       help='Equipment ID (default: PUMP-001)')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='Seconds between readings (default: 2.0)')
    parser.add_argument('--duration', type=int, default=None,
                       help='Simulation duration in seconds (default: infinite)')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("PetroFlow MQTT Telemetry Simulator")
    print("="*60 + "\n")
    
    # Create simulator
    simulator = SensorSimulator(
        broker_host=args.broker,
        broker_port=args.port,
        facility_id=args.facility,
        equipment_id=args.equipment
    )
    
    # Connect to broker
    if not simulator.connect():
        print("\nFailed to connect to MQTT broker. Exiting.")
        return 1
    
    # Run simulation
    try:
        simulator.run_continuous(interval=args.interval, duration=args.duration)
    finally:
        simulator.disconnect()
    
    return 0


if __name__ == '__main__':
    exit(main())

