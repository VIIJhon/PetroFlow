"""
Resiliency and Dynamic Header Injection Tests for Gemini AI Service
Authored by Jhon Villegas
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.api.deps import reset_service_instances
from app.core.security import get_password_hash, create_access_token
from app.services.gemini_service import GeminiAIService

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_gemini_resiliency.db"
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
    reset_service_instances()
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testengineer",
        email="engineer@petroflow.com",
        hashed_password=get_password_hash("securepass123"),
        full_name="Ing. Jhon Villegas",
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


def test_analyze_report_local_twin_fallback(client, auth_headers):
    """
    Test that when NO Gemini API Key is provided, the service automatically
    falls back to the high-fidelity Local Physics Twin engine in Spanish.
    """
    # Send request without any custom X-Gemini-API-Key header
    payload = {
        "equipment_type": "pump",
        "equipment_name": "BOMBA-API610-001",
        "telemetry_data": {
            "vibration": 5.8,
            "temperature": 82.5,
            "rpm": 3550,
            "flow_rate": 88.0
        },
        "historical_context": "Vibración ascendente en cojinete radial."
    }
    
    response = client.post(
        "/api/v2/ai/analyze-report",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["model"] == "local-physics-twin"
    assert "BOMBA" in data["analysis"]
    # Check for Spanish Jhon Villegas signature
    assert "Jhon Villegas" in data["analysis"]
    assert "Líder de Ingeniería" in data["analysis"]
    assert "API 610" in data["analysis"]


def test_dynamic_api_key_injection_success(client, auth_headers):
    """
    Test that providing a custom X-Gemini-API-Key dynamically routes through Gemini AI
    and successfully handles standard generation when mocked.
    """
    mock_key = "AIzaSyMockKeyForTestingResiliency123"
    custom_headers = auth_headers.copy()
    custom_headers["X-Gemini-API-Key"] = mock_key
    
    payload = {
        "equipment_type": "compressor",
        "equipment_name": "COMP-API617-005",
        "telemetry_data": {
            "vibration": 4.8,
            "temperature": 92.5
        },
        "historical_context": "Monitoreo en línea"
    }
    
    # Mock GEMINI_AVAILABLE to True, mock genai module, and mock model generation
    mock_genai = MagicMock()
    with patch("app.services.gemini_service.GEMINI_AVAILABLE", True), \
         patch("app.services.gemini_service.genai", mock_genai), \
         patch.object(GeminiAIService, "_generate_content") as mock_gen:
        
        mock_gen.return_value = "ANÁLISIS MOCK DE GEMINI:\nCompresor COMP-API617-005 operando con vibración elevada de 4.8 mm/s.\nFirmado: Jhon Villegas."
        
        response = client.post(
            "/api/v2/ai/analyze-report",
            json=payload,
            headers=custom_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["model"] == "gemini-pro"
        assert "vibración" in data["analysis"]
        assert "Jhon Villegas" in data["analysis"]


def test_dynamic_api_key_injection_failure_fallback(client, auth_headers):
    """
    Test that even if a dynamic key is provided, if Gemini API fails or times out,
    the system resiliently falls back to the Local Physics Twin engine without crashing.
    """
    mock_key = "AIzaSyBrokenKey123"
    custom_headers = auth_headers.copy()
    custom_headers["X-Gemini-API-Key"] = mock_key
    
    payload = {
        "equipment_type": "turbine",
        "equipment_name": "TURB-API612-002",
        "telemetry_data": {
            "vibration": 3.8,
            "temperature": 410.0
        },
        "historical_context": "Vapor de alta presión"
    }
    
    mock_genai = MagicMock()
    with patch("app.services.gemini_service.GEMINI_AVAILABLE", True), \
         patch("app.services.gemini_service.genai", mock_genai), \
         patch.object(GeminiAIService, "_generate_content", side_effect=Exception("API Key Invalid or Quota Exceeded")):
        
        response = client.post(
            "/api/v2/ai/analyze-report",
            json=payload,
            headers=custom_headers
        )
        
        # Should gracefully fall back to local physics twin instead of throwing 500 error!
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["model"] == "local-physics-twin"
        assert "TURB-API612-002" in data["analysis"]
        assert "Jhon Villegas" in data["analysis"]


def test_ai_health_check_local_vs_gemini(client, auth_headers):
    """
    Test that /health returns appropriate model and connectivity state
    based on the presence of the dynamic API key.
    """
    # 1. No key -> reports healthy local mode
    response = client.get("/api/v2/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model"] == "local-physics-twin"
    
    # 2. Mock key injected -> verifies gemini model health
    custom_headers = auth_headers.copy()
    custom_headers["X-Gemini-API-Key"] = "AIzaSyMockKey"
    
    mock_genai = MagicMock()
    with patch("app.services.gemini_service.GEMINI_AVAILABLE", True), \
         patch("app.services.gemini_service.genai", mock_genai), \
         patch.object(GeminiAIService, "_generate_content") as mock_gen:
        
        mock_gen.return_value = "OK"
        
        response = client.get("/api/v2/ai/health", headers=custom_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model"] == "gemini-pro"
        assert "Gemini AI" in data["message"]
