"""
Compatibility API Endpoints (v1)
Provides backward compatibility for older clients, external SCADA/DCS integrations, and integration tests.
Authored by Jhon Villegas
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from core.physical_validator import validate_single
from core.alarm_manager import get_alarm_manager
from core.security import check_permission
from core.webhook_service import WebhookNotifier
from core.failure_prediction_engine import (
    get_risk_level,
    predict_failure,
    explain_prediction_shap,
    train_failure_prediction_model,
    train_pump_model,
    train_compressor_model,
    train_turbine_model,
    predict_pump_failure,
    predict_compressor_failure,
    predict_turbine_failure,
)

logger = logging.getLogger("petroflow.api.compat")
router = APIRouter(prefix="/api/v1", tags=["Legacy Compatibility V1"])

alarm_manager = get_alarm_manager()

DEFAULT_MODEL_KEY = "generic_rotating_equipment"
model_registry = {}

EQUIPMENT_MODEL_CONFIG = {
    "pump": {
        "train_fn": train_pump_model,
        "predict_fn": predict_pump_failure,
        "feature_columns": [
            "discharge_temperature",
            "inlet_pressure",
            "outlet_pressure",
            "volumetric_flow",
            "available_npsh",
        ],
    },
    "compressor": {
        "train_fn": train_compressor_model,
        "predict_fn": predict_compressor_failure,
        "feature_columns": [
            "discharge_temperature",
            "compression_ratio",
            "radial_vibration",
            "axial_vibration",
            "relative_humidity",
        ],
    },
    "turbine": {
        "train_fn": train_turbine_model,
        "predict_fn": predict_turbine_failure,
        "feature_columns": [
            "steam_temperature",
            "inlet_pressure",
            "axial_vibration",
            "synchronous_speed",
            "exhaust_temperature",
        ],
    },
}


def load_model_registry():
    """Train or load the prediction models for each equipment class."""
    global model_registry
    if model_registry:
        return

    try:
        for equipment, config in EQUIPMENT_MODEL_CONFIG.items():
            model, scaler, accuracy, feature_importance, test_data, metadata = config["train_fn"]()
            model_registry[equipment] = {
                "model": model,
                "scaler": scaler,
                "feature_columns": config["feature_columns"],
                "predict_fn": config["predict_fn"],
                "metadata": metadata,
            }
            logger.info(f"Loaded ML model for {equipment}: {metadata['model_type']} @ {metadata['training_date']}")

        # Generic fallback model for unsupported equipment types or generic sensor payloads
        model, scaler, accuracy, feature_importance, test_data, metadata = train_failure_prediction_model()
        model_registry[DEFAULT_MODEL_KEY] = {
            "model": model,
            "scaler": scaler,
            "feature_columns": ["temperature", "pressure", "vibration", "operating_hours", "rpm"],
            "predict_fn": predict_failure,
            "metadata": metadata,
        }
        logger.info(f"Default ML model loaded: {metadata['model_type']} @ {metadata['training_date']}")
    except Exception as exc:
        logger.error(f"Failed to initialize model registry in compatibility layer: {exc}")
        model_registry = {}


def get_model_info(equipment_type: str):
    load_model_registry()
    return model_registry.get(equipment_type.lower(), model_registry.get(DEFAULT_MODEL_KEY))


def extract_features(feature_columns, sensors):
    return {key: sensors.get(key, 0.0) for key in feature_columns}


# ============================================================================
# Schemas
# ============================================================================

class TelemetryPayload(BaseModel):
    model_config = {"strict": True} # Enforces strict type checking (no string-to-float coercion)
    equipment_id: str = Field(..., description="Unique equipment tag (e.g., PUMP-001)")
    equipment_type: str = Field(..., description="pump, compressor, or turbine")
    power_source: str = Field("electric", description="electric or diesel")
    fluid_type: str = Field("water", description="Operating fluid (e.g., crude, water, gas)")
    sensors: Dict[str, float] = Field(..., description="Key-value pairs of physical readings in SI units")


class TelemetryResponse(BaseModel):
    status: str
    failure_probability: Optional[float] = None
    risk_level: Optional[str] = None
    shap_explanation: Optional[Dict[str, float]] = None
    alarms_triggered: int = 0
    validation_issues: List[str] = []


class AlarmAckRequest(BaseModel):
    alarm_id: str
    operator_id: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/telemetry", response_model=TelemetryResponse)
async def ingest_telemetry(payload: TelemetryPayload):
    """
    Ingest telemetry, validate physical bounds (API 670), run predictions, and evaluate alarms.
    Authored by Jhon Villegas
    """
    # 1. Physical Validation
    validation_issues = []
    blocked = False
    
    for param, value in payload.sensors.items():
        res = validate_single(param, value)
        if res.blocked:
            blocked = True
            validation_issues.extend([i.message for i in res.issues if i.severity == "error"])
            
    if blocked:
        return TelemetryResponse(
            status="REJECTED_PHYSICAL_BOUNDS",
            validation_issues=validation_issues
        )

    # 2. ML Prediction
    failure_prob = 0.0
    risk_level = "Unknown"
    shap_explanation = None

    try:
        model_info = get_model_info(payload.equipment_type)
        if model_info:
            features = extract_features(model_info["feature_columns"], payload.sensors)
            if model_info["predict_fn"] is predict_failure:
                failure_prob, category, category_name, prob_dict = model_info["predict_fn"](
                    model=model_info["model"],
                    scaler=model_info["scaler"],
                    features_dict=features,
                )
            else:
                failure_prob, category, category_name, prob_dict = model_info["predict_fn"](
                    model=model_info["model"],
                    scaler=model_info["scaler"],
                    **features,
                )
            risk_level, _ = get_risk_level(failure_prob)
            try:
                shap_explanation = explain_prediction_shap(
                    model=model_info["model"],
                    scaler=model_info["scaler"],
                    features_dict=features,
                    feature_columns=model_info["feature_columns"],
                )
            except Exception as explanation_error:
                logger.warning(f"SHAP explanation unavailable in compatibility layer: {explanation_error}")
                shap_explanation = None
        else:
            logger.warning("No prediction model available in registry; returning fallback response.")
    except Exception as e:
        logger.error(f"Prediction failed for {payload.equipment_id} in compatibility layer: {e}")

    # 3. Alarm Evaluation (ISA-18.2)
    new_alarms = alarm_manager.evaluate(
        equipment_id=payload.equipment_id,
        equipment_type=payload.equipment_type,
        readings=payload.sensors,
        failure_probability=failure_prob
    )
    
    # 4. Trigger Webhooks for Critical Risk
    if risk_level == "Critical":
        try:
            notifier = WebhookNotifier("https://your-webhook-endpoint.com/alert")
            notifier.send_alert(
                equipment_id=payload.equipment_id,
                risk_level=risk_level,
                probability=failure_prob,
                recommendations=["Automatic Dispatch via API"]
            )
        except Exception as e:
            logger.error(f"Failed to dispatch webhook for {payload.equipment_id} in compatibility layer: {e}")

    return TelemetryResponse(
        status="SUCCESS",
        failure_probability=failure_prob,
        risk_level=risk_level,
        shap_explanation=shap_explanation,
        alarms_triggered=len(new_alarms),
        validation_issues=validation_issues,
    )


@router.get("/alarms")
async def get_active_alarms(equipment_id: Optional[str] = None):
    """
    Get all active alarms, optionally filtered by equipment ID.
    Authored by Jhon Villegas
    """
    alarms = alarm_manager.get_active_alarms(equipment_id=equipment_id)
    return {"alarms": [a.to_dict() for a in alarms]}


@router.post("/alarms/ack")
async def acknowledge_alarm(req: AlarmAckRequest, x_role: str = Header(default="viewer")):
    """
    Acknowledge an alarm. Enforces RBAC from IEC 62443.
    Requires at least 'analyst' role.
    Authored by Jhon Villegas
    """
    if not check_permission(x_role, "acknowledge_alarms"):
        raise HTTPException(status_code=403, detail="Insufficient privileges to acknowledge alarms")
        
    success = alarm_manager.acknowledge(req.alarm_id, req.operator_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alarm not found or already acknowledged")
        
    return {"status": "SUCCESS", "alarm_id": req.alarm_id}
