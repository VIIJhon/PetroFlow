"""
Unit and Integration Tests for User Management CRUD and Well Context Geological Risk Assessment.
Authored by Jhon Villegas
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_active_user, get_current_user
from app.models.user import User, UserRole

# Standard FastAPI Test Client
client = TestClient(app)

# Helper mock users
admin_user = User(
    id=999,
    email="admin@test.com",
    username="admin_test",
    full_name="Test Administrator",
    role=UserRole.ADMIN,
    is_active=True
)

engineer_user = User(
    id=888,
    email="engineer@test.com",
    username="engineer_test",
    full_name="Test Engineer",
    role=UserRole.ENGINEER,
    is_active=True
)

viewer_user = User(
    id=777,
    email="viewer@test.com",
    username="viewer_test",
    full_name="Test Viewer",
    role=UserRole.VIEWER,
    is_active=True
)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Ensure dependency overrides are cleaned up after each test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# ===========================================================================
# 1. TESTS FOR WELL CONTEXT GEOLOGICAL ANALYSIS
# ===========================================================================

def test_well_context_analysis_success():
    # Set up dependency override to allow any active user to call this
    app.dependency_overrides[get_current_user] = lambda: admin_user
    
    payload = {
        "depth_meters": 3200.0,
        "bottom_hole_temp": 110.0,
        "oil_viscosity_cst": 125.0,
        "api_gravity": 22.0,
        "formation_type": "Limestone",
        "gas_oil_ratio": 240.0,
        "water_cut_percent": 45.0,
        "subsea": False
    }
    
    response = client.post("/api/analysis/well-context", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert data["well_type"] is not None
    assert "overall_risk_score" in data
    assert "thermal_risk" in data
    assert "derating" in data
    assert "failure_modes" in data
    assert "text_report" in data
    assert data["derating"]["flow_rate_factor"] <= 1.0


def test_well_context_analysis_missing_auth():
    # Calling without auth should fail with 401/403 depending on security dependencies
    response = client.post("/api/analysis/well-context", json={})
    assert response.status_code in [401, 403]


# ===========================================================================
# 2. TESTS FOR USER MANAGEMENT CRUD (ADMIN RBAC)
# ===========================================================================

def test_list_users_as_admin():
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    
    response = client.get("/api/v2/users/")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data


def test_list_users_as_engineer():
    app.dependency_overrides[get_current_active_user] = lambda: engineer_user
    
    response = client.get("/api/v2/users/")
    assert response.status_code == 200  # Engineers also have read access to users list


def test_list_users_as_viewer_forbidden():
    app.dependency_overrides[get_current_active_user] = lambda: viewer_user
    
    response = client.get("/api/v2/users/")
    assert response.status_code == 403
    assert "permiso" in response.json()["detail"].lower()


def test_create_user_as_admin_success():
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    
    payload = {
        "email": f"new_user_{unique_suffix}@test.com",
        "username": f"user_{unique_suffix}",
        "password": "SuperSecurePassword123",  # Satisfies password strength (has uppercase, lowercase, number)
        "full_name": "New Test User",
        "role": "engineer"
    }
    
    response = client.post("/api/v2/users/", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]
    assert data["role"] == "engineer"
    assert data["is_active"] is True
    assert data["is_admin"] is False


def test_create_user_as_viewer_forbidden():
    app.dependency_overrides[get_current_active_user] = lambda: viewer_user
    
    payload = {
        "email": "should_fail@test.com",
        "username": "should_fail",
        "password": "SuperSecurePassword123",
        "full_name": "Should Fail User",
        "role": "operator"
    }
    
    response = client.post("/api/v2/users/", json=payload)
    assert response.status_code == 403
