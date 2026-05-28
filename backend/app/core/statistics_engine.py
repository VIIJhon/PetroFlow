"""
Statistics Engine - Reliability Analysis Module
Implements Weibull, Kaplan-Meier, and Jackknife for predictive maintenance
Migrated and optimized for FastAPI backend

Mathematical foundations:
- Weibull: Describes failure rate patterns across equipment lifecycle
- Kaplan-Meier: Non-parametric survival curve from censored maintenance data
- Jackknife: Bias reduction and confidence interval estimation via leave-one-out

Author: Jhon Villegas
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
import pandas as pd
import logging
from scipy import stats
from scipy.special import gamma as gamma_func
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

try:
    from lifelines import KaplanMeierFitter
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    logger_init = logging.getLogger(__name__)
    logger_init.warning("lifelines not available: Kaplan-Meier features disabled")

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WeibullResult:
    """Weibull distribution analysis result."""
    shape: float
    scale: float
    mttf: float
    failure_mode: str
    failure_trend: str
    t_points: np.ndarray
    reliability: np.ndarray
    hazard_rate: np.ndarray
    pdf: np.ndarray
    cdf: np.ndarray
    weibull_plot_x: np.ndarray
    weibull_plot_y: np.ndarray
    sorted_failures: np.ndarray


@dataclass
class KaplanMeierResult:
    """Kaplan-Meier survival analysis result."""
    survival_function: pd.DataFrame
    median_survival: float
    confidence_interval: pd.DataFrame
    survival_at_times: Dict[float, Optional[float]]
    kmf_object: Any


@dataclass
class JackknifeResult:
    """Jackknife resampling result."""
    prediction: float
    variance: float
    std_error: float
    ci_lower: float
    ci_upper: float
    all_predictions: np.ndarray


# ============================================================================
# WEIBULL DISTRIBUTION ANALYSIS
# ============================================================================

def fit_weibull_distribution(
    failure_times: np.ndarray,
    confidence_level: float = 0.95
) -> WeibullResult:
    """
    Perform Weibull distribution analysis for reliability prediction.
    
    The Weibull distribution captures three failure patterns:
    - beta < 1: Infant mortality (early failures, decreasing hazard rate)
    - beta = 1: Random failures (constant hazard rate, exponential distribution)
    - beta > 1: Wear-out (aging failures, increasing hazard rate)
    
    Mathematical formulas:
    - PDF: f(t) = (beta/eta)(t/eta)^(beta-1) * exp(-(t/eta)^beta)
    - Reliability: R(t) = exp(-(t/eta)^beta)
    - Hazard rate: h(t) = (beta/eta)(t/eta)^(beta-1)
    - MTTF: eta * Gamma(1 + 1/beta)
    
    Args:
        failure_times: Array of observed failure times (positive values only)
        confidence_level: Confidence level for statistics (default 0.95)
    
    Returns:
        WeibullResult containing shape, scale, MTTF, curves, and failure mode
    
    Raises:
        ValueError: If failure_times is empty or contains invalid values
    """
    if failure_times is None or len(failure_times) == 0:
        raise ValueError("failure_times cannot be empty")
    
    failure_times = np.asarray(failure_times, dtype=float)
    failure_times = failure_times[failure_times > 0]
    
    if len(failure_times) < 2:
        raise ValueError("At least 2 positive failure times required")
    
    try:
        shape, loc, scale = stats.weibull_min.fit(failure_times, floc=0)
    except Exception as e:
        logger.error(f"Weibull fitting failed: {e}")
        raise ValueError(f"Unable to fit Weibull distribution: {e}")
    
    beta = shape
    eta = scale
    
    # Calculate Mean Time To Failure
    mttf = eta * gamma_func(1 + 1/beta)
    
    # Classify failure mode
    if beta < 1:
        failure_mode = "Infant Mortality"
        failure_trend = "Decreasing failure rate - early failures dominant"
    elif beta > 1.5:
        failure_mode = "Wear-out"
        failure_trend = "Increasing failure rate - aging/degradation"
    elif beta > 1:
        failure_mode = "Early Wear-out"
        failure_trend = "Increasing failure rate - moderate aging"
    else:
        failure_mode = "Random Failures"
        failure_trend = "Constant failure rate - random events"
    
    # Generate evaluation points
    t_max = failure_times.max()
    t_points = np.linspace(0.1, t_max * 1.2, 200)
    
    # Calculate curves
    reliability = np.exp(-(t_points / eta) ** beta)
    hazard_rate = (beta / eta) * ((t_points / eta) ** (beta - 1))
    pdf = stats.weibull_min.pdf(t_points, beta, loc=0, scale=eta)
    cdf = stats.weibull_min.cdf(t_points, beta, loc=0, scale=eta)
    
    # Weibull plot coordinates (for linearization)
    sorted_failures = np.sort(failure_times)
    n = len(sorted_failures)
    plotting_positions = (np.arange(1, n + 1) - 0.3) / (n + 0.4)
    
    weibull_y = np.log(-np.log(1 - np.clip(plotting_positions, 0.001, 0.999)))
    weibull_x = np.log(sorted_failures)
    
    logger.info(
        f"Weibull fit: beta={beta:.3f}, eta={eta:.1f}, "
        f"MTTF={mttf:.1f}, mode={failure_mode}"
    )
    
    return WeibullResult(
        shape=beta,
        scale=eta,
        mttf=mttf,
        failure_mode=failure_mode,
        failure_trend=failure_trend,
        t_points=t_points,
        reliability=reliability,
        hazard_rate=hazard_rate,
        pdf=pdf,
        cdf=cdf,
        weibull_plot_x=weibull_x,
        weibull_plot_y=weibull_y,
        sorted_failures=sorted_failures
    )


# ============================================================================
# KAPLAN-MEIER SURVIVAL ANALYSIS
# ============================================================================

def generate_kaplan_meier_data(
    survival_data: pd.DataFrame,
    time_column: str = 'time_to_failure',
    event_column: str = 'event_observed'
) -> KaplanMeierResult:
    """
    Perform Kaplan-Meier non-parametric survival analysis.
    
    The Kaplan-Meier estimator computes the probability of survival at each time point,
    accounting for censored observations (equipment still operating at data collection).
    
    Mathematical formula:
    S(t) = product((1 - d_i/n_i)) for all t_i <= t
    Where:
    - d_i = number of failures at time t_i
    - n_i = number at risk (not yet failed) at time t_i
    
    This is crucial for maintenance planning as it shows:
    - Probability of equipment surviving to time t
    - Median survival time (50% failure point)
    - Confidence intervals accounting for data uncertainty
    
    Args:
        survival_data: DataFrame with time-to-failure and event indicators
        time_column: Column name for time-to-failure values
        event_column: Column name for event observed flags (1=failure, 0=censored)
    
    Returns:
        KaplanMeierResult with survival curves and statistics
    
    Raises:
        ValueError: If required columns missing or data invalid
        ImportError: If lifelines package not installed
    """
    if not LIFELINES_AVAILABLE:
        raise ImportError(
            "lifelines package required for Kaplan-Meier analysis. "
            "Install with: pip install lifelines"
        )
    
    if survival_data is None or survival_data.empty:
        raise ValueError("survival_data cannot be empty")
    
    if time_column not in survival_data.columns:
        raise ValueError(f"Column '{time_column}' not found in survival_data")
    if event_column not in survival_data.columns:
        raise ValueError(f"Column '{event_column}' not found in survival_data")
    
    try:
        kmf = KaplanMeierFitter()
        kmf.fit(
            durations=survival_data[time_column],
            event_observed=survival_data[event_column],
            label='Equipment Survival Curve'
        )
    except Exception as e:
        logger.error(f"Kaplan-Meier fitting failed: {e}")
        raise ValueError(f"Unable to fit Kaplan-Meier model: {e}")
    
    # Extract results
    survival_function = kmf.survival_function_
    median_survival = kmf.median_survival_time_
    confidence_interval = kmf.confidence_interval_survival_function_
    
    # Calculate survival probabilities at key milestones
    time_points = [5000, 10000, 15000, 20000, 30000]
    survival_at_times = {}
    
    max_time = survival_function.index.max() if len(survival_function) > 0 else 0
    
    for t in time_points:
        if t <= max_time:
            time_index = survival_function.index.to_numpy()
            idx = int(np.abs(time_index - t).argmin())
            survival_at_times[t] = float(survival_function.iloc[idx].values[0])
        else:
            survival_at_times[t] = None
    
    logger.info(
        f"Kaplan-Meier fit: median_survival={median_survival:.1f}, "
        f"sample_size={len(survival_data)}, events={survival_data[event_column].sum()}"
    )
    
    return KaplanMeierResult(
        survival_function=survival_function,
        median_survival=median_survival,
        confidence_interval=confidence_interval,
        survival_at_times=survival_at_times,
        kmf_object=kmf
    )


# ============================================================================
# JACKKNIFE RESAMPLING FOR UNCERTAINTY ESTIMATION
# ============================================================================

def jackknife_resampling(
    model: RandomForestClassifier,
    scaler: StandardScaler,
    X_train: np.ndarray,
    y_train: np.ndarray,
    test_features: np.ndarray,
    sample_size: Optional[int] = None
) -> JackknifeResult:
    """
    Perform Jackknife resampling (leave-one-out cross-validation) for uncertainty estimation.
    
    Jackknife is a non-parametric statistical technique that estimates bias and
    confidence intervals by systematically leaving out one observation at a time.
    For large datasets, a random subset can be used for computational efficiency.
    
    Mathematical foundation:
    - theta_hat_(-i) = estimate without observation i
    - Var_jack = (n-1)/n * sum((theta_hat_(-i) - theta_hat_mean)^2)
    - 95% CI = theta_hat +/- 1.96 * sqrt(Var_jack)
    
    Computational strategy:
    - For n < 100: Use full leave-one-out
    - For n >= 100: Use stratified random sampling to reduce computation
    
    Args:
        model: Trained RandomForestClassifier
        scaler: Fitted StandardScaler for feature normalization
        X_train: Training features (n_samples, n_features)
        y_train: Training labels (n_samples,)
        test_features: Features to predict (1D or 2D array)
        sample_size: Maximum number of leave-one-out iterations
                    (None = use all; min(100, n) recommended for large n)
    
    Returns:
        JackknifeResult with prediction, variance, and confidence intervals
    
    Raises:
        ValueError: If input data invalid
        RuntimeError: If jackknife fitting fails
    """
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=int)
    test_features = np.asarray(test_features, dtype=float)
    
    if X_train.ndim != 2 or len(X_train) != len(y_train):
        raise ValueError("X_train and y_train must have matching first dimension")
    
    if test_features.ndim == 1:
        test_features = test_features.reshape(1, -1)
    
    n = len(X_train)
    
    # Determine actual sample size for jackknife
    if sample_size is None:
        # Use full LOO for small datasets, random sampling for large
        actual_sample_size = min(n, 100)
    else:
        actual_sample_size = min(sample_size, n)
    
    # Select indices to remove
    if actual_sample_size < n:
        indices_to_remove = np.random.choice(n, actual_sample_size, replace=False)
        logger.info(
            f"Using stratified Jackknife: {actual_sample_size} of {n} samples "
            "(computational efficiency)"
        )
    else:
        indices_to_remove = np.arange(n)
        logger.info(f"Using full Jackknife: {n} samples (exact but slower)")
    
    predictions = []
    
    try:
        for idx in indices_to_remove:
            # Leave-one-out: remove sample at idx
            mask = np.ones(n, dtype=bool)
            mask[idx] = False
            
            X_loo = X_train[mask]
            y_loo = y_train[mask]
            
            # Scale training subset
            scaler_loo = StandardScaler()
            X_loo_scaled = scaler_loo.fit_transform(X_loo)
            
            # Train LOO model
            model_loo = RandomForestClassifier(
                n_estimators=50,
                max_depth=8,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42 + idx,
                n_jobs=1,
                verbose=0
            )
            model_loo.fit(X_loo_scaled, y_loo)
            
            # Predict on test features
            test_scaled = scaler_loo.transform(test_features)
            probs = model_loo.predict_proba(test_scaled)[0]
            
            # Convert probabilities to failure score (0-100)
            if len(probs) == 3:
                failure_prob = probs[1] * 50 + probs[2] * 100
            else:
                failure_prob = probs[-1] * 100 if len(probs) > 1 else 50.0
            
            predictions.append(failure_prob)
    
    except Exception as e:
        logger.error(f"Jackknife fitting failed: {e}")
        raise RuntimeError(f"Jackknife resampling failed: {e}")
    
    predictions = np.array(predictions)
    
    # Calculate statistics
    theta_mean = np.mean(predictions)
    deviations = predictions - theta_mean
    jackknife_variance = ((n - 1) / n) * np.sum(deviations ** 2)
    jackknife_std = np.sqrt(jackknife_variance)
    
    # Confidence intervals (95%)
    z_score = 1.96
    ci_lower = max(0, theta_mean - z_score * jackknife_std)
    ci_upper = min(100, theta_mean + z_score * jackknife_std)
    
    logger.info(
        f"Jackknife result: prediction={theta_mean:.2f}%, "
        f"CI=[{ci_lower:.2f}%, {ci_upper:.2f}%], std={jackknife_std:.2f}%"
    )
    
    return JackknifeResult(
        prediction=theta_mean,
        variance=jackknife_variance,
        std_error=jackknife_std,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        all_predictions=predictions
    )


# ============================================================================
# MTBF CALCULATION
# ============================================================================

def calculate_mtbf(
    maintenance_data: pd.DataFrame,
    time_column: str = 'operating_hours',
    failure_column: str = 'failure_count'
) -> Dict[str, float]:
    """
    Calculate Mean Time Between Failures (MTBF) from maintenance records.
    
    MTBF = Total operating time / Number of failures
    
    Args:
        maintenance_data: DataFrame with operating hours and failure counts
        time_column: Column name for operating hours
        failure_column: Column name for failure counts
    
    Returns:
        Dictionary with MTBF, failure_rate, and related metrics
    """
    if maintenance_data.empty:
        logger.warning("Empty maintenance data")
        return {
            'mtbf': None,
            'failure_rate': None,
            'total_hours': 0,
            'total_failures': 0
        }
    
    total_hours = maintenance_data[time_column].sum()
    total_failures = maintenance_data[failure_column].sum()
    
    if total_failures == 0:
        mtbf = float('inf')
        failure_rate = 0.0
    else:
        mtbf = total_hours / total_failures
        failure_rate = total_failures / total_hours if total_hours > 0 else 0.0
    
    return {
        'mtbf': mtbf,
        'failure_rate': failure_rate,
        'total_hours': total_hours,
        'total_failures': total_failures
    }


# ============================================================================
# RELIABILITY AT TIME T
# ============================================================================

def calculate_reliability_at_time(
    shape: float,
    scale: float,
    time: float
) -> float:
    """
    Calculate Weibull reliability at specific time using fitted parameters.
    
    R(t) = exp(-(t/eta)^beta)
    
    Args:
        shape: Weibull shape parameter (beta)
        scale: Weibull scale parameter (eta)
        time: Time point for evaluation
    
    Returns:
        Reliability probability (0-1)
    """
    if time <= 0 or scale <= 0:
        return 1.0
    
    reliability = np.exp(-(time / scale) ** shape)
    return float(np.clip(reliability, 0, 1))


def to_dict(result: Any) -> Dict[str, Any]:
    """
    Convert dataclass result to dictionary for JSON serialization.
    """
    if isinstance(result, WeibullResult):
        return {
            'shape': float(result.shape),
            'scale': float(result.scale),
            'mttf': float(result.mttf),
            'failure_mode': result.failure_mode,
            'failure_trend': result.failure_trend,
            't_points': result.t_points.tolist(),
            'reliability': result.reliability.tolist(),
            'hazard_rate': result.hazard_rate.tolist(),
            'pdf': result.pdf.tolist(),
            'cdf': result.cdf.tolist(),
            'weibull_plot_x': result.weibull_plot_x.tolist(),
            'weibull_plot_y': result.weibull_plot_y.tolist(),
            'sorted_failures': result.sorted_failures.tolist(),
        }
    elif isinstance(result, KaplanMeierResult):
        return {
            'median_survival': float(result.median_survival) if result.median_survival else None,
            'survival_at_times': result.survival_at_times,
            'survival_function': result.survival_function.to_dict() if hasattr(result.survival_function, 'to_dict') else None,
        }
    elif isinstance(result, JackknifeResult):
        return {
            'prediction': float(result.prediction),
            'variance': float(result.variance),
            'std_error': float(result.std_error),
            'ci_lower': float(result.ci_lower),
            'ci_upper': float(result.ci_upper),
            'all_predictions': result.all_predictions.tolist(),
        }
    
    return {}
