"""
Test script for Analytics Dashboard Integration
Tests the real-time analysis engine integration with visual simulation
"""

import sys
import os
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.realtime_analysis_engine import RealtimeAnalysisEngine
from core.visual_simulation_integration import (
    initialize_simulation_state,
    analyze_equipment_realtime
)

def test_analytics_engine_initialization():
    """Test analytics engine initialization"""
    print("Testing Analytics Engine Initialization...")
    
    try:
        # Initialize engines for each equipment type
        pump_engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        turbine_engine = RealtimeAnalysisEngine('TURBINE-001', 'turbine', 50.0)
        compressor_engine = RealtimeAnalysisEngine('COMPRESSOR-001', 'compressor', 2000.0)
        
        print("✓ All analytics engines initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Error initializing engines: {e}")
        return False


def test_performance_analysis():
    """Test performance analysis functionality"""
    print("\nTesting Performance Analysis...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        # Test state
        current_state = {
            'flow_rate': 150.0,
            'inlet_pressure': 2.0,
            'outlet_pressure': 8.5,
            'rpm': 1800,
            'temperature': 35.0,
            'efficiency': 0.82,
            'power': 75.0,
            'operating_hours': 15000.0,
            'vibration': 4.5,
            'head': 50.0
        }
        
        # Perform analysis
        results = engine.analyze_realtime(current_state)
        
        # Validate results
        assert 'performance' in results, "Missing performance metrics"
        assert 'prediction' in results, "Missing prediction results"
        assert 'optimization' in results, "Missing optimization recommendations"
        assert 'anomalies' in results, "Missing anomaly detection"
        
        perf = results['performance']
        assert 'efficiency' in perf, "Missing efficiency metric"
        assert 'performance_index' in perf, "Missing performance index"
        assert 'power_consumption' in perf, "Missing power consumption"
        
        print("✓ Performance analysis completed successfully")
        print(f"  - Efficiency: {perf['efficiency']*100:.1f}%")
        print(f"  - Performance Index: {perf['performance_index']:.1f}/100")
        print(f"  - Power Consumption: {perf['power_consumption']:.1f} kW")
        
        return True
    except Exception as e:
        print(f"✗ Error in performance analysis: {e}")
        return False


def test_predictive_analysis():
    """Test predictive analytics functionality"""
    print("\nTesting Predictive Analytics...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        current_state = {
            'flow_rate': 150.0,
            'power': 75.0,
            'efficiency': 0.82,
            'operating_hours': 15000.0,
            'vibration': 4.5,
            'temperature': 35.0
        }
        
        results = engine.analyze_realtime(current_state)
        pred = results['prediction']
        
        assert 'failure_probability' in pred, "Missing failure probability"
        assert 'remaining_useful_life' in pred, "Missing RUL"
        assert 'risk_level' in pred, "Missing risk level"
        assert 'maintenance_recommendation' in pred, "Missing maintenance recommendation"
        
        print("✓ Predictive analysis completed successfully")
        print(f"  - Failure Probability: {pred['failure_probability']*100:.1f}%")
        print(f"  - RUL: {pred['remaining_useful_life']:.0f} hours")
        print(f"  - Risk Level: {pred['risk_level']}")
        
        return True
    except Exception as e:
        print(f"✗ Error in predictive analysis: {e}")
        return False


def test_optimization_recommendations():
    """Test optimization recommendations"""
    print("\nTesting Optimization Recommendations...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        current_state = {
            'flow_rate': 150.0,
            'power': 75.0,
            'efficiency': 0.82,
            'operating_hours': 15000.0,
            'vibration': 4.5,
            'temperature': 35.0
        }
        
        results = engine.analyze_realtime(current_state)
        recommendations = results['optimization']
        
        assert isinstance(recommendations, list), "Recommendations should be a list"
        
        if recommendations:
            rec = recommendations[0]
            assert 'parameter_name' in rec, "Missing parameter name"
            assert 'current_value' in rec, "Missing current value"
            assert 'recommended_value' in rec, "Missing recommended value"
            assert 'expected_improvement' in rec, "Missing expected improvement"
            
            print(f"✓ Generated {len(recommendations)} optimization recommendations")
            print(f"  - Top recommendation: {rec['parameter_name']}")
            print(f"    Current: {rec['current_value']:.2f}")
            print(f"    Recommended: {rec['recommended_value']:.2f}")
            print(f"    Expected improvement: {rec['expected_improvement']*100:.1f}%")
        else:
            print("✓ No optimization recommendations (equipment operating optimally)")
        
        return True
    except Exception as e:
        print(f"✗ Error in optimization: {e}")
        return False


def test_anomaly_detection():
    """Test anomaly detection"""
    print("\nTesting Anomaly Detection...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        # Normal state
        normal_state = {
            'flow_rate': 150.0,
            'power': 75.0,
            'efficiency': 0.82,
            'temperature': 35.0,
            'vibration': 4.5
        }
        
        results = engine.analyze_realtime(normal_state)
        anomalies = results['anomalies']
        
        assert isinstance(anomalies, list), "Anomalies should be a list"
        
        print(f"✓ Anomaly detection completed")
        print(f"  - Detected {len(anomalies)} anomalies")
        
        if anomalies:
            for anom in anomalies:
                print(f"    - {anom['parameter_name']}: {anom['severity']} severity")
        
        return True
    except Exception as e:
        print(f"✗ Error in anomaly detection: {e}")
        return False


def test_trend_analysis():
    """Test trend analysis with historical data"""
    print("\nTesting Trend Analysis...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        # Generate historical data
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(100, 0, -1)]
        historical_data = pd.DataFrame({
            'timestamp': timestamps,
            'efficiency': [0.80 + i*0.0002 for i in range(100)],
            'power': [70.0 + i*0.05 for i in range(100)],
            'vibration': [3.0 + i*0.01 for i in range(100)]
        })
        
        current_state = {
            'flow_rate': 150.0,
            'power': 75.0,
            'efficiency': 0.82,
            'operating_hours': 15000.0,
            'vibration': 4.5,
            'temperature': 35.0
        }
        
        results = engine.analyze_realtime(current_state, historical_data)
        
        print("✓ Trend analysis completed with historical data")
        print(f"  - Historical data points: {len(historical_data)}")
        
        return True
    except Exception as e:
        print(f"✗ Error in trend analysis: {e}")
        return False


def test_scenario_comparison():
    """Test scenario comparison functionality"""
    print("\nTesting Scenario Comparison...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        # Scenario 1: Current operation
        scenario1 = {
            'flow_rate': 150.0,
            'power': 75.0,
            'efficiency': 0.82,
            'operating_hours': 15000.0,
            'vibration': 4.5,
            'temperature': 35.0
        }
        
        # Scenario 2: Optimized operation
        scenario2 = {
            'flow_rate': 140.0,
            'power': 70.0,
            'efficiency': 0.85,
            'operating_hours': 15000.0,
            'vibration': 4.0,
            'temperature': 33.0
        }
        
        results1 = engine.analyze_realtime(scenario1)
        results2 = engine.analyze_realtime(scenario2)
        
        perf1 = results1['performance']
        perf2 = results2['performance']
        
        print("✓ Scenario comparison completed")
        print(f"  Scenario 1 Performance Index: {perf1['performance_index']:.1f}")
        print(f"  Scenario 2 Performance Index: {perf2['performance_index']:.1f}")
        print(f"  Improvement: {perf2['performance_index'] - perf1['performance_index']:.1f} points")
        
        return True
    except Exception as e:
        print(f"✗ Error in scenario comparison: {e}")
        return False


def test_export_functionality():
    """Test export capabilities"""
    print("\nTesting Export Functionality...")
    
    try:
        engine = RealtimeAnalysisEngine('PUMP-001', 'pump', 100.0)
        
        current_state = {
            'flow_rate': 150.0,
            'power': 75.0,
            'efficiency': 0.82,
            'operating_hours': 15000.0,
            'vibration': 4.5,
            'temperature': 35.0
        }
        
        results = engine.analyze_realtime(current_state)
        
        # Test JSON export
        json_export = engine.export_report(results, format='json')
        assert json_export, "JSON export failed"
        assert len(json_export) > 0, "JSON export is empty"
        
        # Test CSV export
        csv_export = engine.export_report(results, format='csv')
        assert csv_export, "CSV export failed"
        assert len(csv_export) > 0, "CSV export is empty"
        
        print("✓ Export functionality working")
        print(f"  - JSON export: {len(json_export)} characters")
        print(f"  - CSV export: {len(csv_export)} characters")
        
        return True
    except Exception as e:
        print(f"✗ Error in export: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("="*60)
    print("Analytics Dashboard Integration Test Suite")
    print("="*60)
    
    tests = [
        test_analytics_engine_initialization,
        test_performance_analysis,
        test_predictive_analysis,
        test_optimization_recommendations,
        test_anomaly_detection,
        test_trend_analysis,
        test_scenario_comparison,
        test_export_functionality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n✓ All tests passed! Analytics integration is working correctly.")
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)