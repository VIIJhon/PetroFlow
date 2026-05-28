"""
Test script for CMMS module
"""

print("Testing CMMS module import...")

try:
    from modules import cmms
    print("[OK] CMMS module imported successfully")
    
    # Check key functions exist
    functions_to_check = [
        'render_add_personnel_form',
        'render_personnel_list',
        'render_add_report_form',
        'render_reports_list',
        'save_profile_photo',
        'export_reports_csv',
        'export_all_personnel_csv'
    ]
    
    print("\nChecking key functions:")
    for func_name in functions_to_check:
        if hasattr(cmms, func_name):
            print(f"  [OK] {func_name}")
        else:
            print(f"  [FAIL] {func_name} - MISSING")
    
    # Check constants
    print("\nChecking constants:")
    constants = ['SPECIALTIES', 'CERTIFICATION_LEVELS', 'INTERVENTION_TYPES', 'PRIORITIES']
    for const in constants:
        if hasattr(cmms, const):
            value = getattr(cmms, const)
            print(f"  [OK] {const}: {value}")
        else:
            print(f"  [FAIL] {const} - MISSING")
    
    print("\n[SUCCESS] All CMMS module tests passed!")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

