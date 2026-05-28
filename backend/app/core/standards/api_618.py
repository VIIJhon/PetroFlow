"""
API 618 Standard - Reciprocating Compressors for Petroleum, Chemical, and Gas Industry Services
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements operating limits and validation rules per API 618 5th Edition.
"""

from typing import Dict, List, Optional
from enum import Enum

from . import (
    IndustryStandard,
    EquipmentType,
    UnitSystem,
    OperatingLimits,
    StandardFactory
)


class RecipCompressorType(Enum):
    """API 618 reciprocating compressor classifications."""
    SINGLE_ACTING = "single_acting"
    DOUBLE_ACTING = "double_acting"
    LABYRINTH_PISTON = "labyrinth_piston"
    DIAPHRAGM = "diaphragm"


class CylinderArrangement(Enum):
    """Cylinder arrangement types."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    V_TYPE = "v_type"
    W_TYPE = "w_type"
    L_TYPE = "l_type"


class API618Standard(IndustryStandard):
    """
    API 618 Standard implementation for reciprocating compressors.
    
    Provides operating limits for:
    - Discharge pressure and temperature
    - Suction pressure and temperature
    - Rod load
    - Piston speed
    - Vibration
    - Bearing temperature
    - Cylinder temperature
    - Valve temperature
    - Crankcase pressure
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        super().__init__(unit_system)
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return "API 618"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [EquipmentType.COMPRESSOR_RECIPROCATING]
    
    def _initialize_limits(self):
        """Initialize operating limits based on unit system."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in SI units."""
        return {
            "compressor_reciprocating": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=1000.0,  # bar (very high pressure capability)
                    warning_max=900.0,
                    alarm_max=950.0,
                    unit="bar"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=0.1,  # bar
                    max_value=500.0,
                    warning_min=0.5,
                    alarm_min=0.2,
                    unit="bar"
                ),
                "discharge_temperature": OperatingLimits(
                    min_value=-50.0,  # °C
                    max_value=200.0,
                    warning_max=175.0,
                    alarm_max=190.0,
                    unit="°C"
                ),
                "suction_temperature": OperatingLimits(
                    min_value=-50.0,  # °C
                    max_value=100.0,
                    warning_max=85.0,
                    alarm_max=95.0,
                    unit="°C"
                ),
                "cylinder_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=180.0,
                    warning_max=160.0,
                    alarm_max=170.0,
                    unit="°C"
                ),
                "valve_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=200.0,
                    warning_max=180.0,
                    alarm_max=190.0,
                    unit="°C"
                ),
                "piston_speed": OperatingLimits(
                    min_value=0.0,  # m/s
                    max_value=5.0,  # API 618 limit
                    warning_max=4.5,
                    alarm_max=4.8,
                    unit="m/s"
                ),
                "rod_load": OperatingLimits(
                    min_value=0.0,  # kN
                    max_value=1000.0,
                    warning_max=900.0,
                    alarm_max=950.0,
                    unit="kN"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,  # RPM
                    max_value=1200.0,
                    warning_max=1140.0,
                    alarm_max=1170.0,
                    unit="RPM"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,  # mm/s RMS
                    max_value=18.0,  # Higher for reciprocating
                    warning_max=11.2,
                    alarm_max=18.0,
                    unit="mm/s"
                ),
                "vibration_displacement": OperatingLimits(
                    min_value=0.0,  # μm peak-to-peak
                    max_value=150.0,
                    warning_max=100.0,
                    alarm_max=125.0,
                    unit="μm"
                ),
                "bearing_temperature": OperatingLimits(
                    min_value=0.0,  # °C
                    max_value=110.0,
                    warning_max=95.0,
                    alarm_max=105.0,
                    unit="°C"
                ),
                "crankcase_pressure": OperatingLimits(
                    min_value=-0.05,  # bar (slight vacuum acceptable)
                    max_value=0.1,
                    warning_max=0.07,
                    alarm_max=0.09,
                    unit="bar"
                ),
                "oil_pressure": OperatingLimits(
                    min_value=1.0,  # bar
                    max_value=10.0,
                    warning_min=1.5,
                    alarm_min=1.2,
                    unit="bar"
                ),
                "cooling_water_temperature": OperatingLimits(
                    min_value=10.0,  # °C
                    max_value=50.0,
                    warning_max=45.0,
                    alarm_max=48.0,
                    unit="°C"
                ),
                "compression_ratio_per_stage": OperatingLimits(
                    min_value=1.0,
                    max_value=5.0,  # API 618 recommendation
                    warning_max=4.5,
                    alarm_max=4.8,
                    unit=""
                ),
                "power": OperatingLimits(
                    min_value=0.0,  # kW
                    max_value=50000.0,
                    warning_max=45000.0,
                    alarm_max=47500.0,
                    unit="kW"
                ),
            }
        }
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in Imperial units."""
        return {
            "compressor_reciprocating": {
                "discharge_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=14500.0,  # psi
                    warning_max=13050.0,
                    alarm_max=13775.0,
                    unit="psi"
                ),
                "suction_pressure": OperatingLimits(
                    min_value=1.5,  # psi
                    max_value=7250.0,
                    warning_min=7.0,
                    alarm_min=3.0,
                    unit="psi"
                ),
                "discharge_temperature": OperatingLimits(
                    min_value=-58.0,  # °F
                    max_value=392.0,
                    warning_max=347.0,
                    alarm_max=374.0,
                    unit="°F"
                ),
                "piston_speed": OperatingLimits(
                    min_value=0.0,  # ft/min
                    max_value=984.0,  # ~5 m/s
                    warning_max=886.0,
                    alarm_max=945.0,
                    unit="ft/min"
                ),
                "speed": OperatingLimits(
                    min_value=0.0,
                    max_value=1200.0,
                    warning_max=1140.0,
                    alarm_max=1170.0,
                    unit="RPM"
                ),
                "vibration_velocity": OperatingLimits(
                    min_value=0.0,  # in/s
                    max_value=0.71,
                    warning_max=0.44,
                    alarm_max=0.71,
                    unit="in/s"
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
            raise ValueError(f"Equipment type {equipment_type} not supported by API 618")
        
        if parameter not in self._limits[equipment_key]:
            raise ValueError(f"Parameter {parameter} not defined for {equipment_type}")
        
        return self._limits[equipment_key][parameter]
    
    def calculate_piston_speed(
        self,
        stroke_length: float,
        rpm: float
    ) -> float:
        """
        Calculate average piston speed.
        
        Piston Speed = 2 * Stroke * RPM / 60
        
        API 618 recommends maximum piston speed of 5 m/s (984 ft/min).
        
        Args:
            stroke_length: Stroke length (m or ft)
            rpm: Compressor speed (RPM)
            
        Returns:
            Average piston speed (m/s or ft/min)
        """
        if self.unit_system == UnitSystem.SI:
            # Return m/s
            return (2 * stroke_length * rpm) / 60
        else:
            # Return ft/min
            return 2 * stroke_length * rpm
    
    def calculate_rod_load(
        self,
        pressure_differential: float,
        piston_area: float,
        rod_area: float = 0.0
    ) -> float:
        """
        Calculate rod load for double-acting cylinder.
        
        Rod Load = (P_discharge * A_piston) - (P_suction * (A_piston - A_rod))
        
        Args:
            pressure_differential: Pressure difference (bar or psi)
            piston_area: Piston area (cm² or in²)
            rod_area: Rod area (cm² or in²), 0 for single-acting
            
        Returns:
            Rod load (kN or lbf)
        """
        effective_area = piston_area - rod_area
        
        if self.unit_system == UnitSystem.SI:
            # Convert bar·cm² to kN
            load = (pressure_differential * effective_area) / 10.0
        else:
            # psi·in² = lbf
            load = pressure_differential * effective_area
        
        return load
    
    def calculate_compression_ratio(
        self,
        discharge_pressure: float,
        suction_pressure: float
    ) -> float:
        """
        Calculate compression ratio per stage.
        
        API 618 recommends compression ratio per stage ≤ 5.0
        
        Args:
            discharge_pressure: Discharge pressure (bar or psi)
            suction_pressure: Suction pressure (bar or psi)
            
        Returns:
            Compression ratio
        """
        if suction_pressure <= 0:
            return 0.0
        
        return discharge_pressure / suction_pressure
    
    def validate_piston_speed(
        self,
        piston_speed: float,
        max_speed: float = 5.0
    ) -> bool:
        """
        Validate piston speed against API 618 limits.
        
        Args:
            piston_speed: Current piston speed (m/s)
            max_speed: Maximum allowable speed (m/s), default 5.0
            
        Returns:
            True if speed is acceptable
        """
        return piston_speed <= max_speed
    
    def validate_compression_ratio(
        self,
        compression_ratio: float,
        max_ratio: float = 5.0
    ) -> bool:
        """
        Validate compression ratio per stage.
        
        Args:
            compression_ratio: Compression ratio
            max_ratio: Maximum allowable ratio, default 5.0
            
        Returns:
            True if ratio is acceptable
        """
        return 1.0 <= compression_ratio <= max_ratio
    
    def calculate_volumetric_efficiency(
        self,
        actual_capacity: float,
        piston_displacement: float,
        clearance_volume_percent: float = 5.0
    ) -> float:
        """
        Calculate volumetric efficiency.
        
        η_v = (Actual Capacity / Piston Displacement) * 100
        
        Affected by:
        - Clearance volume
        - Compression ratio
        - Gas properties
        - Valve losses
        
        Args:
            actual_capacity: Actual gas capacity (m³/h or CFM)
            piston_displacement: Theoretical displacement (m³/h or CFM)
            clearance_volume_percent: Clearance volume as % of swept volume
            
        Returns:
            Volumetric efficiency percentage
        """
        if piston_displacement <= 0:
            return 0.0
        
        efficiency = (actual_capacity / piston_displacement) * 100
        return min(efficiency, 100.0)
    
    def check_rod_reversal(
        self,
        rod_load_compression: float,
        rod_load_tension: float,
        max_reversal_cycles: int = 1000000
    ) -> bool:
        """
        Check for rod load reversal conditions.
        
        Rod reversal can cause fatigue failures. API 618 requires
        evaluation of rod loading throughout the cycle.
        
        Args:
            rod_load_compression: Maximum compression load (kN or lbf)
            rod_load_tension: Maximum tension load (kN or lbf)
            max_reversal_cycles: Maximum allowable reversal cycles
            
        Returns:
            True if rod reversal is within acceptable limits
        """
        # Check if loads reverse (compression to tension)
        has_reversal = (rod_load_compression > 0 and rod_load_tension < 0) or \
                       (rod_load_compression < 0 and rod_load_tension > 0)
        
        if not has_reversal:
            return True
        
        # Additional checks would include fatigue analysis
        # For now, just flag the condition
        self.logger.warning(
            "Rod load reversal detected",
            extra={
                "compression_load": rod_load_compression,
                "tension_load": rod_load_tension
            }
        )
        
        return True  # Would need detailed fatigue analysis


# Register standard with factory
StandardFactory.register_standard("api 618", API618Standard)
StandardFactory.register_standard("api618", API618Standard)