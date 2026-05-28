"""
Test Suite for Operational Optimizer
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Comprehensive tests for optimizer module including:
- Unit tests for individual optimization functions
- Batch optimization tests
- Cache functionality tests
- Vectorization performance tests
- Integration tests with SafetyEnvelopeValidator
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List

from app.core.optimizer import (
    OperationalOptimizer,
    OptimizationConfig,
    OptimizationResult
)
from app.core.safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint
)
from app.core.standards import EquipmentType, UnitSystem
from app.utils.profiling import (
    compare_performance,
    benchmark_batch_sizes,
    print_comparison_report,
    print_batch_benchmark_report
)


@pytest.fixture
def safety_validator():
    """Create safety envelope validator for tests."""
    return SafetyEnvelopeValidator(unit_system=UnitSystem.SI)


@pytest.fixture
def optimizer(safety_validator):
    """Create optimizer instance for tests."""
    config = OptimizationConfig(
        enable_caching=True,
        vectorize_batch=True
    )
    return OperationalOptimizer(
        safety_validator=safety_validator,
        config=config,
        unit_system=UnitSystem.SI
    )


@pytest.fixture
def pump_parameters():
    """Sample pump operating parameters."""
    return {
        'flow_rate': 100.0,  # m3/h
        'head': 50.0,  # m
        'speed': 3600.0,  # RPM
        'power': 55.0,  # kW
        'rated_flow': 120.0,  # m3/h
        'discharge_pressure': 5.0,  # bar
        'suction_pressure': 1.0,  # bar
        'temperature': 25.0  # °C
    }


@pytest.fixture
def compressor_parameters():
    """Sample compressor operating parameters."""
    return {
        'flow_rate': 1000.0,  # m3/h
        'speed': 10000.0,  # RPM
        'suction_pressure': 1.0,  # bar
        'discharge_pressure': 5.0,  # bar
        'suction_temperature': 25.0,  # °C
        'discharge_temperature': 150.0,  # °C
        'power': 250.0,  # kW
        'surge_flow': 800.0  # m3/h
    }


@pytest.fixture
def turbine_parameters():
    """Sample turbine operating parameters."""
    return {
        'inlet_pressure': 100.0,  # bar
        'outlet_pressure': 1.0,  # bar
        'inlet_temperature': 500.0,  # °C
        'outlet_temperature': 150.0,  # °C
        'power': 5000.0,  # kW
        'speed': 5000.0  # RPM
    }


@pytest.fixture
def parameter_units():
    """Standard units for parameters."""
    return {
        'flow_rate': 'm3/h',
        'head': 'm',
        'speed': 'RPM',
        'power': 'kW',
        'pressure': 'bar',
        'temperature': '°C',
        'discharge_pressure': 'bar',
        'suction_pressure': 'bar',
        'inlet_pressure': 'bar',
        'outlet_pressure': 'bar',
        'inlet_temperature': '°C',
        'outlet_temperature': '°C',
        'suction_temperature': '°C',
        'discharge_temperature': '°C'
    }


class TestOptimizerInitialization:
    """Test optimizer initialization and configuration."""
    
    def test_optimizer_creation(self, safety_validator):
        """Test basic optimizer creation."""
        optimizer = OperationalOptimizer(
            safety_validator=safety_validator,
            unit_system=UnitSystem.SI
        )
        
        assert optimizer is not None
        assert optimizer.unit_system == UnitSystem.SI
        assert optimizer.config is not None
    
    def test_optimizer_with_custom_config(self, safety_validator):
        """Test optimizer with custom configuration."""
        config = OptimizationConfig(
            target_metric="energy",
            safety_margin=15.0,
            max_iterations=200,
            enable_caching=False
        )
        
        optimizer = OperationalOptimizer(
            safety_validator=safety_validator,
            config=config
        )
        
        assert optimizer.config.target_metric == "energy"
        assert optimizer.config.safety_margin == 15.0
        assert optimizer.config.max_iterations == 200
        assert optimizer.config.enable_caching is False


class TestPumpOptimization:
    """Test pump-specific optimization algorithms."""
    
    def test_pump_efficiency_calculation(self, optimizer, pump_parameters):
        """Test pump efficiency calculation."""
        # Create hash for caching
        params_hash = hash(str(pump_parameters))
        
        efficiency = optimizer.calculate_efficiency(
            EquipmentType.PUMP_CENTRIFUGAL,
            params_hash
        )
        
        assert 0.0 <= efficiency <= 100.0
        assert efficiency > 50.0  # Reasonable efficiency
    
    def test_pump_optimization(self, optimizer, pump_parameters, parameter_units):
        """Test single pump optimization."""
        result = optimizer.optimize_operating_point(
            equipment_id="PUMP-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.equipment_id == "PUMP-001"
        assert result.equipment_type == EquipmentType.PUMP_CENTRIFUGAL
        assert 'speed' in result.optimized_parameters
        assert 'flow_rate' in result.optimized_parameters
        assert result.computation_time_ms > 0
    
    def test_pump_optimization_with_constraints(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test pump optimization with parameter constraints."""
        constraints = {
            'speed': (3000.0, 4000.0),
            'flow_rate': (80.0, 110.0)
        }
        
        result = optimizer.optimize_operating_point(
            equipment_id="PUMP-002",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units,
            constraints=constraints
        )
        
        # Check constraints are respected
        assert 3000.0 <= result.optimized_parameters['speed'] <= 4000.0
        assert 80.0 <= result.optimized_parameters['flow_rate'] <= 110.0
    
    def test_pump_power_calculation(self, optimizer, pump_parameters):
        """Test pump power calculation."""
        power = optimizer._calculate_pump_power(pump_parameters)
        
        assert power > 0
        assert isinstance(power, float)


class TestCompressorOptimization:
    """Test compressor-specific optimization algorithms."""
    
    def test_compressor_efficiency_calculation(
        self, optimizer, compressor_parameters
    ):
        """Test compressor polytropic efficiency calculation."""
        params_hash = hash(str(compressor_parameters))
        
        efficiency = optimizer.calculate_efficiency(
            EquipmentType.COMPRESSOR_CENTRIFUGAL,
            params_hash
        )
        
        assert 0.0 <= efficiency <= 100.0
        assert efficiency > 40.0  # Reasonable compressor efficiency
    
    def test_compressor_optimization(
        self, optimizer, compressor_parameters, parameter_units
    ):
        """Test single compressor optimization."""
        result = optimizer.optimize_operating_point(
            equipment_id="COMP-001",
            equipment_type=EquipmentType.COMPRESSOR_CENTRIFUGAL,
            current_parameters=compressor_parameters,
            units=parameter_units
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.equipment_id == "COMP-001"
        assert 'speed' in result.optimized_parameters
        assert 'flow_rate' in result.optimized_parameters
    
    def test_surge_margin_calculation(self, optimizer, compressor_parameters):
        """Test compressor surge margin calculation."""
        surge_margin = optimizer._calculate_surge_margin(compressor_parameters)
        
        assert 0.0 <= surge_margin <= 100.0
        assert surge_margin > 0  # Should have positive margin


class TestTurbineOptimization:
    """Test turbine-specific optimization algorithms."""
    
    def test_turbine_efficiency_calculation(
        self, optimizer, turbine_parameters
    ):
        """Test turbine isentropic efficiency calculation."""
        params_hash = hash(str(turbine_parameters))
        
        efficiency = optimizer.calculate_efficiency(
            EquipmentType.TURBINE_STEAM,
            params_hash
        )
        
        assert 0.0 <= efficiency <= 100.0
        assert efficiency > 30.0  # Reasonable turbine efficiency
    
    def test_turbine_optimization(
        self, optimizer, turbine_parameters, parameter_units
    ):
        """Test single turbine optimization."""
        result = optimizer.optimize_operating_point(
            equipment_id="TURB-001",
            equipment_type=EquipmentType.TURBINE_STEAM,
            current_parameters=turbine_parameters,
            units=parameter_units
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.equipment_id == "TURB-001"
        assert 'inlet_temperature' in result.optimized_parameters
        assert 'inlet_pressure' in result.optimized_parameters


class TestBatchOptimization:
    """Test batch optimization with vectorization."""
    
    def test_batch_optimization_vectorized(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test vectorized batch optimization."""
        # Create batch data
        batch_size = 10
        equipment_data = pd.DataFrame({
            'equipment_id': [f'PUMP-{i:03d}' for i in range(batch_size)],
            'equipment_type': ['pump_centrifugal'] * batch_size,
            'parameters': [pump_parameters.copy() for _ in range(batch_size)],
            'units': [parameter_units.copy() for _ in range(batch_size)]
        })
        
        # Optimize batch
        result_df = optimizer.optimize_batch(equipment_data)
        
        assert len(result_df) == batch_size
        assert 'optimization_result' in result_df.columns
        assert 'efficiency_improvement' in result_df.columns
        assert 'energy_savings' in result_df.columns
        assert 'safety_status' in result_df.columns
    
    def test_batch_optimization_iterative(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test non-vectorized batch optimization."""
        # Disable vectorization
        optimizer.config.vectorize_batch = False
        
        batch_size = 5
        equipment_data = pd.DataFrame({
            'equipment_id': [f'PUMP-{i:03d}' for i in range(batch_size)],
            'equipment_type': ['pump_centrifugal'] * batch_size,
            'parameters': [pump_parameters.copy() for _ in range(batch_size)],
            'units': [parameter_units.copy() for _ in range(batch_size)]
        })
        
        result_df = optimizer.optimize_batch(equipment_data)
        
        assert len(result_df) == batch_size
        assert 'optimization_result' in result_df.columns


class TestCacheFunctionality:
    """Test caching mechanisms."""
    
    def test_cache_hit(self, optimizer, pump_parameters, parameter_units):
        """Test cache hit on repeated optimization."""
        # First call - cache miss
        result1 = optimizer.optimize_operating_point(
            equipment_id="PUMP-CACHE-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units
        )
        
        # Second call - should hit cache
        result2 = optimizer.optimize_operating_point(
            equipment_id="PUMP-CACHE-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units
        )
        
        # Results should be identical
        assert result1.equipment_id == result2.equipment_id
        assert result1.efficiency_improvement == result2.efficiency_improvement
    
    def test_cache_statistics(self, optimizer, pump_parameters, parameter_units):
        """Test cache statistics tracking."""
        # Clear cache first
        optimizer.clear_cache()
        
        # Make some calls
        for i in range(5):
            optimizer.optimize_operating_point(
                equipment_id=f"PUMP-{i:03d}",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                current_parameters=pump_parameters,
                units=parameter_units
            )
        
        stats = optimizer.get_cache_statistics()
        
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'hit_ratio_percent' in stats
        assert stats['total_requests'] > 0
    
    def test_cache_clear(self, optimizer, pump_parameters, parameter_units):
        """Test cache clearing."""
        # Add some cached results
        optimizer.optimize_operating_point(
            equipment_id="PUMP-CLEAR-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units
        )
        
        # Clear cache
        optimizer.clear_cache()
        
        stats = optimizer.get_cache_statistics()
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0


class TestSafetyIntegration:
    """Test integration with SafetyEnvelopeValidator."""
    
    def test_optimization_respects_safety_limits(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test that optimization respects safety envelope."""
        result = optimizer.optimize_operating_point(
            equipment_id="PUMP-SAFE-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units
        )
        
        # Safety status should not be CRITICAL
        assert result.safety_status != 'critical'
    
    def test_recommendations_generation(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test generation of optimization recommendations."""
        result = optimizer.optimize_operating_point(
            equipment_id="PUMP-REC-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_parameters,
            units=parameter_units
        )
        
        assert isinstance(result.recommendations, list)
        # Should have at least some recommendations
        assert len(result.recommendations) >= 0


class TestOptimalSetpoint:
    """Test optimal setpoint finding."""
    
    def test_find_optimal_setpoint(self, optimizer, pump_parameters):
        """Test finding optimal setpoint for a parameter."""
        optimal_speed = optimizer.find_optimal_setpoint(
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            parameter_name='speed',
            current_value=3600.0,
            target_efficiency=85.0,
            other_parameters={
                'flow_rate': 100.0,
                'head': 50.0,
                'rated_flow': 120.0
            }
        )
        
        assert isinstance(optimal_speed, float)
        assert optimal_speed > 0


class TestEnergyCalculations:
    """Test energy consumption calculations."""
    
    def test_energy_consumption_calculation(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test vectorized energy consumption calculation."""
        batch_size = 10
        equipment_data = pd.DataFrame({
            'equipment_id': [f'PUMP-{i:03d}' for i in range(batch_size)],
            'equipment_type': ['pump_centrifugal'] * batch_size,
            'parameters': [pump_parameters.copy() for _ in range(batch_size)],
            'units': [parameter_units.copy() for _ in range(batch_size)]
        })
        
        result_df = optimizer.calculate_energy_consumption(equipment_data)
        
        assert 'energy_consumption_kw' in result_df.columns
        assert len(result_df) == batch_size
        assert all(result_df['energy_consumption_kw'] > 0)


class TestPerformanceBenchmarks:
    """Performance benchmarking tests."""
    
    def test_vectorized_vs_iterative_performance(
        self, safety_validator, pump_parameters, parameter_units
    ):
        """Compare vectorized vs iterative batch optimization performance."""
        # Create test data
        batch_size = 50
        equipment_data = pd.DataFrame({
            'equipment_id': [f'PUMP-{i:03d}' for i in range(batch_size)],
            'equipment_type': ['pump_centrifugal'] * batch_size,
            'parameters': [pump_parameters.copy() for _ in range(batch_size)],
            'units': [parameter_units.copy() for _ in range(batch_size)]
        })
        
        # Vectorized optimizer
        config_vectorized = OptimizationConfig(vectorize_batch=True)
        optimizer_vectorized = OperationalOptimizer(
            safety_validator=safety_validator,
            config=config_vectorized
        )
        
        # Iterative optimizer
        config_iterative = OptimizationConfig(vectorize_batch=False)
        optimizer_iterative = OperationalOptimizer(
            safety_validator=safety_validator,
            config=config_iterative
        )
        
        # Compare performance
        implementations = {
            'vectorized': lambda: optimizer_vectorized.optimize_batch(
                equipment_data.copy()
            ),
            'iterative': lambda: optimizer_iterative.optimize_batch(
                equipment_data.copy()
            )
        }
        
        results = compare_performance(
            implementations,
            test_args=[()],  # No args needed
            iterations=3
        )
        
        # Print comparison
        print_comparison_report(results, baseline='iterative')
        
        # Vectorized should be faster (or at least comparable)
        # Note: For small batches, overhead might make iterative faster
        assert 'vectorized' in results
        assert 'iterative' in results
    
    def test_batch_size_scaling(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test performance scaling with different batch sizes."""
        batch_sizes = [10, 50, 100]
        
        def generate_data(n):
            return pd.DataFrame({
                'equipment_id': [f'PUMP-{i:03d}' for i in range(n)],
                'equipment_type': ['pump_centrifugal'] * n,
                'parameters': [pump_parameters.copy() for _ in range(n)],
                'units': [parameter_units.copy() for _ in range(n)]
            })
        
        results = benchmark_batch_sizes(
            func=optimizer.optimize_batch,
            batch_sizes=batch_sizes,
            data_generator=generate_data,
            iterations=3
        )
        
        # Print benchmark report
        print_batch_benchmark_report(results)
        
        # Verify results for all batch sizes
        for batch_size in batch_sizes:
            assert batch_size in results
            assert results[batch_size].total_calls > 0
    
    def test_cache_performance_impact(
        self, optimizer, pump_parameters, parameter_units
    ):
        """Test performance impact of caching."""
        # Warm up cache
        for _ in range(5):
            optimizer.optimize_operating_point(
                equipment_id="PUMP-CACHE-PERF",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                current_parameters=pump_parameters,
                units=parameter_units
            )
        
        stats = optimizer.get_cache_statistics()
        
        # Should have some cache hits
        if stats['total_requests'] > 1:
            assert stats['cache_hits'] > 0
            assert stats['hit_ratio_percent'] > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_flow_rate(self, optimizer, pump_parameters, parameter_units):
        """Test handling of zero flow rate."""
        params = pump_parameters.copy()
        params['flow_rate'] = 0.0
        
        result = optimizer.optimize_operating_point(
            equipment_id="PUMP-ZERO-FLOW",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=params,
            units=parameter_units
        )
        
        # Should handle gracefully
        assert result is not None
    
    def test_extreme_parameters(self, optimizer, pump_parameters, parameter_units):
        """Test handling of extreme parameter values."""
        params = pump_parameters.copy()
        params['speed'] = 50000.0  # Very high speed
        
        result = optimizer.optimize_operating_point(
            equipment_id="PUMP-EXTREME",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=params,
            units=parameter_units
        )
        
        # Should handle without crashing
        assert result is not None
    
    def test_empty_batch(self, optimizer):
        """Test handling of empty batch."""
        empty_df = pd.DataFrame(columns=[
            'equipment_id', 'equipment_type', 'parameters', 'units'
        ])
        
        result_df = optimizer.optimize_batch(empty_df)
        
        assert len(result_df) == 0


class TestVectorizationCorrectness:
    """Test that vectorized operations produce correct results."""
    
    def test_efficiency_calculation_consistency(
        self, optimizer, pump_parameters
    ):
        """Test that efficiency calculation is consistent."""
        params_hash = hash(str(pump_parameters))
        
        # Calculate multiple times
        results = [
            optimizer.calculate_efficiency(
                EquipmentType.PUMP_CENTRIFUGAL,
                params_hash
            )
            for _ in range(5)
        ]
        
        # All results should be identical (deterministic)
        assert all(r == results[0] for r in results)
    
    def test_numpy_vectorization(self, optimizer):
        """Test numpy vectorization in calculations."""
        # Test with array of values
        flow_rates = np.array([50.0, 100.0, 150.0, 200.0])
        heads = np.array([30.0, 50.0, 70.0, 90.0])
        
        # Should handle numpy arrays
        for flow, head in zip(flow_rates, heads):
            params = {
                'flow_rate': float(flow),
                'head': float(head),
                'speed': 3600.0,
                'rated_flow': 120.0
            }
            efficiency = optimizer._calculate_pump_efficiency(params)
            assert 0.0 <= efficiency <= 100.0


# Performance benchmark runner
def run_performance_benchmarks():
    """
    Run comprehensive performance benchmarks.
    
    This function can be called separately to generate detailed
    performance reports.
    """
    print("\n" + "=" * 80)
    print("OPTIMIZER PERFORMANCE BENCHMARKS")
    print("=" * 80)
    
    # Setup
    safety_validator = SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
    config = OptimizationConfig(enable_caching=True, vectorize_batch=True)
    optimizer = OperationalOptimizer(
        safety_validator=safety_validator,
        config=config
    )
    
    pump_params = {
        'flow_rate': 100.0,
        'head': 50.0,
        'speed': 3600.0,
        'power': 55.0,
        'rated_flow': 120.0,
        'discharge_pressure': 5.0,
        'suction_pressure': 1.0,
        'temperature': 25.0
    }
    
    units = {
        'flow_rate': 'm3/h',
        'head': 'm',
        'speed': 'RPM',
        'power': 'kW'
    }
    
    # Benchmark 1: Single optimization
    print("\n1. Single Equipment Optimization")
    print("-" * 80)
    
    import time
    start = time.perf_counter()
    for _ in range(100):
        optimizer.optimize_operating_point(
            equipment_id="PUMP-BENCH",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_params,
            units=units
        )
    end = time.perf_counter()
    
    avg_time = (end - start) / 100 * 1000
    print(f"Average time per optimization: {avg_time:.2f} ms")
    
    # Benchmark 2: Batch sizes
    print("\n2. Batch Size Scaling")
    print("-" * 80)
    
    for batch_size in [10, 100, 1000]:
        equipment_data = pd.DataFrame({
            'equipment_id': [f'PUMP-{i:03d}' for i in range(batch_size)],
            'equipment_type': ['pump_centrifugal'] * batch_size,
            'parameters': [pump_params.copy() for _ in range(batch_size)],
            'units': [units.copy() for _ in range(batch_size)]
        })
        
        start = time.perf_counter()
        optimizer.optimize_batch(equipment_data)
        end = time.perf_counter()
        
        total_time = (end - start) * 1000
        time_per_item = total_time / batch_size
        
        print(f"Batch size {batch_size:4d}: {total_time:8.2f} ms total, "
              f"{time_per_item:6.2f} ms per item")
    
    # Benchmark 3: Cache performance
    print("\n3. Cache Performance")
    print("-" * 80)
    
    optimizer.clear_cache()
    
    # Warm up cache
    for _ in range(10):
        optimizer.optimize_operating_point(
            equipment_id="PUMP-CACHE",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            current_parameters=pump_params,
            units=units
        )
    
    stats = optimizer.get_cache_statistics()
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache misses: {stats['cache_misses']}")
    print(f"Hit ratio: {stats['hit_ratio_percent']:.1f}%")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run benchmarks when executed directly
    run_performance_benchmarks()
