"""
AI Analysis Schemas
Pydantic models for Gemini AI analysis requests and responses
Authored by Jhon Villegas
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UrgencyLevel(str, Enum):
    """Urgency level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SeverityLevel(str, Enum):
    """Severity level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BudgetConstraint(str, Enum):
    """Budget constraint enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNLIMITED = "unlimited"


class LanguageOption(str, Enum):
    """Supported languages for operator messages"""
    ENGLISH = "english"
    SPANISH = "spanish"
    PORTUGUESE = "portuguese"
    FRENCH = "french"


# ========== Equipment Report Analysis ==========

class EquipmentReportRequest(BaseModel):
    """Request schema for equipment report analysis"""
    equipment_type: str = Field(..., description="Type of equipment (pump, compressor, turbine, valve, etc.)")
    equipment_name: str = Field(..., description="Name or ID of the equipment")
    telemetry_data: Dict[str, Any] = Field(..., description="Current telemetry readings")
    historical_context: Optional[str] = Field(None, description="Optional historical context or trends")
    # Campos avanzados de clasificación multinivel (Jhon Villegas - PetroFlow v2.0)
    equipment_subtype: Optional[str] = Field(None, description="Equipment subtype (e.g., centrifugal_surface, esp, reciprocating, axial, gate, globe, ball, butterfly, check, psv)")
    working_fluid: Optional[str] = Field(None, description="Working fluid (e.g., crude_oil, natural_gas, water, gasoline, diesel, steam, air, chemicals)")
    energy_source: Optional[str] = Field(None, description="Energy source (e.g., electric_motor, gas_turbine, steam_turbine, diesel_engine, pneumatic, hydraulic)")
    
    @validator('equipment_type')
    def validate_equipment_type(cls, v):
        """Validate equipment type — accepts main categories and subtype-prefixed strings"""
        base_types = ['pump', 'compressor', 'turbine', 'motor', 'generator', 'heat_exchanger', 'valve',
                      'bomba', 'compresor', 'turbina', 'valvula', 'válvula']
        v_lower = v.lower()
        if not any(b in v_lower for b in base_types):
            raise ValueError(f"Equipment type must contain one of: {', '.join(base_types)}")
        return v_lower
    
    @validator('telemetry_data')
    def validate_telemetry_data(cls, v):
        """Validate telemetry data is not empty"""
        if not v:
            raise ValueError("Telemetry data cannot be empty")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "equipment_type": "pump",
                "equipment_name": "PUMP-001",
                "telemetry_data": {
                    "temperature": 85.5,
                    "pressure": 120.3,
                    "vibration": 2.1,
                    "flow_rate": 450.0,
                    "power_consumption": 75.2
                },
                "historical_context": "Temperature has been trending upward over the past 48 hours"
            }
        }


class AIAnalysisResponse(BaseModel):
    """Response schema for AI analysis"""
    success: bool = Field(..., description="Whether the analysis was successful")
    analysis: Optional[str] = Field(None, description="AI-generated analysis text")
    severity: Optional[SeverityLevel] = Field(None, description="Detected severity level")
    equipment_type: str = Field(..., description="Type of equipment analyzed")
    equipment_name: str = Field(..., description="Name of equipment analyzed")
    timestamp: str = Field(..., description="Analysis timestamp (ISO format)")
    model: Optional[str] = Field(None, description="AI model used")
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "analysis": "Overall equipment health: 7/10\n\nKey findings:\n- Temperature elevated but within acceptable range\n- Vibration levels normal\n- Flow rate optimal\n\nRecommendations:\n1. Monitor temperature trend closely\n2. Schedule inspection within 2 weeks",
                "severity": "medium",
                "equipment_type": "pump",
                "equipment_name": "PUMP-001",
                "timestamp": "2026-05-21T13:45:00Z",
                "model": "gemini-pro"
            }
        }


# ========== Operator Message Generation ==========

class OperatorMessageRequest(BaseModel):
    """Request schema for operator message generation"""
    situation: str = Field(..., description="Description of the current situation")
    technical_details: Dict[str, Any] = Field(..., description="Technical data and context")
    urgency: UrgencyLevel = Field(UrgencyLevel.MEDIUM, description="Urgency level")
    language: LanguageOption = Field(LanguageOption.ENGLISH, description="Target language")
    
    @validator('situation')
    def validate_situation(cls, v):
        """Validate situation description"""
        if len(v.strip()) < 10:
            raise ValueError("Situation description must be at least 10 characters")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "situation": "Pump PUMP-001 showing elevated temperature and increased vibration",
                "technical_details": {
                    "current_temperature": 95.5,
                    "normal_temperature": 75.0,
                    "vibration_level": 3.2,
                    "threshold_vibration": 2.5
                },
                "urgency": "high",
                "language": "english"
            }
        }


class OperatorMessageResponse(BaseModel):
    """Response schema for operator message"""
    success: bool = Field(..., description="Whether message generation was successful")
    message: Optional[str] = Field(None, description="Generated operator message")
    urgency: UrgencyLevel = Field(..., description="Urgency level")
    language: LanguageOption = Field(..., description="Message language")
    timestamp: str = Field(..., description="Generation timestamp (ISO format)")
    model: Optional[str] = Field(None, description="AI model used")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "ATTENTION: Pump PUMP-001 needs immediate attention.\n\nWhat's happening:\n- Temperature is higher than normal (95.5°C vs normal 75°C)\n- Vibration is above safe levels\n\nWhat you need to do:\n1. Reduce pump speed by 20%\n2. Check cooling system\n3. Report any unusual sounds\n\nThis is urgent - please act within the next hour.",
                "urgency": "high",
                "language": "english",
                "timestamp": "2026-05-21T13:45:00Z",
                "model": "gemini-pro"
            }
        }


# ========== Failure Prediction Explanation ==========

class FailurePredictionRequest(BaseModel):
    """Request schema for failure prediction explanation"""
    equipment_type: str = Field(..., description="Type of equipment")
    equipment_name: str = Field(..., description="Name or ID of the equipment")
    prediction_data: Dict[str, Any] = Field(..., description="ML model prediction data and features")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence (0-1)")
    time_to_failure: Optional[str] = Field(None, description="Estimated time until failure")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Validate confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "equipment_type": "compressor",
                "equipment_name": "COMP-005",
                "prediction_data": {
                    "temperature_trend": "increasing",
                    "vibration_pattern": "irregular",
                    "efficiency_drop": 12.5,
                    "operating_hours": 8500
                },
                "confidence": 0.85,
                "time_to_failure": "7-14 days"
            }
        }


class FailurePredictionResponse(BaseModel):
    """Response schema for failure prediction explanation"""
    success: bool = Field(..., description="Whether explanation generation was successful")
    explanation: Optional[str] = Field(None, description="Human-readable explanation")
    confidence: float = Field(..., description="Prediction confidence")
    equipment_type: str = Field(..., description="Type of equipment")
    equipment_name: str = Field(..., description="Name of equipment")
    timestamp: str = Field(..., description="Generation timestamp (ISO format)")
    model: Optional[str] = Field(None, description="AI model used")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "explanation": "Our system predicts that compressor COMP-005 may fail within 7-14 days.\n\nWhy we think this:\n- Temperature has been steadily rising\n- Vibration patterns are becoming irregular\n- Efficiency has dropped by 12.5%\n- The equipment has run for 8,500 hours\n\nConfidence: 85% - This is a strong prediction.\n\nWhat to watch:\n- Any sudden changes in noise\n- Further temperature increases\n- Unusual vibrations\n\nRecommended action: Schedule inspection within 3 days.",
                "confidence": 0.85,
                "equipment_type": "compressor",
                "equipment_name": "COMP-005",
                "timestamp": "2026-05-21T13:45:00Z",
                "model": "gemini-pro"
            }
        }


# ========== Maintenance Suggestions ==========

class MaintenanceHistoryRecord(BaseModel):
    """Schema for maintenance history record"""
    date: str = Field(..., description="Maintenance date")
    action: str = Field(..., description="Maintenance action performed")
    cost: Optional[float] = Field(None, description="Cost of maintenance")
    duration: Optional[str] = Field(None, description="Duration of maintenance")


class MaintenanceSuggestionsRequest(BaseModel):
    """Request schema for maintenance suggestions"""
    equipment_type: str = Field(..., description="Type of equipment")
    equipment_name: str = Field(..., description="Name or ID of the equipment")
    current_condition: Dict[str, Any] = Field(..., description="Current equipment condition and metrics")
    maintenance_history: Optional[List[MaintenanceHistoryRecord]] = Field(None, description="Maintenance history")
    budget_constraint: Optional[BudgetConstraint] = Field(None, description="Budget constraint")
    
    @validator('current_condition')
    def validate_current_condition(cls, v):
        """Validate current condition data"""
        if not v:
            raise ValueError("Current condition data cannot be empty")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "equipment_type": "turbine",
                "equipment_name": "TURB-003",
                "current_condition": {
                    "overall_health": 6.5,
                    "temperature": 450.0,
                    "vibration": 3.8,
                    "efficiency": 82.5,
                    "operating_hours": 12000
                },
                "maintenance_history": [
                    {
                        "date": "2026-03-15",
                        "action": "Bearing replacement",
                        "cost": 5000.0,
                        "duration": "8 hours"
                    }
                ],
                "budget_constraint": "medium"
            }
        }


class MaintenanceSuggestionsResponse(BaseModel):
    """Response schema for maintenance suggestions"""
    success: bool = Field(..., description="Whether suggestion generation was successful")
    suggestions: Optional[str] = Field(None, description="Prioritized maintenance suggestions")
    equipment_type: str = Field(..., description="Type of equipment")
    equipment_name: str = Field(..., description="Name of equipment")
    timestamp: str = Field(..., description="Generation timestamp (ISO format)")
    model: Optional[str] = Field(None, description="AI model used")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "suggestions": "MAINTENANCE ACTION PLAN - TURB-003\n\nIMMEDIATE (24 hours):\n1. Vibration analysis - 2 hours - Critical for safety\n\nSHORT-TERM (1 week):\n1. Lubrication system check - 4 hours - Prevent further wear\n2. Temperature sensor calibration - 2 hours - Ensure accurate readings\n\nMEDIUM-TERM (1 month):\n1. Blade inspection - 8 hours - Scheduled maintenance\n2. Cooling system cleaning - 6 hours - Improve efficiency\n\nLONG-TERM:\n1. Major overhaul planning - Consider at 15,000 hours",
                "equipment_type": "turbine",
                "equipment_name": "TURB-003",
                "timestamp": "2026-05-21T13:45:00Z",
                "model": "gemini-pro"
            }
        }


# ========== Service Health Check ==========

class AIServiceHealthResponse(BaseModel):
    """Response schema for AI service health check"""
    status: str = Field(..., description="Service status (healthy, disabled, unavailable, error)")
    message: str = Field(..., description="Status message")
    enabled: bool = Field(..., description="Whether service is enabled")
    model: Optional[str] = Field(None, description="AI model in use")
    rate_limit_remaining: Optional[int] = Field(None, description="Remaining API calls in current window")
    error: Optional[str] = Field(None, description="Error details if status is error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "message": "Gemini AI service is operational",
                "enabled": True,
                "model": "gemini-pro",
                "rate_limit_remaining": 12
            }
        }