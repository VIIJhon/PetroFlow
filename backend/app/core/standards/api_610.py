"""
API 610 Standard - Centrifugal Pumps for Petroleum, Petrochemical and Natural Gas Industries
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements operating limits and validation rules per API 610 11th Edition.
"""

from typing import Dict, List
from enum import Enum

from . import (
    IndustryStandard,
    EquipmentType,
    UnitSystem,
    OperatingLimits,
    StandardFactory
)


class PumpType(Enum):
    """API 610 pump classifications."""
    OH1 = "oh1"  # Overhung, single stage, centerline mounted
    OH2 = "oh2"  # Overhung, single stage, centerline supported
    OH3 = "oh3"  # Overhung, two stage
    OH4 = "oh4"  # Overhung, single stage, vertically suspended
    OH5 = "oh5"  # Overhung, multistage, vertically suspended
    OH6 = "oh6"  # Overhung, single stage, solid shaft
    BB1 = "bb1"  # Between bearings, single stage, axially split
    BB2 = "bb2"  # Between bearings, two stage, axially split
    BB3 = "bb3"  # Between bearings, multistage, radially split
    BB4 = "bb4"  # Between bearings, single stage, radially split
    BB5 = "bb5"  # Between bearings, multistage, barrel type
    VS1 = "vs1"  # Vertically suspended, single stage diffuser
    VS2 = "vs2"  # Vertically suspended, multistage diffuser
    VS3 = "vs3"  # Vertically suspended, single stage volute
    VS4 = "vs4"  # Vertically suspended, multistage volute
    VS5 = "vs5"  # Vertically suspended, single stage mixed flow
    VS6 = "vs6"  # Vertically suspended, single stage axial flow
    VS7 = "vs7"  # Vertically suspended, multistage mixed flow


class ServiceType(Enum):
    """Service classifications per API 610."""
    GENERAL_PURPOSE = "general_purpose"
    SPECIAL_PURPOSE = "special_purpose"
    SEVERE_DUTY = "severe_duty"


class API610Standard(IndustryStandard):
    """
    API 610 Standard implementation for centrifugal pumps.
    
    Provides operating limits for:
    - Discharge pressure
    - Suction pressure
    - Temperature
    - Flow rate
    - Speed (RPM)
    - Vibration
    - Bearing temperature
    - Seal flush pressure
    - NPSH (Net Positive Suction Head)
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        super().__init__(unit_system)
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return "API 610"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [
            EquipmentType.PUMP_CENTRIFUGAL,
            EquipmentType.PUMP_POSITIVE_DISPLACEMENT
        ]
    
    def _initialize_limits(self):
        """Initialize operating limits based on unit system."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in SI units."""
        return {
            "pump_centrifugal": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=350.0,  # bar
                    warning_max=315.0,
                    alarm_max=332.5,
                    unit="bar"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=-0.9,  # bar (near vacuum)
                    max_value=100.0,
                    warning_min=-0.7,
                    alarm_min=-0.85,
                    unit="bar"
                ),
                "temperature": OperatingLimits(
                    min_value=-50.0,  # °C
                    max_value=400.0,
                    warning_max=370.0,
                    alarm_max=385.0,
                    unit="°C"
                ),
                "flow_rate": OperatingLimits(
                    min_value=0.0,  # m³/h
                    max_value=10000.0,
                    warning_min=50.0,  # Minimum continuous flow
                    alarm_min=25.0,
                    unit="m³/h"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,  # RPM
                    max_value=3600.0,
                    warning_max=3540.0,
                    alarm_max=3570.0,
                    unit="RPM"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,  # mm/s RMS
                    max_value=7.1,  # Per ISO 10816
                    warning_max=4.5,
                    alarm_max=7.1,
                    unit="mm/s"
                ),
                "bearing_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=120.0,
                    warning_max=95.0,
                    alarm_max=110.0,
                    unit="°C"
                ),
                "seal_flush_pressure": OperatingLimits(
                    min_value=1.0,  # bar above suction
                    max_value=50.0,
                    warning_min=1.5,
                    alarm_min=1.2,
                    unit="bar"
                ),
                "npsh_available": OperatingLimits(
                    min_value=0.0,  # m
                    max_value=1000.0,
                    warning_min=3.0,  # Typical NPSHR + margin
                    alarm_min=1.5,
                    unit="m"
                ),
                "efficiency": OperatingLimits(
                    min_value=0.0,  # %
                    max_value=100.0,
                    warning_min=70.0,
                    alarm_min=60.0,
                    unit="%"
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # kW
                    max_value=50000.0,
                    warning_max=45000.0,
                    alarm_max=47500.0,
                    unit="kW"
                ),
                "differential_pressure": OperatingLimits(
                    min_value=0.0,  # bar
                    max_value=300.0,
                    warning_max=270.0,
                    alarm_max=285.0,
                    unit="bar"
                ),
            },
            "pump_positive_displacement": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=700.0,  # bar (higher for PD pumps)
                    warning_max=630.0,
                    alarm_max=665.0,
                    unit="bar"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=-0.5,
                    max_value=50.0,
                    warning_min=-0.3,
                    alarm_min=-0.4,
                    unit="bar"
                ),
                "temperature": OperatingLimits(
                    min_value=-50.0,
                    max_value=350.0,
                    warning_max=320.0,
                    alarm_max=335.0,
                    unit="°C"
                ),
                "flow_rate": OperatingLimits(
                    min_value=0.0,
                    max_value=5000.0,
                    warning_min=10.0,
                    alarm_min=5.0,
                    unit="m³/h"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,
                    max_value=1800.0,
                    warning_max=1750.0,
                    alarm_max=1775.0,
                    unit="RPM"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,
                    max_value=11.2,  # Higher for reciprocating
                    warning_max=7.1,
                    alarm_max=11.2,
                    unit="mm/s"
                ),
            }
        }
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in Imperial units."""
        return {
            "pump_centrifugal": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=5075.0,  # psi
                    warning_max=4568.0,
                    alarm_max=4822.0,
                    unit="psi"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=-13.0,  # psi
                    max_value=1450.0,
                    warning_min=-10.0,
                    alarm_min=-12.0,
                    unit="psi"
                ),
                "temperature": OperatingLimits(
                    min_value=-58.0,  # °F
                    max_value=752.0,
                    warning_max=698.0,
                    alarm_max=725.0,
                    unit="°F"
                ),
                "flow_rate": OperatingLimits(
                    min_value=0.0,  # GPM
                    max_value=44000.0,
                    warning_min=220.0,
                    alarm_min=110.0,
                    unit="GPM"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,
                    max_value=3600.0,
                    warning_max=3540.0,
                    alarm_max=3570.0,
                    unit="RPM"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,  # in/s
                    max_value=0.28,
                    warning_max=0.177,
                    alarm_max=0.28,
                    unit="in/s"
                ),
                "bearing_temperature": OperatingLimits(
                    min_value=32.0,  # °F
                    max_value=248.0,
                    warning_max=203.0,
                    alarm_max=230.0,
                    unit="°F"
                ),
            }
        }
    
    def get_limits(self, equipment_type: EquipmentType, parameter: str) -> OperatingLimits:
        """
        Get operating limits for a specific parameter.
        
        Args:
            equipment_type: Type of pump
            parameter: Parameter name
            
        Returns:
            OperatingLimits object
            
        Raises:
            ValueError: If equipment type or parameter not supported
        """
        equipment_key = equipment_type.value
        
        if equipment_key not in self._limits:
            raise ValueError(f"Equipment type {equipment_type} not supported by API 610")
        
        if parameter not in self._limits[equipment_key]:
            raise ValueError(f"Parameter {parameter} not defined for {equipment_type}")
        
        return self._limits[equipment_key][parameter]
    
    def check_minimum_flow(
        self,
        flow_rate: float,
        rated_flow: float,
        pump_type: PumpType
    ) -> bool:
        """
        Check if flow rate meets minimum continuous flow requirements.
        
        API 610 requires minimum flow to prevent:
        - Overheating
        - Recirculation
        - Cavitation
        - Mechanical damage
        
        Args:
            flow_rate: Current flow rate (m³/h or GPM)
            rated_flow: Rated/design flow rate
            pump_type: Type of pump per API 610 classification
            
        Returns:
            True if flow is acceptable, False otherwise
        """
        # Minimum flow typically 25-40% of rated flow depending on pump type
        min_flow_factors = {
            PumpType.OH1: 0.25,
            PumpType.OH2: 0.25,
            PumpType.OH3: 0.30,
            PumpType.BB1: 0.30,
            PumpType.BB2: 0.30,
            PumpType.BB3: 0.35,
            PumpType.BB4: 0.30,
            PumpType.BB5: 0.40,
            PumpType.VS1: 0.25,
            PumpType.VS2: 0.30,
        }
        
        min_factor = min_flow_factors.get(pump_type, 0.30)
        min_flow = rated_flow * min_factor
        
        return flow_rate >= min_flow
    
    def calculate_npsh_margin(
        self,
        npsh_available: float,
        npsh_required: float
    ) -> float:
        """
        Calculate NPSH margin.
        
        API 610 recommends NPSHA > NPSHR by at least 0.6m (2 ft) or 3% of head.
        
        Args:
            npsh_available: Available NPSH (m or ft)
            npsh_required: Required NPSH (m or ft)
            
        Returns:
            NPSH margin (positive is good)
        """
        return npsh_available - npsh_required
    
    def validate_speed_range(
        self,
        speed: float,
        rated_speed: float,
        tolerance_percent: float = 2.0
    ) -> bool:
        """
        Validate pump speed is within acceptable range.
        
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


# Register standard with factory
StandardFactory.register_standard("api 610", API610Standard)
StandardFactory.register_standard("api610", API610Standard)