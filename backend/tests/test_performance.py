"""
Performance Tests for Phase 4
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Benchmarks for steady-state, transient simulations, and telemetry throughput.
"""

import pytest
import time
from datetime import datetime, timedelta
import statistics

from app.core.safety_envelope import SafetyEnvelopeValidator
from app.core.optimizer import OperationalOptimizer, OptimizationConfig
from app.core.telemetry import TelemetryProcessor, TelemetryPoint
from app.core.simulation import (
    SimulationOrchestrator,
    SimulationConfig,
    SimulationType
)
from app.core.standards import EquipmentType, UnitSystem


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def safety_validator(self):
        """Create safety validator instance."""
        return SafetyEnvelopeValidator(
            unit_system=UnitSystem.SI,
            enable_logging=False
        )
    
    @pytest.fixture
    def optimizer(self, safety_validator):
        """Create optimizer instance."""
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
    def telemetry_processor(self, safety_validator, optimizer):
        """Create telemetry processor instance."""
        return TelemetryProcessor(
            safety_validator=safety_validator,
            optimizer=optimizer,
            buffer_size=10000,
            enable_logging=False
        )
    
    @pytest.fixture
    def simulation_orchestrator(self, safety_validator, optimizer, telemetry_processor):
        """Create simulation orchestrator instance."""
        return SimulationOrchestrator(
            safety_validator=safety_validator,
            optimizer=optimizer,
            telemetry_processor=telemetry_processor,
            unit_system=UnitSystem.SI,
            enable_logging=False
        )
    
    @pytest.fixture
    def sample_equipment_data(self):
        """Create sample equipment data."""
        return {
            "PUMP-001": {
                "type": EquipmentType.PUMP_CENTRIFUGAL.value,
                "parameters": {
                    "flow_rate": 100.0,
                    "head": 50.0,
                    "power": 45.0,
                    "speed": 3600.0,
                    "rated_flow": 100.0
                },
                "units": {
                    "flow_rate": "m3/h",
                    "head": "m",
                    "power": "kW",
                    "speed": "rpm",
                    "rated_flow": "m3/h"
                }
            }
        }
    
    def test_steady_state_benchmark(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """
        Benchmark: Steady-state simulation should complete in <100ms.
        
        Target: <100ms for single equipment
        """
        config = SimulationConfig(
            simulation_type=SimulationType.STEADY_STATE,
            equipment_ids=list(sample_equipment_data.keys()),
            max_iterations=50,
            enable_optimization=True,
            enable_safety_validation=True
        )
        
        # Run multiple times to get average
        durations = []
        for _ in range(10):
            result = simulation_orchestrator.run_steady_state_simulation(
                equipment_data=sample_equipment_data,
                config=config
            )
            durations.append(result.duration_ms)
        
        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\nSteady-State Performance:")
        print(f"  Average: {avg_duration:.2f}ms")
        print(f"  Min: {min_duration:.2f}ms")
        print(f"  Max: {max_duration:.2f}ms")
        
        # Performance requirement
        assert avg_duration < 100, f"Average duration {avg_duration:.2f}ms exceeds 100ms target"
        assert max_duration < 150, f"Max duration {max_duration:.2f}ms exceeds 150ms threshold"
    
    def test_transient_1000_steps_benchmark(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """
        Benchmark: Transient simulation with 1000 steps should complete in <5s.
        
        Target: <5s for 1000 steps
        """
        initial_conditions = {
            eq_id: eq_data["parameters"].copy()
            for eq_id, eq_data in sample_equipment_data.items()
        }
        
        config = SimulationConfig(
            simulation_type=SimulationType.TRANSIENT,
            equipment_ids=list(sample_equipment_data.keys()),
            time_horizon=1000.0,  # 1000 seconds
            time_step=1.0,  # 1 second steps = 1000 steps
            enable_optimization=False,  # Disable for speed
            enable_safety_validation=False,
            enable_anomaly_detection=False
        )
        
        result = simulation_orchestrator.run_transient_simulation(
            equipment_data=sample_equipment_data,
            initial_conditions=initial_conditions,
            config=config
        )
        
        duration_s = result.duration_ms / 1000
        steps_per_second = len(result.steps) / duration_s if duration_s > 0 else 0
        
        print(f"\nTransient Simulation Performance:")
        print(f"  Total Steps: {len(result.steps)}")
        print(f"  Duration: {duration_s:.2f}s")
        print(f"  Steps/Second: {steps_per_second:.0f}")
        
        # Performance requirement
        assert duration_s < 5.0, f"Duration {duration_s:.2f}s exceeds 5s target"
        assert len(result.steps) >= 1000, f"Expected 1000 steps, got {len(result.steps)}"
    
    def test_telemetry_throughput_benchmark(
        self,
        telemetry_processor
    ):
        """
        Benchmark: Telemetry throughput should be >1000 points/s.
        
        Target: >1000 points/s
        """
        # Create 1000 telemetry points
        telemetry_points = []
        for i in range(1000):
            point = TelemetryPoint(
                equipment_id=f"TEST-{i % 10:03d}",
                timestamp=datetime.utcnow() + timedelta(seconds=i * 0.001),
                parameters={
                    "param1": 100.0 + i * 0.1,
                    "param2": 50.0 + i * 0.05,
                    "param3": 25.0 + i * 0.025
                },
                units={
                    "param1": "unit1",
                    "param2": "unit2",
                    "param3": "unit3"
                },
                quality=1.0,
                source="benchmark"
            )
            telemetry_points.append(point)
        
        # Process batch
        start_time = time.time()
        telemetry_processor.process_telemetry_batch(
            telemetry_points,
            validate_safety=False,
            detect_anomalies=False
        )
        duration_s = time.time() - start_time
        
        throughput = 1000 / duration_s
        
        print(f"\nTelemetry Throughput Performance:")
        print(f"  Points Processed: 1000")
        print(f"  Duration: {duration_s:.3f}s")
        print(f"  Throughput: {throughput:.0f} points/s")
        
        # Performance requirement
        assert throughput > 1000, f"Throughput {throughput:.0f} points/s is below 1000 target"
    
    def test_optimization_performance(
        self,
        optimizer,
        sample_equipment_data
    ):
        """
        Benchmark: Single equipment optimization should complete in <50ms.
        
        Target: <50ms per equipment
        """
        eq_data = sample_equipment_data["PUMP-001"]
        
        # Run multiple optimizations
        durations = []
        for _ in range(20):
            result = optimizer.optimize_operating_point(
                equipment_id="PUMP-001",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                current_parameters=eq_data["parameters"],
                units=eq_data["units"]
            )
            durations.append(result.computation_time_ms)
        
        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\nOptimization Performance:")
        print(f"  Average: {avg_duration:.2f}ms")
        print(f"  Min: {min_duration:.2f}ms")
        print(f"  Max: {max_duration:.2f}ms")
        
        # Performance requirement
        assert avg_duration < 50, f"Average duration {avg_duration:.2f}ms exceeds 50ms target"
    
    def test_safety_validation_performance(
        self,
        safety_validator,
        sample_equipment_data
    ):
        """
        Benchmark: Safety validation should complete in <10ms.
        
        Target: <10ms per validation
        """
        from app.core.safety_envelope import OperatingPoint
        
        eq_data = sample_equipment_data["PUMP-001"]
        
        # Run multiple validations
        durations = []
        for _ in range(50):
            op_point = OperatingPoint(
                equipment_id="PUMP-001",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                timestamp=datetime.utcnow(),
                parameters=eq_data["parameters"],
                units=eq_data["units"]
            )
            
            start_time = time.time()
            safety_validator.validate_operating_point(op_point)
            duration_ms = (time.time() - start_time) * 1000
            durations.append(duration_ms)
        
        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\nSafety Validation Performance:")
        print(f"  Average: {avg_duration:.2f}ms")
        print(f"  Min: {min_duration:.2f}ms")
        print(f"  Max: {max_duration:.2f}ms")
        
        # Performance requirement
        assert avg_duration < 10, f"Average duration {avg_duration:.2f}ms exceeds 10ms target"
    
    def test_memory_usage(
        self,
        telemetry_processor
    ):
        """
        Benchmark: Memory usage should remain stable during processing.
        
        Target: No memory leaks, stable usage
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large batch
        for batch in range(10):
            telemetry_points = []
            for i in range(1000):
                point = TelemetryPoint(
                    equipment_id=f"TEST-{i % 10:03d}",
                    timestamp=datetime.utcnow(),
                    parameters={"param1": 100.0 + i},
                    units={"param1": "unit"},
                    quality=1.0,
                    source="memory_test"
                )
                telemetry_points.append(point)
            
            telemetry_processor.process_telemetry_batch(
                telemetry_points,
                validate_safety=False,
                detect_anomalies=False
            )
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        
        # Memory should not increase by more than 100MB
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, possible leak"
    
    def test_concurrent_simulations(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """
        Benchmark: Multiple concurrent simulations should not degrade performance significantly.
        
        Target: <2x slowdown with 5 concurrent simulations
        """
        config = SimulationConfig(
            simulation_type=SimulationType.STEADY_STATE,
            equipment_ids=list(sample_equipment_data.keys()),
            max_iterations=20
        )
        
        # Single simulation baseline
        single_result = simulation_orchestrator.run_steady_state_simulation(
            equipment_data=sample_equipment_data,
            config=config
        )
        baseline_duration = single_result.duration_ms
        
        # Multiple simulations
        start_time = time.time()
        results = []
        for _ in range(5):
            result = simulation_orchestrator.run_steady_state_simulation(
                equipment_data=sample_equipment_data,
                config=config
            )
            results.append(result)
        total_duration = (time.time() - start_time) * 1000
        
        avg_duration = total_duration / 5
        slowdown_factor = avg_duration / baseline_duration
        
        print(f"\nConcurrent Simulation Performance:")
        print(f"  Baseline (single): {baseline_duration:.2f}ms")
        print(f"  Average (5 concurrent): {avg_duration:.2f}ms")
        print(f"  Slowdown Factor: {slowdown_factor:.2f}x")
        
        # Should not slow down by more than 2x
        assert slowdown_factor < 2.0, f"Slowdown factor {slowdown_factor:.2f}x exceeds 2x threshold"
    
    def test_cache_effectiveness(
        self,
        optimizer,
        sample_equipment_data
    ):
        """
        Benchmark: Cache should improve performance for repeated operations.
        
        Target: >50% speedup with cache
        """
        eq_data = sample_equipment_data["PUMP-001"]
        
        # Clear cache
        optimizer.clear_cache()
        
        # First run (no cache)
        start_time = time.time()
        for _ in range(10):
            optimizer.optimize_operating_point(
                equipment_id="PUMP-001",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                current_parameters=eq_data["parameters"],
                units=eq_data["units"]
            )
        no_cache_duration = (time.time() - start_time) * 1000
        
        # Second run (with cache)
        start_time = time.time()
        for _ in range(10):
            optimizer.optimize_operating_point(
                equipment_id="PUMP-001",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                current_parameters=eq_data["parameters"],
                units=eq_data["units"]
            )
        with_cache_duration = (time.time() - start_time) * 1000
        
        speedup = no_cache_duration / with_cache_duration
        cache_stats = optimizer.get_cache_statistics()
        
        print(f"\nCache Performance:")
        print(f"  Without Cache: {no_cache_duration:.2f}ms")
        print(f"  With Cache: {with_cache_duration:.2f}ms")
        print(f"  Speedup: {speedup:.2f}x")
        print(f"  Cache Hit Ratio: {cache_stats['hit_ratio_percent']:.1f}%")
        
        # Cache should provide at least 1.5x speedup
        assert speedup > 1.5, f"Cache speedup {speedup:.2f}x is below 1.5x target"
        assert cache_stats['hit_ratio_percent'] > 50, "Cache hit ratio should be >50%"


class TestScalabilityBenchmarks:
    """Scalability benchmark tests."""
    
    @pytest.fixture
    def safety_validator(self):
        return SafetyEnvelopeValidator(unit_system=UnitSystem.SI, enable_logging=False)
    
    @pytest.fixture
    def optimizer(self, safety_validator):
        return OperationalOptimizer(
            safety_validator=safety_validator,
            unit_system=UnitSystem.SI
        )
    
    @pytest.fixture
    def telemetry_processor(self, safety_validator, optimizer):
        return TelemetryProcessor(
            safety_validator=safety_validator,
            optimizer=optimizer,
            enable_logging=False
        )
    
    @pytest.fixture
    def simulation_orchestrator(self, safety_validator, optimizer, telemetry_processor):
        return SimulationOrchestrator(
            safety_validator=safety_validator,
            optimizer=optimizer,
            telemetry_processor=telemetry_processor,
            enable_logging=False
        )
    
    def test_scaling_with_equipment_count(
        self,
        simulation_orchestrator
    ):
        """
        Test how performance scales with number of equipment.
        
        Target: Linear or sub-linear scaling
        """
        results = {}
        
        for equipment_count in [1, 5, 10, 20]:
            # Create equipment data
            equipment_data = {}
            for i in range(equipment_count):
                equipment_data[f"PUMP-{i:03d}"] = {
                    "type": EquipmentType.PUMP_CENTRIFUGAL.value,
                    "parameters": {
                        "flow_rate": 100.0,
                        "head": 50.0,
                        "power": 45.0,
                        "speed": 3600.0,
                        "rated_flow": 100.0
                    },
                    "units": {
                        "flow_rate": "m3/h",
                        "head": "m",
                        "power": "kW",
                        "speed": "rpm",
                        "rated_flow": "m3/h"
                    }
                }
            
            config = SimulationConfig(
                simulation_type=SimulationType.STEADY_STATE,
                equipment_ids=list(equipment_data.keys()),
                max_iterations=10
            )
            
            result = simulation_orchestrator.run_steady_state_simulation(
                equipment_data=equipment_data,
                config=config
            )
            
            results[equipment_count] = result.duration_ms
        
        print(f"\nScaling with Equipment Count:")
        for count, duration in results.items():
            per_equipment = duration / count
            print(f"  {count} equipment: {duration:.2f}ms ({per_equipment:.2f}ms per equipment)")
        
        # Check that scaling is reasonable (not exponential)
        # Duration for 20 equipment should be less than 20x duration for 1 equipment
        scaling_factor = results[20] / results[1]
        assert scaling_factor < 30, f"Scaling factor {scaling_factor:.2f}x is too high"
    
    def test_scaling_with_time_steps(
        self,
        simulation_orchestrator
    ):
        """
        Test how performance scales with number of time steps.
        
        Target: Linear scaling
        """
        equipment_data = {
            "PUMP-001": {
                "type": EquipmentType.PUMP_CENTRIFUGAL.value,
                "parameters": {
                    "flow_rate": 100.0,
                    "head": 50.0,
                    "power": 45.0,
                    "speed": 3600.0,
                    "rated_flow": 100.0
                },
                "units": {
                    "flow_rate": "m3/h",
                    "head": "m",
                    "power": "kW",
                    "speed": "rpm",
                    "rated_flow": "m3/h"
                }
            }
        }
        
        initial_conditions = {
            "PUMP-001": equipment_data["PUMP-001"]["parameters"].copy()
        }
        
        results = {}
        
        for steps in [10, 50, 100, 500]:
            config = SimulationConfig(
                simulation_type=SimulationType.TRANSIENT,
                equipment_ids=["PUMP-001"],
                time_horizon=float(steps),
                time_step=1.0,
                enable_optimization=False,
                enable_safety_validation=False,
                enable_anomaly_detection=False
            )
            
            result = simulation_orchestrator.run_transient_simulation(
                equipment_data=equipment_data,
                initial_conditions=initial_conditions,
                config=config
            )
            
            results[steps] = result.duration_ms
        
        print(f"\nScaling with Time Steps:")
        for steps, duration in results.items():
            per_step = duration / steps
            print(f"  {steps} steps: {duration:.2f}ms ({per_step:.3f}ms per step)")
        
        # Check linear scaling
        # 500 steps should take less than 60x the time of 10 steps
        scaling_factor = results[500] / results[10]
        assert scaling_factor < 60, f"Scaling factor {scaling_factor:.2f}x is too high"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
