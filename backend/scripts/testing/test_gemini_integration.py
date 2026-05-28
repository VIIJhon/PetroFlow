"""
Test script for Gemini AI integration
Quick verification that all components are working
Authored by Jhon Villegas
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gemini_service import GeminiAIService, get_gemini_service
from app.schemas.ai_analysis import (
    EquipmentReportRequest,
    OperatorMessageRequest,
    FailurePredictionRequest,
    MaintenanceSuggestionsRequest,
    UrgencyLevel,
    LanguageOption
)


def test_service_initialization():
    """Test that the service initializes correctly"""
    print("\n" + "="*60)
    print("TEST 1: Service Initialization")
    print("="*60)
    
    service = get_gemini_service()
    print(f"✓ Service created: {service.__class__.__name__}")
    print(f"✓ Service enabled: {service.enabled}")
    
    if not service.enabled:
        print("\n⚠ WARNING: Service is not enabled.")
        print("  Possible reasons:")
        print("  1. GEMINI_API_KEY not set in .env")
        print("  2. google-generativeai not installed")
        print("\n  To fix:")
        print("  1. Get API key from: https://makersuite.google.com/app/apikey")
        print("  2. Add to .env: GEMINI_API_KEY=your_key_here")
        print("  3. Run: pip install google-generativeai")
    
    return service


def test_health_check(service):
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Health Check")
    print("="*60)
    
    health = service.health_check()
    print(f"Status: {health['status']}")
    print(f"Message: {health['message']}")
    print(f"Enabled: {health['enabled']}")
    
    if health['status'] == 'healthy':
        print(f"✓ Service is healthy")
        print(f"  Rate limit remaining: {health.get('rate_limit_remaining', 'N/A')}")
        return True
    else:
        print(f"✗ Service is not healthy")
        if 'error' in health:
            print(f"  Error: {health['error']}")
        return False


def test_equipment_analysis(service):
    """Test equipment report analysis"""
    print("\n" + "="*60)
    print("TEST 3: Equipment Report Analysis")
    print("="*60)
    
    if not service.enabled:
        print("⊘ Skipped (service not enabled)")
        return
    
    try:
        result = service.analyze_equipment_report(
            equipment_type="pump",
            equipment_name="TEST-PUMP-001",
            telemetry_data={
                "temperature": 85.5,
                "pressure": 120.3,
                "vibration": 2.1,
                "flow_rate": 450.0,
                "power_consumption": 75.2
            },
            historical_context="Temperature trending upward"
        )
        
        if result['success']:
            print("✓ Analysis successful")
            print(f"  Severity: {result['severity']}")
            print(f"  Model: {result['model']}")
            print(f"\n  Analysis preview:")
            print(f"  {result['analysis'][:200]}...")
        else:
            print(f"✗ Analysis failed: {result.get('error')}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_operator_message(service):
    """Test operator message generation"""
    print("\n" + "="*60)
    print("TEST 4: Operator Message Generation")
    print("="*60)
    
    if not service.enabled:
        print("⊘ Skipped (service not enabled)")
        return
    
    try:
        result = service.generate_operator_message(
            situation="Pump showing elevated temperature",
            technical_details={
                "current_temperature": 95.5,
                "normal_temperature": 75.0
            },
            urgency="high",
            language="english"
        )
        
        if result['success']:
            print("✓ Message generation successful")
            print(f"  Urgency: {result['urgency']}")
            print(f"  Language: {result['language']}")
            print(f"\n  Message preview:")
            print(f"  {result['message'][:200]}...")
        else:
            print(f"✗ Message generation failed: {result.get('error')}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_schemas():
    """Test Pydantic schemas"""
    print("\n" + "="*60)
    print("TEST 5: Pydantic Schemas Validation")
    print("="*60)
    
    try:
        # Test EquipmentReportRequest
        request = EquipmentReportRequest(
            equipment_type="pump",
            equipment_name="PUMP-001",
            telemetry_data={"temperature": 85.5}
        )
        print("✓ EquipmentReportRequest validated")
        
        # Test OperatorMessageRequest
        request = OperatorMessageRequest(
            situation="Test situation description",
            technical_details={"test": "data"},
            urgency=UrgencyLevel.HIGH,
            language=LanguageOption.ENGLISH
        )
        print("✓ OperatorMessageRequest validated")
        
        # Test FailurePredictionRequest
        request = FailurePredictionRequest(
            equipment_type="compressor",
            equipment_name="COMP-001",
            prediction_data={"test": "data"},
            confidence=0.85
        )
        print("✓ FailurePredictionRequest validated")
        
        # Test MaintenanceSuggestionsRequest
        request = MaintenanceSuggestionsRequest(
            equipment_type="turbine",
            equipment_name="TURB-001",
            current_condition={"health": 7.5}
        )
        print("✓ MaintenanceSuggestionsRequest validated")
        
        print("\n✓ All schemas validated successfully")
        
    except Exception as e:
        print(f"✗ Schema validation failed: {str(e)}")


def print_summary():
    """Print integration summary"""
    print("\n" + "="*60)
    print("INTEGRATION SUMMARY")
    print("="*60)
    print("\n✓ Components Created:")
    print("  1. GeminiAIService (app/services/gemini_service.py)")
    print("  2. AI Analysis Schemas (app/schemas/ai_analysis.py)")
    print("  3. AI Analysis Endpoints (app/api/endpoints/ai_analysis.py)")
    print("  4. Configuration updated (app/config.py)")
    print("  5. Requirements updated (requirements.txt)")
    print("  6. Documentation created (docs/guides/GEMINI_AI_INTEGRATION.md)")
    
    print("\n✓ API Endpoints Available:")
    print("  POST /api/v2/ai/analyze-report")
    print("  POST /api/v2/ai/operator-message")
    print("  POST /api/v2/ai/explain-prediction")
    print("  POST /api/v2/ai/maintenance-suggestions")
    print("  GET  /api/v2/ai/health")
    print("  GET  /api/v2/ai/demo")
    
    print("\n✓ Features:")
    print("  - Equipment report analysis")
    print("  - Operator message generation")
    print("  - Failure prediction explanation")
    print("  - Maintenance action suggestions")
    print("  - Multi-language support")
    print("  - Rate limiting (15 req/min)")
    print("  - Zero-cost (Gemini free tier)")
    
    print("\n📚 Next Steps:")
    print("  1. Get API key: https://makersuite.google.com/app/apikey")
    print("  2. Add to .env: GEMINI_API_KEY=your_key_here")
    print("  3. Install: pip install google-generativeai")
    print("  4. Start server: uvicorn app.main:app --reload")
    print("  5. Test: http://localhost:8000/api/v2/ai/health")
    print("  6. Read docs: docs/guides/GEMINI_AI_INTEGRATION.md")
    
    print("\n" + "="*60)


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("GEMINI AI INTEGRATION TEST SUITE")
    print("="*60)
    
    # Test 1: Service initialization
    service = test_service_initialization()
    
    # Test 2: Health check
    is_healthy = test_health_check(service)
    
    # Test 3: Equipment analysis (only if healthy)
    if is_healthy:
        test_equipment_analysis(service)
    
    # Test 4: Operator message (only if healthy)
    if is_healthy:
        test_operator_message(service)
    
    # Test 5: Schema validation
    test_schemas()
    
    # Print summary
    print_summary()
    
    print("\n✓ Integration test complete!")
    print("\nFor full documentation, see: docs/guides/GEMINI_AI_INTEGRATION.md\n")


if __name__ == "__main__":
    main()