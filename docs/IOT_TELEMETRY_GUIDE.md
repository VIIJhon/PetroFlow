# PetroFlow IoT MQTT Telemetry System - Complete Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [MQTT Topic Hierarchy](#mqtt-topic-hierarchy)
5. [Message Format](#message-format)
6. [Configuration](#configuration)
7. [Using the System](#using-the-system)
8. [Simulator Usage](#simulator-usage)
9. [Integration with Prediction Engine](#integration-with-prediction-engine)
10. [Security Best Practices](#security-best-practices)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## Overview

The PetroFlow IoT MQTT Telemetry System enables real-time ingestion of sensor data from industrial oil & gas equipment. It uses the MQTT protocol (Message Queuing Telemetry Transport), an industry-standard lightweight messaging protocol designed for IoT applications.

### Key Features

- ✅ **Real-time Data Ingestion**: Receive sensor data from equipment in real-time
- ✅ **Automatic Reconnection**: Handles network interruptions gracefully
- ✅ **Thread-Safe Operations**: Non-blocking message processing
- ✅ **Offline Buffering**: Queues messages when disconnected
- ✅ **QoS Support**: Quality of Service levels 0, 1, and 2
- ✅ **TLS/SSL Encryption**: Secure data transmission
- ✅ **Database Integration**: Automatic storage of telemetry data
- ✅ **Prediction Engine Integration**: Feeds data to ML models
- ✅ **UI Real-time Updates**: Live dashboard updates

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Industrial Equipment                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Pump-001 │  │ Pump-002 │  │Compressor│  │ Turbine  │       │
│  │ Sensors  │  │ Sensors  │  │ Sensors  │  │ Sensors  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
                      ▼
        ┌─────────────────────────┐
        │    MQTT Broker          │
        │  (Mosquitto/HiveMQ)     │
        │    Port: 1883/8883      │
        └─────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────┐
        │  PetroFlow Application  │
        │                         │
        │  ┌───────────────────┐  │
        │  │ MQTT Client       │  │
        │  │ (iot_telemetry.py)│  │
        │  └─────────┬─────────┘  │
        │            │             │
        │  ┌─────────▼─────────┐  │
        │  │ Message Processor │  │
        │  └─────────┬─────────┘  │
        │            │             │
        │  ┌─────────▼─────────┐  │
        │  │   Data Storage    │  │
        │  │  (SQLite/Postgres)│  │
        │  └───────────────────┘  │
        │            │             │
        │  ┌─────────▼─────────┐  │
        │  │ Prediction Engine │  │
        │  │  (math_engine.py) │  │
        │  └───────────────────┘  │
        │            │             │
        │  ┌─────────▼─────────┐  │
        │  │   UI Dashboard    │  │
        │  │   (Streamlit)     │  │
        │  └───────────────────┘  │
        └─────────────────────────┘
```

---

## Installation & Setup

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or install paho-mqtt separately
pip install paho-mqtt==1.6.1
```

### 2. Install MQTT Broker

Choose one of the following MQTT brokers:

#### Option A: Mosquitto (Recommended for local development)

**Windows:**
```bash
# Using Chocolatey
choco install mosquitto

# Or download from: https://mosquitto.org/download/
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients
```

**macOS:**
```bash
brew install mosquitto
```

#### Option B: HiveMQ (Cloud-based)

Sign up at https://www.hivemq.com/mqtt-cloud-broker/

#### Option C: EMQX (Enterprise-grade)

Download from https://www.emqx.io/downloads

### 3. Start MQTT Broker

**Mosquitto:**
```bash
# Start with default configuration
mosquitto -v

# Or as a service (Linux)
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Windows (as service)
net start mosquitto
```

**Verify broker is running:**
```bash
# Test with mosquitto_sub (subscribe)
mosquitto_sub -h localhost -t test/topic -v

# In another terminal, publish a test message
mosquitto_pub -h localhost -t test/topic -m "Hello MQTT"
```

### 4. Configure PetroFlow

Edit `mqtt_config.json`:

```json
{
  "broker": {
    "host": "localhost",
    "port": 1883,
    "use_tls": false
  },
  "authentication": {
    "username": null,
    "password": null
  }
}
```

---

## MQTT Topic Hierarchy

PetroFlow uses a structured topic hierarchy following industrial IoT best practices:

### Topic Structure

```
petroflow/
├── {facility_id}/
│   ├── equipment/{equipment_id}/
│   │   ├── sensors/
│   │   │   ├── temperature
│   │   │   ├── pressure
│   │   │   ├── vibration
│   │   │   ├── flow_rate
│   │   │   ├── rpm
│   │   │   └── power_consumption
│   │   ├── status
│   │   ├── alerts
│   │   └── diagnostics
│   ├── area/{area_name}/
│   └── system/
│       ├── health
│       └── commands
```

### Topic Examples

```
petroflow/REFINERY-A/equipment/PUMP-001/sensors/temperature
petroflow/REFINERY-A/equipment/PUMP-001/sensors/pressure
petroflow/REFINERY-A/equipment/PUMP-001/alerts
petroflow/REFINERY-A/system/health
```

### Wildcard Subscriptions

MQTT supports two types of wildcards:

- **`+` (Single-level wildcard)**: Matches one topic level
  - Example: `petroflow/+/equipment/PUMP-001/sensors/temperature`
  - Matches: `petroflow/REFINERY-A/equipment/PUMP-001/sensors/temperature`
  - Matches: `petroflow/REFINERY-B/equipment/PUMP-001/sensors/temperature`

- **`#` (Multi-level wildcard)**: Matches multiple topic levels
  - Example: `petroflow/REFINERY-A/equipment/+/sensors/#`
  - Matches all sensors for all equipment in REFINERY-A

### Recommended Subscriptions

```
# All sensors from all equipment in all facilities
petroflow/+/equipment/+/sensors/#

# All alerts from all equipment
petroflow/+/equipment/+/alerts

# System health messages
petroflow/+/system/health

# Specific equipment
petroflow/REFINERY-A/equipment/PUMP-001/sensors/#
```

---

## Message Format

### Sensor Data Message

All sensor messages must follow this JSON format:

```json
{
  "timestamp": "2026-05-05T19:55:00.000Z",
  "equipment_id": "PUMP-001",
  "sensor_type": "temperature",
  "value": 85.5,
  "unit": "celsius",
  "quality": "good",
  "facility_id": "REFINERY-A",
  "area": "PROCESSING-UNIT-1"
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string (ISO 8601) | Yes | UTC timestamp of measurement |
| `equipment_id` | string | Yes | Unique equipment identifier |
| `sensor_type` | string | Yes | Type of sensor (temperature, pressure, etc.) |
| `value` | number | Yes | Sensor reading value |
| `unit` | string | Yes | Unit of measurement |
| `quality` | string | No | Data quality indicator (good, bad, uncertain) |
| `facility_id` | string | No | Facility identifier |
| `area` | string | No | Area within facility |

### Alert Message

```json
{
  "timestamp": "2026-05-05T19:55:00.000Z",
  "equipment_id": "PUMP-001",
  "alert_type": "high_vibration",
  "severity": "warning",
  "message": "Vibration level exceeded threshold: 8.5 mm/s",
  "facility_id": "REFINERY-A"
}
```

**Severity Levels:**
- `info`: Informational message
- `warning`: Requires attention
- `critical`: Immediate action required

### System Health Message

```json
{
  "timestamp": "2026-05-05T19:55:00.000Z",
  "status": "online",
  "client_id": "petroflow_1234567890"
}
```

---

## Configuration

### mqtt_config.json Reference

```json
{
  "broker": {
    "host": "localhost",              // MQTT broker hostname/IP
    "port": 1883,                     // MQTT broker port (1883=plain, 8883=TLS)
    "use_tls": false,                 // Enable TLS/SSL encryption
    "tls_ca_cert": null,              // Path to CA certificate
    "tls_client_cert": null,          // Path to client certificate
    "tls_client_key": null,           // Path to client key
    "keepalive": 60,                  // Keepalive interval (seconds)
    "clean_session": true             // Clean session flag
  },
  "authentication": {
    "username": null,                 // MQTT username (null = no auth)
    "password": null                  // MQTT password
  },
  "connection": {
    "auto_reconnect": true,           // Automatic reconnection
    "reconnect_delay_min": 1,         // Min delay between reconnects (seconds)
    "reconnect_delay_max": 60,        // Max delay between reconnects (seconds)
    "max_reconnect_attempts": 10      // Max reconnection attempts
  },
  "subscriptions": {
    "default_qos": 1,                 // Default Quality of Service (0, 1, or 2)
    "topics": [                       // Topics to subscribe on connect
      "petroflow/+/equipment/+/sensors/#",
      "petroflow/+/equipment/+/alerts",
      "petroflow/+/system/health"
    ]
  },
  "data_processing": {
    "enable_validation": true,        // Validate message format
    "enable_unit_conversion": true,   // Convert units to standard
    "enable_anomaly_detection": false,// Detect anomalies in data
    "buffer_size": 1000,              // Message queue size
    "batch_processing": false,        // Process messages in batches
    "batch_size": 10                  // Batch size if enabled
  },
  "integration": {
    "feed_to_prediction_engine": true,// Send data to ML engine
    "store_in_database": true,        // Store in database
    "log_telemetry_events": true,     // Log to audit system
    "update_ui_realtime": true        // Update UI in real-time
  }
}
```

### Quality of Service (QoS) Levels

| QoS | Description | Use Case |
|-----|-------------|----------|
| 0 | At most once (fire and forget) | Non-critical data, high frequency |
| 1 | At least once (acknowledged delivery) | Important data, default choice |
| 2 | Exactly once (guaranteed delivery) | Critical data, alerts |

---

## Using the System

### 1. Start PetroFlow Application

```bash
streamlit run app.py
```

### 2. Navigate to IoT Telemetry Tab

Click on the **"IoT Telemetry"** tab in the application.

### 3. Connect to MQTT Broker

1. Expand **"MQTT Broker Configuration"**
2. Enter broker details:
   - **Broker Host**: `localhost` (or your broker IP)
   - **Broker Port**: `1883`
   - **Username/Password**: (if required)
3. Click **"Connect"**
4. Wait for connection confirmation

### 4. Manage Subscriptions

**View Active Subscriptions:**
- See list of currently subscribed topics

**Add New Subscription:**
1. Expand **"Add New Subscription"**
2. Enter MQTT topic (use wildcards if needed)
3. Select QoS level
4. Click **"Subscribe"**

**Remove Subscription:**
- Click **"Unsubscribe"** next to any active subscription

### 5. Monitor Real-time Data

- **Equipment Cards**: View latest sensor readings per equipment
- **Message Log**: See last 50 received messages
- **Statistics**: Monitor message counts and errors

---

## Simulator Usage

The `mqtt_simulator.py` script generates realistic sensor data for testing.

### Basic Usage

```bash
# Run with defaults (localhost:1883, PUMP-001)
python mqtt_simulator.py

# Specify broker and equipment
python mqtt_simulator.py --broker mqtt.example.com --equipment PUMP-002

# Run for 60 seconds with 1 second interval
python mqtt_simulator.py --duration 60 --interval 1

# Specify facility
python mqtt_simulator.py --facility REFINERY-B --equipment COMPRESSOR-001
```

### Command-Line Options

```
--broker HOST       MQTT broker hostname (default: localhost)
--port PORT         MQTT broker port (default: 1883)
--facility ID       Facility identifier (default: REFINERY-A)
--equipment ID      Equipment identifier (default: PUMP-001)
--interval SECONDS  Seconds between readings (default: 2.0)
--duration SECONDS  Total duration in seconds (default: infinite)
```

### Simulated Sensors

The simulator generates data for:

| Sensor | Baseline | Range | Unit | Notes |
|--------|----------|-------|------|-------|
| Temperature | 85°C | 70-100°C | celsius | Slow drift |
| Pressure | 30 Bar | 20-40 Bar | bar | Medium fluctuation |
| Vibration | 2.5 mm/s | 0.5-10 mm/s | mm/s | Occasional spikes |
| RPM | 2500 | 1000-3000 | rpm | Stable with noise |
| Flow Rate | 100 m³/h | 50-150 m³/h | m3/h | Gradual changes |
| Power | 75 kW | 50-100 kW | kw | Correlated with load |

### Simulating Multiple Equipment

Run multiple simulators in separate terminals:

```bash
# Terminal 1
python mqtt_simulator.py --equipment PUMP-001

# Terminal 2
python mqtt_simulator.py --equipment PUMP-002

# Terminal 3
python mqtt_simulator.py --equipment COMPRESSOR-001
```

### Anomaly Simulation

The simulator automatically generates anomalies:
- **High Vibration**: 5% chance every 10 iterations
- **Sensor Spikes**: Random spikes in vibration data
- **Alerts**: Publishes alert messages when thresholds exceeded

---

## Integration with Prediction Engine

The telemetry system automatically feeds data to the prediction engine when enabled in configuration.

### Data Flow

```
MQTT Message → Validation → Unit Conversion → Database Storage
                                            ↓
                                    Prediction Engine
                                            ↓
                                    Failure Prediction
                                            ↓
                                    UI Dashboard Update
```

### Accessing Telemetry Data in Code

```python
from modules.iot_telemetry import get_telemetry_client
from modules.database import get_session, SensorTelemetry

# Get telemetry client
client = get_telemetry_client()

# Check connection status
if client.is_connected():
    print("Connected to MQTT broker")

# Get statistics
stats = client.get_statistics()
print(f"Messages received: {stats['messages_received']}")

# Query telemetry data from database
with get_session() as session:
    recent_data = session.query(SensorTelemetry)\
        .filter(SensorTelemetry.equipment_id == 'PUMP-001')\
        .order_by(SensorTelemetry.timestamp.desc())\
        .limit(100)\
        .all()
```

---

## Security Best Practices

### 1. Use TLS/SSL Encryption

```json
{
  "broker": {
    "host": "mqtt.example.com",
    "port": 8883,
    "use_tls": true,
    "tls_ca_cert": "/path/to/ca.crt"
  }
}
```

### 2. Enable Authentication

```json
{
  "authentication": {
    "username": "petroflow_client",
    "password": "secure_password_here"
  }
}
```

**Never commit credentials to version control!**

### 3. Use Environment Variables

```python
import os

broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
username = os.getenv('MQTT_USERNAME')
password = os.getenv('MQTT_PASSWORD')
```

### 4. Implement Access Control

Configure broker ACLs (Access Control Lists):

```
# mosquitto.conf
user petroflow_client
topic read petroflow/#
topic write petroflow/+/system/commands
```

### 5. Network Security

- Use VPN for remote connections
- Firewall rules to restrict broker access
- Separate network for IoT devices

### 6. Data Validation

Always validate incoming messages:
- Check message format
- Validate sensor ranges
- Sanitize data before database storage

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to MQTT broker

**Solutions**:
1. Verify broker is running:
   ```bash
   # Check if mosquitto is running
   ps aux | grep mosquitto  # Linux/Mac
   tasklist | findstr mosquitto  # Windows
   ```

2. Check firewall:
   ```bash
   # Allow port 1883
   sudo ufw allow 1883  # Linux
   ```

3. Test with mosquitto_sub:
   ```bash
   mosquitto_sub -h localhost -t test/topic -v
   ```

4. Check broker logs:
   ```bash
   # Linux
   sudo journalctl -u mosquitto -f
   
   # Or check log file
   tail -f /var/log/mosquitto/mosquitto.log
   ```

### No Messages Received

**Problem**: Connected but not receiving messages

**Solutions**:
1. Verify subscriptions are active
2. Check topic patterns match published topics
3. Ensure simulator is running and publishing
4. Check QoS levels match

### High Message Drop Rate

**Problem**: Messages being dropped

**Solutions**:
1. Increase buffer size in `mqtt_config.json`:
   ```json
   "buffer_size": 5000
   ```

2. Enable batch processing:
   ```json
   "batch_processing": true,
   "batch_size": 50
   ```

3. Check system resources (CPU, memory)

### Database Errors

**Problem**: Error storing telemetry data

**Solutions**:
1. Check database connection
2. Verify SensorTelemetry table exists:
   ```python
   from modules.database import init_database
   init_database()
   ```

3. Check disk space
4. Review database logs

### Performance Issues

**Problem**: Application slow with telemetry enabled

**Solutions**:
1. Disable real-time UI updates:
   ```json
   "update_ui_realtime": false
   ```

2. Reduce message frequency in simulator
3. Enable batch processing
4. Use database indexing

---

## API Reference

### MQTTTelemetryClient Class

#### Methods

**`connect(broker_host, port, username, password, use_tls)`**
- Connect to MQTT broker
- Returns: `bool` (success/failure)

**`disconnect()`**
- Disconnect from broker

**`subscribe(topic, qos, callback)`**
- Subscribe to MQTT topic
- Returns: `bool`

**`unsubscribe(topic)`**
- Unsubscribe from topic
- Returns: `bool`

**`publish(topic, payload, qos, retain)`**
- Publish message to topic
- Returns: `bool`

**`publish_sensor_data(equipment_id, sensor_type, value, unit, facility_id, area)`**
- Publish sensor data with standard format
- Returns: `bool`

**`publish_alert(equipment_id, alert_type, severity, message, facility_id)`**
- Publish equipment alert
- Returns: `bool`

**`is_connected()`**
- Check connection status
- Returns: `bool`

**`get_connection_status()`**
- Get detailed connection information
- Returns: `dict`

**`get_statistics()`**
- Get telemetry statistics
- Returns: `dict`

**`get_active_subscriptions()`**
- Get list of active subscriptions
- Returns: `list[str]`

### Database Models

**SensorTelemetry Table**

```python
class SensorTelemetry(Base):
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    equipment_id = Column(String(50), nullable=False, index=True)
    sensor_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    quality = Column(String(20), default='good')
    facility_id = Column(String(50))
    area = Column(String(50))
    raw_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Additional Resources

### MQTT Resources

- **MQTT.org**: https://mqtt.org/
- **Mosquitto Documentation**: https://mosquitto.org/documentation/
- **HiveMQ MQTT Essentials**: https://www.hivemq.com/mqtt-essentials/
- **Paho MQTT Python**: https://www.eclipse.org/paho/index.php?page=clients/python/index.php

### Industrial IoT Standards

- **ISA-95**: Enterprise-Control System Integration
- **OPC UA**: Open Platform Communications Unified Architecture
- **MQTT Sparkplug**: Industrial IoT specification

### PetroFlow Documentation

- **Caching Strategy**: `CACHING_STRATEGY.md`
- **Audit Logging**: `AUDIT_LOGGING_GUIDE.md`
- **3D Viewer**: `3D_VIEWER_DOCUMENTATION.md`

---

## Support

For issues or questions:

1. Check this documentation
2. Review troubleshooting section
3. Check application logs in `logs/` directory
4. Review audit logs for telemetry events

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-05  
**Author**: Jhon Villegas  
**PetroFlow Phase 3**: IoT MQTT Telemetry Integration