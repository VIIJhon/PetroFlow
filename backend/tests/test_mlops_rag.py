"""
Comprehensive Unit & Integration Test Suite for MLOps Local Console and RAG Engineering Database
Authored by Jhon Villegas
Líder de Ingeniería PetroFlow Enterprise
"""

import pytest
import io
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.api.deps import reset_service_instances
from app.core.security import get_password_hash, create_access_token
from app.services.gemini_service import GeminiAIService, API_STANDARDS

# Test database setup (using a separate isolated sqlite db)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_mlops_rag.db"
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
    """Create a test engineer user."""
    user = User(
        username="jvillegas",
        email="jvillegas@petroflow.com",
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


def test_train_predictive_model_success_with_valid_csv(client, auth_headers):
    """
    Test that the training endpoint /api/v2/ai/train-model successfully
    accepts a valid telemetry CSV file and returns the correct MLOps JSON payload.
    """
    # Create a robust valid CSV telemetry dataset with 60 samples to guarantee representative splits
    rows = ["vibration,temperature,pressure,flow_rate,failure_occurred"]
    for i in range(30):
        # 30 normal samples
        rows.append("1.2,45.5,120.0,300.0,0")
    for i in range(30):
        # 30 failure samples
        rows.append("5.2,92.0,170.0,120.5,1")
    csv_data = "\n".join(rows) + "\n"
    
    csv_bytes = csv_data.encode("utf-8")
    files = {"file": ("test_telemetry.csv", csv_bytes, "text/csv")}
    
    response = client.post(
        "/api/v2/ai/train-model",
        files=files,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Assert JSON payload structure matches executive requirements
    assert data["success"] is True
    assert "metrics" in data
    assert "accuracy" in data["metrics"]
    assert "precision" in data["metrics"]
    assert "recall" in data["metrics"]
    assert "f1_score" in data["metrics"]
    assert data["metrics"]["total_samples"] >= 6
    
    assert "confusion_matrix" in data
    assert "true_positives" in data["confusion_matrix"]
    assert "false_positives" in data["confusion_matrix"]
    assert "true_negatives" in data["confusion_matrix"]
    assert "false_negatives" in data["confusion_matrix"]
    
    assert "feature_importances" in data
    assert "Vibración" in data["feature_importances"]
    assert "Temperatura" in data["feature_importances"]
    assert "Presión" in data["feature_importances"]
    assert "Caudal" in data["feature_importances"]
    
    assert "loss_history" in data
    assert len(data["loss_history"]) > 0
    assert "accuracy_history" in data
    assert len(data["accuracy_history"]) > 0
    assert "roc_curve" in data
    assert len(data["roc_curve"]) > 0
    
    assert "model_weights" in data
    assert "vibration_weight" in data["model_weights"]
    assert "temperature_weight" in data["model_weights"]
    
    assert "Jhon Villegas" in data["signature"]
    assert "Líder de Ingeniería" in data["signature"]


def test_train_predictive_model_empty_csv(client, auth_headers):
    """
    Test that uploading an empty or invalid file properly returns a 400 Bad Request.
    """
    files = {"file": ("empty.csv", b"", "text/csv")}
    
    response = client.post(
        "/api/v2/ai/train-model",
        files=files,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "empty" in data["detail"] or "format" in data["detail"]


def test_train_predictive_model_insufficient_rows_trigger_synthetic_fallback(client, auth_headers):
    """
    Test that uploading under 5 telemetry rows triggers the high-fidelity
    synthetic generator fallback to ensure training succeeds for the operator demo.
    """
    # CSV with only 2 rows
    csv_data = (
        "vibration,temperature,pressure,flow_rate,failure_occurred\n"
        "1.2,45.5,120.0,300.0,0\n"
        "4.8,88.5,165.0,140.0,1\n"
    )
    
    csv_bytes = csv_data.encode("utf-8")
    files = {"file": ("insufficient.csv", csv_bytes, "text/csv")}
    
    response = client.post(
        "/api/v2/ai/train-model",
        files=files,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # The synthetic generator creates 200 rows by default, making total samples 200
    assert data["metrics"]["total_samples"] == 200


def test_local_rag_standards_retrieval_logic():
    """
    Test the internal semantic/fuzzy context retrieval logic in GeminiAIService
    for pumps (API 610), compressors (API 617), and steam turbines (API 612).
    """
    service = GeminiAIService()
    
    # 1. Pump RAG context retrieval (API 610)
    pump_context = service._retrieve_api_standards_context(
        equipment_type="Centrifugal Pump",
        telemetry_data={"vibration": 5.2, "temperature": 94.0, "flow_rate": 80.0},
        historical_context="Cavitación recurrente por NPSH insuficiente en succión."
    )
    assert "API 610" in pump_context
    assert "Bearing housing temperature shall not exceed" in pump_context
    assert "vibration level (RMS velocity)" in pump_context
    assert "bubble cavitation" in pump_context

    # 2. Compressor RAG context retrieval (API 617)
    compressor_context = service._retrieve_api_standards_context(
        equipment_type="compressor",
        telemetry_data={"vibration": 4.8, "temperature": 155.0},
        historical_context="El compresor experimenta recirculación y oscilaciones por surge."
    )
    assert "API 617" in compressor_context
    assert "anti-surge valve" in compressor_context
    assert "peak-to-peak displacement" in compressor_context
    assert "discharge temperature" in compressor_context

    # 3. Steam Turbine RAG context retrieval (API 612)
    turbine_context = service._retrieve_api_standards_context(
        equipment_type="turbine",
        telemetry_data={"vibration": 4.2, "temperature": 130.0},
        historical_context="La turbina requiere barring gear o virador para evitar el arqueo térmico del rotor."
    )
    assert "API 612" in turbine_context
    assert "turning gear" in turbine_context or "barring gear" in turbine_context
    assert "exhaust temperature" in turbine_context
    assert "shaft relative to the bearing" in turbine_context


def test_online_rag_prompt_injection_structure(client, auth_headers):
    """
    Test that when a dynamic API Key is provided, the prompt sent to Gemini
    correctly encapsulates the extracted local RAG standards context.
    """
    mock_key = "AIzaSyMockKeyForRAGTesting456"
    custom_headers = auth_headers.copy()
    custom_headers["X-Gemini-API-Key"] = mock_key
    
    payload = {
        "equipment_type": "pump",
        "equipment_name": "BOMBA-CRUDO-A",
        "telemetry_data": {
            "vibration": 5.8,
            "temperature": 85.0,
            "flow_rate": 90.0
        },
        "historical_context": "Detección de cavitación"
    }
    
    mock_genai = MagicMock()
    with patch("app.services.gemini_service.GEMINI_AVAILABLE", True), \
         patch("app.services.gemini_service.genai", mock_genai), \
         patch.object(GeminiAIService, "_generate_content") as mock_gen:
        
        mock_gen.return_value = "Gemini RAG output"
        
        response = client.post(
            "/api/v2/ai/analyze-report",
            json=payload,
            headers=custom_headers
        )
        
        assert response.status_code == 200
        # Verify that the mocked model generation was called
        assert mock_gen.called
        
        # Verify that the prompt contains the official standards section headers
        prompt_arg = mock_gen.call_args[0][0]
        assert "NORMAS TÉCNICAS E ESTÁNDARE DE RESPALDO" in prompt_arg
        assert "API 610" in prompt_arg
        assert "cavitación" in prompt_arg or "cavitation" in prompt_arg


def test_offline_fallback_report_incorporates_rag(client, auth_headers):
    """
    Test that in resilient offline mode (fallback to local physics twin engine),
    the generated report explicitly incorporates and cites the pre-compiled RAG API standards.
    """
    payload = {
        "equipment_type": "compressor",
        "equipment_name": "COMPRESOR-B",
        "telemetry_data": {
            "vibration": 4.8,
            "temperature": 152.0,
            "pressure": 160.0
        },
        "historical_context": "Evento de reciclo anti-surge."
    }
    
    # Request without custom key header to force offline local twin engine
    response = client.post(
        "/api/v2/ai/analyze-report",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["model"] == "local-physics-twin"
    
    # Ensure standards citation and technical limits are rendered in Spanish report
    analysis_text = data["analysis"]
    assert "API 617" in analysis_text
    assert "surge" in analysis_text or "anti-surge" in analysis_text
    assert "150°C" in analysis_text
    assert "Jhon Villegas" in analysis_text
    assert "Líder de Ingeniería" in analysis_text
