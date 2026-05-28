"""
Analysis Schemas
Pydantic models for analysis-related requests/responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AnalysisType(str, Enum):
    """Analysis type enumeration"""
    PERFORMANCE = "performance"
    HEALTH = "health"
    EFFICIENCY = "efficiency"
    VIBRATION = "vibration"
    THERMAL = "thermal"
    PRESSURE = "pressure"
    FLOW = "flow"
    PREDICTIVE = "predictive"
    ROOT_CAUSE = "root_cause"
    TREND = "trend"


class AnalysisStatus(str, Enum):
    """Analysis status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    """Severity level enumeration"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AnalysisBase(BaseModel):
    """Base analysis schema"""
    analysis_type: AnalysisType = Field(..., description="Type of analysis")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Analysis parameters")
    description: Optional[str] = Field(None, description="Analysis description")


class AnalysisCreate(AnalysisBase):
    """Schema for creating an analysis"""
    equipment_id: int = Field(..., description="Equipment ID to analyze")
    
    @validator('parameters')
    def validate_parameters(cls, v, values):
        """Validate analysis parameters based on type"""
        analysis_type = values.get('analysis_type')
        
        if analysis_type == AnalysisType.VIBRATION:
            if 'sensor_data' not in v and 'time_series' not in v:
                raise ValueError("Vibration analysis requires 'sensor_data' or 'time_series'")
        
        elif analysis_type == AnalysisType.PREDICTIVE:
            if 'historical_data' not in v:
                raise ValueError("Predictive analysis requires 'historical_data'")
        
        return v


class AnalysisUpdate(BaseModel):
    """Schema for updating an analysis"""
    status: Optional[AnalysisStatus] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AnalysisResponse(AnalysisBase):
    """Schema for analysis response"""
    id: int
    equipment_id: int
    status: AnalysisStatus
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    """Schema for analysis list response"""
    analyses: List[AnalysisResponse]
    total: int


class PerformanceAnalysisRequest(BaseModel):
    """Schema for performance analysis request"""
    equipment_id: int
    time_period: Optional[str] = Field("24h", description="Time period (1h, 24h, 7d, 30d)")
    metrics: List[str] = Field(default_factory=list, description="Specific metrics to analyze")
    include_baseline: bool = Field(True, description="Include baseline comparison")


class PerformanceAnalysisResponse(BaseModel):
    """Schema for performance analysis results"""
    analysis_id: int
    equipment_tag: str
    overall_performance: float = Field(..., ge=0, le=100, description="Overall performance score")
    efficiency: float = Field(..., ge=0, le=100, description="Efficiency percentage")
    availability: float = Field(..., ge=0, le=100, description="Availability percentage")
    reliability: float = Field(..., ge=0, le=100, description="Reliability score")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Detailed metrics")
    baseline_comparison: Optional[Dict[str, Any]] = None
    trends: Dict[str, str] = Field(default_factory=dict, description="Trend indicators")
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime


class HealthAnalysisRequest(BaseModel):
    """Schema for health analysis request"""
    equipment_id: int
    include_sensors: bool = Field(True, description="Include sensor data analysis")
    include_maintenance: bool = Field(True, description="Include maintenance history")
    include_predictions: bool = Field(True, description="Include failure predictions")


class HealthAnalysisResponse(BaseModel):
    """Schema for health analysis results"""
    analysis_id: int
    equipment_tag: str
    health_score: float = Field(..., ge=0, le=100, description="Overall health score")
    severity: SeverityLevel
    condition_indicators: Dict[str, float] = Field(default_factory=dict)
    sensor_health: Optional[Dict[str, Any]] = None
    maintenance_status: Optional[Dict[str, Any]] = None
    failure_probability: Optional[float] = Field(None, ge=0, le=1)
    remaining_useful_life: Optional[float] = Field(None, description="RUL in hours")
    issues_detected: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime


class VibrationAnalysisRequest(BaseModel):
    """Schema for vibration analysis request"""
    equipment_id: int
    sensor_data: Optional[List[float]] = Field(None, description="Raw vibration data")
    sampling_rate: Optional[float] = Field(None, description="Sampling rate in Hz")
    time_series: Optional[Dict[str, List[float]]] = None
    analysis_methods: List[str] = Field(
        default_factory=lambda: ["fft", "rms", "peak"],
        description="Analysis methods to apply"
    )


class VibrationAnalysisResponse(BaseModel):
    """Schema for vibration analysis results"""
    analysis_id: int
    equipment_tag: str
    overall_vibration: float = Field(..., description="Overall vibration level in mm/s")
    rms_value: float = Field(..., description="RMS vibration value")
    peak_value: float = Field(..., description="Peak vibration value")
    frequency_spectrum: Optional[Dict[str, List[float]]] = None
    dominant_frequencies: List[float] = Field(default_factory=list)
    fault_indicators: Dict[str, Any] = Field(default_factory=dict)
    severity: SeverityLevel
    alarm_status: str
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime


class ThermalAnalysisRequest(BaseModel):
    """Schema for thermal analysis request"""
    equipment_id: int
    temperature_data: Dict[str, float] = Field(..., description="Temperature readings by location")
    ambient_temperature: Optional[float] = None
    operating_conditions: Optional[Dict[str, Any]] = None


class ThermalAnalysisResponse(BaseModel):
    """Schema for thermal analysis results"""
    analysis_id: int
    equipment_tag: str
    max_temperature: float
    avg_temperature: float
    temperature_distribution: Dict[str, float]
    hot_spots: List[Dict[str, Any]] = Field(default_factory=list)
    thermal_efficiency: float = Field(..., ge=0, le=100)
    cooling_effectiveness: float = Field(..., ge=0, le=100)
    severity: SeverityLevel
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime


class PredictiveAnalysisRequest(BaseModel):
    """Schema for predictive analysis request"""
    equipment_id: int
    historical_data: Dict[str, List[Any]] = Field(..., description="Historical sensor/operational data")
    prediction_horizon: int = Field(24, gt=0, description="Prediction horizon in hours")
    confidence_level: float = Field(0.95, ge=0.5, le=0.99, description="Confidence level")


class PredictiveAnalysisResponse(BaseModel):
    """Schema for predictive analysis results"""
    analysis_id: int
    equipment_tag: str
    failure_probability: float = Field(..., ge=0, le=1, description="Failure probability")
    time_to_failure: Optional[float] = Field(None, description="Estimated time to failure in hours")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence")
    risk_level: SeverityLevel
    contributing_factors: List[Dict[str, Any]] = Field(default_factory=list)
    predictions: Dict[str, List[float]] = Field(default_factory=dict, description="Predicted values")
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime


class RootCauseAnalysisRequest(BaseModel):
    """Schema for root cause analysis request"""
    equipment_id: int
    incident_time: datetime
    symptoms: List[str] = Field(..., description="Observed symptoms")
    sensor_data: Optional[Dict[str, Any]] = None
    maintenance_history: Optional[List[Dict[str, Any]]] = None


class RootCauseAnalysisResponse(BaseModel):
    """Schema for root cause analysis results"""
    analysis_id: int
    equipment_tag: str
    incident_time: datetime
    probable_causes: List[Dict[str, Any]] = Field(..., description="Ranked probable causes")
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    contributing_factors: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    corrective_actions: List[str] = Field(default_factory=list)
    preventive_measures: List[str] = Field(default_factory=list)
    timestamp: datetime


class TrendAnalysisRequest(BaseModel):
    """Schema for trend analysis request"""
    equipment_id: int
    metrics: List[str] = Field(..., description="Metrics to analyze trends")
    time_period: str = Field("30d", description="Time period for trend analysis")
    include_forecast: bool = Field(True, description="Include future trend forecast")


class TrendAnalysisResponse(BaseModel):
    """Schema for trend analysis results"""
    analysis_id: int
    equipment_tag: str
    time_period: str
    trends: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Trend data for each metric"
    )
    forecasts: Optional[Dict[str, List[float]]] = None
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    trend_summary: str
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime


class BatchAnalysisRequest(BaseModel):
    """Schema for batch analysis request"""
    equipment_ids: List[int] = Field(..., min_items=1, description="List of equipment IDs")
    analysis_type: AnalysisType
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Common parameters")


class BatchAnalysisResponse(BaseModel):
    """Schema for batch analysis response"""
    batch_id: str
    total_analyses: int
    completed: int
    failed: int
    running: int
    analysis_ids: List[int]
    status: str


class AnalysisComparisonRequest(BaseModel):
    """Schema for comparing analyses"""
    analysis_ids: List[int] = Field(..., min_items=2, max_items=10)
    comparison_metrics: List[str] = Field(default_factory=list)


class AnalysisComparisonResponse(BaseModel):
    """Schema for analysis comparison results"""
    analyses: List[AnalysisResponse]
    comparison_table: Dict[str, List[Any]]
    summary: Dict[str, Any]
    recommendations: List[str]