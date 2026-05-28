#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to enable MFA (Multi-Factor Authentication) for the admin user.
Generates QR code, TOTP secret and backup codes.
"""

import sys
import os
import base64
import sqlite3
import json
from io import BytesIO

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.mfa_service import MFAService

def enable_admin_mfa():
    """Enables MFA for the admin user and generates all necessary codes."""
    
    print("=" * 70)
    print("MFA CONFIGURATION FOR ADMIN USER")
    print("=" * 70)
    print()
    
    # Connect to the database
    print("[*] Connecting to the database...")
    db_path = "petroflow.db"
    conn = None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verify that the admin user exists
        cursor.execute("SELECT id, username, email FROM users WHERE id = 1")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            print("[ERROR] Admin user (id=1) not found in the database")
            conn.close()
            return False
        
        print(f"[OK] User found: {admin_user['username']} ({admin_user['email']})")
        print()
        
        # Initialize MFA service
        print("[*] Initializing MFA service...")
        mfa_service = MFAService(db_path=db_path)
        
        # Generate TOTP secret
        print("[*] Generating TOTP secret...")
        totp_secret = mfa_service.generate_secret()
        
        # Generate backup codes
        print("[*] Generating backup codes...")
        backup_codes = mfa_service.generate_backup_codes()
        
        # Generate QR code
        print("[*] Generating QR code...")
        qr_code_data = mfa_service.generate_qr_code(totp_secret, admin_user['email'])
        
        # Save to database (without verification for initial setup)
        print("[*] Saving MFA configuration in the database...")
        
        # Hash the backup codes
        import hashlib
        hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in backup_codes]
        
        # Insert or update MFA secret
        cursor.execute("""
            INSERT OR REPLACE INTO mfa_secrets (user_id, secret, backup_codes, is_active)
            VALUES (?, ?, ?, 1)
        """, (1, totp_secret, json.dumps(hashed_codes)))
        
        # Update user
        cursor.execute("""
            UPDATE users 
            SET mfa_enabled = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """)
        
        conn.commit()
        
        print("[OK] MFA enabled successfully")
        print()
        
        # Extract base64 from QR (remove the data:image/png;base64, prefix)
        qr_code_base64 = qr_code_data.split(',')[1] if ',' in qr_code_data else qr_code_data
        
        # Display TOTP secret
        print("=" * 70)
        print("TOTP SECRET")
        print("=" * 70)
        print(f"Secret: {totp_secret}")
        print()
        print("IMPORTANT: Save this secret in a secure location.")
        print("You can use it to manually configure your authenticator app.")
        print()
        
        # Display backup codes
        print("=" * 70)
        print("BACKUP CODES (10 codes)")
        print("=" * 70)
        print("IMPORTANT: Save these codes in a secure location.")
        print("Each code can be used ONLY ONCE.")
        print()
        for i, code in enumerate(backup_codes, 1):
            print(f"  {i:2d}. {code}")
        print()
        
        # Save QR code as image
        print("[*] Generating QR code image...")
        qr_image_data = base64.b64decode(qr_code_base64)
        qr_path = "admin_mfa_qr.png"
        
        with open(qr_path, 'wb') as f:
            f.write(qr_image_data)
        
        print(f"[OK] QR Code saved at: {qr_path}")
        print()
        
        # Save all information in a text file
        setup_info_path = "migrations/admin_mfa_setup.txt"
        print(f"[*] Saving complete information at: {setup_info_path}")
        
        with open(setup_info_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("MFA CONFIGURATION - ADMIN USER\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"User: {admin_user['username']}\n")
            f.write(f"Email: {admin_user['email']}\n")
            f.write(f"User ID: {admin_user['id']}\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("TOTP SECRET\n")
            f.write("=" * 70 + "\n")
            f.write(f"{totp_secret}\n\n")
            f.write("IMPORTANT: Use this secret to configure your authenticator app\n")
            f.write("(Google Authenticator, Authy, Microsoft Authenticator, etc.)\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("QR CODE\n")
            f.write("=" * 70 + "\n")
            f.write(f"The QR code was saved at: admin_mfa_qr.png\n")
            f.write("Scan this code with your authenticator app.\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("BACKUP CODES (10 codes)\n")
            f.write("=" * 70 + "\n")
            f.write("Save these codes in a secure location.\n")
            f.write("Each code can be used ONLY ONCE if you lose access to your device.\n\n")
            
            for i, code in enumerate(backup_codes, 1):
                f.write(f"  {i:2d}. {code}\n")
            
            f.write("\n")
            f.write("=" * 70 + "\n")
            f.write("INSTRUCTIONS FOR USE\n")
            f.write("=" * 70 + "\n")
            f.write("1. Install an authenticator app on your phone:\n")
            f.write("   - Google Authenticator\n")
            f.write("   - Microsoft Authenticator\n")
            f.write("   - Authy\n")
            f.write("   - Any TOTP-compatible app\n\n")
            
            f.write("2. Scan the QR code (admin_mfa_qr.png) with the app\n")
            f.write("   Or enter the TOTP secret manually\n\n")
            
            f.write("3. The app will generate a 6-digit code that changes every 30 seconds\n\n")
            
            f.write("4. When logging in, after your password, enter the code\n")
            f.write("   shown by your authenticator app\n\n")
            
            f.write("5. If you lose your phone, use one of the backup codes\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("SECURITY\n")
            f.write("=" * 70 + "\n")
            f.write("IMPORTANT: DO NOT share these codes with anyone\n")
            f.write("IMPORTANT: Save the backup codes in a secure and separate location\n")
            f.write("IMPORTANT: If you suspect your secret was compromised, disable\n")
            f.write("            and re-enable MFA to generate new codes\n\n")
        
        print("[OK] Information saved successfully")
        print()
        
        # Final summary
        print("=" * 70)
        print("CONFIGURATION COMPLETED")
        print("=" * 70)
        print()
        print("Generated files:")
        print(f"  1. {qr_path} - QR Code to scan")
        print(f"  2. {setup_info_path} - Complete configuration information")
        print()
        print("Next steps:")
        print("  1. Scan the QR code with your authenticator app")
        print("  2. Save the backup codes in a secure location")
        print("  3. Test logging in with MFA")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        if conn is not None:
            conn.close()
        return False
    
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    success = enable_admin_mfa()
    sys.exit(0 if success else 1)