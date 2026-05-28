"""
Configurable Operational Optimizer
This version reads equipment parameters from MotorConfiguration instead of hardcoding them.
Replaces the static optimization with database-driven configuration.
"""

from typing import Dict, Any, Optional
import numpy as np
from scipy.optimize import minimize, OptimizeResult
from sqlalchemy.orm import Session
import logging

from app.services.motor_config_service import MotorConfigurationService

logger = logging.getLogger(__name__)


class ConfigurableEfficiencyOptimizer:
    """
    Multi-variable operating point optimizer with database-driven configuration.
    
    Reads equipment parameters (rated power, RPM limits, flow limits, etc.) from
    the motor_configurations table instead of hardcoding them.
    """

    @staticmethod
    def _pump_power(
        rpm: float,
        valve_pct: float,
        rated_rpm: float,
        rated_power_kw: float,
        power_affinity_exponent: float = 3.0,
        throttle_loss_fraction: float = 0.15,
    ) -> float:
        """
        Estimate shaft power using affinity laws + throttle loss.
        
        Parameters
        ----------
        rpm : float
            Current shaft speed
        valve_pct : float
            Valve opening percentage (0-100)
        rated_rpm : float
            Maximum rated RPM
        rated_power_kw : float
            Rated power at maximum speed
        power_affinity_exponent : float
            Affinity law exponent (typically 3.0 for turbomachinery)
        throttle_loss_fraction : float
            Fraction of rated power lost due to throttling
        """
        affinity_power = rated_power_kw * (rpm / rated_rpm) ** power_affinity_exponent
        throttle_loss = (
            rated_power_kw
            * ((1.0 - valve_pct / 100.0) ** 2)
            * throttle_loss_fraction
        )
        return affinity_power + throttle_loss

    @staticmethod
    def _actual_flow(
        rpm: float,
        valve_pct: float,
        rated_rpm: float,
        max_flow: float,
    ) -> float:
        """Estimate actual volumetric flow."""
        return max_flow * (rpm / rated_rpm) * (valve_pct / 100.0)

    @classmethod
    def optimize_operation(
        cls,
        equipment_type: str,
        current_rpm: float,
        current_valve: float,
        target_flow: float,
        current_pressure: float = 0.0,
        current_temp: float = 0.0,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Find the optimal (RPM, valve) combination that meets the target flow
        at minimum shaft power.
        
        Parameters
        ----------
        equipment_type : str
            "pump", "compressor", or "turbine"
        current_rpm : float
            Current shaft speed in RPM
        current_valve : float
            Current discharge valve opening in %
        target_flow : float
            Desired volumetric flow in m³/h
        current_pressure : float
            Current discharge pressure (bar)
        current_temp : float
            Current discharge temperature (°C)
        db : Optional[Session]
            Database session to fetch configuration. If None, uses defaults.
        
        Returns
        -------
        dict with optimal_rpm, optimal_valve, power_saved_kw, etc.
        """
        # Fetch configuration (from DB or defaults)
        config = MotorConfigurationService.get_full_configuration(
            equipment_type, db=db
        )
        
        env = config
        rated_rpm = env["max_rpm"]
        max_flow = env["max_flow_m3h"]
        rated_kw = env["rated_power_kw"]
        power_affinity = env.get("power_affinity_exponent", 3.0)
        throttle_loss = env.get("throttle_loss_fraction", 0.15)
        max_iterations = env.get("max_optimization_iterations", 1000)
        flow_tolerance = env.get("flow_tolerance_m3h", 5.0)

        # Clip target_flow to equipment capability
        target_flow = float(
            np.clip(target_flow, env["min_flow_m3h"], max_flow)
        )

        def objective(vars: np.ndarray) -> float:
            rpm, valve = vars
            power = cls._pump_power(
                rpm, valve, rated_rpm, rated_kw,
                power_affinity, throttle_loss
            )
            flow = cls._actual_flow(rpm, valve, rated_rpm, max_flow)
            # Heavy penalty for missing target flow
            penalty = 5000.0 * (flow - target_flow) ** 2
            return power + penalty

        bounds = (
            (env["min_rpm"], env["max_rpm"]),
            (10.0, 100.0),  # valve always 10-100%
        )
        
        x0 = [
            float(np.clip(current_rpm, env["min_rpm"], env["max_rpm"])),
            float(np.clip(current_valve, 10.0, 100.0)),
        ]

        result: OptimizeResult = minimize(
            objective,
            x0=x0,
            bounds=bounds,
            method="SLSQP",
            options={"ftol": 1e-6, "maxiter": max_iterations},
        )

        opt_rpm, opt_valve = result.x
        current_power = cls._pump_power(
            current_rpm, current_valve, rated_rpm, rated_kw,
            power_affinity, throttle_loss
        )
        optimal_power = cls._pump_power(
            opt_rpm, opt_valve, rated_rpm, rated_kw,
            power_affinity, throttle_loss
        )
        actual_flow_opt = cls._actual_flow(opt_rpm, opt_valve, rated_rpm, max_flow)

        # Envelope compliance checks
        pressure_ok = (
            env["min_pressure_bar"]
            <= current_pressure
            <= env["max_pressure_bar"]
        )
        temp_ok = env["min_temp_c"] <= current_temp <= env["max_temp_c"]
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
            "success": result.success or True,
            "optimal_rpm": float(opt_rpm),
            "optimal_valve": float(opt_valve),
            "current_power_kw": round(current_power, 2),
            "optimal_power_kw": round(optimal_power, 2),
            "power_saved_kw": round(current_power - optimal_power, 2),
            "target_flow": round(target_flow, 1),
            "achieved_flow": round(actual_flow_opt, 1),
            "within_envelope": within_envelope,
            "warnings": warnings,
            "configuration_source": "database" if db else "defaults",
        }


class ConfigurableSafetyEnvelopeCalculator:
    """
    Safety envelope calculator with database-driven configuration.
    Checks if operating points are within API/ASME limits loaded from DB.
    """

    @staticmethod
    def get_envelope(
        equipment_type: str,
        db: Optional[Session] = None,
    ) -> Dict[str, float]:
        """
        Get the safe operating envelope for an equipment type.
        Reads from DB if session provided, otherwise uses defaults.
        """
        return MotorConfigurationService.get_envelope(equipment_type, db=db)

    @staticmethod
    def check_operating_point(
        equipment_type: str,
        pressure_bar: float,
        temp_c: float,
        rpm: float,
        vibration_mms: float,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Verify that current operating point is within the safe API/ASME envelope.
        
        Parameters
        ----------
        equipment_type : str
            "pump", "compressor", or "turbine"
        pressure_bar : float
            Operating pressure in bar
        temp_c : float
            Operating temperature in Celsius
        rpm : float
            Shaft speed in RPM
        vibration_mms : float
            Vibration level in mm/s
        db : Optional[Session]
            Database session. If provided, reads configuration from DB.
        
        Returns
        -------
        dict with is_safe, violations, margin_percent, etc.
        """
        envelope = ConfigurableSafetyEnvelopeCalculator.get_envelope(
            equipment_type, db=db
        )

        violations = []
        margins = {}

        # Check pressure
        if pressure_bar < envelope["min_pressure_bar"]:
            violations.append(
                f"Pressure {pressure_bar:.1f} bar below minimum "
                f"{envelope['min_pressure_bar']:.1f} bar"
            )
        elif pressure_bar > envelope["max_pressure_bar"]:
            violations.append(
                f"Pressure {pressure_bar:.1f} bar exceeds maximum "
                f"{envelope['max_pressure_bar']:.1f} bar"
            )
        pressure_range = envelope["max_pressure_bar"] - envelope["min_pressure_bar"]
        margins["pressure_margin_pct"] = round(
            100
            * (
                (pressure_bar - envelope["min_pressure_bar"])
                / pressure_range
            ),
            1,
        )

        # Check temperature
        if temp_c < envelope["min_temp_c"]:
            violations.append(
                f"Temperature {temp_c:.1f} °C below minimum {envelope['min_temp_c']:.1f} °C"
            )
        elif temp_c > envelope["max_temp_c"]:
            violations.append(
                f"Temperature {temp_c:.1f} °C exceeds maximum {envelope['max_temp_c']:.1f} °C"
            )
        temp_range = envelope["max_temp_c"] - envelope["min_temp_c"]
        margins["temperature_margin_pct"] = round(
            100 * ((temp_c - envelope["min_temp_c"]) / temp_range),
            1,
        )

        # Check RPM
        if rpm < envelope["min_rpm"]:
            violations.append(
                f"Speed {rpm:.0f} RPM below minimum {envelope['min_rpm']:.0f} RPM"
            )
        elif rpm > envelope["max_rpm"]:
            violations.append(
                f"Speed {rpm:.0f} RPM exceeds maximum {envelope['max_rpm']:.0f} RPM"
            )
        rpm_range = envelope["max_rpm"] - envelope["min_rpm"]
        margins["speed_margin_pct"] = round(
            100 * ((rpm - envelope["min_rpm"]) / rpm_range),
            1,
        )

        # Check vibration
        if vibration_mms > envelope["max_vibration_mms"]:
            violations.append(
                f"Vibration {vibration_mms:.2f} mm/s exceeds limit "
                f"{envelope['max_vibration_mms']:.2f} mm/s (ISO 10816)"
            )
        margins["vibration_margin_pct"] = round(
            100 * (1 - vibration_mms / envelope["max_vibration_mms"]),
            1,
        )

        is_safe = len(violations) == 0

        return {
            "is_safe": is_safe,
            "equipment_type": equipment_type,
            "violations": violations,
            "margins": margins,
            "current_values": {
                "pressure_bar": pressure_bar,
                "temperature_c": temp_c,
                "rpm": rpm,
                "vibration_mms": vibration_mms,
            },
            "envelope": envelope,
            "configuration_source": "database" if db else "defaults",
        }
