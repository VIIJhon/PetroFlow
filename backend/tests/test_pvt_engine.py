"""
Unit and Integration Tests for PVT Engine in PetroFlow Enterprise
Verifies calculations and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token

from core.pvt_engine import PVTEngine

# -------------------------------------------------------------
# Test Database & Fixtures Setup (Self-Contained)
# -------------------------------------------------------------

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_pvt_engine.db"
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
# 1. PVT ENGINE UNIT TESTS
# ==========================================

def test_pvt_standing_pb():
    # Realistic well conditions
    rs = 500.0  # scf/bbl
    temp = 180.0  # °F
    api = 35.0  # API
    gas_gravity = 0.65
    
    pb = PVTEngine.calculate_standing_pb(rs, temp, api, gas_gravity)
    assert pb > 14.7
    assert 1000.0 < pb < 4000.0


def test_pvt_standing_rs():
    pb = 2000.0
    total_gor = 500.0
    temp = 180.0
    api = 35.0
    gas_gravity = 0.65
    
    # Pressure above Pb -> Rs should be total GOR
    rs_above = PVTEngine.calculate_standing_rs(2500.0, temp, api, gas_gravity, pb, total_gor)
    assert rs_above == total_gor
    
    # Pressure below Pb -> Rs should be less than total GOR
    rs_below = PVTEngine.calculate_standing_rs(1000.0, temp, api, gas_gravity, pb, total_gor)
    assert rs_below < total_gor
    assert rs_below > 0.0


def test_pvt_standing_bo():
    pb = 2000.0
    rs = 500.0
    temp = 180.0
    api = 35.0
    gas_gravity = 0.65
    
    # Bo should be around 1.1 - 1.5 bbl/STB
    bo_below = PVTEngine.calculate_standing_bo(rs, temp, api, gas_gravity, 1500.0, pb)
    assert 1.0 < bo_below < 2.0
    
    bo_above = PVTEngine.calculate_standing_bo(rs, temp, api, gas_gravity, 3000.0, pb)
    assert 1.0 < bo_above < 2.0


def test_pvt_bg():
    bg = PVTEngine.calculate_bg(1000.0, 180.0, 0.65)
    assert bg > 0
    assert bg < 0.1  # typically very small number like 0.003 bbl/scf


def test_pvt_viscosity():
    pb = 2000.0
    rs = 500.0
    temp = 180.0
    api = 35.0
    
    mu = PVTEngine.calculate_oil_viscosity(rs, temp, api, 1500.0, pb)
    assert mu > 0.0
    assert mu < 50.0  # reasonable for light oil at high temp


def test_pvt_solve_profile():
    profile = PVTEngine.solve_pvt_profile(180.0, 35.0, 0.65, 500.0)
    assert "pressures" in profile
    assert len(profile["pressures"]) == 20
    assert profile["bubblepoint_pressure_psi"] > 0
    assert len(profile["standing"]["rs"]) == 20
    assert len(profile["vasquez_beggs"]["bo"]) == 20
    assert len(profile["viscosity"]) == 20


# ==========================================
# 2. API INTEGRATION TESTS
# ==========================================

def test_api_pvt_endpoint(client, auth_headers):
    # Tests the POST /pvt endpoint
    payload = {
        "temp_f": 180.0,
        "api": 35.0,
        "gas_gravity": 0.65,
        "total_gor": 500.0,
        "p_min": 500.0,
        "p_max": 4000.0,
        "steps": 15
    }
    response = client.post("/api/v2/engineering/pvt", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "bubblepoint_pressure_psi" in data
    assert len(data["pressures"]) == 15
