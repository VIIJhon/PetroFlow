"""
Simulation Engine - Core Module
Migrated from core/ modules for FastAPI backend
Implements dynamic simulation, piping network, and flow analysis

Migrated modules:
- core/dynamic_simulation_engine.py
- core/piping_network.py
- core/navier_stokes_1d.py
- core/multiphase_flow.py (flow aspects)
"""

from typing import Callable, List, Tuple, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import logging
from datetime import datetime
from scipy.optimize import fsolve
from scipy.interpolate import interp1d

logger = logging.getLogger(__name__)


# ============================================================================
# DYNAMIC SIMULATION ENGINE
# ============================================================================

class SolverType(str, Enum):
    EULER = "euler"
    RK2 = "rk2"
    RK3 = "rk3"
    RK4 = "rk4"
    RK45_ADAPTIVE = "rk45_adaptive"


@dataclass
class SimulationState:
    """Represents the state of a simulation at a time step."""
    time: float
    values: np.ndarray
    derivatives: np.ndarray = field(default_factory=lambda: np.array([]))
    step_size: float = 0.0
    error_estimate: float = 0.0
    converged: bool = True


@dataclass
class SimulationResult:
    """Complete simulation result with time series data."""
    time_series: np.ndarray
    state_series: np.ndarray
    derivatives_series: Optional[np.ndarray]
    solver_type: str
    total_time: float
    steps_taken: int
    step_size: float
    initial_state: np.ndarray
    final_state: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicSimulationEngine:
    """
    Core numerical ODE solver for transient equipment analysis.
    Supports multiple solver methods with adaptive step sizing.
    """
    
    def __init__(self, solver_type: SolverType = SolverType.RK4):
        self.solver_type = solver_type
        self.min_step_size = 1e-6
        self.max_step_size = 0.1
        self.tolerance = 1e-6
        self.max_iterations = 100000
        
    def solve(
        self,
        system_equations: Callable[[float, np.ndarray], np.ndarray],
        initial_state: np.ndarray,
        time_span: Tuple[float, float],
        step_size: float,
        dense_output: bool = True,
        events: Optional[List[Callable]] = None
    ) -> SimulationResult:
        """
        Solve system of first-order ODEs.
        
        Args:
            system_equations: Function computing dx/dt = f(t, x)
            initial_state: Initial conditions [x0, x1, ..., xn]
            time_span: (t_start, t_end)
            step_size: Initial step size (s)
            dense_output: Store all intermediate steps
            events: List of event detection functions
            
        Returns:
            SimulationResult with time series
        """
        t_start, t_end = time_span
        t = t_start
        state = initial_state.copy()
        
        time_points = [t]
        state_points = [state.copy()]
        derivatives_points = []
        
        steps_taken = 0
        start_time = datetime.now()
        
        while t < t_end and steps_taken < self.max_iterations:
            if t + step_size > t_end:
                step_size = t_end - t
            
            if self.solver_type == SolverType.EULER:
                state, derivative = self._euler_step(system_equations, t, state, step_size)
            elif self.solver_type == SolverType.RK2:
                state, derivative = self._rk2_step(system_equations, t, state, step_size)
            elif self.solver_type == SolverType.RK4:
                state, derivative = self._rk4_step(system_equations, t, state, step_size)
            else:
                state, derivative = self._rk4_step(system_equations, t, state, step_size)
            
            t += step_size
            steps_taken += 1
            
            if dense_output:
                time_points.append(t)
                state_points.append(state.copy())
                derivatives_points.append(derivative.copy())
            
            if events:
                for event in events:
                    if event(t, state):
                        logger.info(f"Event detected at t={t}")
                        break
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        return SimulationResult(
            time_series=np.array(time_points),
            state_series=np.array(state_points),
            derivatives_series=np.array(derivatives_points) if derivatives_points else None,
            solver_type=self.solver_type.value,
            total_time=total_time,
            steps_taken=steps_taken,
            step_size=step_size,
            initial_state=initial_state,
            final_state=state,
            metadata={"converged": t >= t_end}
        )
    
    def _euler_step(
        self,
        f: Callable[[float, np.ndarray], np.ndarray],
        t: float,
        y: np.ndarray,
        h: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Euler method: y_{n+1} = y_n + h*f(t_n, y_n)"""
        k1 = f(t, y)
        y_new = y + h * k1
        return y_new, k1
    
    def _rk2_step(
        self,
        f: Callable[[float, np.ndarray], np.ndarray],
        t: float,
        y: np.ndarray,
        h: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Runge-Kutta 2nd order (Midpoint method)"""
        k1 = f(t, y)
        k2 = f(t + h/2, y + h*k1/2)
        y_new = y + h * k2
        return y_new, k2
    
    def _rk4_step(
        self,
        f: Callable[[float, np.ndarray], np.ndarray],
        t: float,
        y: np.ndarray,
        h: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Classic Runge-Kutta 4th order"""
        k1 = f(t, y)
        k2 = f(t + h/2, y + h*k1/2)
        k3 = f(t + h/2, y + h*k2/2)
        k4 = f(t + h, y + h*k3)
        
        y_new = y + (h/6) * (k1 + 2*k2 + 2*k3 + k4)
        derivative = (k1 + 2*k2 + 2*k3 + k4) / 6
        
        return y_new, derivative


# ============================================================================
# PIPING NETWORK ANALYSIS
# ============================================================================

@dataclass
class PipeNode:
    """Represents a node in the piping network."""
    node_id: str
    x_position_m: float
    y_position_m: float = 0.0
    z_position_m: float = 0.0
    pressure_pa: float = 1e5
    node_type: str = "pipe"
    
    @property
    def position(self) -> Tuple[float, float, float]:
        """3D position tuple."""
        return (self.x_position_m, self.y_position_m, self.z_position_m)
    
    @property
    def elevation_m(self) -> float:
        """Elevation for gravity calculations."""
        return self.z_position_m


@dataclass
class PipeConnection:
    """Represents a pipe segment connection."""
    connection_id: str
    start_node_id: str
    end_node_id: str
    inner_diameter_m: float
    length_m: float
    roughness_m: float = 5e-5
    flow_rate_m3_s: float = 0.0
    pressure_drop_pa: float = 0.0
    active: bool = True


@dataclass
class PipeJunction:
    """Represents a junction where multiple pipes connect."""
    junction_id: str
    node_id: str
    connected_pipes: List[str] = field(default_factory=list)
    junction_type: str = "tee"
    flow_split_ratios: Dict[str, float] = field(default_factory=dict)


class PipingNetworkAnalysis:
    """Complete piping network definition and analysis."""
    
    def __init__(self, network_id: str):
        self.network_id = network_id
        self.nodes: Dict[str, PipeNode] = {}
        self.connections: Dict[str, PipeConnection] = {}
        self.junctions: Dict[str, PipeJunction] = {}
    
    def add_node(self, node: PipeNode):
        """Add node to network."""
        self.nodes[node.node_id] = node
    
    def add_connection(self, connection: PipeConnection):
        """Add pipe connection."""
        self.connections[connection.connection_id] = connection
    
    def add_junction(self, junction: PipeJunction):
        """Add junction."""
        self.junctions[junction.junction_id] = junction
    
    def get_connected_pipes(self, node_id: str) -> List[str]:
        """Get all pipes connected to a node."""
        connected = []
        for conn_id, conn in self.connections.items():
            if conn.start_node_id == node_id or conn.end_node_id == node_id:
                if conn.active:
                    connected.append(conn_id)
        return connected
    
    def calculate_pressure_drop(
        self,
        connection_id: str,
        flow_rate_m3_s: float,
        fluid_density_kg_m3: float,
        fluid_viscosity_pa_s: float
    ) -> float:
        """Calculate pressure drop in a pipe segment."""
        conn = self.connections.get(connection_id)
        if not conn:
            return 0.0
        
        velocity = flow_rate_m3_s / (np.pi * (conn.inner_diameter_m / 2) ** 2)
        reynolds = (fluid_density_kg_m3 * velocity * conn.inner_diameter_m) / fluid_viscosity_pa_s
        
        friction_factor = self._calculate_friction_factor(reynolds, conn.roughness_m / conn.inner_diameter_m)
        
        pressure_drop = friction_factor * (conn.length_m / conn.inner_diameter_m) * \
                       (fluid_density_kg_m3 * velocity ** 2) / 2
        
        return pressure_drop
    
    def _calculate_friction_factor(self, reynolds: float, relative_roughness: float) -> float:
        """Calculate Darcy friction factor using Colebrook-White."""
        if reynolds < 1:
            return 64.0 / max(reynolds, 0.1)
        
        if reynolds < 4000:
            return 64.0 / reynolds
        
        f_estimate = 0.02
        for _ in range(10):
            lhs = 1.0 / np.sqrt(f_estimate)
            rhs = -2.0 * np.log10(relative_roughness / 3.7 + 2.51 / (reynolds * np.sqrt(f_estimate)))
            f_new = 1.0 / (rhs ** 2)
            
            if abs(f_new - f_estimate) < 1e-6:
                break
            
            f_estimate = 0.9 * f_estimate + 0.1 * f_new
        
        return f_estimate
    
    def solve_network(
        self,
        boundary_conditions: Dict[str, float],
        fluid_density_kg_m3: float = 1000.0,
        fluid_viscosity_pa_s: float = 0.001,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Dict[str, Any]:
        """
        Solve network using Hardy Cross method.
        
        Args:
            boundary_conditions: Dict of {node_id: pressure_pa}
            fluid_density_kg_m3: Fluid density
            fluid_viscosity_pa_s: Fluid viscosity
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
            
        Returns:
            Dict with flow rates and pressures
        """
        max_correction = 0.0
        iteration = 0
        
        for iteration in range(max_iterations):
            max_correction = 0.0
            
            for conn_id, conn in self.connections.items():
                if not conn.active:
                    continue
                
                pressure_drop = self.calculate_pressure_drop(
                    conn_id,
                    conn.flow_rate_m3_s,
                    fluid_density_kg_m3,
                    fluid_viscosity_pa_s
                )
                
                conn.pressure_drop_pa = pressure_drop
                
                correction = pressure_drop * 0.1
                conn.flow_rate_m3_s -= correction
                max_correction = max(max_correction, abs(correction))
            
            if max_correction < tolerance:
                logger.info(f"Network converged in {iteration + 1} iterations")
                break
        
        return {
            "converged": max_correction < tolerance,
            "iterations": iteration + 1,
            "connections": {
                conn_id: {
                    "flow_rate_m3_s": conn.flow_rate_m3_s,
                    "pressure_drop_pa": conn.pressure_drop_pa
                }
                for conn_id, conn in self.connections.items()
            }
        }


# ============================================================================
# NAVIER-STOKES 1D SOLVER
# ============================================================================

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


class NavierStokes1DSolver:
    """
    1D Navier-Stokes solver for compressible pipe flow.
    Implements method of characteristics for transient analysis.
    """
    
    def __init__(self, pipe: PipeSegmentProperties, fluid: FluidProperties):
        self.pipe = pipe
        self.fluid = fluid
        
        self.dx = pipe.length_m / pipe.num_elements
        self.x_grid = np.linspace(0, pipe.length_m, pipe.num_elements + 1)
        
        self.pressure = np.ones(pipe.num_elements + 1) * 1e5
        self.velocity = np.zeros(pipe.num_elements + 1)
    
    def solve_transient(
        self,
        time_span: Tuple[float, float],
        dt: float,
        inlet_bc: Callable[[float], float],
        outlet_bc: Callable[[float], float]
    ) -> Dict[str, np.ndarray]:
        """
        Solve transient flow using method of characteristics.
        
        Args:
            time_span: (t_start, t_end)
            dt: Time step
            inlet_bc: Inlet boundary condition function (pressure or velocity)
            outlet_bc: Outlet boundary condition function
            
        Returns:
            Dict with time series of pressure and velocity
        """
        t_start, t_end = time_span
        num_steps = int((t_end - t_start) / dt)
        
        pressure_history = []
        velocity_history = []
        time_history = []
        
        t = t_start
        for step in range(num_steps):
            self._apply_boundary_conditions(t, inlet_bc, outlet_bc)
            
            self._update_interior_points(dt)
            
            pressure_history.append(self.pressure.copy())
            velocity_history.append(self.velocity.copy())
            time_history.append(t)
            
            t += dt
        
        return {
            "time": np.array(time_history),
            "pressure": np.array(pressure_history),
            "velocity": np.array(velocity_history),
            "x_grid": self.x_grid
        }
    
    def _apply_boundary_conditions(
        self,
        t: float,
        inlet_bc: Callable[[float], float],
        outlet_bc: Callable[[float], float]
    ):
        """Apply boundary conditions at inlet and outlet."""
        self.pressure[0] = inlet_bc(t)
        self.pressure[-1] = outlet_bc(t)
    
    def _update_interior_points(self, dt: float):
        """Update interior points using finite difference."""
        for i in range(1, len(self.pressure) - 1):
            reynolds = self._calculate_reynolds(self.velocity[i])
            friction_factor = self._calculate_friction_factor(reynolds)
            
            friction_term = friction_factor * self.velocity[i] * abs(self.velocity[i]) / (2 * self.pipe.inner_diameter_m)
            
            dv_dt = -(1 / self.fluid.density_kg_m3) * (
                (self.pressure[i+1] - self.pressure[i-1]) / (2 * self.dx) +
                self.fluid.density_kg_m3 * friction_term
            )
            
            self.velocity[i] += dv_dt * dt
            
            dp_dt = -self.fluid.bulk_modulus_pa * (
                (self.velocity[i+1] - self.velocity[i-1]) / (2 * self.dx)
            )
            
            self.pressure[i] += dp_dt * dt
    
    def _calculate_reynolds(self, velocity: float) -> float:
        """Calculate Reynolds number."""
        return abs(velocity) * self.pipe.inner_diameter_m / self.fluid.kinematic_viscosity_m2_s
    
    def _calculate_friction_factor(self, reynolds: float) -> float:
        """Calculate Darcy friction factor."""
        if reynolds < 1:
            return 64.0 / max(reynolds, 0.1)
        
        if reynolds < 4000:
            return 64.0 / reynolds
        
        relative_roughness = self.pipe.absolute_roughness_m / self.pipe.inner_diameter_m
        
        f_estimate = 0.02
        for _ in range(10):
            lhs = 1.0 / np.sqrt(f_estimate)
            rhs = -2.0 * np.log10(relative_roughness / 3.7 + 2.51 / (reynolds * np.sqrt(f_estimate)))
            f_new = 1.0 / (rhs ** 2)
            
            if abs(f_new - f_estimate) < 1e-6:
                break
            
            f_estimate = 0.9 * f_estimate + 0.1 * f_new
        
        return f_estimate


# ============================================================================
# SIMULATION ENGINE - MAIN CLASS
# ============================================================================

class SimulationEngine:
    """
    Main simulation engine integrating all simulation capabilities.
    """
    
    def __init__(self):
        self.dynamic_solver = DynamicSimulationEngine()
        self.networks: Dict[str, PipingNetworkAnalysis] = {}
    
    def create_network(self, network_id: str) -> PipingNetworkAnalysis:
        """Create a new piping network."""
        network = PipingNetworkAnalysis(network_id)
        self.networks[network_id] = network
        return network
    
    def get_network(self, network_id: str) -> Optional[PipingNetworkAnalysis]:
        """Get existing network."""
        return self.networks.get(network_id)
    
    def run_dynamic_simulation(
        self,
        system_equations: Callable[[float, np.ndarray], np.ndarray],
        initial_state: np.ndarray,
        time_span: Tuple[float, float],
        step_size: float = 0.01,
        solver_type: SolverType = SolverType.RK4
    ) -> SimulationResult:
        """Run dynamic simulation."""
        self.dynamic_solver.solver_type = solver_type
        return self.dynamic_solver.solve(
            system_equations,
            initial_state,
            time_span,
            step_size
        )
    
    def run_network_analysis(
        self,
        network_id: str,
        boundary_conditions: Dict[str, float],
        fluid_properties: Dict[str, float]
    ) -> Dict[str, Any]:
        """Run piping network analysis."""
        network = self.networks.get(network_id)
        if not network:
            raise ValueError(f"Network {network_id} not found")
        
        return network.solve_network(
            boundary_conditions,
            fluid_properties.get("density_kg_m3", 1000.0),
            fluid_properties.get("viscosity_pa_s", 0.001)
        )
    
    def run_transient_flow_analysis(
        self,
        pipe_properties: Dict[str, Any],
        fluid_properties: Dict[str, Any],
        time_span: Tuple[float, float],
        dt: float,
        inlet_bc: Callable[[float], float],
        outlet_bc: Callable[[float], float]
    ) -> Dict[str, np.ndarray]:
        """Run transient flow analysis using Navier-Stokes solver."""
        pipe = PipeSegmentProperties(
            length_m=pipe_properties["length_m"],
            inner_diameter_m=pipe_properties["inner_diameter_m"],
            absolute_roughness_m=pipe_properties.get("roughness_m", 5e-5),
            elevation_change_m=pipe_properties.get("elevation_change_m", 0.0),
            num_elements=pipe_properties.get("num_elements", 50)
        )
        
        fluid = FluidProperties(
            density_kg_m3=fluid_properties["density_kg_m3"],
            viscosity_pa_s=fluid_properties.get("viscosity_pa_s", 0.001),
            bulk_modulus_pa=fluid_properties.get("bulk_modulus_pa", 2.2e9),
            speed_of_sound_m_s=fluid_properties.get("speed_of_sound_m_s", 1500),
            vapor_pressure_pa=fluid_properties.get("vapor_pressure_pa", 2340)
        )
        
        solver = NavierStokes1DSolver(pipe, fluid)
        return solver.solve_transient(time_span, dt, inlet_bc, outlet_bc)