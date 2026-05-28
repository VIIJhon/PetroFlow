from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import logging

logger = logging.getLogger("petroflow.tsdb")

class TSDBManager:
    """
    Time-Series Database Manager using InfluxDB 2.x.
    Replaces SQLite for storing high-frequency sensor telemetry.
    """
    def __init__(self, url: str = "http://localhost:8086", token: str = "my-super-secret-auth-token", org: str = "petroflow", bucket: str = "telemetry"):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        
    def connect(self):
        """Initializes the InfluxDB client connection."""
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            logger.info(f"Connected to InfluxDB at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
            
    def close(self):
        """Closes the InfluxDB connection."""
        if self.client:
            self.client.close()
            
    def write_telemetry(self, equipment_id: str, sensor_data: dict, timestamp: datetime = None):
        """
        Writes a single telemetry point to the TSDB.
        Automatically tags the data with the equipment_id.
        """
        if not self.write_api:
            raise ConnectionError("TSDB Client not connected. Call connect() first.")
            
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        try:
            point = Point("equipment_sensor_data") \
                .tag("equipment_id", equipment_id) \
                .time(timestamp, WritePrecision.NS)
                
            for sensor_name, value in sensor_data.items():
                # Ensure values are floats for mathematical consistency
                point.field(sensor_name, float(value))
                
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        except Exception as e:
            logger.error(f"Failed to write to TSDB for {equipment_id}: {e}")
