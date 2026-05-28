"""
Power Source Independent Analysis Module
Extends failure_prediction_engine with specialized models per power source.

This module implements independent ML models for each power source:
- Electric: Low thermal stress, high efficiency, electrical faults
- Diesel: Fuel quality, combustion efficiency, lubrication issues
- Steam: Condensation, thermal fatigue, throttling valve problems
- Gas: Fuel variability, temperature control, detonation risk

Each equipment type (pump, compressor, turbine) has specialized parameters
for each power source, enabling truly independent analysis.

Phase: Phase 5 - Oil & Gas Digital Twin Enhancement
"""

import functools
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import time
import logging
from typing import Tuple, Dict

from .config import RISK_LOW_THRESHOLD, RISK_HIGH_THRESHOLD
from .audit_logging_service import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()


# ============================================================================
# PUMP - Power Source Specific Training Data Generators
# ============================================================================

def generate_pump_electric_training_data(n_samples=800):
    """
    Generate synthetic training data for Electric-powered Centrifugal Pumps.
    
    Electric-specific parameters:
    - Motor efficiency (%), electrical current (A), power factor
    - Bearing temperature, winding temperature
    - Electrical fault indicators: phase imbalance, harmonic distortion
    
    Failure modes:
    - Motor winding degradation (insulation breakdown)
    - Bearing overheating
    - Impeller cavitation (low inlet pressure)
    - Seal leakage
    """
    np.random.seed(42)
    
    # Pump hydraulic parameters
    temp_descarga = np.random.normal(55, 15, n_samples)
    temp_descarga = np.clip(temp_descarga, 30, 90)
    
    presion_entrada = np.random.normal(1.2, 0.6, n_samples)
    presion_entrada = np.clip(presion_entrada, 0.3, 4)
    
    flujo_volumetrico = np.random.normal(180, 40, n_samples)
    flujo_volumetrico = np.clip(flujo_volumetrico, 80, 300)
    
    # Electric-specific parameters
    eficiencia_motor = np.random.normal(92, 3, n_samples)
    eficiencia_motor = np.clip(eficiencia_motor, 85, 98)
    
    temperatura_devanado = np.random.normal(65, 15, n_samples)
    temperatura_devanado = np.clip(temperatura_devanado, 40, 100)
    
    corriente_fase = np.random.normal(15, 3, n_samples)
    corriente_fase = np.clip(corriente_fase, 8, 25)
    
    factor_potencia = np.random.normal(0.92, 0.05, n_samples)
    factor_potencia = np.clip(factor_potencia, 0.80, 0.99)
    
    # Failure logic for electric pumps
    temp_norm = temp_descarga / 90
    presion_norm = presion_entrada / 4
    eficiencia_norm = (100 - eficiencia_motor) / 15  # Higher = worse
    devanado_norm = temperatura_devanado / 100
    corriente_norm = corriente_fase / 25
    factor_potencia_norm = (1.0 - factor_potencia) / 0.2  # Lower = worse
    
    failure_score = (
        temp_norm * 0.15 +
        presion_norm * 0.10 +
        eficiencia_norm * 0.20 +
        devanado_norm * 0.25 +
        corriente_norm * 0.15 +
        factor_potencia_norm * 0.15
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'presion_entrada': presion_entrada,
        'flujo_volumetrico': flujo_volumetrico,
        'eficiencia_motor': eficiencia_motor,
        'temperatura_devanado': temperatura_devanado,
        'corriente_fase': corriente_fase,
        'factor_potencia': factor_potencia,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_pump_diesel_training_data(n_samples=800):
    """
    Generate synthetic training data for Diesel-powered Centrifugal Pumps.
    
    Diesel-specific parameters:
    - Fuel consumption rate (L/h), combustion efficiency (%)
    - Engine oil temperature, pressure
    - Exhaust temperature, smoke density
    - Engine load (%), RPM variation
    
    Failure modes:
    - Fuel injection problems (poor atomization)
    - Lubrication degradation (soot contamination)
    - Thermal stress (hot spots)
    - Vibration induced by combustion
    """
    np.random.seed(42)
    
    # Pump hydraulic parameters
    temp_descarga = np.random.normal(65, 18, n_samples)
    temp_descarga = np.clip(temp_descarga, 35, 105)
    
    presion_entrada = np.random.normal(1.5, 0.7, n_samples)
    presion_entrada = np.clip(presion_entrada, 0.4, 5)
    
    flujo_volumetrico = np.random.normal(170, 45, n_samples)
    flujo_volumetrico = np.clip(flujo_volumetrico, 70, 300)
    
    # Diesel engine-specific parameters
    consumo_combustible = np.random.normal(28, 6, n_samples)
    consumo_combustible = np.clip(consumo_combustible, 15, 45)
    
    temperatura_aceite_motor = np.random.normal(78, 12, n_samples)
    temperatura_aceite_motor = np.clip(temperatura_aceite_motor, 55, 105)
    
    presion_aceite_motor = np.random.normal(2.8, 0.5, n_samples)
    presion_aceite_motor = np.clip(presion_aceite_motor, 1.5, 4.5)
    
    temperatura_escape = np.random.normal(420, 60, n_samples)
    temperatura_escape = np.clip(temperatura_escape, 300, 550)
    
    # Failure logic for diesel pumps
    temp_norm = temp_descarga / 105
    presion_norm = presion_entrada / 5
    combustible_norm = consumo_combustible / 45
    aceite_temp_norm = temperatura_aceite_motor / 105
    aceite_presion_norm = (4.5 - presion_aceite_motor) / 3  # Low pressure = bad
    escape_norm = temperatura_escape / 550
    
    failure_score = (
        temp_norm * 0.15 +
        presion_norm * 0.10 +
        combustible_norm * 0.20 +
        aceite_temp_norm * 0.20 +
        aceite_presion_norm * 0.20 +
        escape_norm * 0.15
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'presion_entrada': presion_entrada,
        'flujo_volumetrico': flujo_volumetrico,
        'consumo_combustible': consumo_combustible,
        'temperatura_aceite_motor': temperatura_aceite_motor,
        'presion_aceite_motor': presion_aceite_motor,
        'temperatura_escape': temperatura_escape,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_pump_steam_training_data(n_samples=800):
    """
    Generate synthetic training data for Steam-powered Centrifugal Pumps.
    
    Steam turbine-specific parameters:
    - Inlet steam pressure (bar), temperature (°C)
    - Outlet condensate temperature, quality
    - Throttle valve position (%)
    - Condenser effectiveness
    
    Failure modes:
    - Condensation in turbine (water droplets)
    - Throttling valve erosion
    - Bearings dry-out (loss of steam lubrication)
    - Thermal expansion mismatch
    """
    np.random.seed(42)
    
    # Pump hydraulic parameters
    temp_descarga = np.random.normal(48, 12, n_samples)
    temp_descarga = np.clip(temp_descarga, 25, 75)
    
    presion_entrada = np.random.normal(1.0, 0.5, n_samples)
    presion_entrada = np.clip(presion_entrada, 0.2, 3)
    
    flujo_volumetrico = np.random.normal(160, 40, n_samples)
    flujo_volumetrico = np.clip(flujo_volumetrico, 70, 280)
    
    # Steam turbine-specific parameters
    presion_vapor_entrada = np.random.normal(25, 5, n_samples)
    presion_vapor_entrada = np.clip(presion_vapor_entrada, 15, 40)
    
    temperatura_vapor = np.random.normal(300, 30, n_samples)
    temperatura_vapor = np.clip(temperatura_vapor, 250, 380)
    
    temperatura_condensado = np.random.normal(45, 15, n_samples)
    temperatura_condensado = np.clip(temperatura_condensado, 20, 80)
    
    posicion_valvula_estrangulacion = np.random.normal(75, 15, n_samples)
    posicion_valvula_estrangulacion = np.clip(posicion_valvula_estrangulacion, 30, 100)
    
    # Failure logic for steam pumps
    temp_norm = temp_descarga / 75
    presion_norm = presion_entrada / 3
    vapor_presion_norm = (40 - presion_vapor_entrada) / 25  # Low steam pressure = bad
    vapor_temp_norm = (temperatura_vapor - 250) / 130
    condensado_norm = temperatura_condensado / 80
    valvula_norm = (100 - posicion_valvula_estrangulacion) / 70  # Throttling increases stress
    
    failure_score = (
        temp_norm * 0.10 +
        presion_norm * 0.10 +
        vapor_presion_norm * 0.25 +
        vapor_temp_norm * 0.15 +
        condensado_norm * 0.20 +
        valvula_norm * 0.20
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'presion_entrada': presion_entrada,
        'flujo_volumetrico': flujo_volumetrico,
        'presion_vapor_entrada': presion_vapor_entrada,
        'temperatura_vapor': temperatura_vapor,
        'temperatura_condensado': temperatura_condensado,
        'posicion_valvula_estrangulacion': posicion_valvula_estrangulacion,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_pump_gas_training_data(n_samples=800):
    """
    Generate synthetic training data for Gas-powered Centrifugal Pumps.
    
    Gas engine-specific parameters:
    - Gas pressure (bar), temperature (°C)
    - Engine air-fuel ratio
    - Spark plug condition (gap, fouling)
    - Knocking index, ignition timing
    
    Failure modes:
    - Detonation (pre-ignition)
    - Lean/rich fuel mixture
    - Spark plug fouling
    - Thermal runaway
    """
    np.random.seed(42)
    
    # Pump hydraulic parameters
    temp_descarga = np.random.normal(62, 16, n_samples)
    temp_descarga = np.clip(temp_descarga, 32, 100)
    
    presion_entrada = np.random.normal(1.4, 0.6, n_samples)
    presion_entrada = np.clip(presion_entrada, 0.35, 4.5)
    
    flujo_volumetrico = np.random.normal(175, 42, n_samples)
    flujo_volumetrico = np.clip(flujo_volumetrico, 75, 295)
    
    # Gas engine-specific parameters
    relacion_aire_combustible = np.random.normal(14.7, 1.5, n_samples)
    relacion_aire_combustible = np.clip(relacion_aire_combustible, 12, 18)
    
    temperatura_aire_admision = np.random.normal(35, 8, n_samples)
    temperatura_aire_admision = np.clip(temperatura_aire_admision, 20, 55)
    
    indice_detonacion = np.random.uniform(0, 100, n_samples)
    indice_detonacion = np.clip(indice_detonacion, 0, 100)
    
    energia_chispa = np.random.normal(0.85, 0.1, n_samples)
    energia_chispa = np.clip(energia_chispa, 0.5, 1.0)
    
    # Failure logic for gas pumps
    temp_norm = temp_descarga / 100
    presion_norm = presion_entrada / 4.5
    aire_combustible_deviation = np.abs((relacion_aire_combustible - 14.7) / 5.3) / 1.0
    aire_temp_norm = temperatura_aire_admision / 55
    detonacion_norm = indice_detonacion / 100
    chispa_norm = (1.0 - energia_chispa) / 0.5  # Lower energy = worse
    
    failure_score = (
        temp_norm * 0.15 +
        presion_norm * 0.10 +
        aire_combustible_deviation * 0.25 +
        aire_temp_norm * 0.15 +
        detonacion_norm * 0.20 +
        chispa_norm * 0.15
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'presion_entrada': presion_entrada,
        'flujo_volumetrico': flujo_volumetrico,
        'relacion_aire_combustible': relacion_aire_combustible,
        'temperatura_aire_admision': temperatura_aire_admision,
        'indice_detonacion': indice_detonacion,
        'energia_chispa': energia_chispa,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


# ============================================================================
# PUMP MODEL TRAINING FUNCTIONS (Per Power Source)
# ============================================================================

@functools.lru_cache(maxsize=1)
def train_pump_electric_model():
    """Train specialized Calibrated Gradient Boosting model for Electric pumps"""
    start_time = time.time()
    audit_logger.log_system("Training electric pump model", action="MODEL_TRAIN_PUMP_ELECTRIC")
    
    try:
        data = generate_pump_electric_training_data(800)
        feature_columns = ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                          'eficiencia_motor', 'temperatura_devanado', 'corriente_fase', 'factor_potencia']
        
        X = data[feature_columns].values
        y = data['failure_category'].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        
        duration = time.time() - start_time
        audit_logger.log_system(f"Electric pump model trained: {accuracy:.2%}", action="MODEL_READY_PUMP_ELECTRIC")
        
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_pump_electric_model")
        raise


@functools.lru_cache(maxsize=1)
def train_pump_diesel_model():
    """Train specialized Calibrated Gradient Boosting model for Diesel pumps"""
    start_time = time.time()
    audit_logger.log_system("Training diesel pump model", action="MODEL_TRAIN_PUMP_DIESEL")
    
    try:
        data = generate_pump_diesel_training_data(800)
        feature_columns = ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                          'consumo_combustible', 'temperatura_aceite_motor', 'presion_aceite_motor', 'temperatura_escape']
        
        X = data[feature_columns].values
        y = data['failure_category'].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        
        duration = time.time() - start_time
        audit_logger.log_system(f"Diesel pump model trained: {accuracy:.2%}", action="MODEL_READY_PUMP_DIESEL")
        
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_pump_diesel_model")
        raise


@functools.lru_cache(maxsize=1)
def train_pump_steam_model():
    """Train specialized Calibrated Gradient Boosting model for Steam pumps"""
    start_time = time.time()
    audit_logger.log_system("Training steam pump model", action="MODEL_TRAIN_PUMP_STEAM")
    
    try:
        data = generate_pump_steam_training_data(800)
        feature_columns = ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                          'presion_vapor_entrada', 'temperatura_vapor', 'temperatura_condensado', 'posicion_valvula_estrangulacion']
        
        X = data[feature_columns].values
        y = data['failure_category'].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        
        duration = time.time() - start_time
        audit_logger.log_system(f"Steam pump model trained: {accuracy:.2%}", action="MODEL_READY_PUMP_STEAM")
        
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_pump_steam_model")
        raise


@functools.lru_cache(maxsize=1)
def train_pump_gas_model():
    """Train specialized Calibrated Gradient Boosting model for Gas pumps"""
    start_time = time.time()
    audit_logger.log_system("Training gas pump model", action="MODEL_TRAIN_PUMP_GAS")
    
    try:
        data = generate_pump_gas_training_data(800)
        feature_columns = ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                          'relacion_aire_combustible', 'temperatura_aire_admision', 'indice_detonacion', 'energia_chispa']
        
        X = data[feature_columns].values
        y = data['failure_category'].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        
        duration = time.time() - start_time
        audit_logger.log_system(f"Gas pump model trained: {accuracy:.2%}", action="MODEL_READY_PUMP_GAS")
        
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_pump_gas_model")
        raise


# ============================================================================
# MODEL REGISTRY - Easy access to all power source models
# ============================================================================

PUMP_POWER_SOURCE_MODELS = {
    'Electric': train_pump_electric_model,
    'Diesel': train_pump_diesel_model,
    'Steam': train_pump_steam_model,
    'Gas': train_pump_gas_model,
}

PUMP_DATA_GENERATORS = {
    'Electric': generate_pump_electric_training_data,
    'Diesel': generate_pump_diesel_training_data,
    'Steam': generate_pump_steam_training_data,
    'Gas': generate_pump_gas_training_data,
}

def get_pump_model_for_power_source(power_source: str):
    """Load the appropriate pump model for a given power source"""
    if power_source not in PUMP_POWER_SOURCE_MODELS:
        raise ValueError(f"Unknown power source: {power_source}")
    return PUMP_POWER_SOURCE_MODELS[power_source]()

def get_pump_features_for_power_source(power_source: str) -> list:
    """Get feature column names for pump with given power source"""
    generators = {
        'Electric': ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico', 
                     'eficiencia_motor', 'temperatura_devanado', 'corriente_fase', 'factor_potencia'],
        'Diesel': ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                   'consumo_combustible', 'temperatura_aceite_motor', 'presion_aceite_motor', 'temperatura_escape'],
        'Steam': ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                  'presion_vapor_entrada', 'temperatura_vapor', 'temperatura_condensado', 'posicion_valvula_estrangulacion'],
        'Gas': ['temperatura_descarga', 'presion_entrada', 'flujo_volumetrico',
                'relacion_aire_combustible', 'temperatura_aire_admision', 'indice_detonacion', 'energia_chispa']
    }
    return generators.get(power_source, [])


# ============================================================================
# COMPRESSOR - Power Source Specific Training Data Generators
# ============================================================================

def generate_compressor_electric_training_data(n_samples=800):
    """Generate training data for Electric-powered Turbocompressors"""
    np.random.seed(42)
    
    temp_descarga = np.random.normal(95, 25, n_samples)
    temp_descarga = np.clip(temp_descarga, 40, 160)
    
    ratio_compresion = np.random.normal(4.2, 1.3, n_samples)
    ratio_compresion = np.clip(ratio_compresion, 1.8, 9)
    
    vibracion_radial = np.random.exponential(1.4, n_samples)
    vibracion_radial = np.clip(vibracion_radial, 0.3, 7)
    
    vibracion_axial = np.random.exponential(1.1, n_samples)
    vibracion_axial = np.clip(vibracion_axial, 0.2, 5)
    
    eficiencia_motor = np.random.normal(91, 3.5, n_samples)
    eficiencia_motor = np.clip(eficiencia_motor, 84, 97)
    
    temperatura_devanado = np.random.normal(68, 16, n_samples)
    temperatura_devanado = np.clip(temperatura_devanado, 40, 105)
    
    corriente_fase = np.random.normal(18, 4, n_samples)
    corriente_fase = np.clip(corriente_fase, 10, 30)
    
    temp_norm = temp_descarga / 160
    ratio_norm = (ratio_compresion - 1.8) / 7.2
    vib_radial_norm = vibracion_radial / 7
    vib_axial_norm = vibracion_axial / 5
    eficiencia_norm = (100 - eficiencia_motor) / 16
    devanado_norm = temperatura_devanado / 105
    corriente_norm = corriente_fase / 30
    
    failure_score = (
        temp_norm * 0.18 + ratio_norm * 0.12 + vib_radial_norm * 0.28 +
        vib_axial_norm * 0.22 + eficiencia_norm * 0.10 + devanado_norm * 0.06 + corriente_norm * 0.04
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'ratio_compresion': ratio_compresion,
        'vibracion_radial': vibracion_radial,
        'vibracion_axial': vibracion_axial,
        'eficiencia_motor': eficiencia_motor,
        'temperatura_devanado': temperatura_devanado,
        'corriente_fase': corriente_fase,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_compressor_diesel_training_data(n_samples=800):
    """Generate training data for Diesel-powered Turbocompressors"""
    np.random.seed(42)
    
    temp_descarga = np.random.normal(105, 28, n_samples)
    temp_descarga = np.clip(temp_descarga, 45, 175)
    
    ratio_compresion = np.random.normal(4.5, 1.4, n_samples)
    ratio_compresion = np.clip(ratio_compresion, 2, 10)
    
    vibracion_radial = np.random.exponential(1.6, n_samples)
    vibracion_radial = np.clip(vibracion_radial, 0.4, 8)
    
    vibracion_axial = np.random.exponential(1.3, n_samples)
    vibracion_axial = np.clip(vibracion_axial, 0.25, 6)
    
    consumo_combustible = np.random.normal(32, 7, n_samples)
    consumo_combustible = np.clip(consumo_combustible, 18, 50)
    
    temperatura_aceite_motor = np.random.normal(82, 14, n_samples)
    temperatura_aceite_motor = np.clip(temperatura_aceite_motor, 60, 110)
    
    presion_aceite_motor = np.random.normal(3.0, 0.6, n_samples)
    presion_aceite_motor = np.clip(presion_aceite_motor, 1.6, 4.8)
    
    temp_norm = temp_descarga / 175
    ratio_norm = (ratio_compresion - 2) / 8
    vib_radial_norm = vibracion_radial / 8
    vib_axial_norm = vibracion_axial / 6
    combustible_norm = consumo_combustible / 50
    aceite_temp_norm = temperatura_aceite_motor / 110
    aceite_presion_norm = (4.8 - presion_aceite_motor) / 3.2
    
    failure_score = (
        temp_norm * 0.20 + ratio_norm * 0.14 + vib_radial_norm * 0.26 +
        vib_axial_norm * 0.20 + combustible_norm * 0.10 + aceite_temp_norm * 0.06 + aceite_presion_norm * 0.04
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'ratio_compresion': ratio_compresion,
        'vibracion_radial': vibracion_radial,
        'vibracion_axial': vibracion_axial,
        'consumo_combustible': consumo_combustible,
        'temperatura_aceite_motor': temperatura_aceite_motor,
        'presion_aceite_motor': presion_aceite_motor,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_compressor_steam_training_data(n_samples=800):
    """Generate training data for Steam-powered Turbocompressors"""
    np.random.seed(42)
    
    temp_descarga = np.random.normal(88, 22, n_samples)
    temp_descarga = np.clip(temp_descarga, 38, 150)
    
    ratio_compresion = np.random.normal(4.0, 1.2, n_samples)
    ratio_compresion = np.clip(ratio_compresion, 1.7, 8.5)
    
    vibracion_radial = np.random.exponential(1.3, n_samples)
    vibracion_radial = np.clip(vibracion_radial, 0.3, 6.5)
    
    vibracion_axial = np.random.exponential(1.0, n_samples)
    vibracion_axial = np.clip(vibracion_axial, 0.2, 4.8)
    
    presion_vapor_entrada = np.random.normal(22, 4.5, n_samples)
    presion_vapor_entrada = np.clip(presion_vapor_entrada, 12, 38)
    
    temperatura_vapor = np.random.normal(280, 35, n_samples)
    temperatura_vapor = np.clip(temperatura_vapor, 240, 360)
    
    temperatura_condensado = np.random.normal(48, 16, n_samples)
    temperatura_condensado = np.clip(temperatura_condensado, 25, 85)
    
    temp_norm = temp_descarga / 150
    ratio_norm = (ratio_compresion - 1.7) / 6.8
    vib_radial_norm = vibracion_radial / 6.5
    vib_axial_norm = vibracion_axial / 4.8
    vapor_presion_norm = (38 - presion_vapor_entrada) / 26
    vapor_temp_norm = (temperatura_vapor - 240) / 120
    condensado_norm = temperatura_condensado / 85
    
    failure_score = (
        temp_norm * 0.15 + ratio_norm * 0.12 + vib_radial_norm * 0.25 +
        vib_axial_norm * 0.18 + vapor_presion_norm * 0.16 + vapor_temp_norm * 0.08 + condensado_norm * 0.06
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'ratio_compresion': ratio_compresion,
        'vibracion_radial': vibracion_radial,
        'vibracion_axial': vibracion_axial,
        'presion_vapor_entrada': presion_vapor_entrada,
        'temperatura_vapor': temperatura_vapor,
        'temperatura_condensado': temperatura_condensado,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_compressor_gas_training_data(n_samples=800):
    """Generate training data for Gas-powered Turbocompressors"""
    np.random.seed(42)
    
    temp_descarga = np.random.normal(100, 26, n_samples)
    temp_descarga = np.clip(temp_descarga, 42, 168)
    
    ratio_compresion = np.random.normal(4.3, 1.35, n_samples)
    ratio_compresion = np.clip(ratio_compresion, 1.9, 9.5)
    
    vibracion_radial = np.random.exponential(1.5, n_samples)
    vibracion_radial = np.clip(vibracion_radial, 0.35, 7.5)
    
    vibracion_axial = np.random.exponential(1.15, n_samples)
    vibracion_axial = np.clip(vibracion_axial, 0.22, 5.5)
    
    relacion_aire_combustible = np.random.normal(15.2, 1.6, n_samples)
    relacion_aire_combustible = np.clip(relacion_aire_combustible, 12.5, 18)
    
    temperatura_aire_admision = np.random.normal(38, 9, n_samples)
    temperatura_aire_admision = np.clip(temperatura_aire_admision, 22, 60)
    
    indice_detonacion = np.random.uniform(5, 95, n_samples)
    
    temp_norm = temp_descarga / 168
    ratio_norm = (ratio_compresion - 1.9) / 7.6
    vib_radial_norm = vibracion_radial / 7.5
    vib_axial_norm = vibracion_axial / 5.5
    aire_combustible_dev = np.abs((relacion_aire_combustible - 15.2) / 5.5)
    aire_temp_norm = temperatura_aire_admision / 60
    detonacion_norm = indice_detonacion / 100
    
    failure_score = (
        temp_norm * 0.18 + ratio_norm * 0.13 + vib_radial_norm * 0.27 +
        vib_axial_norm * 0.20 + aire_combustible_dev * 0.12 + aire_temp_norm * 0.06 + detonacion_norm * 0.04
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    return pd.DataFrame({
        'temperatura_descarga': temp_descarga,
        'ratio_compresion': ratio_compresion,
        'vibracion_radial': vibracion_radial,
        'vibracion_axial': vibracion_axial,
        'relacion_aire_combustible': relacion_aire_combustible,
        'temperatura_aire_admision': temperatura_aire_admision,
        'indice_detonacion': indice_detonacion,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


# ============================================================================
# COMPRESSOR MODEL TRAINING FUNCTIONS (Per Power Source)
# ============================================================================

@functools.lru_cache(maxsize=1)
def train_compressor_electric_model():
    """Train specialized model for Electric compressors"""
    start_time = time.time()
    audit_logger.log_system("Training electric compressor model", action="MODEL_TRAIN_COMPRESSOR_ELECTRIC")
    try:
        data = generate_compressor_electric_training_data(800)
        feature_columns = ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial',
                          'vibracion_axial', 'eficiencia_motor', 'temperatura_devanado', 'corriente_fase']
        X = data[feature_columns].values
        y = data['failure_category'].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        audit_logger.log_system(f"Electric compressor model trained: {accuracy:.2%}", action="MODEL_READY_COMPRESSOR_ELECTRIC")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_compressor_electric_model")
        raise

@functools.lru_cache(maxsize=1)
def train_compressor_diesel_model():
    """Train specialized model for Diesel compressors"""
    start_time = time.time()
    audit_logger.log_system("Training diesel compressor model", action="MODEL_TRAIN_COMPRESSOR_DIESEL")
    try:
        data = generate_compressor_diesel_training_data(800)
        feature_columns = ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial',
                          'vibracion_axial', 'consumo_combustible', 'temperatura_aceite_motor', 'presion_aceite_motor']
        X = data[feature_columns].values
        y = data['failure_category'].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        audit_logger.log_system(f"Diesel compressor model trained: {accuracy:.2%}", action="MODEL_READY_COMPRESSOR_DIESEL")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_compressor_diesel_model")
        raise

@functools.lru_cache(maxsize=1)
def train_compressor_steam_model():
    """Train specialized model for Steam compressors"""
    start_time = time.time()
    audit_logger.log_system("Training steam compressor model", action="MODEL_TRAIN_COMPRESSOR_STEAM")
    try:
        data = generate_compressor_steam_training_data(800)
        feature_columns = ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial',
                          'vibracion_axial', 'presion_vapor_entrada', 'temperatura_vapor', 'temperatura_condensado']
        X = data[feature_columns].values
        y = data['failure_category'].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        audit_logger.log_system(f"Steam compressor model trained: {accuracy:.2%}", action="MODEL_READY_COMPRESSOR_STEAM")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_compressor_steam_model")
        raise

@functools.lru_cache(maxsize=1)
def train_compressor_gas_model():
    """Train specialized model for Gas compressors"""
    start_time = time.time()
    audit_logger.log_system("Training gas compressor model", action="MODEL_TRAIN_COMPRESSOR_GAS")
    try:
        data = generate_compressor_gas_training_data(800)
        feature_columns = ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial',
                          'vibracion_axial', 'relacion_aire_combustible', 'temperatura_aire_admision', 'indice_detonacion']
        X = data[feature_columns].values
        y = data['failure_category'].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=3)
        model.fit(X_train_scaled, y_train)
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        importances = np.mean([clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        audit_logger.log_system(f"Gas compressor model trained: {accuracy:.2%}", action="MODEL_READY_COMPRESSOR_GAS")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_compressor_gas_model")
        raise

COMPRESSOR_POWER_SOURCE_MODELS = {
    'Electric': train_compressor_electric_model,
    'Diesel': train_compressor_diesel_model,
    'Steam': train_compressor_steam_model,
    'Gas': train_compressor_gas_model,
}

def get_compressor_model_for_power_source(power_source: str):
    """Load appropriate compressor model for power source"""
    if power_source not in COMPRESSOR_POWER_SOURCE_MODELS:
        raise ValueError(f"Unknown power source: {power_source}")
    return COMPRESSOR_POWER_SOURCE_MODELS[power_source]()

def get_compressor_features_for_power_source(power_source: str) -> list:
    """Get feature column names for compressor with given power source"""
    generators = {
        'Electric': ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial', 'vibracion_axial', 
                     'eficiencia_motor', 'temperatura_devanado', 'corriente_fase'],
        'Diesel': ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial', 'vibracion_axial',
                   'consumo_combustible', 'temperatura_aceite_motor', 'presion_aceite_motor'],
        'Steam': ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial', 'vibracion_axial',
                  'presion_vapor_entrada', 'temperatura_vapor', 'temperatura_condensado'],
        'Gas': ['temperatura_descarga', 'ratio_compresion', 'vibracion_radial', 'vibracion_axial',
                'relacion_aire_combustible', 'temperatura_aire_admision', 'indice_detonacion']
    }
    return generators.get(power_source, [])
