"""
Analysis Engine - Core Module
Migrated from core/ modules for FastAPI backend
Implements spectral analysis, thermal analysis, and causal diagnosis

Migrated modules:
- core/spectral_analysis.py
- core/realtime_fft.py
- core/thermal_analysis.py
- core/causal_diagnosis.py
- core/statistics.py
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
import logging
from scipy.fftpack import fft, fftfreq
from scipy.signal import hilbert, butter, filtfilt, spectrogram
from scipy.sparse import diags, lil_matrix
from scipy.sparse.linalg import spsolve
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


# ============================================================================
# SPECTRAL ANALYSIS
# ============================================================================

class BearingFrequencyDetector:
    """Calculates bearing fault frequencies (BPFO, BSF, FTF)."""
    
    @staticmethod
    def calculate_frequencies(
        rpm: float,
        n_rollers: int,
        roller_diameter: float,
        pitch_diameter: float,
        contact_angle_deg: float
    ) -> Dict[str, float]:
        """Calculate fundamental bearing defect frequencies."""
        rps = rpm / 60.0
        angle_rad = np.radians(contact_angle_deg)
        ratio = (roller_diameter / pitch_diameter) * np.cos(angle_rad)
        
        ftf = (rps / 2.0) * (1.0 - ratio)
        bpfo = n_rollers * ftf
        bpfi = (n_rollers * rps / 2.0) * (1.0 + ratio)
        bsf = (pitch_diameter / (2.0 * roller_diameter)) * rps * (1.0 - ratio**2)
        
        return {
            "FTF": ftf,
            "BPFO": bpfo,
            "BPFI": bpfi,
            "BSF": bsf,
            "1X": rps
        }


class EnvelopeAnalyzer:
    """Performs envelope analysis (demodulation) for early defect detection."""
    
    @staticmethod
    def apply_envelope(
        signal: np.ndarray,
        fs: float,
        lowcut: float,
        highcut: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply bandpass filter and extract envelope using Hilbert transform."""
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(4, [low, high], btype='band')
        filtered_signal = filtfilt(b, a, signal)
        
        analytic_signal = hilbert(filtered_signal)
        envelope = np.abs(analytic_signal)
        
        n = len(envelope)
        envelope_fft = np.abs(fft(envelope))[:n//2] * 2.0 / n
        freqs = fftfreq(n, 1.0/fs)[:n//2]
        
        envelope_fft[0] = 0
        
        return envelope, freqs, envelope_fft


class SpectrogramGenerator:
    """Generates time-frequency spectrograms for transient analysis."""
    
    @staticmethod
    def generate(
        signal: np.ndarray,
        fs: float,
        nperseg: int = 256
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute spectrogram of the signal."""
        frequencies, times, Sxx = spectrogram(signal, fs=fs, nperseg=nperseg)
        Sxx_db = 10 * np.log10(Sxx + 1e-10)
        return frequencies, times, Sxx_db


class SignatureAnomalyDetector:
    """Uses IsolationForest to detect anomalies based on spectral signatures."""
    
    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.is_trained = False
        
    def train(self, spectral_features: np.ndarray):
        """Train the Isolation Forest on baseline spectral features."""
        if len(spectral_features) > 0:
            self.model.fit(spectral_features)
            self.is_trained = True
            
    def predict(self, spectral_features: np.ndarray) -> np.ndarray:
        """Predict if the features are anomalous (-1) or normal (1)."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction.")
        return self.model.predict(spectral_features)


class SyntheticSignalGenerator:
    """Creates mock vibration signals with controllable defect frequencies."""
    
    @staticmethod
    def generate_signal(
        fs: float,
        duration: float,
        rpm: float,
        defect_freq: float = 0.0,
        noise_level: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate a synthetic vibration signal."""
        t = np.linspace(0, duration, int(fs * duration))
        
        running_speed_freq = rpm / 60.0
        signal = np.sin(2 * np.pi * running_speed_freq * t)
        
        if defect_freq > 0:
            signal += 0.3 * np.sin(2 * np.pi * defect_freq * t)
            signal += 0.15 * np.sin(2 * np.pi * 2 * defect_freq * t)
            signal += 0.08 * np.sin(2 * np.pi * 3 * defect_freq * t)
        
        noise = noise_level * np.random.randn(len(t))
        signal += noise
        
        return t, signal


# ============================================================================
# THERMAL ANALYSIS
# ============================================================================

@dataclass
class MaterialProperties:
    """Temperature-dependent material properties."""
    name: str
    density_kg_m3: float = 7850
    reference_temp_k: float = 298.15
    
    def thermal_conductivity(self, temp_k: float) -> float:
        """Thermal conductivity k(T) in W/(m·K)."""
        k0 = 50.0
        return k0 * (1.0 - 0.0005 * (temp_k - self.reference_temp_k))
    
    def specific_heat(self, temp_k: float) -> float:
        """Specific heat capacity c(T) in J/(kg·K)."""
        c0 = 450.0
        return c0 * (1.0 + 0.0002 * (temp_k - self.reference_temp_k))
    
    def thermal_expansion_coeff(self, temp_k: float) -> float:
        """Linear thermal expansion coefficient α(T) in 1/K."""
        return 12.0e-6
    
    def youngs_modulus(self, temp_k: float) -> float:
        """Young's modulus E(T) in Pa."""
        E0 = 210e9
        return E0 * (1.0 - 0.0004 * (temp_k - self.reference_temp_k))
    
    def poisson_ratio(self) -> float:
        """Poisson's ratio ν (temperature independent)."""
        return 0.30


class BoundaryCondition:
    """Represents boundary conditions for thermal problem."""
    
    class Type:
        DIRICHLET = "dirichlet"
        NEUMANN = "neumann"
        ROBIN = "robin"
    
    def __init__(self, bc_type: str, value: float, parameter: float = 0.0):
        """
        Args:
            bc_type: Type of BC (dirichlet, neumann, robin)
            value: Temperature (Dirichlet) or heat flux (Neumann) or ambient temp (Robin)
            parameter: Convection coefficient h for Robin BC [W/(m²·K)]
        """
        self.type = bc_type
        self.value = value
        self.parameter = parameter


class ThermalConduction2D:
    """
    Advanced 2D Finite Difference solver for heat equation in casings.
    
    Solves: ∂T/∂t = α * (∂²T/∂x² + ∂²T/∂y²) + S/(ρ*c)
    """
    
    def __init__(
        self,
        domain_x: Tuple[float, float] = (0.0, 0.1),
        domain_y: Tuple[float, float] = (0.0, 0.1),
        nx: int = 50,
        ny: int = 50,
        material: Optional[MaterialProperties] = None
    ):
        """Initialize thermal domain."""
        self.domain_x = domain_x
        self.domain_y = domain_y
        self.nx = nx
        self.ny = ny
        self.material = material or MaterialProperties("Steel")
        
        self.dx = (domain_x[1] - domain_x[0]) / (nx - 1)
        self.dy = (domain_y[1] - domain_y[0]) / (ny - 1)
        
        self.x = np.linspace(domain_x[0], domain_x[1], nx)
        self.y = np.linspace(domain_y[0], domain_y[1], ny)
        
        self.temperature = np.ones((ny, nx)) * self.material.reference_temp_k
        
    def solve_steady_state(
        self,
        boundary_conditions: Dict[str, BoundaryCondition],
        heat_source: Optional[np.ndarray] = None,
        max_iterations: int = 10000,
        tolerance: float = 1e-6
    ) -> np.ndarray:
        """
        Solve steady-state heat equation using Gauss-Seidel iteration.
        
        Args:
            boundary_conditions: Dict with keys 'left', 'right', 'top', 'bottom'
            heat_source: Heat generation per unit volume [W/m³]
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
            
        Returns:
            Temperature field [K]
        """
        if heat_source is None:
            heat_source = np.zeros((self.ny, self.nx))
        
        for iteration in range(max_iterations):
            T_old = self.temperature.copy()
            
            for i in range(1, self.ny - 1):
                for j in range(1, self.nx - 1):
                    temp_avg = self.temperature[i, j]
                    k = self.material.thermal_conductivity(temp_avg)
                    rho = self.material.density_kg_m3
                    c = self.material.specific_heat(temp_avg)
                    
                    T_xx = (self.temperature[i, j+1] - 2*self.temperature[i, j] + self.temperature[i, j-1]) / (self.dx**2)
                    T_yy = (self.temperature[i+1, j] - 2*self.temperature[i, j] + self.temperature[i-1, j]) / (self.dy**2)
                    
                    source_term = heat_source[i, j] / (rho * c)
                    
                    alpha = k / (rho * c)
                    self.temperature[i, j] = (alpha * (T_xx + T_yy) + source_term) * 0.25 + 0.75 * self.temperature[i, j]
            
            self._apply_boundary_conditions(boundary_conditions)
            
            max_change = np.max(np.abs(self.temperature - T_old))
            if max_change < tolerance:
                logger.info(f"Thermal solution converged in {iteration + 1} iterations")
                break
        
        return self.temperature
    
    def _apply_boundary_conditions(self, boundary_conditions: Dict[str, BoundaryCondition]):
        """Apply boundary conditions to the domain."""
        if 'left' in boundary_conditions:
            bc = boundary_conditions['left']
            if bc.type == BoundaryCondition.Type.DIRICHLET:
                self.temperature[:, 0] = bc.value
        
        if 'right' in boundary_conditions:
            bc = boundary_conditions['right']
            if bc.type == BoundaryCondition.Type.DIRICHLET:
                self.temperature[:, -1] = bc.value
        
        if 'bottom' in boundary_conditions:
            bc = boundary_conditions['bottom']
            if bc.type == BoundaryCondition.Type.DIRICHLET:
                self.temperature[0, :] = bc.value
        
        if 'top' in boundary_conditions:
            bc = boundary_conditions['top']
            if bc.type == BoundaryCondition.Type.DIRICHLET:
                self.temperature[-1, :] = bc.value
    
    def calculate_thermal_stress(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate thermal stress using temperature field.
        
        Returns:
            (von_mises_stress, max_principal_stress) in Pa
        """
        T_ref = self.material.reference_temp_k
        alpha = self.material.thermal_expansion_coeff(T_ref)
        E = self.material.youngs_modulus(T_ref)
        nu = self.material.poisson_ratio()
        
        thermal_strain = alpha * (self.temperature - T_ref)
        
        stress_factor = E / (1 - nu)
        thermal_stress = stress_factor * thermal_strain
        
        von_mises = np.abs(thermal_stress)
        
        return von_mises, thermal_stress


# ============================================================================
# CAUSAL DIAGNOSIS
# ============================================================================

@dataclass
class FaultRule:
    """Represents a fault diagnosis rule."""
    required_features: set
    mode: str
    root_cause: str
    standards: str
    remediation: List[str]


class CausalDiagnosisEngine:
    """
    Causal diagnosis engine for equipment failure analysis.
    Provides SHAP-based feature attribution and fault tree generation.
    """
    
    def __init__(self):
        self.fault_rules = self._initialize_fault_rules()
    
    def _initialize_fault_rules(self) -> List[FaultRule]:
        """Initialize industrial fault mode knowledge base."""
        return [
            FaultRule(
                required_features={"vibration", "temperature"},
                mode="Bearing Seizure / Mechanical Imbalance",
                root_cause="Loss of lubrication or mechanical misalignment causing abnormal friction and heat generation in bearing assembly.",
                standards="API 610 Section 9.1, ISO 10816-3",
                remediation=[
                    "Inspect bearing clearances and lubrication system",
                    "Perform vibration spectrum analysis for imbalance harmonics",
                    "Check coupling alignment — allowable offset < 0.05 mm/m",
                ]
            ),
            FaultRule(
                required_features={"available_npsh", "vibration"},
                mode="Cavitation",
                root_cause="Net Positive Suction Head available (NPSHa) below required (NPSHr), causing vapor bubble formation and implosion on impeller blades.",
                standards="API 610 Section 7.3, HI 9.6.1",
                remediation=[
                    "Verify NPSHa > NPSHr with minimum 0.6 m safety margin",
                    "Reduce suction pipe restrictions",
                    "Lower fluid temperature or increase suction vessel pressure",
                ]
            ),
            FaultRule(
                required_features={"compression_ratio", "axial_vibration"},
                mode="Compressor Surge",
                root_cause="Operating point crossed the surge line on the compressor map — flow reversed causing cyclic pressure oscillations and axial thrust loads.",
                standards="API 617 Section 2.1.3, API 670",
                remediation=[
                    "Open anti-surge recycle valve immediately",
                    "Reduce compression ratio — lower discharge pressure or increase suction",
                    "Verify surge controller setpoint",
                ]
            ),
            FaultRule(
                required_features={"radial_vibration", "axial_vibration"},
                mode="Rotor Instability / Oil Whirl",
                root_cause="Sub-synchronous vibration indicating fluid-induced instability in hydrodynamic journal bearings or rotor-dynamic instability.",
                standards="API 670 Section 4.3, ISO 10816-4",
                remediation=[
                    "Check bearing clearances — elliptical bearings preferred for stability",
                    "Verify lube oil supply pressure and temperature",
                    "Review critical speed margins (min 15% per API 617)",
                ]
            ),
        ]
    
    def diagnose(
        self,
        sensor_data: Dict[str, float],
        feature_importance: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Diagnose equipment condition based on sensor data.
        
        Args:
            sensor_data: Dict of sensor readings
            feature_importance: Optional SHAP values or feature importance scores
            
        Returns:
            Diagnosis result with fault mode, root cause, and remediation
        """
        available_features = set(sensor_data.keys())
        
        matched_rules = []
        for rule in self.fault_rules:
            if rule.required_features.issubset(available_features):
                confidence = self._calculate_confidence(sensor_data, rule, feature_importance)
                if confidence > 0.5:
                    matched_rules.append({
                        "rule": rule,
                        "confidence": confidence
                    })
        
        if not matched_rules:
            return {
                "fault_detected": False,
                "mode": "Normal Operation",
                "confidence": 0.0
            }
        
        matched_rules.sort(key=lambda x: x["confidence"], reverse=True)
        best_match = matched_rules[0]
        rule = best_match["rule"]
        
        return {
            "fault_detected": True,
            "mode": rule.mode,
            "root_cause": rule.root_cause,
            "standards": rule.standards,
            "remediation": rule.remediation,
            "confidence": best_match["confidence"],
            "alternative_diagnoses": [
                {
                    "mode": m["rule"].mode,
                    "confidence": m["confidence"]
                }
                for m in matched_rules[1:3]
            ]
        }
    
    def _calculate_confidence(
        self,
        sensor_data: Dict[str, float],
        rule: FaultRule,
        feature_importance: Optional[Dict[str, float]]
    ) -> float:
        """Calculate confidence score for a fault rule."""
        base_confidence = 0.7
        
        if feature_importance:
            importance_sum = sum(
                feature_importance.get(feat, 0.0)
                for feat in rule.required_features
            )
            base_confidence += importance_sum * 0.3
        
        return min(1.0, base_confidence)


# ============================================================================
# ANALYSIS ENGINE - MAIN CLASS
# ============================================================================

class AnalysisEngine:
    """
    Main analysis engine integrating all analysis capabilities.
    """
    
    def __init__(self):
        self.bearing_detector = BearingFrequencyDetector()
        self.envelope_analyzer = EnvelopeAnalyzer()
        self.spectrogram_generator = SpectrogramGenerator()
        self.anomaly_detector = SignatureAnomalyDetector()
        self.diagnosis_engine = CausalDiagnosisEngine()
    
    def analyze_vibration(
        self,
        signal: np.ndarray,
        sampling_rate: float,
        equipment_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive vibration analysis."""
        bearing_freqs = self.bearing_detector.calculate_frequencies(
            rpm=equipment_params.get("rpm", 3000),
            n_rollers=equipment_params.get("n_rollers", 8),
            roller_diameter=equipment_params.get("roller_diameter", 0.01),
            pitch_diameter=equipment_params.get("pitch_diameter", 0.05),
            contact_angle_deg=equipment_params.get("contact_angle_deg", 0)
        )
        
        envelope, freqs, envelope_fft = self.envelope_analyzer.apply_envelope(
            signal,
            sampling_rate,
            equipment_params.get("lowcut", 1000),
            equipment_params.get("highcut", 5000)
        )
        
        frequencies, times, spectrogram_db = self.spectrogram_generator.generate(
            signal,
            sampling_rate
        )
        
        return {
            "bearing_frequencies": bearing_freqs,
            "envelope_spectrum": {
                "frequencies": freqs.tolist(),
                "amplitudes": envelope_fft.tolist()
            },
            "spectrogram": {
                "frequencies": frequencies.tolist(),
                "times": times.tolist(),
                "power_db": spectrogram_db.tolist()
            }
        }
    
    def analyze_thermal(
        self,
        domain_size: Tuple[float, float],
        grid_size: Tuple[int, int],
        boundary_conditions: Dict[str, Dict[str, Any]],
        heat_source: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Perform thermal analysis."""
        thermal_solver = ThermalConduction2D(
            domain_x=(0, domain_size[0]),
            domain_y=(0, domain_size[1]),
            nx=grid_size[0],
            ny=grid_size[1]
        )
        
        bcs = {}
        for side, bc_data in boundary_conditions.items():
            bcs[side] = BoundaryCondition(
                bc_type=bc_data["type"],
                value=bc_data["value"],
                parameter=bc_data.get("parameter", 0.0)
            )
        
        temperature_field = thermal_solver.solve_steady_state(bcs, heat_source)
        von_mises, thermal_stress = thermal_solver.calculate_thermal_stress()
        
        return {
            "temperature_field": temperature_field.tolist(),
            "von_mises_stress": von_mises.tolist(),
            "thermal_stress": thermal_stress.tolist(),
            "max_temperature": float(np.max(temperature_field)),
            "min_temperature": float(np.min(temperature_field)),
            "max_stress": float(np.max(von_mises))
        }
    
    def diagnose_fault(
        self,
        sensor_data: Dict[str, float],
        feature_importance: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Perform causal diagnosis."""
        return self.diagnosis_engine.diagnose(sensor_data, feature_importance)
    
    def detect_anomaly(
        self,
        spectral_features: np.ndarray,
        baseline_features: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Detect anomalies in spectral signatures."""
        if baseline_features is not None and not self.anomaly_detector.is_trained:
            self.anomaly_detector.train(baseline_features)
        
        if not self.anomaly_detector.is_trained:
            return {
                "error": "Anomaly detector not trained. Provide baseline_features."
            }
        
        predictions = self.anomaly_detector.predict(spectral_features)
        
        anomaly_count = np.sum(predictions == -1)
        total_count = len(predictions)
        
        return {
            "predictions": predictions.tolist(),
            "anomaly_count": int(anomaly_count),
            "total_count": int(total_count),
            "anomaly_rate": float(anomaly_count / total_count) if total_count > 0 else 0.0
        }