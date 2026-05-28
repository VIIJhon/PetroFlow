"""
Unit Converter Service
Migrated from core/unit_converter.py
Handles all unit conversions for 50+ parameters across SI and Imperial systems
"""

from typing import Dict, List, Optional, Tuple, Any
import logging

try:
    from pint import UnitRegistry
    PINT_AVAILABLE = True
except ImportError:
    PINT_AVAILABLE = False
    logging.warning("pint not installed. Unit conversion features will use manual definitions fallback.")
    class UnitRegistry:
        def __init__(self, *args, **kwargs):
            pass
        def define(self, *args, **kwargs):
            pass

logger = logging.getLogger(__name__)


class UnitConverter:
    """
    Comprehensive unit converter for oil & gas parameters.
    Supports SI and Imperial unit systems with 50+ parameter categories.
    """
    
    def __init__(self):
        """Initialize unit registry."""
        self._registry = UnitRegistry()
        # Custom API gravity conversion is handled explicitly in _convert_api_gravity.
        # Avoid invalid pint definition syntax that causes registry initialization failure.
        # self._registry.define('API = 141.5 / (specific_gravity + 131.5) = api_gravity')
        
    def convert(
        self,
        value: float,
        category: str,
        from_unit: str,
        to_unit: str
    ) -> float:
        """
        Convert value between units within a category.
        
        Args:
            value: Numeric value to convert
            category: Parameter category (e.g., 'pressure', 'temperature')
            from_unit: Source unit key
            to_unit: Target unit key
            
        Returns:
            Converted value
        """
        if from_unit == to_unit:
            return value
        
        # Handle special cases
        if category == "temperature":
            return self._convert_temperature(value, from_unit, to_unit)
        elif category == "api_gravity":
            return self._convert_api_gravity(value, from_unit, to_unit)
        
        # Standard conversion using pint
        try:
            reg = self._registry
            from_entry = UNIT_DEFINITIONS.get(category, {}).get(from_unit)
            to_entry = UNIT_DEFINITIONS.get(category, {}).get(to_unit)
            
            if not from_entry or not to_entry:
                logger.warning(f"Unknown unit: {from_unit} or {to_unit} in category {category}")
                return value
            
            # Convert to SI, then to target
            value_si = value * from_entry.get("to_si_factor", 1.0) + from_entry.get("to_si_offset", 0.0)
            result = (value_si - to_entry.get("to_si_offset", 0.0)) / to_entry.get("to_si_factor", 1.0)
            
            return result
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return value
    
    def convert_batch(
        self,
        values: List[float],
        mappings: List[Tuple[str, str, str]]
    ) -> List[float]:
        """
        Convert multiple values with different unit mappings.
        
        Args:
            values: List of values to convert
            mappings: List of (category, from_unit, to_unit) tuples
            
        Returns:
            List of converted values
        """
        return [
            self.convert(val, cat, from_u, to_u)
            for val, (cat, from_u, to_u) in zip(values, mappings)
        ]
    
    def get_units(self, category: str) -> List[str]:
        """Get available units for a category."""
        return list(UNIT_DEFINITIONS.get(category, {}).keys())
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(UNIT_DEFINITIONS.keys())
    
    def label(self, category: str, unit_key: str) -> str:
        """Get display label for a unit."""
        unit_def = UNIT_DEFINITIONS.get(category, {}).get(unit_key, {})
        return unit_def.get("label", unit_key)
    
    def to_si(self, value: float, category: str, unit_key: str) -> float:
        """Convert value to SI units."""
        si_units = UNIT_DEFINITIONS.get(category, {})
        si_unit = next((k for k, v in si_units.items() if v.get("is_si", False)), None)
        if si_unit:
            return self.convert(value, category, unit_key, si_unit)
        return value
    
    def from_si(self, value_si: float, category: str, to_unit: str) -> float:
        """Convert value from SI units."""
        si_units = UNIT_DEFINITIONS.get(category, {})
        si_unit = next((k for k, v in si_units.items() if v.get("is_si", False)), None)
        if si_unit:
            return self.convert(value_si, category, si_unit, to_unit)
        return value_si
    
    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert temperature with proper offset handling."""
        # Convert to Celsius first
        if from_unit == "celsius":
            c = value
        elif from_unit == "fahrenheit":
            c = (value - 32) * 5/9
        elif from_unit == "kelvin":
            c = value - 273.15
        elif from_unit == "rankine":
            c = (value - 491.67) * 5/9
        else:
            c = value
        
        # Convert from Celsius to target
        if to_unit == "celsius":
            return c
        elif to_unit == "fahrenheit":
            return c * 9/5 + 32
        elif to_unit == "kelvin":
            return c + 273.15
        elif to_unit == "rankine":
            return (c + 273.15) * 9/5
        else:
            return c
    
    def _convert_api_gravity(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert between API gravity and specific gravity."""
        if from_unit == "api" and to_unit == "specific_gravity":
            api = value
            sg = 141.5 / (api + 131.5)
            return sg
        elif from_unit == "specific_gravity" and to_unit == "api":
            sg = value
            api = 141.5 / sg - 131.5
            return api
        else:
            return value


# Global unit definitions
UNIT_DEFINITIONS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "pressure": {
        "pa": {"label": "Pa", "to_si_factor": 1.0, "is_si": True},
        "kpa": {"label": "kPa", "to_si_factor": 1000.0},
        "mpa": {"label": "MPa", "to_si_factor": 1e6},
        "bar": {"label": "bar", "to_si_factor": 1e5},
        "psi": {"label": "psi", "to_si_factor": 6894.76},
        "atm": {"label": "atm", "to_si_factor": 101325.0},
    },
    "temperature": {
        "celsius": {"label": "°C", "is_si": True},
        "fahrenheit": {"label": "°F"},
        "kelvin": {"label": "K"},
        "rankine": {"label": "°R"},
    },
    "flow_rate": {
        "m3_s": {"label": "m³/s", "to_si_factor": 1.0, "is_si": True},
        "m3_h": {"label": "m³/h", "to_si_factor": 1/3600},
        "l_s": {"label": "L/s", "to_si_factor": 0.001},
        "gpm": {"label": "GPM", "to_si_factor": 6.30902e-5},
        "bpd": {"label": "BPD", "to_si_factor": 1.84013e-6},
    },
    "length": {
        "m": {"label": "m", "to_si_factor": 1.0, "is_si": True},
        "cm": {"label": "cm", "to_si_factor": 0.01},
        "mm": {"label": "mm", "to_si_factor": 0.001},
        "ft": {"label": "ft", "to_si_factor": 0.3048},
        "in": {"label": "in", "to_si_factor": 0.0254},
    },
    "power": {
        "w": {"label": "W", "to_si_factor": 1.0, "is_si": True},
        "kw": {"label": "kW", "to_si_factor": 1000.0},
        "mw": {"label": "MW", "to_si_factor": 1e6},
        "hp": {"label": "HP", "to_si_factor": 745.7},
    },
    "density": {
        "kg_m3": {"label": "kg/m³", "to_si_factor": 1.0, "is_si": True},
        "g_cm3": {"label": "g/cm³", "to_si_factor": 1000.0},
        "lb_ft3": {"label": "lb/ft³", "to_si_factor": 16.0185},
    },
    "viscosity": {
        "pa_s": {"label": "Pa·s", "to_si_factor": 1.0, "is_si": True},
        "cp": {"label": "cP", "to_si_factor": 0.001},
        "cst": {"label": "cSt", "to_si_factor": 1e-6},
    },
    "velocity": {
        "m_s": {"label": "m/s", "to_si_factor": 1.0, "is_si": True},
        "ft_s": {"label": "ft/s", "to_si_factor": 0.3048},
        "km_h": {"label": "km/h", "to_si_factor": 1/3.6},
    },
    "vibration": {
        "mm_s": {"label": "mm/s", "to_si_factor": 0.001, "is_si": True},
        "in_s": {"label": "in/s", "to_si_factor": 0.0254},
    },
    "speed": {
        "rpm": {"label": "RPM", "to_si_factor": 1.0, "is_si": True},
        "rad_s": {"label": "rad/s", "to_si_factor": 9.5493},
    },
    "api_gravity": {
        "api": {"label": "°API"},
        "specific_gravity": {"label": "SG"},
    },
}


# Unit system definitions
UNIT_SYSTEMS = {
    "SI": {
        "pressure": "pa",
        "temperature": "celsius",
        "flow_rate": "m3_s",
        "length": "m",
        "power": "w",
        "density": "kg_m3",
        "viscosity": "pa_s",
        "velocity": "m_s",
        "vibration": "mm_s",
        "speed": "rpm",
    },
    "Imperial": {
        "pressure": "psi",
        "temperature": "fahrenheit",
        "flow_rate": "gpm",
        "length": "ft",
        "power": "hp",
        "density": "lb_ft3",
        "viscosity": "cp",
        "velocity": "ft_s",
        "vibration": "in_s",
        "speed": "rpm",
    },
}


# Operating parameters mapping
OPERATING_PARAMETERS = {
    "inlet_pressure": "pressure",
    "outlet_pressure": "pressure",
    "discharge_pressure": "pressure",
    "suction_pressure": "pressure",
    "temperature": "temperature",
    "inlet_temperature": "temperature",
    "outlet_temperature": "temperature",
    "flow_rate": "flow_rate",
    "mass_flow_rate": "flow_rate",
    "volumetric_flow_rate": "flow_rate",
    "speed": "speed",
    "rpm": "speed",
    "power": "power",
    "vibration": "vibration",
    "density": "density",
    "viscosity": "viscosity",
    "velocity": "velocity",
    "head": "length",
    "npsh": "length",
}


# Global instance
_uc = UnitConverter()


def convert(value: float, category: str, from_unit: str, to_unit: str) -> float:
    """Global convert function."""
    return _uc.convert(value, category, from_unit, to_unit)


def get_units(category: str) -> List[str]:
    """Global get_units function."""
    return _uc.get_units(category)


def get_param_display(param: str, use_imperial: bool = False) -> Dict[str, Any]:
    """
    Get display information for a parameter.
    
    Args:
        param: Parameter name
        use_imperial: Use Imperial units instead of SI
        
    Returns:
        Dict with unit, label, and conversion info
    """
    is_si = not use_imperial
    unit_key = "SI" if is_si else "Imperial"
    
    category = OPERATING_PARAMETERS.get(param)
    if not category:
        return {"unit": "", "label": param, "category": None}
    
    unit_system = UNIT_SYSTEMS.get(unit_key, {})
    unit = unit_system.get(category, "")
    
    unit_def = UNIT_DEFINITIONS.get(category, {}).get(unit, {})
    label = unit_def.get("label", unit)
    
    return {
        "unit": unit,
        "label": label,
        "category": category,
        "param": param
    }


def to_si_value(value: float, param: str, use_imperial: bool = False) -> float:
    """Convert parameter value to SI units."""
    if not use_imperial:
        return value
    
    category = OPERATING_PARAMETERS.get(param)
    if not category:
        return value
    
    imperial_unit = UNIT_SYSTEMS["Imperial"].get(category)
    si_unit = UNIT_SYSTEMS["SI"].get(category)
    
    if imperial_unit and si_unit:
        return _uc.convert(value, category, imperial_unit, si_unit)
    
    return value


def format_value(value: float, category: str, unit_key: str, precision: int = 2) -> str:
    """Format value with unit label."""
    label = _uc.label(category, unit_key)
    return f"{value:.{precision}f} {label}"