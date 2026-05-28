"""
Test script for Real-time Analysis and Simulation Engine

This script demonstrates the capabilities of the real-time analysis engine
including performance analysis, predictive analytics, optimization,
scenario simulation, trend analysis, and anomaly detection.

Author: PetroFlow Development Team
Date: 2026-05-13
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

from core.realtime_analysis_engine import (
    RealtimeAnalysisEngine,
    PerformanceAnalyzer,
    PredictiveAnalyzer,
    OptimizationEngine,
    ScenarioSimulator,
    TrendAnalyzer,
    AnomalyDetector
)


def generate_sample_data(num_points: int = 100) -> pd.DataFrame:
    """Generate sample historical data for testing"""
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(num_points, 0, -1)]
    
    data = {
        'timestamp': timestamps,
        'vibration': np.random.normal(3.0, 0.5, num_points),
        'temperature': np.random.normal(60.0, 5.0, num_points),
        'pressure': np.random.normal(100.0, 10.0, num_points),
        'flow_rate': np.random.normal(80.0, 8.0, num_points),
        'power': np.random.normal(500.0, 50.0, num_points),
        'efficiency': np.random.normal(0.85, 0.05, num_points),
        'operating_hours': np.linspace(10000, 10100, num_points)
    }
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    return df


def test_performance_analyzer():
    """Test PerformanceAnalyzer"""
    print("\n" + "="*80)
    print("TESTING PERFORMANCE ANALYZER")
    print("="*80)
    
    analyzer = PerformanceAnalyzer(equipment_type='pump', rated_capacity=100.0)
    
    current_state = {
        'flow_rate': 85.0,
        'head': 50.0,
        'power': 550.0,
        'vibration': 4.5,
        'temperature': 65.0,
        'operating_hours': 15000.0,
        'efficiency': 0.82
    }
    
    historical_data = generate_sample_data(50)
    
    metrics = analyzer.analyze_performance(current_state, historical_data)
    
    print(f"\nPerformance Metrics:")
    print(f"  Efficiency: {metrics.efficiency:.2%}")
    print(f"  Power Consumption: {metrics.power_consumption:.2f} kW")
    print(f"  Throughput: {metrics.throughput:.2f} m³/h")
    print(f"  Reliability Score: {metrics.reliability_score:.2%}")
    print(f"  Operational Cost: ${metrics.operational_cost:.2f}/hr")
    print(f"  Energy Cost: ${metrics.energy_cost:.2f}/hr")
    print(f"  Maintenance Cost: ${metrics.maintenance_cost:.2f}/month")
    print(f"  CO2 Emissions: {metrics.co2_emissions:.2f} kg/hr")
    print(f"  Environmental Impact: {metrics.environmental_impact:.2%}")
    print(f"  Deviation from Optimal: {metrics.deviation_from_optimal:.2%}")
    print(f"  Performance Index: {metrics.performance_index:.1f}/100")
    
    return metrics


def test_predictive_analyzer():
    """Test PredictiveAnalyzer"""
    print("\n" + "="*80)
    print("TESTING PREDICTIVE ANALYZER")
    print("="*80)
    
    analyzer = PredictiveAnalyzer(equipment_id='PUMP-001', equipment_type='pump')
    
    current_state = {
        'vibration': 8.5,
        'temperature': 85.0,
        'pressure': 95.0,
        'flow_rate': 75.0,
        'power': 580.0,
        'efficiency': 0.78,
        'operating_hours': 35000.0
    }
    
    historical_data = generate_sample_data(100)
    
    prediction = analyzer.predict_failure(current_state, historical_data)
    
    print(f"\nPrediction Results:")
    print(f"  Failure Probability: {prediction.failure_probability:.2%}")
    print(f"  Remaining Useful Life: {prediction.remaining_useful_life:.0f} hours")
    print(f"  Confidence Interval: [{prediction.confidence_lower:.0f}, {prediction.confidence_upper:.0f}] hours")
    print(f"  Risk Level: {prediction.risk_level.value.upper()}")
    print(f"  Maintenance Recommendation: {prediction.maintenance_recommendation}")
    
    if prediction.predicted_failure_date:
        print(f"  Predicted Failure Date: {prediction.predicted_failure_date.strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\n  Contributing Factors:")
    for factor, impact in prediction.contributing_factors:
        print(f"    - {factor}: {impact:.2%} impact")
    
    return prediction


def test_optimization_engine():
    """Test OptimizationEngine"""
    print("\n" + "="*80)
    print("TESTING OPTIMIZATION ENGINE")
    print("="*80)
    
    engine = OptimizationEngine(equipment_type='pump')
    
    current_state = {
        'flow_rate': 65.0,
        'pressure': 110.0,
        'speed': 2500.0,
        'temperature': 75.0,
        'rated_capacity': 100.0,
        'target_pressure': 100.0,
        'rated_speed': 3000.0
    }
    
    recommendations = engine.optimize(current_state)
    
    print(f"\nOptimization Recommendations ({len(recommendations)} found):")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n  {i}. {rec.parameter_name.upper()}")
        print(f"     Current Value: {rec.current_value:.2f}")
        print(f"     Recommended Value: {rec.recommended_value:.2f}")
        print(f"     Expected Improvement: {rec.expected_improvement:.2%}")
        print(f"     Impact on Efficiency: {rec.impact_on_efficiency:+.2%}")
        print(f"     Impact on Cost: {rec.impact_on_cost:+.2%}")
        print(f"     Impact on Reliability: {rec.impact_on_reliability:+.2%}")
        print(f"     Priority: {rec.priority}")
        print(f"     Implementation Difficulty: {rec.implementation_difficulty}")
        print(f"     Estimated Savings: ${rec.estimated_savings:.2f}/year")
        print(f"     Payback Period: {rec.payback_period:.1f} years")
    
    return recommendations


def test_scenario_simulator():
    """Test ScenarioSimulator"""
    print("\n" + "="*80)
    print("TESTING SCENARIO SIMULATOR")
    print("="*80)
    
    simulator = ScenarioSimulator(equipment_id='PUMP-001')
    performance_analyzer = PerformanceAnalyzer(equipment_type='pump', rated_capacity=100.0)
    predictive_analyzer = PredictiveAnalyzer(equipment_id='PUMP-001', equipment_type='pump')
    
    scenarios = [
        {
            'name': 'Current Operation',
            'parameters': {
                'flow_rate': 75.0,
                'head': 50.0,
                'power': 550.0,
                'vibration': 5.0,
                'temperature': 65.0,
                'operating_hours': 20000.0
            }
        },
        {
            'name': 'Optimized Operation',
            'parameters': {
                'flow_rate': 80.0,
                'head': 50.0,
                'power': 520.0,
                'vibration': 3.5,
                'temperature': 60.0,
                'operating_hours': 20000.0
            }
        },
        {
            'name': 'High Load Operation',
            'parameters': {
                'flow_rate': 95.0,
                'head': 55.0,
                'power': 650.0,
                'vibration': 6.5,
                'temperature': 75.0,
                'operating_hours': 20000.0
            }
        }
    ]
    
    scenario_results = []
    
    for scenario in scenarios:
        scenario_id = simulator.create_scenario(
            scenario_name=scenario['name'],
            parameters=scenario['parameters']
        )
        
        result = simulator.simulate_scenario(
            scenario_id,
            performance_analyzer,
            predictive_analyzer
        )
        
        scenario_results.append(result)
    
    comparison = simulator.compare_scenarios(scenario_results)
    
    print(f"\nScenario Comparison:")
    print(f"\n  Ranked Scenarios:")
    for scenario in comparison['ranked_scenarios']:
        print(f"    {scenario['rank']}. {scenario['scenario_name']}")
        print(f"       Net Value: ${scenario['net_value']:.2f}")
        print(f"       Efficiency: {scenario['performance_metrics']['efficiency']:.2%}")
        print(f"       Total Cost: ${scenario['total_cost']:.2f}")
        print(f"       Risk Score: {scenario['risk_score']:.2%}")
    
    print(f"\n  Best Overall: {comparison['best_overall']['scenario_name']}")
    print(f"  Best for Efficiency: {comparison['best_for_efficiency']['scenario_name']}")
    print(f"  Best for Cost: {comparison['best_for_cost']['scenario_name']}")
    print(f"  Best for Reliability: {comparison['best_for_reliability']['scenario_name']}")
    
    return scenario_results, comparison


def test_trend_analyzer():
    """Test TrendAnalyzer"""
    print("\n" + "="*80)
    print("TESTING TREND ANALYZER")
    print("="*80)
    
    analyzer = TrendAnalyzer()
    
    historical_data = generate_sample_data(100)
    
    time_series = historical_data['vibration']
    
    analysis = analyzer.analyze_trend(
        parameter_name='vibration',
        time_series=time_series,
        forecast_periods=24
    )
    
    print(f"\nTrend Analysis for Vibration:")
    print(f"  Trend Type: {analysis.trend_type.value.upper()}")
    print(f"  Slope: {analysis.slope:.4f}")
    print(f"  R-squared: {analysis.r_squared:.4f}")
    print(f"  Number of Change Points: {len(analysis.change_points)}")
    
    print(f"\n  24-Hour Forecast:")
    for i in range(0, min(6, len(analysis.forecast_values))):
        print(f"    +{i*4}h: {analysis.forecast_values[i]:.2f}")
    
    return analysis


def test_anomaly_detector():
    """Test AnomalyDetector"""
    print("\n" + "="*80)
    print("TESTING ANOMALY DETECTOR")
    print("="*80)
    
    detector = AnomalyDetector(contamination=0.1)
    
    historical_data = generate_sample_data(200)
    detector.train(historical_data)
    
    normal_state = {
        'vibration': 3.2,
        'temperature': 62.0,
        'pressure': 98.0,
        'flow_rate': 82.0,
        'power': 510.0,
        'efficiency': 0.84
    }
    
    anomalous_state = {
        'vibration': 12.5,
        'temperature': 95.0,
        'pressure': 75.0,
        'flow_rate': 55.0,
        'power': 680.0,
        'efficiency': 0.65
    }
    
    print("\n  Testing Normal State:")
    normal_anomalies = detector.detect_anomalies(normal_state)
    print(f"    Anomalies Detected: {len(normal_anomalies)}")
    
    print("\n  Testing Anomalous State:")
    anomalies = detector.detect_anomalies(anomalous_state)
    print(f"    Anomalies Detected: {len(anomalies)}")
    
    for anomaly in anomalies:
        print(f"\n    Parameter: {anomaly.parameter_name}")
        print(f"      Value: {anomaly.value:.2f}")
        print(f"      Expected: {anomaly.expected_value:.2f}")
        print(f"      Deviation: {anomaly.deviation:.2f}")
        print(f"      Severity: {anomaly.severity.value.upper()}")
        print(f"      Anomaly Score: {anomaly.anomaly_score:.2f}")
        print(f"      Root Causes:")
        for cause in anomaly.root_cause_suggestions:
            print(f"        - {cause}")
        print(f"      Recommended Actions:")
        for action in anomaly.recommended_actions[:2]:
            print(f"        - {action}")
    
    return anomalies


def test_realtime_analysis_engine():
    """Test complete RealtimeAnalysisEngine"""
    print("\n" + "="*80)
    print("TESTING COMPLETE REALTIME ANALYSIS ENGINE")
    print("="*80)
    
    engine = RealtimeAnalysisEngine(
        equipment_id='PUMP-001',
        equipment_type='pump',
        rated_capacity=100.0
    )
    
    historical_data = generate_sample_data(150)
    engine.anomaly_detector.train(historical_data)
    
    current_state = {
        'flow_rate': 78.0,
        'head': 52.0,
        'power': 560.0,
        'vibration': 7.2,
        'temperature': 72.0,
        'pressure': 102.0,
        'operating_hours': 28000.0,
        'efficiency': 0.80,
        'rated_capacity': 100.0,
        'target_pressure': 100.0,
        'rated_speed': 3000.0,
        'speed': 2800.0
    }
    
    results = engine.analyze_realtime(current_state, historical_data)
    
    print(f"\nComprehensive Analysis Results:")
    print(f"  Equipment: {results['equipment_id']} ({results['equipment_type']})")
    print(f"  Timestamp: {results['timestamp']}")
    
    print(f"\n  Performance:")
    print(f"    Efficiency: {results['performance']['efficiency']:.2%}")
    print(f"    Performance Index: {results['performance']['performance_index']:.1f}/100")
    print(f"    Operational Cost: ${results['performance']['operational_cost']:.2f}/hr")
    
    print(f"\n  Prediction:")
    print(f"    Failure Probability: {results['prediction']['failure_probability']:.2%}")
    print(f"    Remaining Useful Life: {results['prediction']['remaining_useful_life']:.0f} hours")
    print(f"    Risk Level: {results['prediction']['risk_level'].upper()}")
    
    print(f"\n  Optimization Recommendations: {len(results['optimization'])}")
    for rec in results['optimization'][:3]:
        print(f"    - {rec['parameter_name']}: {rec['current_value']:.2f} → {rec['recommended_value']:.2f}")
    
    print(f"\n  Anomalies Detected: {len(results['anomalies'])}")
    for anom in results['anomalies']:
        print(f"    - {anom['parameter_name']}: {anom['severity'].upper()}")
    
    json_report = engine.export_report(results, format='json')
    print(f"\n  Report exported ({len(json_report)} characters)")
    
    return results


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PETROFLOW REAL-TIME ANALYSIS ENGINE - COMPREHENSIVE TEST")
    print("="*80)
    
    try:
        test_performance_analyzer()
        test_predictive_analyzer()
        test_optimization_engine()
        test_scenario_simulator()
        test_trend_analyzer()
        test_anomaly_detector()
        test_realtime_analysis_engine()
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)
        
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())