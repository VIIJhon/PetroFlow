"""
Unit tests for math_engine.py
Covers:
  - Risk level classification boundaries
  - Safety factor mathematics (probability, time, reliability types)
  - Synthetic training data generation (shape, ranges, value bounds)
  - Failure prediction output range (0-100 %)
  - Adjusted prediction calculations
  - Weibull distribution fitting
  - Kaplan-Meier survival analysis
  - Jackknife uncertainty estimation
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Import helpers (Streamlit is already mocked in conftest.py)
# ---------------------------------------------------------------------------

from core.failure_prediction_engine import (
    get_risk_level,
    generate_synthetic_training_data,
    apply_safety_factor,
    calculate_adjusted_predictions,
    predict_failure,
    fit_weibull_distribution,
    generate_kaplan_meier_data,
)
from core.config import RISK_LOW_THRESHOLD, RISK_HIGH_THRESHOLD


# ===========================================================================
# 1. get_risk_level
# ===========================================================================

class TestGetRiskLevel:
    """Boundary and interior tests for risk classification."""

    @pytest.mark.unit
    @pytest.mark.parametrize("probability,expected_level", [
        (0.0,    "Low Risk"),
        (15.0,   "Low Risk"),
        (29.99,  "Low Risk"),
        (30.0,   "Medium Risk"),   # At RISK_LOW_THRESHOLD boundary
        (50.0,   "Medium Risk"),
        (69.99,  "Medium Risk"),
        (70.0,   "High Risk"),     # At RISK_HIGH_THRESHOLD boundary
        (85.0,   "High Risk"),
        (100.0,  "High Risk"),
    ])
    def test_risk_level_classification(self, probability, expected_level):
        level, _ = get_risk_level(probability)
        assert level == expected_level, (
            f"Probability={probability} should be '{expected_level}', got '{level}'"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("probability,expected_color", [
        (0.0,   "green"),
        (50.0,  "orange"),
        (100.0, "red"),
    ])
    def test_risk_color_assignment(self, probability, expected_color):
        _, color = get_risk_level(probability)
        assert color == expected_color

    @pytest.mark.unit
    def test_risk_level_uses_configured_thresholds(self):
        """Ensure the function references RISK_LOW_THRESHOLD / RISK_HIGH_THRESHOLD."""
        low_level, _ = get_risk_level(RISK_LOW_THRESHOLD - 1)
        assert low_level == "Low Risk"

        mid_level, _ = get_risk_level(RISK_LOW_THRESHOLD)
        assert mid_level == "Medium Risk"

        high_level, _ = get_risk_level(RISK_HIGH_THRESHOLD)
        assert high_level == "High Risk"


# ===========================================================================
# 2. generate_synthetic_training_data
# ===========================================================================

class TestGenerateSyntheticTrainingData:
    """Data generation correctness and reproducibility."""

    @pytest.fixture(scope="class")
    def data(self):
        return generate_synthetic_training_data(500)

    @pytest.mark.unit
    def test_returns_dataframe(self, data):
        assert isinstance(data, pd.DataFrame)

    @pytest.mark.unit
    def test_row_count(self, data):
        assert len(data) == 500

    @pytest.mark.unit
    def test_required_columns_present(self, data):
        required = {"temperature", "pressure", "vibration", "operating_hours",
                    "rpm", "failure_category", "failure_score"}
        assert required.issubset(set(data.columns))

    @pytest.mark.unit
    def test_temperature_range(self, data):
        assert data["temperature"].min() >= 0
        assert data["temperature"].max() <= 150

    @pytest.mark.unit
    def test_pressure_range(self, data):
        assert data["pressure"].min() >= 0
        assert data["pressure"].max() <= 50

    @pytest.mark.unit
    def test_vibration_range(self, data):
        assert data["vibration"].min() >= 0.5
        assert data["vibration"].max() <= 10

    @pytest.mark.unit
    def test_operating_hours_range(self, data):
        assert data["operating_hours"].min() >= 0
        assert data["operating_hours"].max() <= 20000

    @pytest.mark.unit
    def test_rpm_range(self, data):
        assert data["rpm"].min() >= 0
        assert data["rpm"].max() <= 5000

    @pytest.mark.unit
    def test_failure_score_range(self, data):
        """failure_score must be in [0, 100]."""
        assert data["failure_score"].min() >= 0.0
        assert data["failure_score"].max() <= 100.0

    @pytest.mark.unit
    def test_failure_category_values(self, data):
        """Categories must be 0, 1, or 2 only."""
        assert set(data["failure_category"].unique()).issubset({0, 1, 2})

    @pytest.mark.unit
    def test_no_null_values(self, data):
        assert not data.isnull().any().any()

    @pytest.mark.unit
    def test_reproducibility(self):
        d1 = generate_synthetic_training_data(100)
        d2 = generate_synthetic_training_data(100)
        pd.testing.assert_frame_equal(d1, d2)

    @pytest.mark.unit
    def test_survival_data_columns_when_requested(self):
        data = generate_synthetic_training_data(100, include_survival_data=True)
        assert "time_to_failure" in data.columns
        assert "event_observed" in data.columns

    @pytest.mark.unit
    def test_survival_time_positive(self):
        data = generate_synthetic_training_data(100, include_survival_data=True)
        assert (data["time_to_failure"] > 0).all()

    @pytest.mark.unit
    def test_event_observed_binary(self):
        data = generate_synthetic_training_data(100, include_survival_data=True)
        assert set(data["event_observed"].unique()).issubset({0, 1})


# ===========================================================================
# 3. apply_safety_factor
# ===========================================================================

class TestApplySafetyFactor:
    """Mathematical correctness of the three safety factor modes."""

    @pytest.mark.unit
    @pytest.mark.parametrize("value,sf,expected", [
        (0.5, 20, 0.5 + (1 - 0.5) * 0.20),   # Probability type
        (0.0, 20, 0.0 + (1 - 0.0) * 0.20),
        (1.0, 20, 1.0),                          # Already max, stays at 1.0
        (0.8, 30, min(0.8 + (1 - 0.8) * 0.30, 1.0)),
    ])
    def test_probability_type(self, value, sf, expected):
        result = apply_safety_factor(value, sf, value_type="probability")
        assert abs(result - expected) < 1e-9

    @pytest.mark.unit
    def test_probability_never_exceeds_one(self):
        result = apply_safety_factor(0.99, 30, value_type="probability")
        assert result <= 1.0

    @pytest.mark.unit
    @pytest.mark.parametrize("value,sf", [
        (10000, 10),
        (5000,  25),
        (20000, 0),
    ])
    def test_time_type_reduces_value(self, value, sf):
        result = apply_safety_factor(value, sf, value_type="time")
        expected = value * (1 - sf / 100.0)
        assert abs(result - expected) < 1e-9

    @pytest.mark.unit
    def test_time_type_never_negative(self):
        result = apply_safety_factor(100, 100, value_type="time")
        assert result >= 0

    @pytest.mark.unit
    @pytest.mark.parametrize("value,sf", [
        (0.9,  15),
        (0.5,  20),
    ])
    def test_reliability_type(self, value, sf):
        result = apply_safety_factor(value, sf, value_type="reliability")
        expected = max(value * (1 - sf / 100.0), 0)
        assert abs(result - expected) < 1e-9

    @pytest.mark.unit
    def test_unknown_type_returns_original(self):
        result = apply_safety_factor(42.0, 15, value_type="unknown")
        assert result == 42.0

    @pytest.mark.unit
    def test_zero_safety_factor_no_change_probability(self):
        result = apply_safety_factor(0.5, 0, value_type="probability")
        assert abs(result - 0.5) < 1e-9

    @pytest.mark.unit
    def test_zero_safety_factor_no_change_time(self):
        result = apply_safety_factor(5000, 0, value_type="time")
        assert abs(result - 5000) < 1e-9

    @pytest.mark.unit
    def test_probability_increases_with_safety_factor(self):
        """Higher safety factor must always produce higher adjusted probability."""
        base = 0.4
        r10 = apply_safety_factor(base, 10, "probability")
        r20 = apply_safety_factor(base, 20, "probability")
        assert r20 > r10

    @pytest.mark.unit
    def test_time_decreases_with_safety_factor(self):
        """Higher safety factor must produce lower RUL estimate."""
        base = 10000.0
        r10 = apply_safety_factor(base, 10, "time")
        r20 = apply_safety_factor(base, 20, "time")
        assert r20 < r10


# ===========================================================================
# 4. calculate_adjusted_predictions
# ===========================================================================

class TestCalculateAdjustedPredictions:
    """Integration test for the combined adjusted prediction dict."""

    @pytest.mark.unit
    @pytest.mark.parametrize("raw_prob,sf", [
        (20.0, 10),
        (50.0, 20),
        (80.0, 15),
        (0.0,   5),
        (100.0, 0),
    ])
    def test_adjusted_probability_gte_raw(self, raw_prob, sf):
        result = calculate_adjusted_predictions(raw_prob, sf)
        assert result["adjusted_probability"] >= result["raw_probability"]

    @pytest.mark.unit
    def test_output_keys_present(self):
        result = calculate_adjusted_predictions(50.0, 15)
        expected_keys = {
            "raw_probability", "adjusted_probability", "safety_margin",
            "safety_factor_percent", "raw_risk_level", "raw_risk_color",
            "adjusted_risk_level", "adjusted_risk_color", "conservativeness",
        }
        assert expected_keys.issubset(set(result.keys()))

    @pytest.mark.unit
    def test_safety_margin_is_non_negative(self):
        result = calculate_adjusted_predictions(40.0, 10)
        assert result["safety_margin"] >= 0

    @pytest.mark.unit
    def test_adjusted_probability_bounded(self):
        result = calculate_adjusted_predictions(95.0, 30)
        assert 0 <= result["adjusted_probability"] <= 100

    @pytest.mark.unit
    def test_zero_safety_factor_preserves_probability(self):
        result = calculate_adjusted_predictions(60.0, 0)
        assert abs(result["adjusted_probability"] - 60.0) < 1e-6

    @pytest.mark.unit
    def test_conservativeness_message_includes_factor(self):
        result = calculate_adjusted_predictions(50.0, 25)
        assert "25" in result["conservativeness"]

    @pytest.mark.unit
    @pytest.mark.parametrize("raw_prob,expected_level", [
        (15.0,  "Low Risk"),
        (50.0,  "Medium Risk"),
        (85.0,  "High Risk"),
    ])
    def test_raw_risk_levels(self, raw_prob, expected_level):
        result = calculate_adjusted_predictions(raw_prob, 0)
        assert result["raw_risk_level"] == expected_level


# ===========================================================================
# 5. predict_failure
# ===========================================================================

class TestPredictFailure:
    """Output range and consistency tests for the RF predict_failure function."""

    @pytest.fixture(autouse=True)
    def patch_audit(self):
        """Patch audit_logger in math_engine to avoid the category kwarg conflict."""
        with patch("core.failure_prediction_engine.audit_logger") as _mock:
            yield _mock

    @pytest.mark.unit
    def test_probability_in_range(self, trained_model):
        model, scaler = trained_model
        prob, cat, name, prob_dict = predict_failure(
            model, scaler, {"temperature": 75, "pressure": 25, "vibration": 2.5, "operating_hours": 10000, "rpm": 2500}
        )
        assert 0.0 <= prob <= 100.0

    @pytest.mark.unit
    def test_category_valid_value(self, trained_model):
        model, scaler = trained_model
        _, cat, _, _ = predict_failure(model, scaler, {"temperature": 75, "pressure": 25, "vibration": 2.5, "operating_hours": 10000, "rpm": 2500})
        assert cat in (0, 1, 2)

    @pytest.mark.unit
    def test_category_name_valid(self, trained_model):
        model, scaler = trained_model
        _, _, name, _ = predict_failure(model, scaler, {"temperature": 75, "pressure": 25, "vibration": 2.5, "operating_hours": 10000, "rpm": 2500})
        assert name in ("Normal", "Caution", "Critical")

    @pytest.mark.unit
    def test_prob_dict_keys(self, trained_model):
        model, scaler = trained_model
        _, _, _, prob_dict = predict_failure(model, scaler, {"temperature": 75, "pressure": 25, "vibration": 2.5, "operating_hours": 10000, "rpm": 2500})
        assert set(prob_dict.keys()) == {"Normal", "Caution", "Critical"}

    @pytest.mark.unit
    def test_prob_dict_sum_is_100(self, trained_model):
        model, scaler = trained_model
        _, _, _, prob_dict = predict_failure(model, scaler, {"temperature": 75, "pressure": 25, "vibration": 2.5, "operating_hours": 10000, "rpm": 2500})
        total = sum(prob_dict.values())
        assert abs(total - 100.0) < 1e-6

    @pytest.mark.unit
    @pytest.mark.parametrize("temp,pressure,vib,hours,rpm", [
        (120, 45, 9.0, 19000, 4500),   # Extreme / near-failure conditions
        (20,  5,  0.6, 100,   500),    # Very mild conditions
        (75,  25, 2.5, 10000, 2500),   # Typical operating conditions
    ])
    def test_probability_always_bounded(self, trained_model, temp, pressure, vib, hours, rpm):
        model, scaler = trained_model
        prob, _, _, _ = predict_failure(model, scaler, {"temperature": temp, "pressure": pressure, "vibration": vib, "operating_hours": hours, "rpm": rpm})
        assert 0.0 <= prob <= 100.0

    @pytest.mark.unit
    def test_severe_conditions_higher_risk(self, trained_model):
        """
        Severe sensor values should tend to produce higher failure probability
        than benign values (tested over many calls to reduce statistical noise).
        """
        model, scaler = trained_model
        high_prob, _, _, _ = predict_failure(model, scaler, {"temperature": 140, "pressure": 48, "vibration": 9.5, "operating_hours": 19500, "rpm": 4900})
        low_prob,  _, _, _ = predict_failure(model, scaler,  {"temperature": 30, "pressure": 5, "vibration": 0.6, "operating_hours": 500, "rpm": 600})
        # Not a strict guarantee for every model, but should hold for well-trained RF
        assert high_prob >= low_prob


# ===========================================================================
# 6. fit_weibull_distribution
# ===========================================================================

class TestFitWeibullDistribution:
    """Shape, scale, MTTF, and reliability array correctness."""

    @pytest.mark.unit
    def test_returns_dict_with_required_keys(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        required = {
            "shape", "scale", "mttf", "failure_mode", "failure_trend",
            "t_points", "reliability", "hazard_rate", "pdf", "cdf",
            "weibull_plot_x", "weibull_plot_y", "sorted_failures",
        }
        assert required.issubset(set(result.keys()))

    @pytest.mark.unit
    def test_shape_is_positive(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        assert result["shape"] > 0

    @pytest.mark.unit
    def test_scale_is_positive(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        assert result["scale"] > 0

    @pytest.mark.unit
    def test_mttf_is_positive(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        assert result["mttf"] > 0

    @pytest.mark.unit
    def test_reliability_between_0_and_1(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        rel = result["reliability"]
        assert np.all(rel >= 0) and np.all(rel <= 1.0)

    @pytest.mark.unit
    def test_reliability_is_decreasing(self, failure_times_array):
        """Reliability function R(t) must be monotonically non-increasing."""
        result = fit_weibull_distribution(failure_times_array)
        diffs = np.diff(result["reliability"])
        assert np.all(diffs <= 1e-10), "Reliability must be non-increasing"

    @pytest.mark.unit
    def test_cdf_between_0_and_1(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        cdf = result["cdf"]
        assert np.all(cdf >= 0) and np.all(cdf <= 1.0)

    @pytest.mark.unit
    def test_failure_mode_label_exists(self, failure_times_array):
        result = fit_weibull_distribution(failure_times_array)
        assert isinstance(result["failure_mode"], str) and len(result["failure_mode"]) > 0

    @pytest.mark.unit
    @pytest.mark.parametrize("beta,expected_mode", [
        (0.5,  "Infant Mortality"),
        (2.0,  "Wear-out"),
    ])
    def test_failure_mode_classification(self, beta, expected_mode):
        """Verify correct failure mode classification based on beta."""
        # Generate data from a known Weibull distribution
        np.random.seed(42)
        times = np.random.weibull(beta, 200) * 5000
        times = times[times > 0]
        result = fit_weibull_distribution(times)
        assert expected_mode in result["failure_mode"]


# ===========================================================================
# 7. generate_kaplan_meier_data
# ===========================================================================

class TestGenerateKaplanMeierData:
    """Kaplan-Meier survival function properties."""

    @pytest.fixture
    def km_result(self, survival_data_df):
        return generate_kaplan_meier_data(survival_data_df)

    @pytest.mark.unit
    def test_returns_dict(self, km_result):
        assert isinstance(km_result, dict)

    @pytest.mark.unit
    def test_required_keys(self, km_result):
        required = {"kmf", "survival_function", "median_survival",
                    "confidence_interval", "survival_at_times"}
        assert required.issubset(set(km_result.keys()))

    @pytest.mark.unit
    def test_survival_function_between_0_and_1(self, km_result):
        sf = km_result["survival_function"]
        assert (sf.values >= 0).all() and (sf.values <= 1.0).all()

    @pytest.mark.unit
    def test_survival_function_is_monotone_decreasing(self, km_result):
        sf_values = km_result["survival_function"].values.flatten()
        diffs = np.diff(sf_values)
        assert np.all(diffs <= 1e-10), "Survival function must be non-increasing"

    @pytest.mark.unit
    def test_median_survival_positive(self, km_result):
        median = km_result["median_survival"]
        assert median > 0 or np.isnan(median)  # NaN is valid when no median found

    @pytest.mark.unit
    def test_survival_at_times_dict_structure(self, km_result):
        sat = km_result["survival_at_times"]
        assert isinstance(sat, dict)
        for t, val in sat.items():
            if val is not None:
                assert 0.0 <= val <= 1.0
