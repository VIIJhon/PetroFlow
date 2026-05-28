"""
Phase 5: Comprehensive API Endpoint Tests
Tests for refactored endpoints using modular services
Author: Jhon Villegas
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.equipment import Equipment, EquipmentType as DBEquipmentType
from app.api.deps import reset_service_instances
from app.core.security import get_password_hash, create_access_token


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_phase5.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Reset services for clean state
    reset_service_instances()
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role=UserRole.ENGINEER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers."""
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_equipment(db_session, test_user):
    """Create test equipment."""
    equipment = Equipment(
        tag="PUMP-001",
        name="Test Centrifugal Pump",
        equipment_type=DBEquipmentType.PUMP,
        location="Test Plant",
        owner_id=test_user.id,
        specifications={
            "rated_flow_m3_h": 100.0,
            "rated_head_meters": 50.0,
            "rated_power_kw": 45.0,
            "rated_speed_rpm": 3600.0
        },
        is_active=True
    )
    db_session.add(equipment)
    db_session.commit()
    db_session.refresh(equipment)
    return equipment


# ============================================================================
# Simulation Endpoint Tests
# ============================================================================

class TestSimulationEndpoints:
    """Test refactored simulation endpoints."""
    
    def test_steady_state_simulation(self, client, auth_headers, test_equipment):
        """Test steady-state simulation endpoint."""
        request_data = {
            "equipment_id": test_equipment.id,
            "operating_conditions": {
                "flow_rate": 100.0,
                "head": 50.0,
                "power": 45.0,
                "speed": 3600.0
            },
            "unit_system": "SI",
            "enable_optimization": True,
            "enable_safety_validation": True
        }
        
        response = client.post(
            "/api/v2/simulation/steady-state",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data
        assert "run_id" in data
        assert "status" in data
        assert "duration_ms" in data
        assert "results" in data
    
    def test_transient_simulation(self, client, auth_headers, test_equipment):
        """Test transient simulation endpoint."""
        request_data = {
            "equipment_id": test_equipment.id,
            "initial_conditions": {
                "speed": 0.0,
                "flow_rate": 0.0
            },
            "time_horizon": 10.0,
            "time_step": 0.1,
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/simulation/transient",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data
        assert "time_series" in data
    
    def test_what_if_scenario(self, client, auth_headers, test_equipment):
        """Test what-if scenario analysis."""
        request_data = {
            "equipment_id": test_equipment.id,
            "baseline_conditions": {
                "speed": 3600.0,
                "flow_rate": 100.0
            },
            "scenario_changes": {
                "speed": 3800.0,
                "flow_rate": 105.0
            },
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/simulation/what-if",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "baseline" in data
        assert "scenario" in data
        assert "comparison" in data
    
    def test_optimization_simulation(self, client, auth_headers, test_equipment):
        """Test optimization simulation."""
        request_data = {
            "equipment_id": test_equipment.id,
            "current_conditions": {
                "speed": 3600.0,
                "flow_rate": 100.0,
                "power": 45.0
            },
            "optimization_target": "efficiency",
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/simulation/optimize",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "optimized_parameters" in data
        assert "efficiency_improvement" in data


# ============================================================================
# Equipment Endpoint Tests
# ============================================================================

class TestEquipmentEndpoints:
    """Test refactored equipment endpoints."""
    
    def test_validate_operating_point(self, client, auth_headers, test_equipment):
        """Test operating point validation."""
        request_data = {
            "equipment_id": test_equipment.id,
            "operating_parameters": {
                "flow_rate": 100.0,
                "head": 50.0,
                "power": 45.0,
                "speed": 3600.0
            },
            "units": {
                "flow_rate": "m3/h",
                "head": "m",
                "power": "kW",
                "speed": "rpm"
            },
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/equipment/validate",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equipment_id" in data
        assert "overall_status" in data
        assert "validations" in data
        assert "safety_margins" in data
    
    def test_get_safety_status(self, client, auth_headers, test_equipment):
        """Test safety status retrieval."""
        response = client.get(
            f"/api/v2/equipment/{test_equipment.id}/safety-status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equipment_tag" in data
        assert "overall_status" in data
        assert "alarms" in data
        assert "warnings" in data
    
    def test_optimize_equipment(self, client, auth_headers, test_equipment):
        """Test equipment optimization."""
        request_data = {
            "equipment_id": test_equipment.id,
            "current_parameters": {
                "speed": 3600.0,
                "flow_rate": 100.0,
                "power": 45.0
            },
            "units": {
                "speed": "rpm",
                "flow_rate": "m3/h",
                "power": "kW"
            },
            "optimization_target": "efficiency",
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/equipment/optimize",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "optimized_parameters" in data
        assert "efficiency_improvement" in data
        assert "energy_savings" in data
    
    def test_get_safety_envelope(self, client, auth_headers, test_equipment):
        """Test safety envelope retrieval."""
        response = client.get(
            f"/api/v2/equipment/{test_equipment.id}/envelope",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equipment_type" in data
        assert "standards" in data


# ============================================================================
# IoT/Telemetry Endpoint Tests
# ============================================================================

class TestIoTEndpoints:
    """Test refactored IoT/telemetry endpoints."""
    
    def test_process_telemetry_point(self, client, auth_headers, test_equipment):
        """Test single telemetry point processing."""
        request_data = {
            "equipment_id": test_equipment.id,
            "parameters": {
                "temperature": 65.0,
                "pressure": 150000.0,
                "flow_rate": 0.028,
                "vibration": 2.5,
                "speed": 3600.0,
                "power": 45.0
            },
            "units": {
                "temperature": "C",
                "pressure": "Pa",
                "flow_rate": "m3/s",
                "vibration": "mm/s",
                "speed": "rpm",
                "power": "kW"
            },
            "quality": 1.0,
            "source": "test"
        }
        
        response = client.post(
            "/api/v2/iot/telemetry/process",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "telemetry_id" in data
        assert "status" in data
        assert "validation_status" in data
        assert "processing_time_ms" in data
    
    def test_batch_telemetry_processing(self, client, auth_headers, test_equipment):
        """Test batch telemetry processing."""
        request_data = {
            "equipment_id": test_equipment.id,
            "data_points": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "parameters": {"temperature": 65.0, "pressure": 150000.0},
                    "units": {"temperature": "C", "pressure": "Pa"},
                    "quality": 1.0
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "parameters": {"temperature": 66.0, "pressure": 151000.0},
                    "units": {"temperature": "C", "pressure": "Pa"},
                    "quality": 1.0
                }
            ],
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/iot/telemetry/batch",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_points" in data
        assert "processed" in data
        assert "throughput_points_per_sec" in data
    
    def test_get_anomalies(self, client, auth_headers, test_equipment):
        """Test anomaly retrieval."""
        response = client.get(
            f"/api/v2/iot/telemetry/anomalies?equipment_id={test_equipment.id}&hours=24",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equipment_tag" in data
        assert "anomalies" in data
        assert "time_range" in data
    
    def test_get_telemetry_statistics(self, client, auth_headers, test_equipment):
        """Test telemetry statistics."""
        response = client.get(
            f"/api/v2/iot/telemetry/stats?equipment_id={test_equipment.id}&parameter=temperature&hours=24",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equipment_id" in data
        assert "parameter" in data


# ============================================================================
# Dependency Injection Tests
# ============================================================================

class TestDependencyInjection:
    """Test dependency injection functionality."""
    
    def test_service_singletons(self):
        """Test that services are singletons."""
        from app.api.deps import (
            get_safety_validator,
            get_optimizer,
            get_telemetry_processor
        )
        
        # Get instances twice
        validator1 = get_safety_validator()
        validator2 = get_safety_validator()
        
        optimizer1 = get_optimizer()
        optimizer2 = get_optimizer()
        
        processor1 = get_telemetry_processor()
        processor2 = get_telemetry_processor()
        
        # Should be same instances
        assert validator1 is validator2
        assert optimizer1 is optimizer2
        assert processor1 is processor2
    
    def test_service_reset(self):
        """Test service instance reset."""
        from app.api.deps import (
            get_safety_validator,
            reset_service_instances
        )
        
        # Get instance
        validator1 = get_safety_validator()
        
        # Reset
        reset_service_instances()
        
        # Get new instance
        validator2 = get_safety_validator()
        
        # Should be different instances
        assert validator1 is not validator2


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in endpoints."""
    
    def test_invalid_equipment_id(self, client, auth_headers):
        """Test handling of invalid equipment ID."""
        request_data = {
            "equipment_id": 99999,
            "operating_conditions": {"speed": 3600.0},
            "unit_system": "SI"
        }
        
        response = client.post(
            "/api/v2/simulation/steady-state",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_missing_authentication(self, client, test_equipment):
        """Test handling of missing authentication."""
        request_data = {
            "equipment_id": test_equipment.id,
            "operating_conditions": {"speed": 3600.0}
        }
        
        response = client.post(
            "/api/v2/simulation/steady-state",
            json=request_data
        )
        
        assert response.status_code == 401
    
    def test_invalid_request_data(self, client, auth_headers, test_equipment):
        """Test handling of invalid request data."""
        request_data = {
            "equipment_id": test_equipment.id,
            # Missing required fields
        }
        
        response = client.post(
            "/api/v2/simulation/steady-state",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])