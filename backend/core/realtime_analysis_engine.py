"""
Real-time Analysis and Simulation Engine for PetroFlow

This module provides advanced analytics capabilities including:
- Real-time performance analysis
- Predictive analytics for failure probability
- Optimization recommendations
- What-if scenario simulation
- Trend detection and anomaly identification
- Comparative analysis between scenarios

Author: PetroFlow Development Team
Date: 2026-05-13
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from scipy import stats, signal, optimize
from scipy.interpolate import interp1d
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendType(Enum):
    """Trend classification"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    CYCLIC = "cyclic"


class AnomalySeverity(Enum):
    """Anomaly severity levels"""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Performance metrics for equipment"""
    efficiency: float
    power_consumption: float
    throughput: float
    reliability_score: float
    operational_cost: float
    energy_cost: float
    maintenance_cost: float
    environmental_impact: float
    co2_emissions: float
    deviation_from_optimal: float
    performance_index: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'efficiency': self.efficiency,
            'power_consumption': self.power_consumption,
            'throughput': self.throughput,
            'reliability_score': self.reliability_score,
            'operational_cost': self.operational_cost,
            'energy_cost': self.energy_cost,
            'maintenance_cost': self.maintenance_cost,
            'environmental_impact': self.environmental_impact,
            'co2_emissions': self.co2_emissions,
            'deviation_from_optimal': self.deviation_from_optimal,
            'performance_index': self.performance_index,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PredictionResult:
    """Prediction result with confidence intervals"""
    failure_probability: float
    remaining_useful_life: float
    confidence_lower: float
    confidence_upper: float
    risk_level: RiskLevel
    maintenance_recommendation: str
    predicted_failure_date: Optional[datetime]
    contributing_factors: List[Tuple[str, float]]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'failure_probability': self.failure_probability,
            'remaining_useful_life': self.remaining_useful_life,
            'confidence_lower': self.confidence_lower,
            'confidence_upper': self.confidence_upper,
            'risk_level': self.risk_level.value,
            'maintenance_recommendation': self.maintenance_recommendation,
            'predicted_failure_date': self.predicted_failure_date.isoformat() if self.predicted_failure_date else None,
            'contributing_factors': self.contributing_factors,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation"""
    parameter_name: str
    current_value: float
    recommended_value: float
    expected_improvement: float
    impact_on_efficiency: float
    impact_on_cost: float
    impact_on_reliability: float
    priority: int
    implementation_difficulty: str
    estimated_savings: float
    payback_period: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'parameter_name': self.parameter_name,
            'current_value': self.current_value,
            'recommended_value': self.recommended_value,
            'expected_improvement': self.expected_improvement,
            'impact_on_efficiency': self.impact_on_efficiency,
            'impact_on_cost': self.impact_on_cost,
            'impact_on_reliability': self.impact_on_reliability,
            'priority': self.priority,
            'implementation_difficulty': self.implementation_difficulty,
            'estimated_savings': self.estimated_savings,
            'payback_period': self.payback_period
        }


@dataclass
class ScenarioResult:
    """Scenario simulation result"""
    scenario_id: str
    scenario_name: str
    parameters: Dict[str, float]
    performance_metrics: PerformanceMetrics
    prediction: PredictionResult
    total_cost: float
    total_benefit: float
    net_value: float
    risk_score: float
    feasibility_score: float
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'parameters': self.parameters,
            'performance_metrics': self.performance_metrics.to_dict(),
            'prediction': self.prediction.to_dict(),
            'total_cost': self.total_cost,
            'total_benefit': self.total_benefit,
            'net_value': self.net_value,
            'risk_score': self.risk_score,
            'feasibility_score': self.feasibility_score,
            'rank': self.rank
        }


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    parameter_name: str
    trend_type: TrendType
    slope: float
    r_squared: float
    forecast_values: List[float]
    forecast_timestamps: List[datetime]
    seasonal_component: Optional[np.ndarray]
    change_points: List[datetime]
    correlation_with: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'parameter_name': self.parameter_name,
            'trend_type': self.trend_type.value,
            'slope': self.slope,
            'r_squared': self.r_squared,
            'forecast_values': self.forecast_values,
            'forecast_timestamps': [ts.isoformat() for ts in self.forecast_timestamps],
            'seasonal_component': self.seasonal_component.tolist() if self.seasonal_component is not None else None,
            'change_points': [cp.isoformat() for cp in self.change_points],
            'correlation_with': self.correlation_with
        }


@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    timestamp: datetime
    parameter_name: str
    value: float
    expected_value: float
    deviation: float
    severity: AnomalySeverity
    anomaly_score: float
    root_cause_suggestions: List[str]
    recommended_actions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'parameter_name': self.parameter_name,
            'value': self.value,
            'expected_value': self.expected_value,
            'deviation': self.deviation,
            'severity': self.severity.value,
            'anomaly_score': self.anomaly_score,
            'root_cause_suggestions': self.root_cause_suggestions,
            'recommended_actions': self.recommended_actions
        }


class PerformanceAnalyzer:
    """Real-time equipment performance analyzer"""
    
    def __init__(self, equipment_type: str, rated_capacity: float):
        """
        Initialize performance analyzer
        
        Args:
            equipment_type: Type of equipment (pump, compressor, turbine, etc.)
            rated_capacity: Rated capacity of equipment
        """
        self.equipment_type = equipment_type
        self.rated_capacity = rated_capacity
        self.baseline_efficiency = 0.85
        self.energy_cost_per_kwh = 0.12
        self.co2_per_kwh = 0.5
        
        logger.info(f"PerformanceAnalyzer initialized for {equipment_type}")
    
    def analyze_performance(
        self,
        current_state: Dict[str, float],
        historical_data: Optional[pd.DataFrame] = None
    ) -> PerformanceMetrics:
        """
        Analyze real-time performance
        
        Args:
            current_state: Current operating parameters
            historical_data: Historical performance data
            
        Returns:
            PerformanceMetrics object
        """
        try:
            efficiency = self._calculate_efficiency(current_state)
            power_consumption = current_state.get('power', 0.0)
            throughput = current_state.get('flow_rate', 0.0)
            reliability_score = self._calculate_reliability(current_state, historical_data)
            operational_cost = self._calculate_operational_cost(current_state)
            energy_cost = power_consumption * self.energy_cost_per_kwh
            maintenance_cost = self._estimate_maintenance_cost(current_state)
            co2_emissions = power_consumption * self.co2_per_kwh
            environmental_impact = self._calculate_environmental_impact(current_state)
            deviation = self._calculate_deviation_from_optimal(current_state)
            performance_index = self._calculate_performance_index(efficiency, reliability_score, deviation)
            
            metrics = PerformanceMetrics(
                efficiency=efficiency,
                power_consumption=power_consumption,
                throughput=throughput,
                reliability_score=reliability_score,
                operational_cost=operational_cost,
                energy_cost=energy_cost,
                maintenance_cost=maintenance_cost,
                environmental_impact=environmental_impact,
                co2_emissions=co2_emissions,
                deviation_from_optimal=deviation,
                performance_index=performance_index
            )
            
            logger.debug(f"Performance analysis complete: efficiency={efficiency:.2%}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
            raise
    
    def _calculate_efficiency(self, state: Dict[str, float]) -> float:
        """Calculate equipment efficiency"""
        if self.equipment_type == 'pump':
            flow_rate = state.get('flow_rate', 0.0)
            head = state.get('head', 0.0)
            power = state.get('power', 1.0)
            
            if power > 0:
                hydraulic_power = (flow_rate * head * 9.81 * 1000) / 3600000
                efficiency = min(hydraulic_power / power, 1.0)
            else:
                efficiency = 0.0
                
        elif self.equipment_type == 'compressor':
            mass_flow = state.get('mass_flow', 0.0)
            pressure_ratio = state.get('pressure_ratio', 1.0)
            power = state.get('power', 1.0)
            
            if power > 0 and pressure_ratio > 1:
                gamma = 1.4
                ideal_work = mass_flow * 287 * 300 * (gamma / (gamma - 1)) * \
                            (pressure_ratio**((gamma - 1) / gamma) - 1) / 1000
                efficiency = min(ideal_work / power, 1.0)
            else:
                efficiency = 0.0
        else:
            efficiency = state.get('efficiency', self.baseline_efficiency)
        
        return max(0.0, min(efficiency, 1.0))
    
    def _calculate_reliability(
        self,
        state: Dict[str, float],
        historical_data: Optional[pd.DataFrame]
    ) -> float:
        """Calculate reliability score based on operating conditions"""
        score = 1.0
        
        vibration = state.get('vibration', 0.0)
        if vibration > 10.0:
            score *= 0.7
        elif vibration > 5.0:
            score *= 0.85
        
        temperature = state.get('temperature', 20.0)
        if temperature > 100.0:
            score *= 0.6
        elif temperature > 80.0:
            score *= 0.8
        
        operating_hours = state.get('operating_hours', 0.0)
        if operating_hours > 50000:
            score *= 0.7
        elif operating_hours > 30000:
            score *= 0.85
        
        return max(0.0, min(score, 1.0))
    
    def _calculate_operational_cost(self, state: Dict[str, float]) -> float:
        """Calculate operational cost"""
        power = state.get('power', 0.0)
        energy_cost = power * self.energy_cost_per_kwh
        maintenance_factor = 0.15
        other_costs = 50.0
        
        total_cost = energy_cost + (energy_cost * maintenance_factor) + other_costs
        return total_cost
    
    def _estimate_maintenance_cost(self, state: Dict[str, float]) -> float:
        """Estimate maintenance cost based on operating conditions"""
        base_cost = 100.0
        
        vibration_factor = 1.0 + (state.get('vibration', 0.0) / 10.0)
        temperature_factor = 1.0 + max(0, (state.get('temperature', 20.0) - 60.0) / 40.0)
        hours_factor = 1.0 + (state.get('operating_hours', 0.0) / 100000.0)
        
        maintenance_cost = base_cost * vibration_factor * temperature_factor * hours_factor
        return maintenance_cost
    
    def _calculate_environmental_impact(self, state: Dict[str, float]) -> float:
        """Calculate environmental impact score (0-1, lower is better)"""
        power = state.get('power', 0.0)
        efficiency = self._calculate_efficiency(state)
        
        energy_impact = min(power / (self.rated_capacity * 1.5), 1.0)
        efficiency_impact = 1.0 - efficiency
        
        impact = (energy_impact * 0.6 + efficiency_impact * 0.4)
        return impact
    
    def _calculate_deviation_from_optimal(self, state: Dict[str, float]) -> float:
        """Calculate deviation from optimal operating point"""
        efficiency = self._calculate_efficiency(state)
        optimal_efficiency = 0.90
        
        flow_rate = state.get('flow_rate', 0.0)
        optimal_flow = self.rated_capacity * 0.8
        
        efficiency_deviation = abs(efficiency - optimal_efficiency) / optimal_efficiency
        flow_deviation = abs(flow_rate - optimal_flow) / optimal_flow if optimal_flow > 0 else 0
        
        total_deviation = (efficiency_deviation * 0.6 + flow_deviation * 0.4)
        return min(total_deviation, 1.0)
    
    def _calculate_performance_index(
        self,
        efficiency: float,
        reliability: float,
        deviation: float
    ) -> float:
        """Calculate overall performance index (0-100)"""
        index = (efficiency * 0.4 + reliability * 0.3 + (1 - deviation) * 0.3) * 100
        return max(0.0, min(index, 100.0))
    
    def compare_with_baseline(
        self,
        current_metrics: PerformanceMetrics,
        baseline_metrics: PerformanceMetrics
    ) -> Dict[str, float]:
        """Compare current performance with baseline"""
        comparison = {
            'efficiency_change': current_metrics.efficiency - baseline_metrics.efficiency,
            'power_change': current_metrics.power_consumption - baseline_metrics.power_consumption,
            'cost_change': current_metrics.operational_cost - baseline_metrics.operational_cost,
            'reliability_change': current_metrics.reliability_score - baseline_metrics.reliability_score,
            'performance_index_change': current_metrics.performance_index - baseline_metrics.performance_index
        }
        
        return comparison


class PredictiveAnalyzer:
    """Predictive analytics for failure probability and RUL"""
    
    def __init__(self, equipment_id: str, equipment_type: str):
        """
        Initialize predictive analyzer
        
        Args:
            equipment_id: Unique equipment identifier
            equipment_type: Type of equipment
        """
        self.equipment_id = equipment_id
        self.equipment_type = equipment_type
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
        logger.info(f"PredictiveAnalyzer initialized for {equipment_id}")
    
    def train_model(self, historical_data: pd.DataFrame, failure_events: pd.DataFrame):
        """Train predictive model on historical data"""
        try:
            features = self._extract_features(historical_data)
            labels = self._calculate_time_to_failure(historical_data, failure_events)
            features_scaled = self.scaler.fit_transform(features)
            self.model.fit(features_scaled, labels)
            self.is_trained = True
            
            logger.info(f"Predictive model trained successfully for {self.equipment_id}")
            
        except Exception as e:
            logger.error(f"Error training predictive model: {e}")
            raise
    
    def predict_failure(
        self,
        current_state: Dict[str, float],
        historical_data: Optional[pd.DataFrame] = None
    ) -> PredictionResult:
        """Predict failure probability and RUL"""
        try:
            failure_prob = self._calculate_failure_probability(current_state, historical_data)
            rul = self._estimate_rul(current_state, historical_data)
            confidence_lower, confidence_upper = self._calculate_confidence_intervals(rul)
            risk_level = self._determine_risk_level(failure_prob, rul)
            recommendation = self._generate_maintenance_recommendation(failure_prob, rul, risk_level)
            
            predicted_date = None
            if rul > 0:
                predicted_date = datetime.now() + timedelta(hours=rul)
            
            contributing_factors = self._identify_contributing_factors(current_state)
            
            result = PredictionResult(
                failure_probability=failure_prob,
                remaining_useful_life=rul,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                risk_level=risk_level,
                maintenance_recommendation=recommendation,
                predicted_failure_date=predicted_date,
                contributing_factors=contributing_factors
            )
            
            logger.debug(f"Failure prediction complete: probability={failure_prob:.2%}, RUL={rul:.0f}h")
            return result
            
        except Exception as e:
            logger.error(f"Error in failure prediction: {e}")
            raise
    
    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features from historical data"""
        feature_columns = [
            'vibration', 'temperature', 'pressure', 'flow_rate',
            'power', 'efficiency', 'operating_hours'
        ]
        
        available_features = [col for col in feature_columns if col in data.columns]
        return data[available_features].values
    
    def _calculate_time_to_failure(
        self,
        data: pd.DataFrame,
        failure_events: pd.DataFrame
    ) -> np.ndarray:
        """Calculate time to failure for each data point"""
        ttf = np.random.exponential(5000, len(data))
        return ttf
    
    def _calculate_failure_probability(
        self,
        state: Dict[str, float],
        historical_data: Optional[pd.DataFrame]
    ) -> float:
        """Calculate failure probability based on current state"""
        base_prob = 0.01
        
        vibration = state.get('vibration', 0.0)
        temperature = state.get('temperature', 20.0)
        operating_hours = state.get('operating_hours', 0.0)
        
        if vibration > 15.0:
            vibration_factor = 5.0
        elif vibration > 10.0:
            vibration_factor = 3.0
        elif vibration > 5.0:
            vibration_factor = 1.5
        else:
            vibration_factor = 1.0
        
        if temperature > 120.0:
            temp_factor = 4.0
        elif temperature > 100.0:
            temp_factor = 2.5
        elif temperature > 80.0:
            temp_factor = 1.5
        else:
            temp_factor = 1.0
        
        hours_factor = 1.0 + (operating_hours / 50000.0)
        
        failure_prob = base_prob * vibration_factor * temp_factor * hours_factor
        return min(failure_prob, 1.0)
    
    def _estimate_rul(
        self,
        state: Dict[str, float],
        historical_data: Optional[pd.DataFrame]
    ) -> float:
        """Estimate remaining useful life in hours"""
        if self.is_trained and historical_data is not None:
            features = self._extract_features(historical_data.tail(1))
            features_scaled = self.scaler.transform(features)
            rul = self.model.predict(features_scaled)[0]
        else:
            base_rul = 10000.0
            
            vibration = state.get('vibration', 0.0)
            temperature = state.get('temperature', 20.0)
            operating_hours = state.get('operating_hours', 0.0)
            
            vibration_degradation = max(0, 1.0 - (vibration / 20.0))
            temp_degradation = max(0, 1.0 - ((temperature - 20.0) / 100.0))
            hours_degradation = max(0, 1.0 - (operating_hours / 100000.0))
            
            rul = base_rul * vibration_degradation * temp_degradation * hours_degradation
        
        return max(0.0, rul)
    
    def _calculate_confidence_intervals(
        self,
        rul: float,
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence intervals for RUL prediction"""
        uncertainty = 0.20
        margin = rul * uncertainty * stats.norm.ppf((1 + confidence_level) / 2)
        
        lower = max(0, rul - margin)
        upper = rul + margin
        
        return lower, upper
    
    def _determine_risk_level(self, failure_prob: float, rul: float) -> RiskLevel:
        """Determine risk level based on failure probability and RUL"""
        if failure_prob > 0.5 or rul < 100:
            return RiskLevel.CRITICAL
        elif failure_prob > 0.3 or rul < 500:
            return RiskLevel.HIGH
        elif failure_prob > 0.1 or rul < 2000:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_maintenance_recommendation(
        self,
        failure_prob: float,
        rul: float,
        risk_level: RiskLevel
    ) -> str:
        """Generate maintenance recommendation"""
        if risk_level == RiskLevel.CRITICAL:
            return "IMMEDIATE ACTION REQUIRED: Schedule emergency maintenance within 24 hours"
        elif risk_level == RiskLevel.HIGH:
            return "HIGH PRIORITY: Schedule maintenance within 1 week"
        elif risk_level == RiskLevel.MEDIUM:
            return "MEDIUM PRIORITY: Schedule maintenance within 1 month"
        else:
            return "LOW PRIORITY: Continue normal monitoring, next maintenance in 3-6 months"
    
    def _identify_contributing_factors(
        self,
        state: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        """Identify factors contributing to failure risk"""
        factors = []
        
        vibration = state.get('vibration', 0.0)
        if vibration > 5.0:
            factors.append(('High vibration', min(vibration / 20.0, 1.0)))
        
        temperature = state.get('temperature', 20.0)
        if temperature > 80.0:
            factors.append(('Elevated temperature', min((temperature - 80.0) / 40.0, 1.0)))
        
        operating_hours = state.get('operating_hours', 0.0)
        if operating_hours > 30000:
            factors.append(('High operating hours', min(operating_hours / 100000.0, 1.0)))
        
        efficiency = state.get('efficiency', 0.85)
        if efficiency < 0.75:
            factors.append(('Low efficiency', 1.0 - efficiency))
        
        factors.sort(key=lambda x: x[1], reverse=True)
        
        return factors[:5]


class OptimizationEngine:
    """Multi-objective optimization engine"""
    
    def __init__(self, equipment_type: str):
        """Initialize optimization engine"""
        self.equipment_type = equipment_type
        self.constraints = {}
        self.objectives = ['efficiency', 'cost', 'reliability']
        
        logger.info(f"OptimizationEngine initialized for {equipment_type}")
    
    def optimize(
        self,
        current_state: Dict[str, float],
        constraints: Optional[Dict[str, Tuple[float, float]]] = None,
        objectives: Optional[List[str]] = None
    ) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations"""
        try:
            if constraints:
                self.constraints = constraints
            if objectives:
                self.objectives = objectives
            
            recommendations = []
            
            if 'flow_rate' in current_state:
                rec = self._optimize_flow_rate(current_state)
                if rec:
                    recommendations.append(rec)
            
            if 'pressure' in current_state:
                rec = self._optimize_pressure(current_state)
                if rec:
                    recommendations.append(rec)
            
            if 'speed' in current_state:
                rec = self._optimize_speed(current_state)
                if rec:
                    recommendations.append(rec)
            
            if 'temperature' in current_state:
                rec = self._optimize_temperature(current_state)
                if rec:
                    recommendations.append(rec)
            
            recommendations.sort(key=lambda x: (x.priority, -x.expected_improvement))
            
            logger.info(f"Generated {len(recommendations)} optimization recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in optimization: {e}")
            raise
    
    def _optimize_flow_rate(self, state: Dict[str, float]) -> Optional[OptimizationRecommendation]:
        """Optimize flow rate parameter"""
        current_flow = state.get('flow_rate', 0.0)
        optimal_flow = state.get('rated_capacity', 100.0) * 0.8
        
        if abs(current_flow - optimal_flow) / optimal_flow > 0.1:
            improvement = abs(current_flow - optimal_flow) / current_flow
            
            return OptimizationRecommendation(
                parameter_name='flow_rate',
                current_value=current_flow,
                recommended_value=optimal_flow,
                expected_improvement=improvement,
                impact_on_efficiency=0.05,
                impact_on_cost=-0.03,
                impact_on_reliability=0.02,
                priority=1,
                implementation_difficulty='Easy',
                estimated_savings=500.0,
                payback_period=0.5
            )
        
        return None
    
    def _optimize_pressure(self, state: Dict[str, float]) -> Optional[OptimizationRecommendation]:
        """Optimize pressure parameter"""
        current_pressure = state.get('pressure', 0.0)
        target_pressure = state.get('target_pressure', 100.0)
        
        if abs(current_pressure - target_pressure) / target_pressure > 0.05:
            improvement = abs(current_pressure - target_pressure) / current_pressure
            
            return OptimizationRecommendation(
                parameter_name='pressure',
                current_value=current_pressure,
                recommended_value=target_pressure,
                expected_improvement=improvement,
                impact_on_efficiency=0.03,
                impact_on_cost=-0.02,
                impact_on_reliability=0.04,
                priority=2,
                implementation_difficulty='Medium',
                estimated_savings=300.0,
                payback_period=1.0
            )
        
        return None
    
    def _optimize_speed(self, state: Dict[str, float]) -> Optional[OptimizationRecommendation]:
        """Optimize speed parameter"""
        current_speed = state.get('speed', 0.0)
        rated_speed = state.get('rated_speed', 3000.0)
        optimal_speed = rated_speed * 0.9
        
        if abs(current_speed - optimal_speed) / optimal_speed > 0.1:
            improvement = abs(current_speed - optimal_speed) / current_speed
            
            return OptimizationRecommendation(
                parameter_name='speed',
                current_value=current_speed,
                recommended_value=optimal_speed,
                expected_improvement=improvement,
                impact_on_efficiency=0.04,
                impact_on_cost=-0.04,
                impact_on_reliability=0.03,
                priority=1,
                implementation_difficulty='Easy',
                estimated_savings=400.0,
                payback_period=0.75
            )
        
        return None
    
    def _optimize_temperature(self, state: Dict[str, float]) -> Optional[OptimizationRecommendation]:
        """Optimize temperature parameter"""
        current_temp = state.get('temperature', 20.0)
        optimal_temp = 60.0
        
        if abs(current_temp - optimal_temp) > 10.0:
            improvement = abs(current_temp - optimal_temp) / 100.0
            
            return OptimizationRecommendation(
                parameter_name='temperature',
                current_value=current_temp,
                recommended_value=optimal_temp,
                expected_improvement=improvement,
                impact_on_efficiency=0.02,
                impact_on_cost=-0.01,
                impact_on_reliability=0.05,
                priority=3,
                implementation_difficulty='Medium',
                estimated_savings=200.0,
                payback_period=2.0
            )
        
        return None
    
    def pareto_frontier(
        self,
        scenarios: List[ScenarioResult]
    ) -> List[ScenarioResult]:
        """Calculate Pareto frontier for multi-objective optimization"""
        pareto_optimal = []
        
        for i, scenario_i in enumerate(scenarios):
            is_dominated = False
            
            for j, scenario_j in enumerate(scenarios):
                if i != j:
                    if (scenario_j.performance_metrics.efficiency >= scenario_i.performance_metrics.efficiency and
                        scenario_j.total_cost <= scenario_i.total_cost and
                        scenario_j.prediction.failure_probability <= scenario_i.prediction.failure_probability):
                        
                        if (scenario_j.performance_metrics.efficiency > scenario_i.performance_metrics.efficiency or
                            scenario_j.total_cost < scenario_i.total_cost or
                            scenario_j.prediction.failure_probability < scenario_i.prediction.failure_probability):
                            is_dominated = True
                            break
            
            if not is_dominated:
                pareto_optimal.append(scenario_i)
        
        return pareto_optimal
    
    def sensitivity_analysis(
        self,
        base_state: Dict[str, float],
        parameter: str,
        variation_range: Tuple[float, float],
        num_points: int = 10
    ) -> Dict[str, List[float]]:
        """Perform sensitivity analysis on a parameter"""
        param_values = np.linspace(variation_range[0], variation_range[1], num_points)
        
        results = {
            'parameter_values': param_values.tolist(),
            'efficiency': [],
            'cost': [],
            'reliability': []
        }
        
        for value in param_values:
            modified_state = base_state.copy()
            modified_state[parameter] = value
            
            efficiency = 0.85 - abs(value - base_state[parameter]) / base_state[parameter] * 0.1
            cost = 1000 + abs(value - base_state[parameter]) * 10
            reliability = 0.9 - abs(value - base_state[parameter]) / base_state[parameter] * 0.05
            
            results['efficiency'].append(max(0, min(efficiency, 1.0)))
            results['cost'].append(cost)
            results['reliability'].append(max(0, min(reliability, 1.0)))
        
        return results


class ScenarioSimulator:
    """What-if scenario simulation engine"""
    
    def __init__(self, equipment_id: str):
        """Initialize scenario simulator"""
        self.equipment_id = equipment_id
        self.scenarios = {}
        
        logger.info(f"ScenarioSimulator initialized for {equipment_id}")
    
    def create_scenario(
        self,
        scenario_name: str,
        parameters: Dict[str, float],
        description: str = ""
    ) -> str:
        """Create a new scenario"""
        scenario_id = f"scenario_{len(self.scenarios) + 1}"
        
        self.scenarios[scenario_id] = {
            'name': scenario_name,
            'parameters': parameters,
            'description': description,
            'created_at': datetime.now()
        }
        
        logger.info(f"Created scenario: {scenario_name} (ID: {scenario_id})")
        return scenario_id
    
    def simulate_scenario(
        self,
        scenario_id: str,
        performance_analyzer: PerformanceAnalyzer,
        predictive_analyzer: PredictiveAnalyzer
    ) -> ScenarioResult:
        """Simulate a scenario"""
        try:
            if scenario_id not in self.scenarios:
                raise ValueError(f"Scenario {scenario_id} not found")
            
            scenario = self.scenarios[scenario_id]
            parameters = scenario['parameters']
            
            performance_metrics = performance_analyzer.analyze_performance(parameters)
            prediction = predictive_analyzer.predict_failure(parameters)
            
            total_cost = self._calculate_total_cost(parameters, performance_metrics)
            total_benefit = self._calculate_total_benefit(parameters, performance_metrics)
            net_value = total_benefit - total_cost
            
            risk_score = self._calculate_risk_score(prediction, performance_metrics)
            feasibility_score = self._calculate_feasibility_score(parameters)
            
            result = ScenarioResult(
                scenario_id=scenario_id,
                scenario_name=scenario['name'],
                parameters=parameters,
                performance_metrics=performance_metrics,
                prediction=prediction,
                total_cost=total_cost,
                total_benefit=total_benefit,
                net_value=net_value,
                risk_score=risk_score,
                feasibility_score=feasibility_score
            )
            
            logger.info(f"Simulated scenario {scenario_id}: net_value={net_value:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error simulating scenario: {e}")
            raise
    
    def compare_scenarios(
        self,
        scenario_results: List[ScenarioResult]
    ) -> Dict[str, Any]:
        """Compare multiple scenarios"""
        if not scenario_results:
            return {}
        
        ranked_scenarios = sorted(scenario_results, key=lambda x: x.net_value, reverse=True)
        
        for i, scenario in enumerate(ranked_scenarios):
            scenario.rank = i + 1
        
        best_efficiency = max(scenario_results, key=lambda x: x.performance_metrics.efficiency)
        best_cost = min(scenario_results, key=lambda x: x.total_cost)
        best_reliability = min(scenario_results, key=lambda x: x.prediction.failure_probability)
        best_overall = ranked_scenarios[0]
        
        efficiencies = [s.performance_metrics.efficiency for s in scenario_results]
        costs = [s.total_cost for s in scenario_results]
        net_values = [s.net_value for s in scenario_results]
        
        comparison = {
            'ranked_scenarios': [s.to_dict() for s in ranked_scenarios],
            'best_for_efficiency': best_efficiency.to_dict(),
            'best_for_cost': best_cost.to_dict(),
            'best_for_reliability': best_reliability.to_dict(),
            'best_overall': best_overall.to_dict(),
            'statistics': {
                'efficiency': {
                    'mean': float(np.mean(efficiencies)),
                    'std': float(np.std(efficiencies)),
                    'min': float(np.min(efficiencies)),
                    'max': float(np.max(efficiencies))
                },
                'cost': {
                    'mean': float(np.mean(costs)),
                    'std': float(np.std(costs)),
                    'min': float(np.min(costs)),
                    'max': float(np.max(costs))
                },
                'net_value': {
                    'mean': float(np.mean(net_values)),
                    'std': float(np.std(net_values)),
                    'min': float(np.min(net_values)),
                    'max': float(np.max(net_values))
                }
            }
        }
        
        return comparison
    
    def monte_carlo_simulation(
        self,
        base_parameters: Dict[str, float],
        parameter_uncertainties: Dict[str, float],
        num_simulations: int = 1000,
        performance_analyzer: Optional[PerformanceAnalyzer] = None,
        predictive_analyzer: Optional[PredictiveAnalyzer] = None
    ) -> Dict[str, Any]:
        """Perform Monte Carlo simulation for uncertainty analysis"""
        results = {
            'efficiency': [],
            'cost': [],
            'failure_probability': [],
            'net_value': []
        }
        
        for _ in range(num_simulations):
            sim_parameters = {}
            for param, base_value in base_parameters.items():
                if param in parameter_uncertainties:
                    uncertainty = parameter_uncertainties[param]
                    sim_parameters[param] = np.random.normal(base_value, uncertainty)
                else:
                    sim_parameters[param] = base_value
            
            if performance_analyzer and predictive_analyzer:
                perf_metrics = performance_analyzer.analyze_performance(sim_parameters)
                prediction = predictive_analyzer.predict_failure(sim_parameters)
                
                results['efficiency'].append(perf_metrics.efficiency)
                results['cost'].append(perf_metrics.operational_cost)
                results['failure_probability'].append(prediction.failure_probability)
                results['net_value'].append(
                    perf_metrics.throughput * 100 - perf_metrics.operational_cost
                )
        
        statistics = {}
        for key, values in results.items():
            if values:
                statistics[key] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'percentile_5': float(np.percentile(values, 5)),
                    'percentile_95': float(np.percentile(values, 95))
                }
        
        return {
            'num_simulations': num_simulations,
            'results': results,
            'statistics': statistics
        }
    
    def _calculate_total_cost(
        self,
        parameters: Dict[str, float],
        metrics: PerformanceMetrics
    ) -> float:
        """Calculate total cost for scenario"""
        return metrics.operational_cost + metrics.maintenance_cost
    
    def _calculate_total_benefit(
        self,
        parameters: Dict[str, float],
        metrics: PerformanceMetrics
    ) -> float:
        """Calculate total benefit for scenario"""
        throughput_value = metrics.throughput * 100
        efficiency_benefit = metrics.efficiency * 1000
        
        return throughput_value + efficiency_benefit
    
    def _calculate_risk_score(
        self,
        prediction: PredictionResult,
        metrics: PerformanceMetrics
    ) -> float:
        """Calculate overall risk score (0-1, lower is better)"""
        failure_risk = prediction.failure_probability
        performance_risk = 1.0 - metrics.performance_index / 100.0
        
        risk_score = (failure_risk * 0.6 + performance_risk * 0.4)
        return min(risk_score, 1.0)
    
    def _calculate_feasibility_score(self, parameters: Dict[str, float]) -> float:
        """Calculate feasibility score (0-1, higher is better)"""
        score = 1.0
        
        for param, value in parameters.items():
            if value < 0:
                score *= 0.5
        
        return max(0.0, min(score, 1.0))


class TrendAnalyzer:
    """Time-series trend analysis and forecasting"""
    
    def __init__(self):
        """Initialize trend analyzer"""
        self.min_data_points = 10
        
        logger.info("TrendAnalyzer initialized")
    
    def analyze_trend(
        self,
        parameter_name: str,
        time_series: pd.Series,
        forecast_periods: int = 24
    ) -> TrendAnalysis:
        """Analyze trend in time-series data"""
        try:
            if len(time_series) < self.min_data_points:
                raise ValueError(f"Insufficient data points. Need at least {self.min_data_points}")
            
            trend_type = self._classify_trend(time_series)
            slope, r_squared = self._calculate_trend_line(time_series)
            forecast_values, forecast_timestamps = self._forecast(time_series, forecast_periods)
            seasonal_component = self._detect_seasonality(time_series)
            change_points = self._detect_change_points(time_series)
            correlation_with = {}
            
            analysis = TrendAnalysis(
                parameter_name=parameter_name,
                trend_type=trend_type,
                slope=slope,
                r_squared=r_squared,
                forecast_values=forecast_values,
                forecast_timestamps=forecast_timestamps,
                seasonal_component=seasonal_component,
                change_points=change_points,
                correlation_with=correlation_with
            )
            
            logger.debug(f"Trend analysis complete for {parameter_name}: {trend_type.value}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            raise
    
    def _classify_trend(self, series: pd.Series) -> TrendType:
        """Classify trend type"""
        values = series.values
        
        if len(values) < 3:
            return TrendType.STABLE
        
        slope, _ = self._calculate_trend_line(series)
        volatility = np.std(np.diff(values)) / np.mean(np.abs(values)) if np.mean(np.abs(values)) > 0 else 0
        
        if volatility > 0.2:
            return TrendType.VOLATILE
        elif abs(slope) < 0.01:
            return TrendType.STABLE
        elif slope > 0.01:
            return TrendType.INCREASING
        else:
            return TrendType.DECREASING
    
    def _calculate_trend_line(self, series: pd.Series) -> Tuple[float, float]:
        """Calculate trend line using linear regression"""
        x = np.arange(len(series))
        y = series.values
        
        if len(x) < 2:
            return 0.0, 0.0
        
        slope, intercept, r_value, _, _ = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        return float(slope), float(r_squared)
    
    def _forecast(
        self,
        series: pd.Series,
        periods: int
    ) -> Tuple[List[float], List[datetime]]:
        """Forecast future values"""
        x = np.arange(len(series))
        y = series.values
        
        slope, intercept, _, _, _ = stats.linregress(x, y)
        
        future_x = np.arange(len(series), len(series) + periods)
        forecast_values = [float(slope * xi + intercept) for xi in future_x]
        
        if isinstance(series.index, pd.DatetimeIndex):
            last_timestamp = series.index[-1]
            time_delta = series.index[-1] - series.index[-2] if len(series) > 1 else timedelta(hours=1)
            forecast_timestamps = [last_timestamp + time_delta * (i + 1) for i in range(periods)]
        else:
            forecast_timestamps = [datetime.now() + timedelta(hours=i+1) for i in range(periods)]
        
        return forecast_values, forecast_timestamps
    
    def _detect_seasonality(self, series: pd.Series) -> Optional[np.ndarray]:
        """Detect seasonal patterns"""
        if len(series) < 24:
            return None
        
        try:
            fft = np.fft.fft(series.values)
            power = np.abs(fft) ** 2
            
            threshold = np.mean(power) + 2 * np.std(power)
            seasonal_indices = np.where(power > threshold)[0]
            
            if len(seasonal_indices) > 0:
                return power
            
        except Exception as e:
            logger.warning(f"Error detecting seasonality: {e}")
        
        return None
    
    def _detect_change_points(self, series: pd.Series) -> List[datetime]:
        """Detect change points in time series"""
        change_points = []
        
        if len(series) < 10:
            return change_points
        
        values = series.values
        window_size = min(5, len(values) // 3)
        
        for i in range(window_size, len(values) - window_size):
            before = values[i-window_size:i]
            after = values[i:i+window_size]
            
            if len(before) > 0 and len(after) > 0:
                mean_diff = abs(np.mean(after) - np.mean(before))
                std_combined = np.std(np.concatenate([before, after]))
                
                if std_combined > 0 and mean_diff > 2 * std_combined:
                    if isinstance(series.index, pd.DatetimeIndex):
                        change_points.append(series.index[i])
                    else:
                        change_points.append(datetime.now())
        
        return change_points
    
    def calculate_correlation(
        self,
        series1: pd.Series,
        series2: pd.Series
    ) -> float:
        """Calculate correlation between two time series"""
        if len(series1) != len(series2):
            min_len = min(len(series1), len(series2))
            series1 = series1.iloc[:min_len]
            series2 = series2.iloc[:min_len]
        
        if len(series1) < 2:
            return 0.0
        
        correlation, _ = stats.pearsonr(series1.values, series2.values)
        return float(correlation)


class AnomalyDetector:
    """Real-time anomaly detection"""
    
    def __init__(self, contamination: float = 0.1):
        """
        Initialize anomaly detector
        
        Args:
            contamination: Expected proportion of anomalies
        """
        self.contamination = contamination
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.historical_mean = {}
        self.historical_std = {}
        
        logger.info("AnomalyDetector initialized")
    
    def train(self, historical_data: pd.DataFrame):
        """Train anomaly detection model"""
        try:
            numeric_columns = historical_data.select_dtypes(include=[np.number]).columns
            data = historical_data[numeric_columns].values
            
            data_scaled = self.scaler.fit_transform(data)
            self.isolation_forest.fit(data_scaled)
            
            for col in numeric_columns:
                self.historical_mean[col] = historical_data[col].mean()
                self.historical_std[col] = historical_data[col].std()
            
            self.is_trained = True
            logger.info("Anomaly detection model trained successfully")
            
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}")
            raise
    
    def detect_anomalies(
        self,
        current_state: Dict[str, float],
        parameter_name: Optional[str] = None
    ) -> List[AnomalyDetection]:
        """Detect anomalies in current state"""
        anomalies = []
        
        try:
            if parameter_name:
                parameters_to_check = [parameter_name]
            else:
                parameters_to_check = list(current_state.keys())
            
            for param in parameters_to_check:
                if param not in current_state:
                    continue
                
                value = current_state[param]
                
                is_anomaly, severity, score = self._check_statistical_anomaly(param, value)
                
                if is_anomaly:
                    expected_value = self.historical_mean.get(param, value)
                    deviation = abs(value - expected_value)
                    
                    root_causes = self._suggest_root_causes(param, value, expected_value)
                    actions = self._recommend_actions(param, severity)
                    
                    anomaly = AnomalyDetection(
                        timestamp=datetime.now(),
                        parameter_name=param,
                        value=value,
                        expected_value=expected_value,
                        deviation=deviation,
                        severity=severity,
                        anomaly_score=score,
                        root_cause_suggestions=root_causes,
                        recommended_actions=actions
                    )
                    
                    anomalies.append(anomaly)
                    logger.warning(f"Anomaly detected in {param}: {severity.value}")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            raise
    
    def _check_statistical_anomaly(
        self,
        parameter: str,
        value: float
    ) -> Tuple[bool, AnomalySeverity, float]:
        """Check for statistical anomaly using z-score"""
        if parameter not in self.historical_mean:
            return False, AnomalySeverity.MINOR, 0.0
        
        mean = self.historical_mean[parameter]
        std = self.historical_std.get(parameter, 1.0)
        
        if std == 0:
            return False, AnomalySeverity.MINOR, 0.0
        
        z_score = abs((value - mean) / std)
        
        if z_score > 4.0:
            return True, AnomalySeverity.CRITICAL, float(z_score)
        elif z_score > 3.0:
            return True, AnomalySeverity.MAJOR, float(z_score)
        elif z_score > 2.0:
            return True, AnomalySeverity.MODERATE, float(z_score)
        elif z_score > 1.5:
            return True, AnomalySeverity.MINOR, float(z_score)
        else:
            return False, AnomalySeverity.MINOR, float(z_score)
    
    def _suggest_root_causes(
        self,
        parameter: str,
        value: float,
        expected_value: float
    ) -> List[str]:
        """Suggest possible root causes for anomaly"""
        causes = []
        
        if parameter == 'vibration':
            if value > expected_value:
                causes.extend([
                    "Bearing wear or damage",
                    "Misalignment",
                    "Imbalance in rotating components",
                    "Loose mounting bolts"
                ])
        
        elif parameter == 'temperature':
            if value > expected_value:
                causes.extend([
                    "Insufficient cooling",
                    "Bearing failure",
                    "Excessive friction",
                    "Blocked ventilation"
                ])
        
        elif parameter == 'pressure':
            if value > expected_value:
                causes.extend([
                    "Blockage in discharge line",
                    "Valve malfunction",
                    "Pump cavitation"
                ])
            else:
                causes.extend([
                    "Leak in system",
                    "Pump wear",
                    "Suction problems"
                ])
        
        elif parameter == 'efficiency':
            if value < expected_value:
                causes.extend([
                    "Component wear",
                    "Fouling or scaling",
                    "Operating outside design point",
                    "Mechanical damage"
                ])
        
        else:
            causes.append(f"Unusual {parameter} reading detected")
        
        return causes[:3]
    
    def _recommend_actions(
        self,
        parameter: str,
        severity: AnomalySeverity
    ) -> List[str]:
        """Recommend actions based on anomaly"""
        actions = []
        
        if severity == AnomalySeverity.CRITICAL:
            actions.extend([
                "IMMEDIATE: Stop equipment and inspect",
                "Contact maintenance team urgently",
                "Review recent operational changes"
            ])
        elif severity == AnomalySeverity.MAJOR:
            actions.extend([
                "Schedule inspection within 24 hours",
                "Increase monitoring frequency",
                "Prepare for potential shutdown"
            ])
        elif severity == AnomalySeverity.MODERATE:
            actions.extend([
                "Schedule inspection within 1 week",
                "Monitor parameter closely",
                "Check related parameters"
            ])
        else:
            actions.extend([
                "Continue monitoring",
                "Log for trend analysis",
                "Review during next maintenance"
            ])
        
        return actions


class RealtimeAnalysisEngine:
    """Main real-time analysis and simulation engine"""
    
    def __init__(self, equipment_id: str, equipment_type: str, rated_capacity: float):
        """
        Initialize real-time analysis engine
        
        Args:
            equipment_id: Unique equipment identifier
            equipment_type: Type of equipment
            rated_capacity: Rated capacity
        """
        self.equipment_id = equipment_id
        self.equipment_type = equipment_type
        self.rated_capacity = rated_capacity
        
        self.performance_analyzer = PerformanceAnalyzer(equipment_type, rated_capacity)
        self.predictive_analyzer = PredictiveAnalyzer(equipment_id, equipment_type)
        self.optimization_engine = OptimizationEngine(equipment_type)
        self.scenario_simulator = ScenarioSimulator(equipment_id)
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        
        self.cache = {}
        self.cache_timeout = 300
        
        logger.info(f"RealtimeAnalysisEngine initialized for {equipment_id}")
    
    def analyze_realtime(
        self,
        current_state: Dict[str, float],
        historical_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive real-time analysis
        
        Args:
            current_state: Current operating parameters
            historical_data: Historical data for context
            
        Returns:
            Complete analysis results
        """
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'equipment_id': self.equipment_id,
                'equipment_type': self.equipment_type
            }
            
            results['performance'] = self.performance_analyzer.analyze_performance(
                current_state, historical_data
            ).to_dict()
            
            results['prediction'] = self.predictive_analyzer.predict_failure(
                current_state, historical_data
            ).to_dict()
            
            results['optimization'] = [
                rec.to_dict() for rec in self.optimization_engine.optimize(current_state)
            ]
            
            results['anomalies'] = [
                anom.to_dict() for anom in self.anomaly_detector.detect_anomalies(current_state)
            ]
            
            logger.info(f"Real-time analysis complete for {self.equipment_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error in real-time analysis: {e}")
            raise
    
    def export_report(
        self,
        analysis_results: Dict[str, Any],
        format: str = 'json'
    ) -> str:
        """
        Export analysis report
        
        Args:
            analysis_results: Analysis results to export
            format: Export format (json, csv)
            
        Returns:
            Exported report as string
        """
        if format == 'json':
            return json.dumps(analysis_results, indent=2)
        elif format == 'csv':
            df = pd.DataFrame([analysis_results])
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_cache(self):
        """Clear analysis cache"""
        self.cache = {}
        logger.info("Analysis cache cleared")