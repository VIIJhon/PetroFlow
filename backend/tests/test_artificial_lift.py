"""
Unit and Integration Tests for Artificial Lift Engine in PetroFlow Enterprise
Verifies ESP sizing and Gas Lift optimization calculations and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token

from core.artificial_lift_engine import ArtificialLiftEngine

# -------------------------------------------------------------
# Test Database & Fixtures Setup (Self-Contained)
# -------------------------------------------------------------

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_artificial_lift.db"
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


# ==========================================
# 1. ARTIFICIAL LIFT ENGINE UNIT TESTS
# ==========================================

def test_esp_sizing_math():
    results = ArtificialLiftEngine.solve_esp_sizing(
        flow_rate_m3h=25.0,
        static_lift_m=800.0,
        tubing_length_m=1000.0,
        tubing_diameter_in=2.441,
        roughness_m=5e-5,
        wellhead_pressure_bar=15.0,
        fluid_density_kg_m3=880.0,
        fluid_viscosity_cp=10.0,
        head_per_stage_m=6.5,
        pump_efficiency_pct=65.0
    )
    
    assert "total_dynamic_head_m" in results
    assert results["total_dynamic_head_m"] > 800.0
    assert results["stages_required"] > 0
    assert results["hydraulic_power_kw"] > 0.0
    assert results["shaft_power_kw"] > 0.0
    assert results["motor_horsepower_hp"] > 0.0
    assert "status" in results


def test_gas_lift_optimization_math():
    results = ArtificialLiftEngine.solve_gas_lift_optimization(
        liquid_rate_m3d=120.0,
        gas_injection_rate_m3d=15000.0,
        well_depth_m=2500.0,
        tubing_diameter_in=2.441,
        fluid_density_kg_m3=880.0,
        gas_density_kg_m3=1.2,
        wellhead_pressure_bar=10.0,
        productivity_index_j=2.5,
        reservoir_pressure_bar=180.0
    )
    
    assert "gas_injection_rates_m3d" in results
    assert len(results["gas_injection_rates_m3d"]) == 21
    assert "bottomhole_pressures_bar" in results
    assert "liquid_production_rates_bpd" in results
    assert results["optimal_injection_rate_m3d"] >= 0.0
    assert results["minimum_pwf_bar"] > 0.0
    assert results["maximum_liquid_rate_bpd"] > 0.0


# ==========================================
# 2. API INTEGRATION TESTS
# ==========================================

def test_api_esp_endpoint(client, auth_headers):
    payload = {
        "method": "esp",
        "esp_params": {
            "flow_rate_m3h": 25.0,
            "static_lift_m": 800.0,
            "tubing_length_m": 1000.0,
            "tubing_diameter_in": 2.441,
            "roughness_m": 5e-5,
            "wellhead_pressure_bar": 15.0,
            "fluid_density_kg_m3": 880.0,
            "fluid_viscosity_cp": 10.0,
            "head_per_stage_m": 6.5,
            "pump_efficiency_pct": 65.0
        }
    }
    response = client.post("/api/v2/engineering/artificial-lift", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "esp"
    assert "results" in data
    assert "total_dynamic_head_m" in data["results"]


def test_api_gas_lift_endpoint(client, auth_headers):
    payload = {
        "method": "gas_lift",
        "gas_lift_params": {
            "liquid_rate_m3d": 120.0,
            "gas_injection_rate_m3d": 15000.0,
            "well_depth_m": 2500.0,
            "tubing_diameter_in": 2.441,
            "fluid_density_kg_m3": 880.0,
            "gas_density_kg_m3": 1.2,
            "wellhead_pressure_bar": 10.0,
            "productivity_index_j": 2.5,
            "reservoir_pressure_bar": 180.0
        }
    }
    response = client.post("/api/v2/engineering/artificial-lift", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "gas_lift"
    assert "results" in data
    assert "optimal_injection_rate_m3d" in data["results"]
