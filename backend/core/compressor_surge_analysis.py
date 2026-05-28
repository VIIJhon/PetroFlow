"""
Compressor Surge Analysis Module
Implements surge detection and stability analysis for turbocompressors.
Includes surge line calculation, anti-surge control, and transient response.

Physics:
- Surge line determination using compressor map
- Rotating stall detection
- Pressure oscillation analysis
- Surge recycle valve modeling
- Surge margin calculation

Phase: Phase 2 - Dynamic Simulation
"""

from typing import Tuple, Dict, Optional, Callable
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompressorMapPoint:
    """Single point on compressor performance map."""
    flow_ratio: float
    pressure_ratio: float
    efficiency: float
    stability_margin: float


@dataclass
class CompressorParameters:
    """Physical parameters for compressor surge analysis."""
    rotor_inertia_kg_m2: float
    rated_speed_rpm: float
    rated_flow_kg_s: float
    rated_pressure_ratio: float
    inlet_volume_m3: float
    discharge_volume_m3: float
    surge_line_slope: float
    stage_count: int
    blade_count: int
    polytropic_efficiency: float
    anti_surge_valve_response_time: float


class CompressorSurgeAnalyzer:
    """
    Analyzes compressor stability and surge phenomena.
    """
    
    def __init__(self, params: CompressorParameters):
        """
        Initialize surge analyzer.
        
        Args:
            params: CompressorParameters instance
        """
        self.params = params
        self.nominal_speed = params.rated_speed_rpm * np.pi / 30
        self.nominal_flow = params.rated_flow_kg_s
        self.nominal_pressure_ratio = params.rated_pressure_ratio
        
        self.compressor_map = self._generate_compressor_map()
        self.surge_line = self._generate_surge_line()
    
    def _generate_compressor_map(self) -> Dict[float, Tuple[float, float]]:
        """
        Generate compressor performance map.
        Returns dict of {flow_ratio: (pressure_ratio, efficiency)}
        """
        compressor_map = {}
        
        for flow_ratio in np.linspace(0.3, 1.3, 50):
            pressure_ratio = (
                self.nominal_pressure_ratio *
                (1.0 - 0.4 * (flow_ratio - 1.0) ** 2)
            )
            pressure_ratio = max(1.0, pressure_ratio)
            
            efficiency = (
                0.85 *
                (1.0 - 0.25 * (flow_ratio - 1.0) ** 2) *
                (1.0 - 0.1 * (pressure_ratio - self.nominal_pressure_ratio) ** 2)
            )
            efficiency = np.clip(efficiency, 0.4, 0.95)
            
            compressor_map[flow_ratio] = (pressure_ratio, efficiency)
        
        return compressor_map
    
    def _generate_surge_line(self) -> Dict[float, float]:
        """
        Generate surge line (minimum stable flow at each speed).
        Improved model based on compressor characteristic curves.
        Reference: Greitzer (1976) - "Surge and Rotating Stall in Axial Flow Compressors"
        """
        surge_line = {}
        
        # Configurable surge line parameters
        surge_flow_coefficient = getattr(self, 'surge_flow_coefficient', 0.65)
        surge_line_curvature = getattr(self, 'surge_line_curvature', 0.1)
        
        for speed_ratio in np.linspace(0.5, 1.5, 30):
            # Improved surge line model: parabolic relationship with speed
            # At low speeds, surge line moves to lower flows
            min_flow_ratio = surge_flow_coefficient * speed_ratio * (
                1.0 - surge_line_curvature * (1.0 - speed_ratio) ** 2
            )
            surge_line[speed_ratio] = max(min_flow_ratio, 0.1)  # Minimum physical limit
        
        return surge_line
    
    def is_in_surge_region(
        self,
        flow_ratio: float,
        speed_ratio: float
    ) -> bool:
        """
        Check if operating point is in surge region.
        
        Args:
            flow_ratio: Mass flow ratio (actual / nominal)
            speed_ratio: Speed ratio (actual / nominal)
            
        Returns:
            True if in surge region (unstable)
        """
        if speed_ratio <= 0:
            return False
        
        min_flow_ratio = self.surge_line.get(
            speed_ratio,
            0.65 * speed_ratio
        )
        
        return flow_ratio < min_flow_ratio * 1.05
    
    def calculate_surge_margin(
        self,
        flow_ratio: float,
        speed_ratio: float
    ) -> float:
        """
        Calculate surge margin (percentage above surge line).
        
        Args:
            flow_ratio: Mass flow ratio
            speed_ratio: Speed ratio
            
        Returns:
            Surge margin as percentage (>0 = safe, <0 = in surge)
        """
        if speed_ratio <= 0:
            return 0
        
        min_flow_ratio = self.surge_line.get(
            speed_ratio,
            0.65 * speed_ratio
        )
        
        margin = (flow_ratio - min_flow_ratio) / min_flow_ratio * 100
        return margin
    
    def calculate_operating_point(
        self,
        flow_ratio: float,
        speed_ratio: float
    ) -> Dict[str, float]:
        """
        Calculate compressor operating point.
        
        Args:
            flow_ratio: Mass flow ratio
            speed_ratio: Speed ratio
            
        Returns:
            Dictionary with pressure ratio, efficiency, etc.
        """
        closest_flow_ratio = min(
            self.compressor_map.keys(),
            key=lambda x: abs(x - flow_ratio)
        )
        
        pressure_ratio_base, efficiency_base = self.compressor_map[closest_flow_ratio]
        
        pressure_ratio = pressure_ratio_base * (speed_ratio ** 2)
        
        efficiency = efficiency_base * (1.0 - 0.05 * abs(speed_ratio - 1.0))
        efficiency = np.clip(efficiency, 0.4, 0.95)
        
        surge_margin = self.calculate_surge_margin(flow_ratio, speed_ratio)
        in_surge = self.is_in_surge_region(flow_ratio, speed_ratio)
        
        return {
            "pressure_ratio": float(pressure_ratio),
            "efficiency": float(efficiency),
            "surge_margin": float(surge_margin),
            "in_surge": bool(in_surge),
            "flow_ratio": float(flow_ratio),
            "speed_ratio": float(speed_ratio)
        }
    
    def detect_rotating_stall(
        self,
        pressure_oscillations: np.ndarray,
        time_array: np.ndarray,
        stall_threshold: float = 0.05
    ) -> Dict[str, any]:
        """
        Detect rotating stall precursors.
        Rotating stall appears as pressure perturbations at fraction of blade passing frequency.
        
        Args:
            pressure_oscillations: Pressure time series
            time_array: Time array
            stall_threshold: Pressure oscillation threshold
            
        Returns:
            Dictionary with stall detection results
        """
        if len(pressure_oscillations) < 10:
            return {"stall_detected": False, "confidence": 0.0}
        
        mean_pressure = np.mean(pressure_oscillations)
        if mean_pressure < 1e-6:
            return {"stall_detected": False, "confidence": 0.0}
        
        oscillation_magnitude = np.std(pressure_oscillations) / mean_pressure
        
        dt = time_array[1] - time_array[0]
        sampling_freq = 1.0 / dt
        
        fft_vals = np.fft.fft(pressure_oscillations)
        freqs = np.fft.fftfreq(len(fft_vals), dt)
        power = np.abs(fft_vals) ** 2
        
        blade_passing_freq = (self.params.blade_count / 60.0 *
                             self.params.rated_speed_rpm)
        stall_freq_range = (blade_passing_freq / 4, blade_passing_freq / 2)
        
        stall_power = 0
        for f, p in zip(freqs, power):
            if stall_freq_range[0] <= abs(f) <= stall_freq_range[1]:
                stall_power += p
        
        total_power = np.sum(power)
        stall_energy_ratio = stall_power / (total_power + 1e-10)
        
        stall_detected = (
            oscillation_magnitude > stall_threshold and
            stall_energy_ratio > 0.1
        )
        
        confidence = min(1.0, stall_energy_ratio * 2)
        
        return {
            "stall_detected": bool(stall_detected),
            "confidence": float(confidence),
            "oscillation_magnitude": float(oscillation_magnitude),
            "stall_energy_ratio": float(stall_energy_ratio),
            "stall_frequency_hz": float((stall_freq_range[0] + stall_freq_range[1]) / 2)
        }
    
    def system_equations(
        self,
        t: float,
        state: np.ndarray,
        inlet_flow: Callable[[float], float],
        inlet_pressure: Callable[[float], float],
        outlet_pressure: Callable[[float], float]
    ) -> np.ndarray:
        """
        Compressor system of differential equations.
        
        State:
        - x[0]: Rotor speed (rad/s)
        - x[1]: Outlet pressure (Pa)
        - x[2]: Mass accumulation in discharge volume (kg)
        
        Args:
            t: Current time
            state: State vector
            inlet_flow: Function returning inlet mass flow (kg/s)
            inlet_pressure: Function returning inlet pressure (Pa)
            outlet_pressure: Function returning outlet pressure setpoint (Pa)
            
        Returns:
            State derivatives
        """
        speed, P_outlet, mass_discharge = state
        
        speed = np.clip(speed, 0, self.nominal_speed * 1.5)
        P_outlet = np.clip(P_outlet, 1e5, 1e7)
        
        speed_ratio = speed / self.nominal_speed
        flow_in = inlet_flow(t)
        flow_ratio = flow_in / self.nominal_flow
        
        op_point = self.calculate_operating_point(flow_ratio, speed_ratio)
        pressure_ratio = op_point["pressure_ratio"]
        efficiency = op_point["efficiency"]
        
        P_inlet = inlet_pressure(t)
        P_outlet_demanded = outlet_pressure(t)
        
        if P_inlet < 1:
            P_inlet = 1
        
        actual_pressure_ratio = P_outlet / (P_inlet + 1e-6)
        
        # Calculate flow loss due to surge/stall conditions
        # Use proper aerodynamic loss model instead of arbitrary 0.3
        pressure_ratio_error = actual_pressure_ratio / (pressure_ratio + 1e-6)
        
        if pressure_ratio_error > 1.2:
            # In surge/stall region: losses increase with square of deviation
            loss_coefficient = getattr(self, 'surge_loss_coefficient', 0.3)
            flow_loss = flow_in * loss_coefficient * (pressure_ratio_error - 1.0) ** 2
        else:
            flow_loss = 0
        
        flow_out_theoretical = max(flow_in - flow_loss, 0)
        
        power_input = 200.0
        power_available = power_input * speed / (self.nominal_speed + 1e-6)
        
        # Complete polytropic efficiency calculation
        # Power = m_dot * cp * T_in * [(P_out/P_in)^((gamma-1)/(gamma*eta_poly)) - 1]
        # Reference: Dixon & Hall, "Fluid Mechanics and Thermodynamics of Turbomachinery"
        
        gas_constant_j_kg_k = 287  # Air
        inlet_temperature_k = 288  # Standard conditions
        gamma = 1.4  # Air
        
        # Polytropic efficiency from parameters or default
        eta_poly = self.params.polytropic_efficiency if hasattr(self.params, 'polytropic_efficiency') else efficiency
        
        if eta_poly > 0 and pressure_ratio > 1.0:
            polytropic_exponent = (gamma - 1) / (gamma * eta_poly)
            temperature_ratio = pressure_ratio ** polytropic_exponent
            
            # Specific heat at constant pressure for air
            cp_j_kg_k = gamma * gas_constant_j_kg_k / (gamma - 1)
            
            power_required = (
                flow_in * cp_j_kg_k * inlet_temperature_k * (temperature_ratio - 1)
            ) / 1e6  # Convert to MW
        else:
            power_required = 0
        
        d_speed_dt = (power_available - power_required - 10 * speed) / self.params.rotor_inertia_kg_m2
        
        dP_outlet_dt = (
            (pressure_ratio * P_inlet - P_outlet) / 0.5 +
            (P_outlet_demanded - P_outlet) / 0.1
        )
        
        d_mass_dt = flow_out_theoretical - flow_in
        
        return np.array([d_speed_dt, dP_outlet_dt, d_mass_dt])


class AntiSurgeControl:
    """Anti-surge control valve management."""
    
    def __init__(
        self,
        compressor_analyzer: CompressorSurgeAnalyzer,
        surge_margin_setpoint: float = 15.0
    ):
        """
        Initialize anti-surge controller.
        
        Args:
            compressor_analyzer: CompressorSurgeAnalyzer instance
            surge_margin_setpoint: Target surge margin (percentage)
        """
        self.analyzer = compressor_analyzer
        self.setpoint = surge_margin_setpoint
        self.valve_position = 0.0
        
    def calculate_valve_position(
        self,
        flow_ratio: float,
        speed_ratio: float,
        time_derivative_flow: float = 0.0
    ) -> float:
        """
        Calculate anti-surge recycle valve position.
        
        Args:
            flow_ratio: Mass flow ratio
            speed_ratio: Speed ratio
            time_derivative_flow: d(flow)/dt for predictive control
            
        Returns:
            Valve position (0=closed, 1=full open)
        """
        surge_margin = self.analyzer.calculate_surge_margin(flow_ratio, speed_ratio)
        
        margin_error = self.setpoint - surge_margin
        
        kp = 0.02
        kd = 0.01
        
        valve_position = (
            kp * margin_error +
            kd * time_derivative_flow * 0.1
        )
        
        valve_position = np.clip(valve_position, 0.0, 1.0)
        
        return float(valve_position)


def get_compressor_surge_analyzer(
    params: CompressorParameters
) -> CompressorSurgeAnalyzer:
    """Factory function for compressor surge analyzer."""
    return CompressorSurgeAnalyzer(params)
