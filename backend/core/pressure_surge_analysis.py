"""
Pressure Surge and Cavitation Analysis Module
Analyzes transient overpressure events and cavitation conditions
at the system level, including surge detection, reflection analysis,
and system response to disturbances.

Phase: Phase 3 - Piping Network Analysis
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PressureSurgeEvent:
    """Characterizes a pressure surge event."""
    event_id: str
    onset_time_s: float
    peak_pressure_pa: float
    peak_time_s: float
    duration_s: float
    cause: str
    magnitude_bar: float = 0.0
    
    @property
    def rise_rate_pa_s(self) -> float:
        """Pressure rise rate."""
        if self.peak_time_s <= self.onset_time_s:
            return 0.0
        return self.peak_pressure_pa / (self.peak_time_s - self.onset_time_s)


@dataclass
class CavitationRegion:
    """Characterizes a cavitation region."""
    region_id: str
    location: str
    onset_time_s: float
    duration_s: float
    min_pressure_pa: float
    vapor_pressure_pa: float = 2340
    
    @property
    def npsh_margin_pa(self) -> float:
        """NPSH margin."""
        return self.min_pressure_pa - self.vapor_pressure_pa


class PressureSurgeAnalyzer:
    """Analyzes pressure surge phenomena in systems."""
    
    @staticmethod
    def detect_pressure_surge(
        pressure_time_series: np.ndarray,
        time_array: np.ndarray,
        baseline_pressure_pa: float,
        surge_threshold_pa: float = 5e5,
        event_gap_threshold: int = 10
    ) -> List[PressureSurgeEvent]:
        """
        Detect pressure surge events in time series.
        
        Args:
            pressure_time_series: Pressure vs time
            time_array: Time array
            baseline_pressure_pa: Steady-state baseline
            surge_threshold_pa: Minimum surge magnitude
            event_gap_threshold: Gap between indices to separate events (configurable)
            
        Returns:
            List of detected surges
        """
        surges = []
        
        pressure_above_baseline = pressure_time_series - baseline_pressure_pa
        
        threshold_cross = np.where(pressure_above_baseline > surge_threshold_pa)[0]
        
        if len(threshold_cross) == 0:
            return surges
        
        event_idx = 0
        i = 0
        
        while i < len(threshold_cross):
            start_idx = threshold_cross[i]
            start_time = time_array[start_idx]
            
            j = i
            while j < len(threshold_cross) - 1:
                if threshold_cross[j + 1] - threshold_cross[j] > event_gap_threshold:
                    break
                j += 1
            
            event_indices = threshold_cross[i:j+1]
            end_idx = event_indices[-1]
            end_time = time_array[end_idx]
            
            peak_idx = event_indices[
                np.argmax(pressure_time_series[event_indices])
            ]
            peak_pressure = pressure_time_series[peak_idx]
            peak_time = time_array[peak_idx]
            
            magnitude_bar = (peak_pressure - baseline_pressure_pa) / 1e5
            
            surge = PressureSurgeEvent(
                event_id=f"surge_{event_idx}",
                onset_time_s=start_time,
                peak_pressure_pa=peak_pressure,
                peak_time_s=peak_time,
                duration_s=end_time - start_time,
                cause="transient_detected",
                magnitude_bar=magnitude_bar
            )
            
            surges.append(surge)
            event_idx += 1
            i = j + 1
        
        return surges
    
    @staticmethod
    def estimate_waterhammer_pressure(
        pipe_diameter_m: float,
        pipe_length_m: float,
        pipe_thickness_m: float,
        flow_velocity_m_s: float,
        fluid_bulk_modulus_pa: float,
        pipe_material_modulus_pa: float,
        density_kg_m3: float
    ) -> float:
        """
        Estimate waterhammer pressure surge using Joukowsky equation.
        
        Delta_P = rho * c * Delta_v
        
        where c = wave speed depends on pipe elasticity
        
        Args:
            pipe_diameter_m: Internal pipe diameter
            pipe_thickness_m: Pipe wall thickness
            flow_velocity_m_s: Initial flow velocity
            fluid_bulk_modulus_pa: Fluid bulk modulus
            pipe_material_modulus_pa: Pipe Young's modulus
            density_kg_m3: Fluid density
            
        Returns:
            Waterhammer pressure (Pa)
        """
        d_i = pipe_diameter_m
        d_o = pipe_diameter_m + 2 * pipe_thickness_m
        
        # Korteweg-Joukowsky equation with pipe elasticity correction
        # Wave speed formula: a = sqrt(K/rho) / sqrt(1 + (K/E)*(D/t)*C)
        # where C is a constraint factor (C=1 for thin-walled pipes)
        # Reference: Wylie & Streeter, "Fluid Transients in Systems" (1993)
        
        constraint_factor = 1.0  # For thin-walled pipes with axial restraint
        elastic_term = 1.0 + (fluid_bulk_modulus_pa / pipe_material_modulus_pa) * (d_i / pipe_thickness_m) * constraint_factor
        
        # Verify wave speed calculation (Joukowsky equation)
        wave_speed = np.sqrt(fluid_bulk_modulus_pa / (density_kg_m3 * elastic_term))
        
        velocity_change = flow_velocity_m_s
        
        # Joukowsky formula: ΔP = ρ * a * Δv
        waterhammer_pressure = density_kg_m3 * wave_speed * velocity_change
        
        return waterhammer_pressure
    
    @staticmethod
    def calculate_relief_valve_response(
        pressure_pa: float,
        setpoint_pa: float,
        opening_pressure_pa: float,
        full_flow_pressure_pa: float,
        max_flow_m3_s: float
    ) -> float:
        """
        Calculate relief valve opening and flow.
        
        Args:
            pressure_pa: Current system pressure
            setpoint_pa: Valve setpoint
            opening_pressure_pa: Pressure at which valve starts opening
            full_flow_pressure_pa: Pressure for full valve opening
            max_flow_m3_s: Maximum valve flow
            
        Returns:
            Valve flow (m³/s)
        """
        if pressure_pa < opening_pressure_pa:
            return 0.0
        
        if pressure_pa >= full_flow_pressure_pa:
            return max_flow_m3_s
        
        opening_fraction = (pressure_pa - opening_pressure_pa) / (full_flow_pressure_pa - opening_pressure_pa)
        
        valve_flow = opening_fraction * max_flow_m3_s
        
        return valve_flow
    
    @staticmethod
    def estimate_surge_frequency(
        pipe_length_m: float,
        wave_speed_m_s: float
    ) -> Tuple[float, float]:
        """
        Estimate characteristic surge frequencies.
        
        Fundamental frequency based on pipe length and wave speed:
        f = c / (2*L) for quarter-wave resonance
        
        Args:
            pipe_length_m: Total pipe length
            wave_speed_m_s: Acoustic wave speed
            
        Returns:
            (fundamental_frequency_hz, period_s)
        """
        fundamental_freq = wave_speed_m_s / (4 * pipe_length_m)
        period = 1.0 / fundamental_freq
        
        return fundamental_freq, period


class CavitationAnalyzer:
    """Analyzes cavitation conditions in systems."""
    
    @staticmethod
    def detect_cavitation_regions(
        pressure_field: np.ndarray,
        position_array: np.ndarray,
        time_array: np.ndarray,
        vapor_pressure_pa: float = 2340,
        npsh_margin_threshold_pa: float = 5000
    ) -> List[CavitationRegion]:
        """
        Detect cavitation regions in space-time.
        
        Args:
            pressure_field: Pressure field (n_positions x n_times)
            position_array: Spatial positions
            time_array: Time points
            vapor_pressure_pa: Vapor pressure threshold
            npsh_margin_threshold_pa: NPSH margin for detection
            
        Returns:
            List of cavitation regions
        """
        cavitation_regions = []
        
        for pos_idx, position in enumerate(position_array):
            pressure_at_pos = pressure_field[pos_idx, :]
            
            cavitation_mask = pressure_at_pos < (vapor_pressure_pa + npsh_margin_threshold_pa)
            
            if not np.any(cavitation_mask):
                continue
            
            cavitation_indices = np.where(cavitation_mask)[0]
            
            regions_at_position = []
            i = 0
            
            while i < len(cavitation_indices):
                start_idx = cavitation_indices[i]
                start_time = time_array[start_idx]
                
                j = i
                while j < len(cavitation_indices) - 1:
                    if cavitation_indices[j + 1] - cavitation_indices[j] > 2:
                        break
                    j += 1
                
                event_indices = cavitation_indices[i:j+1]
                end_idx = event_indices[-1]
                end_time = time_array[end_idx]
                
                min_pressure_idx = event_indices[
                    np.argmin(pressure_at_pos[event_indices])
                ]
                min_pressure = pressure_at_pos[min_pressure_idx]
                
                region = CavitationRegion(
                    region_id=f"cavitation_pos{pos_idx}_event{len(regions_at_position)}",
                    location=f"x={position:.3f}",
                    onset_time_s=start_time,
                    duration_s=end_time - start_time,
                    min_pressure_pa=min_pressure,
                    vapor_pressure_pa=vapor_pressure_pa
                )
                
                regions_at_position.append(region)
                i = j + 1
            
            cavitation_regions.extend(regions_at_position)
        
        return cavitation_regions
    
    @staticmethod
    def calculate_cavitation_number(
        local_pressure_pa: float,
        reference_pressure_pa: float,
        flow_velocity_m_s: float,
        density_kg_m3: float,
        vapor_pressure_pa: float = 2340
    ) -> float:
        """
        Calculate cavitation number at a point.
        
        Sigma = (P_local - P_vapor) / (0.5 * rho * v²)
        
        Sigma > 1: Safe
        0.5 < Sigma < 1: Risk
        Sigma < 0.5: Severe cavitation
        
        Args:
            local_pressure_pa: Local pressure
            reference_pressure_pa: Reference pressure (unused, for context)
            flow_velocity_m_s: Local flow velocity
            density_kg_m3: Fluid density
            vapor_pressure_pa: Vapor pressure
            
        Returns:
            Cavitation number (dimensionless)
        """
        dynamic_pressure = 0.5 * density_kg_m3 * flow_velocity_m_s ** 2
        
        if dynamic_pressure < 1e-6:
            return float('inf') if local_pressure_pa > vapor_pressure_pa else float('-inf')
        
        cavitation_number = (local_pressure_pa - vapor_pressure_pa) / dynamic_pressure
        
        return cavitation_number
    
    @staticmethod
    def estimate_collapse_intensity(
        cavitation_bubble_radius_m: float,
        surrounding_pressure_pa: float,
        vapor_pressure_pa: float = 2340,
        bubble_sound_speed_m_s: float = 1000
    ) -> float:
        """
        Estimate collapse intensity of cavitation bubble.
        Used to predict erosion damage.
        
        Args:
            cavitation_bubble_radius_m: Bubble radius
            surrounding_pressure_pa: Pressure when bubble collapses
            vapor_pressure_pa: Vapor pressure inside bubble
            bubble_sound_speed_m_s: Sound speed in liquid
            
        Returns:
            Collapse intensity (pressure in Pa)
        """
        pressure_ratio = surrounding_pressure_pa / vapor_pressure_pa
        
        if pressure_ratio < 1.0:
            return 0.0
        
        collapse_intensity = (
            pressure_ratio * surrounding_pressure_pa +
            0.5 * 1000 * bubble_sound_speed_m_s ** 2 * (1 / cavitation_bubble_radius_m)
        )
        
        return collapse_intensity


class SystemSurgeRecovery:
    """Models system recovery from pressure surge events."""
    
    @staticmethod
    def estimate_recovery_time(
        peak_pressure_pa: float,
        baseline_pressure_pa: float,
        wave_speed_m_s: float,
        pipe_length_m: float,
        damping_ratio: float = 0.05
    ) -> float:
        """
        Estimate time for system to recover after surge.
        
        Args:
            peak_pressure_pa: Peak transient pressure
            baseline_pressure_pa: Steady-state pressure
            wave_speed_m_s: Acoustic wave speed
            pipe_length_m: Total pipe length
            damping_ratio: Damping coefficient (0-1)
            
        Returns:
            Recovery time (s)
        """
        fundamental_period = 4 * pipe_length_m / wave_speed_m_s
        
        surge_magnitude_ratio = (peak_pressure_pa - baseline_pressure_pa) / baseline_pressure_pa
        
        number_of_cycles = -np.log(0.05 * surge_magnitude_ratio) / (2 * np.pi * damping_ratio) if damping_ratio > 0 else 10
        
        recovery_time = number_of_cycles * fundamental_period
        
        return recovery_time


def get_pressure_surge_analyzer() -> PressureSurgeAnalyzer:
    """Factory function."""
    return PressureSurgeAnalyzer()


def get_cavitation_analyzer() -> CavitationAnalyzer:
    """Factory function."""
    return CavitationAnalyzer()
