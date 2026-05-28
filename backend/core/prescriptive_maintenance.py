import numpy as np
from scipy.stats import weibull_min

class WeibullAFTModel:
    """Implements an Accelerated Failure Time (AFT) model using the Weibull distribution."""
    @staticmethod
    def calculate_rul(current_hours: float, shape_beta: float, scale_eta: float, stress_factor: float = 1.0) -> dict:
        """
        Calculates Remaining Useful Life (RUL) and probabilities.
        stress_factor > 1.0 reduces the scale parameter (accelerates failure).
        """
        # Adjusted scale parameter due to stress
        adjusted_eta = scale_eta / stress_factor
        
        # Current reliability R(t)
        if current_hours <= 0:
            current_reliability = 1.0
        else:
            current_reliability = np.exp(- (current_hours / adjusted_eta) ** shape_beta)
            
        # Target reliability thresholds
        # t = eta * (-ln(R))^(1/beta)
        t_90 = adjusted_eta * (-np.log(0.90)) ** (1.0 / shape_beta)
        t_50 = adjusted_eta * (-np.log(0.50)) ** (1.0 / shape_beta)
        t_10 = adjusted_eta * (-np.log(0.10)) ** (1.0 / shape_beta)
        
        rul_50 = max(0.0, t_50 - current_hours)
        
        return {
            "current_reliability": current_reliability,
            "rul_median_hours": rul_50,
            "hours_to_90_rel": max(0.0, t_90 - current_hours),
            "hours_to_10_rel": max(0.0, t_10 - current_hours),
            "adjusted_eta": adjusted_eta
        }

class DegradationTrendAnalyzer:
    """Extrapolates sensor degradation trends and computes confidence bounds."""
    @staticmethod
    def extrapolate_trend(history_times: list, history_values: list, future_hours: float) -> dict:
        """
        Simple linear regression for degradation trend with 95% confidence intervals.
        """
        if len(history_times) < 2:
            return {"slope": 0, "intercept": 0, "predictions": [], "upper_95": [], "lower_95": []}
            
        x = np.array(history_times)
        y = np.array(history_values)
        
        # Linear regression
        A = np.vstack([x, np.ones(len(x))]).T
        slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        
        # Standard error estimation for confidence bands
        y_pred = slope * x + intercept
        residuals = y - y_pred
        sse = np.sum(residuals**2)
        std_error = np.sqrt(sse / max(1, len(x) - 2))
        
        # Predict future
        last_t = x[-1]
        future_t = np.linspace(last_t, last_t + future_hours, 50)
        future_pred = slope * future_t + intercept
        
        # 95% CI (~1.96 * std_error, simplified constant width for demonstration)
        margin = 1.96 * std_error
        upper_95 = future_pred + margin
        lower_95 = future_pred - margin
        
        return {
            "times": future_t,
            "predictions": future_pred,
            "upper_95": upper_95,
            "lower_95": lower_95,
            "slope": slope,
            "intercept": intercept
        }

class ActionRecommendationEngine:
    """Rules-based prescriptive engine translating probabilities into actionable steps."""
    @staticmethod
    def generate_action_plan(rul_hours: float, probability_of_failure: float, equipment_type: str, critical_sensor: str = None) -> list:
        """
        Generates concrete recommendations based on the current health state.
        """
        recommendations = []
        
        if probability_of_failure < 0.3:
            recommendations.append("Continue normal operation.")
            recommendations.append("Maintain standard 30-day inspection schedule.")
        elif probability_of_failure < 0.7:
            recommendations.append(f"Increase monitoring frequency of {equipment_type} to every 12 hours.")
            if critical_sensor == "vibration":
                recommendations.append("Schedule bearing alignment and balancing check within 7 days.")
            elif critical_sensor == "temperature":
                recommendations.append("Inspect lubrication levels and cooling system flow within 48 hours.")
            else:
                recommendations.append("Schedule Level 1 diagnostic review.")
        else:
            recommendations.append("CRITICAL: Reduce operational load (pressure/speed) by 15% immediately.")
            if rul_hours < 48:
                recommendations.append(f"Prepare for emergency shutdown within {max(1, int(rul_hours))} hours.")
            else:
                recommendations.append("Schedule emergency maintenance during the next available downtime window.")
            recommendations.append("Dispatch maintenance team with replacement seals and bearings.")
            
        return recommendations
