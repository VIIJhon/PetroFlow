#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificacion del sistema de licencias.
Verifica que todos los componentes esten correctamente configurados.
"""

import sys
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Agregar el directorio raiz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify_database_connection():
    """Verifica la conexion a la base de datos."""
    print("[*] Verificando conexion a la base de datos...")
    try:
        db_path = "petroflow.db"
        if not Path(db_path).exists():
            return False, f"Base de datos no encontrada: {db_path}"
        
        conn = sqlite3.connect(db_path)
        conn.close()
        return True, "Conexion exitosa"
    except Exception as e:
        return False, f"Error de conexion: {str(e)}"

def verify_tables_exist():
    """Verifica que todas las tablas necesarias existan."""
    print("[*] Verificando tablas de la base de datos...")
    
    required_tables = [
        'users',
        'licenses',
        'license_plans',
        'license_activations',
        'payments',
        'payment_methods',
        'mfa_secrets',
        'audit_logs',
        'api_keys',
        'sessions'
    ]
    
    try:
        conn = sqlite3.connect("petroflow.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)
        
        conn.close()
        
        if missing_tables:
            return False, f"Tablas faltantes: {', '.join(missing_tables)}"
        
        return True, f"Todas las tablas existen ({len(required_tables)} tablas)"
    except Exception as e:
        return False, f"Error verificando tablas: {str(e)}"

def verify_admin_user():
    """Verifica que el usuario admin exista y tenga licencia."""
    print("[*] Verificando usuario admin...")
    
    try:
        conn = sqlite3.connect("petroflow.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar usuario admin
        cursor.execute("SELECT id, username, email, is_active FROM users WHERE id = 1")
        admin = cursor.fetchone()
        
        if not admin:
            conn.close()
            return False, "Usuario admin no encontrado"
        
        if not admin['is_active']:
            conn.close()
            return False, "Usuario admin esta inactivo"
        
        # Verificar licencia del admin
        cursor.execute("""
            SELECT l.id, l.type, l.status, l.expires_at
            FROM licenses l
            WHERE l.user_id = 1 AND l.status = 'active'
        """)
        license = cursor.fetchone()
        
        conn.close()
        
        if not license:
            return False, "Usuario admin no tiene licencia activa"
        
        return True, f"Admin OK - Usuario: {admin['username']}, Licencia: {license['type']}"
    except Exception as e:
        return False, f"Error verificando admin: {str(e)}"

def verify_mfa_enabled():
    """Verifica que MFA este habilitado para el admin."""
    print("[*] Verificando MFA para admin...")
    
    try:
        conn = sqlite3.connect("petroflow.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar MFA en tabla users
        cursor.execute("SELECT mfa_enabled FROM users WHERE id = 1")
        user = cursor.fetchone()
        
        if not user or not user['mfa_enabled']:
            conn.close()
            return False, "MFA no esta habilitado en la tabla users"
        
        # Verificar secreto MFA
        cursor.execute("""
            SELECT id, is_active, backup_codes 
            FROM mfa_secrets 
            WHERE user_id = 1 AND is_active = 1
        """)
        mfa_secret = cursor.fetchone()
        
        conn.close()
        
        if not mfa_secret:
            return False, "Secreto MFA no encontrado o inactivo"
        
        import json
        backup_codes = json.loads(mfa_secret['backup_codes'])
        
        return True, f"MFA habilitado - {len(backup_codes)} codigos de backup disponibles"
    except Exception as e:
        return False, f"Error verificando MFA: {str(e)}"

def verify_module_imports():
    """Verifica que todos los modulos se puedan importar."""
    print("[*] Verificando importacion de modulos...")
    
    modules_to_test = [
        ('core.mfa_service', 'MFAService'),
        ('core.license_manager', 'LicenseManager'),
        ('core.payment_gateway', 'PaymentGateway'),
        ('core.enhanced_auth_manager', 'EnhancedAuthManager'),
        ('core.rate_limiter', 'RateLimiter'),
    ]
    
    failed_imports = []
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
        except Exception as e:
            failed_imports.append(f"{module_name}.{class_name}: {str(e)}")
    
    if failed_imports:
        return False, f"Errores de importacion:\n  " + "\n  ".join(failed_imports)
    
    return True, f"Todos los modulos se importaron correctamente ({len(modules_to_test)} modulos)"

def verify_environment_variables():
    """Verifica que las variables de entorno necesarias esten configuradas."""
    print("[*] Verificando variables de entorno...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'JWT_SECRET_KEY',
        'JWT_ACCESS_TOKEN_EXPIRES',
        'JWT_REFRESH_TOKEN_EXPIRES',
    ]
    
    optional_vars = [
        'PAYPAL_CLIENT_ID',
        'PAYPAL_CLIENT_SECRET',
        'STRIPE_SECRET_KEY',
        'REDIS_URL',
        'SENDGRID_API_KEY',
    ]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    missing_optional = []
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        return False, f"Variables requeridas faltantes: {', '.join(missing_required)}"
    
    warnings = []
    if missing_optional:
        warnings.append(f"Variables opcionales no configuradas: {', '.join(missing_optional)}")
    
    message = f"Variables requeridas OK ({len(required_vars)} configuradas)"
    if warnings:
        message += f"\n  ADVERTENCIA: {warnings[0]}"
    
    return True, message

def verify_subscription_plans():
    """Verifica que existan planes de suscripcion."""
    print("[*] Verificando planes de suscripcion...")
    
    try:
        conn = sqlite3.connect("petroflow.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM license_plans")
        result = cursor.fetchone()
        count = result[0]
        
        conn.close()
        
        if count == 0:
            return False, "No hay planes de licencia configurados"
        
        return True, f"{count} planes de licencia disponibles"
    except Exception as e:
        return False, f"Error verificando planes: {str(e)}"

def generate_report():
    """Genera el reporte completo de verificacion."""
    print("=" * 70)
    print("VERIFICACION DEL SISTEMA DE LICENCIAS")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks = [
        ("Conexion a Base de Datos", verify_database_connection),
        ("Tablas de Base de Datos", verify_tables_exist),
        ("Usuario Admin", verify_admin_user),
        ("MFA Habilitado", verify_mfa_enabled),
        ("Importacion de Modulos", verify_module_imports),
        ("Variables de Entorno", verify_environment_variables),
        ("Planes de Suscripcion", verify_subscription_plans),
    ]
    
    results = []
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            success, message = check_func()
            results.append({
                'name': check_name,
                'success': success,
                'message': message
            })
            
            status = "[OK]" if success else "[ERROR]"
            print(f"{status} {check_name}")
            print(f"    {message}")
            print()
            
            if not success:
                all_passed = False
        except Exception as e:
            results.append({
                'name': check_name,
                'success': False,
                'message': f"Excepcion: {str(e)}"
            })
            print(f"[ERROR] {check_name}")
            print(f"    Excepcion: {str(e)}")
            print()
            all_passed = False
    
    # Resumen
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Verificaciones exitosas: {passed}/{total}")
    print()
    
    if all_passed:
        print("[OK] SISTEMA DE LICENCIAS COMPLETAMENTE FUNCIONAL")
    else:
        print("[ERROR] SE ENCONTRARON PROBLEMAS EN EL SISTEMA")
        print()
        print("Problemas encontrados:")
        for result in results:
            if not result['success']:
                print(f"  - {result['name']}: {result['message']}")
    
    print()
    
    # Guardar reporte
    report_path = "migrations/system_verification_report.txt"
    print(f"[*] Guardando reporte en: {report_path}")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("REPORTE DE VERIFICACION DEL SISTEMA DE LICENCIAS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for result in results:
            status = "OK" if result['success'] else "ERROR"
            f.write(f"[{status}] {result['name']}\n")
            f.write(f"    {result['message']}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("RESUMEN\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Verificaciones exitosas: {passed}/{total}\n\n")
        
        if all_passed:
            f.write("RESULTADO: SISTEMA DE LICENCIAS COMPLETAMENTE FUNCIONAL\n")
        else:
            f.write("RESULTADO: SE ENCONTRARON PROBLEMAS EN EL SISTEMA\n\n")
            f.write("Problemas encontrados:\n")
            for result in results:
                if not result['success']:
                    f.write(f"  - {result['name']}: {result['message']}\n")
    
    print("[OK] Reporte guardado exitosamente")
    print()
    
    return all_passed

if __name__ == "__main__":
    success = generate_report()
    sys.exit(0 if success else 1)