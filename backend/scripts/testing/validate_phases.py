#!/usr/bin/env python
"""
Phase Validation Script
Verifies all 15 phases are correctly integrated and importable.
"""

import sys
import importlib
from pathlib import Path

# Add workspace to path
workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))

# Expected phases
EXPECTED_PHASES = [
    ("phase1", "Phase1UIIntegration", ["initialize_phase1", "render_well_context_panel"]),
    ("phase2", "Phase2UIIntegration", ["initialize_phase2", "render_solver_selection"]),
    ("phase3", "Phase3UIIntegration", ["initialize_phase3", "render_network_topology_panel"]),
    ("phase4", "Phase4UIIntegration", ["initialize_phase4", "render_multiphase_flow_analysis"]),
    ("phase5", "Phase5UIIntegration", ["initialize_phase5", "render_spectral_analysis"]),
    ("phase6", "Phase6UIIntegration", ["initialize_phase6", "render_thermal_analysis"]),
    ("phase7", "Phase7UIIntegration", ["initialize_phase7", "render_prescriptive_actions"]),
    ("phase8", "Phase8UIIntegration", ["initialize_phase8", "render_operator_feedback"]),
    ("phase9", "Phase9UIIntegration", ["initialize_phase9", "render_external_integration"]),
    ("phase10", "Phase10UIIntegration", ["initialize_phase10", "render_causal_diagnosis"]),
    ("phase11", "Phase11UIIntegration", ["initialize_phase11", "render_operational_optimizer"]),
    ("phase12", "Phase12UIIntegration", ["initialize_phase12", "render_mlops_customization"]),
    ("phase13", "Phase13UIIntegration", ["initialize_phase13", "render_compliance_audit"]),
    ("phase14", "Phase14UIIntegration", ["initialize_phase14", "render_visual_simulation"]),
    ("phase15", "Phase15System", ["render_ui"]),
]

def validate_phases():
    """Validate all phases."""
    results = {
        "total": len(EXPECTED_PHASES),
        "valid": 0,
        "invalid": 0,
        "errors": []
    }
    
    print("\n" + "="*70)
    print("PHASE VALIDATION REPORT")
    print("="*70 + "\n")
    
    for phase_num, (phase_key, class_name, methods) in enumerate(EXPECTED_PHASES, 1):
        module_name = f"core.{phase_key}_integration"
        
        try:
            # Import module
            module = importlib.import_module(module_name)
            
            # Check class exists
            if not hasattr(module, class_name):
                raise AttributeError(f"Class {class_name} not found in module")
            
            cls = getattr(module, class_name)
            
            # Check methods exist
            missing_methods = []
            for method in methods:
                if not hasattr(cls, method):
                    missing_methods.append(method)
            
            if missing_methods:
                raise AttributeError(f"Missing methods: {', '.join(missing_methods)}")
            
            # Success
            status = "✅ PASS"
            results["valid"] += 1
            print(f"{phase_num:2d}. {status} | {phase_key:8s} | {class_name:25s} | {len(methods)} methods")
            
        except Exception as e:
            status = "❌ FAIL"
            results["invalid"] += 1
            error_msg = f"{phase_num}. {phase_key}: {str(e)}"
            results["errors"].append(error_msg)
            print(f"{phase_num:2d}. {status} | {phase_key:8s} | {class_name:25s} | ERROR")
            print(f"    └─ {str(e)}")
    
    # Summary
    print("\n" + "="*70)
    print(f"SUMMARY: {results['valid']}/{results['total']} phases valid")
    print("="*70)
    
    if results["invalid"] > 0:
        print("\n⚠️  ERRORS FOUND:")
        for error in results["errors"]:
            print(f"  • {error}")
        return False
    else:
        print("\n✅ ALL PHASES VALIDATED SUCCESSFULLY!")
        return True

def check_phase_executor():
    """Check phase_executor.py has all handlers."""
    print("\n" + "="*70)
    print("PHASE EXECUTOR VERIFICATION")
    print("="*70 + "\n")
    
    try:
        from core.phase_executor import PHASE_METADATA, PhaseExecutor
        
        print(f"✅ PHASE_METADATA: {len(PHASE_METADATA)} phases registered")
        
        # Check all phases have metadata
        expected_keys = set(f"phase{i}" for i in range(1, 16))
        metadata_keys = set(PHASE_METADATA.keys())
        
        missing = expected_keys - metadata_keys
        extra = metadata_keys - expected_keys
        
        if missing:
            print(f"❌ Missing in metadata: {missing}")
            return False
        
        if extra:
            print(f"⚠️  Extra in metadata: {extra}")
        
        # Check each metadata entry
        for phase_key in sorted(metadata_keys):
            meta = PHASE_METADATA[phase_key]
            required_fields = {"title", "description", "icon", "color", "section"}
            missing_fields = required_fields - set(meta.keys())
            
            if missing_fields:
                print(f"❌ {phase_key}: Missing fields: {missing_fields}")
                return False
        
        print("✅ All metadata entries complete")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    phases_ok = validate_phases()
    executor_ok = check_phase_executor()
    
    print("\n" + "="*70)
    if phases_ok and executor_ok:
        print("🎉 VALIDATION COMPLETE - ALL SYSTEMS GO!")
        sys.exit(0)
    else:
        print("⚠️  VALIDATION FAILED - ISSUES DETECTED")
        sys.exit(1)
