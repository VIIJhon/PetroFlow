"""
core/unit_converter.py
======================
PetroFlow Enterprise — Comprehensive Unit Conversion Engine

Supports bidirectional conversion between SI and Imperial (US Customary)
units for all Oil & Gas field variables.

Variable coverage
-----------------
  Temperature       : °C, °F, K
  Pressure          : Bar, PSI, kPa, MPa, atm
  Volume flow rate  : m³/h, m³/s, GPM, BPD (barrels/day), LPM
  Volume            : m³, L, US gallon, oil barrel (bbl)
  Density           : kg/m³, lb/ft³, lb/gal, API gravity (from kg/m³)
  Viscosity         : cP (centiPoise), mPa·s (= cP), Pa·s
  Vibration         : mm/s, in/s, mm (displacement), mils
  Displacement      : mm, in, ft, m
  Power             : kW, HP (mechanical), W
  Torque            : N·m, ft·lbf, in·lbf, kgf·m
  Speed (linear)    : m/s, ft/s, ft/min
  Rotational speed  : RPM (dimensionless – same in both systems)
  Operating hours   : h (same in both systems)
  Energy            : kWh, BTU, MJ
  Mass              : kg, lb, ton (metric), short ton
  Length            : mm, in, ft, m

Usage
-----
    from core.unit_converter import UnitConverter, UNIT_SYSTEMS

    uc = UnitConverter()
    celsius = uc.convert(212, "temperature", "fahrenheit", "celsius")  # → 100.0
    gpm = uc.convert(10, "flow_rate", "m3_per_h", "gpm")             # → 44.03
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Any
import math
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unit registry
# ---------------------------------------------------------------------------

# Maps (category, unit_key) → (display_label, SI_equivalent_factor_or_callable)
# "Factor" means: value_in_SI = value_in_unit * factor
# When conversion is non-linear (temperature, API gravity) → callable provided.

# Temperature: base unit = Celsius
# Pressure:    base unit = Bar
# Flow rate:   base unit = m³/h
# Volume:      base unit = m³
# Density:     base unit = kg/m³
# Viscosity:   base unit = cP (= mPa·s)
# Vibration:   base unit = mm/s
# Displacement:base unit = mm
# Power:       base unit = kW
# Torque:      base unit = N·m
# Speed:       base unit = m/s
# Energy:      base unit = kWh
# Mass:        base unit = kg
# Length:      base unit = mm

# fmt: off
_FACTOR_UNITS: Dict[str, Dict[str, Tuple[str, float]]] = {
    # ---- Pressure (base: Bar) ----------------------------------------
    "pressure": {
        "bar":    ("Bar",   1.0),
        "psi":    ("PSI",   0.0689476),   # 1 PSI = 0.0689476 bar
        "kpa":    ("kPa",   0.01),        # 1 kPa = 0.01 bar
        "mpa":    ("MPa",   10.0),        # 1 MPa = 10 bar
        "atm":    ("atm",   1.01325),     # 1 atm = 1.01325 bar
        "mmhg":   ("mmHg",  0.00133322),  # 1 mmHg = 0.001333 bar
        "inHg":   ("inHg",  0.0338639),   # 1 inHg = 0.03386 bar
    },

    # ---- Volume flow rate (base: m³/h) ----------------------------------
    "flow_rate": {
        "m3_per_h":  ("m³/h",  1.0),
        "m3_per_s":  ("m³/s",  3600.0),
        "l_per_min": ("L/min", 0.06),          # 1 L/min = 0.06 m³/h
        "l_per_s":   ("L/s",   3.6),           # 1 L/s = 3.6 m³/h
        "gpm":       ("GPM",   0.227124),       # 1 US GPM = 0.227124 m³/h
        "bpd":       ("BPD",   0.00662783),     # 1 barrel/day = 0.006628 m³/h
        "bph":       ("BPH",   0.158987),       # 1 barrel/hour = 0.158987 m³/h
        "cfm":       ("CFM",   1.6990),         # 1 ft³/min = 1.699 m³/h
    },

    # ---- Volume (base: m³) ----------------------------------------------
    "volume": {
        "m3":     ("m³",       1.0),
        "liter":  ("L",        0.001),
        "gal_us": ("gal (US)", 0.00378541),
        "gal_uk": ("gal (UK)", 0.00454609),
        "bbl":    ("bbl",      0.158987),       # 1 oil barrel = 0.158987 m³
        "ft3":    ("ft³",      0.0283168),
        "in3":    ("in³",      1.63871e-5),
    },

    # ---- Density (base: kg/m³) ------------------------------------------
    "density": {
        "kg_per_m3":  ("kg/m³",  1.0),
        "g_per_cm3":  ("g/cm³",  1000.0),
        "lb_per_ft3": ("lb/ft³", 16.0185),      # 1 lb/ft³ = 16.0185 kg/m³
        "lb_per_gal": ("lb/gal", 119.826),      # 1 lb/US gal = 119.826 kg/m³
        "sg":         ("SG",     1000.0),       # specific gravity × 1000 = kg/m³ (water=1)
    },

    # ---- Viscosity (base: cP = mPa·s) -----------------------------------
    "viscosity": {
        "cp":     ("cP",    1.0),
        "mpa_s":  ("mPa·s", 1.0),
        "pa_s":   ("Pa·s",  1000.0),
        "poise":  ("P",     100.0),
        "cst":    ("cSt",   1.0),              # approx for water (≈ 1 cP ≈ 1 cSt)
    },

    # ---- Vibration velocity (base: mm/s) --------------------------------
    "vibration": {
        "mm_per_s": ("mm/s",  1.0),
        "in_per_s": ("in/s",  25.4),           # 1 in/s = 25.4 mm/s
        "cm_per_s": ("cm/s",  10.0),
        "m_per_s":  ("m/s",   1000.0),
    },

    # ---- Displacement (base: mm) ----------------------------------------
    "displacement": {
        "mm":   ("mm",   1.0),
        "mils": ("mils", 0.0254),              # 1 mil = 0.0254 mm
        "um":   ("µm",   0.001),
        "in":   ("in",   25.4),
        "ft":   ("ft",   304.8),
        "m":    ("m",    1000.0),
    },

    # ---- Power (base: kW) -----------------------------------------------
    "power": {
        "kw":  ("kW",        1.0),
        "w":   ("W",         0.001),
        "mw":  ("MW",        1000.0),
        "hp":  ("HP (mech)", 0.745700),        # 1 metric HP = 0.7355 kW; 1 mechanical HP = 0.7457 kW
        "ps":  ("PS (métr)", 0.735499),
    },

    # ---- Torque (base: N·m) --------------------------------------------
    "torque": {
        "n_m":    ("N·m",    1.0),
        "kn_m":   ("kN·m",   1000.0),
        "ft_lbf": ("ft·lbf", 1.35582),        # 1 ft·lbf = 1.35582 N·m
        "in_lbf": ("in·lbf", 0.113),
        "kgf_m":  ("kgf·m",  9.80665),
    },

    # ---- Linear speed (base: m/s) ----------------------------------------
    "speed": {
        "m_per_s":  ("m/s",   1.0),
        "km_per_h": ("km/h",  0.277778),
        "ft_per_s": ("ft/s",  0.3048),
        "ft_per_m": ("ft/min", 0.00508),
        "mph":      ("mph",   0.44704),
        "knot":     ("knot",  0.514444),
    },

    # ---- Energy (base: kWh) ---------------------------------------------
    "energy": {
        "kwh":   ("kWh",  1.0),
        "mj":    ("MJ",   0.277778),           # 1 MJ = 0.277778 kWh
        "j":     ("J",    2.77778e-7),
        "btu":   ("BTU",  2.93071e-4),         # 1 BTU = 0.000293071 kWh
        "kcal":  ("kcal", 1.163e-3),
    },

    # ---- Mass (base: kg) -----------------------------------------------
    "mass": {
        "kg":        ("kg",         1.0),
        "g":         ("g",          0.001),
        "ton":       ("ton (met.)", 1000.0),
        "lb":        ("lb",         0.453592),
        "short_ton": ("short ton",  907.185),
        "long_ton":  ("long ton",   1016.05),
    },

    # ---- Length (base: mm) ---------------------------------------------
    "length": {
        "mm": ("mm", 1.0),
        "cm": ("cm", 10.0),
        "m":  ("m",  1000.0),
        "km": ("km", 1e6),
        "in": ("in", 25.4),
        "ft": ("ft", 304.8),
        "yd": ("yd", 914.4),
        "mi": ("mi", 1.609344e6),
    },
}
# fmt: on

# Non-linear conversions (temperature, API gravity)
_NONLINEAR_CATEGORIES = {"temperature", "api_gravity"}


class UnitConverter:
    """
    Bidirectional unit conversion engine for Oil & Gas field variables.

    All conversions route through a canonical base unit (SI):
        value_SI = to_si(value_in_from_unit)
        result   = from_si(value_SI, to_unit)

    Example
    -------
        uc = UnitConverter()
        uc.convert(100, "temperature", "celsius", "fahrenheit")  # → 212.0
        uc.convert(100, "pressure", "psi", "bar")                # → 6.895
    """

    def __init__(self) -> None:
        self._registry = _FACTOR_UNITS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        value: float,
        category: str,
        from_unit: str,
        to_unit: str,
    ) -> float:
        """
        Convert *value* from *from_unit* to *to_unit* within *category*.

        Returns the converted value.  Raises ValueError on unknown
        category / unit keys.
        """
        if category == "temperature":
            return self._convert_temperature(value, from_unit, to_unit)
        if category == "api_gravity":
            return self._convert_api_gravity(value, from_unit, to_unit)

        reg = self._registry.get(category)
        if reg is None:
            raise ValueError(f"Unknown unit category: '{category}'")

        from_entry = reg.get(from_unit)
        to_entry   = reg.get(to_unit)

        if from_entry is None:
            raise ValueError(f"Unknown unit '{from_unit}' in category '{category}'")
        if to_entry is None:
            raise ValueError(f"Unknown unit '{to_unit}' in category '{category}'")

        if from_unit == to_unit:
            return float(value)

        # Route through SI base unit
        value_si  = value * from_entry[1]
        result    = value_si / to_entry[1]
        return result

    def convert_batch(
        self,
        values: Dict[str, float],
        mappings: Dict[str, Tuple[str, str, str]],
    ) -> Dict[str, float]:
        """
        Convert multiple values in one call.

        Parameters
        ----------
        values   : {name: raw_value}
        mappings : {name: (category, from_unit, to_unit)}

        Returns  : {name: converted_value}
        """
        return {
            name: self.convert(val, *mappings[name])
            for name, val in values.items()
            if name in mappings
        }

    def get_units(self, category: str) -> Dict[str, str]:
        """
        Return all available units for a category as {key: display_label}.
        """
        if category == "temperature":
            return {"celsius": "°C", "fahrenheit": "°F", "kelvin": "K"}
        if category == "api_gravity":
            return {"api": "°API", "sg": "SG", "kg_per_m3": "kg/m³"}

        reg = self._registry.get(category)
        if reg is None:
            raise ValueError(f"Unknown unit category: '{category}'")
        return {k: v[0] for k, v in reg.items()}

    def get_categories(self) -> List[str]:
        """Return all supported unit categories."""
        return list(self._registry.keys()) + ["temperature", "api_gravity"]

    def label(self, category: str, unit_key: str) -> str:
        """Return the human-readable label for a unit."""
        return self.get_units(category).get(unit_key, unit_key)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def to_si(self, value: float, category: str, unit_key: str) -> float:
        """Convert *value* in *unit_key* to the canonical SI base unit."""
        si_units = {
            "temperature": "celsius",
            "pressure":    "bar",
            "flow_rate":   "m3_per_h",
            "volume":      "m3",
            "density":     "kg_per_m3",
            "viscosity":   "cp",
            "vibration":   "mm_per_s",
            "displacement":"mm",
            "power":       "kw",
            "torque":      "n_m",
            "speed":       "m_per_s",
            "energy":      "kwh",
            "mass":        "kg",
            "length":      "mm",
        }
        return self.convert(value, category, unit_key, si_units[category])

    def from_si(self, value_si: float, category: str, to_unit: str) -> float:
        """Convert *value_si* from the canonical SI base unit to *to_unit*."""
        si_units = {
            "temperature": "celsius",
            "pressure":    "bar",
            "flow_rate":   "m3_per_h",
            "volume":      "m3",
            "density":     "kg_per_m3",
            "viscosity":   "cp",
            "vibration":   "mm_per_s",
            "displacement":"mm",
            "power":       "kw",
            "torque":      "n_m",
            "speed":       "m_per_s",
            "energy":      "kwh",
            "mass":        "kg",
            "length":      "mm",
        }
        return self.convert(value_si, category, si_units[category], to_unit)

    # ------------------------------------------------------------------
    # Non-linear conversions
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
        """Temperature conversion routing through Celsius."""
        # Step 1: to Celsius
        if from_unit == "celsius":
            c = value
        elif from_unit == "fahrenheit":
            c = (value - 32) * 5 / 9
        elif from_unit == "kelvin":
            c = value - 273.15
        elif from_unit == "rankine":
            c = (value - 491.67) * 5 / 9
        else:
            raise ValueError(f"Unknown temperature unit: '{from_unit}'")

        # Step 2: from Celsius
        if to_unit == "celsius":
            return c
        elif to_unit == "fahrenheit":
            return c * 9 / 5 + 32
        elif to_unit == "kelvin":
            return c + 273.15
        elif to_unit == "rankine":
            return (c + 273.15) * 9 / 5
        else:
            raise ValueError(f"Unknown temperature unit: '{to_unit}'")

    @staticmethod
    def _convert_api_gravity(value: float, from_unit: str, to_unit: str) -> float:
        """
        API gravity conversions.
        API = (141.5 / SG) - 131.5  where SG = density_kg_m3 / 1000
        """
        # Step 1: to API
        if from_unit == "api":
            api = value
        elif from_unit == "sg":
            api = 141.5 / value - 131.5
        elif from_unit == "kg_per_m3":
            sg  = value / 1000.0
            api = 141.5 / sg - 131.5
        else:
            raise ValueError(f"Unknown API gravity unit: '{from_unit}'")

        # Step 2: from API
        if to_unit == "api":
            return api
        elif to_unit == "sg":
            return 141.5 / (api + 131.5)
        elif to_unit == "kg_per_m3":
            sg = 141.5 / (api + 131.5)
            return sg * 1000.0
        else:
            raise ValueError(f"Unknown API gravity unit: '{to_unit}'")


# ---------------------------------------------------------------------------
# Singleton instance (import-level convenience)
# ---------------------------------------------------------------------------
_uc = UnitConverter()


def convert(value: float, category: str, from_unit: str, to_unit: str) -> float:
    """Module-level shortcut: convert a single value."""
    return _uc.convert(value, category, from_unit, to_unit)


def get_units(category: str) -> Dict[str, str]:
    """Module-level shortcut: get available units for a category."""
    return _uc.get_units(category)


# ---------------------------------------------------------------------------
# Unit System Presets — maps variable name → (si_unit_key, imperial_unit_key)
# ---------------------------------------------------------------------------

UNIT_SYSTEMS: Dict[str, Dict[str, Tuple[str, str]]] = {
    # variable_name: (si_key, imperial_key)
    "temperature":       ("celsius",     "fahrenheit"),
    "pressure":          ("bar",         "psi"),
    "flow_rate":         ("m3_per_h",    "gpm"),
    "volume":            ("m3",          "bbl"),
    "density":           ("kg_per_m3",   "lb_per_ft3"),
    "viscosity":         ("cp",          "cp"),         # cP used in both systems
    "vibration":         ("mm_per_s",    "in_per_s"),
    "displacement":      ("mm",          "mils"),
    "power":             ("kw",          "hp"),
    "torque":            ("n_m",         "ft_lbf"),
    "speed":             ("m_per_s",     "ft_per_s"),
    "energy":            ("kwh",         "btu"),
    "mass":              ("kg",          "lb"),
    "length":            ("mm",          "in"),
}


# ---------------------------------------------------------------------------
# Operating parameter definitions for the UI sidebar
# ---------------------------------------------------------------------------

# Each entry defines one operating parameter:
#   label_si        : label shown in SI mode
#   label_imperial  : label shown in Imperial mode
#   category        : unit category (for UnitConverter)
#   si_unit         : SI unit key
#   imperial_unit   : Imperial unit key
#   si_min          : minimum in SI
#   si_max          : maximum in SI
#   si_default      : default value in SI
#   si_step         : slider step in SI
#   description     : tooltip / help text

OPERATING_PARAMETERS = [
    {
        "id":               "temperature",
        "label_si":         "Inlet Temperature (°C)",
        "label_imperial":   "Inlet Temperature (°F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           0,
        "si_max":           150,
        "si_default":       75,
        "si_step":          1,
        "description":      "Process fluid temperature at pump inlet",
    },
    {
        "id":               "pressure",
        "label_si":         "Operating Pressure (Bar)",
        "label_imperial":   "Operating Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0,
        "si_max":           50,
        "si_default":       25,
        "si_step":          1,
        "description":      "Discharge or operating pressure",
    },
    {
        "id":               "vibration",
        "label_si":         "Vibration (mm/s RMS)",
        "label_imperial":   "Vibration (in/s RMS)",
        "category":         "vibration",
        "si_unit":          "mm_per_s",
        "imperial_unit":    "in_per_s",
        "si_min":           0.5,
        "si_max":           10.0,
        "si_default":       2.3,
        "si_step":          0.1,
        "description":      "Vibration velocity (ISO 10816 / API 670)",
    },
    {
        "id":               "flow_rate",
        "label_si":         "Flow Rate (m³/h)",
        "label_imperial":   "Flow Rate (GPM)",
        "category":         "flow_rate",
        "si_unit":          "m3_per_h",
        "imperial_unit":    "gpm",
        "si_min":           0.0,
        "si_max":           500.0,
        "si_default":       120.0,
        "si_step":          5.0,
        "description":      "Volumetric flow rate through the equipment",
    },
    {
        "id":               "operating_hours",
        "label_si":         "Operating Hours (h)",
        "label_imperial":   "Operating Hours (h)",
        "category":         None,              # dimensionless — same both systems
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           20000,
        "si_default":       12450,
        "si_step":          50,
        "description":      "Cumulative equipment operating hours",
    },
    {
        "id":               "rpm",
        "label_si":         "Rotational Speed (RPM)",
        "label_imperial":   "Rotational Speed (RPM)",
        "category":         None,              # dimensionless
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           5000,
        "si_default":       2500,
        "si_step":          50,
        "description":      "Equipment rotational speed",
    },
    {
        "id":               "power",
        "label_si":         "Power Consumption (kW)",
        "label_imperial":   "Power Consumption (HP)",
        "category":         "power",
        "si_unit":          "kw",
        "imperial_unit":    "hp",
        "si_min":           0.0,
        "si_max":           2000.0,
        "si_default":       250.0,
        "si_step":          10.0,
        "description":      "Shaft or motor power consumption",
    },
    {
        "id":               "fluid_density",
        "label_si":         "Fluid Density (kg/m³)",
        "label_imperial":   "Fluid Density (lb/ft³)",
        "category":         "density",
        "si_unit":          "kg_per_m3",
        "imperial_unit":    "lb_per_ft3",
        "si_min":           500.0,
        "si_max":           1100.0,
        "si_default":       870.0,
        "si_step":          10.0,
        "description":      "Process fluid density (crude: ~830–900, water: 1000)",
    },
    {
        "id":               "differential_pressure",
        "label_si":         "Differential Pressure (Bar)",
        "label_imperial":   "Differential Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           30.0,
        "si_default":       8.0,
        "si_step":          0.5,
        "description":      "Pressure drop across the equipment (ΔP)",
    },
    {
        "id":               "discharge_temperature",
        "label_si":         "Discharge Temperature (°C)",
        "label_imperial":   "Discharge Temperature (°F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           0,
        "si_max":           200,
        "si_default":       85,
        "si_step":          1,
        "description":      "Fluid temperature at equipment discharge",
    },
    {
        "id":               "compression_ratio",
        "label_si":         "Compression Ratio",
        "label_imperial":   "Compression Ratio",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           1.0,
        "si_max":           15.0,
        "si_default":       4.5,
        "si_step":          0.1,
        "description":      "Ratio of discharge pressure to suction pressure",
    },
    {
        "id":               "radial_vibration",
        "label_si":         "Radial Vibration (mm/s)",
        "label_imperial":   "Radial Vibration (in/s)",
        "category":         "vibration",
        "si_unit":          "mm_per_s",
        "imperial_unit":    "in_per_s",
        "si_min":           0.0,
        "si_max":           15.0,
        "si_default":       1.5,
        "si_step":          0.1,
        "description":      "Radial vibration amplitude",
    },
    {
        "id":               "axial_vibration",
        "label_si":         "Axial Vibration (mm/s)",
        "label_imperial":   "Axial Vibration (in/s)",
        "category":         "vibration",
        "si_unit":          "mm_per_s",
        "imperial_unit":    "in_per_s",
        "si_min":           0.0,
        "si_max":           15.0,
        "si_default":       1.2,
        "si_step":          0.1,
        "description":      "Axial vibration amplitude",
    },
    {
        "id":               "relative_humidity",
        "label_si":         "Relative Humidity (%)",
        "label_imperial":   "Relative Humidity (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       55,
        "si_step":          1,
        "description":      "Process gas relative humidity",
    },
    {
        "id":               "steam_temperature",
        "label_si":         "Steam Temperature (C)",
        "label_imperial":   "Steam Temperature (F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           50,
        "si_max":           600,
        "si_default":       250,
        "si_step":          1,
        "description":      "Turbine inlet steam temperature",
    },
    {
        "id":               "inlet_pressure",
        "label_si":         "Inlet Pressure (Bar)",
        "label_imperial":   "Inlet Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           150.0,
        "si_default":       25.0,
        "si_step":          1.0,
        "description":      "Equipment suction/inlet pressure",
    },
    {
        "id":               "synchronous_speed",
        "label_si":         "Synchronous Speed (RPM)",
        "label_imperial":   "Synchronous Speed (RPM)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           10000,
        "si_default":       3000,
        "si_step":          50,
        "description":      "Turbine synchronous speed",
    },
    {
        "id":               "exhaust_temperature",
        "label_si":         "Exhaust Temperature (C)",
        "label_imperial":   "Exhaust Temperature (F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           0,
        "si_max":           400,
        "si_default":       120,
        "si_step":          1,
        "description":      "Turbine exhaust gas/steam temperature",
    },
    {
        "id":               "outlet_pressure",
        "label_si":         "Outlet Pressure (Bar)",
        "label_imperial":   "Outlet Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           150.0,
        "si_default":       20.0,
        "si_step":          1.0,
        "description":      "Equipment discharge/outlet pressure",
    },
    {
        "id":               "available_npsh",
        "label_si":         "Available NPSH (m)",
        "label_imperial":   "Available NPSH (ft)",
        "category":         "displacement",
        "si_unit":          "m",
        "imperial_unit":    "ft",
        "si_min":           0.0,
        "si_max":           20.0,
        "si_default":       4.0,
        "si_step":          0.1,
        "description":      "Net Positive Suction Head Available",
    },
    {
        "id":               "submergence_depth",
        "label_si":         "Submergence Depth (m)",
        "label_imperial":   "Submergence Depth (ft)",
        "category":         "displacement",
        "si_unit":          "m",
        "imperial_unit":    "ft",
        "si_min":           0.0,
        "si_max":           500.0,
        "si_default":       50.0,
        "si_step":          5.0,
        "description":      "Depth of submersible pump installation below surface",
    },
    {
        "id":               "motor_temperature",
        "label_si":         "Motor Temperature (°C)",
        "label_imperial":   "Motor Temperature (°F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           20,
        "si_max":           150,
        "si_default":       65,
        "si_step":          1,
        "description":      "Motor winding temperature for submersible/underground pumps",
    },
    {
        "id":               "cable_length",
        "label_si":         "Cable Length (m)",
        "label_imperial":   "Cable Length (ft)",
        "category":         "displacement",
        "si_unit":          "m",
        "imperial_unit":    "ft",
        "si_min":           0.0,
        "si_max":           1000.0,
        "si_default":       100.0,
        "si_step":          10.0,
        "description":      "Power cable length for submersible equipment",
    },
    {
        "id":               "fluid_viscosity",
        "label_si":         "Fluid Viscosity (cP)",
        "label_imperial":   "Fluid Viscosity (cP)",
        "category":         "viscosity",
        "si_unit":          "cp",
        "imperial_unit":    "cp",
        "si_min":           0.5,
        "si_max":           500.0,
        "si_default":       10.0,
        "si_step":          0.5,
        "description":      "Dynamic viscosity of process fluid (water: ~1 cP, crude: 5-100 cP)",
    },
    {
        "id":               "gas_composition_h2",
        "label_si":         "H₂ Content (%)",
        "label_imperial":   "H₂ Content (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       0,
        "si_step":          1,
        "description":      "Hydrogen content in gas mixture for air/fuel operation",
    },
    {
        "id":               "gas_composition_ch4",
        "label_si":         "CH₄ Content (%)",
        "label_imperial":   "CH₄ Content (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       85,
        "si_step":          1,
        "description":      "Methane content in gas mixture for fuel operation",
    },
    {
        "id":               "water_content",
        "label_si":         "Water Content (%)",
        "label_imperial":   "Water Content (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       2,
        "si_step":          0.5,
        "description":      "Water content in petroleum/fuel mixture",
    },
    {
        "id":               "api_gravity",
        "label_si":         "API Gravity (°API)",
        "label_imperial":   "API Gravity (°API)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           10.0,
        "si_max":           50.0,
        "si_default":       35.0,
        "si_step":          0.5,
        "description":      "API gravity for petroleum fluids (light crude: 35-45, heavy: 10-25)",
    },
    {
        "id":               "suction_pressure",
        "label_si":         "Suction Pressure (Bar)",
        "label_imperial":   "Suction Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           50.0,
        "si_default":       5.0,
        "si_step":          0.5,
        "description":      "Suction pressure at equipment inlet",
    },
    {
        "id":               "seal_flush_rate",
        "label_si":         "Seal Flush Rate (L/min)",
        "label_imperial":   "Seal Flush Rate (GPM)",
        "category":         "flow_rate",
        "si_unit":          "l_per_min",
        "imperial_unit":    "gpm",
        "si_min":           0.0,
        "si_max":           50.0,
        "si_default":       5.0,
        "si_step":          0.5,
        "description":      "Mechanical seal flush flow rate",
    },
    {
        "id":               "bearing_temperature",
        "label_si":         "Bearing Temperature (°C)",
        "label_imperial":   "Bearing Temperature (°F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           20,
        "si_max":           120,
        "si_default":       55,
        "si_step":          1,
        "description":      "Bearing housing temperature",
    },
    {
        "id":               "lube_oil_pressure",
        "label_si":         "Lube Oil Pressure (Bar)",
        "label_imperial":   "Lube Oil Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           10.0,
        "si_default":       2.5,
        "si_step":          0.1,
        "description":      "Lubrication oil supply pressure",
    },
    {
        "id":               "seal_chamber_pressure",
        "label_si":         "Seal Chamber Pressure (Bar)",
        "label_imperial":   "Seal Chamber Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           50.0,
        "si_default":       5.0,
        "si_step":          0.5,
        "description":      "Mechanical seal chamber pressure",
    },
    {
        "id":               "cooling_water_flow",
        "label_si":         "Cooling Water Flow (L/min)",
        "label_imperial":   "Cooling Water Flow (GPM)",
        "category":         "flow_rate",
        "si_unit":          "l_per_min",
        "imperial_unit":    "gpm",
        "si_min":           0.0,
        "si_max":           500.0,
        "si_default":       50.0,
        "si_step":          5.0,
        "description":      "Cooling water circulation flow rate",
    },
    {
        "id":               "cooling_water_temperature",
        "label_si":         "Cooling Water Temp (°C)",
        "label_imperial":   "Cooling Water Temp (°F)",
        "category":         "temperature",
        "si_unit":          "celsius",
        "imperial_unit":    "fahrenheit",
        "si_min":           10,
        "si_max":           50,
        "si_default":       25,
        "si_step":          1,
        "description":      "Cooling water inlet temperature",
    },
    {
        "id":               "shaft_displacement",
        "label_si":         "Shaft Displacement (mm)",
        "label_imperial":   "Shaft Displacement (mils)",
        "category":         "displacement",
        "si_unit":          "mm",
        "imperial_unit":    "mils",
        "si_min":           0.0,
        "si_max":           1.0,
        "si_default":       0.1,
        "si_step":          0.01,
        "description":      "Shaft radial displacement (proximity probe)",
    },
    {
        "id":               "thrust_position",
        "label_si":         "Thrust Position (mm)",
        "label_imperial":   "Thrust Position (mils)",
        "category":         "displacement",
        "si_unit":          "mm",
        "imperial_unit":    "mils",
        "si_min":           -5.0,
        "si_max":           5.0,
        "si_default":       0.0,
        "si_step":          0.1,
        "description":      "Axial thrust bearing position",
    },
    {
        "id":               "efficiency",
        "label_si":         "Efficiency (%)",
        "label_imperial":   "Efficiency (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       75,
        "si_step":          1,
        "description":      "Equipment operating efficiency",
    },
    {
        "id":               "head",
        "label_si":         "Head (m)",
        "label_imperial":   "Head (ft)",
        "category":         "displacement",
        "si_unit":          "m",
        "imperial_unit":    "ft",
        "si_min":           0.0,
        "si_max":           500.0,
        "si_default":       50.0,
        "si_step":          5.0,
        "description":      "Pump total developed head",
    },
    {
        "id":               "impeller_diameter",
        "label_si":         "Impeller Diameter (mm)",
        "label_imperial":   "Impeller Diameter (in)",
        "category":         "length",
        "si_unit":          "mm",
        "imperial_unit":    "in",
        "si_min":           50.0,
        "si_max":           1000.0,
        "si_default":       250.0,
        "si_step":          10.0,
        "description":      "Pump impeller diameter",
    },
    {
        "id":               "stage_count",
        "label_si":         "Number of Stages",
        "label_imperial":   "Number of Stages",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           1,
        "si_max":           20,
        "si_default":       1,
        "si_step":          1,
        "description":      "Number of pump/compressor stages",
    },
    {
        "id":               "polytropic_efficiency",
        "label_si":         "Polytropic Efficiency (%)",
        "label_imperial":   "Polytropic Efficiency (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           50,
        "si_max":           95,
        "si_default":       78,
        "si_step":          1,
        "description":      "Compressor polytropic efficiency",
    },
    {
        "id":               "surge_margin",
        "label_si":         "Surge Margin (%)",
        "label_imperial":   "Surge Margin (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           50,
        "si_default":       10,
        "si_step":          1,
        "description":      "Compressor surge margin (distance from surge line)",
    },
    {
        "id":               "molecular_weight",
        "label_si":         "Molecular Weight (kg/kmol)",
        "label_imperial":   "Molecular Weight (lb/lbmol)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           2.0,
        "si_max":           100.0,
        "si_default":       16.0,
        "si_step":          0.5,
        "description":      "Gas molecular weight (CH4: 16, Air: 29)",
    },
    {
        "id":               "specific_heat_ratio",
        "label_si":         "Specific Heat Ratio (k)",
        "label_imperial":   "Specific Heat Ratio (k)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           1.0,
        "si_max":           1.7,
        "si_default":       1.4,
        "si_step":          0.01,
        "description":      "Gas specific heat ratio (Air: 1.4, CH4: 1.31)",
    },
    {
        "id":               "heat_transfer_coefficient",
        "label_si":         "Heat Transfer Coeff (W/m²·K)",
        "label_imperial":   "Heat Transfer Coeff (BTU/hr·ft²·°F)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           10.0,
        "si_max":           10000.0,
        "si_default":       500.0,
        "si_step":          50.0,
        "description":      "Overall heat transfer coefficient",
    },
    {
        "id":               "fouling_factor",
        "label_si":         "Fouling Factor (m²·K/W)",
        "label_imperial":   "Fouling Factor (hr·ft²·°F/BTU)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0.0,
        "si_max":           0.01,
        "si_default":       0.0002,
        "si_step":          0.0001,
        "description":      "Heat exchanger fouling resistance",
    },
    {
        "id":               "valve_cv",
        "label_si":         "Valve Cv",
        "label_imperial":   "Valve Cv",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0.1,
        "si_max":           1000.0,
        "si_default":       10.0,
        "si_step":          0.5,
        "description":      "Valve flow coefficient",
    },
    {
        "id":               "valve_position",
        "label_si":         "Valve Position (%)",
        "label_imperial":   "Valve Position (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       50,
        "si_step":          1,
        "description":      "Control valve stem position",
    },
    {
        "id":               "set_pressure",
        "label_si":         "Set Pressure (Bar)",
        "label_imperial":   "Set Pressure (PSI)",
        "category":         "pressure",
        "si_unit":          "bar",
        "imperial_unit":    "psi",
        "si_min":           0.0,
        "si_max":           300.0,
        "si_default":       10.0,
        "si_step":          1.0,
        "description":      "Safety valve set pressure",
    },
    {
        "id":               "liquid_level",
        "label_si":         "Liquid Level (%)",
        "label_imperial":   "Liquid Level (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       50,
        "si_step":          1,
        "description":      "Vessel/separator liquid level",
    },
    {
        "id":               "interface_level",
        "label_si":         "Interface Level (%)",
        "label_imperial":   "Interface Level (%)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0,
        "si_max":           100,
        "si_default":       30,
        "si_step":          1,
        "description":      "Oil-water interface level in separator",
    },
    {
        "id":               "residence_time",
        "label_si":         "Residence Time (min)",
        "label_imperial":   "Residence Time (min)",
        "category":         None,
        "si_unit":          None,
        "imperial_unit":    None,
        "si_min":           0.5,
        "si_max":           60.0,
        "si_default":       3.0,
        "si_step":          0.5,
        "description":      "Fluid residence time in vessel",
    },
]


def get_param_display(param: dict, use_imperial: bool) -> dict:
    """
    Given a parameter definition and the selected unit system,
    return a UI-ready dictionary with:
      label, unit_key, min, max, default, step, display_format_fn
    """
    is_si = not use_imperial
    unit_key = param["si_unit"] if is_si else param["imperial_unit"]

    if param["category"] is None or param["category"] == "":
        # Dimensionless — same in both systems
        return {
            "label":      param["label_si"],
            "unit_key":   None,
            "category":   None,
            "min":        param["si_min"],
            "max":        param["si_max"],
            "default":    param["si_default"],
            "step":       param["si_step"],
        }

    if is_si:
        return {
            "label":    param["label_si"],
            "unit_key": param["si_unit"],
            "category": param["category"],
            "min":      param["si_min"],
            "max":      param["si_max"],
            "default":  param["si_default"],
            "step":     param["si_step"],
        }
    else:
        # Convert all SI bounds and default to imperial
        uc = UnitConverter()
        cat  = param["category"]
        si_u = param["si_unit"]
        im_u = param["imperial_unit"]

        def c(v):
            return round(uc.convert(v, cat, si_u, im_u), 4)

        return {
            "label":    param["label_imperial"],
            "unit_key": im_u,
            "category": cat,
            "min":      c(param["si_min"])  if param["si_min"]  != 0 else 0,
            "max":      c(param["si_max"]),
            "default":  c(param["si_default"]),
            "step":     round(c(param["si_step"]), 4),
        }


def to_si_value(value: float, param: dict, use_imperial: bool) -> float:
    """
    Given a raw slider value and parameter definition, return the
    equivalent value in SI units (for ML model input).
    """
    if not use_imperial or param["category"] is None:
        return float(value)
    uc = UnitConverter()
    return uc.convert(value, param["category"], param["imperial_unit"], param["si_unit"])


def format_value(value: float, category: Optional[str], unit_key: Optional[str],
                 precision: int = 2) -> str:
    """Return a formatted string like '78.5 °C' or '173.3 °F'."""
    if category is None or unit_key is None:
        return f"{value:,.{precision}f}"
    label = _uc.label(category, unit_key)
    return f"{value:,.{precision}f} {label}"
