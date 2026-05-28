"""
API 617 Standard - Axial and Centrifugal Compressors for Petroleum, Chemical and Gas Industry Services
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements operating limits and validation rules per API 617 8th Edition.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import math

from . import (
    IndustryStandard,
    EquipmentType,
    UnitSystem,
    OperatingLimits,
    StandardFactory
)


class CompressorType(Enum):
    """API 617 compressor classifications."""
    CENTRIFUGAL_SINGLE_STAGE = "centrifugal_single_stage"
    CENTRIFUGAL_MULTISTAGE = "centrifugal_multistage"
    AXIAL_SINGLE_STAGE = "axial_single_stage"
    AXIAL_MULTISTAGE = "axial_multistage"
    INTEGRALLY_GEARED = "integrally_geared"


class CompressorService(Enum):
    """Service classifications."""
    AIR = "air"
    NATURAL_GAS = "natural_gas"
    PROCESS_GAS = "process_gas"
    REFRIGERATION = "refrigeration"
    VAPOR_RECOVERY = "vapor_recovery"


class API617Standard(IndustryStandard):
    """
    API 617 Standard implementation for centrifugal and axial compressors.
    
    Provides operating limits for:
    - Discharge pressure and temperature
    - Suction pressure and temperature
    - Differential pressure
    - Flow rate
    - Speed (RPM)
    - Polytropic efficiency
    - Surge margin
    - Vibration
    - Bearing temperature
    - Seal gas pressure
    - Thrust bearing load
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        super().__init__(unit_system)
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return "API 617"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [EquipmentType.COMPRESSOR_CENTRIFUGAL]
    
    def _initialize_limits(self):
        """Initialize operating limits based on unit system."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in SI units."""
        return {
            "compressor_centrifugal": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=500.0,  # bar
                    warning_max=450.0,
                    alarm_max=475.0,
                    unit="bar"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=0.1,  # bar (near vacuum)
                    max_value=200.0,
                    warning_min=0.5,
                    alarm_min=0.2,
                    unit="bar"
                ),
                "discharge_temperature": OperatingLimits(
                    min_value=-50.0,  # °C
                    max_value=250.0,
                    warning_max=220.0,
                    alarm_max=235.0,
                    unit="°C"
                ),
                "suction_temperature": OperatingLimits(
                    min_value=-50.0,  # °C
                    max_value=150.0,
                    warning_max=130.0,
                    alarm_max=140.0,
                    unit="°C"
                ),
                "differential_pressure": OperatingLimits(
                    min_value=0.0,  # bar
                    max_value=400.0,
                    warning_max=360.0,
                    alarm_max=380.0,
                    unit="bar"
                ),
                "flow_rate": OperatingLimits(
                    min_value=0.0,  # m³/h at standard conditions
                    max_value=500000.0,
                    warning_min=5000.0,  # Surge margin
                    alarm_min=2500.0,
                    unit="m³/h"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,  # RPM
                    max_value=30000.0,  # High-speed compressors
                    warning_max=28500.0,
                    alarm_max=29250.0,
                    unit="RPM"
                ),
                "polytropic_efficiency": OperatingLimits(
                    min_value=0.0,  # %
                    max_value=100.0,
                    warning_min=75.0,
                    alarm_min=70.0,
                    unit="%"
                ),
                "surge_margin": OperatingLimits(
                    min_value=0.0,  # %
                    max_value=100.0,
                    warning_min=10.0,
                    alarm_min=5.0,
                    unit="%"
                ),
                "vibration_displacement": OperatingLimits(
                    min_value=0.0,  # μm peak-to-peak
                    max_value=75.0,
                    warning_max=50.0,
                    alarm_max=65.0,
                    unit="μm"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,  # mm/s RMS
                    max_value=11.2,
                    warning_max=7.1,
                    alarm_max=11.2,
                    unit="mm/s"
                ),
                "bearing_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=120.0,
                    warning_max=100.0,
                    alarm_max=110.0,
                    unit="°C"
                ),
                "seal_gas_pressure": OperatingLimits(
                    min_value=0.5,  # bar above discharge
                    max_value=50.0,
                    warning_min=1.0,
                    alarm_min=0.7,
                    unit="bar"
                ),
                "thrust_bearing_load": OperatingLimits(
                    min_value=0.0,  # kN
                    max_value=500.0,
                    warning_max=450.0,
                    alarm_max=475.0,
                    unit="kN"
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # kW
                    max_value=100000.0,
                    warning_max=90000.0,
                    alarm_max=95000.0,
                    unit="kW"
                ),
                "compression_ratio": OperatingLimits(
                    min_value=1.0,
                    max_value=10.0,
                    warning_max=9.0,
                    alarm_max=9.5,
                    unit=""
                ),
                "mach_number": OperatingLimits(
                    min_value=0.0,
                    max_value=0.9,
                    warning_max=0.8,
                    alarm_max=0.85,
                    unit=""
                ),
            }
        }
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in Imperial units."""
        return {
            "compressor_centrifugal": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=7250.0,  # psi
                    warning_max=6525.0,
                    alarm_max=6888.0,
                    unit="psi"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=1.5,  # psi
                    max_value=2900.0,
                    warning_min=7.0,
                    alarm_min=3.0,
                    unit="psi"
                ),
                "discharge_temperature": OperatingLimits(
                    min_value=-58.0,  # °F
                    max_value=482.0,
                    warning_max=428.0,
                    alarm_max=455.0,
                    unit="°F"
                ),
                "flow_rate": OperatingLimits(
                    min_value=0.0,  # ACFM
                    max_value=300000.0,
                    warning_min=3000.0,
                    alarm_min=1500.0,
                    unit="ACFM"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,
                    max_value=30000.0,
                    warning_max=28500.0,
                    alarm_max=29250.0,
                    unit="RPM"
                ),
                "vibration_displacement": OperatingLimits(
                    min_value=0.0,  # mils peak-to-peak
                    max_value=3.0,
                    warning_max=2.0,
                    alarm_max=2.6,
                    unit="mils"
                ),
            }
        }
    
    def get_limits(self, equipment_type: EquipmentType, parameter: str) -> OperatingLimits:
        """
        Get operating limits for a specific parameter.
        
        Args:
            equipment_type: Type of compressor
            parameter: Parameter name
            
        Returns:
            OperatingLimits object
            
        Raises:
            ValueError: If equipment type or parameter not supported
        """
        equipment_key = equipment_type.value
        
        if equipment_key not in self._limits:
            raise ValueError(f"Equipment type {equipment_type} not supported by API 617")
        
        if parameter not in self._limits[equipment_key]:
            raise ValueError(f"Parameter {parameter} not defined for {equipment_type}")
        
        return self._limits[equipment_key][parameter]
    
    def calculate_surge_margin(
        self,
        current_flow: float,
        surge_flow: float
    ) -> float:
        """
        Calculate surge margin percentage.
        
        Surge margin = ((Current Flow - Surge Flow) / Surge Flow) * 100
        
        API 617 recommends minimum 10% surge margin for safe operation.
        
        Args:
            current_flow: Current operating flow rate
            surge_flow: Surge line flow rate at current conditions
            
        Returns:
            Surge margin percentage (positive is safe)
        """
        if surge_flow <= 0:
            return 0.0
        
        margin = ((current_flow - surge_flow) / surge_flow) * 100
        return margin
    
    def calculate_polytropic_efficiency(
        self,
        polytropic_head: float,
        actual_head: float
    ) -> float:
        """
        Calculate polytropic efficiency.
        
        η_p = (Polytropic Head / Actual Head) * 100
        
        Args:
            polytropic_head: Theoretical polytropic head (kJ/kg or BTU/lb)
            actual_head: Actual head developed (kJ/kg or BTU/lb)
            
        Returns:
            Polytropic efficiency percentage
        """
        if actual_head <= 0:
            return 0.0
        
        efficiency = (polytropic_head / actual_head) * 100
        return min(efficiency, 100.0)
    
    def calculate_compression_ratio(
        self,
        discharge_pressure: float,
        suction_pressure: float
    ) -> float:
        """
        Calculate compression ratio.
        
        Args:
            discharge_pressure: Discharge pressure (bar or psi)
            suction_pressure: Suction pressure (bar or psi)
            
        Returns:
            Compression ratio
        """
        if suction_pressure <= 0:
            return 0.0
        
        return discharge_pressure / suction_pressure
    
    def calculate_mach_number(
        self,
        tip_speed: float,
        speed_of_sound: float
    ) -> float:
        """
        Calculate impeller tip Mach number.
        
        Mach number should be < 0.9 to avoid shock losses.
        
        Args:
            tip_speed: Impeller tip speed (m/s or ft/s)
            speed_of_sound: Speed of sound in gas (m/s or ft/s)
            
        Returns:
            Mach number
        """
        if speed_of_sound <= 0:
            return 0.0
        
        return tip_speed / speed_of_sound
    
    def check_surge_condition(
        self,
        current_flow: float,
        surge_flow: float,
        min_margin_percent: float = 10.0
    ) -> Tuple[bool, float]:
        """
        Check if compressor is operating safely away from surge.
        
        Args:
            current_flow: Current flow rate
            surge_flow: Surge line flow rate
            min_margin_percent: Minimum acceptable surge margin
            
        Returns:
            Tuple of (is_safe, margin_percent)
        """
        margin = self.calculate_surge_margin(current_flow, surge_flow)
        is_safe = margin >= min_margin_percent
        
        return is_safe, margin
    
    def check_choke_condition(
        self,
        current_flow: float,
        choke_flow: float,
        max_margin_percent: float = 95.0
    ) -> Tuple[bool, float]:
        """
        Check if compressor is approaching choke condition.
        
        Args:
            current_flow: Current flow rate
            choke_flow: Choke flow rate
            max_margin_percent: Maximum acceptable percentage of choke flow
            
        Returns:
            Tuple of (is_safe, percent_of_choke)
        """
        if choke_flow <= 0:
            return True, 0.0
        
        percent_of_choke = (current_flow / choke_flow) * 100
        is_safe = percent_of_choke <= max_margin_percent
        
        return is_safe, percent_of_choke
    
    def validate_speed_range(
        self,
        speed: float,
        rated_speed: float,
        tolerance_percent: float = 5.0
    ) -> bool:
        """
        Validate compressor speed is within acceptable range.
        
        Args:
            speed: Current speed (RPM)
            rated_speed: Rated/design speed (RPM)
            tolerance_percent: Acceptable deviation percentage
            
        Returns:
            True if speed is acceptable
        """
        min_speed = rated_speed * (1 - tolerance_percent / 100)
        max_speed = rated_speed * (1 + tolerance_percent / 100)
        
        return min_speed <= speed <= max_speed
    
    def calculate_polytropic_head(
        self,
        suction_pressure: float,
        discharge_pressure: float,
        suction_temperature: float,
        gas_constant: float,
        polytropic_exponent: float
    ) -> float:
        """
        Calculate polytropic head for compressor.
        
        H_p = (n/(n-1)) * R * T1 * [(P2/P1)^((n-1)/n) - 1]
        
        Args:
            suction_pressure: Suction pressure (bar or psi)
            discharge_pressure: Discharge pressure (bar or psi)
            suction_temperature: Suction temperature (K or R)
            gas_constant: Specific gas constant (J/kg·K or ft·lbf/lbm·R)
            polytropic_exponent: Polytropic exponent n
            
        Returns:
            Polytropic head (kJ/kg or BTU/lb)
        """
        if suction_pressure <= 0 or polytropic_exponent <= 1:
            return 0.0
        
        pressure_ratio = discharge_pressure / suction_pressure
        exponent = (polytropic_exponent - 1) / polytropic_exponent
        
        head = (polytropic_exponent / (polytropic_exponent - 1)) * \
               gas_constant * suction_temperature * \
               (math.pow(pressure_ratio, exponent) - 1)
        
        # Convert J/kg to kJ/kg for SI
        if self.unit_system == UnitSystem.SI:
            head = head / 1000.0
        
        return head


# Register standard with factory
StandardFactory.register_standard("api 617", API617Standard)
StandardFactory.register_standard("api617", API617Standard)