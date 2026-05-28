"""
Equipment Engine - Core Module
Migrated from core/ modules for FastAPI backend
Implements equipment calculations for all equipment types

Migrated modules:
- core/pump_dynamic_model.py
- core/compressor_surge_analysis.py
- core/multiphase_flow.py
- core/statistics.py (equipment classes)
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
import numpy as np
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ============================================================================
# PUMP DYNAMIC MODEL
# ============================================================================

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
        """System of differential equations for pump transient response."""
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
        
        head = self._calculate_pump_head(omega, Q)
        power = head * Q * self.params.fluid_density_kg_m3 * 9.81 / 1e6
        
        peak_efficiency = 0.85
        flow_sensitivity = 0.2
        flow_ratio = Q / self.nominal_flow
        
        efficiency = peak_efficiency * (1.0 - flow_sensitivity * abs(flow_ratio - 1.0) ** 2)
        efficiency = max(0.3, min(0.95, efficiency))
        
        torque = (power * 1e6) / (omega * efficiency) if omega > 0 else 0
        return torque
    
    def _calculate_pump_head(self, omega: float, Q: float) -> float:
        """Calculate pump head using affinity laws."""
        if omega < 0.01:
            return 0
        
        speed_ratio = omega / self.nominal_speed
        flow_ratio = Q / self.nominal_flow
        
        head_coefficient = 1.0 - 0.5 * (flow_ratio / speed_ratio - 1.0) ** 2
        head = self.nominal_head * speed_ratio ** 2 * head_coefficient
        
        return max(0, head)
    
    def _calculate_theoretical_flow(self, omega: float) -> float:
        """Calculate theoretical flow from speed."""
        return self.params.pump_displacement_m3_rev * omega / (2 * np.pi)
    
    def _calculate_leakage(self, pressure_diff: float) -> float:
        """Calculate internal leakage flow."""
        leakage_coefficient = 1e-8
        return leakage_coefficient * abs(pressure_diff) ** 0.5
    
    def _calculate_flow_acceleration(self, P_outlet: float, P_inlet: float, Q: float) -> float:
        """Calculate flow acceleration."""
        pressure_gradient = (P_outlet - P_inlet) / self.params.outlet_pipe_length_m
        friction_loss = self.params.pipe_friction_coefficient * Q * abs(Q)
        
        acceleration = (pressure_gradient - friction_loss) / self.params.fluid_density_kg_m3
        return acceleration * 0.1
    
    def check_cavitation(self, P_inlet: float, fluid_vapor_pressure: float) -> Tuple[bool, float]:
        """Check for cavitation conditions."""
        npsh_available = (P_inlet - fluid_vapor_pressure) / (self.params.fluid_density_kg_m3 * 9.81)
        npsh_required = self.nominal_head * 0.1
        
        is_cavitating = npsh_available < npsh_required
        cavitation_margin = npsh_available - npsh_required
        
        return is_cavitating, cavitation_margin


# ============================================================================
# COMPRESSOR SURGE ANALYSIS
# ============================================================================

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
    """Analyzes compressor stability and surge phenomena."""
    
    def __init__(self, params: CompressorParameters):
        self.params = params
        self.nominal_speed = params.rated_speed_rpm * np.pi / 30
        self.nominal_flow = params.rated_flow_kg_s
        self.nominal_pressure_ratio = params.rated_pressure_ratio
        
        self.compressor_map = self._generate_compressor_map()
        self.surge_line = self._generate_surge_line()
    
    def _generate_compressor_map(self) -> Dict[float, Tuple[float, float]]:
        """Generate compressor performance map."""
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
        """Generate surge line (minimum stable flow at each speed)."""
        surge_line = {}
        surge_flow_coefficient = 0.65
        surge_line_curvature = 0.1
        
        for speed_ratio in np.linspace(0.5, 1.5, 30):
            min_flow_ratio = surge_flow_coefficient * speed_ratio * (
                1.0 - surge_line_curvature * (1.0 - speed_ratio) ** 2
            )
            surge_line[speed_ratio] = max(min_flow_ratio, 0.1)
        
        return surge_line
    
    def is_in_surge_region(self, flow_ratio: float, speed_ratio: float) -> bool:
        """Check if operating point is in surge region."""
        if speed_ratio <= 0:
            return False
        
        min_flow_ratio = self.surge_line.get(speed_ratio, 0.65 * speed_ratio)
        return flow_ratio < min_flow_ratio * 1.05
    
    def calculate_surge_margin(self, flow_ratio: float, speed_ratio: float) -> float:
        """Calculate surge margin (percentage above surge line)."""
        if speed_ratio <= 0:
            return 100.0
        
        min_flow_ratio = self.surge_line.get(speed_ratio, 0.65 * speed_ratio)
        
        if flow_ratio <= 0:
            return -100.0
        
        margin = ((flow_ratio - min_flow_ratio) / min_flow_ratio) * 100
        return margin
    
    def detect_rotating_stall(self, pressure_oscillations: np.ndarray, sampling_rate: float) -> Tuple[bool, float]:
        """Detect rotating stall from pressure oscillations."""
        from scipy.fftpack import fft, fftfreq
        
        n = len(pressure_oscillations)
        fft_vals = np.abs(fft(pressure_oscillations))[:n//2]
        freqs = fftfreq(n, 1.0/sampling_rate)[:n//2]
        
        blade_passing_freq = (self.params.blade_count * self.nominal_speed) / (2 * np.pi)
        stall_freq_range = (blade_passing_freq * 0.3, blade_passing_freq * 0.7)
        
        stall_indices = np.where((freqs >= stall_freq_range[0]) & (freqs <= stall_freq_range[1]))[0]
        
        if len(stall_indices) > 0:
            stall_amplitude = np.max(fft_vals[stall_indices])
            baseline_amplitude = np.mean(fft_vals)
            
            is_stalling = stall_amplitude > baseline_amplitude * 3
            stall_severity = stall_amplitude / baseline_amplitude if baseline_amplitude > 0 else 0
            
            return is_stalling, stall_severity
        
        return False, 0.0


# ============================================================================
# MULTIPHASE FLOW
# ============================================================================

class LockhartMartinelliCorrelation:
    """Calculates void fraction using Lockhart-Martinelli correlation."""
    
    @staticmethod
    def calculate_void_fraction(
        quality: float,
        density_gas: float,
        density_liquid: float,
        viscosity_gas: float,
        viscosity_liquid: float
    ) -> float:
        """Calculate void fraction based on Chisholm correlation."""
        if quality <= 0.0:
            return 0.0
        if quality >= 1.0:
            return 1.0
        
        rho_ratio = density_liquid / density_gas
        mu_ratio = viscosity_liquid / viscosity_gas
        
        x_tt = ((1 - quality) / quality) ** 0.9 * (rho_ratio) ** -0.5 * (mu_ratio) ** 0.1
        
        void_fraction = 1.0 / (1.0 + ((1.0 - quality) / quality) * (density_gas / density_liquid) ** (2.0 / 3.0))
        return void_fraction


class MixedDensityCalculator:
    """Computes variable mixed density based on gas fraction."""
    
    @staticmethod
    def calculate_mixed_density(void_fraction: float, density_gas: float, density_liquid: float) -> float:
        """Calculate homogeneous mixed density of two-phase flow."""
        void_fraction = max(0.0, min(1.0, void_fraction))
        return void_fraction * density_gas + (1.0 - void_fraction) * density_liquid


class DNVErosionCorrosionModel:
    """Implements DNV RP O501 standard for erosion and corrosion rates."""
    
    @staticmethod
    def calculate_erosion_rate(
        fluid_velocity: float,
        particle_density: float,
        particle_diameter: float,
        sand_production_rate: float,
        pipe_diameter: float
    ) -> float:
        """Simplified DNV RP O501 erosion rate prediction (mm/year)."""
        K = 2.0e-9
        n = 2.6
        
        area = np.pi * (pipe_diameter / 2.0) ** 2
        
        if area > 0 and fluid_velocity > 0:
            concentration = sand_production_rate / (fluid_velocity * area)
        else:
            concentration = 0.0
        
        erosion_rate = K * concentration * (fluid_velocity ** n)
        erosion_rate_mm_yr = erosion_rate * 1000 * 31536000
        
        return erosion_rate_mm_yr


class SlurryWearPredictor:
    """Predicts wear rates in slurry transport systems."""
    
    @staticmethod
    def calculate_wear_rate(
        velocity: float,
        concentration_vol: float,
        particle_hardness: float,
        pipe_hardness: float
    ) -> float:
        """Calculate slurry abrasive wear rate."""
        if pipe_hardness <= 0:
            return 0.0
        
        hardness_ratio = particle_hardness / pipe_hardness
        wear_index = (velocity ** 3) * concentration_vol * (hardness_ratio ** 1.2)
        
        return wear_index * 1e-4


# ============================================================================
# EQUIPMENT ENGINE - MAIN CLASS
# ============================================================================

class EquipmentEngine:
    """
    Equipment calculation and management engine.
    Integrates all equipment-specific calculation modules.
    Authored by Jhon Villegas
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_equipment(self, equipment_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """
        Create new equipment configuration in the database.
        Authored by Jhon Villegas
        """
        logger.info(f"Creating equipment for user {user_id}")
        
        # Extract fields and resolve enums
        tag = equipment_data.get("tag")
        name = equipment_data.get("name")
        description = equipment_data.get("description")
        
        equipment_type_str = equipment_data.get("equipment_type")
        try:
            equipment_type = EquipmentType(equipment_type_str)
        except ValueError:
            equipment_type = EquipmentType.PUMP
            
        status_str = equipment_data.get("status", "operational")
        try:
            status = EquipmentStatus(status_str)
        except ValueError:
            status = EquipmentStatus.OPERATIONAL

        specifications = equipment_data.get("specifications", {})
        operating_parameters = equipment_data.get("operating_parameters", {})
        design_parameters = equipment_data.get("design_parameters", {})
        
        db_equipment = Equipment(
            tag=tag,
            name=name,
            description=description,
            equipment_type=equipment_type,
            status=status,
            location=equipment_data.get("location"),
            facility=equipment_data.get("facility"),
            unit=equipment_data.get("unit"),
            manufacturer=equipment_data.get("manufacturer"),
            model=equipment_data.get("model"),
            serial_number=equipment_data.get("serial_number"),
            specifications=specifications,
            operating_parameters=operating_parameters,
            design_parameters=design_parameters,
            rated_capacity=equipment_data.get("rated_capacity"),
            rated_power_kw=equipment_data.get("rated_power_kw"),
            efficiency=equipment_data.get("efficiency"),
            is_active=equipment_data.get("is_active", True),
            is_critical=equipment_data.get("is_critical", False),
            requires_monitoring=equipment_data.get("requires_monitoring", True),
            owner_id=user_id
        )
        
        self.db.add(db_equipment)
        self.db.commit()
        self.db.refresh(db_equipment)
        
        return db_equipment.to_dict()
    
    def list_equipment(
        self,
        skip: int = 0,
        limit: int = 100,
        equipment_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List equipment configurations from the database.
        Authored by Jhon Villegas
        """
        query = self.db.query(Equipment)
        if user_id is not None:
            query = query.filter(Equipment.owner_id == user_id)
        if equipment_type is not None:
            try:
                eq_type = EquipmentType(equipment_type)
                query = query.filter(Equipment.equipment_type == eq_type)
            except ValueError:
                pass
        
        equipment_list = query.offset(skip).limit(limit).all()
        return [eq.to_dict() for eq in equipment_list]
    
    def get_equipment(self, equipment_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get specific equipment configuration from the database.
        Authored by Jhon Villegas
        """
        equipment = self.db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == user_id
        ).first()
        if not equipment:
            return None
        return equipment.to_dict()
    
    def update_equipment(
        self,
        equipment_id: int,
        equipment_data: Dict[str, Any],
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Update equipment configuration in the database.
        Authored by Jhon Villegas
        """
        db_equipment = self.db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == user_id
        ).first()
        if not db_equipment:
            return None
            
        for key, value in equipment_data.items():
            if hasattr(db_equipment, key):
                if key == "equipment_type" and value is not None:
                    try:
                        value = EquipmentType(value)
                    except ValueError:
                        continue
                elif key == "status" and value is not None:
                    try:
                        value = EquipmentStatus(value)
                    except ValueError:
                        continue
                setattr(db_equipment, key, value)
                
        self.db.commit()
        self.db.refresh(db_equipment)
        return db_equipment.to_dict()
    
    def delete_equipment(self, equipment_id: int, user_id: int) -> bool:
        """
        Delete equipment configuration from the database.
        Authored by Jhon Villegas
        """
        db_equipment = self.db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == user_id
        ).first()
        if not db_equipment:
            return False
            
        self.db.delete(db_equipment)
        self.db.commit()
        return True
    
    def calculate(self, equipment: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform equipment calculations.
        Authored by Jhon Villegas
        """
        equipment_type = equipment.get("equipment_type")
        
        if equipment_type == "pump":
            return self._calculate_pump(parameters)
        elif equipment_type == "compressor":
            return self._calculate_compressor(parameters)
        elif equipment_type == "separator":
            return self._calculate_separator(parameters)
        else:
            raise ValueError(f"Unknown equipment type: {equipment_type}")
    
    def _calculate_pump(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate pump performance using PumpDynamicModel.
        Authored by Jhon Villegas
        """
        try:
            pump_params = PumpParameters(
                rotor_inertia_kg_m2=parameters.get("rotor_inertia_kg_m2", 10.0),
                pump_displacement_m3_rev=parameters.get("pump_displacement_m3_rev", 0.01),
                fluid_density_kg_m3=parameters.get("fluid_density_kg_m3", 1000.0),
                rated_speed_rpm=parameters.get("rated_speed_rpm", 3000.0),
                rated_head_meters=parameters.get("rated_head_meters", 100.0),
                rated_flow_m3_h=parameters.get("rated_flow_m3_h", 100.0),
                inlet_volume_m3=parameters.get("inlet_volume_m3", 1.0),
                outlet_volume_m3=parameters.get("outlet_volume_m3", 1.0),
                pipe_friction_coefficient=parameters.get("pipe_friction_coefficient", 0.02),
                inlet_pipe_length_m=parameters.get("inlet_pipe_length_m", 10.0),
                outlet_pipe_length_m=parameters.get("outlet_pipe_length_m", 10.0),
                inlet_pipe_diameter_m=parameters.get("inlet_pipe_diameter_m", 0.2),
                outlet_pipe_diameter_m=parameters.get("outlet_pipe_diameter_m", 0.15)
            )
            
            model = PumpDynamicModel(pump_params)
            
            is_cavitating, cavitation_margin = model.check_cavitation(
                parameters.get("inlet_pressure", 101325),
                parameters.get("vapor_pressure", 2340)
            )
            
            return {
                "status": "calculated",
                "results": {
                    "nominal_speed_rad_s": model.nominal_speed,
                    "nominal_flow_m3_s": model.nominal_flow,
                    "nominal_head_m": model.nominal_head,
                    "is_cavitating": is_cavitating,
                    "cavitation_margin_m": cavitation_margin
                }
            }
        except Exception as e:
            logger.error(f"Pump calculation error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _calculate_compressor(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate compressor performance using CompressorSurgeAnalyzer.
        Authored by Jhon Villegas
        """
        try:
            comp_params = CompressorParameters(
                rotor_inertia_kg_m2=parameters.get("rotor_inertia_kg_m2", 50.0),
                rated_speed_rpm=parameters.get("rated_speed_rpm", 10000.0),
                rated_flow_kg_s=parameters.get("rated_flow_kg_s", 10.0),
                rated_pressure_ratio=parameters.get("rated_pressure_ratio", 3.0),
                inlet_volume_m3=parameters.get("inlet_volume_m3", 2.0),
                discharge_volume_m3=parameters.get("discharge_volume_m3", 1.0),
                surge_line_slope=parameters.get("surge_line_slope", 0.5),
                stage_count=parameters.get("stage_count", 3),
                blade_count=parameters.get("blade_count", 20),
                polytropic_efficiency=parameters.get("polytropic_efficiency", 0.85),
                anti_surge_valve_response_time=parameters.get("anti_surge_valve_response_time", 0.5)
            )
            
            analyzer = CompressorSurgeAnalyzer(comp_params)
            
            flow_ratio = parameters.get("flow_ratio", 1.0)
            speed_ratio = parameters.get("speed_ratio", 1.0)
            
            is_surging = analyzer.is_in_surge_region(flow_ratio, speed_ratio)
            surge_margin = analyzer.calculate_surge_margin(flow_ratio, speed_ratio)
            
            return {
                "status": "calculated",
                "results": {
                    "is_surging": is_surging,
                    "surge_margin_percent": surge_margin,
                    "nominal_speed_rad_s": analyzer.nominal_speed,
                    "nominal_flow_kg_s": analyzer.nominal_flow
                }
            }
        except Exception as e:
            logger.error(f"Compressor calculation error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _calculate_separator(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate separator performance using multiphase flow models.
        Authored by Jhon Villegas
        """
        try:
            quality = parameters.get("quality", 0.5)
            density_gas = parameters.get("density_gas", 1.2)
            density_liquid = parameters.get("density_liquid", 1000.0)
            viscosity_gas = parameters.get("viscosity_gas", 1.8e-5)
            viscosity_liquid = parameters.get("viscosity_liquid", 0.001)
            
            void_fraction = LockhartMartinelliCorrelation.calculate_void_fraction(
                quality, density_gas, density_liquid, viscosity_gas, viscosity_liquid
            )
            
            mixed_density = MixedDensityCalculator.calculate_mixed_density(
                void_fraction, density_gas, density_liquid
            )
            
            return {
                "status": "calculated",
                "results": {
                    "void_fraction": void_fraction,
                    "mixed_density_kg_m3": mixed_density,
                    "gas_fraction": quality,
                    "liquid_fraction": 1.0 - quality
                }
            }
        except Exception as e:
            logger.error(f"Separator calculation error: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_performance_metrics(self, equipment_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get equipment performance metrics from database telemetry.
        Authored by Jhon Villegas
        """
        from app.models.telemetry import TelemetryData
        
        last_telemetry = self.db.query(TelemetryData).filter(
            TelemetryData.equipment_id == equipment_id
        ).order_by(TelemetryData.timestamp.desc()).first()
        
        if last_telemetry:
            efficiency = 0.85
            if last_telemetry.power_kw and last_telemetry.flow_rate_m3_s:
                density = 1000.0
                g = 9.81
                flow = last_telemetry.flow_rate_m3_s
                head = last_telemetry.pressure_pa / (density * g) if last_telemetry.pressure_pa else 50.0
                theoretical_power = density * g * flow * head / 1000.0
                if last_telemetry.power_kw > 0:
                    efficiency = min(0.98, max(0.2, theoretical_power / last_telemetry.power_kw))
                    
            vibration = last_telemetry.vibration_mm_s or 1.5
            maintenance_score = max(0.1, min(1.0, 1.0 - (vibration / 15.0)))
            
            return {
                "efficiency": float(efficiency),
                "uptime": 0.98,
                "maintenance_score": float(maintenance_score),
                "last_vibration": vibration,
                "last_temperature": last_telemetry.temperature_c
            }
            
        return {
            "efficiency": 0.85,
            "uptime": 0.95,
            "maintenance_score": 0.90
        }