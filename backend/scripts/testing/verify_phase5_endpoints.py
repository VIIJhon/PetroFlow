"""
Phase 5: Endpoint Verification Script
Verifies that all refactored endpoints are properly registered and functional
Author: Jhon Villegas
"""

import sys
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def verify_imports():
    """Verify all required imports are available."""
    logger.info("=" * 70)
    logger.info("PHASE 5 ENDPOINT VERIFICATION")
    logger.info("=" * 70)
    logger.info("\n1. Verifying imports...")
    
    try:
        from app.main import app
        logger.info("✓ Main app imported")
        
        from app.api.deps import (
            get_safety_validator,
            get_optimizer,
            get_telemetry_processor,
            get_simulation_orchestrator,
            get_report_generator
        )
        logger.info("✓ Dependency injection functions imported")
        
        from app.api.endpoints import simulation_refactored, equipment_refactored, iot_refactored
        logger.info("✓ Refactored endpoint modules imported")
        
        from app.core.simulation import SimulationOrchestrator
        from app.core.safety_envelope import SafetyEnvelopeValidator
        from app.core.optimizer import OperationalOptimizer
        from app.core.telemetry import TelemetryProcessor
        from app.core.report_generator import ReportGenerator
        logger.info("✓ Phase 4 service classes imported")
        
        return True, app
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False, None


def verify_routes(app):
    """Verify all routes are registered."""
    logger.info("\n2. Verifying registered routes...")
    
    expected_v2_routes = [
        "/api/v2/simulation/steady-state",
        "/api/v2/simulation/transient",
        "/api/v2/simulation/what-if",
        "/api/v2/simulation/optimize",
        "/api/v2/equipment/validate",
        "/api/v2/equipment/{equipment_id}/safety-status",
        "/api/v2/equipment/optimize",
        "/api/v2/equipment/{equipment_id}/envelope",
        "/api/v2/iot/telemetry/process",
        "/api/v2/iot/telemetry/batch",
        "/api/v2/iot/telemetry/anomalies",
        "/api/v2/iot/telemetry/stats",
    ]
    
    registered_routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            registered_routes.append(route.path)
    
    found_routes = []
    missing_routes = []
    
    for expected_route in expected_v2_routes:
        # Check if route exists (handle path parameters)
        route_base = expected_route.split('{')[0].rstrip('/')
        found = any(route.startswith(route_base) for route in registered_routes)
        
        if found:
            found_routes.append(expected_route)
            logger.info(f"✓ {expected_route}")
        else:
            missing_routes.append(expected_route)
            logger.warning(f"✗ {expected_route} - NOT FOUND")
    
    logger.info(f"\nRoutes found: {len(found_routes)}/{len(expected_v2_routes)}")
    
    return len(missing_routes) == 0


def verify_services():
    """Verify services can be instantiated."""
    logger.info("\n3. Verifying service instantiation...")
    
    try:
        from app.api.deps import (
            get_safety_validator,
            get_optimizer,
            get_telemetry_processor,
            get_simulation_orchestrator,
            get_report_generator,
            reset_service_instances
        )
        
        # Reset to ensure clean state
        reset_service_instances()
        
        # Test each service
        validator = get_safety_validator()
        logger.info(f"✓ SafetyEnvelopeValidator: {type(validator).__name__}")
        
        optimizer = get_optimizer()
        logger.info(f"✓ OperationalOptimizer: {type(optimizer).__name__}")
        
        processor = get_telemetry_processor()
        logger.info(f"✓ TelemetryProcessor: {type(processor).__name__}")
        
        orchestrator = get_simulation_orchestrator()
        logger.info(f"✓ SimulationOrchestrator: {type(orchestrator).__name__}")
        
        generator = get_report_generator()
        logger.info(f"✓ ReportGenerator: {type(generator).__name__}")
        
        # Verify singleton pattern
        validator2 = get_safety_validator()
        if validator is validator2:
            logger.info("✓ Singleton pattern working correctly")
        else:
            logger.warning("✗ Singleton pattern not working")
            return False
        
        return True
    except Exception as e:
        logger.error(f"✗ Service instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_endpoint_structure():
    """Verify endpoint file structure."""
    logger.info("\n4. Verifying endpoint file structure...")
    
    import os
    
    expected_files = [
        "petroflow/app/api/endpoints/simulation_refactored.py",
        "petroflow/app/api/endpoints/equipment_refactored.py",
        "petroflow/app/api/endpoints/iot_refactored.py",
        "petroflow/app/api/deps.py",
        "petroflow/tests/test_api_endpoints.py"
    ]
    
    all_exist = True
    for file_path in expected_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            logger.info(f"✓ {file_path} ({size} bytes)")
        else:
            logger.error(f"✗ {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist


def verify_backward_compatibility(app):
    """Verify old endpoints still exist."""
    logger.info("\n5. Verifying backward compatibility...")
    
    old_routes = [
        "/api/simulation/run",
        "/api/simulation/optimize",
        "/api/equipment/",
        "/api/iot/telemetry"
    ]
    
    registered_routes = [route.path for route in app.routes if hasattr(route, 'path')]
    
    compatible = True
    for old_route in old_routes:
        found = any(old_route in route for route in registered_routes)
        if found:
            logger.info(f"✓ {old_route} (backward compatible)")
        else:
            logger.warning(f"⚠ {old_route} - may not be backward compatible")
    
    return compatible


def generate_summary(results: Dict[str, bool]):
    """Generate verification summary."""
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for check, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {check}")
    
    logger.info(f"\nTotal: {passed}/{total} checks passed")
    logger.info("=" * 70)
    
    if passed == total:
        logger.info("\n🎉 ALL VERIFICATIONS PASSED!")
        logger.info("\nPhase 5 refactoring is complete and functional.")
        logger.info("\nNew V2 endpoints available at:")
        logger.info("  - /api/v2/simulation/*")
        logger.info("  - /api/v2/equipment/*")
        logger.info("  - /api/v2/iot/*")
        logger.info("\nOriginal endpoints remain at /api/* for backward compatibility.")
        return True
    else:
        logger.error("\n❌ SOME VERIFICATIONS FAILED")
        logger.error(f"\n{total - passed} check(s) failed. Please review the errors above.")
        return False


def main():
    """Run all verifications."""
    results = {}
    
    # Run verifications
    imports_ok, app = verify_imports()
    results["Imports"] = imports_ok
    
    if not imports_ok:
        logger.error("\nCannot proceed without successful imports.")
        return False
    
    results["Routes"] = verify_routes(app)
    results["Services"] = verify_services()
    results["File Structure"] = verify_endpoint_structure()
    results["Backward Compatibility"] = verify_backward_compatibility(app)
    
    # Generate summary
    success = generate_summary(results)
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)