"""
Valve Calculation Engine
Specialized calculations for industrial valves across all subtypes

Supports:
- Gate Valves (API 600)
- Ball Valves (API 602)
- Check Valves (API 608)
- Relief Valves (API 6D)
- Control Valves (API 6D)

Key calculations:
- Pressure drop and flow capacity (Cv coefficient)
- Seat erosion and wear rates
- Cavitation detection
- Hysteresis and instability analysis
- Noise prediction

Author: Jhon Villegas
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ValvePerformance:
    """Valve performance metrics."""
    pressure_drop_psi: float
    flow_capacity_gpm: float
    velocity_ft_s: float
    erosion_rate_mm_year: Optional[float]
    cavitation_index: float
    is_cavitating: bool
    noise_level_db: Optional[float]
    seat_wear_status: str
    valve_authority: float


@dataclass
class ValveCondition:
    """Valve condition assessment."""
    overall_health: str  # "Good", "Acceptable", "Degraded", "Critical"
    pressure_drop_trend: str  # "Stable", "Increasing", "Decreasing"
    seat_condition: str  # "Tight", "Slight Leakage", "Leaking", "Failed"
    actuator_status: str  # "Responsive", "Sluggish", "Stuck", "Failed"
    remaining_life_hours: Optional[float]
    recommended_action: str


# ============================================================================
# GATE VALVE CALCULATIONS (API 600)
# ============================================================================

class GateValveCalculator:
    """
    Gate valve calculations per API 600 standards.
    
    Gate valves are bidirectional with full port capacity.
    Used for on-off service with minimal pressure drop in full open position.
    """
    
    @staticmethod
    def calculate_pressure_drop(
        flow_gpm: float,
        inlet_pressure_psi: float,
        outlet_pressure_psi: float,
        valve_opening_percent: float,
        cv_rating: float
    ) -> Dict[str, float]:
        """
        Calculate pressure drop across gate valve.
        
        Cv (flow coefficient) method:
        Q = Cv * sqrt(delta_P / SG)
        delta_P = (Q / Cv)^2 * SG
        
        Args:
            flow_gpm: Flow rate in GPM
            inlet_pressure_psi: Inlet pressure
            outlet_pressure_psi: Outlet pressure
            valve_opening_percent: Valve opening (0-100%)
            cv_rating: Cv rating at full open
        
        Returns:
            Dictionary with pressure drop and flow metrics
        """
        # Adjust Cv for opening percentage (nonlinear)
        opening_ratio = valve_opening_percent / 100.0
        cv_effective = cv_rating * (opening_ratio ** 1.8)
        
        # Calculate pressure drop
        delta_p_calc = (flow_gpm / cv_effective) ** 2
        delta_p_actual = inlet_pressure_psi - outlet_pressure_psi
        
        # Valve authority (delta_p_valve / total_delta_p)
        total_delta_p = inlet_pressure_psi if outlet_pressure_psi < 0.5 else inlet_pressure_psi - outlet_pressure_psi
        valve_authority = delta_p_actual / total_delta_p if total_delta_p > 0 else 0
        
        return {
            'pressure_drop_calculated_psi': delta_p_calc,
            'pressure_drop_actual_psi': delta_p_actual,
            'cv_effective': cv_effective,
            'valve_authority': min(1.0, valve_authority)
        }
    
    @staticmethod
    def detect_cavitation(
        inlet_pressure_psi: float,
        outlet_pressure_psi: float,
        fluid_vapor_pressure_psi: float,
        valve_opening_percent: float
    ) -> Tuple[bool, float, str]:
        """
        Detect cavitation conditions in gate valve.
        
        Cavitation index (sigma):
        σ = (P_inlet - P_vapor) / (P_inlet - P_outlet)
        
        - σ < σ_inc: Inception cavitation begins
        - σ < σ_choke: Choke cavitation (sonic velocity)
        
        Args:
            inlet_pressure_psi: Inlet pressure
            outlet_pressure_psi: Outlet pressure
            fluid_vapor_pressure_psi: Fluid vapor pressure
            valve_opening_percent: Valve opening percentage
        
        Returns:
            Tuple of (is_cavitating, cavitation_index, severity_level)
        """
        numerator = inlet_pressure_psi - fluid_vapor_pressure_psi
        denominator = inlet_pressure_psi - outlet_pressure_psi
        
        if denominator <= 0 or numerator <= 0:
            return False, 1.0, "No cavitation risk"
        
        sigma = numerator / denominator
        
        # Inception and choke thresholds vary with opening
        opening_ratio = valve_opening_percent / 100.0
        sigma_inc = 1.5 + 0.5 * (1.0 - opening_ratio)  # Higher at reduced openings
        sigma_choke = 0.5
        
        if sigma < sigma_choke:
            is_cavitating = True
            severity = "Severe (sonic flow)"
        elif sigma < sigma_inc:
            is_cavitating = True
            severity = "Moderate (incipient cavitation)"
        else:
            is_cavitating = False
            severity = "None"
        
        return is_cavitating, sigma, severity


# ============================================================================
# BALL VALVE CALCULATIONS (API 602)
# ============================================================================

class BallValveCalculator:
    """Ball valve calculations per API 602."""
    
    @staticmethod
    def calculate_cv_reduction_factor(
        ball_diameter_inch: float,
        nominal_size_inch: float,
        port_type: str = "full"
    ) -> float:
        """
        Calculate Cv reduction factor for ball valve geometry.
        
        Full port: ~97% of nominal Cv
        Reduced port: ~50-70% of nominal Cv
        V-port: Linear Cv variation with opening
        """
        size_ratio = ball_diameter_inch / nominal_size_inch
        
        if port_type.lower() == "full":
            return 0.97
        elif port_type.lower() == "reduced":
            return 0.60 + 0.1 * size_ratio
        elif port_type.lower() == "v_port":
            return 0.50 + 0.3 * size_ratio
        else:
            return 0.80
    
    @staticmethod
    def estimate_seat_wear(
        operating_hours: float,
        pressure_differential_psi: float,
        flow_rate_gpm: float,
        fluid_contains_sand: bool = False
    ) -> Dict[str, Any]:
        """
        Estimate ball valve seat wear over operating time.
        
        Wear rate depends on:
        - Pressure differential (erosive force)
        - Flow rate (erosive velocity)
        - Fluid contamination (sand, scale)
        - Ball/seat material hardness
        """
        # Base wear rate (PTFE seats)
        base_wear_mm_year = 0.1
        
        # Pressure factor
        pressure_factor = (pressure_differential_psi / 100.0) ** 0.8
        
        # Velocity factor
        velocity_factor = (flow_rate_gpm / 100.0) ** 1.2
        
        # Contamination factor
        contamination_factor = 5.0 if fluid_contains_sand else 1.0
        
        # Total wear rate
        wear_rate_mm_year = base_wear_mm_year * pressure_factor * velocity_factor * contamination_factor
        
        # Estimate remaining seat life (assuming seat thickness ~5mm before replacement)
        seat_thickness_mm = 5.0
        remaining_life_years = seat_thickness_mm / wear_rate_mm_year if wear_rate_mm_year > 0 else float('inf')
        remaining_life_hours = remaining_life_years * 8760
        
        # Condition assessment
        if remaining_life_years > 5:
            condition = "Good"
        elif remaining_life_years > 1:
            condition = "Acceptable"
        elif remaining_life_years > 0.25:
            condition = "Degraded"
        else:
            condition = "Critical - Schedule maintenance"
        
        return {
            'wear_rate_mm_year': wear_rate_mm_year,
            'remaining_seat_life_years': remaining_life_years,
            'remaining_seat_life_hours': remaining_life_hours,
            'seat_condition': condition
        }


# ============================================================================
# RELIEF VALVE CALCULATIONS (API 6D)
# ============================================================================

class ReliefValveCalculator:
    """Relief valve calculations for pressure protection."""
    
    @staticmethod
    def calculate_relief_capacity(
        relief_setting_psi: float,
        seat_area_in2: float,
        pilot_ratio: Optional[float] = None,
        is_pilot_operated: bool = False
    ) -> Dict[str, float]:
        """
        Calculate relief valve flow capacity at relief setting.
        
        Direct-acting valve:
        Q = C * A * sqrt(2 * g * (P_set - P_downstream) / SG)
        
        Pilot-operated valve:
        Q = C * A_pilot * sqrt(2 * g * (P_set - P_pilot_drain) / SG)
        """
        # Discharge coefficient (typical 0.6-0.85)
        discharge_coeff = 0.75
        
        # Gravitational constant
        g = 32.174  # ft/s^2
        
        # Specific gravity of oil (typical)
        sg = 0.85
        
        if not is_pilot_operated:
            # Direct-acting
            pilot_pressure_drop = 3.0  # Typical 3 psi across pilot
            pressure_factor = relief_setting_psi - pilot_pressure_drop
        else:
            # Pilot-operated (if pilot ratio provided)
            if pilot_ratio is None:
                pilot_ratio = 4.0
            pressure_factor = (relief_setting_psi - 3.0) * pilot_ratio
        
        # Flow capacity (GPM)
        velocity = np.sqrt(2 * g * pressure_factor / sg)
        area_ft2 = seat_area_in2 / 144.0
        flow_ft3_s = discharge_coeff * area_ft2 * velocity
        flow_gpm = flow_ft3_s * 60 / 0.13368
        
        return {
            'relief_capacity_gpm': flow_gpm,
            'relief_capacity_scfm': flow_gpm * 0.12,  # Rough conversion
            'velocity_ft_s': velocity,
            'pressure_factor': pressure_factor
        }
    
    @staticmethod
    def check_pilot_stability(
        pilot_pressure_psi: float,
        main_valve_pressure_psi: float,
        pilot_ratio: float = 4.0,
        hysteresis_margin_psi: float = 0.5
    ) -> Dict[str, Any]:
        """
        Check for pilot-operated relief valve instability (chatter).
        
        Instability occurs when:
        - Pilot feedback not adequate
        - Pressure overshoots relief setting
        - Hysteresis too small
        """
        # Calculate opening/closing pressures
        cracking_pressure = main_valve_pressure_psi * pilot_ratio
        closing_pressure = cracking_pressure - hysteresis_margin_psi
        
        # Margin between cracking and closing
        pressure_margin = cracking_pressure - closing_pressure
        min_margin_psi = 1.0
        
        is_stable = pressure_margin >= min_margin_psi
        
        # Calculate instability risk
        if pressure_margin < 0.3:
            stability_risk = "Critical - Chatter likely"
        elif pressure_margin < 1.0:
            stability_risk = "High - Monitor closely"
        elif pressure_margin < 2.0:
            stability_risk = "Moderate - Acceptable with attention"
        else:
            stability_risk = "Low - Stable operation"
        
        return {
            'cracking_pressure_psi': cracking_pressure,
            'closing_pressure_psi': closing_pressure,
            'pressure_margin_psi': pressure_margin,
            'is_stable': is_stable,
            'stability_risk': stability_risk
        }


# ============================================================================
# CHECK VALVE CALCULATIONS (API 608)
# ============================================================================

class CheckValveCalculator:
    """Check valve calculations."""
    
    @staticmethod
    def calculate_cracking_pressure(
        cracking_setting_psi: float,
        flow_rate_gpm: float,
        valve_capacity_cv: float
    ) -> Dict[str, float]:
        """
        Calculate actual pressure required to crack open a check valve.
        
        Flow-dependent cracking pressure:
        P_crack_actual = P_setting + (Flow / Cv)^2
        """
        flow_induced_pressure = (flow_rate_gpm / valve_capacity_cv) ** 2
        actual_cracking = cracking_setting_psi + flow_induced_pressure
        
        return {
            'cracking_setting_psi': cracking_setting_psi,
            'flow_induced_pressure_psi': flow_induced_pressure,
            'actual_cracking_pressure_psi': actual_cracking
        }
    
    @staticmethod
    def assess_leakage_risk(
        upstream_pressure_psi: float,
        downstream_pressure_psi: float,
        cracking_pressure_psi: float,
        seat_leakage_rate_sccm: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Assess backflow leakage risk in check valve.
        """
        # Calculate pressure ratio
        pressure_ratio = downstream_pressure_psi / upstream_pressure_psi if upstream_pressure_psi > 0 else 0
        
        # Determine leakage severity
        if pressure_ratio < 0.95:
            leakage_risk = "None - Good backpressure"
            leakage_status = "Tight"
        elif pressure_ratio < 0.99:
            leakage_risk = "Low - Acceptable leakage"
            leakage_status = "Slight leakage"
        else:
            leakage_risk = "High - Significant leakage"
            leakage_status = "Leaking"
        
        return {
            'pressure_ratio': pressure_ratio,
            'backpressure_psi': upstream_pressure_psi - downstream_pressure_psi,
            'leakage_risk': leakage_risk,
            'leakage_status': leakage_status,
            'estimated_leakage_sccm': seat_leakage_rate_sccm
        }


# ============================================================================
# CONTROL VALVE CALCULATIONS
# ============================================================================

class ControlValveCalculator:
    """Control valve calculations for process flow control."""
    
    @staticmethod
    def calculate_valve_rangeability(
        cv_max: float,
        cv_min: float
    ) -> float:
        """
        Calculate valve rangeability (max/min controllable flow).
        
        Typical: 50:1 for equal percentage, 10:1 for linear
        """
        if cv_min <= 0:
            return float('inf')
        return cv_max / cv_min
    
    @staticmethod
    def assess_valve_authority(
        valve_pressure_drop_psi: float,
        system_pressure_drop_psi: float
    ) -> Dict[str, Any]:
        """
        Assess valve authority (control effectiveness).
        
        Valve authority = valve delta_P / total system delta_P
        
        Recommended:
        - > 0.5: Good control
        - 0.3-0.5: Acceptable
        - < 0.3: Poor control, oversizing likely
        """
        authority = valve_pressure_drop_psi / system_pressure_drop_psi if system_pressure_drop_psi > 0 else 0
        
        if authority > 0.5:
            authority_status = "Good - Effective control"
        elif authority > 0.3:
            authority_status = "Acceptable - Moderate control"
        else:
            authority_status = "Poor - Consider valve resizing"
        
        return {
            'valve_authority': authority,
            'authority_status': authority_status,
            'recommendation': authority_status
        }


# ============================================================================
# GENERAL VALVE ASSESSMENT
# ============================================================================

def assess_valve_condition(
    valve_type: str,
    operating_hours: float,
    pressure_differential_psi: float,
    flow_rate_gpm: float,
    inlet_pressure_psi: float,
    outlet_pressure_psi: float,
    fluid_vapor_pressure_psi: float,
    last_maintenance_hours: Optional[float] = None
) -> ValveCondition:
    """
    Comprehensive valve condition assessment.
    
    Args:
        valve_type: Type of valve (gate, ball, check, relief, control)
        operating_hours: Total operating hours
        pressure_differential_psi: Pressure drop across valve
        flow_rate_gpm: Flow rate
        inlet_pressure_psi: Inlet pressure
        outlet_pressure_psi: Outlet pressure
        fluid_vapor_pressure_psi: Vapor pressure of fluid
        last_maintenance_hours: Hours since last maintenance
    
    Returns:
        ValveCondition with health assessment and recommendations
    """
    # Pressure drop trend (increase = wear)
    expected_dp = (flow_rate_gpm / 100.0) ** 2  # Simplified
    dp_ratio = pressure_differential_psi / expected_dp if expected_dp > 0 else 1.0
    
    if dp_ratio > 1.5:
        pressure_drop_trend = "Increasing (seat wear)"
        health_degradation = 2
    elif dp_ratio > 1.2:
        pressure_drop_trend = "Slightly increasing"
        health_degradation = 1
    else:
        pressure_drop_trend = "Stable"
        health_degradation = 0
    
    # Cavitation check (for gate/ball valves)
    if valve_type.lower() in ["gate", "ball"]:
        is_cavitating, sigma, cav_severity = GateValveCalculator.detect_cavitation(
            inlet_pressure_psi, outlet_pressure_psi, fluid_vapor_pressure_psi, 100
        )
        if is_cavitating:
            health_degradation += 2
    else:
        cav_severity = "N/A"
    
    # Age-based maintenance
    if last_maintenance_hours and (operating_hours - last_maintenance_hours) > 8760:
        remaining_life_hours = 8760 * 2 - (operating_hours - last_maintenance_hours)
        maintenance_urgency = "Soon" if remaining_life_hours < 2000 else "Not urgent"
    else:
        remaining_life_hours = None
        maintenance_urgency = "Unknown"
    
    # Overall health assessment
    if health_degradation >= 4:
        overall_health = "Critical"
        recommended_action = "Schedule immediate maintenance"
    elif health_degradation >= 2:
        overall_health = "Degraded"
        recommended_action = "Schedule maintenance within 1 month"
    elif health_degradation >= 1:
        overall_health = "Acceptable"
        recommended_action = "Monitor and schedule routine maintenance"
    else:
        overall_health = "Good"
        recommended_action = "Continue normal operation"
    
    return ValveCondition(
        overall_health=overall_health,
        pressure_drop_trend=pressure_drop_trend,
        seat_condition="Tight" if dp_ratio < 1.2 else "Slight leakage" if dp_ratio < 1.5 else "Leaking",
        actuator_status="Responsive",  # Would need additional data
        remaining_life_hours=remaining_life_hours,
        recommended_action=recommended_action
    )
