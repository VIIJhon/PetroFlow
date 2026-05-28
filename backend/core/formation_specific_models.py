"""
Formation-Specific Models Module
Generates and manages ML models tailored to specific geological formations,
well depths, bottom-hole temperatures, and crude oil viscosities.

Supported formations:
- Sandstone: Higher erosion risk, sand production
- Limestone: Corrosion risk, scale deposits
- Shale: High pressure zones, mud invasion
- Dolomite: Fracture complexity, water cut
- Mudstone: Compaction, low permeability

Phase: Phase 1 - Formation-Specific Models
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import functools
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import logging
import time

logger = logging.getLogger(__name__)


class FormationType(str, Enum):
    SANDSTONE = "sandstone"
    LIMESTONE = "limestone"
    SHALE = "shale"
    DOLOMITE = "dolomite"
    MUDSTONE = "mudstone"


@dataclass
class WellContext:
    """Contextual information for a production well."""
    formation_type: FormationType
    well_depth_meters: float
    bottom_hole_temperature_celsius: float
    oil_viscosity_cst: float
    api_gravity: float
    producing_zone_pressure_bar: Optional[float] = None
    water_cut_percent: Optional[float] = None
    gas_oil_ratio: Optional[float] = None
    skin_factor: Optional[float] = None


@dataclass
class FormationModelMetadata:
    """Metadata about a formation-specific model."""
    formation_type: FormationType
    equipment_type: str
    power_source: str
    depth_range: Tuple[float, float]
    temperature_range: Tuple[float, float]
    viscosity_range: Tuple[float, float]
    sample_count: int
    accuracy: float
    feature_names: List[str]
    training_date: str


class FormationSpecificModelGenerator:
    """
    Generates synthetic training data and ML models specific to
    formation type, depth, temperature, and viscosity conditions.
    """
    
    FORMATION_EROSION_FACTORS = {
        FormationType.SANDSTONE: 1.4,
        FormationType.LIMESTONE: 0.9,
        FormationType.SHALE: 0.7,
        FormationType.DOLOMITE: 0.8,
        FormationType.MUDSTONE: 0.6,
    }
    
    FORMATION_CORROSION_FACTORS = {
        FormationType.SANDSTONE: 0.8,
        FormationType.LIMESTONE: 1.6,
        FormationType.SHALE: 0.6,
        FormationType.DOLOMITE: 1.2,
        FormationType.MUDSTONE: 0.5,
    }
    
    FORMATION_PRESSURE_SENSITIVITY = {
        FormationType.SANDSTONE: 1.0,
        FormationType.LIMESTONE: 0.8,
        FormationType.SHALE: 1.3,
        FormationType.DOLOMITE: 1.1,
        FormationType.MUDSTONE: 0.7,
    }
    
    def __init__(self):
        """Initialize the formation-specific model generator."""
        self.models_cache = {}
        
    def generate_pump_training_data(
        self,
        well_context: WellContext,
        n_samples: int = 800,
        power_source: str = "Electric"
    ) -> pd.DataFrame:
        """
        Generate synthetic training data for centrifugal pumps
        specific to well formation and operating conditions.
        
        Args:
            well_context: WellContext instance with formation/depth/temp data
            n_samples: Number of synthetic samples
            power_source: Power source type (Electric, Diesel, Steam, Gas)
            
        Returns:
            DataFrame with training data
        """
        np.random.seed(42)
        
        formation_erosion = self.FORMATION_EROSION_FACTORS[well_context.formation_type]
        formation_corrosion = self.FORMATION_CORROSION_FACTORS[well_context.formation_type]
        
        depth_factor = self._calculate_depth_factor(well_context.well_depth_meters)
        temp_factor = self._calculate_temperature_factor(well_context.bottom_hole_temperature_celsius)
        viscosity_factor = self._calculate_viscosity_factor(well_context.oil_viscosity_cst)
        
        discharge_temp = np.random.normal(55 + temp_factor * 20, 15, n_samples)
        discharge_temp = np.clip(discharge_temp, 30, 120)
        
        inlet_pressure = np.random.normal(1.2 + depth_factor * 0.5, 0.6, n_samples)
        inlet_pressure = np.clip(inlet_pressure, 0.3, 6)
        
        outlet_pressure = np.random.normal(20 + depth_factor * 10, 8, n_samples)
        outlet_pressure = np.clip(outlet_pressure, 5, 80)
        
        volumetric_flow = np.random.normal(180 * viscosity_factor ** -0.3, 40, n_samples)
        volumetric_flow = np.clip(volumetric_flow, 40, 400)
        
        available_npsh = np.random.normal(4 - depth_factor * 1.5, 1.5, n_samples)
        available_npsh = np.clip(available_npsh, 0.3, 10)
        
        if power_source == "Electric":
            motor_efficiency = np.random.normal(92 - temp_factor * 3, 3, n_samples)
            motor_efficiency = np.clip(motor_efficiency, 82, 98)
            
            winding_temp = np.random.normal(65 + temp_factor * 20, 15, n_samples)
            winding_temp = np.clip(winding_temp, 35, 120)
            
            phase_current = np.random.normal(15, 3, n_samples)
            phase_current = np.clip(phase_current, 5, 30)
            
            power_factor = np.random.normal(0.92, 0.05, n_samples)
            power_factor = np.clip(power_factor, 0.75, 0.99)
            
            temp_norm = discharge_temp / 120
            efficiency_norm = (100 - motor_efficiency) / 20
            winding_norm = winding_temp / 120
            cavitation_risk = np.maximum(0, (2.5 - available_npsh) / 2.5)
            erosion_risk = cavitation_risk * formation_erosion * viscosity_factor
            corrosion_risk = (temp_norm + winding_norm) / 2 * formation_corrosion
            
            failure_score = (
                temp_norm * 0.15 +
                efficiency_norm * 0.20 +
                winding_norm * 0.25 +
                cavitation_risk * 0.20 +
                erosion_risk * 0.12 +
                corrosion_risk * 0.08
            )
            
        elif power_source == "Diesel":
            fuel_consumption = np.random.normal(32 + depth_factor * 5, 8, n_samples)
            fuel_consumption = np.clip(fuel_consumption, 15, 60)
            
            engine_oil_temp = np.random.normal(82 + temp_factor * 15, 12, n_samples)
            engine_oil_temp = np.clip(engine_oil_temp, 60, 130)
            
            engine_oil_pressure = np.random.normal(3.0, 0.5, n_samples)
            engine_oil_pressure = np.clip(engine_oil_pressure, 1.5, 6)
            
            exhaust_temp = np.random.normal(450 + temp_factor * 50, 80, n_samples)
            exhaust_temp = np.clip(exhaust_temp, 300, 700)
            
            temp_norm = discharge_temp / 120
            oil_temp_norm = engine_oil_temp / 130
            combustion_efficiency = 1 - (exhaust_temp - 400) / 400
            erosion_risk = formation_erosion * viscosity_factor * (fuel_consumption / 50)
            lubrication_degradation = oil_temp_norm * temp_norm
            
            failure_score = (
                temp_norm * 0.15 +
                oil_temp_norm * 0.20 +
                (1 - combustion_efficiency) * 0.18 +
                erosion_risk * 0.15 +
                lubrication_degradation * 0.20 +
                (1 - engine_oil_pressure / 6) * 0.12
            )
            
        elif power_source == "Steam":
            inlet_steam_pressure = np.random.normal(8 + depth_factor * 1, 2, n_samples)
            inlet_steam_pressure = np.clip(inlet_steam_pressure, 3, 15)
            
            steam_temperature = np.random.normal(250 + temp_factor * 30, 30, n_samples)
            steam_temperature = np.clip(steam_temperature, 150, 400)
            
            condensate_temp = np.random.normal(70 + temp_factor * 15, 15, n_samples)
            condensate_temp = np.clip(condensate_temp, 30, 150)
            
            throttle_valve_position = np.random.uniform(20, 100, n_samples)
            
            temp_norm = discharge_temp / 120
            steam_quality_indicator = (steam_temperature - 150) / 250
            condensation_risk = 1 - steam_quality_indicator
            thermal_fatigue = np.abs(steam_temperature - condensate_temp) / 200
            corrosion_risk = formation_corrosion * (condensate_temp / 100)
            
            failure_score = (
                temp_norm * 0.12 +
                condensation_risk * 0.20 +
                thermal_fatigue * 0.22 +
                corrosion_risk * 0.18 +
                (1 - steam_quality_indicator) * 0.18 +
                (throttle_valve_position - 50) ** 2 / 2500 * 0.10
            )
            
        elif power_source == "Gas":
            air_fuel_ratio = np.random.normal(14.7, 2, n_samples)
            air_fuel_ratio = np.clip(air_fuel_ratio, 10, 20)
            
            intake_temp = np.random.normal(35 + temp_factor * 20, 10, n_samples)
            intake_temp = np.clip(intake_temp, 15, 80)
            
            knock_index = np.random.uniform(0, 100, n_samples)
            spark_energy_millijoules = np.random.normal(40, 15, n_samples)
            spark_energy_millijoules = np.clip(spark_energy_millijoules, 5, 100)
            
            temp_norm = discharge_temp / 120
            combustion_quality = 1 - np.abs(air_fuel_ratio - 14.7) / 14.7
            detonation_risk = knock_index / 100
            ignition_efficiency = spark_energy_millijoules / 100
            erosion_risk = detonation_risk * formation_erosion * viscosity_factor
            
            failure_score = (
                temp_norm * 0.14 +
                (1 - combustion_quality) * 0.18 +
                detonation_risk * 0.22 +
                (1 - ignition_efficiency) * 0.16 +
                erosion_risk * 0.18 +
                (intake_temp / 80) * 0.12
            )
        
        else:
            raise ValueError(f"Unknown power source: {power_source}")
        
        failure_score += np.random.normal(0, 0.04, n_samples)
        failure_score = np.clip(failure_score, 0, 1)
        
        failure_category = np.zeros(n_samples, dtype=int)
        failure_category[failure_score >= 0.35] = 1
        failure_category[failure_score >= 0.60] = 2
        
        if power_source == "Electric":
            return pd.DataFrame({
                'discharge_temperature': discharge_temp,
                'inlet_pressure': inlet_pressure,
                'outlet_pressure': outlet_pressure,
                'volumetric_flow': volumetric_flow,
                'motor_efficiency': motor_efficiency,
                'winding_temperature': winding_temp,
                'phase_current': phase_current,
                'power_factor': power_factor,
                'failure_category': failure_category,
                'failure_score': failure_score * 100
            })
        elif power_source == "Diesel":
            return pd.DataFrame({
                'discharge_temperature': discharge_temp,
                'inlet_pressure': inlet_pressure,
                'outlet_pressure': outlet_pressure,
                'volumetric_flow': volumetric_flow,
                'fuel_consumption': fuel_consumption,
                'engine_oil_temperature': engine_oil_temp,
                'engine_oil_pressure': engine_oil_pressure,
                'exhaust_temperature': exhaust_temp,
                'failure_category': failure_category,
                'failure_score': failure_score * 100
            })
        elif power_source == "Steam":
            return pd.DataFrame({
                'discharge_temperature': discharge_temp,
                'inlet_pressure': inlet_pressure,
                'outlet_pressure': outlet_pressure,
                'volumetric_flow': volumetric_flow,
                'inlet_steam_pressure': inlet_steam_pressure,
                'steam_temperature': steam_temperature,
                'condensate_temperature': condensate_temp,
                'throttle_valve_position': throttle_valve_position,
                'failure_category': failure_category,
                'failure_score': failure_score * 100
            })
        else:  # Gas
            return pd.DataFrame({
                'discharge_temperature': discharge_temp,
                'inlet_pressure': inlet_pressure,
                'outlet_pressure': outlet_pressure,
                'volumetric_flow': volumetric_flow,
                'air_fuel_ratio': air_fuel_ratio,
                'intake_temperature': intake_temp,
                'knock_index': knock_index,
                'spark_energy_millijoules': spark_energy_millijoules,
                'failure_category': failure_category,
                'failure_score': failure_score * 100
            })
    
    def generate_compressor_training_data(
        self,
        well_context: WellContext,
        n_samples: int = 800,
        power_source: str = "Electric"
    ) -> pd.DataFrame:
        """
        Generate synthetic training data for turbocompressors
        specific to formation and well conditions.
        """
        np.random.seed(42)
        
        formation_erosion = self.FORMATION_EROSION_FACTORS[well_context.formation_type]
        formation_corrosion = self.FORMATION_CORROSION_FACTORS[well_context.formation_type]
        pressure_sensitivity = self.FORMATION_PRESSURE_SENSITIVITY[well_context.formation_type]
        
        depth_factor = self._calculate_depth_factor(well_context.well_depth_meters)
        temp_factor = self._calculate_temperature_factor(well_context.bottom_hole_temperature_celsius)
        viscosity_factor = self._calculate_viscosity_factor(well_context.oil_viscosity_cst)
        
        discharge_temp = np.random.normal(85 + temp_factor * 25, 25, n_samples)
        discharge_temp = np.clip(discharge_temp, 30, 180)
        
        compression_ratio = np.random.normal(
            4.5 + depth_factor * 2 * pressure_sensitivity,
            1.5,
            n_samples
        )
        compression_ratio = np.clip(compression_ratio, 1.5, 12)
        
        radial_vibration = np.random.exponential(1.5 * formation_erosion, n_samples)
        radial_vibration = np.clip(radial_vibration, 0.1, 12)
        
        axial_vibration = np.random.exponential(1.2 * formation_erosion, n_samples)
        axial_vibration = np.clip(axial_vibration, 0.05, 10)
        
        relative_humidity = np.random.normal(50, 20, n_samples)
        relative_humidity = np.clip(relative_humidity, 10, 95)
        
        if power_source == "Electric":
            motor_efficiency = np.random.normal(90 - temp_factor * 2, 3, n_samples)
            motor_efficiency = np.clip(motor_efficiency, 80, 96)
            
            winding_temp = np.random.normal(70 + temp_factor * 20, 15, n_samples)
            winding_temp = np.clip(winding_temp, 40, 130)
            
            phase_current = np.random.normal(18, 4, n_samples)
            phase_current = np.clip(phase_current, 8, 35)
            
            temp_norm = discharge_temp / 180
            efficiency_norm = (100 - motor_efficiency) / 20
            vibration_norm = (radial_vibration + axial_vibration) / 20
            humidity_risk = np.abs(relative_humidity - 50) / 50
            winding_norm = winding_temp / 130
            corrosion_from_humidity = formation_corrosion * (relative_humidity / 100)
            
            failure_score = (
                temp_norm * 0.16 +
                efficiency_norm * 0.18 +
                vibration_norm * 0.22 +
                humidity_risk * 0.15 +
                winding_norm * 0.16 +
                corrosion_from_humidity * 0.17
            )
            
        elif power_source == "Diesel":
            fuel_consumption = np.random.normal(35 + depth_factor * 6, 9, n_samples)
            fuel_consumption = np.clip(fuel_consumption, 18, 70)
            
            engine_oil_temp = np.random.normal(85 + temp_factor * 18, 12, n_samples)
            engine_oil_temp = np.clip(engine_oil_temp, 60, 140)
            
            engine_oil_pressure = np.random.normal(3.2, 0.6, n_samples)
            engine_oil_pressure = np.clip(engine_oil_pressure, 1.5, 7)
            
            temp_norm = discharge_temp / 180
            vibration_norm = (radial_vibration + axial_vibration) / 20
            oil_temp_norm = engine_oil_temp / 140
            combustion_stress = (fuel_consumption / 50) * compression_ratio / 6
            bearing_stress = vibration_norm * oil_temp_norm
            erosion_from_fuel = formation_erosion * (fuel_consumption / 50)
            
            failure_score = (
                temp_norm * 0.14 +
                vibration_norm * 0.20 +
                oil_temp_norm * 0.18 +
                combustion_stress * 0.16 +
                bearing_stress * 0.18 +
                erosion_from_fuel * 0.14
            )
            
        elif power_source == "Steam":
            inlet_steam_pressure = np.random.normal(9 + depth_factor * 1.5, 2, n_samples)
            inlet_steam_pressure = np.clip(inlet_steam_pressure, 4, 18)
            
            steam_temperature = np.random.normal(280 + temp_factor * 40, 40, n_samples)
            steam_temperature = np.clip(steam_temperature, 150, 450)
            
            condensate_temp = np.random.normal(80 + temp_factor * 20, 15, n_samples)
            condensate_temp = np.clip(condensate_temp, 40, 160)
            
            throttle_position = np.random.uniform(15, 100, n_samples)
            
            temp_norm = discharge_temp / 180
            vibration_norm = (radial_vibration + axial_vibration) / 20
            steam_quality = (steam_temperature - 150) / 300
            condensation_risk = 1 - steam_quality
            thermal_stress = np.abs(steam_temperature - condensate_temp) / 250
            corrosion_from_condensate = formation_corrosion * (condensate_temp / 160)
            
            failure_score = (
                temp_norm * 0.13 +
                vibration_norm * 0.19 +
                condensation_risk * 0.22 +
                thermal_stress * 0.20 +
                corrosion_from_condensate * 0.16 +
                (1 - steam_quality) * 0.10
            )
            
        elif power_source == "Gas":
            air_fuel_ratio = np.random.normal(14.7, 2, n_samples)
            air_fuel_ratio = np.clip(air_fuel_ratio, 11, 19)
            
            intake_temp = np.random.normal(40 + temp_factor * 20, 12, n_samples)
            intake_temp = np.clip(intake_temp, 15, 100)
            
            knock_index = np.random.uniform(0, 100, n_samples)
            turbine_inlet_temp = np.random.normal(650 + temp_factor * 50, 80, n_samples)
            turbine_inlet_temp = np.clip(turbine_inlet_temp, 400, 900)
            
            temp_norm = discharge_temp / 180
            vibration_norm = (radial_vibration + axial_vibration) / 20
            combustion_quality = 1 - np.abs(air_fuel_ratio - 14.7) / 14.7
            detonation_risk = knock_index / 100
            thermal_stress_turbine = (turbine_inlet_temp - 500) / 400
            erosion_from_detonation = formation_erosion * detonation_risk
            
            failure_score = (
                temp_norm * 0.14 +
                vibration_norm * 0.20 +
                (1 - combustion_quality) * 0.16 +
                detonation_risk * 0.18 +
                thermal_stress_turbine * 0.18 +
                erosion_from_detonation * 0.14
            )
        
        else:
            raise ValueError(f"Unknown power source: {power_source}")
        
        failure_score += np.random.normal(0, 0.04, n_samples)
        failure_score = np.clip(failure_score, 0, 1)
        
        failure_category = np.zeros(n_samples, dtype=int)
        failure_category[failure_score >= 0.35] = 1
        failure_category[failure_score >= 0.60] = 2
        
        base_data = {
            'discharge_temperature': discharge_temp,
            'compression_ratio': compression_ratio,
            'radial_vibration': radial_vibration,
            'axial_vibration': axial_vibration,
            'relative_humidity': relative_humidity,
            'failure_category': failure_category,
            'failure_score': failure_score * 100
        }
        
        if power_source == "Electric":
            base_data.update({
                'motor_efficiency': motor_efficiency,
                'winding_temperature': winding_temp,
                'phase_current': phase_current,
            })
        elif power_source == "Diesel":
            base_data.update({
                'fuel_consumption': fuel_consumption,
                'engine_oil_temperature': engine_oil_temp,
                'engine_oil_pressure': engine_oil_pressure,
            })
        elif power_source == "Steam":
            base_data.update({
                'inlet_steam_pressure': inlet_steam_pressure,
                'steam_temperature': steam_temperature,
                'condensate_temperature': condensate_temp,
                'throttle_position': throttle_position,
            })
        else:  # Gas
            base_data.update({
                'air_fuel_ratio': air_fuel_ratio,
                'intake_temperature': intake_temp,
                'knock_index': knock_index,
                'turbine_inlet_temperature': turbine_inlet_temp,
            })
        
        return pd.DataFrame(base_data)
    
    @staticmethod
    def _calculate_depth_factor(depth_meters: float) -> float:
        """Calculate operational stress factor from well depth."""
        if depth_meters < 1000:
            return 0.2
        elif depth_meters < 2000:
            return 0.4
        elif depth_meters < 3000:
            return 0.6
        elif depth_meters < 4000:
            return 0.8
        else:
            return 1.0
    
    @staticmethod
    def _calculate_temperature_factor(bottom_hole_temp: float) -> float:
        """Calculate thermal stress factor from bottom-hole temperature."""
        if bottom_hole_temp < 40:
            return 0.0
        elif bottom_hole_temp < 60:
            return 0.2
        elif bottom_hole_temp < 90:
            return 0.4
        elif bottom_hole_temp < 120:
            return 0.6
        elif bottom_hole_temp < 150:
            return 0.8
        else:
            return 1.0
    
    @staticmethod
    def _calculate_viscosity_factor(oil_viscosity_cst: float) -> float:
        """Calculate viscosity correction factor for flow rates and efficiency."""
        if oil_viscosity_cst < 10:
            return 0.8
        elif oil_viscosity_cst < 50:
            return 0.9
        elif oil_viscosity_cst < 100:
            return 1.0
        elif oil_viscosity_cst < 500:
            return 1.1
        else:
            return 1.2
    
    @functools.lru_cache(maxsize=128)
    def train_formation_model(
        self,
        well_context: WellContext,
        equipment_type: str,
        power_source: str
    ) -> Tuple[Any, StandardScaler, float, List[str]]:
        """
        Train a formation-specific model.
        
        Args:
            well_context: WellContext with formation/depth/temp
            equipment_type: 'pump' or 'compressor'
            power_source: 'Electric', 'Diesel', 'Steam', 'Gas'
            
        Returns:
            Tuple of (model, scaler, accuracy, feature_names)
        """
        cache_key = f"{well_context.formation_type}_{equipment_type}_{power_source}"
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]
        
        try:
            start_time = time.time()
            
            if equipment_type == "pump":
                df = self.generate_pump_training_data(well_context, power_source=power_source)
            elif equipment_type == "compressor":
                df = self.generate_compressor_training_data(well_context, power_source=power_source)
            else:
                raise ValueError(f"Unknown equipment type: {equipment_type}")
            
            X = df.drop(['failure_category', 'failure_score'], axis=1)
            y = df['failure_category']
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            base_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                n_iter_no_change=10,
                validation_fraction=0.1
            )
            
            model = CalibratedClassifierCV(base_model, cv=5)
            model.fit(X_train_scaled, y_train)
            
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            training_time = time.time() - start_time
            
            result = (model, scaler, accuracy, list(X.columns))
            self.models_cache[cache_key] = result
            
            logger.info(
                f"Formation model trained: {well_context.formation_type} - "
                f"{equipment_type} - {power_source} "
                f"(Accuracy: {accuracy:.2%}, Time: {training_time:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error training formation model: {str(e)}")
            raise


def get_formation_model_generator() -> FormationSpecificModelGenerator:
    """Get singleton instance of formation model generator."""
    if not hasattr(get_formation_model_generator, "_instance"):
        get_formation_model_generator._instance = FormationSpecificModelGenerator()
    return get_formation_model_generator._instance
