"""
Causal Diagnosis Engine — Phase 10
Provides SHAP-based feature attribution, fault tree generation,
and natural language explanation for predictive maintenance diagnostics.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Industrial fault mode knowledge base
# Maps combinations of dominant SHAP features to established failure modes
# per API 610 (pumps), API 617 (compressors), API 670 (machinery protection)
# ---------------------------------------------------------------------------

_FAULT_RULES: List[Dict] = [
    # Pump-specific modes
    {
        "required": {"vibration", "temperature"},
        "keywords": {},
        "mode": "Bearing Seizure / Mechanical Imbalance",
        "root_cause": "Loss of lubrication or mechanical misalignment causing abnormal friction and heat generation in bearing assembly.",
        "standards": "API 610 Section 9.1, ISO 10816-3",
        "remediation": [
            "Inspect bearing clearances and lubrication system",
            "Perform vibration spectrum analysis for imbalance harmonics",
            "Check coupling alignment — allowable offset < 0.05 mm/m",
        ],
    },
    {
        "required": {"available_npsh", "vibration"},
        "keywords": {},
        "mode": "Cavitation",
        "root_cause": "Net Positive Suction Head available (NPSHa) below required (NPSHr), causing vapor bubble formation and implosion on impeller blades.",
        "standards": "API 610 Section 7.3, HI 9.6.1",
        "remediation": [
            "Verify NPSHa > NPSHr with minimum 0.6 m safety margin",
            "Reduce suction pipe restrictions",
            "Lower fluid temperature or increase suction vessel pressure",
        ],
    },
    {
        "required": {"inlet_pressure", "vibration"},
        "keywords": {},
        "mode": "Cavitation",
        "root_cause": "Low suction pressure causing vapor bubble implosion on impeller blades.",
        "standards": "API 610 Section 7.3",
        "remediation": [
            "Check suction valve is fully open",
            "Inspect suction strainer for fouling",
            "Verify operating flow is within 70-120% of BEP",
        ],
    },
    # Compressor-specific modes
    {
        "required": {"compression_ratio", "axial_vibration"},
        "keywords": {},
        "mode": "Compressor Surge",
        "root_cause": "Operating point crossed the surge line on the compressor map — flow reversed causing cyclic pressure oscillations and axial thrust loads.",
        "standards": "API 617 Section 2.1.3, API 670",
        "remediation": [
            "Open anti-surge recycle valve immediately",
            "Reduce compression ratio — lower discharge pressure or increase suction",
            "Verify surge controller setpoint",
        ],
    },
    {
        "required": {"radial_vibration", "axial_vibration"},
        "keywords": {},
        "mode": "Rotor Instability / Oil Whirl",
        "root_cause": "Sub-synchronous vibration indicating fluid-induced instability in hydrodynamic journal bearings or rotor-dynamic instability.",
        "standards": "API 670 Section 4.3, ISO 10816-4",
        "remediation": [
            "Check bearing clearances — elliptical bearings preferred for stability",
            "Verify lube oil supply pressure and temperature",
            "Review critical speed margins (min 15% per API 617)",
        ],
    },
    # Turbine-specific modes
    {
        "required": {"steam_temperature", "axial_vibration"},
        "keywords": {},
        "mode": "Thermal Shock / Differential Expansion",
        "root_cause": "Excessive differential thermal expansion between rotor and casing during transient operation, reducing tip clearances below limits.",
        "standards": "API 611 Section 6.1, OEM thermal gradient limits",
        "remediation": [
            "Review startup/shutdown rate — limit to OEM thermal gradient specification",
            "Inspect differential expansion probes — verify calibration",
            "Check steam quality — superheating below dew point causes water induction",
        ],
    },
    {
        "required": {"synchronous_speed", "axial_vibration"},
        "keywords": {},
        "mode": "Rotor Unbalance / Critical Speed Crossing",
        "root_cause": "Operating at or near a rotor critical speed amplifying residual unbalance forces. Possible blade fouling increasing unbalance.",
        "standards": "API 684, API 670",
        "remediation": [
            "Perform online balance correction if system supports it",
            "Verify critical speed margins in operating speed range",
            "Inspect turbine blades for fouling deposits (wash if applicable)",
        ],
    },
    # Generic fallback
    {
        "required": set(),
        "keywords": {},
        "mode": "Multi-Factor Degradation",
        "root_cause": "Multiple interacting wear and stress factors detected. No single dominant failure mode identified — broad inspection recommended.",
        "standards": "ISO 14224, OREDA reliability data",
        "remediation": [
            "Perform comprehensive condition monitoring sweep",
            "Review maintenance history for recurring failure patterns",
            "Assess operating point relative to equipment design envelope",
        ],
    },
]


class ShapAnalyzer:
    """
    Computes SHAP-equivalent feature attributions from the active ML model
    stored in Streamlit session state.

    When the trained model is not accessible (fallback mode), uses normalized
    sensor deviations as a proxy for feature importance.
    """

    # Default alarm setpoints per ISA-18.2 / API 670 limits
    _NOMINAL_RANGES: Dict[str, Tuple[float, float]] = {
        "temperature":          (20.0,  95.0),
        "discharge_temperature": (20.0,  95.0),
        "pressure":             (0.5,  45.0),
        "inlet_pressure":       (0.5,   5.0),
        "outlet_pressure":      (5.0,  50.0),
        "vibration":            (0.0,   4.5),
        "radial_vibration":     (0.0,   4.5),
        "axial_vibration":      (0.0,   3.5),
        "available_npsh":       (1.5,   8.0),
        "volumetric_flow":      (50.0, 300.0),
        "compression_ratio":    (1.5,   7.0),
        "relative_humidity":    (20.0,  80.0),
        "steam_temperature":    (150.0, 320.0),
        "exhaust_temperature":  (50.0, 180.0),
        "synchronous_speed":    (1500.0, 4500.0),
    }

    @staticmethod
    def compute_shap_from_model(
        model,
        scaler,
        features_dict: Dict[str, float],
        feature_columns: List[str],
    ) -> Dict[str, float]:
        """
        Compute approximate SHAP values using the marginal contribution method
        (permutation importance proxy). Works with any sklearn-compatible model.

        Args:
            model: Trained calibrated model with predict_proba
            scaler: Fitted StandardScaler
            features_dict: Current sensor readings
            feature_columns: Ordered list of feature names the model expects

        Returns:
            Dictionary mapping feature names to signed impact values (%).
            Positive values increase failure probability, negative values decrease it.
        """
        try:
            feature_vector = np.array(
                [[features_dict.get(f, 0.0) for f in feature_columns]]
            )
            scaled = scaler.transform(feature_vector)
            baseline_probs = model.predict_proba(scaled)[0]
            n_classes = len(baseline_probs)

            if n_classes >= 3:
                baseline_prob = baseline_probs[1] * 50.0 + baseline_probs[2] * 100.0
            else:
                baseline_prob = baseline_probs[-1] * 100.0

            shap_values: Dict[str, float] = {}

            for i, feat in enumerate(feature_columns):
                perturbed = feature_vector.copy()
                perturbed[0, i] = 0.0  # Set feature to mean (zero in scaled space equivalent)
                perturbed_scaled = scaler.transform(perturbed)
                perturbed_probs = model.predict_proba(perturbed_scaled)[0]

                if n_classes >= 3:
                    perturbed_prob = perturbed_probs[1] * 50.0 + perturbed_probs[2] * 100.0
                else:
                    perturbed_prob = perturbed_probs[-1] * 100.0

                # Impact = how much this feature contributes above mean
                shap_values[feat] = round(baseline_prob - perturbed_prob, 3)

            logger.debug(f"SHAP computed from model: {shap_values}")
            return shap_values

        except Exception as exc:
            logger.warning(f"Model-based SHAP failed, using deviation fallback: {exc}")
            return ShapAnalyzer.compute_shap_from_deviations(features_dict)

    @staticmethod
    def compute_shap_from_deviations(sensor_data: Dict[str, float]) -> Dict[str, float]:
        """
        Fallback: Compute signed normalized deviations when model is unavailable.
        Deviation > 0 means the sensor is above its safe upper limit (risk-increasing).
        Deviation < 0 means the sensor is below its safe lower limit.
        """
        shap_values: Dict[str, float] = {}
        for feat, value in sensor_data.items():
            lo, hi = ShapAnalyzer._NOMINAL_RANGES.get(feat, (None, None))
            if lo is None:
                continue
            span = hi - lo
            if span == 0:
                continue
            if value > hi:
                impact = (value - hi) / span
            elif value < lo:
                impact = (value - lo) / span
            else:
                impact = 0.0
            shap_values[feat] = round(impact, 3)

        return shap_values

    @staticmethod
    def extract_top_factors(
        shap_values: Dict[str, float], threshold: float = 0.05
    ) -> List[Dict]:
        """
        Filter and rank features by absolute impact above threshold.

        Returns:
            List of dicts with keys: feature, impact, direction
        """
        factors = []
        for feature, importance in shap_values.items():
            if abs(importance) >= threshold:
                factors.append({
                    "feature": feature,
                    "impact": importance,
                    "direction": "increasing" if importance > 0 else "decreasing",
                })
        factors.sort(key=lambda x: abs(x["impact"]), reverse=True)
        return factors


class FaultTreeGenerator:
    """
    Maps dominant SHAP features to established O&G industrial failure modes
    using a deterministic rule engine based on API/ISO standards.
    """

    @staticmethod
    def generate_fault_tree(top_factors: List[Dict]) -> Dict:
        """
        Match active features to the most specific fault rule.

        Returns:
            Dict with keys: mode, root_cause, standards, remediation, matched_features
        """
        active_features = {f["feature"] for f in top_factors}

        # Try rules in priority order (most specific first)
        for rule in _FAULT_RULES[:-1]:  # Skip fallback
            required = rule["required"]
            if required and required.issubset(active_features):
                return {
                    "mode": rule["mode"],
                    "root_cause": rule["root_cause"],
                    "standards": rule["standards"],
                    "remediation": rule["remediation"],
                    "matched_features": list(required),
                }

        # Fallback rule
        fallback = _FAULT_RULES[-1]
        return {
            "mode": fallback["mode"],
            "root_cause": fallback["root_cause"],
            "standards": fallback["standards"],
            "remediation": fallback["remediation"],
            "matched_features": list(active_features),
        }


class NaturalLanguageExplainer:
    """
    Generates structured, plain-English diagnostic narratives from SHAP attributions
    and fault tree results for display to field engineers.
    """

    _UNITS: Dict[str, str] = {
        "temperature": "degC",
        "discharge_temperature": "degC",
        "exhaust_temperature": "degC",
        "steam_temperature": "degC",
        "pressure": "bar",
        "inlet_pressure": "bar",
        "outlet_pressure": "bar",
        "vibration": "mm/s",
        "radial_vibration": "mm/s",
        "axial_vibration": "mm/s",
        "available_npsh": "m",
        "volumetric_flow": "m3/h",
        "compression_ratio": "dimensionless",
        "relative_humidity": "%",
        "synchronous_speed": "RPM",
    }

    @staticmethod
    def explain(
        fault_mode: str,
        sensor_data: Dict[str, float],
        top_factors: List[Dict],
    ) -> str:
        """
        Build a concise diagnostic summary suitable for a field engineer.
        """
        if not top_factors:
            return (
                "All monitored parameters are within nominal operating ranges. "
                "No dominant failure drivers detected."
            )

        lines = [f"Primary failure mode identified: {fault_mode}."]
        lines.append("Contributing sensor deviations (sorted by impact):")

        for factor in top_factors:
            feat = factor["feature"]
            val = sensor_data.get(feat)
            unit = NaturalLanguageExplainer._UNITS.get(feat, "")
            direction = "elevated" if factor["impact"] > 0 else "depressed"
            val_str = f"{val:.2f} {unit}".strip() if val is not None else "N/A"
            display_feat = feat.replace("_", " ").title()
            contribution = abs(factor["impact"])
            lines.append(
                f"  - {display_feat}: {direction} at {val_str} "
                f"(attribution: {contribution:.1f}% probability impact)"
            )

        return "\n".join(lines)
