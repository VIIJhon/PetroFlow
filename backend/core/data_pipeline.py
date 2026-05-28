"""
ETL Data Pipeline Module
Handles cleaning, standardization, and grouping of raw CMMS reports.
"""

import pandas as pd
import numpy as np

def clean_cmms_data(df: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """
    Cleans and standardizes raw CMMS data using a dynamic column mapping.
    
    Args:
        df: Raw pandas DataFrame.
        column_mapping: Dictionary where keys are internal variables 
                        (e.g., 'ID_Equipo', 'Fecha_Evento') and values 
                        are the actual column names in the df.
    Returns:
        Cleaned and standardized DataFrame.
    """
    # 1. Rename columns based on mapping
    # We invert the dictionary to map from Original -> Internal for pandas rename
    rename_dict = {v: k for k, v in column_mapping.items() if v is not None and v in df.columns}
    df_clean = df.rename(columns=rename_dict)
    
    # Keep only the mapped columns to strip away unnecessary data
    internal_cols = list(rename_dict.values())
    df_clean = df_clean[internal_cols].copy()
    
    # 2. Critical columns that cannot have nulls
    critical_cols = [col for col in ['ID_Equipo', 'Fecha_Evento', 'Tiempo_Operacion_Horas'] if col in df_clean.columns]
    
    # Drop rows with NaN in critical columns
    if critical_cols:
        df_clean.dropna(subset=critical_cols, inplace=True)
        
    # 3. Data Type Conversions
    if 'Fecha_Evento' in df_clean.columns:
        # Using infer_datetime_format to be flexible with various CMMS formats
        df_clean['Fecha_Evento'] = pd.to_datetime(df_clean['Fecha_Evento'], errors='coerce')
        # Drop rows where date parsing failed
        df_clean.dropna(subset=['Fecha_Evento'], inplace=True)
        
    if 'Tiempo_Operacion_Horas' in df_clean.columns:
        df_clean['Tiempo_Operacion_Horas'] = pd.to_numeric(df_clean['Tiempo_Operacion_Horas'], errors='coerce')
        
    if 'Tiempo_Reparacion_Horas' in df_clean.columns:
        df_clean['Tiempo_Reparacion_Horas'] = pd.to_numeric(df_clean['Tiempo_Reparacion_Horas'], errors='coerce')
        
    # Drop rows where numeric conversion failed for critical math fields
    if 'Tiempo_Operacion_Horas' in df_clean.columns:
        df_clean.dropna(subset=['Tiempo_Operacion_Horas'], inplace=True)

    return df_clean

def group_reliability_data(df: pd.DataFrame, group_by_column: str) -> dict:
    """
    Segments the cleaned DataFrame for independent reliability calculations.
    
    Args:
        df: Cleaned pandas DataFrame.
        group_by_column: Internal column name to group by (e.g., 'Modo_Falla').
    Returns:
        Dictionary where keys are the group names and values are the segmented DataFrames.
    """
    if group_by_column not in df.columns:
        raise ValueError(f"Column '{group_by_column}' not found in the dataset.")
        
    grouped_data = {}
    
    # Group by the specified column
    groups = df.groupby(group_by_column)
    
    for name, group_df in groups:
        # Convert name to string to ensure dict keys are clean
        grouped_data[str(name)] = group_df.copy()
        
    return grouped_data
