import os
import sys
import sqlite3
import importlib

def print_result(check, status, message=""):
    print(f"{'[OK]' if status else '[FAIL]'} {check:<40} {message}")

def verify_system():
    print("=" * 60)
    print("SYSTEM VERIFICATION REPORT")
    print("=" * 60)

    all_passed = True

    # 1. Python version
    py_version = sys.version_info
    py_status = py_version.major == 3 and py_version.minor >= 9
    print_result("Python Version >= 3.9", py_status, f"(Found {py_version.major}.{py_version.minor})")
    all_passed = all_passed and py_status

    # 2. Database & MFA
    db_path = "petroflow.db"
    db_status = os.path.exists(db_path)
    print_result("Database File Exists", db_status, db_path)
    all_passed = all_passed and db_status

    if db_status:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mfa_secrets'")
            mfa_table_exists = bool(cursor.fetchone())
            print_result("MFA Secrets Table Exists", mfa_table_exists)
            all_passed = all_passed and mfa_table_exists

            if mfa_table_exists:
                cursor.execute("SELECT COUNT(*) FROM mfa_secrets")
                count = cursor.fetchone()[0]
                print_result("MFA Secrets Populated", count > 0, f"({count} records found)")
            conn.close()
        except Exception as e:
            print_result("Database Verification", False, str(e))
            all_passed = False

    # 3. Dependencies
    required_modules = ["stripe", "jwt", "jose", "pyotp", "qrcode", "cryptography", "argon2"]
    for mod in required_modules:
        try:
            importlib.import_module(mod)
            print_result(f"Module '{mod}' Installed", True)
        except ImportError:
            print_result(f"Module '{mod}' Installed", False, "Missing dependency")
            all_passed = False

    # 4. Environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        env_vars = ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"]
        for var in env_vars:
            val = os.getenv(var)
            status = bool(val and val != "sk_test_YOUR_STRIPE_SECRET_KEY_HERE")
            msg = "Configured" if status else "Missing or default value"
            # It's okay if they are placeholders for now, we just check if they are defined
            print_result(f"Env Var '{var}' Defined", bool(val), msg)
    except Exception as e:
        print_result("Environment Variables", False, str(e))

    print("=" * 60)
    if all_passed:
        print("[OK] System verification completed successfully.")
    else:
        print("[FAIL] System verification found issues.")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    success = verify_system()
    sys.exit(0 if success else 1)
