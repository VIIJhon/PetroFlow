"""
1D Navier-Stokes Pipe Flow Solver Module
Implements compressible flow equations for pressure and velocity transients
in pipe networks with friction, acceleration, and gravity effects.

Conservation Laws:
- Mass: d(rho*A)/dt + d(rho*A*v)/dx = 0
- Momentum: rho*A*dv/dt + rho*A*v*dv/dx + dP/dx + f = 0

where f includes friction and gravity losses.

Phase: Phase 3 - Piping Network Analysis
"""

from typing import Callable, Tuple, Dict, Optional, List
from dataclasses import dataclass
import numpy as np
import logging
from scipy.interpolate import interp1d

logger = logging.getLogger(__name__)


@dataclass
class PipeSegmentProperties:
    """Physical properties of a pipe segment."""
    length_m: float
    inner_diameter_m: float
    absolute_roughness_m: float = 5e-5
    elevation_change_m: float = 0.0
    num_elements: int = 50
    
    @property
    def area_m2(self) -> float:
        """Cross-sectional area."""
        return np.pi * (self.inner_diameter_m / 2) ** 2
    
    @property
    def perimeter_m(self) -> float:
        """Wetted perimeter."""
        return np.pi * self.inner_diameter_m
    
    @property
    def hydraulic_diameter_m(self) -> float:
        """Hydraulic diameter."""
        return 4 * self.area_m2 / self.perimeter_m


@dataclass
class FluidProperties:
    """Fluid properties for flow simulation."""
    density_kg_m3: float
    viscosity_pa_s: float = 0.001
    bulk_modulus_pa: float = 2.2e9
    speed_of_sound_m_s: float = 1500
    vapor_pressure_pa: float = 2340
    
    @property
    def kinematic_viscosity_m2_s(self) -> float:
        """Kinematic viscosity."""
        return self.viscosity_pa_s / self.density_kg_m3


class FrictionModel:
    """Calculate friction factor using Colebrook-White equation."""
    
    @staticmethod
    def colebrook_white(reynolds: float, relative_roughness: float) -> float:
        """
        Colebrook-White friction factor.
        Valid for turbulent flow (Re > 4000)
        
        1/sqrt(f) = -2*log10(epsilon/(3.7*D) + 2.51/(Re*sqrt(f)))
        """
        if reynolds < 1:
            return 64.0 / max(reynolds, 0.1)
        
        if reynolds < 4000:
            return 64.0 / reynolds
        
        f_estimate = 0.02
        for _ in range(10):
            lhs = 1.0 / np.sqrt(f_estimate)
            rhs = -2.0 * np.log10(
                relative_roughness / 3.7 + 2.51 / (reynolds * np.sqrt(f_estimate))
            )
            f_new = 1.0 / (rhs ** 2)
            
            if abs(f_new - f_estimate) < 1e-6:
                break
            
            f_estimate = 0.9 * f_estimate + 0.1 * f_new
        
        return f_estimate
    
    @staticmethod
    def friction_head_loss(
        velocity_m_s: float,
        diameter_m: float,
        length_m: float,
        roughness_m: float,
        density_kg_m3: float,
        viscosity_pa_s: float
    ) -> float:
        """
        Darcy-Weisbach friction head loss.
        
        hf = f * (L/D) * (v²/2g)
        
        Returns pressure drop (Pa).
        """
        if abs(velocity_m_s) < 1e-6:
            return 0.0
        
        kinematic_visc = viscosity_pa_s / density_kg_m3
        reynolds = abs(velocity_m_s) * diameter_m / kinematic_visc
        relative_roughness = roughness_m / diameter_m
        
        friction_factor = FrictionModel.colebrook_white(reynolds, relative_roughness)
        
        velocity_head = 0.5 * density_kg_m3 * velocity_m_s ** 2
        friction_loss = friction_factor * (length_m / diameter_m) * velocity_head
        
        return friction_loss * np.sign(velocity_m_s)


class NavierStokes1DSolver:
    """
    1D Navier-Stokes solver for compressible pipe flow.
    Uses method of characteristics with finite differences.
    
    State variables:
    - x[0:n]: Pressure at nodes (Pa)
    - x[n:2n]: Velocity at elements (m/s)
    """
    
    def __init__(
        self,
        pipe_properties: PipeSegmentProperties,
        fluid_properties: FluidProperties
    ):
        """
        Initialize NS1D solver.
        
        Args:
            pipe_properties: Pipe geometry and roughness
            fluid_properties: Fluid physical properties
        """
        self.pipe = pipe_properties
        self.fluid = fluid_properties
        
        self.n_elements = pipe_properties.num_elements
        self.dx = pipe_properties.length_m / self.n_elements
        self.n_nodes = self.n_elements + 1
        
        self.c = fluid_properties.speed_of_sound_m_s
        self.courant_max = 0.9
        self.dt_max = self.courant_max * self.dx / self.c
        
        logger.info(
            f"NS1D initialized: {self.n_elements} elements, "
            f"dx={self.dx:.4f}m, dt_max={self.dt_max:.6f}s"
        )
    
    def system_equations(
        self,
        t: float,
        state: np.ndarray,
        inlet_pressure: Callable[[float], float],
        outlet_pressure: Callable[[float], float],
        inlet_velocity: Callable[[float], float]
    ) -> np.ndarray:
        """
        System of ODEs for pressure and velocity dynamics.
        
        Args:
            t: Current time (s)
            state: [P_nodes, v_elements] concatenated
            inlet_pressure: Function P_inlet(t)
            outlet_pressure: Function P_outlet(t)
            inlet_velocity: Function v_inlet(t)
            
        Returns:
            State derivatives [dP/dt, dv/dt]
        """
        P = state[:self.n_nodes].copy()
        v = state[self.n_nodes:self.n_nodes + self.n_elements].copy()
        
        P = np.clip(P, 1e5, 2e7)
        v = np.clip(v, -100, 100)
        
        dP_dt = np.zeros(self.n_nodes)
        dv_dt = np.zeros(self.n_elements)
        
        # Enforce boundary conditions: pressure at inlet and outlet
        P[0] = inlet_pressure(t)
        P[-1] = outlet_pressure(t)
        
        dv_dt[0] = self._element_momentum_equation(
            0, P, v, inlet_velocity(t)
        )
        
        for i in range(1, self.n_elements):
            dv_dt[i] = self._element_momentum_equation(i, P, v, None)
        
        for j in range(1, self.n_nodes - 1):
            dP_dt[j] = self._node_continuity_equation(j, P, v)
        
        # Boundary conditions: fixed pressure at inlet and outlet (dP/dt = 0)
        dP_dt[0] = 0.0
        dP_dt[-1] = 0.0
        
        return np.concatenate([dP_dt, dv_dt])
    
    def _element_momentum_equation(
        self,
        element_idx: int,
        P: np.ndarray,
        v: np.ndarray,
        inlet_v: Optional[float] = None
    ) -> float:
        """
        Momentum equation for element.
        
        rho * dv/dt = -(dP/dx) - f_friction - rho*g*sin(theta)
        """
        if inlet_v is not None:
            v_current = inlet_v
            dP_dx = (P[element_idx + 1] - P[element_idx]) / self.dx
        else:
            v_current = v[element_idx]
            dP_dx = (P[element_idx + 1] - P[element_idx]) / self.dx
        
        friction_loss = FrictionModel.friction_head_loss(
            v_current,
            self.pipe.inner_diameter_m,
            self.dx,
            self.pipe.absolute_roughness_m,
            self.fluid.density_kg_m3,
            self.fluid.viscosity_pa_s
        )
        
        # Gravity term: positive elevation change (upward) opposes flow (negative contribution)
        # Sign convention: gravity_term is positive for upward flow, negative for downward
        gravity_term = (
            self.fluid.density_kg_m3 * 9.81 *
            (self.pipe.elevation_change_m / self.pipe.length_m)
        )
        
        # Momentum equation: dv/dt = -(dP/dx + friction - rho*g*sin(theta)) / rho
        # The gravity term opposes upward flow, so it's subtracted
        dv_dt = -(dP_dx + friction_loss / self.dx - gravity_term) / self.fluid.density_kg_m3
        
        return dv_dt
    
    def _node_continuity_equation(
        self,
        node_idx: int,
        P: np.ndarray,
        v: np.ndarray
    ) -> float:
        """
        Continuity equation at node.
        
        dP/dt = -rho*c²*(dv/dx)
        
        where c is speed of sound.
        """
        dv_dx = (v[node_idx] - v[node_idx - 1]) / self.dx
        
        dP_dt = -self.fluid.density_kg_m3 * (self.c ** 2) * dv_dx
        
        return dP_dt
    
    def calculate_flow_rate(
        self,
        velocity: np.ndarray
    ) -> np.ndarray:
        """Calculate volumetric flow rate at each element."""
        return velocity * self.pipe.area_m2
    
    def calculate_reynolds_number(
        self,
        velocity: np.ndarray
    ) -> np.ndarray:
        """Calculate Reynolds number at each element."""
        kinematic_visc = self.fluid.kinematic_viscosity_m2_s
        return np.abs(velocity) * self.pipe.inner_diameter_m / kinematic_visc
    
    def detect_cavitation(
        self,
        pressure: np.ndarray,
        vapor_pressure: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Detect cavitation regions.
        
        Args:
            pressure: Pressure field (Pa)
            vapor_pressure: Vapor pressure threshold (Pa)
            
        Returns:
            Cavitation detection metrics
        """
        if vapor_pressure is None:
            vapor_pressure = self.fluid.vapor_pressure_pa
        
        cavitation_mask = pressure < vapor_pressure
        cavitation_nodes = np.where(cavitation_mask)[0]
        
        npsh_available = pressure - vapor_pressure
        npsh_min = np.min(npsh_available)
        cavitation_margin = npsh_min / vapor_pressure
        
        return {
            "cavitation_detected": bool(np.any(cavitation_mask)),
            "cavitation_nodes": cavitation_nodes.tolist(),
            "num_cavitation_nodes": int(np.sum(cavitation_mask)),
            "npsh_available_pa": float(np.min(npsh_available)),
            "cavitation_margin": float(cavitation_margin),
            "min_pressure_pa": float(np.min(pressure))
        }


class CompressibleFlowAnalyzer:
    """Analyzes compressible flow effects and wave propagation."""
    
    def __init__(self, fluid_properties: FluidProperties):
        """Initialize analyzer."""
        self.fluid = fluid_properties
    
    def mach_number(self, velocity_m_s: float) -> float:
        """Calculate Mach number."""
        return abs(velocity_m_s) / self.fluid.speed_of_sound_m_s
    
    def pressure_wave_propagation(
        self,
        initial_pressure: np.ndarray,
        x_positions: np.ndarray,
        wave_speed: float,
        time: float
    ) -> np.ndarray:
        """
        Model pressure wave propagation using method of characteristics.
        
        Args:
            initial_pressure: Initial pressure field
            x_positions: Position array
            wave_speed: Speed of wave propagation (m/s)
            time: Time (s)
            
        Returns:
            Pressure field at given time
        """
        characteristics_position = x_positions - wave_speed * time
        
        f = interp1d(
            x_positions,
            initial_pressure,
            kind='cubic',
            bounds_error=False,
            fill_value='extrapolate'
        )
        
        return f(characteristics_position)
    
    def pressure_transient_severity(
        self,
        pressure_change_pa: float,
        rated_pressure_pa: float
    ) -> Dict[str, any]:
        """
        Classify pressure transient severity.
        
        Args:
            pressure_change_pa: Magnitude of pressure change
            rated_pressure_pa: Rated system pressure
            
        Returns:
            Severity classification
        """
        transient_ratio = pressure_change_pa / rated_pressure_pa
        
        if transient_ratio < 0.05:
            severity = "LOW"
            risk_level = 1
        elif transient_ratio < 0.15:
            severity = "MODERATE"
            risk_level = 2
        elif transient_ratio < 0.30:
            severity = "HIGH"
            risk_level = 3
        else:
            severity = "CRITICAL"
            risk_level = 4
        
        return {
            "severity": severity,
            "risk_level": risk_level,
            "transient_ratio": float(transient_ratio),
            "pressure_change_pa": float(pressure_change_pa),
            "rated_pressure_pa": float(rated_pressure_pa)
        }


def get_ns1d_solver(
    pipe_properties: PipeSegmentProperties,
    fluid_properties: FluidProperties
) -> NavierStokes1DSolver:
    """Factory function for NS1D solver."""
    return NavierStokes1DSolver(pipe_properties, fluid_properties)
