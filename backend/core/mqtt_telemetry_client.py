"""
PetroFlow IoT MQTT Telemetry System
Industrial-grade MQTT client for real-time sensor data ingestion from oil & gas equipment.
Implements singleton pattern, automatic reconnection, and thread-safe operations.
"""

import json
import logging
import threading
import time
import queue
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from contextlib import contextmanager
import traceback

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("paho-mqtt not installed. IoT telemetry features will be disabled.")

from .audit_logging_service import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()


class MQTTTelemetryClient:
    """
    Singleton MQTT client for industrial IoT telemetry.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Thread-safe message handling
    - Offline message buffering
    - QoS support (0, 1, 2)
    - TLS/SSL encryption
    - Last Will and Testament (LWT)
    - Subscription management
    - Message validation
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the MQTT telemetry client."""
        if hasattr(self, '_initialized'):
            return
        
        if not MQTT_AVAILABLE:
            logger.error("paho-mqtt library not available. Install with: pip install paho-mqtt")
            self._initialized = True
            self.enabled = False
            return
        
        self._initialized = True
        self.enabled = True
        self.config = self._load_config()
        
        # Connection state
        self.client = None
        self.connected = False
        self.connection_attempts = 0
        self.last_connection_attempt = None
        
        # Message handling
        self.message_queue = queue.Queue(maxsize=self.config['data_processing']['buffer_size'])
        self.subscriptions = {}  # topic -> (qos, callback)
        self.message_callbacks = {}  # topic_pattern -> callback
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_published': 0,
            'messages_dropped': 0,
            'connection_count': 0,
            'last_message_time': None,
            'errors': 0
        }
        
        # Threading
        self.processing_thread = None
        self.stop_processing = threading.Event()
        
        logger.info("MQTT Telemetry Client initialized")
        audit_logger.log_system("IoT Telemetry system initialized", action="IOT_INIT")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MQTT configuration from JSON file."""
        config_path = Path('config/mqtt_config.json')
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"MQTT configuration loaded from {config_path}")
                return config
            else:
                logger.warning(f"MQTT config file not found: {config_path}. Using defaults.")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading MQTT config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default MQTT configuration."""
        return {
            "broker": {
                "host": "localhost",
                "port": 1883,
                "use_tls": False,
                "keepalive": 60,
                "clean_session": True
            },
            "authentication": {
                "username": None,
                "password": None
            },
            "connection": {
                "auto_reconnect": True,
                "reconnect_delay_min": 1,
                "reconnect_delay_max": 60,
                "max_reconnect_attempts": 10
            },
            "subscriptions": {
                "default_qos": 1,
                "topics": []
            },
            "data_processing": {
                "enable_validation": True,
                "enable_unit_conversion": True,
                "enable_anomaly_detection": False,
                "buffer_size": 1000,
                "batch_processing": False,
                "batch_size": 10
            },
            "integration": {
                "feed_to_prediction_engine": True,
                "store_in_database": True,
                "log_telemetry_events": True,
                "update_ui_realtime": True
            }
        }
    
    def connect(self, broker_host: str = None, port: int = None, 
                username: str = None, password: str = None, use_tls: bool = None) -> bool:
        """
        Connect to MQTT broker.
        
        Args:
            broker_host: MQTT broker hostname/IP (overrides config)
            port: MQTT broker port (overrides config)
            username: Authentication username (overrides config)
            password: Authentication password (overrides config)
            use_tls: Enable TLS/SSL (overrides config)
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.enabled:
            logger.error("MQTT client not available")
            return False
        
        try:
            # Use provided values or fall back to config
            broker_host = broker_host or self.config['broker']['host']
            port = port or self.config['broker']['port']
            use_tls = use_tls if use_tls is not None else self.config['broker']['use_tls']
            username = username or self.config['authentication'].get('username')
            password = password or self.config['authentication'].get('password')
            
            # Create MQTT client
            client_id = f"petroflow_{int(time.time())}"
            self.client = mqtt.Client(client_id=client_id, 
                                     clean_session=self.config['broker']['clean_session'])
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe
            self.client.on_publish = self._on_publish
            
            # Set Last Will and Testament
            lwt_topic = "petroflow/system/status"
            lwt_payload = json.dumps({
                "status": "offline",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": client_id
            })
            self.client.will_set(lwt_topic, lwt_payload, qos=1, retain=True)
            
            # Authentication
            if username and password:
                self.client.username_pw_set(username, password)
                logger.info(f"MQTT authentication configured for user: {username}")
            
            # TLS/SSL
            if use_tls:
                tls_config = self.config['broker']
                if tls_config.get('tls_ca_cert'):
                    self.client.tls_set(
                        ca_certs=tls_config.get('tls_ca_cert'),
                        certfile=tls_config.get('tls_client_cert'),
                        keyfile=tls_config.get('tls_client_key')
                    )
                    logger.info("MQTT TLS/SSL configured")
                else:
                    self.client.tls_set()
                    logger.info("MQTT TLS/SSL configured (default)")
            
            # Connect to broker
            logger.info(f"Connecting to MQTT broker: {broker_host}:{port}")
            self.client.connect(broker_host, port, keepalive=self.config['broker']['keepalive'])
            
            # Start network loop in background thread
            self.client.loop_start()
            
            # Start message processing thread
            if not self.processing_thread or not self.processing_thread.is_alive():
                self.stop_processing.clear()
                self.processing_thread = threading.Thread(target=self._process_messages, daemon=True)
                self.processing_thread.start()
            
            # Wait for connection (with timeout)
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                logger.info("Successfully connected to MQTT broker")
                audit_logger.log_system(f"Connected to MQTT broker: {broker_host}:{port}", 
                                       action="MQTT_CONNECT")
                
                # Publish online status
                self._publish_status("online")
                
                # Subscribe to configured topics
                self._subscribe_to_configured_topics()
                
                return True
            else:
                logger.error("Failed to connect to MQTT broker (timeout)")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            logger.error(traceback.format_exc())
            audit_logger.log_error(f"MQTT connection failed: {e}", action="MQTT_CONNECT_ERROR")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if not self.enabled or not self.client:
            return
        
        try:
            # Publish offline status
            self._publish_status("offline")
            
            # Stop processing thread
            self.stop_processing.set()
            if self.processing_thread:
                self.processing_thread.join(timeout=5)
            
            # Disconnect client
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            
            logger.info("Disconnected from MQTT broker")
            audit_logger.log_system("Disconnected from MQTT broker", action="MQTT_DISCONNECT")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self.connected = True
            self.connection_attempts = 0
            self.stats['connection_count'] += 1
            logger.info(f"Connected to MQTT broker (rc={rc})")
        else:
            self.connected = False
            logger.error(f"Failed to connect to MQTT broker (rc={rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")
        
        # Auto-reconnect if enabled
        if self.config['connection']['auto_reconnect'] and rc != 0:
            self._attempt_reconnect()
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received."""
        try:
            # Add message to queue for processing
            if not self.message_queue.full():
                self.message_queue.put((msg.topic, msg.payload, msg.qos, msg.retain))
                self.stats['messages_received'] += 1
                self.stats['last_message_time'] = datetime.now(timezone.utc)
            else:
                self.stats['messages_dropped'] += 1
                logger.warning(f"Message queue full, dropped message from topic: {msg.topic}")
                
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
            self.stats['errors'] += 1
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscription confirmed."""
        logger.debug(f"Subscription confirmed (mid={mid}, qos={granted_qos})")
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message published."""
        self.stats['messages_published'] += 1
        logger.debug(f"Message published (mid={mid})")
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to broker with exponential backoff."""
        if self.connection_attempts >= self.config['connection']['max_reconnect_attempts']:
            logger.error("Max reconnection attempts reached. Giving up.")
            audit_logger.log_error("MQTT max reconnection attempts reached", 
                                  action="MQTT_RECONNECT_FAILED")
            return
        
        self.connection_attempts += 1
        
        # Calculate backoff delay
        min_delay = self.config['connection']['reconnect_delay_min']
        max_delay = self.config['connection']['reconnect_delay_max']
        delay = min(min_delay * (2 ** (self.connection_attempts - 1)), max_delay)
        
        logger.info(f"Attempting reconnection in {delay} seconds (attempt {self.connection_attempts})")
        time.sleep(delay)
        
        try:
            self.client.reconnect()
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {e}")
    
    def _process_messages(self):
        """Process messages from queue in background thread."""
        logger.info("Message processing thread started")
        
        while not self.stop_processing.is_set():
            try:
                # Get message from queue (with timeout)
                topic, payload, qos, retain = self.message_queue.get(timeout=1)
                
                # Process the message
                self._handle_message(topic, payload, qos, retain)
                
                self.message_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(traceback.format_exc())
                self.stats['errors'] += 1
        
        logger.info("Message processing thread stopped")
    
    def _handle_message(self, topic: str, payload: bytes, qos: int, retain: bool):
        """
        Handle received MQTT message.
        
        Args:
            topic: MQTT topic
            payload: Message payload (bytes)
            qos: Quality of Service level
            retain: Retain flag
        """
        try:
            # Decode payload
            payload_str = payload.decode('utf-8')
            
            # Parse JSON
            try:
                message_data = json.loads(payload_str)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in message from topic {topic}")
                return
            
            # Validate message format
            if self.config['data_processing']['enable_validation']:
                if not self.validate_message_format(message_data):
                    logger.warning(f"Invalid message format from topic {topic}")
                    return
            
            # Log telemetry event
            if self.config['integration']['log_telemetry_events']:
                audit_logger.log_data_access(
                    f"Received telemetry: {topic}",
                    action="TELEMETRY_RECEIVED",
                    details={'topic': topic, 'qos': qos}
                )
            
            # Process sensor data
            if '/sensors/' in topic:
                self.process_sensor_message(topic, message_data)
            
            # Process alerts
            elif '/alerts' in topic:
                self._process_alert_message(topic, message_data)
            
            # Process system health
            elif '/system/health' in topic:
                self._process_health_message(topic, message_data)
            
            # Call registered callbacks
            for pattern, callback in self.message_callbacks.items():
                if self._topic_matches(topic, pattern):
                    try:
                        callback(topic, message_data)
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling message from topic {topic}: {e}")
            logger.error(traceback.format_exc())
    
    def process_sensor_message(self, topic: str, message_data: Dict[str, Any]):
        """
        Process sensor telemetry message.
        
        Args:
            topic: MQTT topic
            message_data: Parsed message data
        """
        try:
            # Extract sensor data
            equipment_id = message_data.get('equipment_id')
            sensor_type = message_data.get('sensor_type')
            value = message_data.get('value')
            unit = message_data.get('unit')
            timestamp_str = message_data.get('timestamp')
            
            if not all([equipment_id, sensor_type, value is not None, unit]):
                logger.warning(f"Incomplete sensor data in message: {message_data}")
                return
            
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                timestamp = datetime.now(timezone.utc)
            
            # Unit conversion if enabled
            if self.config['data_processing']['enable_unit_conversion']:
                value = self._convert_to_standard_units(value, unit, sensor_type)
            
            # Store in database if enabled
            if self.config['integration']['store_in_database']:
                self._store_sensor_data(equipment_id, sensor_type, value, unit, 
                                       timestamp, message_data)
            
            # Feed to prediction engine if enabled
            if self.config['integration']['feed_to_prediction_engine']:
                self._feed_to_prediction_engine(equipment_id, sensor_type, value, timestamp)
            
            # Note: UI real-time updates moved to deprecated Streamlit layer
            # The config option 'update_ui_realtime' is now handled by the UI layer
            
            logger.debug(f"Processed sensor data: {equipment_id}/{sensor_type} = {value} {unit}")
            
        except Exception as e:
            logger.error(f"Error processing sensor message: {e}")
            logger.error(traceback.format_exc())
    
    def _process_alert_message(self, topic: str, message_data: Dict[str, Any]):
        """Process equipment alert message."""
        try:
            equipment_id = message_data.get('equipment_id')
            alert_type = message_data.get('alert_type')
            severity = message_data.get('severity', 'info')
            message = message_data.get('message', '')
            
            logger.info(f"Alert received: {equipment_id} - {alert_type} ({severity}): {message}")
            audit_logger.log_security(
                f"Equipment alert: {equipment_id} - {alert_type}",
                action="EQUIPMENT_ALERT",
                details={'severity': severity, 'message': message}
            )
            
        except Exception as e:
            logger.error(f"Error processing alert message: {e}")
    
    def _process_health_message(self, topic: str, message_data: Dict[str, Any]):
        """Process system health message."""
        try:
            status = message_data.get('status')
            logger.debug(f"System health update: {status}")
        except Exception as e:
            logger.error(f"Error processing health message: {e}")
    
    def _store_sensor_data(self, equipment_id: str, sensor_type: str, value: float,
                          unit: str, timestamp: datetime, raw_message: Dict[str, Any]):
        """Store sensor data in database."""
        try:
            from .database import get_session, SensorTelemetry
            
            with get_session() as session:
                telemetry = SensorTelemetry(
                    timestamp=timestamp,
                    equipment_id=equipment_id,
                    sensor_type=sensor_type,
                    value=value,
                    unit=unit,
                    quality=raw_message.get('quality', 'good'),
                    facility_id=raw_message.get('facility_id'),
                    area=raw_message.get('area'),
                    raw_message=json.dumps(raw_message)
                )
                session.add(telemetry)
                session.commit()
                
            logger.debug(f"Stored sensor data in database: {equipment_id}/{sensor_type}")
            
        except Exception as e:
            logger.error(f"Error storing sensor data in database: {e}")
    
    def _feed_to_prediction_engine(self, equipment_id: str, sensor_type: str, 
                                   value: float, timestamp: datetime):
        """Feed sensor data to prediction engine."""
        try:
            # This will be integrated with math_engine.py
            # For now, just log the data
            logger.debug(f"Feeding to prediction engine: {equipment_id}/{sensor_type} = {value}")
            
        except Exception as e:
            logger.error(f"Error feeding data to prediction engine: {e}")
    
    # Note: _update_ui_realtime() method removed - UI updates moved to deprecated Streamlit layer
    
    def _convert_to_standard_units(self, value: float, unit: str, sensor_type: str) -> float:
        """Convert sensor value to standard units."""
        # Simple unit conversion (can be extended)
        conversions = {
            'fahrenheit': lambda v: (v - 32) * 5/9,  # to Celsius
            'psi': lambda v: v / 14.5038,  # to Bar
            'in/s': lambda v: v * 25.4,  # to mm/s
        }
        
        unit_lower = unit.lower()
        if unit_lower in conversions:
            return conversions[unit_lower](value)
        
        return value
    
    def validate_message_format(self, message_data: Dict[str, Any]) -> bool:
        """
        Validate MQTT message format.
        
        Args:
            message_data: Parsed message data
        
        Returns:
            bool: True if valid, False otherwise
        """
        # Check for required fields
        if 'timestamp' not in message_data:
            return False
        
        # Validate sensor messages
        if 'sensor_type' in message_data:
            required_fields = ['equipment_id', 'sensor_type', 'value', 'unit']
            if not all(field in message_data for field in required_fields):
                return False
        
        return True
    
    def subscribe(self, topic: str, qos: int = None, callback: Callable = None) -> bool:
        """
        Subscribe to MQTT topic.
        
        Args:
            topic: MQTT topic (supports wildcards + and #)
            qos: Quality of Service level (0, 1, or 2)
            callback: Optional callback function for messages
        
        Returns:
            bool: True if subscription successful
        """
        if not self.enabled or not self.connected:
            logger.warning("Cannot subscribe: not connected to broker")
            return False
        
        try:
            qos = qos if qos is not None else self.config['subscriptions']['default_qos']
            
            result, mid = self.client.subscribe(topic, qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscriptions[topic] = (qos, callback)
                if callback:
                    self.message_callbacks[topic] = callback
                
                logger.info(f"Subscribed to topic: {topic} (QoS {qos})")
                audit_logger.log_system(f"Subscribed to MQTT topic: {topic}", 
                                       action="MQTT_SUBSCRIBE")
                return True
            else:
                logger.error(f"Failed to subscribe to topic: {topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from MQTT topic.
        
        Args:
            topic: MQTT topic
        
        Returns:
            bool: True if unsubscription successful
        """
        if not self.enabled or not self.connected:
            return False
        
        try:
            result, mid = self.client.unsubscribe(topic)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.subscriptions:
                    del self.subscriptions[topic]
                if topic in self.message_callbacks:
                    del self.message_callbacks[topic]
                
                logger.info(f"Unsubscribed from topic: {topic}")
                return True
            else:
                logger.error(f"Failed to unsubscribe from topic: {topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing from topic {topic}: {e}")
            return False
    
    def subscribe_to_equipment(self, equipment_id: str, sensor_types: List[str] = None) -> bool:
        """
        Subscribe to all sensors for specific equipment.
        
        Args:
            equipment_id: Equipment identifier
            sensor_types: List of sensor types (None = all sensors)
        
        Returns:
            bool: True if subscription successful
        """
        if sensor_types:
            success = True
            for sensor_type in sensor_types:
                topic = f"petroflow/+/equipment/{equipment_id}/sensors/{sensor_type}"
                success = success and self.subscribe(topic)
            return success
        else:
            topic = f"petroflow/+/equipment/{equipment_id}/sensors/#"
            return self.subscribe(topic)
    
    def subscribe_to_facility(self, facility_id: str) -> bool:
        """
        Subscribe to all equipment in a facility.
        
        Args:
            facility_id: Facility identifier
        
        Returns:
            bool: True if subscription successful
        """
        topic = f"petroflow/{facility_id}/equipment/+/sensors/#"
        return self.subscribe(topic)
    
    def _subscribe_to_configured_topics(self):
        """Subscribe to topics configured in mqtt_config.json."""
        topics = self.config['subscriptions'].get('topics', [])
        for topic in topics:
            self.subscribe(topic)
    
    def publish(self, topic: str, payload: Any, qos: int = 1, retain: bool = False) -> bool:
        """
        Publish message to MQTT topic.
        
        Args:
            topic: MQTT topic
            payload: Message payload (will be JSON-encoded if dict)
            qos: Quality of Service level
            retain: Retain flag
        
        Returns:
            bool: True if publish successful
        """
        if not self.enabled or not self.connected:
            logger.warning("Cannot publish: not connected to broker")
            return False
        
        try:
            # Convert payload to JSON if dict
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            
            result = self.client.publish(topic, payload, qos, retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to topic: {topic}")
                return True
            else:
                logger.error(f"Failed to publish to topic: {topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing to topic {topic}: {e}")
            return False
    
    def publish_sensor_data(self, equipment_id: str, sensor_type: str, 
                           value: float, unit: str, facility_id: str = "REFINERY-A",
                           area: str = None) -> bool:
        """
        Publish sensor data to MQTT.
        
        Args:
            equipment_id: Equipment identifier
            sensor_type: Type of sensor (temperature, pressure, etc.)
            value: Sensor value
            unit: Unit of measurement
            facility_id: Facility identifier
            area: Area within facility
        
        Returns:
            bool: True if publish successful
        """
        topic = f"petroflow/{facility_id}/equipment/{equipment_id}/sensors/{sensor_type}"
        
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equipment_id": equipment_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "quality": "good",
            "facility_id": facility_id,
            "area": area
        }
        
        return self.publish(topic, payload)
    
    def publish_alert(self, equipment_id: str, alert_type: str, 
                     severity: str, message: str, facility_id: str = "REFINERY-A") -> bool:
        """
        Publish equipment alert.
        
        Args:
            equipment_id: Equipment identifier
            alert_type: Type of alert
            severity: Alert severity (info, warning, critical)
            message: Alert message
            facility_id: Facility identifier
        
        Returns:
            bool: True if publish successful
        """
        topic = f"petroflow/{facility_id}/equipment/{equipment_id}/alerts"
        
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equipment_id": equipment_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "facility_id": facility_id
        }
        
        return self.publish(topic, payload, qos=2, retain=True)
    
    def _publish_status(self, status: str):
        """Publish system status."""
        topic = "petroflow/system/status"
        payload = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_id": self.client._client_id.decode() if self.client else "unknown"
        }
        self.publish(topic, payload, qos=1, retain=True)
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (with wildcards)."""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(pattern_parts) > len(topic_parts):
            return False
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == '#':
                return True
            elif pattern_part == '+':
                continue
            elif i >= len(topic_parts) or pattern_part != topic_parts[i]:
                return False
        
        return len(topic_parts) == len(pattern_parts)
    
    def is_connected(self) -> bool:
        """Check if connected to broker."""
        return self.enabled and self.connected
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status."""
        return {
            'enabled': self.enabled,
            'connected': self.connected,
            'broker': self.config['broker']['host'],
            'port': self.config['broker']['port'],
            'connection_attempts': self.connection_attempts,
            'subscriptions': list(self.subscriptions.keys()),
            'stats': self.stats.copy()
        }
    
    def get_active_subscriptions(self) -> List[str]:
        """Get list of active subscriptions."""
        return list(self.subscriptions.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get telemetry statistics."""
        return self.stats.copy()


# Singleton instance getter
_telemetry_client = None

def get_telemetry_client() -> MQTTTelemetryClient:
    """Get singleton telemetry client instance."""
    global _telemetry_client
    if _telemetry_client is None:
        _telemetry_client = MQTTTelemetryClient()
    return _telemetry_client

