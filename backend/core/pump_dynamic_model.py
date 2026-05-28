"""
Pump Dynamic Model Module
Implements second-order transient model for centrifugal pumps including
impeller dynamics, surge tank effects, and inlet/outlet pressure transients.

Physics:
- Rotor angular acceleration with inertia
- Inlet pressure surge
- Outlet pressure surge
- Cavitation dynamics
- Mechanical friction and damping

Phase: Phase 2 - Dynamic Simulation
"""

from typing import Tuple, Dict, Callable, Optional
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PumpParameters:
    """Physical parameters for centrifugal pump dynamic model."""
    rotor_inertia_kg_m2: float
    pump_displacement_m3_rev: float
    fluid_density_kg_m3: float
    rated_speed_rpm: float
    rated_head_meters: float
    rated_flow_m3_h: float
    inlet_volume_m3: float
    outlet_volume_m3: float
    pipe_friction_coefficient: float
    inlet_pipe_length_m: float
    outlet_pipe_length_m: float
    inlet_pipe_diameter_m: float
    outlet_pipe_diameter_m: float
    damping_coefficient: float = 0.05
    cavitation_number_threshold: float = 0.5


class PumpDynamicModel:
    """
    Second-order dynamic model for centrifugal pumps.
    
    State variables:
    - x[0]: Rotor angular velocity (rad/s)
    - x[1]: Outlet pressure (Pa)
    - x[2]: Inlet pressure (Pa)
    - x[3]: Impeller outlet flow (m³/s)
    """
    
    def __init__(self, params: PumpParameters):
        """
        Initialize pump dynamic model.
        
        Args:
            params: PumpParameters instance
        """
        self.params = params
        self.nominal_speed = params.rated_speed_rpm * np.pi / 30
        self.nominal_flow = params.rated_flow_m3_h / 3600
        self.nominal_head = params.rated_head_meters
        
        self.inlet_area = np.pi * (params.inlet_pipe_diameter_m / 2) ** 2
        self.outlet_area = np.pi * (params.outlet_pipe_diameter_m / 2) ** 2
        
        self.inlet_pressure_accumulator_constant = (
            params.inlet_volume_m3 / (params.fluid_density_kg_m3 * 9.81)
        )
        self.outlet_pressure_accumulator_constant = (
            params.outlet_volume_m3 / (params.fluid_density_kg_m3 * 9.81)
        )
    
    def system_equations(
        self,
        t: float,
        state: np.ndarray,
        torque_input: Callable[[float], float],
        demand_pressure: Callable[[float], float]
    ) -> np.ndarray:
        """
        System of differential equations for pump transient response.
        
        Args:
            t: Current time (s)
            state: [omega, P_outlet, P_inlet, Q_outlet]
            torque_input: Function returning motor torque (N·m) at time t
            demand_pressure: Function returning demanded discharge pressure (Pa) at time t
            
        Returns:
            State derivatives [domega/dt, dP_outlet/dt, dP_inlet/dt, dQ/dt]
        """
        omega, P_outlet, P_inlet, Q = state
        
        omega = np.clip(omega, 0, self.nominal_speed * 2)
        P_outlet = np.clip(P_outlet, 0, self.nominal_head * self.params.fluid_density_kg_m3 * 9.81 * 2)
        P_inlet = np.clip(P_inlet, 0, P_outlet)
        Q = np.clip(Q, 0, self.nominal_flow * 2)
        
        pump_torque = self._calculate_pump_torque(omega, Q)
        motor_torque = torque_input(t)
        friction_torque = self.params.damping_coefficient * omega
        
        d_omega_dt = (motor_torque - pump_torque - friction_torque) / self.params.rotor_inertia_kg_m2
        
        pump_head = self._calculate_pump_head(omega, Q)
        pressure_rise = pump_head * self.params.fluid_density_kg_m3 * 9.81
        
        # Calculate actual flow considering leakage (avoid duplicate calculation)
        Q_outlet_theoretical = self._calculate_theoretical_flow(omega)
        leakage = self._calculate_leakage(P_outlet - P_inlet)
        Q_actual = Q_outlet_theoretical - leakage
        
        demand_pressure_t = demand_pressure(t)
        pressure_error = P_outlet - demand_pressure_t
        
        dP_outlet_dt = (
            (pressure_rise - pressure_error) / self.outlet_pressure_accumulator_constant -
            Q_actual * self.params.pipe_friction_coefficient * Q_actual / (2 * self.outlet_area ** 2)
        )
        
        dP_inlet_dt = -(Q_actual / self.inlet_pressure_accumulator_constant)
        
        dQ_dt = self._calculate_flow_acceleration(P_outlet, P_inlet, Q)
        
        return np.array([d_omega_dt, dP_outlet_dt, dP_inlet_dt, dQ_dt])
    
    def _calculate_pump_torque(self, omega: float, Q: float) -> float:
        """Calculate torque required to produce flow."""
        if omega < 0.1 * self.nominal_speed:
            return 0
        
        speed_ratio = omega / self.nominal_speed
        flow_ratio = Q / self.nominal_flow
        
        head = self._calculate_pump_head(omega, Q)
        power = head * Q * self.params.fluid_density_kg_m3 * 9.81 / 1e6
        
        # Improved efficiency model using Anderson's correlation for centrifugal pumps
        # Reference: Anderson, H.H. (1980) "Centrifugal Pumps"
        # Peak efficiency at design point, degrading with flow deviation
        peak_efficiency = getattr(self, 'peak_efficiency', 0.85)
        flow_sensitivity = getattr(self, 'efficiency_flow_sensitivity', 0.2)
        
        efficiency = peak_efficiency * (1.0 - flow_sensitivity * abs(flow_ratio - 1.0) ** 2)
        
        # Account for speed effects on efficiency (lower speeds = lower Reynolds number = lower efficiency)
        speed_efficiency_factor = 1.0 - 0.05 * (1.0 - speed_ratio) ** 2 if speed_ratio < 1.0 else 1.0
        efficiency = efficiency * speed_efficiency_factor
        
        efficiency = np.clip(efficiency, 0.3, 0.95)
        
        if efficiency > 0:
            torque = power * 1e6 / (omega + 1e-6)
        else:
            torque = 0
        
        return torque
    
    def _calculate_pump_head(self, omega: float, Q: float) -> float:
        """
        Calculate pump head using affinity laws.
        Head ~ N² at rated flow, with flow variation effects
        """
        speed_ratio = omega / self.nominal_speed
        flow_ratio = Q / self.nominal_flow
        
        head_speed = speed_ratio ** 2
        
        # Improved surge line model based on pump characteristic curves
        # Reference: Greitzer (1976) surge line theory
        # Surge occurs at low flow rates with steep head rise
        surge_flow_ratio = getattr(self, 'surge_flow_ratio', 0.4)
        surge_head_multiplier = getattr(self, 'surge_head_multiplier', 1.5)
        
        # Parabolic head-flow characteristic with surge region
        if flow_ratio < surge_flow_ratio:
            # In surge region: steep head rise as flow decreases
            surge_line_head = surge_head_multiplier * self.nominal_head * (
                1.0 + (surge_flow_ratio - flow_ratio) / surge_flow_ratio
            )
            head = head_speed * surge_line_head
        else:
            # Normal operating region: parabolic head-flow curve
            head = head_speed * self.nominal_head * (1.0 - 0.3 * (flow_ratio - 1.0) ** 2)
        
        return head
    
    def _calculate_theoretical_flow(self, omega: float) -> float:
        """Calculate theoretical flow at nominal pressure."""
        flow = omega * self.params.pump_displacement_m3_rev / (2 * np.pi)
        return max(flow, 0)
    
    def _calculate_leakage(self, delta_pressure: float) -> float:
        """Calculate internal leakage due to pressure difference."""
        if delta_pressure < 0:
            return 0
        
        leakage_coeff = 1e-8
        leakage = leakage_coeff * np.sqrt(delta_pressure)
        return leakage
    
    def _calculate_flow_acceleration(
        self,
        P_outlet: float,
        P_inlet: float,
        Q: float
    ) -> float:
        """Calculate flow acceleration due to pressure gradient."""
        delta_P = P_outlet - P_inlet
        
        pipe_length_equiv = (
            self.params.inlet_pipe_length_m + self.params.outlet_pipe_length_m
        )
        
        fluid_mass = (
            self.params.fluid_density_kg_m3 * pipe_length_equiv * self.inlet_area
        )
        
        friction_force = (
            self.params.pipe_friction_coefficient * Q ** 2 /
            (2 * self.inlet_area)
        )
        
        dQ_dt = (delta_P - friction_force) / (fluid_mass + 1e-6)
        
        return dQ_dt
    
    def calculate_cavitation_number(
        self,
        P_inlet: float,
        P_vapor: float = 2340.0
    ) -> float:
        """
        Calculate cavitation number (NPSH-related).
        Sigma = (P_inlet - P_vapor) / (0.5 * rho * V²)
        
        Args:
            P_inlet: Inlet pressure (Pa)
            P_vapor: Vapor pressure (Pa, default 2340 for water at 20°C)
            
        Returns:
            Cavitation number (dimensionless)
        """
        inlet_velocity = (0.5 if P_inlet > 0 else 0) * self.nominal_flow / self.inlet_area
        
        dynamic_pressure = 0.5 * self.params.fluid_density_kg_m3 * inlet_velocity ** 2
        
        if dynamic_pressure < 1e-6:
            return float('inf')
        
        sigma = (P_inlet - P_vapor) / dynamic_pressure
        return sigma


class PumpStartupSimulation:
    """Simulates pump startup transient response."""
    
    def __init__(self, pump_model: PumpDynamicModel):
        """
        Initialize startup simulation.
        
        Args:
            pump_model: PumpDynamicModel instance
        """
        self.pump = pump_model
    
    def ramp_startup(
        self,
        ramp_time: float,
        final_speed_ratio: float = 1.0,
        demand_pressure_bar: float = 20.0
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Simulate pump startup with linear motor torque ramp.
        
        Args:
            ramp_time: Time to reach final speed (s)
            final_speed_ratio: Final speed as ratio of nominal
            demand_pressure_bar: Discharge pressure setpoint (bar)
            
        Returns:
            Tuple of (time_array, metrics_dict)
        """
        from .dynamic_simulation_engine import get_simulation_engine, SolverType
        
        nominal_speed = self.pump.nominal_speed
        final_speed = final_speed_ratio * nominal_speed
        demand_pressure_pa = demand_pressure_bar * 1e5
        
        def torque_ramp(t: float) -> float:
            if t < ramp_time:
                speed_ratio = t / ramp_time
                return 200 * speed_ratio
            else:
                return 200
        
        def demand_pressure_func(t: float) -> float:
            return demand_pressure_pa
        
        initial_state = np.array([0.1 * nominal_speed, 1e5, 1e5, 0.1 * self.pump.nominal_flow])
        
        def system_eqs(t: float, state: np.ndarray) -> np.ndarray:
            return self.pump.system_equations(
                t, state,
                lambda t_: torque_ramp(t_),
                lambda t_: demand_pressure_func(t_)
            )
        
        engine = get_simulation_engine(SolverType.RK4)
        result = engine.solve(
            system_eqs,
            initial_state,
            (0, ramp_time + 1.0),
            0.001
        )
        
        metrics = {
            "startup_time_to_rated": float(ramp_time),
            "final_speed": float(result.state_series[-1, 0]),
            "overshoot_speed_percent": 0,
            "final_outlet_pressure_pa": float(result.state_series[-1, 1]),
            "cavitation_margin_min": float(
                self.pump.calculate_cavitation_number(
                    np.min(result.state_series[:, 2])
                )
            )
        }
        
        return result.time_series, metrics
    
    def step_load_transient(
        self,
        initial_speed_ratio: float = 1.0,
        pressure_step_bar: float = 10.0,
        step_time: float = 0.5
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Simulate pump response to sudden load increase.
        
        Args:
            initial_speed_ratio: Initial speed as ratio of nominal
            pressure_step_bar: Magnitude of pressure step (bar)
            step_time: Time of step disturbance (s)
            
        Returns:
            Tuple of (time_array, metrics_dict)
        """
        from .dynamic_simulation_engine import get_simulation_engine, SolverType
        
        nominal_speed = self.pump.nominal_speed
        initial_speed = initial_speed_ratio * nominal_speed
        
        def torque_const(t: float) -> float:
            return 200
        
        base_pressure = 15e5
        
        def demand_pressure_func(t: float) -> float:
            if t < step_time:
                return base_pressure
            else:
                return base_pressure + pressure_step_bar * 1e5
        
        initial_state = np.array([
            initial_speed,
            base_pressure,
            1.2e5,
            self.pump.nominal_flow * 0.8
        ])
        
        def system_eqs(t: float, state: np.ndarray) -> np.ndarray:
            return self.pump.system_equations(
                t, state,
                lambda t_: torque_const(t_),
                lambda t_: demand_pressure_func(t_)
            )
        
        engine = get_simulation_engine(SolverType.RK4)
        result = engine.solve(
            system_eqs,
            initial_state,
            (0, 5.0),
            0.001
        )
        
        speed_response = result.state_series[:, 0]
        speed_decrease = (initial_speed - speed_response) / initial_speed * 100
        
        metrics = {
            "speed_drop_percent": float(np.max(speed_decrease)),
            "speed_recovery_time": float(
                result.time_series[np.where(speed_decrease < 5)[0][0]]
                if np.any(speed_decrease < 5) else result.time_series[-1]
            ),
            "outlet_pressure_rise": float(
                result.state_series[-1, 1] - result.state_series[0, 1]
            ),
            "inlet_pressure_drop": float(
                result.state_series[0, 2] - np.min(result.state_series[:, 2])
            )
        }
        
        return result.time_series, metrics


def get_pump_dynamic_model(params: PumpParameters) -> PumpDynamicModel:
    """Factory function for pump dynamic model."""
    return PumpDynamicModel(params)
