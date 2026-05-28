"""
Turbine Transient Model Module
Implements transient response model for steam and gas turbines.
Includes speed governors, thermal lag, and blade stress.

Physics:
- Governor control dynamics
- Steam/gas flow transients
- Thermal lag in rotor
- Blade stress calculation
- Overspeed protection

Phase: Phase 2 - Dynamic Simulation
"""

from typing import Tuple, Dict, Callable, Optional
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class TurbineParameters:
    """Physical parameters for turbine transient model."""
    rotor_inertia_kg_m2: float
    rated_speed_rpm: float
    rated_power_kw: float
    inlet_volume_m3: float
    rotor_mass_kg: float
    blade_length_m: float
    material_max_stress_mpa: float
    thermal_capacity_j_k: float
    thermal_time_constant_s: float
    governor_response_time_s: float
    overspeed_shutdown_rpm: float


class TurbineGovernor:
    """Governor control system for turbine speed regulation."""
    
    def __init__(
        self,
        rated_speed_rpm: float,
        response_time: float = 0.5,
        deadband_percent: float = 1.0,
        proportional_gain: float = 100.0
    ):
        """
        Initialize governor.
        
        Args:
            rated_speed_rpm: Rated turbine speed
            response_time: Governor response time constant
            deadband_percent: Speed deadband (percent)
            proportional_gain: Proportional control gain
        """
        self.rated_speed = rated_speed_rpm * np.pi / 30
        self.response_time = response_time
        self.deadband = self.rated_speed * deadband_percent / 100
        self.proportional_gain = proportional_gain
        self.valve_position = 0.5
    
    def calculate_valve_position(
        self,
        actual_speed: float,
        speed_demand: float,
        dt: float = 0.001
    ) -> float:
        """
        Calculate steam/gas inlet valve position.
        
        Args:
            actual_speed: Current turbine speed (rad/s)
            speed_demand: Demanded speed (rad/s)
            dt: Time step
            
        Returns:
            Valve position (0=closed, 1=full open)
        """
        speed_error = actual_speed - speed_demand
        
        if abs(speed_error) < self.deadband:
            speed_error = 0
        
        valve_change = (
            -self.proportional_gain * speed_error / self.response_time * dt
        )
        
        self.valve_position += valve_change
        self.valve_position = np.clip(self.valve_position, 0.0, 1.0)
        
        return self.valve_position


class TurbineTransientModel:
    """
    Transient response model for steam/gas turbines.
    
    State variables:
    - x[0]: Rotor angular velocity (rad/s)
    - x[1]: Inlet steam/gas pressure (Pa)
    - x[2]: Rotor temperature (K)
    - x[3]: Accumulated blade stress (relative)
    """
    
    def __init__(self, params: TurbineParameters, turbine_type: str = "steam"):
        """
        Initialize turbine model.
        
        Args:
            params: TurbineParameters instance
            turbine_type: "steam" or "gas"
        """
        self.params = params
        self.turbine_type = turbine_type
        self.nominal_speed = params.rated_speed_rpm * np.pi / 30
        self.nominal_power = params.rated_power_kw * 1000
        
        self.governor = TurbineGovernor(params.rated_speed_rpm)
        self.rotor_temperature_nominal = 560 if turbine_type == "steam" else 900
    
    def system_equations(
        self,
        t: float,
        state: np.ndarray,
        inlet_pressure_func: Callable[[float], float],
        load_fraction: Callable[[float], float]
    ) -> np.ndarray:
        """
        System of differential equations for turbine.
        
        Args:
            t: Current time (s)
            state: [omega, P_inlet, T_rotor, stress]
            inlet_pressure_func: Function returning inlet pressure (Pa)
            load_fraction: Function returning load fraction (0-1)
            
        Returns:
            State derivatives
        """
        omega, P_inlet, T_rotor, stress = state
        
        omega = np.clip(omega, 0, self.nominal_speed * 1.3)
        P_inlet = np.clip(P_inlet, 1e5, 3e7)
        T_rotor = np.clip(T_rotor, 300, 1000)
        
        inlet_pressure = inlet_pressure_func(t)
        load = load_fraction(t)
        
        valve_pos = self.governor.calculate_valve_position(
            omega,
            self.nominal_speed * 0.95
        )
        
        flow_factor = valve_pos * np.sqrt(max(0, inlet_pressure - 1e5) / 1e5)
        
        power_available = self.nominal_power * flow_factor
        power_demanded = self.nominal_power * load
        
        turbine_inertia = self.params.rotor_inertia_kg_m2
        
        # Calculate friction torque using proper bearing friction model
        # Friction = viscous damping + Coulomb friction
        viscous_friction_coeff = getattr(self, 'viscous_friction_coeff', 0.5)  # Nm/(rad/s)
        coulomb_friction_nm = getattr(self, 'coulomb_friction_nm', 10.0)  # Nm
        
        friction_torque = viscous_friction_coeff * omega + coulomb_friction_nm * np.sign(omega)
        
        # Correct power-to-torque conversion: Torque = Power / angular_velocity
        # Power is in watts, omega in rad/s
        torque_available = power_available * 1000 / (omega + 1e-6)  # Convert kW to W
        torque_demanded = power_demanded * 1000 / (omega + 1e-6)
        
        d_omega_dt = (torque_available - torque_demanded - friction_torque) / turbine_inertia
        
        dp_inlet_dt = -(P_inlet - inlet_pressure) / 0.1
        
        rotor_temp_equilibrium = (
            self.rotor_temperature_nominal +
            omega / self.nominal_speed * 100
        )
        
        dT_rotor_dt = (
            (rotor_temp_equilibrium - T_rotor) / self.params.thermal_time_constant_s
        )
        
        # Improved centrifugal stress model using blade stress formula
        # Stress = rho * omega^2 * r^2 / 2 (for rotating disk)
        # Reference: Timoshenko & Goodier, "Theory of Elasticity"
        blade_tip_radius = self.params.blade_length_m
        material_density = getattr(self, 'blade_material_density_kg_m3', 7850)  # Steel default
        
        centrifugal_stress = (
            material_density * (omega ** 2) * (blade_tip_radius ** 2) / (2 * 1e6)
        )
        
        # Improved thermal stress model using thermal expansion coefficient
        # Thermal stress = E * alpha * delta_T (constrained expansion)
        # Reference: Boley & Weiner, "Theory of Thermal Stresses"
        youngs_modulus_gpa = getattr(self, 'youngs_modulus_gpa', 200)  # Steel default
        thermal_expansion_coeff = getattr(self, 'thermal_expansion_coeff', 12e-6)  # 1/K for steel
        reference_temp_k = getattr(self, 'reference_temp_k', 300)
        
        delta_T = T_rotor - reference_temp_k
        thermal_stress = (
            youngs_modulus_gpa * 1000 * thermal_expansion_coeff * delta_T
        )  # Result in MPa
        
        total_stress = centrifugal_stress + thermal_stress
        stress_rate = (total_stress - stress) / 1.0
        
        d_stress_dt = stress_rate
        
        return np.array([d_omega_dt, dp_inlet_dt, dT_rotor_dt, d_stress_dt])
    
    def calculate_blade_stress(
        self,
        rotor_speed: float,
        rotor_temperature: float
    ) -> Dict[str, float]:
        """
        Calculate blade stress from centrifugal and thermal loads.
        
        Args:
            rotor_speed: Rotor angular velocity (rad/s)
            rotor_temperature: Rotor temperature (K)
            
        Returns:
            Dictionary with stress metrics
        """
        centrifugal_stress = (
            self.params.rotor_mass_kg *
            (rotor_speed ** 2) *
            (self.params.blade_length_m / 2) / 1e6
        )
        
        stress_coefficient = (rotor_temperature - 300) / 700
        thermal_stress = stress_coefficient * self.params.material_max_stress_mpa * 0.3
        
        total_stress = centrifugal_stress + thermal_stress
        
        safety_factor = self.params.material_max_stress_mpa / (total_stress + 1e-6)
        
        speed_percent = rotor_speed / self.nominal_speed * 100
        
        return {
            "centrifugal_stress_mpa": float(centrifugal_stress),
            "thermal_stress_mpa": float(thermal_stress),
            "total_stress_mpa": float(total_stress),
            "safety_factor": float(safety_factor),
            "stress_limit_remaining_percent": float(
                (1 - total_stress / self.params.material_max_stress_mpa) * 100
            ),
            "speed_percent": float(speed_percent)
        }
    
    def detect_overspeed(
        self,
        rotor_speed: float,
        margin_percent: float = 10.0
    ) -> bool:
        """
        Detect overspeed condition.
        
        Args:
            rotor_speed: Rotor speed (rad/s)
            margin_percent: Margin above trip speed
            
        Returns:
            True if overspeed trip should activate
        """
        trip_speed = (
            self.params.overspeed_shutdown_rpm * np.pi / 30 *
            (1 - margin_percent / 100)
        )
        
        return rotor_speed > trip_speed


class TurbineLoadStepResponse:
    """Analyzes turbine response to load changes."""
    
    def __init__(self, turbine_model: TurbineTransientModel):
        """
        Initialize load step response analyzer.
        
        Args:
            turbine_model: TurbineTransientModel instance
        """
        self.turbine = turbine_model
    
    def simulate_load_step(
        self,
        initial_load: float,
        load_step: float,
        step_time: float = 1.0
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Simulate turbine response to load step change.
        
        Args:
            initial_load: Initial load fraction (0-1)
            load_step: Load change magnitude (0-1)
            step_time: Time of load step (s)
            
        Returns:
            Tuple of (time_array, metrics_dict)
        """
        from .dynamic_simulation_engine import get_simulation_engine, SolverType
        
        def inlet_pressure_func(t: float) -> float:
            return 1.5e7
        
        def load_fraction_func(t: float) -> float:
            if t < step_time:
                return initial_load
            else:
                return np.clip(initial_load + load_step, 0, 1)
        
        initial_state = np.array([
            self.turbine.nominal_speed * (1 - 0.05 * initial_load),
            1.5e7,
            self.turbine.rotor_temperature_nominal,
            100
        ])
        
        def system_eqs(t: float, state: np.ndarray) -> np.ndarray:
            return self.turbine.system_equations(
                t, state,
                inlet_pressure_func,
                load_fraction_func
            )
        
        engine = get_simulation_engine(SolverType.RK4)
        result = engine.solve(
            system_eqs,
            initial_state,
            (0, 5.0),
            0.001
        )
        
        speed_response = result.state_series[:, 0]
        speed_initial = speed_response[0]
        speed_final = speed_response[-1]
        
        max_speed_deviation = np.max(np.abs(speed_response - speed_initial))
        
        metrics = {
            "speed_dip_percent": float(
                (speed_initial - np.min(speed_response)) / speed_initial * 100
            ),
            "max_speed_deviation_percent": float(
                max_speed_deviation / speed_initial * 100
            ),
            "recovery_time_seconds": float(
                result.time_series[np.where(
                    np.abs(speed_response - speed_final) < 0.01 * speed_initial
                )[0][0]] if np.any(
                    np.abs(speed_response - speed_final) < 0.01 * speed_initial
                ) else result.time_series[-1]
            ),
            "final_speed_rpm": float(speed_final * 30 / np.pi),
            "max_rotor_stress_mpa": float(np.max(result.state_series[:, 3])),
            "rotor_temperature_max_k": float(np.max(result.state_series[:, 2]))
        }
        
        return result.time_series, metrics


def get_turbine_transient_model(
    params: TurbineParameters,
    turbine_type: str = "steam"
) -> TurbineTransientModel:
    """Factory function for turbine model."""
    return TurbineTransientModel(params, turbine_type)
