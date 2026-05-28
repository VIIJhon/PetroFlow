"""
API 611 Standard - General-Purpose Steam Turbines for Petroleum, Chemical, and Gas Industry Services
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements operating limits and validation rules per API 611 5th Edition.
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


class TurbineType(Enum):
    """API 611 steam turbine classifications."""
    SINGLE_STAGE = "single_stage"
    MULTISTAGE = "multistage"
    CONDENSING = "condensing"
    NON_CONDENSING = "non_condensing"
    EXTRACTION = "extraction"
    BACK_PRESSURE = "back_pressure"


class API611Standard(IndustryStandard):
    """
    API 611 Standard implementation for steam turbines.
    
    Provides operating limits for:
    - Steam inlet pressure and temperature
    - Exhaust pressure and temperature
    - Speed (RPM)
    - Power output
    - Vibration
    - Bearing temperature
    - Thrust bearing load
    - Steam flow rate
    - Efficiency
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        super().__init__(unit_system)
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return "API 611"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [EquipmentType.TURBINE_STEAM]
    
    def _initialize_limits(self):
        """Initialize operating limits based on unit system."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in SI units."""
        return {
            "turbine_steam": {
                "inlet_pressure": OperatingLimits(
                    min_value=1.0,  # bar
                    max_value=200.0,
                    warning_max=180.0,
                    alarm_max=190.0,
                    unit="bar"
                ),
                "inlet_temperature": OperatingLimits(
                    min_value=100.0,  # °C
                    max_value=550.0,
                    warning_max=520.0,
                    alarm_max=535.0,
                    unit="°C"
                ),
                "exhaust_pressure": OperatingLimits(
                    min_value=0.05,  # bar (vacuum)
                    max_value=50.0,
                    warning_min=0.1,
                    alarm_min=0.07,
                    unit="bar"
                ),
                "exhaust_temperature": OperatingLimits(
                    min_value=50.0,  # °C
                    max_value=300.0,
                    warning_max=280.0,
                    alarm_max=290.0,
                    unit="°C"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,  # RPM
                    max_value=15000.0,
                    warning_max=14250.0,
                    alarm_max=14625.0,
                    unit="RPM"
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # kW
                    max_value=50000.0,
                    warning_max=45000.0,
                    alarm_max=47500.0,
                    unit="kW"
                ),
                "steam_flow": OperatingLimits(
                    min_value=0.0,  # kg/h
                    max_value=500000.0,
                    warning_min=5000.0,
                    alarm_min=2500.0,
                    unit="kg/h"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,  # mm/s RMS
                    max_value=11.2,
                    warning_max=7.1,
                    alarm_max=11.2,
                    unit="mm/s"
                ),
                "vibration_displacement": OperatingLimits(
                    min_value=0.0,  # μm peak-to-peak
                    max_value=100.0,
                    warning_max=75.0,
                    alarm_max=90.0,
                    unit="μm"
                ),
                "bearing_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=120.0,
                    warning_max=100.0,
                    alarm_max=110.0,
                    unit="°C"
                ),
                "thrust_bearing_load": OperatingLimits(
                    min_value=0.0,  # kN
                    max_value=500.0,
                    warning_max=450.0,
                    alarm_max=475.0,
                    unit="kN"
                ),
                "efficiency": OperatingLimits(
                    min_value=0.0,  # %
                    max_value=100.0,
                    warning_min=70.0,
                    alarm_min=60.0,
                    unit="%"
                ),
                "casing_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=400.0,
                    warning_max=370.0,
                    alarm_max=385.0,
                    unit="°C"
                ),
                "differential_expansion": OperatingLimits(
                    min_value=-5.0,  # mm
                    max_value=5.0,
                    warning_max=4.0,
                    alarm_max=4.5,
                    unit="mm"
                ),
            }
        }
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in Imperial units."""
        return {
            "turbine_steam": {
                "inlet_pressure": OperatingLimits(
                    min_value=14.5,  # psi
                    max_value=2900.0,
                    warning_max=2610.0,
                    alarm_max=2755.0,
                    unit="psi"
                ),
                "inlet_temperature": OperatingLimits(
                    min_value=212.0,  # °F
                    max_value=1022.0,
                    warning_max=968.0,
                    alarm_max=995.0,
                    unit="°F"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,
                    max_value=15000.0,
                    warning_max=14250.0,
                    alarm_max=14625.0,
                    unit="RPM"
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # HP
                    max_value=67000.0,
                    warning_max=60300.0,
                    alarm_max=63650.0,
                    unit="HP"
                ),
                "steam_flow": OperatingLimits(
                    min_value=0.0,  # lb/h
                    max_value=1100000.0,
                    warning_min=11000.0,
                    alarm_min=5500.0,
                    unit="lb/h"
                ),
            }
        }
    
    def get_limits(self, equipment_type: EquipmentType, parameter: str) -> OperatingLimits:
        """
        Get operating limits for a specific parameter.
        
        Args:
            equipment_type: Type of turbine
            parameter: Parameter name
            
        Returns:
            OperatingLimits object
            
        Raises:
            ValueError: If equipment type or parameter not supported
        """
        equipment_key = equipment_type.value
        
        if equipment_key not in self._limits:
            raise ValueError(f"Equipment type {equipment_type} not supported by API 611")
        
        if parameter not in self._limits[equipment_key]:
            raise ValueError(f"Parameter {parameter} not defined for {equipment_type}")
        
        return self._limits[equipment_key][parameter]
    
    def calculate_isentropic_efficiency(
        self,
        actual_work: float,
        isentropic_work: float
    ) -> float:
        """
        Calculate isentropic efficiency.
        
        η_s = (Actual Work / Isentropic Work) * 100
        
        Args:
            actual_work: Actual work output (kW or HP)
            isentropic_work: Isentropic work (kW or HP)
            
        Returns:
            Isentropic efficiency percentage
        """
        if isentropic_work <= 0:
            return 0.0
        
        efficiency = (actual_work / isentropic_work) * 100
        return min(efficiency, 100.0)
    
    def calculate_steam_rate(
        self,
        steam_flow: float,
        power_output: float
    ) -> float:
        """
        Calculate steam rate (specific steam consumption).
        
        Steam Rate = Steam Flow / Power Output
        
        Args:
            steam_flow: Steam flow rate (kg/h or lb/h)
            power_output: Power output (kW or HP)
            
        Returns:
            Steam rate (kg/kWh or lb/HPh)
        """
        if power_output <= 0:
            return 0.0
        
        return steam_flow / power_output
    
    def validate_speed_range(
        self,
        speed: float,
        rated_speed: float,
        tolerance_percent: float = 5.0
    ) -> bool:
        """
        Validate turbine speed is within acceptable range.
        
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
StandardFactory.register_standard("api 611", API611Standard)
StandardFactory.register_standard("api611", API611Standard)