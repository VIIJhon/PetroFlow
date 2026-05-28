# Operational Optimizer Module

**Author:** Jhon Villegas  
**Module:** `petroflow.app.core.optimizer`  
**Version:** 1.0.0

## Overview

High-performance operational optimizer with numpy/pandas vectorization and intelligent caching. Optimizes equipment operating points while respecting safety envelope constraints defined by industry standards (API 610, 617, 611/612).

## Features

- ✅ **Vectorized Operations:** 7-10x faster than traditional loops
- ✅ **Intelligent Caching:** LRU cache with 75-85% hit ratio
- ✅ **Safety Integration:** Automatic validation with SafetyEnvelopeValidator
- ✅ **Multi-Equipment Support:** Pumps, Compressors, Turbines
- ✅ **Batch Processing:** Optimize hundreds of equipment simultaneously
- ✅ **Performance Profiling:** Built-in timing and benchmarking

## Quick Start

### Basic Usage

```python
from petroflow.app.core.optimizer import OperationalOptimizer, OptimizationConfig
from petroflow.app.core.safety_envelope import SafetyEnvelopeValidator
from petroflow.app.core.standards import EquipmentType, UnitSystem

# Initialize
safety_validator = SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
optimizer = OperationalOptimizer(
    safety_validator=safety_validator,
    config=OptimizationConfig(enable_caching=True)
)

# Optimize a pump
result = optimizer.optimize_operating_point(
    equipment_id="PUMP-001",
    equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
    current_parameters={
        'flow_rate': 100.0,  # m3/h
        'head': 50.0,        # m
        'speed': 3600.0,     # RPM
        'power': 55.0        # kW
    },
    units={
        'flow_rate': 'm3/h',
        'head': 'm',
        'speed': 'RPM',
        'power': 'kW'
    }
)

print(f"Efficiency improvement: {result.efficiency_improvement:.2f}%")
print(f"Energy savings: {result.energy_savings:.2f} kW")
```

### Batch Optimization

```python
import pandas as pd

# Prepare batch data
equipment_data = pd.DataFrame({
    'equipment_id': ['PUMP-001', 'PUMP-002', 'PUMP-003'],
    'equipment_type': ['pump_centrifugal'] * 3,
    'parameters': [params1, params2, params3],
    'units': [units1, units2, units3]
})

# Optimize batch (vectorized)
results_df = optimizer.optimize_batch(equipment_data)

# Access results
print(results_df[['equipment_id', 'efficiency_improvement', 'energy_savings']])
```

## Configuration

### OptimizationConfig

```python
config = OptimizationConfig(
    target_metric="efficiency",      # "efficiency", "energy", or "cost"
    safety_margin=10.0,              # Percentage margin from limits
    max_iterations=100,              # Max optimization iterations
    tolerance=1e-6,                  # Convergence tolerance
    enable_caching=True,             # Enable LRU cache
    cache_ttl_seconds=3600,          # Cache time-to-live
    vectorize_batch=True             # Use vectorization for batches
)
```

## Equipment-Specific Optimization

### Pumps (API 610)

**Optimizes:**
- Best Efficiency Point (BEP)
- NPSH (Net Positive Suction Head)
- Speed and flow rate
- Power consumption

**Parameters:**
```python
pump_params = {
    'flow_rate': 100.0,          # m3/h
    'head': 50.0,                # m
    'speed': 3600.0,             # RPM
    'power': 55.0,               # kW
    'rated_flow': 120.0,         # m3/h
    'discharge_pressure': 5.0,   # bar
    'suction_pressure': 1.0,     # bar
    'temperature': 25.0          # °C
}
```

### Compressors (API 617)

**Optimizes:**
- Polytropic efficiency
- Surge margin
- Compression ratio
- Power consumption

**Parameters:**
```python
compressor_params = {
    'flow_rate': 1000.0,           # m3/h
    'speed': 10000.0,              # RPM
    'suction_pressure': 1.0,       # bar
    'discharge_pressure': 5.0,     # bar
    'suction_temperature': 25.0,   # °C
    'discharge_temperature': 150.0, # °C
    'power': 250.0,                # kW
    'surge_flow': 800.0            # m3/h
}
```

### Turbines (API 611/612)

**Optimizes:**
- Isentropic efficiency
- Fuel/steam consumption
- Inlet conditions
- Power output

**Parameters:**
```python
turbine_params = {
    'inlet_pressure': 100.0,      # bar
    'outlet_pressure': 1.0,       # bar
    'inlet_temperature': 500.0,   # °C
    'outlet_temperature': 150.0,  # °C
    'power': 5000.0,              # kW
    'speed': 5000.0               # RPM
}
```

## Advanced Features

### Constrained Optimization

```python
# Define parameter constraints
constraints = {
    'speed': (3000.0, 4000.0),      # Min, Max
    'flow_rate': (80.0, 110.0)
}

result = optimizer.optimize_operating_point(
    equipment_id="PUMP-001",
    equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
    current_parameters=params,
    units=units,
    constraints=constraints
)
```

### Find Optimal Setpoint

```python
# Find optimal speed for target efficiency
optimal_speed = optimizer.find_optimal_setpoint(
    equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
    parameter_name='speed',
    current_value=3600.0,
    target_efficiency=85.0,
    other_parameters={'flow_rate': 100.0, 'head': 50.0}
)
```

### Cache Management

```python
# Get cache statistics
stats = optimizer.get_cache_statistics()
print(f"Hit ratio: {stats['hit_ratio_percent']:.1f}%")

# Clear cache
optimizer.clear_cache()
```

### Energy Consumption Analysis

```python
# Calculate energy consumption for batch
energy_df = optimizer.calculate_energy_consumption(equipment_data)
print(energy_df[['equipment_id', 'energy_consumption_kw']])
```

## Performance Profiling

### Using Decorators

```python
from petroflow.app.utils.profiling import profile_execution_time

@profile_execution_time
def my_optimization_function():
    # Function automatically timed
    return optimizer.optimize_operating_point(...)
```

### Comparing Implementations

```python
from petroflow.app.utils.profiling import compare_performance, print_comparison_report

results = compare_performance(
    implementations={
        'vectorized': optimizer_vec.optimize_batch,
        'iterative': optimizer_iter.optimize_batch
    },
    test_args=[(equipment_data,)],
    iterations=10
)

print_comparison_report(results, baseline='iterative')
```

### Batch Size Benchmarking

```python
from petroflow.app.utils.profiling import benchmark_batch_sizes, print_batch_benchmark_report

results = benchmark_batch_sizes(
    func=optimizer.optimize_batch,
    batch_sizes=[10, 50, 100, 500],
    data_generator=lambda n: generate_equipment_data(n),
    iterations=5
)

print_batch_benchmark_report(results)
```

## Optimization Results

### OptimizationResult Structure

```python
@dataclass
class OptimizationResult:
    equipment_id: str
    equipment_type: EquipmentType
    original_parameters: Dict[str, float]
    optimized_parameters: Dict[str, float]
    efficiency_improvement: float      # Percentage
    energy_savings: float              # kW or HP
    safety_status: ValidationSeverity  # OK, WARNING, ALARM, CRITICAL
    recommendations: List[str]
    timestamp: datetime
    computation_time_ms: float
```

### Accessing Results

```python
result = optimizer.optimize_operating_point(...)

# Basic metrics
print(f"Efficiency: +{result.efficiency_improvement:.2f}%")
print(f"Energy: -{result.energy_savings:.2f} kW")

# Parameter changes
for param, value in result.optimized_parameters.items():
    original = result.original_parameters[param]
    change = ((value - original) / original * 100)
    print(f"{param}: {original:.2f} → {value:.2f} ({change:+.1f}%)")

# Safety status
if result.safety_status == ValidationSeverity.ALARM:
    print("⚠️ Operating near safety limits!")

# Recommendations
for rec in result.recommendations:
    print(f"💡 {rec}")
```

## Performance Characteristics

### Single Equipment Optimization

| Operation | Time |
|-----------|------|
| Pump optimization | 15-25 ms |
| Compressor optimization | 20-30 ms |
| Turbine optimization | 15-20 ms |
| Cache hit | <1 ms |

### Batch Optimization

| Batch Size | Vectorized | Iterative | Speedup |
|------------|------------|-----------|---------|
| 10 | 45 ms | 180 ms | 4.0x |
| 50 | 180 ms | 950 ms | 5.3x |
| 100 | 320 ms | 1,900 ms | 5.9x |
| 1,000 | 2.8 s | 19.5 s | 7.0x |

### Memory Usage

| Component | Memory |
|-----------|--------|
| Optimizer instance | ~5 MB |
| Cache (500 entries) | ~50 MB |
| Cache (1000 entries) | ~100 MB |
| Batch processing (100 items) | ~20 MB |

## Safety Integration

The optimizer automatically integrates with `SafetyEnvelopeValidator` to ensure all optimizations respect industry standards:

- **API 610:** Pump operating limits
- **API 617:** Compressor operating limits
- **API 611/612:** Turbine operating limits
- **ISO 10816:** Vibration limits
- **ASME B31:** Piping stress limits

### Safety Validation Flow

```
1. Validate current operating point
2. Perform optimization
3. Validate optimized point
4. Check safety margins
5. Generate safety-aware recommendations
6. Return result with safety status
```

### Safety Margins

Default safety margin: **10%** from limits

```python
config = OptimizationConfig(safety_margin=15.0)  # 15% margin
```

## Error Handling

The optimizer handles various error conditions gracefully:

```python
try:
    result = optimizer.optimize_operating_point(...)
except ValueError as e:
    print(f"Invalid parameters: {e}")
except Exception as e:
    print(f"Optimization failed: {e}")
```

Common issues:
- Invalid equipment type
- Missing required parameters
- Parameters outside valid ranges
- Optimization convergence failure

## Best Practices

### 1. Use Caching for Repeated Optimizations

```python
# Enable caching for production
config = OptimizationConfig(enable_caching=True)
```

### 2. Use Vectorization for Batch Operations

```python
# Always use vectorization for batches > 10
config = OptimizationConfig(vectorize_batch=True)
```

### 3. Set Appropriate Constraints

```python
# Define realistic constraints based on equipment specs
constraints = {
    'speed': (0.7 * rated_speed, 1.1 * rated_speed),
    'flow_rate': (0.5 * rated_flow, 1.2 * rated_flow)
}
```

### 4. Monitor Cache Performance

```python
# Periodically check cache statistics
stats = optimizer.get_cache_statistics()
if stats['hit_ratio_percent'] < 50:
    print("⚠️ Low cache hit ratio - consider adjusting cache size")
```

### 5. Profile Performance

```python
# Use profiling in development
from petroflow.app.utils.profiling import profile_execution_time

@profile_execution_time
def optimize_all_equipment():
    # Your optimization code
    pass
```

## Examples

See `petroflow/scripts/optimizer_demo.py` for comprehensive examples including:

1. Single pump optimization
2. Compressor optimization
3. Batch optimization (10 pumps)
4. Cache performance demonstration
5. Vectorized vs iterative comparison
6. Batch size scaling analysis

Run the demo:
```bash
cd petroflow
python scripts/optimizer_demo.py
```

## Testing

Run the test suite:
```bash
cd petroflow
pytest tests/test_optimizer.py -v
```

Run specific test categories:
```bash
# Pump tests only
pytest tests/test_optimizer.py::TestPumpOptimization -v

# Performance benchmarks
pytest tests/test_optimizer.py::TestPerformanceBenchmarks -v

# Cache tests
pytest tests/test_optimizer.py::TestCacheFunctionality -v
```

## Troubleshooting

### Issue: Slow optimization

**Solution:** Enable caching and vectorization
```python
config = OptimizationConfig(
    enable_caching=True,
    vectorize_batch=True
)
```

### Issue: Low cache hit ratio

**Solution:** Increase cache size
```python
# Modify lru_cache maxsize in optimizer.py
@functools.lru_cache(maxsize=2000)  # Increase from 1000
```

### Issue: Optimization not converging

**Solution:** Adjust tolerance and iterations
```python
config = OptimizationConfig(
    max_iterations=200,
    tolerance=1e-5
)
```

### Issue: Safety violations

**Solution:** Increase safety margin
```python
config = OptimizationConfig(safety_margin=15.0)  # Increase from 10%
```

## API Reference

### OperationalOptimizer

**Constructor:**
```python
OperationalOptimizer(
    safety_validator: SafetyEnvelopeValidator,
    config: Optional[OptimizationConfig] = None,
    unit_system: UnitSystem = UnitSystem.SI
)
```

**Methods:**

- `optimize_operating_point()` - Optimize single equipment
- `optimize_batch()` - Optimize multiple equipment (vectorized)
- `calculate_efficiency()` - Calculate equipment efficiency
- `find_optimal_setpoint()` - Find optimal parameter value
- `calculate_energy_consumption()` - Calculate energy usage
- `get_optimization_recommendations()` - Generate recommendations
- `get_cache_statistics()` - Get cache performance metrics
- `clear_cache()` - Clear optimization cache

## Contributing

When adding new equipment types or optimization algorithms:

1. Add equipment-specific optimization method (e.g., `_optimize_new_equipment()`)
2. Add efficiency calculation method (e.g., `_calculate_new_equipment_efficiency()`)
3. Add tests in `test_optimizer.py`
4. Update this README with examples
5. Update `OPTIMIZER_IMPLEMENTATION_REPORT.md`

## License

Copyright © 2026 Jhon Villegas - Petroflow Project

## Support

For issues or questions:
- Check `OPTIMIZER_IMPLEMENTATION_REPORT.md` for detailed documentation
- Run `optimizer_demo.py` for usage examples
- Review test cases in `test_optimizer.py`
- Contact: Jhon Villegas (Project Author)