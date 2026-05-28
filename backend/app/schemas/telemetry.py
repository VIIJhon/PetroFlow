"""
Telemetry Schemas
Pydantic models for IoT telemetry data requests/responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SensorType(str, Enum):
    """Sensor type enumeration"""
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    VIBRATION = "vibration"
    FLOW = "flow"
    LEVEL = "level"
    SPEED = "speed"
    CURRENT = "current"
    VOLTAGE = "voltage"
    POWER = "power"
    TORQUE = "torque"
    POSITION = "position"
    HUMIDITY = "humidity"
    PH = "ph"
    CONDUCTIVITY = "conductivity"


class DataQuality(str, Enum):
    """Data quality enumeration"""
    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"
    MISSING = "missing"


class TelemetryBase(BaseModel):
    """Base telemetry schema"""
    sensor_type: SensorType = Field(..., description="Type of sensor")
    value: float = Field(..., description="Sensor reading value")
    unit: str = Field(..., description="Unit of measurement")
    quality: DataQuality = Field(DataQuality.GOOD, description="Data quality indicator")


class TelemetryCreate(TelemetryBase):
    """Schema for creating telemetry data"""
    equipment_id: int = Field(..., description="Equipment ID")
    timestamp: Optional[datetime] = Field(None, description="Measurement timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """Set timestamp to now if not provided"""
        return v or datetime.utcnow()
    
    @validator('value')
    def validate_value(cls, v, values):
        """Validate sensor value based on type"""
        sensor_type = values.get('sensor_type')
        
        if sensor_type == SensorType.TEMPERATURE:
            if v < -273.15 or v > 1000:
                raise ValueError("Temperature out of valid range")
        elif sensor_type == SensorType.PRESSURE:
            if v < 0:
                raise ValueError("Pressure cannot be negative")
        elif sensor_type == SensorType.VIBRATION:
            if v < 0:
                raise ValueError("Vibration cannot be negative")
        
        return v


class TelemetryResponse(TelemetryBase):
    """Schema for telemetry response"""
    id: int
    equipment_id: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class TelemetryListResponse(BaseModel):
    """Schema for telemetry list response"""
    telemetry: List[TelemetryResponse]
    total: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class TelemetryQuery(BaseModel):
    """Schema for querying telemetry data"""
    equipment_id: Optional[int] = None
    equipment_ids: Optional[List[int]] = None
    sensor_types: Optional[List[SensorType]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    quality: Optional[DataQuality] = None
    limit: int = Field(1000, ge=1, le=10000, description="Maximum number of records")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class TelemetryAggregation(str, Enum):
    """Aggregation method enumeration"""
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    STDDEV = "stddev"


class TelemetryAggregateRequest(BaseModel):
    """Schema for aggregated telemetry request"""
    equipment_id: int
    sensor_type: SensorType
    aggregation: TelemetryAggregation = Field(..., description="Aggregation method")
    interval: str = Field("1h", description="Time interval (1m, 5m, 1h, 1d)")
    start_time: datetime
    end_time: datetime


class TelemetryAggregateResponse(BaseModel):
    """Schema for aggregated telemetry response"""
    equipment_id: int
    sensor_type: SensorType
    aggregation: TelemetryAggregation
    interval: str
    data_points: List[Dict[str, Any]] = Field(..., description="Aggregated data points")
    statistics: Dict[str, float] = Field(default_factory=dict, description="Overall statistics")


class TelemetryStreamRequest(BaseModel):
    """Schema for real-time telemetry stream subscription"""
    equipment_ids: List[int] = Field(..., min_items=1, description="Equipment IDs to monitor")
    sensor_types: Optional[List[SensorType]] = None
    sample_rate: Optional[float] = Field(None, gt=0, description="Desired sample rate in Hz")


class TelemetryStreamResponse(BaseModel):
    """Schema for real-time telemetry stream data"""
    equipment_id: int
    sensor_type: SensorType
    value: float
    unit: str
    quality: DataQuality
    timestamp: datetime
    sequence_number: int = Field(..., description="Sequence number for ordering")


class TelemetryBatchCreate(BaseModel):
    """Schema for batch telemetry creation"""
    telemetry_data: List[TelemetryCreate] = Field(..., min_items=1, max_items=1000)


class TelemetryBatchResponse(BaseModel):
    """Schema for batch telemetry response"""
    total_submitted: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class TelemetryStatistics(BaseModel):
    """Schema for telemetry statistics"""
    equipment_id: int
    sensor_type: SensorType
    time_period: str
    count: int
    min_value: float
    max_value: float
    avg_value: float
    stddev: float
    quality_distribution: Dict[DataQuality, int]


class TelemetryAlert(BaseModel):
    """Schema for telemetry-based alerts"""
    equipment_id: int
    sensor_type: SensorType
    alert_type: str = Field(..., description="Type of alert (threshold, anomaly, etc.)")
    severity: str = Field(..., description="Alert severity (info, warning, critical)")
    message: str
    value: float
    threshold: Optional[float] = None
    timestamp: datetime


class TelemetryAlertCreate(BaseModel):
    """Schema for creating telemetry alerts"""
    equipment_id: int
    sensor_type: SensorType
    alert_type: str
    threshold_value: float
    comparison: str = Field(..., description="Comparison operator (gt, lt, eq, etc.)")
    enabled: bool = Field(True, description="Whether alert is enabled")


class TelemetryAlertResponse(TelemetryAlertCreate):
    """Schema for telemetry alert response"""
    id: int
    created_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = Field(0, description="Number of times alert has triggered")
    
    class Config:
        from_attributes = True


class TelemetryExportRequest(BaseModel):
    """Schema for exporting telemetry data"""
    equipment_id: int
    sensor_types: Optional[List[SensorType]] = None
    start_time: datetime
    end_time: datetime
    format: str = Field("csv", description="Export format (csv, json, parquet)")
    include_metadata: bool = Field(False, description="Include metadata in export")


class TelemetryExportResponse(BaseModel):
    """Schema for telemetry export response"""
    export_id: str
    status: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    record_count: int
    created_at: datetime


class TelemetryHealthCheck(BaseModel):
    """Schema for telemetry system health check"""
    equipment_id: int
    last_reading_time: Optional[datetime] = None
    readings_last_hour: int
    readings_last_day: int
    data_quality_score: float = Field(..., ge=0, le=100)
    sensor_status: Dict[SensorType, str] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)


class MQTTPublishRequest(BaseModel):
    """Schema for publishing data via MQTT"""
    equipment_id: int
    sensor_type: SensorType
    value: float
    unit: str
    facility_id: str = Field("REFINERY-A", description="Facility identifier")
    area: Optional[str] = None
    quality: DataQuality = DataQuality.GOOD


class MQTTSubscribeRequest(BaseModel):
    """Schema for MQTT subscription"""
    equipment_ids: Optional[List[int]] = None
    sensor_types: Optional[List[SensorType]] = None
    facility_id: Optional[str] = None
    qos: int = Field(1, ge=0, le=2, description="MQTT QoS level")


class MQTTStatusResponse(BaseModel):
    """Schema for MQTT connection status"""
    connected: bool
    broker: str
    port: int
    subscriptions: List[str]
    messages_received: int
    messages_published: int
    last_message_time: Optional[datetime] = None


class TelemetryValidationRequest(BaseModel):
    """Schema for validating telemetry data"""
    equipment_id: int
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime


class TelemetryValidationResponse(BaseModel):
    """Schema for telemetry validation response"""
    is_valid: bool
    quality: DataQuality
    issues: List[str] = Field(default_factory=list)
    corrected_value: Optional[float] = None
    recommendations: List[str] = Field(default_factory=list)