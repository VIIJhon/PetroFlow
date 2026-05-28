"""
Math Engine Module
Contains ML models, statistical analysis, safety factors, and reliability functions
"""

from functools import lru_cache
# Refactored by Jhon Villegas: Completely decoupled from Streamlit UI modules for FastAPI backend autonomy
# import streamlit as st
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from scipy import stats
from scipy.special import gamma as gamma_func
from lifelines import KaplanMeierFitter
from datetime import datetime
from typing import Tuple, Dict
import logging
import time

from .config import RISK_LOW_THRESHOLD, RISK_HIGH_THRESHOLD
from .audit_logging_service import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

def get_risk_level(probability: float) -> Tuple[str, str]:
    """
    Determine risk level and color based on probability
    
    Args:
        probability: Failure probability (0-100)
    
    Returns:
        Tuple of (risk_level, color)
    """
    if probability < RISK_LOW_THRESHOLD:
        return "Low Risk", "green"
    elif probability < RISK_HIGH_THRESHOLD:
        return "Medium Risk", "orange"
    else:
        return "High Risk", "red"



def generate_survival_data(n_samples=250):
    """
    Generate synthetic time-to-failure and censoring data for survival analysis.
    """
    np.random.seed(42)
    vibration_norm = np.random.uniform(0.1, 1.0, n_samples)
    failure_score = np.random.uniform(0.1, 0.9, n_samples)
    
    scale_base = 15000
    scale = scale_base * (1.5 - failure_score)
    scale = np.clip(scale, 3000, 25000)
    
    shape = 1.5 + vibration_norm * 0.8
    shape = np.clip(shape, 0.8, 3.0)
    
    time_to_failure = np.zeros(n_samples)
    for i in range(n_samples):
        time_to_failure[i] = np.random.weibull(shape[i]) * scale[i]
    
    time_to_failure = np.clip(time_to_failure, 100, 30000)
    
    censoring_prob = 0.7 - failure_score * 0.5
    censoring_prob = np.clip(censoring_prob, 0.1, 0.6)
    event_observed = np.random.binomial(1, 1 - censoring_prob)
    
    for i in range(n_samples):
        if event_observed[i] == 0:
            time_to_failure[i] = np.random.uniform(100, time_to_failure[i])
            
    return pd.DataFrame({
        'time_to_failure': time_to_failure,
        'event_observed': event_observed
    })

def generate_pump_training_data(n_samples=800):
    """
    Generate synthetic training data specific to turbopumps (Centrifugal pump).
    Parameters: Discharge Temperature, Inlet Pressure, Outlet Pressure, Volumetric Flow, Available NPSH
    """
    np.random.seed(42)

    discharge_temperature = np.random.normal(65, 20, n_samples)
    discharge_temperature = np.clip(discharge_temperature, 20, 120)

    inlet_pressure = np.random.normal(1.5, 0.8, n_samples)
    inlet_pressure = np.clip(inlet_pressure, 0.5, 5)

    outlet_pressure = np.random.normal(20, 8, n_samples)
    outlet_pressure = np.clip(outlet_pressure, 5, 50)

    volumetric_flow = np.random.normal(150, 50, n_samples)
    volumetric_flow = np.clip(volumetric_flow, 50, 300)

    available_npsh = np.random.normal(4, 1.5, n_samples)
    available_npsh = np.clip(available_npsh, 0.5, 8)

    # Failure logic specific to pumps
    temp_norm = discharge_temperature / 120
    pressure_diff_norm = (outlet_pressure - inlet_pressure) / 45
    cavitation_risk = np.maximum(0, (2.5 - available_npsh) / 2.5)
    flow_efficiency = 1 - np.abs((volumetric_flow - 150) / 250)

    failure_score = (
        temp_norm * 0.25 +
        pressure_diff_norm * 0.20 +
        cavitation_risk * 0.35 +
        (1 - flow_efficiency) * 0.20
    )

    failure_score += cavitation_risk * 0.15
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)

    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2

    return pd.DataFrame({
        'discharge_temperature': discharge_temperature,
        'inlet_pressure': inlet_pressure,
        'outlet_pressure': outlet_pressure,
        'volumetric_flow': volumetric_flow,
        'available_npsh': available_npsh,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })

def generate_compressor_training_data(n_samples=800):
    """
    Generate synthetic training data specific to turbocompressors.
    Parameters: Discharge Temperature, Compression Ratio, Radial Vibration, Axial Vibration, Relative Humidity
    """
    np.random.seed(42)

    discharge_temperature = np.random.normal(85, 25, n_samples)
    discharge_temperature = np.clip(discharge_temperature, 30, 150)

    compression_ratio = np.random.normal(4.5, 1.5, n_samples)
    compression_ratio = np.clip(compression_ratio, 1.5, 10)

    radial_vibration = np.random.exponential(1.5, n_samples)
    radial_vibration = np.clip(radial_vibration, 0.2, 8)

    axial_vibration = np.random.exponential(1.2, n_samples)
    axial_vibration = np.clip(axial_vibration, 0.1, 6)

    relative_humidity = np.random.normal(55, 20, n_samples)
    relative_humidity = np.clip(relative_humidity, 20, 95)

    # Failure logic specific to compressors
    temp_norm = discharge_temperature / 150
    ratio_norm = (compression_ratio - 1.5) / 8.5
    vib_radial_norm = radial_vibration / 8
    vib_axial_norm = axial_vibration / 6
    moisture_risk = np.abs((relative_humidity - 50) / 50)

    failure_score = (
        temp_norm * 0.20 +
        ratio_norm * 0.15 +
        vib_radial_norm * 0.30 +
        vib_axial_norm * 0.25 +
        moisture_risk * 0.10
    )

    failure_score += vib_radial_norm * vib_axial_norm * 0.10
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)

    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2

    return pd.DataFrame({
        'discharge_temperature': discharge_temperature,
        'compression_ratio': compression_ratio,
        'radial_vibration': radial_vibration,
        'axial_vibration': axial_vibration,
        'relative_humidity': relative_humidity,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })

def generate_turbine_training_data(n_samples=800):
    """
    Generate synthetic training data specific to turbines.
    Parameters: Steam Temperature, Inlet Pressure, Axial Vibration, Synchronous Speed, Exhaust Temperature
    """
    np.random.seed(42)

    steam_temperature = np.random.normal(250, 40, n_samples)
    steam_temperature = np.clip(steam_temperature, 150, 350)

    inlet_pressure = np.random.normal(25, 8, n_samples)
    inlet_pressure = np.clip(inlet_pressure, 10, 60)

    axial_vibration = np.random.exponential(1.0, n_samples)
    axial_vibration = np.clip(axial_vibration, 0.1, 5)

    synchronous_speed = np.random.normal(3000, 500, n_samples)
    synchronous_speed = np.clip(synchronous_speed, 1500, 5000)

    exhaust_temperature = np.random.normal(120, 30, n_samples)
    exhaust_temperature = np.clip(exhaust_temperature, 50, 200)

    # Failure logic specific to turbines
    steam_temp_norm = steam_temperature / 350
    pressure_norm = inlet_pressure / 60
    vib_axial_norm = axial_vibration / 5
    speed_deviation = np.abs((synchronous_speed - 3000) / 3500)
    exhaust_temp_norm = exhaust_temperature / 200

    failure_score = (
        steam_temp_norm * 0.25 +
        pressure_norm * 0.15 +
        vib_axial_norm * 0.30 +
        speed_deviation * 0.20 +
        exhaust_temp_norm * 0.10
    )

    failure_score += steam_temp_norm * pressure_norm * 0.12
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
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })

@lru_cache(maxsize=1)
def train_pump_model():
    """Train specialized Calibrated Gradient Boosting model for turbopumps"""
    start_time = time.time()
    audit_logger.log_system("Training specialized pump model", action="MODEL_TRAIN_PUMP")
    
    try:
        data = generate_pump_training_data(800)
        feature_columns = ['discharge_temperature', 'inlet_pressure', 'outlet_pressure',
                          'volumetric_flow', 'available_npsh']

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

        importances = np.mean([
            clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_
        ], axis=0)
        feature_importance = dict(zip(feature_columns, importances))

        duration = time.time() - start_time
        audit_logger.log_system(f"Pump model trained: {accuracy:.2%} accuracy", action="MODEL_READY_PUMP")

        metadata = {
            'version': '1.0',
            'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'accuracy': accuracy,
            'features': feature_columns,
            'model_type': 'GradientBoosting_Calibrated_Pump'
        }

        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}, metadata

    except Exception as e:
        audit_logger.log_error(e, context="train_pump_model")
        raise

@lru_cache(maxsize=1)
def train_compressor_model():
    """Train specialized Calibrated Gradient Boosting model for turbocompressors"""
    start_time = time.time()
    audit_logger.log_system("Training specialized compressor model", action="MODEL_TRAIN_COMPRESSOR")
    
    try:
        data = generate_compressor_training_data(800)
        feature_columns = ['discharge_temperature', 'compression_ratio', 'radial_vibration',
                          'axial_vibration', 'relative_humidity']

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

        importances = np.mean([
            clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_
        ], axis=0)
        feature_importance = dict(zip(feature_columns, importances))

        duration = time.time() - start_time
        audit_logger.log_system(f"Compressor model trained: {accuracy:.2%} accuracy", action="MODEL_READY_COMPRESSOR")

        metadata = {
            'version': '1.0',
            'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'accuracy': accuracy,
            'features': feature_columns,
            'model_type': 'GradientBoosting_Calibrated_Compressor'
        }

        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}, metadata

    except Exception as e:
        audit_logger.log_error(e, context="train_compressor_model")
        raise

@lru_cache(maxsize=1)
def train_turbine_model():
    """Train specialized Calibrated Gradient Boosting model for turbines"""
    start_time = time.time()
    audit_logger.log_system("Training specialized turbine model", action="MODEL_TRAIN_TURBINE")
    
    try:
        data = generate_turbine_training_data(800)
        feature_columns = ['steam_temperature', 'inlet_pressure', 'axial_vibration',
                          'synchronous_speed', 'exhaust_temperature']

        X = data[feature_columns].values
        y = data['failure_category'].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=5)
        model.fit(X_train_scaled, y_train)

        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))

        importances = np.mean([
            clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_
        ], axis=0)
        feature_importance = dict(zip(feature_columns, importances))

        duration = time.time() - start_time
        audit_logger.log_system(f"Turbine model trained: {accuracy:.2%} accuracy", action="MODEL_READY_TURBINE")

        metadata = {
            'version': '1.0',
            'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'accuracy': accuracy,
            'features': feature_columns,
            'model_type': 'GradientBoosting_Calibrated_Turbine'
        }

        return model, scaler, accuracy, feature_importance, {'X_test': X_test, 'y_test': y_test}, metadata

    except Exception as e:
        audit_logger.log_error(e, context="train_turbine_model")
        raise



def predict_pump_failure(model, scaler, discharge_temperature, inlet_pressure, outlet_pressure,
                        volumetric_flow, available_npsh):
    """Predict failure for turbopump with specialized parameters."""
    try:
        features = np.array([[discharge_temperature, inlet_pressure, outlet_pressure,
                             volumetric_flow, available_npsh]])
        features_scaled = scaler.transform(features)

        category = model.predict(features_scaled)[0]
        probabilities = model.predict_proba(features_scaled)[0]

        failure_prob = (probabilities[0] * 0 + probabilities[1] * 50 + probabilities[2] * 100)

        category_names = {0: "Normal", 1: "Caution", 2: "Critical"}
        category_name = category_names[category]

        prob_dict = {
            "Normal": probabilities[0] * 100,
            "Caution": probabilities[1] * 100,
            "Critical": probabilities[2] * 100
        }

        input_params = {
            'discharge_temperature': discharge_temperature,
            'inlet_pressure': inlet_pressure,
            'outlet_pressure': outlet_pressure,
            'volumetric_flow': volumetric_flow,
            'available_npsh': available_npsh
        }

        audit_logger.log_prediction(
            input_params=input_params,
            output_probability=failure_prob,
            confidence=float(probabilities[category]),
            model_type='GradientBoosting_Pump',
            prediction_category=category_name
        )

        if failure_prob > 70:
            audit_logger.log_system(
                f"CRITICAL PUMP FAILURE: {failure_prob:.1f}%",
                action="CRITICAL_ALERT_PUMP",
                equipment_type='pump'
            )

        return failure_prob, category, category_name, prob_dict
    except Exception as e:
        audit_logger.log_error(e, context="predict_pump_failure")
        raise

def predict_compressor_failure(model, scaler, discharge_temperature, compression_ratio,
                               radial_vibration, axial_vibration, relative_humidity):
    """Predict failure for turbocompressor with specialized parameters."""
    try:
        features = np.array([[discharge_temperature, compression_ratio, radial_vibration,
                             axial_vibration, relative_humidity]])
        features_scaled = scaler.transform(features)

        category = model.predict(features_scaled)[0]
        probabilities = model.predict_proba(features_scaled)[0]

        failure_prob = (probabilities[0] * 0 + probabilities[1] * 50 + probabilities[2] * 100)

        category_names = {0: "Normal", 1: "Caution", 2: "Critical"}
        category_name = category_names[category]

        prob_dict = {
            "Normal": probabilities[0] * 100,
            "Caution": probabilities[1] * 100,
            "Critical": probabilities[2] * 100
        }

        input_params = {
            'discharge_temperature': discharge_temperature,
            'compression_ratio': compression_ratio,
            'radial_vibration': radial_vibration,
            'axial_vibration': axial_vibration,
            'relative_humidity': relative_humidity
        }

        audit_logger.log_prediction(
            input_params=input_params,
            output_probability=failure_prob,
            confidence=float(probabilities[category]),
            model_type='GradientBoosting_Compressor',
            prediction_category=category_name
        )

        if failure_prob > 70:
            audit_logger.log_system(
                f"CRITICAL COMPRESSOR FAILURE: {failure_prob:.1f}%",
                action="CRITICAL_ALERT_COMPRESSOR",
                equipment_type='compressor'
            )

        return failure_prob, category, category_name, prob_dict
    except Exception as e:
        audit_logger.log_error(e, context="predict_compressor_failure")
        raise

def predict_turbine_failure(model, scaler, steam_temperature, inlet_pressure,
                            axial_vibration, synchronous_speed, exhaust_temperature):
    """Predict failure for turbine with specialized parameters."""
    try:
        features = np.array([[steam_temperature, inlet_pressure, axial_vibration,
                             synchronous_speed, exhaust_temperature]])
        features_scaled = scaler.transform(features)

        category = model.predict(features_scaled)[0]
        probabilities = model.predict_proba(features_scaled)[0]

        failure_prob = (probabilities[0] * 0 + probabilities[1] * 50 + probabilities[2] * 100)

        category_names = {0: "Normal", 1: "Caution", 2: "Critical"}
        category_name = category_names[category]

        prob_dict = {
            "Normal": probabilities[0] * 100,
            "Caution": probabilities[1] * 100,
            "Critical": probabilities[2] * 100
        }

        input_params = {
            'steam_temperature': steam_temperature,
            'inlet_pressure': inlet_pressure,
            'axial_vibration': axial_vibration,
            'synchronous_speed': synchronous_speed,
            'exhaust_temperature': exhaust_temperature
        }

        audit_logger.log_prediction(
            input_params=input_params,
            output_probability=failure_prob,
            confidence=float(probabilities[category]),
            model_type='GradientBoosting_Turbine',
            prediction_category=category_name
        )

        if failure_prob > 70:
            audit_logger.log_system(
                f"CRITICAL TURBINE FAILURE: {failure_prob:.1f}%",
                action="CRITICAL_ALERT_TURBINE",
                equipment_type='turbine'
            )

        return failure_prob, category, category_name, prob_dict
    except Exception as e:
        audit_logger.log_error(e, context="predict_turbine_failure")
        raise

def predict_failure(model, scaler, features_dict):
    """
    Generic failure prediction function compatible with multiple model types.
    
    Args:
        model: Trained model
        scaler: Fitted StandardScaler
        features_dict: Dictionary of features to predict
    
    Returns:
        float: Failure probability (0-100)
    """
    try:
        # Extract features in consistent order
        feature_order = ['temperature', 'pressure', 'vibration', 'operating_hours', 'rpm']
        features = np.array([[features_dict.get(f, 0) for f in feature_order]])
        features_scaled = scaler.transform(features)
        
        probabilities = model.predict_proba(features_scaled)[0]
        failure_prob = (probabilities[0] * 0 + probabilities[1] * 50 + probabilities[2] * 100) if len(probabilities) >= 3 else probabilities[-1] * 100
        
        failure_prob = min(100, max(0, failure_prob))
        
        category = int(model.predict(features_scaled)[0]) if hasattr(model, 'predict') else 0
        category_names = {0: "Normal", 1: "Caution", 2: "Critical"}
        category_name = category_names.get(category, "Unknown")
        
        if len(probabilities) >= 3:
            prob_dict = {
                "Normal": probabilities[0] * 100,
                "Caution": probabilities[1] * 100,
                "Critical": probabilities[2] * 100
            }
        else:
            prob_dict = {
                "Normal": (1 - probabilities[-1]) * 100,
                "Critical": probabilities[-1] * 100
            }
            
        return failure_prob, category, category_name, prob_dict
    except Exception as e:
        audit_logger.log_error(e, context="predict_failure")
        raise

def apply_safety_factor(value, safety_factor_percent, value_type='probability'):
    """
    Apply Oil & Gas industry safety factor (derating) to predictions.
    
    Mathematical formulas:
    - For RUL/MTTF/eta: Adjusted = Original × (1 - SF%)
    - For Probability: Adjusted = Original + (1 - Original) × SF%
    
    Args:
        value: Original value to adjust
        safety_factor_percent: Safety factor percentage (0-30)
        value_type: 'probability', 'time', or 'reliability'
    
    Returns:
        Adjusted value with safety factor applied
    """
    sf_decimal = safety_factor_percent / 100.0
    
    if value_type == 'probability':
        adjusted = value + (1 - value) * sf_decimal
        return min(adjusted, 1.0)
    
    elif value_type == 'time':
        adjusted = value * (1 - sf_decimal)
        return max(adjusted, 0)
    
    elif value_type == 'reliability':
        adjusted = value * (1 - sf_decimal)
        return max(adjusted, 0)
    
    else:
        return value

def calculate_adjusted_predictions(raw_probability, safety_factor_percent):
    """
    Calculate adjusted predictions with safety factor.
    
    Returns dict with raw and adjusted values plus safety margin.
    """
    raw_prob_decimal = raw_probability / 100.0
    
    adjusted_prob_decimal = apply_safety_factor(
        raw_prob_decimal,
        safety_factor_percent,
        'probability'
    )
    
    adjusted_probability = adjusted_prob_decimal * 100.0
    
    safety_margin = adjusted_probability - raw_probability
    
    def get_risk_level_local(prob):
        if prob < 30:
            return "Low Risk", "green"
        elif prob < 70:
            return "Medium Risk", "orange"
        else:
            return "High Risk", "red"
    
    raw_risk, raw_color = get_risk_level_local(raw_probability)
    adjusted_risk, adjusted_color = get_risk_level_local(adjusted_probability)
    
    return {
        'raw_probability': raw_probability,
        'adjusted_probability': adjusted_probability,
        'safety_margin': safety_margin,
        'safety_factor_percent': safety_factor_percent,
        'raw_risk_level': raw_risk,
        'raw_risk_color': raw_color,
        'adjusted_risk_level': adjusted_risk,
        'adjusted_risk_color': adjusted_color,
        'conservativeness': f"{safety_factor_percent}% more conservative"
    }

def retrain_model_with_new_data(new_features_df, model_version='2.0'):
    """
    Retrain the ML model with uploaded data from Phase 2.
    
    Args:
        new_features_df: DataFrame with prepared features from prepare_for_ml()
        model_version: Version identifier for the new model
    
    Returns:
        new_model, new_scaler, new_accuracy, new_feature_importance,
        new_test_data, new_metadata, comparison_report
    """
    feature_columns = ['temperature', 'pressure', 'vibration', 'operating_hours', 'rpm']
    
    if 'failure_category' not in new_features_df.columns:
        temp_norm = new_features_df['temperature'] / 150
        pressure_norm = new_features_df['pressure'] / 50
        vibration_norm = new_features_df['vibration'] / 10
        hours_norm = new_features_df['operating_hours'] / 20000
        rpm_norm = np.abs(new_features_df['rpm'] - 2500) / 2500
        
        failure_score = (
            temp_norm * 0.25 +
            pressure_norm * 0.20 +
            vibration_norm * 0.30 +
            hours_norm * 0.15 +
            rpm_norm * 0.10
        )
        
        failure_category = np.zeros(len(new_features_df), dtype=int)
        failure_category[failure_score >= 0.3] = 1
        failure_category[failure_score >= 0.7] = 2
        new_features_df['failure_category'] = failure_category
    
    X = new_features_df[feature_columns].values
    y = new_features_df['failure_category'].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    new_scaler = StandardScaler()
    X_train_scaled = new_scaler.fit_transform(X_train)
    X_test_scaled = new_scaler.transform(X_test)
    
    new_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    new_model.fit(X_train_scaled, y_train)
    
    y_pred = new_model.predict(X_test_scaled)
    new_accuracy = accuracy_score(y_test, y_pred)
    
    new_feature_importance = dict(zip(feature_columns, new_model.feature_importances_))
    
    new_test_data = {
        'X_test': X_test,
        'y_test': y_test,
        'y_pred': y_pred
    }
    
    new_metadata = {
        'version': model_version,
        'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'accuracy': new_accuracy,
        'data_source': 'uploaded_data'
    }
    
    comparison_report = {
        'new_accuracy': new_accuracy,
        'new_training_samples': len(X_train),
        'feature_importance_changes': new_feature_importance
    }
    
    return new_model, new_scaler, new_accuracy, new_feature_importance, new_test_data, new_metadata, comparison_report

# Caching removed by Jhon Villegas to prevent direct Streamlit module-level bindings in backend execution context
def jackknife_resampling(_model, _scaler, X_train, y_train, test_features):
    """
    Perform Jackknife resampling (leave-one-out cross-validation) for uncertainty estimation.
    
    CACHING: Uses @st.cache_data with 1-hour TTL
    - Rationale: Jackknife requires training n models (very expensive for large datasets)
    - Cache key: Based on training data hash and test features
    - TTL: 1 hour (results stable for same training data)
    - Performance impact: Reduces computation from minutes to instant for repeated queries
    
    Mathematical formulas:
    - theta_hat_(-i) = estimate without observation i
    - Var_jack = (n-1)/n * sum((theta_hat_(-i) - theta_hat_mean)^2)
    - 95% CI = theta_hat +/- 1.96 * sqrt(Var_jack)
    
    Args:
        model: Trained RandomForest model (prefixed with _ to exclude from cache key)
        scaler: Fitted StandardScaler (prefixed with _ to exclude from cache key)
        X_train: Training features
        y_train: Training labels
        test_features: Features to predict (1D array)
    
    Returns:
        dict with prediction, variance, confidence_interval, all_predictions
    """
    n = len(X_train)
    predictions = []
    
    for i in range(n):
        X_loo = np.delete(X_train, i, axis=0)
        y_loo = np.delete(y_train, i, axis=0)
        
        scaler_loo = StandardScaler()
        X_loo_scaled = scaler_loo.fit_transform(X_loo)
        
        model_loo = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42 + i,
            n_jobs=-1
        )
        model_loo.fit(X_loo_scaled, y_loo)
        
        test_scaled = scaler_loo.transform(test_features.reshape(1, -1))
        probs = model_loo.predict_proba(test_scaled)[0]
        
        failure_prob = (probs[0] * 0 + probs[1] * 50 + probs[2] * 100)
        predictions.append(failure_prob)
    
    predictions = np.array(predictions)
    
    theta_mean = np.mean(predictions)
    
    jackknife_variance = ((n - 1) / n) * np.sum((predictions - theta_mean) ** 2)
    jackknife_std = np.sqrt(jackknife_variance)
    
    ci_lower = theta_mean - 1.96 * jackknife_std
    ci_upper = theta_mean + 1.96 * jackknife_std
    
    ci_lower = max(0, ci_lower)
    ci_upper = min(100, ci_upper)
    
    return {
        'prediction': theta_mean,
        'variance': jackknife_variance,
        'std_error': jackknife_std,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'all_predictions': predictions
    }

# Caching removed by Jhon Villegas to prevent direct Streamlit module-level bindings in backend execution context
def generate_kaplan_meier_data(survival_data):
    """
    Perform Kaplan-Meier survival analysis.
    
    CACHING: Uses @st.cache_data with 1-hour TTL
    - Rationale: Survival analysis involves iterative probability calculations
    - Cache key: Based on survival_data DataFrame hash
    - TTL: 1 hour (survival data doesn't change frequently)
    - Performance impact: Reduces computation time for repeated analyses
    
    Mathematical formula:
    S(t) = product((1 - d_i/n_i)) for all t_i <= t
    Where:
    - d_i = number of failures at time t_i
    - n_i = number at risk at time t_i
    
    Args:
        survival_data: DataFrame with 'time_to_failure' and 'event_observed' columns
    
    Returns:
        dict with survival_function, median_survival, confidence_intervals, kmf_object
    """
    kmf = KaplanMeierFitter()
    
    kmf.fit(
        durations=survival_data['time_to_failure'],
        event_observed=survival_data['event_observed'],
        label='Equipment Survival'
    )
    
    survival_function = kmf.survival_function_
    
    median_survival = kmf.median_survival_time_
    
    confidence_interval = kmf.confidence_interval_survival_function_
    
    time_points = [5000, 10000, 15000, 20000]
    survival_at_times = {}
    for t in time_points:
        if t <= survival_function.index.max():
            idx = pd.Series(survival_function.index).sub(t).abs().argmin()
            survival_at_times[t] = survival_function.iloc[idx].values[0]
        else:
            survival_at_times[t] = None
    
    return {
        'kmf': kmf,
        'survival_function': survival_function,
        'median_survival': median_survival,
        'confidence_interval': confidence_interval,
        'survival_at_times': survival_at_times
    }

# Caching removed by Jhon Villegas to prevent direct Streamlit module-level bindings in backend execution context
def fit_weibull_distribution(failure_times):
    """
    Perform Weibull distribution analysis for reliability prediction.
    
    CACHING: Uses @st.cache_data with 1-hour TTL
    - Rationale: Weibull fitting involves iterative optimization and statistical calculations
    - Cache key: Based on failure_times array hash
    - TTL: 1 hour (failure data doesn't change frequently)
    - Performance impact: Reduces computation from seconds to milliseconds
    
    Mathematical formulas:
    - PDF: f(t) = (beta/eta)(t/eta)^(beta-1) * exp(-(t/eta)^beta)
    - Reliability: R(t) = exp(-(t/eta)^beta)
    - Hazard rate: h(t) = (beta/eta)(t/eta)^(beta-1)
    - MTTF: eta * Gamma(1 + 1/beta)
    
    Where:
    - beta = shape parameter (failure mode indicator)
    - eta = scale parameter (characteristic life)
    
    Args:
        failure_times: Array of observed failure times (only actual failures, not censored)
    
    Returns:
        dict with shape, scale, MTTF, reliability_function, hazard_rate, failure_mode
    """
    failure_times = failure_times[failure_times > 0]
    
    shape, loc, scale = stats.weibull_min.fit(failure_times, floc=0)
    
    beta = shape
    eta = scale
    
    mttf = eta * gamma_func(1 + 1/beta)
    
    if beta < 1:
        failure_mode = "Infant Mortality (beta < 1)"
        failure_trend = "Decreasing failure rate - early failures"
    elif beta > 1:
        failure_mode = "Wear-out (beta > 1)"
        failure_trend = "Increasing failure rate - aging/wear"
    else:
        failure_mode = "Random Failures (beta approx 1)"
        failure_trend = "Constant failure rate - random events"
    
    t_max = failure_times.max()
    t_points = np.linspace(0, t_max * 1.2, 200)
    t_points = t_points[t_points > 0]
    
    reliability = np.exp(-(t_points / eta) ** beta)
    
    hazard_rate = (beta / eta) * ((t_points / eta) ** (beta - 1))
    
    pdf = stats.weibull_min.pdf(t_points, beta, loc=0, scale=eta)
    cdf = stats.weibull_min.cdf(t_points, beta, loc=0, scale=eta)
    
    sorted_failures = np.sort(failure_times)
    n = len(sorted_failures)
    plotting_positions = (np.arange(1, n + 1) - 0.3) / (n + 0.4)
    
    weibull_y = np.log(-np.log(1 - plotting_positions))
    weibull_x = np.log(sorted_failures)
    
    return {
        'shape': beta,
        'scale': eta,
        'mttf': mttf,
        'failure_mode': failure_mode,
        'failure_trend': failure_trend,
        't_points': t_points,
        'reliability': reliability,
        'hazard_rate': hazard_rate,
        'pdf': pdf,
        'cdf': cdf,
        'weibull_plot_x': weibull_x,
        'weibull_plot_y': weibull_y,
        'sorted_failures': sorted_failures
    }

# ============================================================================
# Generic Training Function for app.py compatibility
# ============================================================================

def generate_synthetic_training_data(n_samples=800, include_survival_data=False):
    """
    Generate synthetic training data for generic failure prediction model.
    
    Args:
        n_samples: Number of samples to generate
        include_survival_data: Whether to include survival analysis data
    
    Returns:
        DataFrame with synthetic training data
    """
    np.random.seed(42)
    
    # Generic parameters suitable for rotating equipment
    temperature = np.random.normal(65, 20, n_samples)
    temperature = np.clip(temperature, 20, 120)
    
    pressure = np.random.normal(15, 5, n_samples)
    pressure = np.clip(pressure, 5, 40)
    
    vibration = np.random.exponential(0.8, n_samples)
    vibration = np.clip(vibration, 0.5, 5)  # Fixed: minimum 0.5
    
    operating_hours = np.random.uniform(100, 20000, n_samples)  # Fixed: maximum 20000
    rpm = np.random.normal(3000, 500, n_samples)
    rpm = np.clip(rpm, 1500, 5000)
    
    # Failure logic
    temp_norm = temperature / 120
    pressure_norm = pressure / 40
    vib_norm = vibration / 5
    hours_norm = operating_hours / 20000  # Fixed: use 20000 as scale
    
    failure_score = (
        temp_norm * 0.25 +
        pressure_norm * 0.20 +
        vib_norm * 0.30 +
        hours_norm * 0.25
    )
    
    failure_score += np.random.normal(0, 0.05, n_samples)
    failure_score = np.clip(failure_score, 0, 1)
    
    failure_category = np.zeros(n_samples, dtype=int)
    failure_category[failure_score >= 0.35] = 1
    failure_category[failure_score >= 0.60] = 2
    
    data = pd.DataFrame({
        'temperature': temperature,
        'pressure': pressure,
        'vibration': vibration,
        'operating_hours': operating_hours,
        'rpm': rpm,
        'failure_category': failure_category,
        'failure_score': failure_score * 100
    })
    
    if include_survival_data:
        # Add survival analysis data
        survival_data = generate_survival_data(n_samples)
        data['time_to_failure'] = survival_data['time_to_failure'].values
        data['event_observed'] = survival_data['event_observed'].values
    
    return data


@lru_cache(maxsize=1)
def train_failure_prediction_model():
    """
    Train the main failure prediction model for app.py.
    
    Returns:
        Tuple of (model, scaler, accuracy, feature_importance, test_data, metadata)
    """
    start_time = time.time()
    audit_logger.log_system("Training main failure prediction model", action="MODEL_TRAIN_GENERIC")
    
    try:
        data = generate_synthetic_training_data(n_samples=800)
        feature_columns = ['temperature', 'pressure', 'vibration', 'operating_hours', 'rpm']
        
        X = data[feature_columns].values
        y = data['failure_category'].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        base_gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model = CalibratedClassifierCV(base_gb, method='sigmoid', cv=5)
        model.fit(X_train_scaled, y_train)
        
        accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
        
        importances = np.mean([
            clf.estimator.feature_importances_ for clf in model.calibrated_classifiers_
        ], axis=0)
        feature_importance = dict(zip(feature_columns, importances))
        
        duration = time.time() - start_time
        audit_logger.log_system(f"Generic model trained: {accuracy:.2%} accuracy in {duration:.1f}s", 
                                action="MODEL_READY_GENERIC")
        
        test_data = {
            'X_test': X_test,
            'y_test': y_test,
            'X_test_scaled': X_test_scaled
        }
        
        metadata = {
            'version': '1.0',
            'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'accuracy': accuracy,
            'features': feature_columns,
            'model_type': 'GradientBoosting_Calibrated'
        }
        
        return model, scaler, accuracy, feature_importance, test_data, metadata
        
    except Exception as e:
        audit_logger.log_error(e, context="train_failure_prediction_model")
        raise
    


def explain_prediction_shap(model, scaler, features_dict, feature_columns):
    """
    Generate SHAP (SHapley Additive exPlanations) values to explain why 
    a specific failure probability was predicted.

    Args:
        model: Trained CalibratedClassifierCV or GradientBoostingClassifier
        scaler: Fitted StandardScaler
        features_dict: {feature_name: value}
        feature_columns: Ordered list of feature names used by the model

    Returns:
        dict: feature_name -> impact_value (positive = increases risk, negative = decreases risk)
    """
    try:
        import importlib.util
        import sys

        bad_matplotlib = sys.modules.get("matplotlib")
        if bad_matplotlib is not None and not getattr(bad_matplotlib, "__path__", None):
            logger.debug(
                "Detected invalid matplotlib module in sys.modules; removing it so the real package can be imported."
            )
            del sys.modules["matplotlib"]
            if "matplotlib.colors" in sys.modules:
                del sys.modules["matplotlib.colors"]

        import shap
    except Exception as e:
        logger.warning(f"SHAP package unavailable or broken: {e}")
        try:
            shap_spec = importlib.util.find_spec("shap")
            matplotlib_spec = importlib.util.find_spec("matplotlib")
            matplotlib_colors_spec = importlib.util.find_spec("matplotlib.colors")
            logger.warning(f"shap spec={shap_spec}, matplotlib spec={matplotlib_spec}, matplotlib.colors spec={matplotlib_colors_spec}")
        except Exception as inspect_err:
            logger.warning(f"Failed inspecting shap/matplotlib specs: {inspect_err}")

        if hasattr(model, 'feature_importances_'):
            return {f: float(imp) for f, imp in zip(feature_columns, model.feature_importances_)}
        return {f: 0.0 for f in feature_columns}

    try:
        # 1. Prepare data
        features = np.array([[features_dict.get(f, 0) for f in feature_columns]])
        features_scaled = scaler.transform(features)

        # 2. Extract base estimator if calibrated
        base_model = model
        if hasattr(model, 'calibrated_classifiers_'):
            # Take the first base estimator from the calibration ensemble
            base_model = model.calibrated_classifiers_[0].estimator

        # If the estimator is multiclass GradientBoosting, SHAP TreeExplainer support is limited.
        if hasattr(base_model, 'classes_') and len(base_model.classes_) > 2:
            logger.debug(
                "SHAP explanation skipped for multiclass model; using feature importances fallback."
            )
            if hasattr(model, 'feature_importances_'):
                return {f: float(imp) for f, imp in zip(feature_columns, model.feature_importances_)}
            return {f: 0.0 for f in feature_columns}

        # 3. Compute SHAP values
        # TreeExplainer is fast for GradientBoosting/RandomForest
        explainer = shap.TreeExplainer(base_model)
        shap_values = explainer.shap_values(features_scaled)

        # shap_values might be a list (multiclass) or array (binary/regression)
        if isinstance(shap_values, list):
            # For classification, taking the values for the 'failure' class (usually index 1 or 2)
            target_class_idx = min(len(shap_values) - 1, 2)  # Assuming class 2 is Critical Failure
            impacts = shap_values[target_class_idx][0]
        else:
            # If 2D array, taking the only row
            impacts = shap_values[0]

        # 4. Map to feature names
        explanation = {feature_columns[i]: float(impacts[i]) for i in range(len(feature_columns))}
        
        # Sort by absolute impact for easier UI rendering
        explanation = dict(sorted(explanation.items(), key=lambda item: abs(item[1]), reverse=True))

        return explanation

    except Exception as e:
        logger.warning(f"Could not compute SHAP values: {e}")
        if hasattr(model, 'feature_importances_'):
            return {f: float(imp) for f, imp in zip(feature_columns, model.feature_importances_)}
        return {f: 0.0 for f in feature_columns}


def generate_whatif_curves(
    current_vib: float,
    current_temp: float,
    current_rpm: float,
    sim_vib: float,
    sim_temp: float,
    sim_rpm: float,
    days: int = 365
) -> pd.DataFrame:
    """
    Generate equipment health degradation curves for What-If analysis.

    Computes a baseline curve from current operating parameters and a simulated
    curve from the stressed parameters using an exponential degradation model
    that weights vibration, temperature, and RPM deviation.

    Args:
        current_vib: Baseline vibration (mm/s)
        current_temp: Baseline temperature (C)
        current_rpm: Baseline RPM
        sim_vib: Simulated vibration (mm/s)
        sim_temp: Simulated temperature (C)
        sim_rpm: Simulated RPM
        days: Projection horizon in days

    Returns:
        DataFrame with columns: Days, Baseline Health (%), Simulated Health (%)
    """
    time_axis = np.arange(0, days + 1)

    # Degradation rate coefficients (empirical industrial weights)
    VIB_WEIGHT  = 0.012   # contribution per mm/s per day
    TEMP_WEIGHT = 0.003   # contribution per degree C above 60 per day
    RPM_WEIGHT  = 0.0001  # contribution per RPM above 1500 per day

    def _rate(vib: float, temp: float, rpm: float) -> float:
        temp_excess = max(0.0, temp - 60.0)
        rpm_excess  = max(0.0, rpm - 1500.0)
        return VIB_WEIGHT * vib + TEMP_WEIGHT * temp_excess + RPM_WEIGHT * rpm_excess

    baseline_rate  = _rate(current_vib, current_temp, current_rpm)
    simulated_rate = _rate(sim_vib, sim_temp, sim_rpm)

    baseline_health  = np.clip(100.0 * np.exp(-baseline_rate  * time_axis / 100.0), 0.0, 100.0)
    simulated_health = np.clip(100.0 * np.exp(-simulated_rate * time_axis / 100.0), 0.0, 100.0)

    return pd.DataFrame({
        "Days":                  time_axis,
        "Baseline Health (%)":  baseline_health,
        "Simulated Health (%)": simulated_health,
    })

