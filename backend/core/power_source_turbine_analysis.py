"""
TURBINE - Power Source Specific Training Data Generators  
Part of Power Source Independent Analysis Module
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

from .config import RISK_LOW_THRESHOLD, RISK_HIGH_THRESHOLD
from .audit_logging_service import get_audit_logger

audit_logger = get_audit_logger()


# ============================================================================
# TURBINE - Power Source Specific Training Data Generators
# ============================================================================

def generate_turbine_electric_training_data(n_samples=800):
    """Generate training data for Electric-powered turbines."""
    np.random.seed(42)

    steam_temperature = np.random.normal(260, 45, n_samples)
    steam_temperature = np.clip(steam_temperature, 170, 380)

    inlet_pressure = np.random.normal(24, 7, n_samples)
    inlet_pressure = np.clip(inlet_pressure, 12, 55)

    axial_vibration = np.random.exponential(1.1, n_samples)
    axial_vibration = np.clip(axial_vibration, 0.15, 5.5)

    synchronous_speed = np.random.normal(3050, 520, n_samples)
    synchronous_speed = np.clip(synchronous_speed, 1650, 5250)

    exhaust_temperature = np.random.normal(125, 32, n_samples)
    exhaust_temperature = np.clip(exhaust_temperature, 55, 220)

    generator_efficiency = np.random.normal(94, 2.5, n_samples)
    generator_efficiency = np.clip(generator_efficiency, 88, 98)

    generator_winding_temperature = np.random.normal(70, 15, n_samples)
    generator_winding_temperature = np.clip(generator_winding_temperature, 45, 110)

    steam_temp_norm = steam_temperature / 380
    pressure_norm = inlet_pressure / 55
    vib_axial_norm = axial_vibration / 5.5
    speed_dev_norm = np.abs((synchronous_speed - 3050) / 3600)
    exhaust_norm = exhaust_temperature / 220
    efficiency_norm = (100 - generator_efficiency) / 12
    winding_norm = generator_winding_temperature / 110

    failure_score = (
        steam_temp_norm * 0.22 + pressure_norm * 0.14 + vib_axial_norm * 0.28 +
        speed_dev_norm * 0.18 + exhaust_norm * 0.08 + efficiency_norm * 0.06 + winding_norm * 0.04
    )

    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)

    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2

    return pd.DataFrame({
        'steam_temperature': steam_temperature,
        'inlet_pressure': inlet_pressure,
        'axial_vibration': axial_vibration,
        'synchronous_speed': synchronous_speed,
        'exhaust_temperature': exhaust_temperature,
        'generator_efficiency': generator_efficiency,
        'generator_winding_temperature': generator_winding_temperature,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_turbine_diesel_training_data(n_samples=800):
    """Generate training data for Diesel-powered turbines."""
    np.random.seed(42)

    steam_temperature = np.random.normal(280, 50, n_samples)
    steam_temperature = np.clip(steam_temperature, 185, 410)

    inlet_pressure = np.random.normal(28, 8, n_samples)
    inlet_pressure = np.clip(inlet_pressure, 14, 65)

    axial_vibration = np.random.exponential(1.3, n_samples)
    axial_vibration = np.clip(axial_vibration, 0.18, 6.5)

    synchronous_speed = np.random.normal(3100, 550, n_samples)
    synchronous_speed = np.clip(synchronous_speed, 1700, 5400)

    exhaust_temperature = np.random.normal(145, 38, n_samples)
    exhaust_temperature = np.clip(exhaust_temperature, 60, 260)

    fuel_consumption = np.random.normal(35, 8, n_samples)
    fuel_consumption = np.clip(fuel_consumption, 20, 55)

    engine_oil_temperature = np.random.normal(85, 15, n_samples)
    engine_oil_temperature = np.clip(engine_oil_temperature, 60, 120)

    steam_temp_norm = steam_temperature / 410
    pressure_norm = inlet_pressure / 65
    vib_axial_norm = axial_vibration / 6.5
    speed_dev_norm = np.abs((synchronous_speed - 3100) / 3700)
    exhaust_norm = exhaust_temperature / 260
    fuel_norm = fuel_consumption / 55
    oil_norm = engine_oil_temperature / 120

    failure_score = (
        steam_temp_norm * 0.24 + pressure_norm * 0.15 + vib_axial_norm * 0.26 +
        speed_dev_norm * 0.16 + exhaust_norm * 0.08 + fuel_norm * 0.06 + oil_norm * 0.05
    )

    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)

    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2

    return pd.DataFrame({
        'steam_temperature': steam_temperature,
        'inlet_pressure': inlet_pressure,
        'axial_vibration': axial_vibration,
        'synchronous_speed': synchronous_speed,
        'exhaust_temperature': exhaust_temperature,
        'fuel_consumption': fuel_consumption,
        'engine_oil_temperature': engine_oil_temperature,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_turbine_steam_training_data(n_samples=800):
    """Generate training data for Steam-powered turbines."""
    np.random.seed(42)

    steam_temperature = np.random.normal(300, 55, n_samples)
    steam_temperature = np.clip(steam_temperature, 200, 450)

    inlet_pressure = np.random.normal(32, 9, n_samples)
    inlet_pressure = np.clip(inlet_pressure, 16, 75)

    axial_vibration = np.random.exponential(1.2, n_samples)
    axial_vibration = np.clip(axial_vibration, 0.16, 6)

    synchronous_speed = np.random.normal(3000, 500, n_samples)
    synchronous_speed = np.clip(synchronous_speed, 1500, 5000)

    exhaust_temperature = np.random.normal(100, 25, n_samples)
    exhaust_temperature = np.clip(exhaust_temperature, 45, 180)

    steam_outlet_pressure = np.random.normal(2.5, 1.2, n_samples)
    steam_outlet_pressure = np.clip(steam_outlet_pressure, 0.5, 6)

    steam_flow_rate = np.random.normal(120, 35, n_samples)
    steam_flow_rate = np.clip(steam_flow_rate, 40, 250)

    steam_temp_norm = steam_temperature / 450
    pressure_norm = inlet_pressure / 75
    vib_axial_norm = axial_vibration / 6
    speed_dev_norm = np.abs((synchronous_speed - 3000) / 3500)
    exhaust_norm = exhaust_temperature / 180
    outlet_pressure_norm = (6 - steam_outlet_pressure) / 5.5
    flow_norm = np.abs((steam_flow_rate - 120) / 210)

    failure_score = (
        steam_temp_norm * 0.25 + pressure_norm * 0.18 + vib_axial_norm * 0.24 +
        speed_dev_norm * 0.15 + exhaust_norm * 0.08 + outlet_pressure_norm * 0.06 + flow_norm * 0.04
    )

    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)

    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2

    return pd.DataFrame({
        'steam_temperature': steam_temperature,
        'inlet_pressure': inlet_pressure,
        'axial_vibration': axial_vibration,
        'synchronous_speed': synchronous_speed,
        'exhaust_temperature': exhaust_temperature,
        'steam_outlet_pressure': steam_outlet_pressure,
        'steam_flow_rate': steam_flow_rate,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


def generate_turbine_gas_training_data(n_samples=800):
    """Generate training data for Gas-powered turbines."""
    np.random.seed(42)

    steam_temperature = np.random.normal(290, 52, n_samples)
    steam_temperature = np.clip(steam_temperature, 190, 420)

    inlet_pressure = np.random.normal(30, 8.5, n_samples)
    inlet_pressure = np.clip(inlet_pressure, 15, 70)

    axial_vibration = np.random.exponential(1.25, n_samples)
    axial_vibration = np.clip(axial_vibration, 0.17, 6.2)

    synchronous_speed = np.random.normal(3080, 540, n_samples)
    synchronous_speed = np.clip(synchronous_speed, 1650, 5300)

    exhaust_temperature = np.random.normal(135, 35, n_samples)
    exhaust_temperature = np.clip(exhaust_temperature, 55, 250)

    air_fuel_ratio = np.random.normal(15, 1.8, n_samples)
    air_fuel_ratio = np.clip(air_fuel_ratio, 12, 18.5)

    detonation_index = np.random.uniform(8, 92, n_samples)

    steam_temp_norm = steam_temperature / 420
    pressure_norm = inlet_pressure / 70
    vib_axial_norm = axial_vibration / 6.2
    speed_dev_norm = np.abs((synchronous_speed - 3080) / 3650)
    exhaust_norm = exhaust_temperature / 250
    air_fuel_dev = np.abs((air_fuel_ratio - 15) / 6)
    detonation_norm = detonation_index / 100

    failure_score = (
        steam_temp_norm * 0.23 + pressure_norm * 0.16 + vib_axial_norm * 0.25 +
        speed_dev_norm * 0.17 + exhaust_norm * 0.08 + air_fuel_dev * 0.08 + detonation_norm * 0.03
    )

    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)

    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2

    return pd.DataFrame({
        'steam_temperature': steam_temperature,
        'inlet_pressure': inlet_pressure,
        'axial_vibration': axial_vibration,
        'synchronous_speed': synchronous_speed,
        'exhaust_temperature': exhaust_temperature,
        'air_fuel_ratio': air_fuel_ratio,
        'detonation_index': detonation_index,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })


# ============================================================================
# TURBINE MODEL TRAINING FUNCTIONS (Per Power Source)
# ============================================================================

@functools.lru_cache(maxsize=1)
def train_turbine_electric_model():
    """Train specialized model for Electric turbines"""
    audit_logger.log_system("Training electric turbine model", action="MODEL_TRAIN_TURBINE_ELECTRIC")
    try:
        data = generate_turbine_electric_training_data(800)
        feature_columns = ['steam_temperature', 'inlet_pressure', 'axial_vibration',
                          'synchronous_speed', 'exhaust_temperature', 'generator_efficiency', 'generator_winding_temperature']
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
        audit_logger.log_system(f"Electric turbine model trained: {accuracy:.2%}", action="MODEL_READY_TURBINE_ELECTRIC")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_turbine_electric_model")
        raise

@functools.lru_cache(maxsize=1)
def train_turbine_diesel_model():
    """Train specialized model for Diesel turbines"""
    audit_logger.log_system("Training diesel turbine model", action="MODEL_TRAIN_TURBINE_DIESEL")
    try:
        data = generate_turbine_diesel_training_data(800)
        feature_columns = ['steam_temperature', 'inlet_pressure', 'axial_vibration',
                          'synchronous_speed', 'exhaust_temperature', 'fuel_consumption', 'engine_oil_temperature']
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
        audit_logger.log_system(f"Diesel turbine model trained: {accuracy:.2%}", action="MODEL_READY_TURBINE_DIESEL")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_turbine_diesel_model")
        raise

@functools.lru_cache(maxsize=1)
def train_turbine_steam_model():
    """Train specialized model for Steam turbines"""
    audit_logger.log_system("Training steam turbine model", action="MODEL_TRAIN_TURBINE_STEAM")
    try:
        data = generate_turbine_steam_training_data(800)
        feature_columns = ['steam_temperature', 'inlet_pressure', 'axial_vibration',
                          'synchronous_speed', 'exhaust_temperature', 'steam_outlet_pressure', 'steam_flow_rate']
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
        audit_logger.log_system(f"Steam turbine model trained: {accuracy:.2%}", action="MODEL_READY_TURBINE_STEAM")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_turbine_steam_model")
        raise

@functools.lru_cache(maxsize=1)
def train_turbine_gas_model():
    """Train specialized model for Gas turbines"""
    audit_logger.log_system("Training gas turbine model", action="MODEL_TRAIN_TURBINE_GAS")
    try:
        data = generate_turbine_gas_training_data(800)
        feature_columns = ['steam_temperature', 'inlet_pressure', 'axial_vibration',
                          'synchronous_speed', 'exhaust_temperature', 'air_fuel_ratio', 'detonation_index']
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
        audit_logger.log_system(f"Gas turbine model trained: {accuracy:.2%}", action="MODEL_READY_TURBINE_GAS")
        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}
    except Exception as e:
        audit_logger.log_error(e, context="train_turbine_gas_model")
        raise

TURBINE_POWER_SOURCE_MODELS = {
    'Electric': train_turbine_electric_model,
    'Diesel': train_turbine_diesel_model,
    'Steam': train_turbine_steam_model,
    'Gas': train_turbine_gas_model,
}

def get_turbine_model_for_power_source(power_source: str):
    """Load appropriate turbine model for power source"""
    if power_source not in TURBINE_POWER_SOURCE_MODELS:
        raise ValueError(f"Unknown power source: {power_source}")
    return TURBINE_POWER_SOURCE_MODELS[power_source]()

def get_turbine_features_for_power_source(power_source: str) -> list:
    """Get feature column names for turbine with given power source."""
    features = {
        'Electric': ['steam_temperature', 'inlet_pressure', 'axial_vibration', 'synchronous_speed',
                     'exhaust_temperature', 'generator_efficiency', 'generator_winding_temperature'],
        'Diesel':   ['steam_temperature', 'inlet_pressure', 'axial_vibration', 'synchronous_speed',
                     'exhaust_temperature', 'fuel_consumption', 'engine_oil_temperature'],
        'Steam':    ['steam_temperature', 'inlet_pressure', 'axial_vibration', 'synchronous_speed',
                     'exhaust_temperature', 'steam_outlet_pressure', 'steam_flow_rate'],
        'Gas':      ['steam_temperature', 'inlet_pressure', 'axial_vibration', 'synchronous_speed',
                     'exhaust_temperature', 'air_fuel_ratio', 'detonation_index']
    }
    return features.get(power_source, [])


# ============================================================================
# MASTER REGISTRY - Equipment & Power Source Model Lookup
# ============================================================================

def get_model_for_equipment_and_power_source(equipment_type: str, power_source: str):
    """
    Get model tuple for any equipment type + power source combination
    Returns: (model, scaler, accuracy, feature_importance, test_data)
    """
    from .power_source_analysis import (
        get_pump_model_for_power_source, get_compressor_model_for_power_source,
        get_turbine_model_for_power_source
    )
    
    equipment_models = {
        'pump': get_pump_model_for_power_source,
        'compressor': get_compressor_model_for_power_source,
        'turbine': get_turbine_model_for_power_source,
    }
    
    if equipment_type not in equipment_models:
        raise ValueError(f"Unknown equipment type: {equipment_type}")
    
    return equipment_models[equipment_type](power_source)

def get_features_for_equipment_and_power_source(equipment_type: str, power_source: str) -> list:
    """Get features for any equipment + power source combination"""
    from .power_source_analysis import (
        get_pump_features_for_power_source, get_compressor_features_for_power_source,
        get_turbine_features_for_power_source
    )
    
    equipment_features = {
        'pump': get_pump_features_for_power_source,
        'compressor': get_compressor_features_for_power_source,
        'turbine': get_turbine_features_for_power_source,
    }
    
    if equipment_type not in equipment_features:
        raise ValueError(f"Unknown equipment type: {equipment_type}")
    
    return equipment_features[equipment_type](power_source)
