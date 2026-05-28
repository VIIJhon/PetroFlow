#!/usr/bin/env python
"""Quick verification script for all PetroFlow core modules."""

import sys
import traceback

print("=" * 70)
print("PetroFlow Module Import Verification")
print("=" * 70)

try:
    print("\n[1/3] Importing statistics_engine...")
    from app.core.statistics_engine import (
        fit_weibull_distribution,
        generate_kaplan_meier_data,
        jackknife_resampling,
        calculate_mtbf,
    )
    print("      ✓ Statistics engine imported successfully")
except Exception as e:
    print(f"      ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[2/3] Importing equipment_classification...")
    from app.core.equipment_classification import (
        get_valid_subtypes,
        get_required_parameters,
        is_valid_subtype,
        get_api_standard,
    )
    print("      ✓ Equipment classification imported successfully")
except Exception as e:
    print(f"      ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[3/3] Importing valve_engine...")
    from app.core.valve_engine import (
        GateValveCalculator,
        BallValveCalculator,
        ReliefValveCalculator,
        CheckValveCalculator,
        assess_valve_condition,
    )
    print("      ✓ Valve engine imported successfully")
except Exception as e:
    print(f"      ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("[SUCCESS] All core modules imported successfully!")
print("=" * 70)

# Quick functional test
print("\n[FUNCTIONAL TEST]")
try:
    print("  - Testing Weibull fitting...")
    import numpy as np
    failure_times = np.array([100, 200, 300, 400, 500])
    result = fit_weibull_distribution(failure_times)
    print(f"    ✓ Weibull shape: {result.shape:.4f}, scale: {result.scale:.4f}")
    
    print("  - Testing equipment classification...")
    subtypes = get_valid_subtypes("pump")
    print(f"    ✓ Found {len(subtypes)} pump subtypes")
    
    print("  - Testing valve calculator instantiation...")
    calc = GateValveCalculator()
    print(f"    ✓ GateValveCalculator instantiated: {type(calc).__name__}")
    
except Exception as e:
    print(f"    ✗ Error during functional test: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[ALL TESTS PASSED]")
print("=" * 70)
