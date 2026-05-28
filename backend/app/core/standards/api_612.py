"""
API 612 Standard - Petroleum, Petrochemical and Natural Gas Industries - Steam Turbines - Special-purpose Applications
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements operating limits and validation rules per API 612 5th Edition for gas turbines.
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


class GasTurbineType(Enum):
    """Gas turbine classifications."""
    INDUSTRIAL = "industrial"
    AERODERIVATIVE = "aeroderivative"
    HEAVY_DUTY = "heavy_duty"


class API612Standard(IndustryStandard):
    """
    API 612 Standard implementation for gas turbines.
    
    Provides operating limits for:
    - Compressor inlet/discharge conditions
    - Turbine inlet/exhaust conditions
    - Speed (RPM)
    - Power output
    - Fuel gas pressure and temperature
    - Vibration
    - Bearing temperature
    - Exhaust gas temperature
    - Combustion temperature
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        super().__init__(unit_system)
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return "API 612"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [EquipmentType.TURBINE_GAS]
    
    def _initialize_limits(self):
        """Initialize operating limits based on unit system."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in SI units."""
        return {
            "turbine_gas": {
                "compressor_inlet_pressure": OperatingLimits(
                    min_value=0.8,  # bar
                    max_value=1.2,
                    warning_min=0.9,
                    alarm_min=0.85,
                    unit="bar"
                ),
                "compressor_inlet_temperature": OperatingLimits(
                    min_value=-20.0,  # °C
                    max_value=50.0,
                    warning_max=45.0,
                    alarm_max=48.0,
                    unit="°C"
                ),
                "compressor_discharge_pressure": OperatingLimits(
                    min_value=5.0,  # bar
                    max_value=40.0,
                    warning_max=36.0,
                    alarm_max=38.0,
                    unit="bar"
                ),
                "turbine_inlet_temperature": OperatingLimits(
                    min_value=800.0,  # °C (combustion temperature)
                    max_value=1600.0,
                    warning_max=1500.0,
                    alarm_max=1550.0,
                    unit="°C"
                ),
                "exhaust_temperature": OperatingLimits(
                    min_value=300.0,  # °C
                    max_value=650.0,
                    warning_max=620.0,
                    alarm_max=635.0,
                    unit="°C"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,  # RPM
                    max_value=20000.0,  # High-speed gas turbines
                    warning_max=19000.0,
                    alarm_max=19500.0,
                    unit="RPM"
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # kW
                    max_value=100000.0,
                    warning_max=90000.0,
                    alarm_max=95000.0,
                    unit="kW"
                ),
                "fuel_gas_pressure": OperatingLimits(
                    min_value=10.0,  # bar
                    max_value=50.0,
                    warning_min=12.0,
                    alarm_min=11.0,
                    unit="bar"
                ),
                "fuel_gas_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=80.0,
                    warning_max=70.0,
                    alarm_max=75.0,
                    unit="°C"
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
                "lube_oil_pressure": OperatingLimits(
                    min_value=2.0,  # bar
                    max_value=10.0,
                    warning_min=2.5,
                    alarm_min=2.2,
                    unit="bar"
                ),
                "lube_oil_temperature": OperatingLimits(
                    min_value=30.0,  # °C
                    max_value=70.0,
                    warning_max=65.0,
                    alarm_max=68.0,
                    unit="°C"
                ),
                "thermal_efficiency": OperatingLimits(
                    min_value=0.0,  # %
                    max_value=45.0,  # Modern gas turbines
                    warning_min=30.0,
                    alarm_min=25.0,
                    unit="%"
                ),
                "pressure_ratio": OperatingLimits(
                    min_value=5.0,
                    max_value=40.0,
                    warning_max=36.0,
                    alarm_max=38.0,
                    unit=""
                ),
                "air_flow": OperatingLimits(
                    min_value=0.0,  # kg/s
                    max_value=1000.0,
                    warning_min=50.0,
                    alarm_min=25.0,
                    unit="kg/s"
                ),
                "fuel_flow": OperatingLimits(
                    min_value=0.0,  # kg/s
                    max_value=50.0,
                    warning_max=45.0,
                    alarm_max=47.5,
                    unit="kg/s"
                ),
            }
        }
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in Imperial units."""
        return {
            "turbine_gas": {
                "compressor_inlet_pressure": OperatingLimits(
                    min_value=11.6,  # psi
                    max_value=17.4,
                    warning_min=13.0,
                    alarm_min=12.3,
                    unit="psi"
                ),
                "compressor_inlet_temperature": OperatingLimits(
                    min_value=-4.0,  # °F
                    max_value=122.0,
                    warning_max=113.0,
                    alarm_max=118.0,
                    unit="°F"
                ),
                "turbine_inlet_temperature": OperatingLimits(
                    min_value=1472.0,  # °F
                    max_value=2912.0,
                    warning_max=2732.0,
                    alarm_max=2822.0,
                    unit="°F"
                ),
                "exhaust_temperature": OperatingLimits(
                    min_value=572.0,  # °F
                    max_value=1202.0,
                    warning_max=1148.0,
                    alarm_max=1175.0,
                    unit="°F"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,
                    max_value=20000.0,
                    warning_max=19000.0,
                    alarm_max=19500.0,
                    unit="RPM"
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # HP
                    max_value=134000.0,
                    warning_max=120600.0,
                    alarm_max=127300.0,
                    unit="HP"
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
            raise ValueError(f"Equipment type {equipment_type} not supported by API 612")
        
        if parameter not in self._limits[equipment_key]:
            raise ValueError(f"Parameter {parameter} not defined for {equipment_type}")
        
        return self._limits[equipment_key][parameter]
    
    def calculate_thermal_efficiency(
        self,
        power_output: float,
        fuel_flow: float,
        fuel_heating_value: float
    ) -> float:
        """
        Calculate thermal efficiency.
        
        η_th = (Power Output / (Fuel Flow * LHV)) * 100
        
        Args:
            power_output: Power output (kW)
            fuel_flow: Fuel flow rate (kg/s)
            fuel_heating_value: Lower heating value (kJ/kg)
            
        Returns:
            Thermal efficiency percentage
        """
        if fuel_flow <= 0 or fuel_heating_value <= 0:
            return 0.0
        
        fuel_energy = fuel_flow * fuel_heating_value
        efficiency = (power_output / fuel_energy) * 100
        
        return min(efficiency, 100.0)
    
    def calculate_pressure_ratio(
        self,
        discharge_pressure: float,
        inlet_pressure: float
    ) -> float:
        """
        Calculate compressor pressure ratio.
        
        Args:
            discharge_pressure: Discharge pressure (bar or psi)
            inlet_pressure: Inlet pressure (bar or psi)
            
        Returns:
            Pressure ratio
        """
        if inlet_pressure <= 0:
            return 0.0
        
        return discharge_pressure / inlet_pressure
    
    def calculate_specific_fuel_consumption(
        self,
        fuel_flow: float,
        power_output: float
    ) -> float:
        """
        Calculate specific fuel consumption (SFC).
        
        SFC = Fuel Flow / Power Output
        
        Args:
            fuel_flow: Fuel flow rate (kg/h)
            power_output: Power output (kW)
            
        Returns:
            SFC (kg/kWh)
        """
        if power_output <= 0:
            return 0.0
        
        return fuel_flow / power_output
    
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
    
    def check_combustion_stability(
        self,
        exhaust_temperature: float,
        expected_temperature: float,
        tolerance: float = 50.0
    ) -> bool:
        """
        Check combustion stability based on exhaust temperature.
        
        Args:
            exhaust_temperature: Current exhaust temperature (°C or °F)
            expected_temperature: Expected exhaust temperature (°C or °F)
            tolerance: Acceptable deviation (°C or °F)
            
        Returns:
            True if combustion is stable
        """
        deviation = abs(exhaust_temperature - expected_temperature)
        return deviation <= tolerance


# Register standard with factory
StandardFactory.register_standard("api 612", API612Standard)
StandardFactory.register_standard("api612", API612Standard)