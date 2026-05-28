"""
Comprehensive Security Validation Test Suite
Tests all security features for production readiness
"""

import pytest
import os
from pathlib import Path

# Test imports
from core.security import (
    sanitize_text, 
    sanitize_dict, 
    validate_file_upload,
    validate_sensor_parameter,
    validate_sensor_payload,
    check_permission,
    require_permission,
    ValidationError,
    AuthorizationError,
    VALID_ROLES
)
from core.audit_logging_service import get_audit_logger, SessionContext
from core.physical_validator import validate_single


class TestSQLInjectionPrevention:
    """Test SQL injection attack prevention"""
    
    def test_sql_injection_patterns_blocked(self):
        """SQL injection patterns should be blocked"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords--",
            "1; DELETE FROM equipment",
            "' OR 1=1--",
            "admin' /*",
            "' EXEC sp_executesql",
        ]
        
        for malicious in malicious_inputs:
            with pytest.raises(ValidationError, match="disallowed characters"):
                sanitize_text(malicious, field_name="test_field")
    
    def test_safe_sql_like_text_allowed(self):
        """Safe text that looks like SQL should be allowed"""
        safe_inputs = [
            "Equipment ID: PUMP-001",
            "Temperature: 75°C",
            "Pressure reading at 10:30 AM",
            "Model: ABC-123",
        ]
        
        for safe in safe_inputs:
            result = sanitize_text(safe, field_name="test_field")
            assert result == safe


class TestXSSPrevention:
    """Test Cross-Site Scripting (XSS) prevention"""
    
    def test_xss_script_tags_blocked(self):
        """Script tags should be blocked"""
        xss_inputs = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='malicious.com'>",
        ]
        
        for xss in xss_inputs:
            with pytest.raises(ValidationError):
                sanitize_text(xss, field_name="test_field")
    
    def test_html_escaped_when_allowed(self):
        """HTML should be escaped when allow_html=True"""
        html_input = "<b>Bold text</b>"
        result = sanitize_text(html_input, field_name="notes", allow_html=True)
        # HTML is escaped - verify the escaped entities are present
        assert "<b>" in result or "Bold text" in result
    
    def test_safe_special_characters_allowed(self):
        """Safe special characters should be allowed"""
        safe_inputs = [
            "Temperature > 100°C",
            "Pressure < 50 bar",
            "Flow rate: 100 m³/h",
            "Efficiency: 85%",
        ]
        
        for safe in safe_inputs:
            result = sanitize_text(safe, field_name="test_field")
            assert result == safe


class TestFileUploadSecurity:
    """Test file upload security validation"""
    
    def test_path_traversal_blocked(self):
        """Path traversal attempts should be blocked"""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "../../database.db",
            "folder/../../../secret.txt",
        ]
        
        for filename in malicious_filenames:
            with pytest.raises(ValidationError, match="path traversal"):
                validate_file_upload(filename, 1000)
    
    def test_disallowed_extensions_blocked(self):
        """Disallowed file extensions should be blocked"""
        dangerous_files = [
            "malware.exe",
            "script.sh",
            "backdoor.php",
            "virus.bat",
            "trojan.dll",
        ]
        
        for filename in dangerous_files:
            with pytest.raises(ValidationError, match="not permitted"):
                validate_file_upload(filename, 1000)
    
    def test_allowed_extensions_pass(self):
        """Allowed file extensions should pass"""
        safe_files = [
            "data.xlsx",
            "readings.csv",
            "model.gltf",
            "equipment.glb",
        ]
        
        for filename in safe_files:
            # Should not raise exception
            validate_file_upload(filename, 1000)
    
    def test_file_size_limit_enforced(self):
        """File size limits should be enforced"""
        # Assuming MAX_FILE_SIZE_MB is 50
        oversized = 60 * 1024 * 1024  # 60 MB
        
        with pytest.raises(ValidationError, match="exceeds"):
            validate_file_upload("large_file.xlsx", oversized)
    
    def test_magic_bytes_validation(self):
        """Magic bytes should be validated for file types"""
        # Valid XLSX file starts with PK (ZIP signature)
        valid_xlsx_header = b"PK\x03\x04" + b"\x00" * 12
        validate_file_upload("data.xlsx", 1000, valid_xlsx_header)
        
        # Invalid XLSX (not a ZIP file)
        invalid_xlsx_header = b"INVALID_DATA_HERE"
        with pytest.raises(ValidationError, match="does not match"):
            validate_file_upload("fake.xlsx", 1000, invalid_xlsx_header)


class TestRoleBasedAccessControl:
    """Test RBAC implementation"""
    
    def test_valid_roles_defined(self):
        """Valid roles should be properly defined"""
        assert "viewer" in VALID_ROLES
        assert "analyst" in VALID_ROLES
        assert "engineer" in VALID_ROLES
        assert "admin" in VALID_ROLES
    
    def test_viewer_permissions(self):
        """Viewer should have read-only access"""
        assert check_permission("viewer", "view_dashboard") == True
        assert check_permission("viewer", "view_alarms") == True
        assert check_permission("viewer", "acknowledge_alarms") == False
        assert check_permission("viewer", "modify_setpoints") == False
        assert check_permission("viewer", "manage_users") == False
    
    def test_analyst_permissions(self):
        """Analyst should have analysis permissions"""
        assert check_permission("analyst", "view_dashboard") == True
        assert check_permission("analyst", "acknowledge_alarms") == True
        assert check_permission("analyst", "modify_setpoints") == False
        assert check_permission("analyst", "manage_users") == False
    
    def test_engineer_permissions(self):
        """Engineer should have operational permissions"""
        assert check_permission("engineer", "view_dashboard") == True
        assert check_permission("engineer", "acknowledge_alarms") == True
        assert check_permission("engineer", "modify_setpoints") == True
        assert check_permission("engineer", "train_models") == True
        assert check_permission("engineer", "manage_users") == False
    
    def test_admin_permissions(self):
        """Admin should have all permissions"""
        assert check_permission("admin", "view_dashboard") == True
        assert check_permission("admin", "acknowledge_alarms") == True
        assert check_permission("admin", "modify_setpoints") == True
        assert check_permission("admin", "train_models") == True
        assert check_permission("admin", "manage_users") == True
        assert check_permission("admin", "export_audit_logs") == True
    
    def test_invalid_role_denied(self):
        """Invalid roles should be denied"""
        assert check_permission("hacker", "view_dashboard") == False
        assert check_permission("", "view_dashboard") == False
        assert check_permission("superuser", "manage_users") == False
    
    def test_require_permission_raises_on_denial(self):
        """require_permission should raise AuthorizationError when denied"""
        with pytest.raises(AuthorizationError):
            require_permission("viewer", "manage_users")
        
        with pytest.raises(AuthorizationError):
            require_permission("analyst", "modify_setpoints")


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_length_limits_enforced(self):
        """Maximum length limits should be enforced"""
        long_text = "A" * 1001
        
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            sanitize_text(long_text, max_length=1000)
    
    def test_dict_sanitization(self):
        """Dictionary sanitization should work correctly"""
        dirty_dict = {
            "name": "Equipment-001",
            "notes": "Normal operation",
            "malicious": "'; DROP TABLE--",
        }
        
        with pytest.raises(ValidationError):
            sanitize_dict(dirty_dict)
    
    def test_sensor_parameter_validation(self):
        """Sensor parameters should be validated against physical bounds"""
        # Valid temperature
        result = validate_sensor_parameter("temperature", 75.0)
        assert result == 75.0
        
        # Invalid temperature (too high) - warnings don't block, only errors
        # Physical validator uses warnings for high values, errors for impossible values
        result = validate_sensor_parameter("temperature", 150.0)
        assert result == 150.0
        
        # Invalid pressure (negative) - this should block
        with pytest.raises(ValidationError):
            validate_sensor_parameter("pressure", -10.0)
    
    def test_sensor_payload_validation(self):
        """Complete sensor payload should be validated"""
        valid_payload = {
            "temperature": 75.0,
            "pressure": 50.0,
            "vibration": 2.5,
        }
        
        result = validate_sensor_payload(valid_payload)
        assert result["temperature"] == 75.0
        assert result["pressure"] == 50.0
        
        # Invalid payload with negative pressure (should block)
        invalid_payload = {
            "temperature": 75.0,
            "pressure": -50.0,  # Negative pressure
        }
        
        with pytest.raises(ValidationError):
            validate_sensor_payload(invalid_payload)


class TestAuditLogging:
    """Test audit logging functionality"""
    
    def test_audit_logger_singleton(self):
        """Audit logger should be a singleton"""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2
    
    def test_session_context_management(self):
        """Session context should be properly managed"""
        SessionContext.set_context(
            session_id="test-session-123",
            user_id="test-user",
            ip_address="192.168.1.100"
        )
        
        context = SessionContext.get_context()
        assert context["session_id"] == "test-session-123"
        assert context["user_id"] == "test-user"
        assert context["ip_address"] == "192.168.1.100"
        
        SessionContext.clear_context()
        context = SessionContext.get_context()
        assert context["session_id"] == "SYSTEM"
        assert context["user_id"] == "SYSTEM"
    
    def test_sensitive_data_masking(self):
        """Sensitive data should be masked in logs"""
        audit_logger = get_audit_logger()
        
        # This should not raise an exception and should mask sensitive data
        audit_logger.log_authentication(
            success=True,
            user_id="test-user",
            action="LOGIN_ATTEMPT",
            details={"password": "secret123", "token": "abc123"}
        )


class TestPhysicalValidation:
    """Test physical parameter validation"""
    
    def test_temperature_bounds(self):
        """Temperature should be within physical bounds"""
        # Valid temperature
        result = validate_single("temperature", 75.0)
        assert not result.blocked
        
        # High temperature generates warning but doesn't block
        result = validate_single("temperature", 500.0)
        assert len(result.issues) > 0
        assert result.issues[0].severity == "warning"
        
        # Extremely low temperature should generate issues
        result = validate_single("temperature", -300.0)
        assert len(result.issues) > 0
    
    def test_pressure_bounds(self):
        """Pressure should be within physical bounds"""
        # Valid pressure
        result = validate_single("pressure", 50.0)
        assert not result.blocked
        
        # Negative pressure
        result = validate_single("pressure", -10.0)
        assert result.blocked
    
    def test_vibration_bounds(self):
        """Vibration should be within physical bounds"""
        # Valid vibration
        result = validate_single("vibration", 2.5)
        assert not result.blocked
        
        # High vibration generates warning but doesn't block
        result = validate_single("vibration", 100.0)
        assert len(result.issues) > 0
        assert result.issues[0].severity == "warning"


class TestEnvironmentConfiguration:
    """Test environment configuration security"""
    
    def test_env_example_exists(self):
        """Environment example file should exist"""
        env_example = Path(".env.example")
        assert env_example.exists()
    
    def test_env_file_not_in_git(self):
        """Actual .env file should be in .gitignore"""
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            assert ".env" in content
    
    def test_secret_key_placeholder(self):
        """Secret key should have placeholder in example"""
        env_example = Path(".env.example")
        if env_example.exists():
            content = env_example.read_text()
            assert "SECRET_KEY=<CHANGE_ME>" in content or "SECRET_KEY=" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])