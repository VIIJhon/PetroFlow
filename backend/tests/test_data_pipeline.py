"""
Unit tests for data_pipeline.py
Covers:
  - Excel structure validation (English & Spanish column aliases)
  - Missing column detection
  - Data cleaning (type coercion, null imputation, deduplication, outlier clipping)
  - Anomaly detection (rule-based out-of-range flags)
  - ML feature preparation (required features, no nulls, statistics)
  - Sample Excel generation (BytesIO output, content validation)
  - Robustness against corrupted / empty inputs
"""

import pytest
import io
import numpy as np
import pandas as pd
from unittest.mock import patch


# Streamlit is already mocked in conftest.py
from core.excel_data_ingestion import (
    validate_excel_structure,
    clean_data,
    detect_anomalies,
    prepare_for_ml,
    generate_sample_excel,
)


# ===========================================================================
# 1. validate_excel_structure
# ===========================================================================

class TestValidateExcelStructure:

    @pytest.mark.unit
    def test_valid_english_df_passes(self, valid_sensor_df):
        result = validate_excel_structure(valid_sensor_df)
        assert result["valid"] is True
        assert result["missing_columns"] == []

    @pytest.mark.unit
    def test_valid_spanish_df_passes(self, valid_sensor_df_spanish):
        result = validate_excel_structure(valid_sensor_df_spanish)
        assert result["valid"] is True
        assert result["missing_columns"] == []

    @pytest.mark.unit
    def test_missing_columns_detected(self, missing_columns_df):
        result = validate_excel_structure(missing_columns_df)
        assert result["valid"] is False
        assert len(result["missing_columns"]) > 0

    @pytest.mark.unit
    def test_missing_columns_list_content(self, missing_columns_df):
        """temperature is present but others are missing."""
        result = validate_excel_structure(missing_columns_df)
        assert "temperature" not in result["missing_columns"]
        assert "pressure" in result["missing_columns"]

    @pytest.mark.unit
    def test_column_mapping_populated(self, valid_sensor_df):
        result = validate_excel_structure(valid_sensor_df)
        assert len(result["column_mapping"]) == 7  # All 7 required fields mapped

    @pytest.mark.unit
    def test_column_mapping_standard_names(self, valid_sensor_df):
        result = validate_excel_structure(valid_sensor_df)
        expected_keys = {
            "equipment_id", "timestamp", "temperature",
            "pressure", "vibration", "rpm", "operating_hours",
        }
        assert expected_keys == set(result["column_mapping"].keys())

    @pytest.mark.unit
    def test_message_contains_missing_names(self, missing_columns_df):
        result = validate_excel_structure(missing_columns_df)
        for col in result["missing_columns"]:
            assert col in result["message"]

    @pytest.mark.unit
    def test_case_insensitive_matching(self):
        df = pd.DataFrame({
            "EQUIPMENT_ID": ["X"],
            "TIMESTAMP": ["2024-01-01"],
            "TEMPERATURE": [70.0],
            "PRESSURE": [25.0],
            "VIBRATION": [2.0],
            "RPM": [2500.0],
            "OPERATING_HOURS": [5000.0],
        })
        result = validate_excel_structure(df)
        assert result["valid"] is True

    @pytest.mark.unit
    def test_empty_dataframe_reports_all_missing(self):
        df = pd.DataFrame()
        result = validate_excel_structure(df)
        assert result["valid"] is False
        assert len(result["missing_columns"]) == 7


# ===========================================================================
# 2. clean_data
# ===========================================================================

class TestCleanData:

    @pytest.fixture
    def mapped_df(self, valid_sensor_df):
        """Provide a pre-validated mapping for valid_sensor_df."""
        result = validate_excel_structure(valid_sensor_df)
        return valid_sensor_df, result["column_mapping"]

    @pytest.mark.unit
    def test_returns_tuple(self, mapped_df):
        df, mapping = mapped_df
        cleaned, report = clean_data(df, mapping)
        assert isinstance(cleaned, pd.DataFrame)
        assert isinstance(report, dict)

    @pytest.mark.unit
    def test_no_nulls_in_numeric_columns(self, mapped_df):
        df, mapping = mapped_df
        cleaned, _ = clean_data(df, mapping)
        numeric_cols = ["temperature", "pressure", "vibration", "rpm", "operating_hours"]
        for col in numeric_cols:
            if col in cleaned.columns:
                assert cleaned[col].isna().sum() == 0

    @pytest.mark.unit
    def test_report_contains_expected_keys(self, mapped_df):
        df, mapping = mapped_df
        _, report = clean_data(df, mapping)
        expected_keys = {
            "original_rows", "original_columns", "duplicates_removed",
            "outliers_detected", "data_types_converted",
        }
        assert expected_keys.issubset(set(report.keys()))

    @pytest.mark.unit
    def test_duplicates_removed(self):
        """Duplicate (equipment_id, timestamp) rows should be removed."""
        ts = pd.Timestamp("2024-01-01 00:00:00")
        df = pd.DataFrame({
            "equipment_id": ["PUMP-001", "PUMP-001", "PUMP-002"],
            "timestamp": [ts, ts, ts],
            "temperature": [70.0, 70.0, 75.0],
            "pressure": [25.0, 25.0, 26.0],
            "vibration": [2.5, 2.5, 2.8],
            "rpm": [2500.0, 2500.0, 2600.0],
            "operating_hours": [5000.0, 5000.0, 5100.0],
        })
        mapping = {
            "equipment_id": "equipment_id", "timestamp": "timestamp",
            "temperature": "temperature", "pressure": "pressure",
            "vibration": "vibration", "rpm": "rpm",
            "operating_hours": "operating_hours",
        }
        cleaned, report = clean_data(df, mapping)
        assert report["duplicates_removed"] >= 1
        assert len(cleaned) < len(df)

    @pytest.mark.unit
    def test_outliers_clipped(self):
        """Extreme outlier should be clipped, not produce NaN."""
        df = pd.DataFrame({
            "equipment_id": ["PUMP-001"] * 30,
            "timestamp": pd.date_range("2024-01-01", periods=30, freq="h"),
            "temperature": [70.0] * 29 + [99999.0],   # Extreme outlier
            "pressure": [25.0] * 30,
            "vibration": [2.5] * 30,
            "rpm": [2500.0] * 30,
            "operating_hours": [5000.0] * 30,
        })
        mapping = {k: k for k in df.columns}
        cleaned, report = clean_data(df, mapping)
        assert cleaned["temperature"].isna().sum() == 0
        assert cleaned["temperature"].max() < 99999.0

    @pytest.mark.unit
    def test_timestamp_converted_to_datetime(self, mapped_df):
        df, mapping = mapped_df
        cleaned, _ = clean_data(df, mapping)
        if "timestamp" in cleaned.columns:
            assert pd.api.types.is_datetime64_any_dtype(cleaned["timestamp"])

    @pytest.mark.unit
    def test_data_sorted_by_timestamp(self, mapped_df):
        df, mapping = mapped_df
        cleaned, _ = clean_data(df.sample(frac=1, random_state=7), mapping)
        if "timestamp" in cleaned.columns:
            ts = cleaned["timestamp"].dropna()
            assert (ts.values[:-1] <= ts.values[1:]).all()

    @pytest.mark.unit
    def test_corrupted_df_numeric_coercion(self, corrupted_sensor_df):
        """
        After cleaning, numeric columns should not contain string 'INVALID' values.
        The clean_data function should coerce, not crash.
        """
        result = validate_excel_structure(corrupted_sensor_df)
        if result["valid"]:
            cleaned, report = clean_data(corrupted_sensor_df, result["column_mapping"])
            assert isinstance(cleaned, pd.DataFrame)
            # No raw non-numeric values should remain
            for col in ["temperature", "pressure", "vibration", "rpm", "operating_hours"]:
                if col in cleaned.columns:
                    assert pd.to_numeric(cleaned[col], errors="coerce").isna().sum() == 0


# ===========================================================================
# 3. detect_anomalies
# ===========================================================================

class TestDetectAnomalies:

    @pytest.fixture
    def cleaned_df(self, valid_sensor_df):
        result = validate_excel_structure(valid_sensor_df)
        cleaned, _ = clean_data(valid_sensor_df, result["column_mapping"])
        return cleaned

    @pytest.mark.unit
    def test_returns_tuple_df_and_report(self, cleaned_df):
        df_flagged, report = detect_anomalies(cleaned_df)
        assert isinstance(df_flagged, pd.DataFrame)
        assert isinstance(report, dict)

    @pytest.mark.unit
    def test_anomaly_flag_column_created(self, cleaned_df):
        df_flagged, _ = detect_anomalies(cleaned_df)
        assert "anomaly_flag" in df_flagged.columns

    @pytest.mark.unit
    def test_anomaly_reason_column_created(self, cleaned_df):
        df_flagged, _ = detect_anomalies(cleaned_df)
        assert "anomaly_reason" in df_flagged.columns

    @pytest.mark.unit
    def test_normal_data_has_no_anomalies(self, cleaned_df):
        """Clean normal-range data should produce zero anomalies."""
        df_flagged, report = detect_anomalies(cleaned_df)
        # Valid sensor data after cleaning should have 0 anomalies
        assert report["total_anomalies"] == 0

    @pytest.mark.unit
    def test_out_of_range_temperature_flagged(self):
        """Temperature > 200 should trigger anomaly flag."""
        df = pd.DataFrame({
            "temperature": [300.0, 70.0],   # 300 is out of range
            "pressure": [25.0, 25.0],
            "vibration": [2.5, 2.5],
            "rpm": [2500.0, 2500.0],
            "operating_hours": [5000.0, 5000.0],
        })
        df_flagged, report = detect_anomalies(df)
        assert report["total_anomalies"] >= 1
        assert df_flagged.loc[0, "anomaly_flag"] is True or df_flagged.loc[0, "anomaly_flag"] == True

    @pytest.mark.unit
    def test_negative_pressure_flagged(self):
        df = pd.DataFrame({
            "temperature": [70.0],
            "pressure": [-5.0],   # Negative pressure
            "vibration": [2.5],
            "rpm": [2500.0],
            "operating_hours": [5000.0],
        })
        df_flagged, report = detect_anomalies(df)
        assert report["total_anomalies"] >= 1

    @pytest.mark.unit
    def test_out_of_range_vibration_flagged(self):
        df = pd.DataFrame({
            "temperature": [70.0],
            "pressure": [25.0],
            "vibration": [100.0],   # Max is 50
            "rpm": [2500.0],
            "operating_hours": [5000.0],
        })
        df_flagged, report = detect_anomalies(df)
        assert report["total_anomalies"] >= 1

    @pytest.mark.unit
    def test_report_anomaly_percentage_calculation(self):
        df = pd.DataFrame({
            "temperature": [300.0, 70.0, 75.0, 72.0],  # 1 anomaly out of 4
        })
        _, report = detect_anomalies(df)
        if report["total_anomalies"] > 0:
            assert 0.0 < report["anomaly_percentage"] <= 100.0

    @pytest.mark.unit
    def test_report_contains_required_keys(self, cleaned_df):
        _, report = detect_anomalies(cleaned_df)
        assert "total_anomalies" in report
        assert "anomaly_types" in report
        assert "anomaly_percentage" in report


# ===========================================================================
# 4. prepare_for_ml
# ===========================================================================

class TestPrepareForMl:

    @pytest.fixture
    def cleaned_df(self, valid_sensor_df):
        result = validate_excel_structure(valid_sensor_df)
        cleaned, _ = clean_data(valid_sensor_df, result["column_mapping"])
        return cleaned

    @pytest.mark.unit
    def test_returns_tuple(self, cleaned_df):
        feature_df, report = prepare_for_ml(cleaned_df)
        assert isinstance(feature_df, pd.DataFrame)
        assert isinstance(report, dict)

    @pytest.mark.unit
    def test_output_contains_required_features(self, cleaned_df):
        feature_df, _ = prepare_for_ml(cleaned_df)
        required = {"temperature", "pressure", "vibration", "rpm", "operating_hours"}
        assert required.issubset(set(feature_df.columns))

    @pytest.mark.unit
    def test_no_null_values_in_output(self, cleaned_df):
        feature_df, _ = prepare_for_ml(cleaned_df)
        assert not feature_df.isnull().any().any()

    @pytest.mark.unit
    def test_samples_ready_count_correct(self, cleaned_df):
        feature_df, report = prepare_for_ml(cleaned_df)
        assert report["samples_ready"] == len(feature_df)

    @pytest.mark.unit
    def test_feature_statistics_present(self, cleaned_df):
        _, report = prepare_for_ml(cleaned_df)
        for feature in ["temperature", "pressure", "vibration", "rpm", "operating_hours"]:
            assert feature in report["feature_statistics"]
            stats = report["feature_statistics"][feature]
            assert "mean" in stats and "std" in stats
            assert "min" in stats and "max" in stats

    @pytest.mark.unit
    def test_missing_required_feature_raises_value_error(self):
        df = pd.DataFrame({
            "temperature": [70.0, 75.0],
            "pressure": [25.0, 26.0],
            # Missing: vibration, rpm, operating_hours
        })
        with pytest.raises(ValueError, match="Missing required features"):
            prepare_for_ml(df)

    @pytest.mark.unit
    def test_features_created_list(self, cleaned_df):
        _, report = prepare_for_ml(cleaned_df)
        assert "features_created" in report
        assert len(report["features_created"]) == 5


# ===========================================================================
# 5. generate_sample_excel
# ===========================================================================

class TestGenerateSampleExcel:

    @pytest.mark.unit
    def test_returns_bytes_io(self):
        result = generate_sample_excel()
        assert isinstance(result, io.BytesIO)

    @pytest.mark.unit
    def test_output_is_readable_excel(self):
        result = generate_sample_excel()
        df = pd.read_excel(result, sheet_name="Equipment_Data")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    @pytest.mark.unit
    def test_equipment_data_has_required_columns(self):
        result = generate_sample_excel()
        df = pd.read_excel(result, sheet_name="Equipment_Data")
        required = {"equipment_id", "timestamp", "temperature", "pressure",
                    "vibration", "rpm", "operating_hours"}
        assert required.issubset(set(df.columns))

    @pytest.mark.unit
    def test_documentation_sheet_exists(self):
        result = generate_sample_excel()
        sheets = pd.ExcelFile(result).sheet_names
        assert "Documentation" in sheets

    @pytest.mark.unit
    def test_sample_row_count(self):
        result = generate_sample_excel()
        df = pd.read_excel(result, sheet_name="Equipment_Data")
        assert len(df) == 100

    @pytest.mark.unit
    def test_temperature_values_in_valid_range(self):
        result = generate_sample_excel()
        df = pd.read_excel(result, sheet_name="Equipment_Data")
        assert df["temperature"].between(0, 200).all()

    @pytest.mark.unit
    def test_two_equipment_ids_present(self):
        result = generate_sample_excel()
        df = pd.read_excel(result, sheet_name="Equipment_Data")
        assert df["equipment_id"].nunique() == 2

    @pytest.mark.unit
    def test_deterministic_output(self):
        """
        Two calls to generate_sample_excel should produce identical numeric data.
        Timestamps are excluded since they are based on pd.Timestamp.now().
        """
        result1 = generate_sample_excel()
        result2 = generate_sample_excel()
        df1 = pd.read_excel(result1, sheet_name="Equipment_Data")
        df2 = pd.read_excel(result2, sheet_name="Equipment_Data")
        # Compare numeric columns only (timestamp uses now() so may differ)
        numeric_cols = ["temperature", "pressure", "vibration", "rpm", "operating_hours"]
        pd.testing.assert_frame_equal(
            df1[numeric_cols].reset_index(drop=True),
            df2[numeric_cols].reset_index(drop=True),
        )
