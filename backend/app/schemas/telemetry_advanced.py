"""
Advanced Telemetry Schemas with Pydantic v2 Validators
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Advanced Pydantic schemas with field validators, model validators, and equipment-specific validations.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


class EquipmentCategory(str, Enum):
    """Equipment category enumeration"""
    PUMP = "pump"
    COMPRESSOR = "compressor"
    TURBINE = "turbine"
    VALVE = "valve"
    HEAT_EXCHANGER = "heat_exchanger"
    SEPARATOR = "separator"
    VESSEL = "vessel"
    MOTOR = "motor"


class SignalQuality(str, Enum):
    """Signal quality enumeration"""
    EXCELLENT = "excellent"  # >95%
    GOOD = "good"  # 80-95%
    FAIR = "fair"  # 60-80%
    POOR = "poor"  # 40-60%
    BAD = "bad"  # <40%


class UnitSystem(str, Enum):
    """Unit system enumeration"""
    SI = "si"
    IMPERIAL = "imperial"
    MIXED = "mixed"


class TelemetryPoint(BaseModel):
    """
    Advanced telemetry point with comprehensive validation.
    
    Validates:
    - Equipment ID format
    - Physical parameter ranges
    - Unit consistency
    - Timestamp validity
    - Quality thresholds
    """
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3, max_length=100, description="Equipment identifier")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    parameters: Dict[str, float] = Field(..., min_length=1, description="Parameter values")
    units: Dict[str, str] = Field(..., min_length=1, description="Parameter units")
    quality: float = Field(1.0, ge=0.0, le=1.0, description="Data quality score")
    source: str = Field("unknown", max_length=50, description="Data source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        if not v or len(v) < 3:
            raise ValueError('Equipment ID must be at least 3 characters')
        
        # Convert to uppercase for consistency
        v = v.upper()
        
        # Check for valid characters (alphanumeric, dash, underscore)
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            raise ValueError('Equipment ID contains invalid characters')
        
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Validate timestamp is not in future and not too old."""
        now = datetime.utcnow()
        
        # Check if timestamp is in future
        if v > now:
            raise ValueError('Timestamp cannot be in the future')
        
        # Check if timestamp is too old (more than 1 year)
        max_age_days = 365
        if (now - v).days > max_age_days:
            raise ValueError(f'Timestamp is too old (>{max_age_days} days)')
        
        return v
    
    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate physical parameter ranges."""
        for param, value in v.items():
            param_lower = param.lower()
            
            # Pressure validation (Pa)
            if 'pressure' in param_lower or 'press' in param_lower:
                if value < 0:
                    raise ValueError(f'Pressure cannot be negative: {param}={value}')
                if value > 1e9:  # 1 GPa max
                    raise ValueError(f'Pressure exceeds maximum: {param}={value}')
            
            # Temperature validation (K or C)
            elif 'temperature' in param_lower or 'temp' in param_lower:
                # Assume Kelvin if > 200, Celsius otherwise
                if value > 200:  # Likely Kelvin
                    if value < 0:
                        raise ValueError(f'Temperature (K) cannot be negative: {param}={value}')
                    if value > 2000:
                        raise ValueError(f'Temperature exceeds maximum: {param}={value}')
                else:  # Likely Celsius
                    if value < -273.15:
                        raise ValueError(f'Temperature below absolute zero: {param}={value}')
                    if value > 2000:
                        raise ValueError(f'Temperature exceeds maximum: {param}={value}')
            
            # Flow rate validation
            elif 'flow' in param_lower or 'rate' in param_lower:
                if value < 0:
                    raise ValueError(f'Flow rate cannot be negative: {param}={value}')
                if value > 1e6:  # Reasonable max
                    raise ValueError(f'Flow rate exceeds maximum: {param}={value}')
            
            # Vibration validation
            elif 'vibration' in param_lower or 'vib' in param_lower:
                if value < 0:
                    raise ValueError(f'Vibration cannot be negative: {param}={value}')
                if value > 1000:  # mm/s max
                    raise ValueError(f'Vibration exceeds maximum: {param}={value}')
            
            # Speed validation (RPM)
            elif 'speed' in param_lower or 'rpm' in param_lower:
                if value < 0:
                    raise ValueError(f'Speed cannot be negative: {param}={value}')
                if value > 100000:  # 100k RPM max
                    raise ValueError(f'Speed exceeds maximum: {param}={value}')
            
            # Power validation
            elif 'power' in param_lower:
                if value < 0:
                    raise ValueError(f'Power cannot be negative: {param}={value}')
                if value > 1e9:  # 1 GW max
                    raise ValueError(f'Power exceeds maximum: {param}={value}')
            
            # Check for NaN or Inf
            if not (-1e308 < value < 1e308):
                raise ValueError(f'Invalid numeric value: {param}={value}')
        
        return v
    
    @model_validator(mode='after')
    def validate_unit_consistency(self) -> 'TelemetryPoint':
        """Validate that all parameters have corresponding units."""
        for param in self.parameters:
            if param not in self.units:
                raise ValueError(f'Missing unit for parameter: {param}')
        
        # Check for extra units
        for unit_param in self.units:
            if unit_param not in self.parameters:
                raise ValueError(f'Unit specified for non-existent parameter: {unit_param}')
        
        return self
    
    @model_validator(mode='after')
    def validate_quality_threshold(self) -> 'TelemetryPoint':
        """Validate quality meets minimum threshold for critical parameters."""
        critical_params = ['pressure', 'temperature', 'flow']
        
        for param in self.parameters:
            param_lower = param.lower()
            if any(critical in param_lower for critical in critical_params):
                if self.quality < 0.5:
                    raise ValueError(
                        f'Quality too low ({self.quality}) for critical parameter: {param}'
                    )
        
        return self


class PumpTelemetry(TelemetryPoint):
    """Telemetry schema specific to pumps with API 610 validation."""
    
    equipment_category: EquipmentCategory = Field(
        EquipmentCategory.PUMP,
        description="Equipment category"
    )
    
    @field_validator('parameters')
    @classmethod
    def validate_pump_parameters(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate pump-specific parameters."""
        # Check for required pump parameters
        required_params = ['suction_pressure', 'discharge_pressure', 'flow_rate']
        param_keys_lower = [k.lower() for k in v.keys()]
        
        for required in required_params:
            if not any(required in key for key in param_keys_lower):
                raise ValueError(f'Missing required pump parameter: {required}')
        
        # Validate differential pressure
        suction = None
        discharge = None
        
        for param, value in v.items():
            param_lower = param.lower()
            if 'suction' in param_lower and 'pressure' in param_lower:
                suction = value
            elif 'discharge' in param_lower and 'pressure' in param_lower:
                discharge = value
        
        if suction is not None and discharge is not None:
            if discharge <= suction:
                raise ValueError(
                    f'Discharge pressure ({discharge}) must be greater than '
                    f'suction pressure ({suction})'
                )
            
            # Check for reasonable differential
            diff = discharge - suction
            if diff > 1e8:  # 100 MPa max differential
                raise ValueError(f'Differential pressure too high: {diff}')
        
        return v
    
    @model_validator(mode='after')
    def validate_pump_operating_point(self) -> 'PumpTelemetry':
        """Validate pump is operating within reasonable envelope."""
        # Get flow rate
        flow_rate = None
        for param, value in self.parameters.items():
            if 'flow' in param.lower():
                flow_rate = value
                break
        
        if flow_rate is not None:
            # Check for minimum flow (prevent deadheading)
            if flow_rate < 0.01:  # Very low flow
                if self.quality > 0.8:  # Only warn if data quality is good
                    self.metadata['warning'] = 'Flow rate very low - check for deadheading'
        
        return self


class CompressorTelemetry(TelemetryPoint):
    """Telemetry schema specific to compressors with API 617 validation."""
    
    equipment_category: EquipmentCategory = Field(
        EquipmentCategory.COMPRESSOR,
        description="Equipment category"
    )
    
    @field_validator('parameters')
    @classmethod
    def validate_compressor_parameters(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate compressor-specific parameters."""
        # Check for required compressor parameters
        required_params = ['suction_pressure', 'discharge_pressure', 'suction_temperature']
        param_keys_lower = [k.lower() for k in v.keys()]
        
        for required in required_params:
            if not any(required in key for key in param_keys_lower):
                raise ValueError(f'Missing required compressor parameter: {required}')
        
        # Validate compression ratio
        suction_p = None
        discharge_p = None
        
        for param, value in v.items():
            param_lower = param.lower()
            if 'suction' in param_lower and 'pressure' in param_lower:
                suction_p = value
            elif 'discharge' in param_lower and 'pressure' in param_lower:
                discharge_p = value
        
        if suction_p is not None and discharge_p is not None:
            if suction_p <= 0:
                raise ValueError('Suction pressure must be positive')
            
            compression_ratio = discharge_p / suction_p
            
            if compression_ratio < 1.0:
                raise ValueError(
                    f'Invalid compression ratio: {compression_ratio} '
                    f'(discharge must be > suction)'
                )
            
            # Check for reasonable compression ratio (API 617)
            if compression_ratio > 10.0:
                raise ValueError(
                    f'Compression ratio too high: {compression_ratio} '
                    f'(typical max ~10 for single stage)'
                )
        
        return v
    
    @model_validator(mode='after')
    def validate_surge_conditions(self) -> 'CompressorTelemetry':
        """Check for potential surge conditions."""
        # Get flow rate
        flow_rate = None
        for param, value in self.parameters.items():
            if 'flow' in param.lower():
                flow_rate = value
                break
        
        if flow_rate is not None and flow_rate < 0.1:
            self.metadata['warning'] = 'Low flow - potential surge condition'
        
        return self


class TurbineTelemetry(TelemetryPoint):
    """Telemetry schema specific to turbines with API 611/612 validation."""
    
    equipment_category: EquipmentCategory = Field(
        EquipmentCategory.TURBINE,
        description="Equipment category"
    )
    
    @field_validator('parameters')
    @classmethod
    def validate_turbine_parameters(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate turbine-specific parameters."""
        # Check for required turbine parameters
        required_params = ['speed', 'inlet_pressure', 'inlet_temperature']
        param_keys_lower = [k.lower() for k in v.keys()]
        
        for required in required_params:
            if not any(required in key for key in param_keys_lower):
                raise ValueError(f'Missing required turbine parameter: {required}')
        
        # Validate speed limits
        speed = None
        for param, value in v.items():
            if 'speed' in param.lower() or 'rpm' in param.lower():
                speed = value
                break
        
        if speed is not None:
            # Typical turbine speed limits
            if speed > 50000:  # 50k RPM max for most turbines
                raise ValueError(f'Turbine speed exceeds typical maximum: {speed} RPM')
        
        return v
    
    @model_validator(mode='after')
    def validate_turbine_efficiency(self) -> 'TurbineTelemetry':
        """Validate turbine operating efficiency."""
        # Get inlet and outlet conditions
        inlet_p = None
        outlet_p = None
        
        for param, value in self.parameters.items():
            param_lower = param.lower()
            if 'inlet' in param_lower and 'pressure' in param_lower:
                inlet_p = value
            elif 'outlet' in param_lower and 'pressure' in param_lower:
                outlet_p = value
        
        if inlet_p is not None and outlet_p is not None:
            if outlet_p >= inlet_p:
                raise ValueError(
                    f'Turbine outlet pressure ({outlet_p}) must be less than '
                    f'inlet pressure ({inlet_p})'
                )
        
        return self


class ValveTelemetry(TelemetryPoint):
    """Telemetry schema specific to control valves."""
    
    equipment_category: EquipmentCategory = Field(
        EquipmentCategory.VALVE,
        description="Equipment category"
    )
    
    @field_validator('parameters')
    @classmethod
    def validate_valve_parameters(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate valve-specific parameters."""
        # Check for valve position
        position = None
        for param, value in v.items():
            if 'position' in param.lower() or 'opening' in param.lower():
                position = value
                break
        
        if position is not None:
            if not (0 <= position <= 100):
                raise ValueError(f'Valve position must be 0-100%: {position}')
        
        return v
    
    @model_validator(mode='after')
    def validate_valve_operation(self) -> 'ValveTelemetry':
        """Validate valve operating conditions."""
        # Check for cavitation risk
        upstream_p = None
        downstream_p = None
        
        for param, value in self.parameters.items():
            param_lower = param.lower()
            if 'upstream' in param_lower and 'pressure' in param_lower:
                upstream_p = value
            elif 'downstream' in param_lower and 'pressure' in param_lower:
                downstream_p = value
        
        if upstream_p is not None and downstream_p is not None:
            pressure_drop = upstream_p - downstream_p
            
            # Check for excessive pressure drop (cavitation risk)
            if pressure_drop > 0.5 * upstream_p:
                self.metadata['warning'] = 'High pressure drop - cavitation risk'
        
        return self


class TelemetryBatch(BaseModel):
    """Batch of telemetry points with validation."""
    model_config = ConfigDict(validate_assignment=True)
    
    points: List[TelemetryPoint] = Field(..., min_length=1, max_length=10000)
    batch_id: Optional[str] = Field(None, max_length=100)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('points')
    @classmethod
    def validate_batch_consistency(cls, v: List[TelemetryPoint]) -> List[TelemetryPoint]:
        """Validate batch consistency."""
        if not v:
            raise ValueError('Batch cannot be empty')
        
        # Check for duplicate timestamps per equipment
        equipment_timestamps = {}
        for point in v:
            if point.equipment_id not in equipment_timestamps:
                equipment_timestamps[point.equipment_id] = set()
            
            if point.timestamp in equipment_timestamps[point.equipment_id]:
                raise ValueError(
                    f'Duplicate timestamp for equipment {point.equipment_id}: '
                    f'{point.timestamp}'
                )
            
            equipment_timestamps[point.equipment_id].add(point.timestamp)
        
        return v
    
    @model_validator(mode='after')
    def validate_batch_time_range(self) -> 'TelemetryBatch':
        """Validate batch time range is reasonable."""
        if len(self.points) > 1:
            timestamps = [p.timestamp for p in self.points]
            time_span = (max(timestamps) - min(timestamps)).total_seconds()
            
            # Check if time span is too large (>24 hours)
            if time_span > 86400:
                raise ValueError(
                    f'Batch time span too large: {time_span/3600:.1f} hours '
                    f'(max 24 hours)'
                )
        
        return self


class TelemetryValidationResult(BaseModel):
    """Result of telemetry validation."""
    model_config = ConfigDict(validate_assignment=True)
    
    is_valid: bool
    equipment_id: str
    timestamp: datetime
    quality_score: float = Field(ge=0.0, le=1.0)
    signal_quality: SignalQuality
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    corrected_values: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def determine_signal_quality(self) -> 'TelemetryValidationResult':
        """Determine signal quality from quality score."""
        if self.quality_score >= 0.95:
            self.signal_quality = SignalQuality.EXCELLENT
        elif self.quality_score >= 0.80:
            self.signal_quality = SignalQuality.GOOD
        elif self.quality_score >= 0.60:
            self.signal_quality = SignalQuality.FAIR
        elif self.quality_score >= 0.40:
            self.signal_quality = SignalQuality.POOR
        else:
            self.signal_quality = SignalQuality.BAD
        
        return self


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection."""
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str
    parameter: str
    timestamp: datetime
    value: float
    expected_value: float
    deviation: float
    z_score: float = Field(ge=0.0)
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    confidence: float = Field(ge=0.0, le=1.0)
    description: Optional[str] = None
    
    @model_validator(mode='after')
    def generate_description(self) -> 'AnomalyDetectionResult':
        """Generate human-readable description."""
        if not self.description:
            self.description = (
                f"{self.parameter} anomaly detected: "
                f"value={self.value:.2f}, expected={self.expected_value:.2f}, "
                f"deviation={self.deviation:.2f} ({self.severity} severity)"
            )
        return self


class TelemetryAggregationRequest(BaseModel):
    """Request for telemetry aggregation."""
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3)
    parameters: List[str] = Field(..., min_length=1)
    start_time: datetime
    end_time: datetime
    aggregation_window: str = Field(
        "1h",
        pattern="^[0-9]+(s|m|h|d)$",
        description="Aggregation window (e.g., 1s, 5m, 1h, 1d)"
    )
    aggregation_functions: List[str] = Field(
        default_factory=lambda: ["mean", "min", "max", "std"],
        description="Aggregation functions to apply"
    )
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: datetime, info) -> datetime:
        """Validate time range is valid."""
        start_time = info.data.get('start_time')
        if start_time and v <= start_time:
            raise ValueError('end_time must be after start_time')
        
        # Check if time range is reasonable (max 1 year)
        if start_time and (v - start_time).days > 365:
            raise ValueError('Time range cannot exceed 1 year')
        
        return v
    
    @field_validator('aggregation_functions')
    @classmethod
    def validate_aggregation_functions(cls, v: List[str]) -> List[str]:
        """Validate aggregation functions are supported."""
        valid_functions = ["mean", "median", "min", "max", "sum", "std", "count", "p95", "p99"]
        
        for func in v:
            if func not in valid_functions:
                raise ValueError(
                    f'Invalid aggregation function: {func}. '
                    f'Valid options: {", ".join(valid_functions)}'
                )
        
        return v


class TelemetryStreamConfig(BaseModel):
    """Configuration for telemetry streaming."""
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_ids: List[str] = Field(..., min_length=1, max_length=100)
    parameters: Optional[List[str]] = None
    sample_rate_hz: float = Field(1.0, gt=0.0, le=1000.0)
    buffer_size: int = Field(1000, ge=100, le=100000)
    enable_validation: bool = True
    enable_anomaly_detection: bool = True
    quality_threshold: float = Field(0.5, ge=0.0, le=1.0)
    
    @field_validator('equipment_ids')
    @classmethod
    def validate_equipment_ids(cls, v: List[str]) -> List[str]:
        """Validate equipment IDs."""
        # Remove duplicates
        unique_ids = list(set(v))
        
        # Validate format
        for eq_id in unique_ids:
            if len(eq_id) < 3:
                raise ValueError(f'Invalid equipment ID: {eq_id}')
        
        return unique_ids