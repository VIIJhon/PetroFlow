"""
ISO 10816 Standard - Mechanical vibration - Evaluation of machine vibration by measurements on non-rotating parts
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements vibration severity zones and limits per ISO 10816 Parts 1-7.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum

from . import (
    IndustryStandard,
    EquipmentType,
    UnitSystem,
    OperatingLimits,
    StandardFactory
)


class MachineClass(Enum):
    """ISO 10816 machine classifications."""
    CLASS_I = "class_i"      # Small machines (≤15 kW)
    CLASS_II = "class_ii"    # Medium machines (15-75 kW), no special foundation
    CLASS_III = "class_iii"  # Large machines (>75 kW), rigid foundation
    CLASS_IV = "class_iv"    # Large machines (>75 kW), flexible foundation


class SeverityZone(Enum):
    """ISO 10816 vibration severity zones."""
    ZONE_A = "zone_a"  # Good - Newly commissioned machines
    ZONE_B = "zone_b"  # Acceptable - Unrestricted long-term operation
    ZONE_C = "zone_c"  # Unsatisfactory - Limited operation, corrective action needed
    ZONE_D = "zone_d"  # Unacceptable - Damage possible, immediate action required


class MeasurementLocation(Enum):
    """Vibration measurement locations."""
    BEARING_HOUSING = "bearing_housing"
    PEDESTAL = "pedestal"
    FOUNDATION = "foundation"
    CASING = "casing"


class ISO10816Standard(IndustryStandard):
    """
    ISO 10816 Standard implementation for vibration evaluation.
    
    Provides vibration limits based on:
    - Machine class (I, II, III, IV)
    - Operating conditions (rigid vs flexible support)
    - Measurement type (velocity, displacement, acceleration)
    - Frequency range
    
    Severity zones:
    - Zone A: Good (newly commissioned)
    - Zone B: Acceptable (unrestricted operation)
    - Zone C: Unsatisfactory (limited operation)
    - Zone D: Unacceptable (damage possible)
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        super().__init__(unit_system)
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return "ISO 10816"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [
            EquipmentType.PUMP_CENTRIFUGAL,
            EquipmentType.PUMP_POSITIVE_DISPLACEMENT,
            EquipmentType.COMPRESSOR_CENTRIFUGAL,
            EquipmentType.COMPRESSOR_RECIPROCATING,
            EquipmentType.TURBINE_STEAM,
            EquipmentType.TURBINE_GAS,
            EquipmentType.GENERIC
        ]
    
    def _initialize_limits(self):
        """Initialize vibration limits based on unit system and machine class."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Get vibration limits in SI units (mm/s RMS).
        
        Structure: {machine_class: {zone: {boundary: value}}}
        """
        return {
            "class_i": {
                "zone_a_b": 0.71,   # Good to Acceptable
                "zone_b_c": 1.8,    # Acceptable to Unsatisfactory
                "zone_c_d": 4.5,    # Unsatisfactory to Unacceptable
            },
            "class_ii": {
                "zone_a_b": 1.12,
                "zone_b_c": 2.8,
                "zone_c_d": 7.1,
            },
            "class_iii": {
                "zone_a_b": 1.8,
                "zone_b_c": 4.5,
                "zone_c_d": 11.2,
            },
            "class_iv": {
                "zone_a_b": 2.8,
                "zone_b_c": 7.1,
                "zone_c_d": 18.0,
            },
        }
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, float]]:
        """Get vibration limits in Imperial units (in/s RMS)."""
        return {
            "class_i": {
                "zone_a_b": 0.028,
                "zone_b_c": 0.071,
                "zone_c_d": 0.177,
            },
            "class_ii": {
                "zone_a_b": 0.044,
                "zone_b_c": 0.110,
                "zone_c_d": 0.280,
            },
            "class_iii": {
                "zone_a_b": 0.071,
                "zone_b_c": 0.177,
                "zone_c_d": 0.441,
            },
            "class_iv": {
                "zone_a_b": 0.110,
                "zone_b_c": 0.280,
                "zone_c_d": 0.709,
            },
        }
    
    def get_limits(self, equipment_type: EquipmentType, parameter: str) -> OperatingLimits:
        """
        Get operating limits for vibration.
        
        Note: For ISO 10816, use get_severity_zone() instead for proper classification.
        This method provides generic limits for compatibility.
        
        Args:
            equipment_type: Type of equipment
            parameter: Should be 'vibration_velocity'
            
        Returns:
            OperatingLimits object with generic Class III limits
        """
        if parameter != "vibration_velocity":
            raise ValueError(f"ISO 10816 only defines limits for vibration_velocity, not {parameter}")
        
        # Return generic Class III limits (most common)
        class_limits = self._limits["class_iii"]
        
        return OperatingLimits(
            min_value=0.0,
            max_value=class_limits["zone_c_d"],
            warning_max=class_limits["zone_a_b"],
            alarm_max=class_limits["zone_b_c"],
            unit="mm/s" if self.unit_system == UnitSystem.SI else "in/s"
        )
    
    def get_severity_zone(
        self,
        vibration_velocity: float,
        machine_class: MachineClass
    ) -> SeverityZone:
        """
        Determine vibration severity zone based on velocity and machine class.
        
        Args:
            vibration_velocity: RMS vibration velocity (mm/s or in/s)
            machine_class: Machine classification
            
        Returns:
            SeverityZone enum value
        """
        class_key = machine_class.value
        limits = self._limits.get(class_key)
        
        if not limits:
            raise ValueError(f"Unknown machine class: {machine_class}")
        
        if vibration_velocity <= limits["zone_a_b"]:
            return SeverityZone.ZONE_A
        elif vibration_velocity <= limits["zone_b_c"]:
            return SeverityZone.ZONE_B
        elif vibration_velocity <= limits["zone_c_d"]:
            return SeverityZone.ZONE_C
        else:
            return SeverityZone.ZONE_D
    
    def classify_machine(
        self,
        power_rating: float,
        foundation_type: str = "rigid"
    ) -> MachineClass:
        """
        Classify machine based on power rating and foundation.
        
        Args:
            power_rating: Machine power rating (kW or HP)
            foundation_type: "rigid" or "flexible"
            
        Returns:
            MachineClass enum value
        """
        # Convert HP to kW if needed
        if self.unit_system == UnitSystem.IMPERIAL:
            power_rating = power_rating * 0.745699
        
        if power_rating <= 15:
            return MachineClass.CLASS_I
        elif power_rating <= 75:
            return MachineClass.CLASS_II
        elif foundation_type.lower() == "rigid":
            return MachineClass.CLASS_III
        else:
            return MachineClass.CLASS_IV
    
    def get_zone_limits(
        self,
        machine_class: MachineClass
    ) -> Dict[str, float]:
        """
        Get all zone boundary limits for a machine class.
        
        Args:
            machine_class: Machine classification
            
        Returns:
            Dictionary with zone boundaries
        """
        class_key = machine_class.value
        return self._limits.get(class_key, {})
    
    def is_acceptable(
        self,
        vibration_velocity: float,
        machine_class: MachineClass,
        allow_zone_c: bool = False
    ) -> Tuple[bool, SeverityZone]:
        """
        Check if vibration level is acceptable.
        
        Args:
            vibration_velocity: RMS vibration velocity (mm/s or in/s)
            machine_class: Machine classification
            allow_zone_c: If True, Zone C is considered acceptable for limited operation
            
        Returns:
            Tuple of (is_acceptable, severity_zone)
        """
        zone = self.get_severity_zone(vibration_velocity, machine_class)
        
        if allow_zone_c:
            acceptable = zone in [SeverityZone.ZONE_A, SeverityZone.ZONE_B, SeverityZone.ZONE_C]
        else:
            acceptable = zone in [SeverityZone.ZONE_A, SeverityZone.ZONE_B]
        
        return acceptable, zone
    
    def calculate_displacement_from_velocity(
        self,
        velocity: float,
        frequency: float
    ) -> float:
        """
        Convert vibration velocity to displacement.
        
        Displacement (peak) = Velocity (RMS) / (2π * frequency) * √2
        
        Args:
            velocity: RMS velocity (mm/s or in/s)
            frequency: Vibration frequency (Hz)
            
        Returns:
            Peak-to-peak displacement (μm or mils)
        """
        if frequency <= 0:
            return 0.0
        
        import math
        
        # Convert RMS to peak
        velocity_peak = velocity * math.sqrt(2)
        
        # Calculate displacement (peak)
        displacement_peak = velocity_peak / (2 * math.pi * frequency)
        
        # Convert to peak-to-peak
        displacement_pp = displacement_peak * 2
        
        # Convert to μm (SI) or mils (Imperial)
        if self.unit_system == UnitSystem.SI:
            return displacement_pp * 1000  # mm to μm
        else:
            return displacement_pp * 1000  # in to mils
    
    def calculate_acceleration_from_velocity(
        self,
        velocity: float,
        frequency: float
    ) -> float:
        """
        Convert vibration velocity to acceleration.
        
        Acceleration (RMS) = Velocity (RMS) * 2π * frequency
        
        Args:
            velocity: RMS velocity (mm/s or in/s)
            frequency: Vibration frequency (Hz)
            
        Returns:
            RMS acceleration (m/s² or in/s²)
        """
        import math
        
        acceleration = velocity * 2 * math.pi * frequency
        
        # Convert mm/s² to m/s² for SI
        if self.unit_system == UnitSystem.SI:
            return acceleration / 1000
        
        return acceleration
    
    def get_recommendation(
        self,
        severity_zone: SeverityZone
    ) -> str:
        """
        Get operational recommendation based on severity zone.
        
        Args:
            severity_zone: Current severity zone
            
        Returns:
            Recommendation string
        """
        recommendations = {
            SeverityZone.ZONE_A: "Vibration level is good. Machine is suitable for unrestricted long-term operation.",
            SeverityZone.ZONE_B: "Vibration level is acceptable. Machine is suitable for unrestricted long-term operation.",
            SeverityZone.ZONE_C: "Vibration level is unsatisfactory. Machine may operate for limited period. Corrective action should be taken.",
            SeverityZone.ZONE_D: "Vibration level is unacceptable. Damage to machine is possible. Immediate corrective action required."
        }
        
        return recommendations.get(severity_zone, "Unknown severity zone")


# Register standard with factory
StandardFactory.register_standard("iso 10816", ISO10816Standard)
StandardFactory.register_standard("iso10816", ISO10816Standard)