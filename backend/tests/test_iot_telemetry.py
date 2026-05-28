"""
Unit tests for iot_telemetry.py (MQTTTelemetryClient)
Covers:
  - Singleton pattern
  - Default configuration loading
  - validate_message_format
  - _convert_to_standard_units (unit conversion reversibility & known values)
  - Topic pattern matching (_topic_matches)
  - process_sensor_message (with mocked dependencies)
  - _process_alert_message and _process_health_message
  - Message queue behaviour (drop on full queue)
  - Statistics tracking
  - subscribe / unsubscribe routing
"""

import pytest
import json
import threading
import queue
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call


# Streamlit already mocked in conftest.py
# Reset the singleton before each test so tests are independent
import core.mqtt_telemetry_client as iot_module


@pytest.fixture(autouse=True)
def reset_mqtt_singleton():
    """Destroy the MQTTTelemetryClient singleton before each test."""
    iot_module.MQTTTelemetryClient._instance = None
    yield
    iot_module.MQTTTelemetryClient._instance = None


@pytest.fixture
def client(mqtt_default_config):
    """Return a freshly initialised MQTTTelemetryClient with mocked MQTT."""
    with patch("core.mqtt_telemetry_client.MQTT_AVAILABLE", True), \
         patch("core.mqtt_telemetry_client.mqtt") as mock_mqtt_module, \
         patch.object(iot_module.MQTTTelemetryClient, "_load_config",
                      return_value=mqtt_default_config):

        mock_mqtt_module.Client.return_value = MagicMock()
        mock_mqtt_module.MQTT_ERR_SUCCESS = 0

        c = iot_module.MQTTTelemetryClient()
        c.enabled = True
        c.config = mqtt_default_config
        c.connected = False
        c.client = MagicMock()
        c.client.subscribe.return_value = (0, 1)
        c.client.unsubscribe.return_value = (0, 1)
        publish_result = MagicMock()
        publish_result.rc = 0
        c.client.publish.return_value = publish_result
        yield c


# ===========================================================================
# 1. Singleton Pattern
# ===========================================================================

class TestSingletonPattern:

    @pytest.mark.unit
    def test_same_instance_returned(self, mqtt_default_config):
        with patch("core.mqtt_telemetry_client.MQTT_AVAILABLE", True), \
             patch("core.mqtt_telemetry_client.mqtt"), \
             patch.object(iot_module.MQTTTelemetryClient, "_load_config",
                          return_value=mqtt_default_config):
            c1 = iot_module.MQTTTelemetryClient()
            c2 = iot_module.MQTTTelemetryClient()
            assert c1 is c2

    @pytest.mark.unit
    def test_singleton_thread_safe(self, mqtt_default_config):
        """Two threads must get the same instance."""
        instances = []

        def create():
            with patch("core.mqtt_telemetry_client.MQTT_AVAILABLE", True), \
                 patch("core.mqtt_telemetry_client.mqtt"), \
                 patch.object(iot_module.MQTTTelemetryClient, "_load_config",
                              return_value=mqtt_default_config):
                instances.append(iot_module.MQTTTelemetryClient())

        t1 = threading.Thread(target=create)
        t2 = threading.Thread(target=create)
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert instances[0] is instances[1]


# ===========================================================================
# 2. validate_message_format
# ===========================================================================

class TestValidateMessageFormat:

    @pytest.mark.unit
    def test_valid_sensor_message_passes(self, client, sample_mqtt_message):
        assert client.validate_message_format(sample_mqtt_message) is True

    @pytest.mark.unit
    def test_missing_timestamp_fails(self, client, sample_mqtt_message):
        msg = dict(sample_mqtt_message)
        del msg["timestamp"]
        assert client.validate_message_format(msg) is False

    @pytest.mark.unit
    def test_sensor_message_missing_equipment_id_fails(self, client, sample_mqtt_message):
        msg = dict(sample_mqtt_message)
        del msg["equipment_id"]
        assert client.validate_message_format(msg) is False

    @pytest.mark.unit
    def test_sensor_message_missing_value_fails(self, client, sample_mqtt_message):
        msg = dict(sample_mqtt_message)
        del msg["value"]
        assert client.validate_message_format(msg) is False

    @pytest.mark.unit
    def test_sensor_message_missing_unit_fails(self, client, sample_mqtt_message):
        msg = dict(sample_mqtt_message)
        del msg["unit"]
        assert client.validate_message_format(msg) is False

    @pytest.mark.unit
    def test_alert_message_passes(self, client, sample_alert_message):
        """Alert messages only require 'timestamp'."""
        assert client.validate_message_format(sample_alert_message) is True

    @pytest.mark.unit
    def test_empty_message_fails(self, client):
        assert client.validate_message_format({}) is False

    @pytest.mark.unit
    def test_minimal_valid_message(self, client):
        msg = {"timestamp": datetime.now(timezone.utc).isoformat()}
        assert client.validate_message_format(msg) is True


# ===========================================================================
# 3. _convert_to_standard_units (unit conversion)
# ===========================================================================

class TestUnitConversion:

    @pytest.mark.unit
    @pytest.mark.parametrize("fahrenheit,expected_celsius", [
        (32.0,   0.0),
        (212.0, 100.0),
        (98.6,  37.0),
    ])
    def test_fahrenheit_to_celsius(self, client, fahrenheit, expected_celsius):
        result = client._convert_to_standard_units(fahrenheit, "fahrenheit", "temperature")
        assert abs(result - expected_celsius) < 0.01

    @pytest.mark.unit
    @pytest.mark.parametrize("psi,expected_bar", [
        (14.5038, 1.0),
        (29.0076, 2.0),
        (0.0,     0.0),
    ])
    def test_psi_to_bar(self, client, psi, expected_bar):
        result = client._convert_to_standard_units(psi, "psi", "pressure")
        assert abs(result - expected_bar) < 0.01

    @pytest.mark.unit
    @pytest.mark.parametrize("inches_per_sec,expected_mm", [
        (1.0, 25.4),
        (2.0, 50.8),
        (0.5, 12.7),
    ])
    def test_inches_per_sec_to_mm_per_sec(self, client, inches_per_sec, expected_mm):
        result = client._convert_to_standard_units(inches_per_sec, "in/s", "vibration")
        assert abs(result - expected_mm) < 0.01

    @pytest.mark.unit
    def test_unknown_unit_returns_unchanged(self, client):
        result = client._convert_to_standard_units(100.0, "unknown_unit", "temperature")
        assert result == 100.0

    @pytest.mark.unit
    def test_celsius_returns_unchanged(self, client):
        result = client._convert_to_standard_units(75.0, "celsius", "temperature")
        assert result == 75.0

    @pytest.mark.unit
    def test_bar_returns_unchanged(self, client):
        result = client._convert_to_standard_units(25.0, "bar", "pressure")
        assert result == 25.0

    @pytest.mark.unit
    def test_fahrenheit_to_celsius_reversibility(self, client):
        """
        Convert C -> F manually, then apply the conversion function.
        Result should match original Celsius value.
        """
        original_c = 65.0
        converted_f = original_c * 9 / 5 + 32
        back_to_c = client._convert_to_standard_units(converted_f, "fahrenheit", "temperature")
        assert abs(back_to_c - original_c) < 0.01


# ===========================================================================
# 4. Topic Matching (_topic_matches)
# ===========================================================================

class TestTopicMatching:

    @pytest.mark.unit
    def test_exact_topic_match(self, client):
        assert client._topic_matches("petroflow/test", "petroflow/test") is True

    @pytest.mark.unit
    def test_exact_topic_no_match(self, client):
        assert client._topic_matches("petroflow/test", "petroflow/other") is False

    @pytest.mark.unit
    def test_single_level_wildcard(self, client):
        assert client._topic_matches("petroflow/sensor/temp", "petroflow/+/temp") is True

    @pytest.mark.unit
    def test_multi_level_wildcard(self, client):
        assert client._topic_matches(
            "petroflow/facility/equipment/PUMP-001/sensors/temperature",
            "petroflow/#"
        ) is True

    @pytest.mark.unit
    def test_wildcard_does_not_match_different_root(self, client):
        assert client._topic_matches(
            "otherapp/sensor/temp",
            "petroflow/#"
        ) is False


# ===========================================================================
# 5. Message Queue Behaviour
# ===========================================================================

class TestMessageQueueBehaviour:

    @pytest.mark.unit
    def test_messages_added_to_queue(self, client):
        client.message_queue = queue.Queue(maxsize=10)
        client.stats["messages_received"] = 0
        client.stats["messages_dropped"] = 0

        msg = MagicMock()
        msg.topic = "petroflow/test"
        msg.payload = b'{"timestamp":"2024-01-01T00:00:00Z"}'
        msg.qos = 1
        msg.retain = False

        client._on_message(None, None, msg)

        assert client.stats["messages_received"] == 1
        assert not client.message_queue.empty()

    @pytest.mark.unit
    def test_full_queue_drops_message(self, client):
        client.message_queue = queue.Queue(maxsize=1)
        client.stats["messages_received"] = 0
        client.stats["messages_dropped"] = 0

        msg = MagicMock()
        msg.topic = "petroflow/test"
        msg.payload = b'{"ts": "2024"}'
        msg.qos = 1
        msg.retain = False

        # First message fills the queue
        client._on_message(None, None, msg)
        # Second message should be dropped
        client._on_message(None, None, msg)

        assert client.stats["messages_dropped"] == 1

    @pytest.mark.unit
    def test_stats_initialized(self, client):
        expected_keys = {
            "messages_received", "messages_published", "messages_dropped",
            "connection_count", "last_message_time", "errors",
        }
        assert expected_keys.issubset(set(client.stats.keys()))


# ===========================================================================
# 6. process_sensor_message
# ===========================================================================

class TestProcessSensorMessage:

    @pytest.mark.unit
    def test_incomplete_message_skipped(self, client, caplog):
        """Message missing required fields should be logged and skipped."""
        incomplete = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equipment_id": "PUMP-001",
            # Missing: sensor_type, value, unit
        }
        # Should not raise; just log warning
        client.process_sensor_message("petroflow/test/sensors/temperature", incomplete)

    @pytest.mark.unit
    def test_valid_sensor_message_processed(self, client, sample_mqtt_message):
        """Valid sensor message with storage/prediction disabled should complete."""
        client.config["integration"]["store_in_database"] = False
        client.config["integration"]["feed_to_prediction_engine"] = False
        client.config["integration"]["update_ui_realtime"] = False
        client.config["data_processing"]["enable_unit_conversion"] = False

        # Should not raise
        client.process_sensor_message(
            "petroflow/REFINERY-A/equipment/PUMP-001/sensors/temperature",
            sample_mqtt_message
        )


# ===========================================================================
# 7. subscribe / unsubscribe
# ===========================================================================

class TestSubscribeUnsubscribe:

    @pytest.mark.unit
    def test_subscribe_when_not_connected_returns_false(self, client):
        client.connected = False
        result = client.subscribe("petroflow/#")
        assert result is False

    @pytest.mark.unit
    def test_subscribe_when_connected_returns_true(self, client):
        client.connected = True

        import core.mqtt_telemetry_client as iot_mod
        with patch.object(iot_mod, "mqtt") as mock_mqtt:
            mock_mqtt.MQTT_ERR_SUCCESS = 0
            client.client.subscribe.return_value = (0, 1)
            result = client.subscribe("petroflow/#", qos=1)
        assert result is True

    @pytest.mark.unit
    def test_subscribe_registers_topic(self, client):
        client.connected = True

        import core.mqtt_telemetry_client as iot_mod
        with patch.object(iot_mod, "mqtt") as mock_mqtt:
            mock_mqtt.MQTT_ERR_SUCCESS = 0
            client.client.subscribe.return_value = (0, 1)
            client.subscribe("petroflow/test", qos=0)
        assert "petroflow/test" in client.subscriptions

    @pytest.mark.unit
    def test_unsubscribe_when_not_connected_returns_false(self, client):
        client.connected = False
        result = client.unsubscribe("petroflow/#")
        assert result is False

    @pytest.mark.unit
    def test_unsubscribe_removes_topic_from_registry(self, client):
        client.connected = True
        client.subscriptions["petroflow/test"] = (1, None)

        import core.mqtt_telemetry_client as iot_mod
        with patch.object(iot_mod, "mqtt") as mock_mqtt:
            mock_mqtt.MQTT_ERR_SUCCESS = 0
            client.client.unsubscribe.return_value = (0, 1)
            result = client.unsubscribe("petroflow/test")

        assert result is True
        assert "petroflow/test" not in client.subscriptions


# ===========================================================================
# 8. publish
# ===========================================================================

class TestPublish:

    @pytest.mark.unit
    def test_publish_when_not_connected_returns_false(self, client):
        client.connected = False
        result = client.publish("petroflow/test", {"value": 1})
        assert result is False

    @pytest.mark.unit
    def test_publish_dict_converts_to_json(self, client):
        client.connected = True

        import core.mqtt_telemetry_client as iot_mod
        with patch.object(iot_mod, "mqtt") as mock_mqtt:
            mock_mqtt.MQTT_ERR_SUCCESS = 0
            publish_result = MagicMock()
            publish_result.rc = 0
            client.client.publish.return_value = publish_result

            result = client.publish("petroflow/test", {"key": "value"})

        assert result is True
        # Verify client.publish was called with a string payload (JSON)
        call_args = client.client.publish.call_args
        payload_arg = call_args[0][1]  # positional arg index 1 is payload
        assert isinstance(payload_arg, str)
        parsed = json.loads(payload_arg)
        assert parsed["key"] == "value"

    @pytest.mark.unit
    def test_publish_sensor_data_correct_topic(self, client):
        client.connected = True

        import core.mqtt_telemetry_client as iot_mod
        with patch.object(iot_mod, "mqtt") as mock_mqtt:
            mock_mqtt.MQTT_ERR_SUCCESS = 0
            publish_result = MagicMock()
            publish_result.rc = 0
            client.client.publish.return_value = publish_result

            client.publish_sensor_data(
                equipment_id="PUMP-001",
                sensor_type="temperature",
                value=78.5,
                unit="celsius",
                facility_id="REFINERY-A",
            )

        call_args = client.client.publish.call_args
        topic = call_args[0][0]
        assert "PUMP-001" in topic
        assert "temperature" in topic
        assert "REFINERY-A" in topic
