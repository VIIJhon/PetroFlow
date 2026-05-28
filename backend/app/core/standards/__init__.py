"""
Industry Standards Module
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Centralized industry standards for equipment validation and safety envelope checks.
Supports API 610, 617, 618, 611, 612, ISO 10816, and ASME B31 standards.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class EquipmentType(Enum):
    """Equipment types supported by industry standards."""
    PUMP_CENTRIFUGAL = "pump_centrifugal"
    PUMP_POSITIVE_DISPLACEMENT = "pump_positive_displacement"
    COMPRESSOR_CENTRIFUGAL = "compressor_centrifugal"
    COMPRESSOR_RECIPROCATING = "compressor_reciprocating"
    TURBINE_STEAM = "turbine_steam"
    TURBINE_GAS = "turbine_gas"
    PIPING = "piping"
    GENERIC = "generic"


class UnitSystem(Enum):
    """Unit system for measurements."""
    SI = "si"
    IMPERIAL = "imperial"


class ValidationSeverity(Enum):
    """Severity levels for validation results."""
    OK = "ok"
    WARNING = "warning"
    ALARM = "alarm"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    parameter: str
    value: float
    limit: float
    severity: ValidationSeverity
    message: str
    margin_percent: float
    unit: str


@dataclass
class OperatingLimits:
    """Operating limits for a parameter."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    warning_min: Optional[float] = None
    warning_max: Optional[float] = None
    alarm_min: Optional[float] = None
    alarm_max: Optional[float] = None
    unit: str = ""


class IndustryStandard(ABC):
    """
    Base class for all industry standards.
    
    Provides common interface for validation, unit conversion, and limit checking.
    All specific standards (API 610, 617, etc.) inherit from this class.
    """
    
    def __init__(self, unit_system: UnitSystem = UnitSystem.SI):
        """
        Initialize industry standard.
        
        Args:
            unit_system: Unit system to use (SI or Imperial)
        """
        self.unit_system = unit_system
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_standard_name(self) -> str:
        """Return the standard name (e.g., 'API 610')."""
        pass
    
    @abstractmethod
    def get_supported_equipment_types(self) -> List[EquipmentType]:
        """Return list of equipment types supported by this standard."""
        pass
    
    @abstractmethod
    def get_limits(self, equipment_type: EquipmentType, parameter: str) -> OperatingLimits:
        """
        Get operating limits for a specific parameter.
        
        Args:
            equipment_type: Type of equipment
            parameter: Parameter name (e.g., 'pressure', 'temperature', 'vibration')
            
        Returns:
            OperatingLimits object with min/max/warning/alarm values
        """
        pass
    
    def validate_parameter(
        self,
        equipment_type: EquipmentType,
        parameter: str,
        value: float,
        unit: str
    ) -> ValidationResult:
        """
        Validate a parameter value against standard limits.
        
        Args:
            equipment_type: Type of equipment
            parameter: Parameter name
            value: Current value
            unit: Unit of measurement
            
        Returns:
            ValidationResult with severity and details
        """
        limits = self.get_limits(equipment_type, parameter)
        
        # Determine severity
        severity = ValidationSeverity.OK
        message = f"{parameter} within normal operating range"
        margin_percent = 100.0
        
        if limits.max_value is not None:
            if value > limits.max_value:
                severity = ValidationSeverity.CRITICAL
                message = f"{parameter} exceeds maximum limit"
                margin_percent = ((value - limits.max_value) / limits.max_value) * 100
            elif limits.alarm_max is not None and value > limits.alarm_max:
                severity = ValidationSeverity.ALARM
                message = f"{parameter} exceeds alarm threshold"
                margin_percent = ((limits.max_value - value) / limits.max_value) * 100
            elif limits.warning_max is not None and value > limits.warning_max:
                severity = ValidationSeverity.WARNING
                message = f"{parameter} approaching maximum limit"
                margin_percent = ((limits.max_value - value) / limits.max_value) * 100
        
        if limits.min_value is not None:
            if value < limits.min_value:
                severity = ValidationSeverity.CRITICAL
                message = f"{parameter} below minimum limit"
                margin_percent = ((limits.min_value - value) / limits.min_value) * 100
            elif limits.alarm_min is not None and value < limits.alarm_min:
                severity = ValidationSeverity.ALARM
                message = f"{parameter} below alarm threshold"
                margin_percent = ((value - limits.min_value) / limits.min_value) * 100
            elif limits.warning_min is not None and value < limits.warning_min:
                severity = ValidationSeverity.WARNING
                message = f"{parameter} approaching minimum limit"
                margin_percent = ((value - limits.min_value) / limits.min_value) * 100
        
        self.logger.info(
            f"Validated {parameter}={value}{unit} for {equipment_type.value}: {severity.value}",
            extra={
                "standard": self.get_standard_name(),
                "equipment_type": equipment_type.value,
                "parameter": parameter,
                "value": value,
                "severity": severity.value,
                "margin_percent": margin_percent
            }
        )
        
        return ValidationResult(
            parameter=parameter,
            value=value,
            limit=limits.max_value if limits.max_value else limits.min_value,
            severity=severity,
            message=message,
            margin_percent=margin_percent,
            unit=unit
        )
    
    def convert_unit(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert value between units.
        
        Args:
            value: Value to convert
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Converted value
        """
        # Common conversions
        conversions = {
            # Pressure
            ("psi", "bar"): lambda x: x * 0.0689476,
            ("bar", "psi"): lambda x: x * 14.5038,
            ("psi", "kpa"): lambda x: x * 6.89476,
            ("kpa", "psi"): lambda x: x * 0.145038,
            # Temperature
            ("f", "c"): lambda x: (x - 32) * 5/9,
            ("c", "f"): lambda x: x * 9/5 + 32,
            ("c", "k"): lambda x: x + 273.15,
            ("k", "c"): lambda x: x - 273.15,
            # Flow
            ("gpm", "m3/h"): lambda x: x * 0.227125,
            ("m3/h", "gpm"): lambda x: x * 4.40287,
            # Power
            ("hp", "kw"): lambda x: x * 0.745699,
            ("kw", "hp"): lambda x: x * 1.34102,
            # Vibration
            ("in/s", "mm/s"): lambda x: x * 25.4,
            ("mm/s", "in/s"): lambda x: x * 0.0393701,
        }
        
        key = (from_unit.lower(), to_unit.lower())
        if key in conversions:
            return conversions[key](value)
        
        # If no conversion needed
        if from_unit.lower() == to_unit.lower():
            return value
        
        raise ValueError(f"Conversion from {from_unit} to {to_unit} not supported")


class StandardFactory:
    """Factory for creating industry standard instances."""
    
    _standards: Dict[str, type] = {}
    
    @classmethod
    def register_standard(cls, standard_name: str, standard_class: type):
        """Register a standard class."""
        cls._standards[standard_name.lower()] = standard_class
    
    @classmethod
    def get_standard(
        cls,
        standard_name: str,
        unit_system: UnitSystem = UnitSystem.SI
    ) -> IndustryStandard:
        """
        Get an instance of a standard by name.
        
        Args:
            standard_name: Name of standard (e.g., 'API 610', 'ISO 10816')
            unit_system: Unit system to use
            
        Returns:
            Instance of the requested standard
            
        Raises:
            ValueError: If standard not found
        """
        standard_class = cls._standards.get(standard_name.lower())
        if not standard_class:
            raise ValueError(f"Standard '{standard_name}' not registered")
        
        return standard_class(unit_system)
    
    @classmethod
    def get_standard_for_equipment(
        cls,
        equipment_type: EquipmentType,
        unit_system: UnitSystem = UnitSystem.SI
    ) -> List[IndustryStandard]:
        """
        Get all standards applicable to an equipment type.
        
        Args:
            equipment_type: Type of equipment
            unit_system: Unit system to use
            
        Returns:
            List of applicable standard instances
        """
        applicable_standards = []
        
        for standard_class in cls._standards.values():
            instance = standard_class(unit_system)
            if equipment_type in instance.get_supported_equipment_types():
                applicable_standards.append(instance)
        
        return applicable_standards


# Export main classes
__all__ = [
    "IndustryStandard",
    "StandardFactory",
    "EquipmentType",
    "UnitSystem",
    "ValidationSeverity",
    "ValidationResult",
    "OperatingLimits",
]