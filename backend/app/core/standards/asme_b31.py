"""
ASME B31 Standard - Code for Pressure Piping
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Implements pressure and temperature limits per ASME B31.1, B31.3, B31.4, B31.8 codes.
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


class PipingCode(Enum):
    """ASME B31 piping code sections."""
    B31_1 = "b31_1"    # Power Piping
    B31_3 = "b31_3"    # Process Piping
    B31_4 = "b31_4"    # Pipeline Transportation Systems for Liquids
    B31_8 = "b31_8"    # Gas Transmission and Distribution Piping


class ServiceClass(Enum):
    """Service classifications for piping."""
    NORMAL = "normal"
    SEVERE_CYCLIC = "severe_cyclic"
    HIGH_PRESSURE = "high_pressure"
    CATEGORY_D = "category_d"  # B31.3 Category D (non-flammable, non-toxic)
    CATEGORY_M = "category_m"  # B31.3 Category M (toxic/lethal)


class MaterialGrade(Enum):
    """Common piping material grades."""
    CARBON_STEEL = "carbon_steel"
    STAINLESS_STEEL = "stainless_steel"
    ALLOY_STEEL = "alloy_steel"
    DUPLEX_STEEL = "duplex_steel"


class ASMEB31Standard(IndustryStandard):
    """
    ASME B31 Standard implementation for pressure piping.
    
    Provides operating limits for:
    - Design pressure
    - Operating pressure
    - Design temperature
    - Operating temperature
    - Allowable stress
    - Pressure test requirements
    - Velocity limits
    - Erosion considerations
    """
    
    def __init__(
        self,
        unit_system: UnitSystem = UnitSystem.SI,
        piping_code: PipingCode = PipingCode.B31_3
    ):
        super().__init__(unit_system)
        self.piping_code = piping_code
        self._initialize_limits()
    
    def get_standard_name(self) -> str:
        return f"ASME {self.piping_code.value.upper().replace('_', '.')}"
    
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        return [EquipmentType.PIPING]
    
    def _initialize_limits(self):
        """Initialize operating limits based on unit system and piping code."""
        if self.unit_system == UnitSystem.SI:
            self._limits = self._get_si_limits()
        else:
            self._limits = self._get_imperial_limits()
    
    def _get_si_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in SI units."""
        # Base limits for B31.3 Process Piping (most common in petrochemical)
        base_limits = {
            "piping": {
                "design_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=420.0,  # bar (typical max for B31.3)
                    warning_max=380.0,
                    alarm_max=400.0,
                    unit="bar"
                ),
                "operating_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=350.0,  # bar (90% of design typical)
                    warning_max=315.0,
                    alarm_max=332.5,
                    unit="bar"
                ),
                "design_temperature": OperatingLimits(
                    min_value=-196.0,  # °C (cryogenic)
                    max_value=650.0,   # °C (high temp service)
                    warning_max=600.0,
                    alarm_max=625.0,
                    unit="°C"
                ),
                "operating_temperature": OperatingLimits(
                    min_value=-196.0,  # °C
                    max_value=600.0,
                    warning_max=550.0,
                    alarm_max=575.0,
                    unit="°C"
                ),
                "fluid_velocity_liquid": OperatingLimits(
                    min_value=0.0,  # m/s
                    max_value=6.0,  # Erosion limit for clean liquids
                    warning_max=5.0,
                    alarm_max=5.5,
                    unit="m/s"
                ),
                "fluid_velocity_gas": OperatingLimits(
                    min_value=0.0,  # m/s
                    max_value=30.0,  # Erosion limit for gases
                    warning_max=25.0,
                    alarm_max=27.5,
                    unit="m/s"
                ),
                "fluid_velocity_steam": OperatingLimits(
                    min_value=0.0,  # m/s
                    max_value=50.0,  # Steam velocity limit
                    warning_max=45.0,
                    alarm_max=47.5,
                    unit="m/s"
                ),
                "pressure_drop": OperatingLimits(
                    min_value=0.0,  # bar/100m
                    max_value=5.0,
                    warning_max=4.0,
                    alarm_max=4.5,
                    unit="bar/100m"
                ),
                "wall_thickness": OperatingLimits(
                    min_value=2.0,  # mm (minimum practical)
                    max_value=150.0,
                    warning_min=3.0,
                    alarm_min=2.5,
                    unit="mm"
                ),
            }
        }
        
        # Adjust limits based on piping code
        if self.piping_code == PipingCode.B31_1:
            # Power piping - higher temperatures
            base_limits["piping"]["design_temperature"].max_value = 750.0
            base_limits["piping"]["operating_temperature"].max_value = 700.0
        elif self.piping_code == PipingCode.B31_4:
            # Liquid pipelines - lower pressures, higher velocities
            base_limits["piping"]["design_pressure"].max_value = 200.0
            base_limits["piping"]["fluid_velocity_liquid"].max_value = 8.0
        elif self.piping_code == PipingCode.B31_8:
            # Gas pipelines - higher pressures
            base_limits["piping"]["design_pressure"].max_value = 250.0
        
        return base_limits
    
    def _get_imperial_limits(self) -> Dict[str, Dict[str, OperatingLimits]]:
        """Get limits in Imperial units."""
        return {
            "piping": {
                "design_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=6090.0,  # psi
                    warning_max=5510.0,
                    alarm_max=5800.0,
                    unit="psi"
                ),
                "operating_pressure": OperatingLimits(
                    min_value=0.0,
                    max_value=5075.0,  # psi
                    warning_max=4568.0,
                    alarm_max=4822.0,
                    unit="psi"
                ),
                "design_temperature": OperatingLimits(
                    min_value=-320.0,  # °F
                    max_value=1200.0,
                    warning_max=1110.0,
                    alarm_max=1155.0,
                    unit="°F"
                ),
                "operating_temperature": OperatingLimits(
                    min_value=-320.0,  # °F
                    max_value=1110.0,
                    warning_max=1020.0,
                    alarm_max=1065.0,
                    unit="°F"
                ),
                "fluid_velocity_liquid": OperatingLimits(
                    min_value=0.0,  # ft/s
                    max_value=20.0,
                    warning_max=16.0,
                    alarm_max=18.0,
                    unit="ft/s"
                ),
                "fluid_velocity_gas": OperatingLimits(
                    min_value=0.0,  # ft/s
                    max_value=100.0,
                    warning_max=82.0,
                    alarm_max=90.0,
                    unit="ft/s"
                ),
            }
        }
    
    def get_limits(self, equipment_type: EquipmentType, parameter: str) -> OperatingLimits:
        """
        Get operating limits for a specific parameter.
        
        Args:
            equipment_type: Type of equipment (should be PIPING)
            parameter: Parameter name
            
        Returns:
            OperatingLimits object
            
        Raises:
            ValueError: If equipment type or parameter not supported
        """
        equipment_key = equipment_type.value
        
        if equipment_key not in self._limits:
            raise ValueError(f"Equipment type {equipment_type} not supported by ASME B31")
        
        if parameter not in self._limits[equipment_key]:
            raise ValueError(f"Parameter {parameter} not defined for {equipment_type}")
        
        return self._limits[equipment_key][parameter]
    
    def calculate_required_thickness(
        self,
        pressure: float,
        diameter: float,
        allowable_stress: float,
        weld_efficiency: float = 1.0,
        corrosion_allowance: float = 3.0
    ) -> float:
        """
        Calculate required wall thickness per ASME B31.3.
        
        t = (P * D) / (2 * S * E + P) + CA
        
        Args:
            pressure: Design pressure (bar or psi)
            diameter: Outside diameter (mm or in)
            allowable_stress: Allowable stress (MPa or psi)
            weld_efficiency: Weld joint efficiency (0.0-1.0)
            corrosion_allowance: Corrosion allowance (mm or in)
            
        Returns:
            Required thickness (mm or in)
        """
        if self.unit_system == UnitSystem.SI:
            # Convert bar to MPa
            pressure_mpa = pressure / 10.0
            numerator = pressure_mpa * diameter
            denominator = 2 * allowable_stress * weld_efficiency + pressure_mpa
        else:
            # Imperial units
            numerator = pressure * diameter
            denominator = 2 * allowable_stress * weld_efficiency + pressure
        
        if denominator <= 0:
            return corrosion_allowance
        
        thickness = (numerator / denominator) + corrosion_allowance
        return thickness
    
    def calculate_allowable_pressure(
        self,
        thickness: float,
        diameter: float,
        allowable_stress: float,
        weld_efficiency: float = 1.0,
        corrosion_allowance: float = 3.0
    ) -> float:
        """
        Calculate maximum allowable pressure.
        
        P = (2 * S * E * t) / (D - 2 * t)
        
        Args:
            thickness: Wall thickness (mm or in)
            diameter: Outside diameter (mm or in)
            allowable_stress: Allowable stress (MPa or psi)
            weld_efficiency: Weld joint efficiency (0.0-1.0)
            corrosion_allowance: Corrosion allowance (mm or in)
            
        Returns:
            Allowable pressure (bar or psi)
        """
        effective_thickness = thickness - corrosion_allowance
        
        if effective_thickness <= 0:
            return 0.0
        
        numerator = 2 * allowable_stress * weld_efficiency * effective_thickness
        denominator = diameter - 2 * effective_thickness
        
        if denominator <= 0:
            return 0.0
        
        pressure = numerator / denominator
        
        # Convert MPa to bar for SI
        if self.unit_system == UnitSystem.SI:
            pressure = pressure * 10.0
        
        return pressure
    
    def check_erosional_velocity(
        self,
        velocity: float,
        fluid_density: float,
        c_factor: float = 100.0
    ) -> bool:
        """
        Check if velocity exceeds erosional velocity limit.
        
        V_erosional = C / √ρ
        
        API RP 14E recommends C = 100 for continuous service.
        
        Args:
            velocity: Fluid velocity (m/s or ft/s)
            fluid_density: Fluid density (kg/m³ or lb/ft³)
            c_factor: Empirical constant (default 100)
            
        Returns:
            True if velocity is acceptable
        """
        import math
        
        if fluid_density <= 0:
            return False
        
        erosional_velocity = c_factor / math.sqrt(fluid_density)
        
        return velocity <= erosional_velocity
    
    def calculate_pressure_test(
        self,
        design_pressure: float,
        test_type: str = "hydrostatic"
    ) -> float:
        """
        Calculate required test pressure.
        
        ASME B31.3:
        - Hydrostatic: 1.5 × Design Pressure
        - Pneumatic: 1.1 × Design Pressure (max)
        
        Args:
            design_pressure: Design pressure (bar or psi)
            test_type: "hydrostatic" or "pneumatic"
            
        Returns:
            Test pressure (bar or psi)
        """
        if test_type.lower() == "hydrostatic":
            return design_pressure * 1.5
        elif test_type.lower() == "pneumatic":
            return design_pressure * 1.1
        else:
            raise ValueError(f"Unknown test type: {test_type}")
    
    def validate_pressure_temperature_rating(
        self,
        pressure: float,
        temperature: float,
        flange_rating: str
    ) -> bool:
        """
        Validate pressure-temperature rating for flanges.
        
        Args:
            pressure: Operating pressure (bar or psi)
            temperature: Operating temperature (°C or °F)
            flange_rating: Flange class (e.g., "150", "300", "600")
            
        Returns:
            True if within rating
        """
        # Simplified validation - actual ratings are temperature-dependent
        # and material-specific
        
        rating_limits_si = {
            "150": 20.0,   # bar at ambient
            "300": 51.0,
            "600": 102.0,
            "900": 153.0,
            "1500": 255.0,
            "2500": 425.0,
        }
        
        rating_limits_imperial = {
            "150": 290.0,   # psi at ambient
            "300": 740.0,
            "600": 1480.0,
            "900": 2220.0,
            "1500": 3705.0,
            "2500": 6170.0,
        }
        
        limits = rating_limits_si if self.unit_system == UnitSystem.SI else rating_limits_imperial
        
        max_pressure = limits.get(flange_rating)
        if max_pressure is None:
            return False
        
        # Apply temperature derating (simplified)
        if self.unit_system == UnitSystem.SI:
            if temperature > 200:
                max_pressure *= 0.8
            if temperature > 400:
                max_pressure *= 0.6
        else:
            if temperature > 392:
                max_pressure *= 0.8
            if temperature > 752:
                max_pressure *= 0.6
        
        return pressure <= max_pressure


# Register standard with factory
StandardFactory.register_standard("asme b31", ASMEB31Standard)
StandardFactory.register_standard("asme b31.3", lambda us: ASMEB31Standard(us, PipingCode.B31_3))
StandardFactory.register_standard("asme b31.1", lambda us: ASMEB31Standard(us, PipingCode.B31_1))
StandardFactory.register_standard("asme b31.4", lambda us: ASMEB31Standard(us, PipingCode.B31_4))
StandardFactory.register_standard("asme b31.8", lambda us: ASMEB31Standard(us, PipingCode.B31_8))