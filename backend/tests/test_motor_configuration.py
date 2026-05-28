"""
Tests for Motor Configuration API endpoints.
Validates CRUD operations and the configurable optimizer.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import MagicMock

from app.main import app
from app.database import Base, get_db
from app.api.deps import get_current_user
from app.models.motor_config import MotorConfiguration
from app.models.user import User
from app.services.motor_config_service import MotorConfigurationService
from app.services.configurable_optimizer import (
    ConfigurableEfficiencyOptimizer,
    ConfigurableSafetyEnvelopeCalculator,
)

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    """Mock current user for testing."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "testuser"
    return mock_user


Base.metadata.create_all(bind=engine)
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture(autouse=True, scope="function")
def setup_teardown():
    """Setup and teardown for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)


def test_create_motor_config():
    """Test creating a motor configuration."""
    config_data = {
        "equipment_type": "pump",
        "max_pressure_bar": 50.0,
        "min_pressure_bar": 0.5,
        "max_temp_c": 160.0,
        "min_temp_c": 5.0,
        "max_rpm": 4000.0,
        "min_rpm": 500.0,
        "max_flow_m3h": 1500.0,
        "min_flow_m3h": 25.0,
        "max_vibration_mms": 5.0,
        "rated_power_kw": 300.0,
        "power_affinity_exponent": 3.0,
        "throttle_loss_fraction": 0.15,
        "flow_tolerance_m3h": 5.0,
        "max_optimization_iterations": 1000,
        "description": "Test pump configuration",
    }
    
    response = client.post("/api/v1/motor-config/", json=config_data)
    assert response.status_code == 201
    data = response.json()
    assert data["equipment_type"] == "pump"
    assert data["max_pressure_bar"] == 50.0
    assert data["is_active"] is True


def test_get_motor_config():
    """Test retrieving a motor configuration."""
    # Create first
    db = TestingSessionLocal()
    config_data = {
        "equipment_type": "compressor",
        "max_pressure_bar": 250.0,
        "min_pressure_bar": 1.0,
        "max_temp_c": 210.0,
        "min_temp_c": 10.0,
        "max_rpm": 12500.0,
        "min_rpm": 2500.0,
        "max_flow_m3h": 25000.0,
        "min_flow_m3h": 400.0,
        "max_vibration_mms": 3.0,
        "rated_power_kw": 1800.0,
    }
    
    MotorConfigurationService.create_or_update(db, **config_data)
    db.commit()
    db.close()
    
    # Retrieve
    response = client.get("/api/v1/motor-config/compressor")
    assert response.status_code == 200
    data = response.json()
    assert data["equipment_type"] == "compressor"
    assert data["max_pressure_bar"] == 250.0


def test_list_motor_configs():
    """Test listing all motor configurations."""
    # Create multiple configs
    db = TestingSessionLocal()
    pump_config = {
        "equipment_type": "pump",
        "max_pressure_bar": 50.0,
        "min_pressure_bar": 0.5,
        "max_temp_c": 160.0,
        "min_temp_c": 5.0,
        "max_rpm": 4000.0,
        "min_rpm": 500.0,
        "max_flow_m3h": 1500.0,
        "min_flow_m3h": 25.0,
        "max_vibration_mms": 5.0,
        "rated_power_kw": 300.0,
    }
    
    compressor_config = {
        "equipment_type": "compressor",
        "max_pressure_bar": 250.0,
        "min_pressure_bar": 1.0,
        "max_temp_c": 210.0,
        "min_temp_c": 10.0,
        "max_rpm": 12500.0,
        "min_rpm": 2500.0,
        "max_flow_m3h": 25000.0,
        "min_flow_m3h": 400.0,
        "max_vibration_mms": 3.0,
        "rated_power_kw": 1800.0,
    }
    
    MotorConfigurationService.create_or_update(db, **pump_config)
    MotorConfigurationService.create_or_update(db, **compressor_config)
    db.commit()
    db.close()
    
    response = client.get("/api/v1/motor-config/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_update_motor_config():
    """Test updating a motor configuration."""
    # Create first
    db = TestingSessionLocal()
    pump_config = {
        "equipment_type": "pump",
        "max_pressure_bar": 50.0,
        "min_pressure_bar": 0.5,
        "max_temp_c": 160.0,
        "min_temp_c": 5.0,
        "max_rpm": 4000.0,
        "min_rpm": 500.0,
        "max_flow_m3h": 1500.0,
        "min_flow_m3h": 25.0,
        "max_vibration_mms": 5.0,
        "rated_power_kw": 300.0,
    }
    MotorConfigurationService.create_or_update(db, **pump_config)
    db.commit()
    db.close()
    
    # Update
    updated_data = pump_config.copy()
    updated_data["max_pressure_bar"] = 60.0
    updated_data["description"] = "Updated pump"
    
    response = client.put("/api/v1/motor-config/pump", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["max_pressure_bar"] == 60.0


def test_configurable_optimizer_uses_db_config():
    """Test that the configurable optimizer uses DB configuration."""
    # Create custom config
    db = TestingSessionLocal()
    custom_config = {
        "equipment_type": "pump",
        "max_pressure_bar": 60.0,
        "min_pressure_bar": 0.5,
        "max_temp_c": 180.0,
        "min_temp_c": 5.0,
        "max_rpm": 5000.0,
        "min_rpm": 500.0,
        "max_flow_m3h": 2000.0,
        "min_flow_m3h": 20.0,
        "max_vibration_mms": 5.0,
        "rated_power_kw": 400.0,
        "power_affinity_exponent": 3.0,
        "throttle_loss_fraction": 0.2,  # Higher throttling
        "max_optimization_iterations": 1500,
    }
    MotorConfigurationService.create_or_update(db, **custom_config)
    db.commit()
    
    # Optimize using DB config
    result = ConfigurableEfficiencyOptimizer.optimize_operation(
        equipment_type="pump",
        current_rpm=3000.0,
        current_valve=75.0,
        target_flow=500.0,
        current_pressure=30.0,
        current_temp=80.0,
        db=db,
    )
    
    db.close()
    
    assert result["success"]
    assert "optimal_rpm" in result
    assert "optimal_valve" in result
    assert result["configuration_source"] == "database"


def test_safety_envelope_check_with_db_config():
    """Test safety envelope check using DB configuration."""
    # Create custom envelope
    db = TestingSessionLocal()
    custom_envelope = {
        "equipment_type": "pump",
        "max_pressure_bar": 45.0,
        "min_pressure_bar": 1.0,
        "max_temp_c": 140.0,
        "min_temp_c": 15.0,
        "max_rpm": 3600.0,
        "min_rpm": 700.0,
        "max_flow_m3h": 1200.0,
        "min_flow_m3h": 40.0,
        "max_vibration_mms": 4.5,
        "rated_power_kw": 250.0,
    }
    MotorConfigurationService.create_or_update(db, **custom_envelope)
    db.commit()
    
    # Check within limits
    result = ConfigurableSafetyEnvelopeCalculator.check_operating_point(
        equipment_type="pump",
        pressure_bar=35.0,
        temp_c=90.0,
        rpm=2000.0,
        vibration_mms=2.5,
        db=db,
    )
    
    db.close()
    
    assert result["is_safe"] is True
    assert len(result["violations"]) == 0
    assert result["configuration_source"] == "database"


def test_safety_envelope_check_violation():
    """Test safety envelope detection of violations."""
    # Create config
    db = TestingSessionLocal()
    custom_envelope = {
        "equipment_type": "pump",
        "max_pressure_bar": 45.0,
        "min_pressure_bar": 1.0,
        "max_temp_c": 140.0,
        "min_temp_c": 15.0,
        "max_rpm": 3600.0,
        "min_rpm": 700.0,
        "max_flow_m3h": 1200.0,
        "min_flow_m3h": 40.0,
        "max_vibration_mms": 4.5,
        "rated_power_kw": 250.0,
    }
    MotorConfigurationService.create_or_update(db, **custom_envelope)
    db.commit()
    
    # Check outside limits (pressure too high)
    result = ConfigurableSafetyEnvelopeCalculator.check_operating_point(
        equipment_type="pump",
        pressure_bar=50.0,  # Exceeds max of 45.0
        temp_c=90.0,
        rpm=2000.0,
        vibration_mms=2.5,
        db=db,
    )
    
    db.close()
    
    assert result["is_safe"] is False
    assert len(result["violations"]) > 0
    assert any("Pressure" in v for v in result["violations"])
