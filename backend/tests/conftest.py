import sys
import os
import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Path setup - ensure project root is importable before any module imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Pre-mock ALL optional / heavy dependencies before any package import
# This prevents ImportError chains when modules/__init__.py eagerly imports
# viewer_3d, cmms, and config which pull in plotly, trimesh, lifelines, etc.
# ---------------------------------------------------------------------------

def _make_mock(name):
    m = MagicMock()
    m.__name__ = name
    return m

# 3D viewer dependencies
for _mod in [
    "trimesh", "trimesh.load", "pygltflib", "stl", "stl.mesh",
    "dataclasses_json", "marshmallow",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = _make_mock(_mod)

# Plotly (used in config.py and cmms.py)
if "plotly" not in sys.modules:
    sys.modules["plotly"] = _make_mock("plotly")
    sys.modules["plotly.graph_objects"] = _make_mock("plotly.graph_objects")
    sys.modules["plotly.express"] = _make_mock("plotly.express")
    sys.modules["plotly.subplots"] = _make_mock("plotly.subplots")

# Matplotlib (used indirectly)
if "matplotlib" not in sys.modules:
    sys.modules["matplotlib"] = _make_mock("matplotlib")
    sys.modules["matplotlib.pyplot"] = _make_mock("matplotlib.pyplot")

# Paho-mqtt
if "paho" not in sys.modules:
    sys.modules["paho"] = _make_mock("paho")
    sys.modules["paho.mqtt"] = _make_mock("paho.mqtt")
    sys.modules["paho.mqtt.client"] = _make_mock("paho.mqtt.client")


# ---------------------------------------------------------------------------
# Streamlit mock - must be installed before any module-level import of 'st'
# ---------------------------------------------------------------------------

def _identity_decorator(*args, **kwargs):
    """Return function unchanged; acts as a no-op decorator."""
    if len(args) == 1 and callable(args[0]):
        return args[0]
    def decorator(func):
        return func
    return decorator


_st_mock = MagicMock()
_st_mock.cache_data = _identity_decorator
_st_mock.cache_resource = _identity_decorator
_st_mock.session_state = {}
_st_mock.secrets = {}

sys.modules["streamlit"] = _st_mock


# ---------------------------------------------------------------------------
# Fixtures: sample DataFrames
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def valid_sensor_df():
    """Realistic sensor DataFrame with all required columns (English names)."""
    np.random.seed(42)
    n = 50
    return pd.DataFrame({
        "equipment_id": ["PUMP-001"] * 25 + ["COMPRESSOR-002"] * 25,
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h"),
        "temperature": np.random.normal(75, 10, n).clip(50, 100),
        "pressure": np.random.normal(25, 5, n).clip(15, 40),
        "vibration": np.random.normal(2.5, 0.8, n).clip(0.5, 8),
        "rpm": np.random.normal(2500, 200, n).clip(2000, 3000),
        "operating_hours": np.linspace(10000, 15000, n),
    })


@pytest.fixture(scope="session")
def valid_sensor_df_spanish():
    """Sensor DataFrame using Spanish column aliases."""
    np.random.seed(7)
    n = 30
    return pd.DataFrame({
        "equipo_id": ["BOMBA-001"] * n,
        "fecha": pd.date_range("2024-06-01", periods=n, freq="h"),
        "temperatura": np.random.normal(70, 8, n).clip(45, 95),
        "presion": np.random.normal(22, 4, n).clip(12, 38),
        "vibracion": np.random.normal(2.0, 0.6, n).clip(0.3, 7),
        "rpm": np.random.normal(2400, 150, n).clip(1900, 2900),
        "horas": np.linspace(5000, 8000, n),
    })


@pytest.fixture(scope="session")
def corrupted_sensor_df():
    """DataFrame with missing values, type mismatches, and out-of-range data."""
    np.random.seed(0)
    n = 20
    df = pd.DataFrame({
        "equipment_id": ["PUMP-BAD"] * n,
        "timestamp": ["not-a-date"] * 5 + list(pd.date_range("2024-01-01", periods=n - 5, freq="h")),
        "temperature": [None, "INVALID", 999, -999] + list(np.random.normal(70, 5, n - 4)),
        "pressure": [None] * 4 + list(np.random.normal(25, 3, n - 4)),
        "vibration": list(np.random.normal(2, 0.5, n - 2)) + [None, None],
        "rpm": list(np.random.normal(2500, 100, n)),
        "operating_hours": list(np.linspace(1000, 5000, n)),
    })
    return df


@pytest.fixture(scope="session")
def missing_columns_df():
    """DataFrame lacking required columns to trigger validation failure."""
    return pd.DataFrame({
        "equipment_id": ["PUMP-001"] * 5,
        "temperature": [70, 72, 68, 75, 71],
        # Missing: timestamp, pressure, vibration, rpm, operating_hours
    })


@pytest.fixture(scope="session")
def ml_ready_df(valid_sensor_df):
    """Feature DataFrame ready for ML model input (5 numeric columns only)."""
    return valid_sensor_df[["temperature", "pressure", "vibration", "rpm", "operating_hours"]].copy()


@pytest.fixture(scope="session")
def survival_data_df():
    """Survival analysis DataFrame with time-to-failure and event_observed."""
    np.random.seed(42)
    n = 200
    return pd.DataFrame({
        "time_to_failure": np.random.weibull(1.5, n) * 10000,
        "event_observed": np.random.binomial(1, 0.7, n),
    })


@pytest.fixture(scope="session")
def failure_times_array(survival_data_df):
    """Array of positive failure times for Weibull fitting."""
    mask = (survival_data_df["event_observed"] == 1) & (survival_data_df["time_to_failure"] > 0)
    return survival_data_df.loc[mask, "time_to_failure"].values


# ---------------------------------------------------------------------------
# Fixtures: trained ML model
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def trained_model():
    """Pre-trained RandomForest model + scaler for reuse across tests."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from core.failure_prediction_engine import generate_synthetic_training_data

    data = generate_synthetic_training_data(300)
    feature_cols = ["temperature", "pressure", "vibration", "operating_hours", "rpm"]
    X = data[feature_cols].values
    y = data["failure_category"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=10, random_state=42, n_jobs=1)
    model.fit(X_scaled, y)

    return model, scaler


# ---------------------------------------------------------------------------
# Fixtures: in-memory SQLite database
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_engine():
    """SQLAlchemy engine backed by an in-memory SQLite database."""
    from sqlalchemy import create_engine
    from core.database import Base

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(in_memory_engine):
    """
    SQLAlchemy session bound to the in-memory engine.
    Each test gets a fresh, rolled-back session.
    """
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_personnel_data():
    """Minimal valid personnel record dictionary."""
    return {
        "nombre_completo": "Carlos Mendoza",
        "cedula": "V-12345678",
        "especialidad": "Mechanical Engineering",
        "nivel_certificacion": "Senior",
        "email": "c.mendoza@petroflow.com",
        "telefono": "+58-412-1234567",
        "fecha_ingreso": datetime(2020, 3, 15),
        "estado": "Active",
    }


@pytest.fixture
def sample_report_data():
    """Minimal valid intervention report dictionary."""
    return {
        "equipo_id": "PUMP-001",
        "equipo_nombre": "Main Crude Pump",
        "tipo_intervencion": "Corrective",
        "descripcion_falla": "Bearing overheating",
        "descripcion_trabajo": "Replaced bearing assembly",
        "tecnico_id": None,
        "fecha_inicio": datetime(2024, 1, 10, 8, 0),
        "fecha_fin": datetime(2024, 1, 10, 14, 0),
        "duracion_horas": 6.0,
        "costo_estimado": 1500.0,
        "repuestos_utilizados": "SKF Bearing 6205",
        "prioridad": "High",
        "estado_reporte": "Closed",
        "observaciones": "Root cause: lubrication failure",
    }


# ---------------------------------------------------------------------------
# Fixtures: MQTT mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mqtt_client():
    """Fully mocked paho-mqtt Client object."""
    client = MagicMock()
    client.connect.return_value = None
    client.disconnect.return_value = None
    client.loop_start.return_value = None
    client.loop_stop.return_value = None
    client.subscribe.return_value = (0, 1)   # MQTT_ERR_SUCCESS, mid=1
    client.unsubscribe.return_value = (0, 1)
    publish_result = MagicMock()
    publish_result.rc = 0  # MQTT_ERR_SUCCESS
    client.publish.return_value = publish_result
    return client


@pytest.fixture
def sample_mqtt_message():
    """Valid MQTT sensor message payload."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "equipment_id": "PUMP-001",
        "sensor_type": "temperature",
        "value": 78.5,
        "unit": "celsius",
        "quality": "good",
        "facility_id": "REFINERY-A",
        "area": "Processing",
    }


@pytest.fixture
def sample_alert_message():
    """Valid MQTT alert message payload."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "equipment_id": "COMPRESSOR-002",
        "alert_type": "high_vibration",
        "severity": "warning",
        "message": "Vibration exceeded threshold (8.2 mm/s)",
    }


# ---------------------------------------------------------------------------
# Fixtures: temporary directories
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_storage(tmp_path):
    """Temporary storage directory hierarchy."""
    for subdir in ("profile_photos", "maintenance_docs", "excel_uploads"):
        (tmp_path / subdir).mkdir()
    return tmp_path


@pytest.fixture
def tmp_logs(tmp_path):
    """Temporary logs directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


# ---------------------------------------------------------------------------
# Fixtures: config overrides
# ---------------------------------------------------------------------------

@pytest.fixture
def mqtt_default_config():
    """Default MQTT configuration dictionary (mirrors MQTTTelemetryClient defaults)."""
    return {
        "broker": {
            "host": "localhost",
            "port": 1883,
            "use_tls": False,
            "keepalive": 60,
            "clean_session": True,
        },
        "authentication": {"username": None, "password": None},
        "connection": {
            "auto_reconnect": True,
            "reconnect_delay_min": 1,
            "reconnect_delay_max": 60,
            "max_reconnect_attempts": 10,
        },
        "subscriptions": {"default_qos": 1, "topics": []},
        "data_processing": {
            "enable_validation": True,
            "enable_unit_conversion": True,
            "enable_anomaly_detection": False,
            "buffer_size": 100,
            "batch_processing": False,
            "batch_size": 10,
        },
        "integration": {
            "feed_to_prediction_engine": False,
            "store_in_database": False,
            "log_telemetry_events": False,
            "update_ui_realtime": False,
        },
    }
