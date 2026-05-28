"""
Safety Envelope Validator
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Centralized safety envelope validation using industry standards.
Validates operating points against API, ISO, and ASME limits.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .standards import (
    IndustryStandard,
    StandardFactory,
    EquipmentType,
    UnitSystem,
    ValidationResult,
    ValidationSeverity
)

logger = logging.getLogger(__name__)


@dataclass
class OperatingPoint:
    """Represents a single operating point with multiple parameters."""
    equipment_id: str
    equipment_type: EquipmentType
    timestamp: datetime
    parameters: Dict[str, float]  # {parameter_name: value}
    units: Dict[str, str]  # {parameter_name: unit}
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyEnvelopeResult:
    """Result of safety envelope validation."""
    equipment_id: str
    timestamp: datetime
    overall_status: ValidationSeverity
    validations: List[ValidationResult]
    alarms: List[str]
    warnings: List[str]
    recommendations: List[str]
    safety_margins: Dict[str, float]  # {parameter: margin_percent}


class SafetyEnvelopeValidator:
    """
    Validates equipment operating points against industry standards.
    
    Features:
    - Multi-standard validation (API, ISO, ASME)
    - Automatic standard selection based on equipment type
    - Configurable alarm thresholds
    - Safety margin calculation
    - Structured logging of validation decisions
    - Dependency injection for standards (no hardcoding)
    """
    
    def __init__(
        self,
        unit_system: UnitSystem = UnitSystem.SI,
        standards: Optional[List[str]] = None,
        enable_logging: bool = True
    ):
        """
        Initialize safety envelope validator.
        
        Args:
            unit_system: Unit system to use (SI or Imperial)
            standards: List of standard names to use (None = auto-detect)
            enable_logging: Enable structured logging
        """
        self.unit_system = unit_system
        self.enable_logging = enable_logging
        self.logger = logging.getLogger(f"{__name__}.SafetyEnvelopeValidator")
        
        # Load standards
        self.standards: Dict[str, IndustryStandard] = {}
        if standards:
            for std_name in standards:
                try:
                    self.standards[std_name] = StandardFactory.get_standard(
                        std_name, unit_system
                    )
                except ValueError as e:
                    self.logger.warning(f"Failed to load standard {std_name}: {e}")
        
        self._log_initialization()
    
    def _log_initialization(self):
        """Log validator initialization."""
        if self.enable_logging:
            self.logger.info(
                "SafetyEnvelopeValidator initialized",
                extra={
                    "unit_system": self.unit_system.value,
                    "standards_loaded": list(self.standards.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    def validate_operating_point(
        self,
        operating_point: OperatingPoint,
        standards_override: Optional[List[str]] = None
    ) -> SafetyEnvelopeResult:
        """
        Validate an operating point against applicable standards.
        
        Args:
            operating_point: Operating point to validate
            standards_override: Override auto-detected standards
            
        Returns:
            SafetyEnvelopeResult with validation details
        """
        start_time = datetime.utcnow()
        
        # Get applicable standards
        if standards_override:
            applicable_standards = [
                StandardFactory.get_standard(std, self.unit_system)
                for std in standards_override
            ]
        else:
            applicable_standards = self._get_applicable_standards(
                operating_point.equipment_type
            )
        
        # Validate each parameter against each standard
        all_validations: List[ValidationResult] = []
        alarms: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []
        safety_margins: Dict[str, float] = {}
        
        for parameter, value in operating_point.parameters.items():
            unit = operating_point.units.get(parameter, "")
            
            for standard in applicable_standards:
                try:
                    validation = standard.validate_parameter(
                        operating_point.equipment_type,
                        parameter,
                        value,
                        unit
                    )
                    
                    all_validations.append(validation)
                    safety_margins[parameter] = validation.margin_percent
                    
                    # Categorize by severity
                    if validation.severity == ValidationSeverity.ALARM:
                        alarms.append(
                            f"{parameter}: {validation.message} "
                            f"(Standard: {standard.get_standard_name()})"
                        )
                    elif validation.severity == ValidationSeverity.WARNING:
                        warnings.append(
                            f"{parameter}: {validation.message} "
                            f"(Standard: {standard.get_standard_name()})"
                        )
                    elif validation.severity == ValidationSeverity.CRITICAL:
                        alarms.append(
                            f"CRITICAL - {parameter}: {validation.message} "
                            f"(Standard: {standard.get_standard_name()})"
                        )
                        recommendations.append(
                            f"Immediate action required for {parameter}"
                        )
                    
                except ValueError as e:
                    # Parameter not defined in this standard
                    self.logger.debug(
                        f"Parameter {parameter} not defined in {standard.get_standard_name()}: {e}"
                    )
                    continue
        
        # Determine overall status
        overall_status = self._determine_overall_status(all_validations)
        
        # Create result
        result = SafetyEnvelopeResult(
            equipment_id=operating_point.equipment_id,
            timestamp=operating_point.timestamp,
            overall_status=overall_status,
            validations=all_validations,
            alarms=alarms,
            warnings=warnings,
            recommendations=recommendations,
            safety_margins=safety_margins
        )
        
        # Log validation
        self._log_validation(operating_point, result, start_time)
        
        return result
    
    def _get_applicable_standards(
        self,
        equipment_type: EquipmentType
    ) -> List[IndustryStandard]:
        """
        Get standards applicable to equipment type.
        
        Args:
            equipment_type: Type of equipment
            
        Returns:
            List of applicable standard instances
        """
        if self.standards:
            # Use pre-loaded standards
            return [
                std for std in self.standards.values()
                if equipment_type in std.get_supported_equipment_types()
            ]
        else:
            # Auto-detect from factory
            return StandardFactory.get_standard_for_equipment(
                equipment_type,
                self.unit_system
            )
    
    def _determine_overall_status(
        self,
        validations: List[ValidationResult]
    ) -> ValidationSeverity:
        """
        Determine overall validation status.
        
        Args:
            validations: List of validation results
            
        Returns:
            Overall severity level
        """
        if not validations:
            return ValidationSeverity.OK
        
        # Worst case determines overall status
        severities = [v.severity for v in validations]
        
        if ValidationSeverity.CRITICAL in severities:
            return ValidationSeverity.CRITICAL
        elif ValidationSeverity.ALARM in severities:
            return ValidationSeverity.ALARM
        elif ValidationSeverity.WARNING in severities:
            return ValidationSeverity.WARNING
        else:
            return ValidationSeverity.OK
    
    def _log_validation(
        self,
        operating_point: OperatingPoint,
        result: SafetyEnvelopeResult,
        start_time: datetime
    ):
        """Log validation decision with structured data."""
        if not self.enable_logging:
            return
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        self.logger.info(
            f"Validated {operating_point.equipment_id}: {result.overall_status.value}",
            extra={
                "equipment_id": operating_point.equipment_id,
                "equipment_type": operating_point.equipment_type.value,
                "overall_status": result.overall_status.value,
                "alarm_count": len(result.alarms),
                "warning_count": len(result.warnings),
                "validation_count": len(result.validations),
                "duration_ms": duration_ms,
                "timestamp": operating_point.timestamp.isoformat()
            }
        )
    
    def get_safety_margins(
        self,
        operating_point: OperatingPoint
    ) -> Dict[str, float]:
        """
        Calculate safety margins for all parameters.
        
        Args:
            operating_point: Operating point to analyze
            
        Returns:
            Dictionary of {parameter: margin_percent}
        """
        result = self.validate_operating_point(operating_point)
        return result.safety_margins
    
    def check_alarm_conditions(
        self,
        operating_point: OperatingPoint,
        alarm_threshold: ValidationSeverity = ValidationSeverity.ALARM
    ) -> Tuple[bool, List[str]]:
        """
        Check if any alarm conditions are present.
        
        Args:
            operating_point: Operating point to check
            alarm_threshold: Minimum severity to trigger alarm
            
        Returns:
            Tuple of (has_alarms, alarm_messages)
        """
        result = self.validate_operating_point(operating_point)
        
        # Check if overall status meets threshold
        severity_order = [
            ValidationSeverity.OK,
            ValidationSeverity.WARNING,
            ValidationSeverity.ALARM,
            ValidationSeverity.CRITICAL
        ]
        
        has_alarms = (
            severity_order.index(result.overall_status) >= 
            severity_order.index(alarm_threshold)
        )
        
        alarm_messages = result.alarms if has_alarms else []
        
        return has_alarms, alarm_messages
    
    def validate_batch(
        self,
        operating_points: List[OperatingPoint]
    ) -> List[SafetyEnvelopeResult]:
        """
        Validate multiple operating points.
        
        Args:
            operating_points: List of operating points
            
        Returns:
            List of validation results
        """
        results = []
        
        for op in operating_points:
            try:
                result = self.validate_operating_point(op)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    f"Failed to validate {op.equipment_id}: {e}",
                    extra={
                        "equipment_id": op.equipment_id,
                        "error": str(e)
                    }
                )
        
        return results
    
    def get_critical_parameters(
        self,
        result: SafetyEnvelopeResult,
        min_severity: ValidationSeverity = ValidationSeverity.ALARM
    ) -> List[str]:
        """
        Get list of parameters that exceed severity threshold.
        
        Args:
            result: Validation result
            min_severity: Minimum severity to include
            
        Returns:
            List of parameter names
        """
        severity_order = [
            ValidationSeverity.OK,
            ValidationSeverity.WARNING,
            ValidationSeverity.ALARM,
            ValidationSeverity.CRITICAL
        ]
        
        min_index = severity_order.index(min_severity)
        
        critical_params = [
            v.parameter for v in result.validations
            if severity_order.index(v.severity) >= min_index
        ]
        
        return list(set(critical_params))  # Remove duplicates
    
    def generate_report(
        self,
        result: SafetyEnvelopeResult
    ) -> str:
        """
        Generate human-readable validation report.
        
        Args:
            result: Validation result
            
        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            f"Safety Envelope Validation Report",
            f"Equipment: {result.equipment_id}",
            f"Timestamp: {result.timestamp.isoformat()}",
            f"Overall Status: {result.overall_status.value.upper()}",
            "=" * 60,
            ""
        ]
        
        if result.alarms:
            lines.append("ALARMS:")
            for alarm in result.alarms:
                lines.append(f"  ⚠️  {alarm}")
            lines.append("")
        
        if result.warnings:
            lines.append("WARNINGS:")
            for warning in result.warnings:
                lines.append(f"  ⚡ {warning}")
            lines.append("")
        
        if result.recommendations:
            lines.append("RECOMMENDATIONS:")
            for rec in result.recommendations:
                lines.append(f"  💡 {rec}")
            lines.append("")
        
        lines.append("SAFETY MARGINS:")
        for param, margin in result.safety_margins.items():
            status = "✓" if margin > 10 else "⚠️"
            lines.append(f"  {status} {param}: {margin:.1f}%")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


# Convenience function for quick validation
def validate_equipment(
    equipment_id: str,
    equipment_type: EquipmentType,
    parameters: Dict[str, float],
    units: Dict[str, str],
    unit_system: UnitSystem = UnitSystem.SI
) -> SafetyEnvelopeResult:
    """
    Quick validation function for single equipment.
    
    Args:
        equipment_id: Equipment identifier
        equipment_type: Type of equipment
        parameters: Dictionary of parameter values
        units: Dictionary of parameter units
        unit_system: Unit system to use
        
    Returns:
        SafetyEnvelopeResult
    """
    validator = SafetyEnvelopeValidator(unit_system=unit_system)
    
    operating_point = OperatingPoint(
        equipment_id=equipment_id,
        equipment_type=equipment_type,
        timestamp=datetime.utcnow(),
        parameters=parameters,
        units=units
    )
    
    return validator.validate_operating_point(operating_point)