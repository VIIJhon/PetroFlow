"""
core/statistics.py
==================
PetroFlow Enterprise — Physics & Thermodynamics Engine
API Standards Compliance: API 610, API 617, API 611/612

Implements strict Object-Oriented representations of rotary equipment.
Each class defines the thermodynamic and physical failure modes specific
to its equipment type, establishing a base failure probability that
is combined with Machine Learning outputs for a hybrid diagnostic.
"""

from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class RotaryEquipment(ABC):
    """
    Abstract Base Class for all rotating equipment.
    Contains shared statistical methods like Jackknife Resampling.
    """
    
    def __init__(self, tag: str):
        self.tag = tag
        
    @staticmethod
    def jackknife_variance(failure_times: np.ndarray) -> Tuple[float, float, Tuple[float, float]]:
        """
        Perform Jackknife resampling to estimate MTBF variance and 95% Confidence Intervals.
        
        Args:
            failure_times: Array of historical time-to-failure (hours).
            
        Returns:
            (mean_mtbf, variance, (ci_lower, ci_upper))
        """
        n = len(failure_times)
        if n <= 1:
            mean_val = float(np.mean(failure_times)) if n == 1 else 0.0
            return mean_val, 0.0, (mean_val, mean_val)
            
        # Calculate the base mean
        theta_hat = np.mean(failure_times)
        
        # Calculate jackknife samples (leave one out)
        jackknife_samples = np.zeros(n)
        for i in range(n):
            jackknife_samples[i] = np.mean(np.delete(failure_times, i))
            
        # Calculate jackknife mean and variance
        theta_hat_mean = np.mean(jackknife_samples)
        variance = ((n - 1) / n) * np.sum((jackknife_samples - theta_hat_mean)**2)
        
        # 95% Confidence Interval (Z = 1.96)
        margin = 1.96 * np.sqrt(variance)
        ci_lower = max(0.0, theta_hat - margin)
        ci_upper = theta_hat + margin
        
        return float(theta_hat), float(variance), (float(ci_lower), float(ci_upper))

    @abstractmethod
    def calculate_physical_risk(self, sensors: Dict[str, float]) -> Tuple[float, str]:
        """
        Calculate failure risk based strictly on thermodynamics and physics.
        Returns: (probability_0_to_100, critical_reason_string)
        """
        pass
        
    def hybrid_predict_failure(self, ml_probability: float, sensors: Dict[str, float]) -> Tuple[float, str]:
        """
        Combines API physical modeling with ML predictions for maximum accuracy.
        
        Args:
            ml_probability: Probability (0-100) output from the GradientBoosting model.
            sensors: Real-time telemetry data.
            
        Returns:
            (final_probability, critical_reason)
        """
        physics_prob, reason = self.calculate_physical_risk(sensors)
        
        # If physics detects an absolute critical event (e.g., Surge or Cavitation),
        # it strongly overrides the ML baseline.
        if physics_prob > 80.0:
            final_prob = max(ml_probability, physics_prob)
        else:
            # Weighted average: 60% ML, 40% Physics API
            final_prob = (ml_probability * 0.6) + (physics_prob * 0.4)
            
        return min(100.0, final_prob), reason


class CentrifugalPump(RotaryEquipment):
    """
    API 610 Centrifugal Pump Physics.
    Failure Modes: Cavitation (NPSHa vs NPSHr), Mechanical Wear/Misalignment (Vibration).
    """
    
    def __init__(self, tag: str, npshr: float = 2.0, vapor_pressure_bar: float = 0.02):
        """
        Args:
            npshr: Net Positive Suction Head Required by manufacturer (meters).
            vapor_pressure_bar: Vapor pressure of the fluid at operating temp.
        """
        super().__init__(tag)
        self.npshr = npshr
        self.vapor_pressure = vapor_pressure_bar
        
    def calculate_physical_risk(self, sensors: Dict[str, float]) -> Tuple[float, str]:
        """
        API 610 Logic:
        1. Cavitation Risk: NPSH available must exceed NPSH required + safety margin (0.5m).
        2. Misalignment Risk: Elevated 1x or 2x RPM vibration indicates shaft/coupling issues.
        """
        risk_score = 0.0
        reasons = []
        
        # 1. Cavitation Analysis
        # Simplification: NPSHa is roughly (inlet_pressure - vapor_pressure) converted to head, 
        # plus static head (assumed constant here if 'available_npsh' sensor isn't explicitly provided).
        # We prefer the direct 'available_npsh' sensor if present.
        npsha = sensors.get('available_npsh')
        
        if npsha is None:
            # Estimate if not provided (Head in meters roughly P(bar) * 10.19 for water)
            inlet_p = sensors.get('inlet_pressure', 1.0)
            npsha = max(0.0, (inlet_p - self.vapor_pressure) * 10.19)

        margin = npsha - self.npshr
        
        if margin < 0:
            # Severe cavitation — immediate threat
            risk_score += 85.0
            reasons.append("CRITICAL: Severe Cavitation (NPSHa < NPSHr)")
        elif margin < 0.5:
            # Marginal — risk of cavitation damage over time
            risk_score += 40.0
            reasons.append("WARNING: Low NPSH Margin (Risk of incipient cavitation)")
            
        # 2. Vibration Analysis (1x and 2x RPM)
        # Using overall vibration as proxy if spectrum isn't available
        vib = sensors.get('vibration', sensors.get('radial_vibration', 0.0))
        
        # API 610 Zone C/D limits applied dynamically
        if vib > 7.1:
            risk_score += 70.0
            reasons.append("CRITICAL: Destructive Vibration (ISO 10816 Zone D)")
        elif vib > 4.5:
            risk_score += 30.0
            reasons.append("WARNING: High Vibration (Possible misalignment/wear)")
            
        final_risk = min(100.0, risk_score)
        reason_str = " | ".join(reasons) if reasons else "Physical parameters normal"
        
        return final_risk, reason_str


class GasCompressor(RotaryEquipment):
    """
    API 617 / API 618 Gas Compressor Physics.
    Failure Modes: Surge (Bombeo) and Choke (Piedra).
    """
    
    def __init__(self, tag: str, design_compression_ratio: float = 4.0, surge_margin_limit: float = 1.1):
        """
        Args:
            design_compression_ratio: Normal operating Rc.
            surge_margin_limit: Min distance from the Surge line (usually 10% - 15%).
        """
        super().__init__(tag)
        self.design_rc = design_compression_ratio
        self.surge_limit = surge_margin_limit
        
    def calculate_physical_risk(self, sensors: Dict[str, float]) -> Tuple[float, str]:
        """
        API 617 Logic:
        1. Surge Risk: If (Actual Compression Ratio / Mass Flow proxy) exceeds the surge line,
           failure risk becomes exponentially critical.
        """
        risk_score = 0.0
        reasons = []
        
        rc = sensors.get('compression_ratio', self.design_rc)
        
        # In a real environment, mass flow is used. Here volumetric flow is a proxy if mass flow is absent.
        flow = sensors.get('volumetric_flow', 100.0) 
        
        # Simplified Surge Curve mapping (Rc vs Flow)
        # Assuming nominal flow is 100. If flow drops while Rc remains high, we approach Surge.
        flow_ratio = flow / 100.0 
        
        if flow_ratio <= 0:
            surge_proximity = 99.0 # Division by zero prevention
        else:
            surge_proximity = rc / flow_ratio
            
        # Surge Control Line evaluation
        if surge_proximity > (self.design_rc * self.surge_limit):
            # We crossed the surge line - massive mechanical stress, blade reversal
            risk_score += 99.0
            reasons.append("CRITICAL: SURGE CONDITION DETECTED (Imminent Catastrophic Failure)")
        elif surge_proximity > (self.design_rc * 1.05):
            # Nearing surge line
            risk_score += 60.0
            reasons.append("WARNING: Approaching Surge Control Line")
            
        # Add basic vibration threshold for compressors (API 617)
        vib = sensors.get('radial_vibration', 0.0)
        if vib > 10.0:  # API 670 Danger limit
            risk_score += 80.0
            reasons.append("CRITICAL: Radial Vibration > 10 mm/s (API 670 Danger)")
            
        final_risk = min(100.0, risk_score)
        reason_str = " | ".join(reasons) if reasons else "Thermodynamic state normal"
        
        return final_risk, reason_str


class SteamTurbine(RotaryEquipment):
    """
    API 611 / API 612 Steam Turbine Physics.
    Failure Modes: Thermal Fatigue (Creep), Overspeed, Mass Unbalance.
    """
    
    def __init__(self, tag: str, max_exhaust_temp: float = 550.0):
        """
        Args:
            max_exhaust_temp: Maximum allowable exhaust temperature before Creep accelerates.
        """
        super().__init__(tag)
        self.max_exhaust_temp = max_exhaust_temp
        
    def calculate_physical_risk(self, sensors: Dict[str, float]) -> Tuple[float, str]:
        """
        API 611/612 Logic:
        1. Thermal Fatigue (Creep): Temperatures above design limit exponentially consume life.
        2. Overspeed: Mechanical trip threshold.
        """
        risk_score = 0.0
        reasons = []
        
        exhaust_temp = sensors.get('exhaust_temperature', sensors.get('steam_temperature', 300.0))
        speed = sensors.get('synchronous_speed', sensors.get('rpm', 3600.0))
        
        # 1. Thermal Fatigue (Simplified Miner's Rule application)
        # If temp > max_exhaust_temp, damage accrues exponentially
        temp_delta = exhaust_temp - self.max_exhaust_temp
        if temp_delta > 0:
            # For every 10 degrees over, risk spikes
            creep_risk = (temp_delta / 10.0) ** 2 * 5.0
            risk_score += creep_risk
            
            if temp_delta > 50:
                reasons.append(f"CRITICAL: Extreme Thermal Fatigue (Exhaust Temp > {self.max_exhaust_temp}C)")
            else:
                reasons.append("WARNING: Elevated temperature accelerating Creep damage")
                
        # 2. Overspeed Trip (API 670 / API 612)
        # Typically 105% to 110% of synchronous speed
        nominal_speed = 3600.0 # Standard 60Hz 2-pole
        if speed > (nominal_speed * 1.10):
            risk_score += 99.0
            reasons.append("CRITICAL: OVERSPEED (Mechanical Trip Range)")
            
        # 3. Axial Vibration (API 670)
        vib_axial = sensors.get('axial_vibration', 0.0)
        if vib_axial > 9.0: # API 670 Danger
            risk_score += 80.0
            reasons.append("CRITICAL: Axial Displacement/Vibration Exceeds API 670 Danger Limit")
            
        final_risk = min(100.0, risk_score)
        reason_str = " | ".join(reasons) if reasons else "Thermal and mechanical states normal"
        
        return final_risk, reason_str

