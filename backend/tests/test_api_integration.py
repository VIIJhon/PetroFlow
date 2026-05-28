"""Integration tests for the FastAPI API layer and model integration."""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_post_telemetry_uses_ai_model_and_returns_prediction():
    payload = {
        "equipment_id": "PUMP-001",
        "equipment_type": "pump",
        "power_source": "electric",
        "fluid_type": "water",
        "sensors": {
            "discharge_temperature": 75.0,
            "inlet_pressure": 1.8,
            "outlet_pressure": 20.0,
            "volumetric_flow": 160.0,
            "available_npsh": 3.2,
        },
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "SUCCESS"
    assert isinstance(body["failure_probability"], float)
    assert 0.0 <= body["failure_probability"] <= 100.0
    assert body["risk_level"] in ["Low Risk", "Medium Risk", "High Risk", "Unknown"]
    assert isinstance(body["validation_issues"], list)
    assert isinstance(body["alarms_triggered"], int)
    assert "shap_explanation" in body


def test_post_telemetry_uses_compressor_model_and_returns_prediction():
    payload = {
        "equipment_id": "COMP-001",
        "equipment_type": "compressor",
        "power_source": "electric",
        "fluid_type": "gas",
        "sensors": {
            "discharge_temperature": 90.0,
            "compression_ratio": 4.8,
            "radial_vibration": 1.2,
            "axial_vibration": 0.8,
            "relative_humidity": 52.0,
        },
    }

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "SUCCESS"
    assert isinstance(body["failure_probability"], float)
    assert 0.0 <= body["failure_probability"] <= 100.0
    assert body["risk_level"] in ["Low Risk", "Medium Risk", "High Risk", "Unknown"]
    assert isinstance(body["validation_issues"], list)
    assert isinstance(body["alarms_triggered"], int)
    assert "shap_explanation" in body


def test_acknowledge_alarm_enforces_rbac_for_viewer():
    response = client.post(
        "/api/v1/alarms/ack",
        json={"alarm_id": "missing", "operator_id": "op1"},
        headers={"x-role": "viewer"},
    )
    assert response.status_code == 403


def test_acknowledge_alarm_allows_analyst_and_returns_not_found_for_missing_alarm():
    response = client.post(
        "/api/v1/alarms/ack",
        json={"alarm_id": "missing", "operator_id": "op1"},
        headers={"x-role": "analyst"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Alarm not found or already acknowledged"
