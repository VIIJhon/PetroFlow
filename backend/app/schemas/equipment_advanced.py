"""
Advanced Equipment Validation Schemas
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Advanced Pydantic schemas for equipment configuration validation with industry standards.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


class EquipmentType(str, Enum):
    """Equipment type enumeration"""
    PUMP = "pump"
    COMPRESSOR = "compressor"
    TURBINE = "turbine"
    VALVE = "valve"
    HEAT_EXCHANGER = "heat_exchanger"
    SEPARATOR = "separator"
    VESSEL = "vessel"
    MOTOR = "motor"
    GENERATOR = "generator"


class EquipmentStatus(str, Enum):
    """Equipment operational status"""
    RUNNING = "running"
    STOPPED = "stopped"
    STANDBY = "standby"
    MAINTENANCE = "maintenance"
    FAULT = "fault"
    UNKNOWN = "unknown"


class PumpType(str, Enum):
    """Pump type enumeration (API 610)"""
    CENTRIFUGAL = "centrifugal"
    POSITIVE_DISPLACEMENT = "positive_displacement"
    RECIPROCATING = "reciprocating"
    ROTARY = "rotary"


class CompressorType(str, Enum):
    """Compressor type enumeration (API 617/618)"""
    CENTRIFUGAL = "centrifugal"
    AXIAL = "axial"
    RECIPROCATING = "reciprocating"
    SCREW = "screw"
    ROTARY = "rotary"


class EquipmentParametersBase(BaseModel):
    """Base class for equipment parameters with common validations."""
    model_config = ConfigDict(validate_assignment=True, extra='forbid')
    
    rated_power_kw: Optional[float] = Field(None, gt=0, le=100000, description="Rated power in kW")
    rated_speed_rpm: Optional[float] = Field(None, gt=0, le=100000, description="Rated speed in RPM")
    design_pressure_pa: Optional[float] = Field(None, gt=0, le=1e9, description="Design pressure in Pa")
    design_temperature_k: Optional[float] = Field(None, gt=0, le=2000, description="Design temperature in K")
    
    @field_validator('design_temperature_k')
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is above absolute zero."""
        if v is not None and v < 0:
            raise ValueError('Temperature cannot be below absolute zero')
        return v


class PumpParameters(EquipmentParametersBase):
    """
    Pump-specific parameters with API 610 validation.
    
    Validates:
    - Flow rate ranges
    - Head ranges
    - NPSH requirements
    - Efficiency limits
    - Speed limits
    """
    
    pump_type: PumpType = Field(..., description="Type of pump")
    rated_flow_m3_s: float = Field(..., gt=0, le=10, description="Rated flow rate in m³/s")
    rated_head_m: float = Field(..., gt=0, le=10000, description="Rated head in meters")
    npsh_required_m: float = Field(..., gt=0, le=100, description="NPSH required in meters")
    impeller_diameter_mm: Optional[float] = Field(None, gt=0, le=5000, description="Impeller diameter in mm")
    number_of_stages: int = Field(1, ge=1, le=20, description="Number of pump stages")
    design_efficiency: float = Field(..., gt=0, le=1.0, description="Design efficiency (0-1)")
    min_flow_m3_s: Optional[float] = Field(None, gt=0, description="Minimum continuous flow in m³/s")
    max_flow_m3_s: Optional[float] = Field(None, gt=0, description="Maximum flow in m³/s")
    
    @field_validator('design_efficiency')
    @classmethod
    def validate_efficiency(cls, v: float) -> float:
        """Validate pump efficiency is realistic."""
        if v < 0.3:
            raise ValueError('Pump efficiency too low (<30%)')
        if v > 0.95:
            raise ValueError('Pump efficiency unrealistically high (>95%)')
        return v
    
    @model_validator(mode='after')
    def validate_flow_ranges(self) -> 'PumpParameters':
        """Validate flow rate ranges are consistent."""
        if self.min_flow_m3_s and self.min_flow_m3_s >= self.rated_flow_m3_s:
            raise ValueError('Minimum flow must be less than rated flow')
        
        if self.max_flow_m3_s and self.max_flow_m3_s <= self.rated_flow_m3_s:
            raise ValueError('Maximum flow must be greater than rated flow')
        
        # Typical range: min flow ~20% of rated, max flow ~120% of rated
        if self.min_flow_m3_s and self.min_flow_m3_s < 0.1 * self.rated_flow_m3_s:
            raise ValueError('Minimum flow too low (<10% of rated) - risk of recirculation')
        
        if self.max_flow_m3_s and self.max_flow_m3_s > 1.5 * self.rated_flow_m3_s:
            raise ValueError('Maximum flow too high (>150% of rated) - risk of cavitation')
        
        return self
    
    @model_validator(mode='after')
    def validate_npsh_margin(self) -> 'PumpParameters':
        """Validate NPSH requirements are reasonable."""
        # NPSH should typically be less than 50% of head
        if self.npsh_required_m > 0.5 * self.rated_head_m:
            raise ValueError(
                f'NPSH required ({self.npsh_required_m}m) is too high '
                f'relative to head ({self.rated_head_m}m)'
            )
        return self
    
    @model_validator(mode='after')
    def validate_specific_speed(self) -> 'PumpParameters':
        """Validate pump specific speed is within typical ranges."""
        if self.rated_speed_rpm and self.impeller_diameter_mm:
            # Calculate specific speed (dimensionless)
            # Ns = N * sqrt(Q) / H^0.75
            import math
            ns = (self.rated_speed_rpm * math.sqrt(self.rated_flow_m3_s) / 
                  (self.rated_head_m ** 0.75))
            
            # Typical ranges for centrifugal pumps: 10-200
            if self.pump_type == PumpType.CENTRIFUGAL:
                if ns < 5 or ns > 300:
                    raise ValueError(
                        f'Specific speed ({ns:.1f}) outside typical range for centrifugal pumps'
                    )
        
        return self


class CompressorParameters(EquipmentParametersBase):
    """
    Compressor-specific parameters with API 617/618 validation.
    
    Validates:
    - Compression ratio limits
    - Polytropic efficiency
    - Surge margin
    - Speed limits
    """
    
    compressor_type: CompressorType = Field(..., description="Type of compressor")
    rated_flow_m3_s: float = Field(..., gt=0, le=100, description="Rated flow rate in m³/s")
    suction_pressure_pa: float = Field(..., gt=0, le=1e8, description="Suction pressure in Pa")
    discharge_pressure_pa: float = Field(..., gt=0, le=1e9, description="Discharge pressure in Pa")
    polytropic_efficiency: float = Field(..., gt=0, le=1.0, description="Polytropic efficiency (0-1)")
    number_of_stages: int = Field(1, ge=1, le=10, description="Number of compressor stages")
    surge_flow_m3_s: Optional[float] = Field(None, gt=0, description="Surge flow rate in m³/s")
    max_flow_m3_s: Optional[float] = Field(None, gt=0, description="Maximum flow in m³/s")
    
    @field_validator('polytropic_efficiency')
    @classmethod
    def validate_efficiency(cls, v: float) -> float:
        """Validate compressor efficiency is realistic."""
        if v < 0.5:
            raise ValueError('Compressor efficiency too low (<50%)')
        if v > 0.92:
            raise ValueError('Compressor efficiency unrealistically high (>92%)')
        return v
    
    @model_validator(mode='after')
    def validate_compression_ratio(self) -> 'CompressorParameters':
        """Validate compression ratio is within limits."""
        compression_ratio = self.discharge_pressure_pa / self.suction_pressure_pa
        
        # Overall compression ratio limits
        if compression_ratio < 1.05:
            raise ValueError(f'Compression ratio too low: {compression_ratio:.2f}')
        
        if compression_ratio > 20:
            raise ValueError(
                f'Overall compression ratio too high: {compression_ratio:.2f} '
                f'(typical max ~20 for multi-stage)'
            )
        
        # Per-stage compression ratio (API 617)
        if self.number_of_stages > 0:
            per_stage_ratio = compression_ratio ** (1 / self.number_of_stages)
            
            if self.compressor_type == CompressorType.CENTRIFUGAL:
                if per_stage_ratio > 2.5:
                    raise ValueError(
                        f'Per-stage compression ratio too high: {per_stage_ratio:.2f} '
                        f'(typical max 2.5 for centrifugal)'
                    )
            elif self.compressor_type == CompressorType.RECIPROCATING:
                if per_stage_ratio > 5.0:
                    raise ValueError(
                        f'Per-stage compression ratio too high: {per_stage_ratio:.2f} '
                        f'(typical max 5.0 for reciprocating)'
                    )
        
        return self
    
    @model_validator(mode='after')
    def validate_surge_margin(self) -> 'CompressorParameters':
        """Validate surge margin is adequate."""
        if self.surge_flow_m3_s:
            if self.surge_flow_m3_s >= self.rated_flow_m3_s:
                raise ValueError('Surge flow must be less than rated flow')
            
            # Typical surge margin: 10-20% below rated flow
            surge_margin = (self.rated_flow_m3_s - self.surge_flow_m3_s) / self.rated_flow_m3_s
            
            if surge_margin < 0.05:
                raise ValueError(
                    f'Surge margin too small: {surge_margin*100:.1f}% '
                    f'(typical minimum 10%)'
                )
        
        return self


class TurbineParameters(EquipmentParametersBase):
    """
    Turbine-specific parameters with API 611/612 validation.
    
    Validates:
    - Expansion ratio
    - Efficiency
    - Speed limits
    - Temperature limits
    """
    
    turbine_type: str = Field(..., description="Type of turbine (steam, gas, etc.)")
    rated_power_output_kw: float = Field(..., gt=0, le=500000, description="Rated power output in kW")
    inlet_pressure_pa: float = Field(..., gt=0, le=1e8, description="Inlet pressure in Pa")
    outlet_pressure_pa: float = Field(..., gt=0, le=1e8, description="Outlet pressure in Pa")
    inlet_temperature_k: float = Field(..., gt=273, le=2000, description="Inlet temperature in K")
    isentropic_efficiency: float = Field(..., gt=0, le=1.0, description="Isentropic efficiency (0-1)")
    number_of_stages: int = Field(1, ge=1, le=50, description="Number of turbine stages")
    
    @field_validator('isentropic_efficiency')
    @classmethod
    def validate_efficiency(cls, v: float) -> float:
        """Validate turbine efficiency is realistic."""
        if v < 0.6:
            raise ValueError('Turbine efficiency too low (<60%)')
        if v > 0.95:
            raise ValueError('Turbine efficiency unrealistically high (>95%)')
        return v
    
    @model_validator(mode='after')
    def validate_expansion_ratio(self) -> 'TurbineParameters':
        """Validate expansion ratio is within limits."""
        if self.outlet_pressure_pa >= self.inlet_pressure_pa:
            raise ValueError(
                f'Outlet pressure ({self.outlet_pressure_pa}) must be less than '
                f'inlet pressure ({self.inlet_pressure_pa})'
            )
        
        expansion_ratio = self.inlet_pressure_pa / self.outlet_pressure_pa
        
        # Typical expansion ratio limits
        if expansion_ratio > 100:
            raise ValueError(
                f'Expansion ratio too high: {expansion_ratio:.1f} '
                f'(typical max ~100 for multi-stage)'
            )
        
        return self
    
    @model_validator(mode='after')
    def validate_temperature_drop(self) -> 'TurbineParameters':
        """Validate temperature drop is reasonable."""
        # For expansion, temperature should drop
        # Rough estimate: ΔT ≈ T1 * (1 - (P2/P1)^((γ-1)/γ))
        # For air/gas: γ ≈ 1.4
        import math
        
        pressure_ratio = self.outlet_pressure_pa / self.inlet_pressure_pa
        gamma = 1.4  # Typical for air/gas
        
        expected_temp_ratio = pressure_ratio ** ((gamma - 1) / gamma)
        expected_outlet_temp = self.inlet_temperature_k * expected_temp_ratio
        
        # Check if outlet temperature would be too low
        if expected_outlet_temp < 200:  # Below typical minimum
            raise ValueError(
                f'Expected outlet temperature too low: {expected_outlet_temp:.1f}K '
                f'(check expansion ratio)'
            )
        
        return self


class ValveParameters(EquipmentParametersBase):
    """
    Valve-specific parameters with validation.
    
    Validates:
    - Cv coefficient
    - Pressure rating
    - Position limits
    """
    
    valve_type: str = Field(..., description="Type of valve (control, isolation, etc.)")
    cv_coefficient: float = Field(..., gt=0, le=10000, description="Flow coefficient Cv")
    rated_pressure_pa: float = Field(..., gt=0, le=1e9, description="Rated pressure in Pa")
    max_pressure_drop_pa: float = Field(..., gt=0, le=1e8, description="Max pressure drop in Pa")
    actuator_type: Optional[str] = Field(None, description="Actuator type (pneumatic, electric, etc.)")
    fail_position: Optional[str] = Field(None, description="Fail position (open, closed)")
    
    @model_validator(mode='after')
    def validate_pressure_drop(self) -> 'ValveParameters':
        """Validate pressure drop is within valve rating."""
        if self.max_pressure_drop_pa > self.rated_pressure_pa:
            raise ValueError(
                f'Max pressure drop ({self.max_pressure_drop_pa}) exceeds '
                f'valve rating ({self.rated_pressure_pa})'
            )
        
        # Check for cavitation risk (pressure drop > 50% of upstream pressure)
        if self.max_pressure_drop_pa > 0.5 * self.rated_pressure_pa:
            # Add warning in metadata (would need to be handled by caller)
            pass
        
        return self


class EquipmentConfiguration(BaseModel):
    """
    Complete equipment configuration with validation.
    
    Validates:
    - Equipment type matches parameters
    - Operating limits
    - Safety margins
    """
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3, max_length=100)
    equipment_type: EquipmentType
    equipment_name: str = Field(..., min_length=1, max_length=200)
    parameters: Union[
        PumpParameters,
        CompressorParameters,
        TurbineParameters,
        ValveParameters,
        EquipmentParametersBase
    ]
    status: EquipmentStatus = EquipmentStatus.UNKNOWN
    location: Optional[str] = Field(None, max_length=200)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    installation_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        v = v.upper()
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            raise ValueError('Equipment ID contains invalid characters')
        return v
    
    @model_validator(mode='after')
    def validate_equipment_type_matches_parameters(self) -> 'EquipmentConfiguration':
        """Validate equipment type matches parameter type."""
        type_param_map = {
            EquipmentType.PUMP: PumpParameters,
            EquipmentType.COMPRESSOR: CompressorParameters,
            EquipmentType.TURBINE: TurbineParameters,
            EquipmentType.VALVE: ValveParameters
        }
        
        expected_param_type = type_param_map.get(self.equipment_type)
        
        if expected_param_type and not isinstance(self.parameters, expected_param_type):
            raise ValueError(
                f'Equipment type {self.equipment_type} requires '
                f'{expected_param_type.__name__} parameters'
            )
        
        return self
    
    @model_validator(mode='after')
    def validate_maintenance_dates(self) -> 'EquipmentConfiguration':
        """Validate maintenance dates are logical."""
        if self.last_maintenance_date and self.next_maintenance_date:
            if self.next_maintenance_date <= self.last_maintenance_date:
                raise ValueError(
                    'Next maintenance date must be after last maintenance date'
                )
        
        if self.installation_date:
            now = datetime.utcnow()
            if self.installation_date > now:
                raise ValueError('Installation date cannot be in the future')
            
            if self.last_maintenance_date and self.last_maintenance_date < self.installation_date:
                raise ValueError(
                    'Last maintenance date cannot be before installation date'
                )
        
        return self


class OperatingLimits(BaseModel):
    """Operating limits for equipment with validation."""
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3)
    parameter_name: str = Field(..., min_length=1)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    alarm_low: Optional[float] = None
    alarm_high: Optional[float] = None
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    unit: str = Field(..., min_length=1)
    
    @model_validator(mode='after')
    def validate_limit_hierarchy(self) -> 'OperatingLimits':
        """Validate limit hierarchy is logical."""
        # Check min/max relationship
        if self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                raise ValueError('min_value must be less than max_value')
        
        # Check alarm/warning hierarchy
        if self.alarm_low is not None and self.warning_low is not None:
            if self.alarm_low >= self.warning_low:
                raise ValueError('alarm_low must be less than warning_low')
        
        if self.alarm_high is not None and self.warning_high is not None:
            if self.alarm_high <= self.warning_high:
                raise ValueError('alarm_high must be greater than warning_high')
        
        # Check limits are within min/max
        if self.min_value is not None:
            if self.alarm_low is not None and self.alarm_low < self.min_value:
                raise ValueError('alarm_low cannot be below min_value')
            if self.warning_low is not None and self.warning_low < self.min_value:
                raise ValueError('warning_low cannot be below min_value')
        
        if self.max_value is not None:
            if self.alarm_high is not None and self.alarm_high > self.max_value:
                raise ValueError('alarm_high cannot exceed max_value')
            if self.warning_high is not None and self.warning_high > self.max_value:
                raise ValueError('warning_high cannot exceed max_value')
        
        return self