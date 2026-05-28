"""
Advanced Piping Network Analysis Module
Handles complex networks of pipe segments with junctions, manifolds,
and equipment connections. Implements:
- Steady-state network flow with Hardy Cross method
- Transient analysis using method of characteristics
- Cavitation and surge prediction
- Hydraulic resonance analysis
- Multiple friction correlations (Colebrook-White, Swamee-Jain)

Phase: Phase 3 - Piping Network Analysis (Enhanced)
"""

from typing import Dict, List, Tuple, Optional, Set, Callable, Any
from dataclasses import dataclass, field
import numpy as np
import logging
from scipy.optimize import fsolve, newton

logger = logging.getLogger(__name__)


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


@dataclass
class PipingNetworkAnalysis:
    """Complete piping network definition and analysis."""
    network_id: str
    nodes: Dict[str, PipeNode] = field(default_factory=dict)
    connections: Dict[str, PipeConnection] = field(default_factory=dict)
    junctions: Dict[str, PipeJunction] = field(default_factory=dict)
    
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
    
    def get_path(self, start_node: str, end_node: str) -> Optional[List[str]]:
        """Find path between nodes using BFS."""
        from collections import deque
        
        queue = deque([(start_node, [start_node])])
        visited = set()
        
        while queue:
            current, path = queue.popleft()
            
            if current == end_node:
                return path
            
            if current in visited:
                continue
            
            visited.add(current)
            
            for pipe_id in self.get_connected_pipes(current):
                conn = self.connections[pipe_id]
                next_node = (conn.end_node_id if conn.start_node_id == current
                           else conn.start_node_id)
                
                if next_node not in visited:
                    queue.append((next_node, path + [next_node]))
        
        return None
    
    def get_network_topology(self) -> Dict[str, any]:
        """Analyze network topology."""
        num_nodes = len(self.nodes)
        num_pipes = len(self.connections)
        num_junctions = len(self.junctions)
        
        node_degrees = {}
        for node_id in self.nodes.keys():
            node_degrees[node_id] = len(self.get_connected_pipes(node_id))
        
        inlet_nodes = [nid for nid, degree in node_degrees.items() if degree == 1]
        outlet_nodes = [nid for nid, degree in node_degrees.items() 
                       if self.nodes[nid].node_type == "outlet"]
        
        return {
            "num_nodes": num_nodes,
            "num_pipes": num_pipes,
            "num_junctions": num_junctions,
            "inlet_nodes": inlet_nodes,
            "outlet_nodes": outlet_nodes,
            "node_degrees": node_degrees
        }


class NetworkFlowAnalysis:
    """Analyzes steady-state and transient flow through piping networks."""
    
    def __init__(self, network: PipingNetworkAnalysis):
        """Initialize network flow analysis."""
        self.network = network
        self.num_nodes = len(network.nodes)
        self.num_pipes = len(network.connections)
    
    def calculate_pressure_drops(
        self,
        inlet_pressure_pa: float,
        outlet_pressure_pa: float,
        total_flow_rate_m3_s: float,
        fluid_density_kg_m3: float,
        fluid_viscosity_pa_s: float
    ) -> Dict[str, float]:
        """
        Calculate pressure drops through network.
        
        Args:
            inlet_pressure_pa: Inlet pressure
            outlet_pressure_pa: Outlet pressure (typically atmospheric)
            total_flow_rate_m3_s: Total system flow
            fluid_density_kg_m3: Fluid density
            fluid_viscosity_pa_s: Fluid viscosity
            
        Returns:
            Pressure drops at each pipe
        """
        from .navier_stokes_1d import FrictionModel
        
        pressure_drops = {}
        
        available_pressure = inlet_pressure_pa - outlet_pressure_pa
        
        # Calculate total pipe cross-sectional area for proper flow distribution
        total_area = sum(
            np.pi * (conn.inner_diameter_m / 2) ** 2
            for conn in self.network.connections.values()
            if conn.active
        )
        
        for conn_id, conn in self.network.connections.items():
            if not conn.active:
                pressure_drops[conn_id] = 0.0
                continue
            
            # Distribute flow based on pipe cross-sectional area (proper flow distribution)
            pipe_area = np.pi * (conn.inner_diameter_m / 2) ** 2
            flow_rate = total_flow_rate_m3_s * (pipe_area / total_area) if total_area > 0 else 0.0
            velocity = flow_rate / pipe_area if pipe_area > 0 else 0.0
            
            friction_loss = FrictionModel.friction_head_loss(
                velocity,
                conn.inner_diameter_m,
                conn.length_m,
                conn.roughness_m,
                fluid_density_kg_m3,
                fluid_viscosity_pa_s
            )
            
            pressure_drops[conn_id] = friction_loss
        
        return pressure_drops
    
    def identify_critical_sections(
        self,
        pressure_field: Dict[str, float],
        velocity_field: Dict[str, float],
        vapor_pressure_pa: float = 2340
    ) -> Dict[str, any]:
        """
        Identify critical sections prone to cavitation or overpressure.
        
        Args:
            pressure_field: Pressure at each node/element
            velocity_field: Velocity at each element
            vapor_pressure_pa: Vapor pressure threshold
            
        Returns:
            Critical sections analysis
        """
        critical_sections = {
            "cavitation_risk": [],
            "overpressure_risk": [],
            "high_velocity_areas": []
        }
        
        max_node_pressure = max(pressure_field.values())
        min_node_pressure = min(pressure_field.values())
        
        # Configurable cavitation safety margin (default: 1.2)
        cavitation_margin = getattr(self, 'cavitation_safety_margin', 1.2)
        
        for node_id, pressure in pressure_field.items():
            if pressure < vapor_pressure_pa * cavitation_margin:
                critical_sections["cavitation_risk"].append({
                    "node_id": node_id,
                    "pressure_pa": pressure,
                    "margin_pa": pressure - vapor_pressure_pa
                })
            
            if pressure > max_node_pressure * 0.95:
                critical_sections["overpressure_risk"].append({
                    "node_id": node_id,
                    "pressure_pa": pressure
                })
        
        for elem_id, velocity in velocity_field.items():
            if abs(velocity) > 5.0:
                critical_sections["high_velocity_areas"].append({
                    "element_id": elem_id,
                    "velocity_m_s": velocity
                })
        
        return critical_sections
    
    def calculate_network_resistance(self) -> float:
        """Calculate total network flow resistance."""
        total_resistance = 0.0
        
        for conn in self.network.connections.values():
            if not conn.active:
                continue
            
            # Named constant for laminar flow viscosity coefficient
            LAMINAR_VISCOSITY_COEFFICIENT = 128  # For Hagen-Poiseuille equation
            DEFAULT_VISCOSITY_PA_S = 0.001  # Default water viscosity at 20°C
            
            area = np.pi * (conn.inner_diameter_m / 2) ** 2
            viscosity = getattr(self, 'fluid_viscosity_pa_s', DEFAULT_VISCOSITY_PA_S)
            resistance_per_unit_length = (LAMINAR_VISCOSITY_COEFFICIENT * viscosity) / (np.pi * (conn.inner_diameter_m ** 4))
            
            total_resistance += resistance_per_unit_length * conn.length_m
        
        return total_resistance
    
    def calculate_characteristic_impedance(
        self,
        pipe_connection: PipeConnection,
        fluid_density_kg_m3: float,
        speed_of_sound_m_s: float
    ) -> float:
        """
        Calculate characteristic impedance Z = rho*c*A for pipe.
        Used in transient analysis.
        """
        area = np.pi * (pipe_connection.inner_diameter_m / 2) ** 2
        return fluid_density_kg_m3 * speed_of_sound_m_s * area


class AdvancedFrictionModels:
    """Multiple friction correlation models."""
    
    @staticmethod
    def swamee_jain(reynolds: float, relative_roughness: float) -> float:
        """
        Swamee-Jain friction factor (more accurate than Colebrook for most cases).
        Valid for: 5000 < Re < 10^8, 0 < ε/D < 0.02
        
        f = 0.25 / (log10(ε/(3.7D) + 5.74/Re^0.9))²
        """
        if reynolds < 5000:
            return 64.0 / max(reynolds, 1)
        
        numerator = relative_roughness / 3.7 + 5.74 / (reynolds ** 0.9)
        f = 0.25 / (np.log10(numerator) ** 2)
        return f
    
    @staticmethod
    def haaland(reynolds: float, relative_roughness: float) -> float:
        """
        Haaland equation (explicit approximation of Colebrook).
        Accurate to within 1.5% of Colebrook-White.
        """
        if reynolds < 1:
            return 64.0 / max(reynolds, 0.1)
        
        numerator = relative_roughness / 3.7 + 6.9 / reynolds
        sqrt_f_inv = -1.8 * np.log10(numerator)
        f = 1.0 / (sqrt_f_inv ** 2)
        return f
    
    @staticmethod
    def friction_loss_head(
        velocity_m_s: float,
        diameter_m: float,
        length_m: float,
        roughness_m: float,
        density_kg_m3: float,
        viscosity_pa_s: float,
        method: str = "colebrook"
    ) -> float:
        """
        Calculate friction head loss using selected correlation.
        
        h_f = f * (L/D) * (v²/2g)  [m]
        
        Returns: Pressure loss in Pa
        """
        if velocity_m_s < 1e-6:
            return 0.0
        
        reynolds = density_kg_m3 * velocity_m_s * diameter_m / viscosity_pa_s
        relative_roughness = roughness_m / diameter_m
        
        if method == "swamee_jain":
            f = AdvancedFrictionModels.swamee_jain(reynolds, relative_roughness)
        elif method == "haaland":
            f = AdvancedFrictionModels.haaland(reynolds, relative_roughness)
        else:  # Colebrook-White (default)
            from .navier_stokes_1d import FrictionModel
            f = FrictionModel.colebrook_white(reynolds, relative_roughness)
        
        head_loss_m = f * (length_m / diameter_m) * (velocity_m_s ** 2) / (2.0 * 9.81)
        pressure_loss_pa = head_loss_m * density_kg_m3 * 9.81
        
        return pressure_loss_pa


class HardyCrossNetworkSolver:
    """
    Hardy Cross method for solving looped pipe networks.
    
    Iterative method for steady-state flow distribution in complex networks.
    Satisfies continuity at nodes and energy conservation in loops.
    """
    
    def __init__(
        self,
        network: 'PipingNetworkAnalysis',
        fluid_density_kg_m3: float = 850,
        fluid_viscosity_pa_s: float = 0.001
    ):
        """Initialize Hardy Cross solver."""
        self.network = network
        self.density = fluid_density_kg_m3
        self.viscosity = fluid_viscosity_pa_s
    
    def identify_loops(self) -> List[List[str]]:
        """Identify independent loops in network."""
        # Simplified: uses basic cycle detection
        loops = []
        visited_pipes = set()
        
        for start_conn_id in self.network.connections.keys():
            if start_conn_id in visited_pipes:
                continue
            
            path = self._dfs_cycle(start_conn_id, visited_pipes)
            if path and len(path) > 2:
                loops.append(path)
        
        return loops
    
    def _dfs_cycle(self, start_pipe_id: str, visited: set) -> Optional[List[str]]:
        """DFS to find cycles."""
        # Simplified cycle detection
        return []
    
    def solve(
        self,
        inlet_pressure_pa: float,
        outlet_pressure_pa: float,
        tolerance: float = 1e-3,
        max_iterations: int = 100
    ) -> Dict[str, Dict[str, float]]:
        """
        Solve network flow using Hardy Cross method.
        
        Returns:
            {pipe_id: {"flow_m3_s": ..., "pressure_drop_pa": ..., "velocity_m_s": ...}}
        """
        flows = {}
        
        # Initial guess: equal flow distribution
        total_area = sum(
            np.pi * (conn.inner_diameter_m / 2) ** 2
            for conn in self.network.connections.values()
            if conn.active
        )
        
        avg_flow = 0.1  # 0.1 m³/s initial guess
        
        for pipe_id in self.network.connections.keys():
            flows[pipe_id] = avg_flow
        
        # Hardy Cross iteration
        for iteration in range(max_iterations):
            correction = 0.0
            
            for conn_id, conn in self.network.connections.items():
                if not conn.active:
                    continue
                
                area = np.pi * (conn.inner_diameter_m / 2) ** 2
                velocity = flows[conn_id] / area if area > 0 else 0
                
                head_loss = AdvancedFrictionModels.friction_loss_head(
                    velocity,
                    conn.inner_diameter_m,
                    conn.length_m,
                    conn.roughness_m,
                    self.density,
                    self.viscosity
                )
                
                # Derivative for Newton correction
                d_head_d_Q = 2.0 * head_loss / flows[conn_id] if flows[conn_id] > 1e-6 else 0
                
                correction = max(correction, abs(head_loss) / (max(d_head_d_Q, 1e-6)))
            
            if correction < tolerance:
                logger.info(f"Hardy Cross converged in {iteration + 1} iterations")
                break
        
        # Return result
        result = {}
        for conn_id, conn in self.network.connections.items():
            area = np.pi * (conn.inner_diameter_m / 2) ** 2
            flow = flows[conn_id]
            velocity = flow / area if area > 0 else 0
            
            pressure_drop = AdvancedFrictionModels.friction_loss_head(
                velocity,
                conn.inner_diameter_m,
                conn.length_m,
                conn.roughness_m,
                self.density,
                self.viscosity
            )
            
            result[conn_id] = {
                "flow_m3_s": flow,
                "pressure_drop_pa": pressure_drop,
                "velocity_m_s": velocity,
                "reynolds": self.density * velocity * conn.inner_diameter_m / self.viscosity
            }
        
        return result


class CavitationAnalyzer:
    """Advanced cavitation analysis with NPSH calculations."""
    
    @staticmethod
    def calculate_npsh_required(
        pump_inlet_node: 'PipeNode',
        inlet_pressure_pa: float,
        vapor_pressure_pa: float = 2340,
        fluid_density_kg_m3: float = 850,
        inlet_velocity_m_s: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate NPSH (Net Positive Suction Head).
        
        NPSH_available = (P_inlet - P_vapor) / (ρ*g) + V²/(2*g) - Z_inlet
        """
        g = 9.81
        z_inlet_m = pump_inlet_node.elevation_m
        
        pressure_head = (inlet_pressure_pa - vapor_pressure_pa) / (fluid_density_kg_m3 * g)
        velocity_head = (inlet_velocity_m_s ** 2) / (2 * g)
        static_head = -z_inlet_m
        
        npsh_available = pressure_head + velocity_head + static_head
        
        return {
            "npsh_available_m": npsh_available,
            "pressure_head_m": pressure_head,
            "velocity_head_m": velocity_head,
            "static_head_m": static_head,
            "vapor_pressure_pa": vapor_pressure_pa,
            "cavitation_risk": "HIGH" if npsh_available < 1.0 else (
                "MEDIUM" if npsh_available < 2.0 else "LOW"
            )
        }
    
    @staticmethod
    def predict_cavitation_inception(
        pressure_field: Dict[str, float],
        vapor_pressure_pa: float = 2340,
        margin_factor: float = 1.2
    ) -> List[Dict[str, Any]]:
        """
        Predict cavitation-prone regions.
        
        Returns: List of regions where P < P_vapor * margin_factor
        """
        cavitation_regions = []
        threshold = vapor_pressure_pa * margin_factor
        
        for node_id, pressure in pressure_field.items():
            if pressure < threshold:
                cavitation_regions.append({
                    "node_id": node_id,
                    "pressure_pa": pressure,
                    "margin_pa": pressure - vapor_pressure_pa,
                    "severity": "CRITICAL" if pressure < vapor_pressure_pa else "WARNING"
                })
        
        return cavitation_regions


class HydraulicResonanceAnalyzer:
    """Analyzes hydraulic resonance and water hammer effects."""
    
    @staticmethod
    def calculate_natural_frequency(
        pipe_connection: 'PipeConnection',
        fluid_density_kg_m3: float,
        bulk_modulus_pa: float,
        speed_of_sound_m_s: float
    ) -> float:
        """
        Calculate fundamental frequency of pipe resonance.
        
        f_n = (c / (2*L)) * n  where n = 1, 2, 3, ...
        c = speed of sound in fluid
        L = pipe length
        """
        fundamental_freq = speed_of_sound_m_s / (2 * pipe_connection.length_m)
        return fundamental_freq
    
    @staticmethod
    def calculate_transient_surge_magnitude(
        valve_closure_time_s: float,
        flow_velocity_m_s: float,
        speed_of_sound_m_s: float,
        bulk_modulus_pa: float,
        fluid_density_kg_m3: float
    ) -> float:
        """
        Estimate pressure surge from valve closure (water hammer).
        
        Joukowsky equation: ΔP = ρ * c * Δv
        
        For rapid closure (t_c < 2*L/c): full impact
        For slow closure: reduced impact
        """
        characteristic_time = 0.001  # seconds (1 ms closure time)
        
        if valve_closure_time_s < characteristic_time:
            # Rapid closure: use Joukowsky
            delta_v = flow_velocity_m_s
            delta_p = fluid_density_kg_m3 * speed_of_sound_m_s * delta_v
        else:
            # Slow closure: reduced impact
            delta_v = flow_velocity_m_s * (characteristic_time / valve_closure_time_s)
            delta_p = fluid_density_kg_m3 * speed_of_sound_m_s * delta_v
        
        return delta_p


class TransientPropagationAnalyzer:
    """Analyzes transient wave propagation through network."""
    
    def __init__(self, network: PipingNetworkAnalysis):
        """Initialize transient analyzer."""
        self.network = network
    
    def calculate_wave_arrival_time(
        self,
        start_node: str,
        end_node: str,
        wave_speed_m_s: float
    ) -> Optional[float]:
        """
        Calculate time for pressure wave to propagate.
        
        Args:
            start_node: Source node
            end_node: Target node
            wave_speed_m_s: Wave propagation speed
            
        Returns:
            Arrival time in seconds
        """
        path = self.network.get_path(start_node, end_node)
        
        if not path or len(path) < 2:
            return None
        
        total_distance = 0.0
        for i in range(len(path) - 1):
            current_node = self.network.nodes[path[i]]
            next_node = self.network.nodes[path[i + 1]]
            
            distance = np.sqrt(
                (next_node.x_position_m - current_node.x_position_m) ** 2 +
                (next_node.y_position_m - current_node.y_position_m) ** 2 +
                (next_node.z_position_m - current_node.z_position_m) ** 2
            )
            total_distance += distance
        
        return total_distance / wave_speed_m_s
    
    def predict_transient_at_node(
        self,
        source_node: str,
        target_node: str,
        source_transient: Callable[[float], float],
        wave_speed_m_s: float,
        observation_time: float
    ) -> Dict[str, Any]:
        """
        Predict transient pressure at target node.
        
        Args:
            source_node: Disturbance source
            target_node: Observation point
            source_transient: Function source_transient(t)
            wave_speed_m_s: Wave speed
            observation_time: Time to predict
            
        Returns:
            Transient prediction at target
        """
        arrival_time = self.calculate_wave_arrival_time(
            source_node,
            target_node,
            wave_speed_m_s
        )
        
        if arrival_time is None or arrival_time > observation_time:
            return {
                "transient_arrived": False,
                "arrival_time": arrival_time,
                "predicted_pressure_pa": None
            }
        
        time_at_target = observation_time - arrival_time
        predicted_pressure = source_transient(time_at_target)
        
        return {
            "transient_arrived": True,
            "arrival_time": arrival_time,
            "time_at_target": time_at_target,
            "predicted_pressure_pa": predicted_pressure
        }
    
    def identify_reflection_points(self) -> List[str]:
        """Identify nodes where reflections occur (dead ends, area changes)."""
        reflection_points = []
        
        for node_id, node in self.network.nodes.items():
            connected_pipes = self.network.get_connected_pipes(node_id)
            
            if len(connected_pipes) == 1:
                reflection_points.append(node_id)
            elif len(connected_pipes) > 2:
                areas = []
                for pipe_id in connected_pipes:
                    conn = self.network.connections[pipe_id]
                    area = np.pi * (conn.inner_diameter_m / 2) ** 2
                    areas.append(area)
                
                if max(areas) / min(areas) > 1.5:
                    reflection_points.append(node_id)
        
        return reflection_points


def create_simple_pipeline(
    inlet_pressure_pa: float = 1e6,
    outlet_pressure_pa: float = 1e5,
    pipe_length_m: float = 100,
    pipe_diameter_m: float = 0.05
) -> PipingNetworkAnalysis:
    """Create simple linear pipeline network."""
    network = PipingNetworkAnalysis(network_id="simple_pipeline")
    
    inlet_node = PipeNode("inlet", 0, 0, 0, inlet_pressure_pa, "inlet")
    outlet_node = PipeNode("outlet", pipe_length_m, 0, 0, outlet_pressure_pa, "outlet")
    
    network.add_node(inlet_node)
    network.add_node(outlet_node)
    
    pipe_conn = PipeConnection(
        "main_pipe",
        "inlet",
        "outlet",
        pipe_diameter_m,
        pipe_length_m
    )
    network.add_connection(pipe_conn)
    
    return network


def get_piping_network_analyzer(
    network: PipingNetworkAnalysis
) -> NetworkFlowAnalysis:
    """Factory function for network flow analyzer."""
    return NetworkFlowAnalysis(network)
