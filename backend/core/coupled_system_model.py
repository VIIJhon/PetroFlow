"""
Coupled System Model Module
Integrates pump dynamics, piping network, and manifold models
into a complete coupled system for well production systems.

Handles:
- Pump-pipe inlet coupling
- Manifold distribution logic
- Outlet backpressure effects
- System-level transients

Phase: Phase 3 - Piping Network Analysis
"""

from typing import Dict, List, Callable, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemNode:
    """Represents a node in coupled system."""
    node_id: str
    pressure_pa: float = 1e5
    flow_rate_m3_s: float = 0.0
    temperature_k: float = 298.15
    node_type: str = "pipe"


@dataclass
class CoupledSystemConfiguration:
    """Configuration for coupled pump-pipe-manifold system."""
    pump_outlet_node_id: str
    inlet_manifold_node_id: str
    outlet_manifold_node_id: str
    discharge_line_id: str
    inlet_line_id: str
    manifold_volume_m3: float = 0.1
    manifold_dead_volume_m3: float = 0.01


class CoupledSystemModel:
    """
    Complete coupled model for pump-pipe-manifold systems.
    
    State variables:
    - Pump rotor speed (from pump model)
    - Pipe pressures and velocities (from NS1D)
    - Manifold pressure and accumulated mass
    """
    
    def __init__(
        self,
        config: CoupledSystemConfiguration,
        pump_inertia_kg_m2: float = 5.0,
        fluid_density_kg_m3: float = 850,
        bulk_modulus_pa: float = 2.2e9,
        pipe_length_m: float = 100,
        pipe_diameter_m: float = 0.05
    ):
        """Initialize coupled system."""
        self.config = config
        self.pump_inertia = pump_inertia_kg_m2
        self.fluid_density = fluid_density_kg_m3
        self.bulk_modulus = bulk_modulus_pa
        self.pipe_length = pipe_length_m
        self.pipe_diameter = pipe_diameter_m
        
        self.pipe_area = np.pi * (pipe_diameter_m / 2) ** 2
        self.system_nodes: Dict[str, SystemNode] = {}
        
        self._initialize_system_nodes()
        
        logger.info(
            f"Coupled system initialized: "
            f"pump -> {pipe_diameter_m*1000:.1f}mm pipe ({pipe_length_m}m) -> manifold"
        )
    
    def _initialize_system_nodes(self):
        """Initialize system nodes."""
        self.system_nodes[self.config.pump_outlet_node_id] = SystemNode(
            self.config.pump_outlet_node_id,
            pressure_pa=1.5e6,
            node_type="pump_outlet"
        )
        self.system_nodes[self.config.inlet_manifold_node_id] = SystemNode(
            self.config.inlet_manifold_node_id,
            pressure_pa=1.4e6,
            node_type="manifold_inlet"
        )
        self.system_nodes[self.config.outlet_manifold_node_id] = SystemNode(
            self.config.outlet_manifold_node_id,
            pressure_pa=1.0e6,
            node_type="manifold_outlet"
        )
    
    def system_equations(
        self,
        t: float,
        state: np.ndarray,
        pump_model_callback: Callable,
        demand_pressure_func: Callable[[float], float]
    ) -> np.ndarray:
        """
        Coupled system ODEs.
        
        State: [pump_speed, pipe_flow, P_inlet_manifold, manifold_accum]
        
        Args:
            t: Current time
            state: System state vector
            pump_model_callback: Function computing pump torque/flow
            demand_pressure_func: Function returning demanded pressure
            
        Returns:
            State derivatives
        """
        pump_speed, pipe_flow, P_manifold_inlet, manifold_mass = state
        
        pump_speed = np.clip(pump_speed, 0, 200)
        pipe_flow = np.clip(pipe_flow, -0.05, 0.5)
        P_manifold_inlet = np.clip(P_manifold_inlet, 1e5, 2e7)
        
        pump_outlet_flow, pump_head = pump_model_callback(pump_speed)
        pump_outlet_pressure = 1e5 + pump_head * self.fluid_density * 9.81
        
        friction_loss = self._calculate_line_friction(pipe_flow)
        
        P_inlet_manifold = pump_outlet_pressure - friction_loss
        
        dQ_dt = self._pipe_acceleration_equation(
            pump_outlet_pressure,
            P_manifold_inlet,
            pipe_flow
        )
        
        demand_pressure = demand_pressure_func(t)
        mass_flow_in = pipe_flow * self.fluid_density
        mass_flow_out = self._calculate_outlet_flow(P_manifold_inlet, demand_pressure)
        
        dP_manifold_dt = self._manifold_pressure_equation(
            P_manifold_inlet,
            mass_flow_in,
            mass_flow_out
        )
        
        dM_manifold_dt = mass_flow_in - mass_flow_out
        
        # Implement proper pump speed dynamics based on torque balance
        # T_motor - T_pump - T_friction = I * d(omega)/dt
        # Using pump power to estimate torque: T = P / omega
        motor_torque = getattr(self, 'motor_torque_nm', 100.0)  # Configurable motor torque
        
        # Estimate pump torque from power and speed
        pump_power_w = pump_head * pipe_flow * self.fluid_density * 9.81
        pump_torque = (pump_power_w / (pump_speed * 2 * np.pi / 60)) if pump_speed > 0 else 0.0
        
        friction_torque = getattr(self, 'friction_torque_nm', 5.0)  # Configurable friction
        pump_inertia = getattr(self, 'pump_inertia_kg_m2', 0.5)  # Configurable inertia
        
        d_pump_speed_dt = (motor_torque - pump_torque - friction_torque) / pump_inertia if pump_inertia > 0 else 0.0
        
        return np.array([d_pump_speed_dt, dQ_dt, dP_manifold_dt, dM_manifold_dt])
    
    def _calculate_line_friction(self, flow_rate: float) -> float:
        """Calculate pressure drop in discharge line."""
        from .navier_stokes_1d import FrictionModel
        
        if abs(flow_rate) < 1e-6:
            return 0.0
        
        velocity = flow_rate / self.pipe_area
        
        friction_loss = FrictionModel.friction_head_loss(
            velocity,
            self.pipe_diameter,
            self.pipe_length,
            5e-5,
            self.fluid_density,
            0.001
        )
        
        return friction_loss
    
    def _pipe_acceleration_equation(
        self,
        P_upstream: float,
        P_downstream: float,
        Q_current: float
    ) -> float:
        """
        Calculate flow acceleration in pipe.
        
        L_p * dQ/dt = (P_up - P_down) - f_friction
        """
        pipe_inertance = (self.pipe_length / self.pipe_area) / 9.81
        
        pressure_gradient = (P_upstream - P_downstream) / 1e5
        
        # Calculate proper friction using Darcy-Weisbach equation
        velocity = Q_current / self.pipe_area if self.pipe_area > 0 else 0.0
        reynolds = (self.fluid_density * abs(velocity) * self.pipe_diameter) / getattr(self, 'fluid_viscosity_pa_s', 0.001)
        
        # Friction factor (Swamee-Jain approximation for turbulent flow)
        if reynolds > 2300:
            roughness = getattr(self, 'pipe_roughness_m', 5e-5)
            friction_factor = 0.25 / (np.log10(roughness / (3.7 * self.pipe_diameter) + 5.74 / (reynolds ** 0.9))) ** 2
        else:
            friction_factor = 64 / reynolds if reynolds > 0 else 0.0
        
        friction_loss = friction_factor * (self.pipe_length / self.pipe_diameter) * (velocity ** 2) / (2 * 9.81)
        friction_term = friction_loss * np.sign(Q_current)
        
        dQ_dt = 9.81 * (pressure_gradient - friction_term) / pipe_inertance
        
        return dQ_dt
    
    def _manifold_pressure_equation(
        self,
        P_manifold: float,
        mass_flow_in: float,
        mass_flow_out: float
    ) -> float:
        """
        Pressure change in manifold due to accumulator effect.
        
        V_eff * dP/dt = (m_in - m_out) * RT / rho
        """
        accumulator_factor = self.config.manifold_volume_m3 / self.bulk_modulus
        
        net_mass_flow = mass_flow_in - mass_flow_out
        
        dP_dt = net_mass_flow * self.bulk_modulus / (self.config.manifold_volume_m3 * self.fluid_density)
        
        return dP_dt
    
    def _calculate_outlet_flow(
        self,
        P_manifold: float,
        P_demand: float,
        orifice_diameter_m: Optional[float] = None
    ) -> float:
        """
        Calculate outlet flow based on control valve dynamics.
        Assumes orifice equation for control valve.
        
        Q_out = Cd * A * sqrt(2*DP/rho)
        """
        pressure_drop = max(P_manifold - P_demand, 0)
        
        if pressure_drop < 100:
            return 0.0
        
        # Make orifice diameter configurable
        effective_diameter = orifice_diameter_m if orifice_diameter_m is not None else getattr(self, 'orifice_diameter_m', 0.01)
        
        orifice_area = np.pi * (effective_diameter / 2) ** 2
        
        # Make discharge coefficient configurable (typical range: 0.6-0.65 for sharp-edged orifice)
        # Reference: ISO 5167 standard for orifice plates
        discharge_coeff = getattr(self, 'discharge_coefficient', 0.61)
        
        flow_rate = (
            discharge_coeff * orifice_area *
            np.sqrt(2 * pressure_drop / self.fluid_density)
        )
        
        return flow_rate
    
    def calculate_system_efficiency(
        self,
        pump_flow_m3_s: float,
        pump_head_m: float,
        system_flow_m3_s: float,
        system_backpressure_pa: float
    ) -> Dict[str, float]:
        """
        Calculate overall system efficiency.
        
        Args:
            pump_flow_m3_s: Pump delivery flow
            pump_head_m: Pump delivery head
            system_flow_m3_s: Actual system flow
            system_backpressure_pa: System outlet pressure
            
        Returns:
            Efficiency metrics
        """
        pump_power = pump_flow_m3_s * pump_head_m * self.fluid_density * 9.81
        
        system_power = system_flow_m3_s * system_backpressure_pa
        
        hydraulic_efficiency = system_flow_m3_s / pump_flow_m3_s if pump_flow_m3_s > 0 else 0
        pressure_efficiency = system_backpressure_pa / (pump_head_m * self.fluid_density * 9.81) if pump_head_m > 0 else 0
        
        overall_efficiency = hydraulic_efficiency * pressure_efficiency
        
        return {
            "pump_power_w": float(pump_power),
            "system_power_w": float(system_power),
            "hydraulic_efficiency": float(hydraulic_efficiency),
            "pressure_efficiency": float(pressure_efficiency),
            "overall_efficiency": float(overall_efficiency)
        }


class ManifoldModel:
    """Models manifold/header tank behavior."""
    
    def __init__(
        self,
        volume_m3: float,
        inlet_diameter_m: float,
        outlet_diameter_m: float,
        fluid_density_kg_m3: float = 850
    ):
        """Initialize manifold."""
        self.volume = volume_m3
        self.inlet_area = np.pi * (inlet_diameter_m / 2) ** 2
        self.outlet_area = np.pi * (outlet_diameter_m / 2) ** 2
        self.fluid_density = fluid_density_kg_m3
        
        self.residence_time = volume_m3 / 0.1 if 0.1 > 0 else 10
    
    def calculate_residence_time(
        self,
        flow_rate_m3_s: float
    ) -> float:
        """Calculate fluid residence time in manifold."""
        if flow_rate_m3_s < 1e-6:
            return float('inf')
        
        return self.volume / flow_rate_m3_s
    
    def calculate_pressure_recovery(
        self,
        inlet_velocity_m_s: float
    ) -> float:
        """
        Calculate pressure recovery in manifold due to velocity reduction.
        
        DP_recovery = 0.5 * rho * v^2
        """
        return 0.5 * self.fluid_density * inlet_velocity_m_s ** 2
    
    def calculate_manifold_level(
        self,
        mass_in_kg_s: float,
        mass_out_kg_s: float,
        current_mass_kg: float,
        dt: float
    ) -> float:
        """Calculate manifold fluid mass accumulation."""
        net_mass_flow = mass_in_kg_s - mass_out_kg_s
        new_mass = current_mass_kg + net_mass_flow * dt
        
        return new_mass


def get_coupled_system_model(
    config: CoupledSystemConfiguration,
    **kwargs
) -> CoupledSystemModel:
    """Factory function for coupled system model."""
    return CoupledSystemModel(config, **kwargs)
