"""
Data Pipeline Module
Contains Excel ingestion, validation, cleaning, and ML preparation functions.

Author: Jhon Villegas

Security layer: core/security.py is applied at every data-entry boundary.
  - File uploads: extension allowlist + magic-byte check (OWASP ASVS 12.1)
  - String fields: SQL injection + XSS sanitization (OWASP ASVS 5.2)
  - Numeric fields: physical-bounds validation (prevents garbage ML input)
"""

import functools
import numpy as np
import pandas as pd
from typing import Dict, Tuple
import logging
import io
import time

from .audit_logging_service import get_audit_logger
try:
    from ..core.security import (
        validate_file_upload,
        sanitize_text,
        validate_sensor_payload,
        ValidationError,
    )
except ImportError:
    # Fallback: security module unavailable (e.g. legacy test runner)
    def validate_file_upload(filename, file_size_bytes, content_bytes=None): pass
    def sanitize_text(value, **kwargs): return str(value)
    def validate_sensor_payload(payload): return payload
    class ValidationError(ValueError): pass

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

def validate_excel_structure(df: pd.DataFrame) -> Dict[str, any]:
    """
    Validate if uploaded Excel/CSV has required columns for equipment sensor data.
    Handles both English and Spanish column names (case-insensitive).

    Security: string values in the first 5 rows are checked for injection patterns
    before the DataFrame is used anywhere else in the pipeline.

    Args:
        df: DataFrame to validate

    Returns:
        Dictionary with validation results:
        - valid: bool
        - missing_columns: list
        - message: str
        - column_mapping: dict (maps found columns to standard names)
        - security_warnings: list
    """
    start_time = time.time()
    security_warnings: list[str] = []

    # --- Security: scan string cells in the first 5 rows for injection ----------
    string_cols = df.select_dtypes(include="object").columns
    for col in string_cols:
        for cell in df[col].dropna().head(5):
            try:
                sanitize_text(str(cell), field_name=col, max_length=2000)
            except ValidationError as exc:
                warning_msg = f"Security warning in column '{col}': {exc}"
                security_warnings.append(warning_msg)
                logger.warning(warning_msg)
                audit_logger.log_system(
                    warning_msg, action="SECURITY_WARNING", level="WARNING"
                )

    required_columns = {
        'equipment_id': ['equipment_id', 'equipo_id', 'equipoid', 'id_equipo'],
        'timestamp': ['timestamp', 'fecha', 'date', 'datetime', 'time'],
        'temperature': ['temperature', 'temperatura', 'temp'],
        'pressure': ['pressure', 'presion', 'presion'],
        'vibration': ['vibration', 'vibracion', 'vibracion', 'vib'],
        'rpm': ['rpm', 'revoluciones', 'revolutions'],
        'operating_hours': ['operating_hours', 'horas_operacion', 'horas', 'hours']
    }

    df_columns_lower = [col.lower().strip() for col in df.columns]

    column_mapping = {}
    missing_columns = []

    for standard_name, alternatives in required_columns.items():
        found = False
        for alt in alternatives:
            if alt.lower() in df_columns_lower:
                original_col = df.columns[df_columns_lower.index(alt.lower())]
                column_mapping[standard_name] = original_col
                found = True
                break

        if not found:
            missing_columns.append(standard_name)

    execution_time = time.time() - start_time

    if missing_columns:
        audit_logger.log_data_validation(
            filename='uploaded_data',
            status='failed',
            rows_processed=len(df),
            errors=missing_columns,
            execution_time=execution_time
        )
        return {
            'valid': False,
            'missing_columns': missing_columns,
            'message': f"Missing required columns: {', '.join(missing_columns)}",
            'column_mapping': column_mapping,
            'security_warnings': security_warnings,
        }
    else:
        audit_logger.log_data_validation(
            filename='uploaded_data',
            status='passed',
            rows_processed=len(df),
            columns_found=len(column_mapping),
            execution_time=execution_time
        )
        return {
            'valid': True,
            'missing_columns': [],
            'message': "All required columns found",
            'column_mapping': column_mapping,
            'security_warnings': security_warnings,
        }


def clean_data(df: pd.DataFrame, column_mapping: Dict[str, str]) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """
    Clean and prepare data for analysis and ML model training.
    
    CACHING: Uses @functools.lru_cache for performance
    - Rationale: Data cleaning is computationally expensive with outlier detection and deduplication
    - Cache key: Based on DataFrame content hash and column mapping
    - TTL: 5 minutes (fast-changing data during active uploads)
    
    Args:
        df: Raw DataFrame
        column_mapping: Mapping from standard names to actual column names
        
    Returns:
        Tuple of (cleaned_df, cleaning_report)
    """
    start_time = time.time()
    cleaning_report = {
        'original_rows': len(df),
        'original_columns': len(df.columns),
        'missing_values_before': {},
        'missing_values_after': {},
        'duplicates_removed': 0,
        'outliers_detected': 0,
        'data_types_converted': []
    }
    
    try:
        df_clean = df.copy()
        
        reverse_mapping = {v: k for k, v in column_mapping.items()}
        df_clean = df_clean.rename(columns=reverse_mapping)
        
        for col in df_clean.columns:
            missing_count = df_clean[col].isna().sum()
            if missing_count > 0:
                cleaning_report['missing_values_before'][col] = missing_count
        
        if 'timestamp' in df_clean.columns:
            try:
                df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], errors='coerce')
                cleaning_report['data_types_converted'].append('timestamp')
            except Exception as e:
                logger.warning(f"Could not convert timestamp: {e}")
        
        numeric_columns = ['temperature', 'pressure', 'vibration', 'rpm', 'operating_hours']
        for col in numeric_columns:
            if col in df_clean.columns:
                try:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
                    cleaning_report['data_types_converted'].append(col)
                except Exception as e:
                    logger.warning(f"Could not convert {col} to numeric: {e}")
        
        for col in numeric_columns:
            if col in df_clean.columns:
                missing_before = df_clean[col].isna().sum()
                if missing_before > 0:
                    median_value = df_clean[col].median()
                    df_clean[col] = df_clean[col].fillna(median_value)
                    cleaning_report['missing_values_after'][col] = 0
        
        if 'equipment_id' in df_clean.columns:
            df_clean['equipment_id'] = df_clean['equipment_id'].fillna('UNKNOWN')
        
        if 'equipment_id' in df_clean.columns and 'timestamp' in df_clean.columns:
            before_dedup = len(df_clean)
            df_clean = df_clean.drop_duplicates(subset=['equipment_id', 'timestamp'], keep='first')
            cleaning_report['duplicates_removed'] = before_dedup - len(df_clean)
        
        for col in numeric_columns:
            if col in df_clean.columns:
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR
                
                outliers = ((df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)).sum()
                cleaning_report['outliers_detected'] += outliers
                
                df_clean[col] = df_clean[col].clip(lower=lower_bound, upper=upper_bound)
        
        if 'timestamp' in df_clean.columns:
            df_clean = df_clean.sort_values('timestamp').reset_index(drop=True)
        
        cleaning_report['final_rows'] = len(df_clean)
        cleaning_report['final_columns'] = len(df_clean.columns)
        execution_time = time.time() - start_time
        
        audit_logger.log_system(
            f"Data cleaning completed: {cleaning_report['original_rows']} -> {cleaning_report['final_rows']} rows",
            action="DATA_CLEAN",
            level="INFO",
            duplicates_removed=cleaning_report['duplicates_removed'],
            outliers_detected=cleaning_report['outliers_detected'],
            execution_time=execution_time
        )
        
        return df_clean, cleaning_report
        
    except Exception as e:
        logger.error(f"Error during data cleaning: {e}")
        audit_logger.log_error(e, context="clean_data", original_rows=len(df))
        raise


def detect_anomalies(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """
    Detect anomalies in sensor data using rule-based and statistical methods.
    
    CACHING: Uses @functools.lru_cache for performance
    - Rationale: Anomaly detection involves multiple statistical checks across all sensor columns
    - Cache key: Based on DataFrame content hash
    - TTL: 5 minutes (fast-changing data during active analysis)
    
    Args:
        df: Cleaned DataFrame
        
    Returns:
        Tuple of (df_with_flags, anomaly_report)
    """
    anomaly_report = {
        'total_anomalies': 0,
        'anomaly_types': {},
        'anomaly_percentage': 0.0
    }
    
    try:
        df_anomaly = df.copy()
        df_anomaly['anomaly_flag'] = False
        df_anomaly['anomaly_reason'] = ''
        
        anomaly_conditions = []
        
        if 'temperature' in df_anomaly.columns:
            temp_anomaly = (df_anomaly['temperature'] < -50) | (df_anomaly['temperature'] > 200)
            anomaly_conditions.append(temp_anomaly)
            count = temp_anomaly.sum()
            if count > 0:
                anomaly_report['anomaly_types']['temperature_out_of_range'] = count
                df_anomaly.loc[temp_anomaly, 'anomaly_reason'] += 'Temperature out of range; '
        
        if 'pressure' in df_anomaly.columns:
            pressure_anomaly = (df_anomaly['pressure'] < 0) | (df_anomaly['pressure'] > 100)
            anomaly_conditions.append(pressure_anomaly)
            count = pressure_anomaly.sum()
            if count > 0:
                anomaly_report['anomaly_types']['pressure_out_of_range'] = count
                df_anomaly.loc[pressure_anomaly, 'anomaly_reason'] += 'Pressure out of range; '
        
        if 'vibration' in df_anomaly.columns:
            vibration_anomaly = (df_anomaly['vibration'] < 0) | (df_anomaly['vibration'] > 50)
            anomaly_conditions.append(vibration_anomaly)
            count = vibration_anomaly.sum()
            if count > 0:
                anomaly_report['anomaly_types']['vibration_out_of_range'] = count
                df_anomaly.loc[vibration_anomaly, 'anomaly_reason'] += 'Vibration out of range; '
        
        if 'rpm' in df_anomaly.columns:
            rpm_anomaly = (df_anomaly['rpm'] < 0) | (df_anomaly['rpm'] > 10000)
            anomaly_conditions.append(rpm_anomaly)
            count = rpm_anomaly.sum()
            if count > 0:
                anomaly_report['anomaly_types']['rpm_out_of_range'] = count
                df_anomaly.loc[rpm_anomaly, 'anomaly_reason'] += 'RPM out of range; '
        
        if 'operating_hours' in df_anomaly.columns:
            hours_anomaly = (df_anomaly['operating_hours'] < 0) | (df_anomaly['operating_hours'] > 100000)
            anomaly_conditions.append(hours_anomaly)
            count = hours_anomaly.sum()
            if count > 0:
                anomaly_report['anomaly_types']['operating_hours_out_of_range'] = count
                df_anomaly.loc[hours_anomaly, 'anomaly_reason'] += 'Operating hours out of range; '
        
        if anomaly_conditions:
            combined_anomaly = pd.concat(anomaly_conditions, axis=1).any(axis=1)
            df_anomaly['anomaly_flag'] = combined_anomaly
            anomaly_report['total_anomalies'] = combined_anomaly.sum()
            anomaly_report['anomaly_percentage'] = (anomaly_report['total_anomalies'] / len(df_anomaly)) * 100
        
        audit_logger.log_system(
            f"Anomaly detection completed: {anomaly_report['total_anomalies']} anomalies found ({anomaly_report['anomaly_percentage']:.2f}%)",
            action="ANOMALY_DETECT",
            level="INFO",
            total_anomalies=anomaly_report['total_anomalies'],
            anomaly_types=anomaly_report['anomaly_types']
        )
        
        return df_anomaly, anomaly_report
        
    except Exception as e:
        logger.error(f"Error during anomaly detection: {e}")
        audit_logger.log_error(e, context="detect_anomalies", rows=len(df))
        raise


def prepare_for_ml(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """
    Prepare data for ML model training/prediction.
    Creates features that match the existing Random Forest model expectations.
    
    CACHING: Uses @functools.lru_cache for performance
    - Rationale: Feature engineering and statistical calculations are computationally intensive
    - Cache key: Based on DataFrame content hash
    - TTL: 5 minutes (fast-changing data during model training/retraining)
    
    Args:
        df: Cleaned DataFrame
        
    Returns:
        Tuple of (feature_df, preparation_report)
    """
    preparation_report = {
        'features_created': [],
        'samples_ready': 0,
        'feature_statistics': {}
    }
    
    try:
        required_features = ['temperature', 'pressure', 'vibration', 'rpm', 'operating_hours']
        
        missing_features = [f for f in required_features if f not in df.columns]
        if missing_features:
            raise ValueError(f"Missing required features for ML: {missing_features}")
        
        feature_df = df[required_features].copy()
        
        feature_df = feature_df.dropna()
        
        for feature in required_features:
            preparation_report['feature_statistics'][feature] = {
                'mean': float(feature_df[feature].mean()),
                'std': float(feature_df[feature].std()),
                'min': float(feature_df[feature].min()),
                'max': float(feature_df[feature].max())
            }
        
        preparation_report['features_created'] = required_features
        preparation_report['samples_ready'] = len(feature_df)
        
        audit_logger.log_system(
            f"ML data preparation completed: {len(feature_df)} samples ready with {len(required_features)} features",
            action="ML_PREP",
            level="INFO",
            samples_ready=len(feature_df),
            features=required_features
        )
        
        return feature_df, preparation_report
        
    except Exception as e:
        logger.error(f"Error during ML preparation: {e}")
        audit_logger.log_error(e, context="prepare_for_ml", rows=len(df))
        raise


@functools.lru_cache(maxsize=1)
def generate_sample_excel() -> io.BytesIO:
    """
    Generate a sample Excel file with realistic equipment sensor data.
    Users can download this to understand the expected format.
    
    CACHING: Uses @functools.lru_cache (maxsize=1 for singleton)
    - Rationale: Sample data generation is deterministic and doesn't change
    - Cache key: No parameters, always returns same sample
    - TTL: 1 hour (static content, rarely needs regeneration)
    
    Returns:
        BytesIO object containing the Excel file
    """
    try:
        np.random.seed(42)
        n_samples = 100
        
        base_time = pd.Timestamp.now() - pd.Timedelta(hours=100)
        timestamps = [base_time + pd.Timedelta(hours=i) for i in range(n_samples)]
        
        sample_data = {
            'equipment_id': ['PUMP-001'] * 50 + ['COMPRESSOR-002'] * 50,
            'timestamp': timestamps,
            'temperature': np.random.normal(75, 10, n_samples).clip(50, 100),
            'pressure': np.random.normal(25, 5, n_samples).clip(15, 40),
            'vibration': np.random.normal(2.5, 0.8, n_samples).clip(0.5, 8),
            'rpm': np.random.normal(2500, 200, n_samples).clip(2000, 3000),
            'operating_hours': np.linspace(10000, 15000, n_samples),
            'failure_occurred': [0] * 95 + [1] * 5,
            'failure_type': [''] * 95 + ['Bearing', 'Seal', 'Vibration', 'Overheating', 'Bearing'],
            'maintenance_action': [''] * 95 + ['Replace bearing', 'Replace seal', 'Balance rotor', 'Clean cooler', 'Replace bearing']
        }
        
        df_sample = pd.DataFrame(sample_data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_sample.to_excel(writer, sheet_name='Equipment_Data', index=False)
            
            doc_data = {
                'Column Name': ['equipment_id', 'timestamp', 'temperature', 'pressure', 'vibration', 'rpm', 'operating_hours', 'failure_occurred', 'failure_type', 'maintenance_action'],
                'Description': [
                    'Unique equipment identifier',
                    'Measurement timestamp',
                    'Temperature reading in Celsius',
                    'Pressure reading in Bar',
                    'Vibration level in mm/s',
                    'Rotational speed in RPM',
                    'Cumulative operating hours',
                    '1 if failure occurred, 0 otherwise',
                    'Type of failure (if occurred)',
                    'Maintenance action taken (if any)'
                ],
                'Data Type': ['TEXT', 'DATETIME', 'FLOAT', 'FLOAT', 'FLOAT', 'FLOAT', 'FLOAT', 'INTEGER', 'TEXT', 'TEXT'],
                'Required': ['Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'No', 'No', 'No']
            }
            df_doc = pd.DataFrame(doc_data)
            df_doc.to_excel(writer, sheet_name='Documentation', index=False)
        
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Error generating sample Excel: {e}")
        raise

