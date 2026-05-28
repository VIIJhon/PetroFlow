"""
core/physical_validator.py
===========================
PetroFlow Enterprise — Fail-Safe Physical Input Validator

Validates operating parameters against physically possible bounds
(based on thermodynamics, fluid mechanics, and API standards).

Blocks ML predictions and emits structured alerts when the user
supplies physically impossible or operationally extreme values.

All bounds are stored in SI units. The validator converts imperial
inputs before checking.

Audit integration
-----------------
Every blocked validation is emitted via the audit_logging_service
under the 'security' category with action='INPUT_BLOCKED'.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bound definitions (all in SI)
# ---------------------------------------------------------------------------

@dataclass
class BoundSpec:
    """Physical bounds for a single variable."""
    name:        str
    unit_si:     str
    absolute_min: float          # Physically impossible below this
    absolute_max: float          # Physically impossible above this
    warn_min:    Optional[float] # Below this → warning but allowed
    warn_max:    Optional[float] # Above this → warning but allowed
    description: str


# fmt: off
PHYSICAL_BOUNDS: Dict[str, BoundSpec] = {
    "temperature": BoundSpec(
        name         = "Inlet Temperature",
        unit_si      = "°C",
        absolute_min = -273.15,   # Absolute zero
        absolute_max =  600.0,    # Practical max for process equipment
        warn_min     =  -40.0,    # Cryogenic process boundary
        warn_max     =  150.0,    # Typical centrifugal pump limit
        description  = "Temperature must be above absolute zero (−273.15 °C)",
    ),
    "discharge_temperature": BoundSpec(
        name         = "Discharge Temperature",
        unit_si      = "°C",
        absolute_min = -273.15,
        absolute_max =  600.0,
        warn_min     =  -40.0,
        warn_max     =  200.0,
        description  = "Discharge temperature must be above absolute zero",
    ),
    "pressure": BoundSpec(
        name         = "Operating Pressure",
        unit_si      = "Bar",
        absolute_min =  0.0,      # Absolute vacuum
        absolute_max =  700.0,    # Ultra-high pressure process limit
        warn_min     =  0.5,      # Below this → possible cavitation
        warn_max     =  50.0,     # Standard pump design limit
        description  = "Gauge pressure must be ≥ 0 Bar (absolute vacuum)",
    ),
    "differential_pressure": BoundSpec(
        name         = "Differential Pressure",
        unit_si      = "Bar",
        absolute_min =  0.0,
        absolute_max =  300.0,
        warn_min     =  None,
        warn_max     =  30.0,
        description  = "ΔP must be non-negative",
    ),
    "vibration": BoundSpec(
        name         = "Vibration Velocity",
        unit_si      = "mm/s",
        absolute_min =  0.0,
        absolute_max =  100.0,    # Beyond this: structural failure imminent
        warn_min     =  None,
        warn_max     =  7.1,      # ISO 10816 Class III severity D boundary
        description  = "Vibration ≥ 0 mm/s; > 7.1 mm/s is ISO Class D (dangerous)",
    ),
    "flow_rate": BoundSpec(
        name         = "Flow Rate",
        unit_si      = "m³/h",
        absolute_min =  0.0,
        absolute_max =  50000.0,  # Large pipeline pumps
        warn_min     =  1.0,      # Below minimum continuous flow → cavitation
        warn_max     =  500.0,    # Application-specific
        description  = "Flow rate must be ≥ 0 m³/h",
    ),
    "rpm": BoundSpec(
        name         = "Rotational Speed",
        unit_si      = "RPM",
        absolute_min =  0.0,
        absolute_max =  50000.0,  # High-speed turbo machinery
        warn_min     =  100.0,    # Near-zero → transient / startup
        warn_max     =  5000.0,   # Standard centrifugal pump range
        description  = "RPM must be ≥ 0; > 50,000 is physically implausible",
    ),
    "operating_hours": BoundSpec(
        name         = "Operating Hours",
        unit_si      = "h",
        absolute_min =  0.0,
        absolute_max =  876000.0,  # 100 years of continuous operation
        warn_min     =  None,
        warn_max     =  87600.0,   # 10 years — overhaul expected
        description  = "Operating hours must be ≥ 0",
    ),
    "power": BoundSpec(
        name         = "Power Consumption",
        unit_si      = "kW",
        absolute_min =  0.0,
        absolute_max =  50000.0,
        warn_min     =  None,
        warn_max     =  2000.0,
        description  = "Power must be ≥ 0 kW",
    ),
    "fluid_density": BoundSpec(
        name         = "Fluid Density",
        unit_si      = "kg/m³",
        absolute_min =  0.001,    # Near-vacuum gas
        absolute_max =  25000.0,  # Densest known fluid
        warn_min     =  400.0,    # Light hydrocarbons
        warn_max     =  1200.0,   # Brine / dense fluids
        description  = "Density must be > 0 kg/m³",
    ),
}
# fmt: on


# ---------------------------------------------------------------------------
# API 670 / ISO 10816-3 Equipment-specific vibration limits (SI: mm/s RMS)
# Zone A: 0-2.3 | Zone B: 2.3-4.5 | Zone C: 4.5-7.1 | Zone D: >7.1
# ---------------------------------------------------------------------------

_EQUIPMENT_VIBRATION_BOUNDS: dict[str, BoundSpec] = {
    "pump": BoundSpec(
        name         = "Pump Vibration (API 610 / ISO 10816-3)",
        unit_si      = "mm/s",
        absolute_min = 0.0,
        absolute_max = 12.5,
        warn_min     = None,
        warn_max     = 7.1,
        description  = "ISO 10816-3 Zone D (>7.1 mm/s) or API 670 Danger (>12.5 mm/s)",
    ),
    "compressor": BoundSpec(
        name         = "Compressor Radial Vibration (API 670 / API 617)",
        unit_si      = "mm/s",
        absolute_min = 0.0,
        absolute_max = 10.0,
        warn_min     = None,
        warn_max     = 5.0,
        description  = "API 670 Alert >5.0 mm/s, Danger >10.0 mm/s",
    ),
    "turbine": BoundSpec(
        name         = "Turbine Axial Vibration (API 670 / API 612)",
        unit_si      = "mm/s",
        absolute_min = 0.0,
        absolute_max = 9.0,
        warn_min     = None,
        warn_max     = 4.5,
        description  = "API 670 Alert >4.5 mm/s, Danger >9.0 mm/s",
    ),
}

_EQUIPMENT_DISPLACEMENT_BOUNDS: dict[str, BoundSpec] = {
    "pump": BoundSpec(
        name="Shaft Displacement Pump (API 670)", unit_si="um pk-pk",
        absolute_min=0.0, absolute_max=127.0, warn_min=None, warn_max=76.0,
        description="API 670: Alert >76 um, Danger >127 um shaft displacement",
    ),
    "compressor": BoundSpec(
        name="Shaft Displacement Compressor (API 670)", unit_si="um pk-pk",
        absolute_min=0.0, absolute_max=127.0, warn_min=None, warn_max=76.0,
        description="API 670: Alert >76 um, Danger >127 um shaft displacement",
    ),
    "turbine": BoundSpec(
        name="Shaft Displacement Turbine (API 670)", unit_si="um pk-pk",
        absolute_min=0.0, absolute_max=127.0, warn_min=None, warn_max=76.0,
        description="API 670: Alert >76 um, Danger >127 um shaft displacement",
    ),
}


def get_bounds_for_equipment(equipment_type: str, parameter: str) -> 'BoundSpec | None':
    """
    Return the correct BoundSpec for a given equipment type and parameter,
    applying API 670 / ISO 10816-3 limits where applicable.
    Falls back to generic PHYSICAL_BOUNDS for non-vibration parameters.
    """
    eq = equipment_type.lower()
    if parameter in ("vibration", "radial_vibration", "axial_vibration"):
        return _EQUIPMENT_VIBRATION_BOUNDS.get(eq, PHYSICAL_BOUNDS.get("vibration"))
    if parameter == "shaft_displacement":
        return _EQUIPMENT_DISPLACEMENT_BOUNDS.get(eq)
    return PHYSICAL_BOUNDS.get(parameter)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """One validation finding (error or warning)."""
    variable:  str
    severity:  str          # "error" | "warning"
    message:   str
    value_si:  float
    unit_si:   str
    bound:     float
    bound_type: str         # "absolute_min" | "absolute_max" | "warn_min" | "warn_max"


@dataclass
class ValidationResult:
    """Aggregate result of a full parameter validation pass."""
    valid:    bool
    blocked:  bool                          # True → ML calculation must be blocked
    issues:   List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def summary(self) -> str:
        lines = []
        for issue in self.issues:
            prefix = "[BLOCKED]" if issue.severity == "error" else "[WARNING]"
            lines.append(f"{prefix} {issue.variable}: {issue.message}")
        return "\n".join(lines) if lines else "[OK] All parameters within physical bounds"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class PhysicalValidator:
    """
    Validates operating parameters against physical bounds.

    Usage
    -----
        validator = PhysicalValidator()
        result = validator.validate({
            "temperature":  75.0,   # °C
            "pressure":     25.0,   # Bar
            "vibration":     2.3,   # mm/s
            "flow_rate":   120.0,   # m³/h
            "rpm":         2500.0,
            "operating_hours": 12450.0,
        })
        if result.blocked:
            st.error(result.summary())
        elif result.warnings:
            st.warning(result.summary())
    """

    def validate(
        self,
        params_si: Dict[str, float],
        log_to_audit: bool = True,
    ) -> ValidationResult:
        """
        Validate a dictionary of {variable_name: value_in_SI}.

        Parameters
        ----------
        params_si      : values in SI units as defined in PHYSICAL_BOUNDS
        log_to_audit   : emit audit log entries for each blocked variable

        Returns
        -------
        ValidationResult with .blocked=True if any absolute bound is violated.
        """
        issues: List[ValidationIssue] = []
        blocked = False

        for var_name, value in params_si.items():
            spec = PHYSICAL_BOUNDS.get(var_name)
            if spec is None:
                continue  # Unknown variable → skip silently

            # --- Absolute minimum (error) ---------------------------------
            if value < spec.absolute_min:
                issue = ValidationIssue(
                    variable   = spec.name,
                    severity   = "error",
                    message    = (
                        f"Value {value:.4g} {spec.unit_si} is below the "
                        f"physical minimum ({spec.absolute_min} {spec.unit_si}). "
                        f"Calculation blocked."
                    ),
                    value_si   = value,
                    unit_si    = spec.unit_si,
                    bound      = spec.absolute_min,
                    bound_type = "absolute_min",
                )
                issues.append(issue)
                blocked = True
                if log_to_audit:
                    self._log_block(var_name, issue)

            # --- Absolute maximum (error) ---------------------------------
            elif value > spec.absolute_max:
                issue = ValidationIssue(
                    variable   = spec.name,
                    severity   = "error",
                    message    = (
                        f"Value {value:.4g} {spec.unit_si} exceeds the "
                        f"physical maximum ({spec.absolute_max} {spec.unit_si}). "
                        f"Calculation blocked."
                    ),
                    value_si   = value,
                    unit_si    = spec.unit_si,
                    bound      = spec.absolute_max,
                    bound_type = "absolute_max",
                )
                issues.append(issue)
                blocked = True
                if log_to_audit:
                    self._log_block(var_name, issue)

            else:
                # --- Warn minimum ----------------------------------------
                if spec.warn_min is not None and value < spec.warn_min:
                    issues.append(ValidationIssue(
                        variable   = spec.name,
                        severity   = "warning",
                        message    = (
                            f"Value {value:.4g} {spec.unit_si} is below the "
                            f"recommended minimum ({spec.warn_min} {spec.unit_si}). "
                            f"Proceed with caution."
                        ),
                        value_si   = value,
                        unit_si    = spec.unit_si,
                        bound      = spec.warn_min,
                        bound_type = "warn_min",
                    ))

                # --- Warn maximum ----------------------------------------
                if spec.warn_max is not None and value > spec.warn_max:
                    issues.append(ValidationIssue(
                        variable   = spec.name,
                        severity   = "warning",
                        message    = (
                            f"Value {value:.4g} {spec.unit_si} exceeds the "
                            f"recommended maximum ({spec.warn_max} {spec.unit_si}). "
                            f"Review operating conditions."
                        ),
                        value_si   = value,
                        unit_si    = spec.unit_si,
                        bound      = spec.warn_max,
                        bound_type = "warn_max",
                    ))

        return ValidationResult(
            valid   = not blocked,
            blocked = blocked,
            issues  = issues,
        )

    @staticmethod
    def _log_block(var_name: str, issue: ValidationIssue) -> None:
        """Emit an audit log entry for a blocked parameter."""
        try:
            from core.audit_logging_service import get_audit_logger
            al = get_audit_logger()
            al.log_security(
                f"INPUT BLOCKED — {issue.variable}: {issue.message}",
                action="INPUT_BLOCKED",
                details={
                    "variable":   var_name,
                    "value_si":   issue.value_si,
                    "unit_si":    issue.unit_si,
                    "bound":      issue.bound,
                    "bound_type": issue.bound_type,
                },
            )
        except Exception:
            # Never let audit failure block the main flow
            logger.warning("Could not emit audit log for input block: %s", var_name)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------
_validator = PhysicalValidator()


def validate(params_si: Dict[str, float], log_to_audit: bool = True) -> ValidationResult:
    """Module-level shortcut."""
    return _validator.validate(params_si, log_to_audit)


def validate_single(var_name: str, value_si: float) -> ValidationResult:
    """Validate a single variable."""
    return _validator.validate({var_name: value_si})
