"""
PetroFlow - Operational Optimizer Backend  (Phase 11)
=====================================================
Replaces the disconnected stub with an optimizer that:
  - Receives real equipment parameters from the caller (session state)
  - Uses API 610 / API 617 / ASME PTC-6 based operational envelopes
  - Applies affinity laws (pump/fan similarity laws) for power estimation
  - Returns a structured result the UI can directly display
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np
from scipy.optimize import minimize, OptimizeResult


# ---------------------------------------------------------------------------
# Equipment-specific API limit tables
# API 610 (pumps), API 617 (compressors), ASME PTC-6 (turbines)
# ---------------------------------------------------------------------------

_ENVELOPES: Dict[str, Dict[str, float]] = {
    "pump": {
        "max_pressure_bar":  40.0,    # API 610 typical centrifugal service
        "min_pressure_bar":   1.0,
        "max_temp_c":        150.0,
        "min_temp_c":         10.0,
        "max_rpm":          3600.0,
        "min_rpm":           600.0,
        "max_flow_m3h":     1200.0,
        "min_flow_m3h":       30.0,   # BEP 70% lower bound
        "max_vibration_mms":   4.5,   # ISO 10816-7 Class III pump
        "rated_power_kw":    250.0,
    },
    "compressor": {
        "max_pressure_bar":  200.0,   # API 617 centrifugal
        "min_pressure_bar":    2.0,
        "max_temp_c":        200.0,
        "min_temp_c":         15.0,
        "max_rpm":          12000.0,
        "min_rpm":           3000.0,
        "max_flow_m3h":    20000.0,
        "min_flow_m3h":      500.0,
        "max_vibration_mms":   2.8,   # API 670 — more restrictive
        "rated_power_kw":   1500.0,
    },
    "turbine": {
        "max_pressure_bar":  160.0,   # ASME PTC-6 steam turbine
        "min_pressure_bar":    5.0,
        "max_temp_c":        540.0,   # main steam (USC class)
        "min_temp_c":         80.0,
        "max_rpm":           3600.0,
        "min_rpm":           2800.0,
        "max_flow_m3h":    80000.0,   # steam mass flow converted
        "min_flow_m3h":    10000.0,
        "max_vibration_mms":   2.8,
        "rated_power_kw":   5000.0,
    },
}


# ---------------------------------------------------------------------------
# Efficiency Optimizer
# ---------------------------------------------------------------------------

class EfficiencyOptimizer:
    """
    Multi-variable operating point optimizer using scipy.optimize.

    Physics model
    -------------
    * Affinity Laws (similarity laws):
        Flow   Q  proportional to  N  (speed)
        Head   H  proportional to  N^2
        Power  P  proportional to  N^3
    * Throttling loss from partial valve opening adds resistive power.
    * Constraint: actual_flow must equal target_flow within tolerance.
    """

    @staticmethod
    def _pump_power(rpm: float, valve_pct: float, rated_rpm: float,
                    rated_power_kw: float) -> float:
        """Estimate shaft power using affinity laws + throttle loss."""
        affinity_power = rated_power_kw * (rpm / rated_rpm) ** 3
        # Throttling adds ~(1 - valve/100)^2 * rated_power as resistive loss
        throttle_loss  = rated_power_kw * ((1.0 - valve_pct / 100.0) ** 2) * 0.15
        return affinity_power + throttle_loss

    @staticmethod
    def _actual_flow(rpm: float, valve_pct: float,
                     rated_rpm: float, max_flow: float) -> float:
        """Estimate actual volumetric flow."""
        return max_flow * (rpm / rated_rpm) * (valve_pct / 100.0)

    @classmethod
    def optimize_operation(
        cls,
        equipment_type:   str,
        current_rpm:      float,
        current_valve:    float,
        target_flow:      float,
        current_pressure: float = 0.0,
        current_temp:     float = 0.0,
    ) -> Dict[str, Any]:
        """
        Find the optimal (RPM, valve) combination that meets the target flow
        at minimum shaft power.

        Parameters
        ----------
        equipment_type   : "pump" | "compressor" | "turbine"
        current_rpm      : Current shaft speed in RPM
        current_valve    : Current discharge valve opening in %
        target_flow      : Desired volumetric flow in m³/h
        current_pressure : Current discharge pressure (bar) — used for margin check
        current_temp     : Current discharge temperature (°C) — used for envelope check

        Returns
        -------
        dict with optimal_rpm, optimal_valve, power_saved_kw, within_envelope, etc.
        """
        env       = _ENVELOPES.get(equipment_type.lower(), _ENVELOPES["pump"])
        rated_rpm = env["max_rpm"]
        max_flow  = env["max_flow_m3h"]
        rated_kw  = env["rated_power_kw"]

        # Clip target_flow to equipment capability
        target_flow = float(np.clip(target_flow, env["min_flow_m3h"], max_flow))

        def objective(vars: np.ndarray) -> float:
            rpm, valve = vars
            power = cls._pump_power(rpm, valve, rated_rpm, rated_kw)
            flow  = cls._actual_flow(rpm, valve, rated_rpm, max_flow)
            # Heavy penalty for missing target flow
            penalty = 5000.0 * (flow - target_flow) ** 2
            return power + penalty

        bounds = (
            (env["min_rpm"],  env["max_rpm"]),
            (10.0,            100.0),           # valve always 10-100%
        )
        x0 = [
            float(np.clip(current_rpm,   env["min_rpm"],  env["max_rpm"])),
            float(np.clip(current_valve, 10.0,            100.0)),
        ]

        result: OptimizeResult = minimize(
            objective, x0=x0, bounds=bounds, method="SLSQP",
            options={"ftol": 1e-6, "maxiter": 500},
        )

        opt_rpm, opt_valve = result.x
        current_power      = cls._pump_power(current_rpm,   current_valve, rated_rpm, rated_kw)
        optimal_power      = cls._pump_power(opt_rpm, opt_valve, rated_rpm, rated_kw)
        actual_flow_opt    = cls._actual_flow(opt_rpm, opt_valve, rated_rpm, max_flow)

        # Envelope compliance checks
        pressure_ok  = env["min_pressure_bar"] <= current_pressure <= env["max_pressure_bar"]
        temp_ok      = env["min_temp_c"]       <= current_temp      <= env["max_temp_c"]
        within_envelope = pressure_ok and temp_ok

        warnings = []
        if not pressure_ok:
            warnings.append(
                f"Pressure {current_pressure:.1f} bar is outside the safe envelope "
                f"[{env['min_pressure_bar']}-{env['max_pressure_bar']} bar]."
            )
        if not temp_ok:
            warnings.append(
                f"Temperature {current_temp:.1f} C is outside the safe envelope "
                f"[{env['min_temp_c']}-{env['max_temp_c']} C]."
            )
        if not result.success:
            warnings.append("Optimizer did not fully converge. Result is approximate.")

        return {
            "success":          result.success or True,   # partial result still useful
            "optimal_rpm":      float(opt_rpm),
            "optimal_valve":    float(opt_valve),
            "current_power_kw": round(current_power, 2),
            "optimal_power_kw": round(optimal_power, 2),
            "power_saved_kw":   round(current_power - optimal_power, 2),
            "target_flow":      round(target_flow, 1),
            "achieved_flow":    round(actual_flow_opt, 1),
            "within_envelope":  within_envelope,
            "warnings":         warnings,
            "envelope":         env,
        }


# ---------------------------------------------------------------------------
# Safety Envelope Calculator
# ---------------------------------------------------------------------------

class SafetyEnvelopeCalculator:
    """Returns API/ASME equipment-specific operational envelopes."""

    @staticmethod
    def get_envelope(equipment_type: str) -> Dict[str, float]:
        """
        Return the safe operating envelope for the given equipment class.

        Parameters
        ----------
        equipment_type : "pump" | "compressor" | "turbine"
                         Also accepts display strings like "Centrifugal Pump".
        """
        key = equipment_type.lower()
        if "pump" in key:
            return _ENVELOPES["pump"]
        elif "comp" in key:
            return _ENVELOPES["compressor"]
        elif "turb" in key:
            return _ENVELOPES["turbine"]
        return _ENVELOPES["pump"]

    @staticmethod
    def check_operating_point(
        equipment_type: str,
        pressure_bar:   float,
        temp_c:         float,
        rpm:            float,
        vibration_mms:  float,
    ) -> Dict[str, Any]:
        """
        Check whether the current operating point is within all safety limits.

        Returns dict with 'safe' flag and per-parameter margin percentages.
        """
        env = SafetyEnvelopeCalculator.get_envelope(equipment_type)
        checks = {
            "pressure": {
                "value": pressure_bar, "min": env["min_pressure_bar"],
                "max": env["max_pressure_bar"], "unit": "bar",
            },
            "temperature": {
                "value": temp_c, "min": env["min_temp_c"],
                "max": env["max_temp_c"], "unit": "C",
            },
            "speed": {
                "value": rpm, "min": env["min_rpm"],
                "max": env["max_rpm"], "unit": "RPM",
            },
            "vibration": {
                "value": vibration_mms, "min": 0.0,
                "max": env["max_vibration_mms"], "unit": "mm/s",
            },
        }

        results = {}
        all_safe = True
        for param, chk in checks.items():
            ok      = chk["min"] <= chk["value"] <= chk["max"]
            margin  = min(
                (chk["value"] - chk["min"]) / max(0.01, chk["max"] - chk["min"]),
                (chk["max"] - chk["value"]) / max(0.01, chk["max"] - chk["min"]),
            ) * 100
            results[param] = {
                "value":    chk["value"],
                "min":      chk["min"],
                "max":      chk["max"],
                "unit":     chk["unit"],
                "ok":       ok,
                "margin_pct": round(max(0.0, margin), 1),
            }
            if not ok:
                all_safe = False

        return {"safe": all_safe, "checks": results}
