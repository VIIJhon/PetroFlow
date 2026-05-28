"""
Unit tests for audit_logger.py
Covers:
  - Singleton pattern
  - SessionContext: set / get / clear
  - ContextFilter: adds session context to log records
  - _mask_sensitive_data: password, token, api_key
  - AuditLogger.log_* methods (smoke tests + format validation)
  - log_error captures exception type
  - log_authentication level selection
  - log_model_training level selection
  - log_data_validation level selection
  - Cleanup: cleanup_old_logs does not raise
"""

import pytest
import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Streamlit already mocked in conftest.py
from core.audit_logging_service import (
    AuditLogger,
    SessionContext,
    ContextFilter,
    get_audit_logger,
    log_system,
    log_database,
    log_error as module_log_error,
    log_prediction as module_log_prediction,
    log_file_operation as module_log_file_operation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_singleton():
    """Force AuditLogger singleton to re-initialise."""
    AuditLogger._instance = None
    import core.audit_logging_service as al_mod
    al_mod._audit_logger = None


@pytest.fixture(autouse=True)
def reset_audit_singleton():
    _reset_singleton()
    yield
    _reset_singleton()


@pytest.fixture
def audit_logger(tmp_logs):
    """AuditLogger with logs directed to a temp directory."""
    with patch.object(AuditLogger, "_load_config", return_value={
        "log_level": "DEBUG",
        "log_directory": str(tmp_logs),
        "max_file_size_mb": 1,
        "backup_count": 2,
        "enable_console_output": False,
        "enable_file_output": False,   # Disable file I/O for speed
        "categories": {
            "system_audit":    {"enabled": True, "file": "system_audit.log",    "level": "DEBUG"},
            "authentication":  {"enabled": True, "file": "authentication.log",  "level": "DEBUG"},
            "database":        {"enabled": True, "file": "database.log",         "level": "DEBUG"},
            "predictions":     {"enabled": True, "file": "predictions.log",      "level": "DEBUG"},
            "file_operations": {"enabled": True, "file": "file_operations.log", "level": "DEBUG"},
            "errors":          {"enabled": True, "file": "errors.log",           "level": "DEBUG"},
            "security":        {"enabled": True, "file": "security.log",         "level": "DEBUG"},
        },
    }):
        logger = AuditLogger()
        yield logger


# ===========================================================================
# 1. Singleton Pattern
# ===========================================================================

class TestAuditLoggerSingleton:

    @pytest.mark.unit
    def test_same_instance_returned(self, audit_logger):
        a1 = AuditLogger()
        a2 = AuditLogger()
        assert a1 is a2

    @pytest.mark.unit
    def test_get_audit_logger_returns_instance(self, audit_logger):
        instance = get_audit_logger()
        assert isinstance(instance, AuditLogger)


# ===========================================================================
# 2. SessionContext
# ===========================================================================

class TestSessionContext:

    @pytest.mark.unit
    def test_default_context_values(self):
        SessionContext.clear_context()
        ctx = SessionContext.get_context()
        assert ctx["session_id"] == "SYSTEM"
        assert ctx["user_id"] == "SYSTEM"
        assert ctx["ip_address"] == "127.0.0.1"

    @pytest.mark.unit
    def test_set_context_updates_values(self):
        SessionContext.set_context(
            session_id="sess-123",
            user_id="operator1",
            ip_address="192.168.1.10"
        )
        ctx = SessionContext.get_context()
        assert ctx["session_id"] == "sess-123"
        assert ctx["user_id"] == "operator1"
        assert ctx["ip_address"] == "192.168.1.10"

    @pytest.mark.unit
    def test_clear_context_resets_to_system(self):
        SessionContext.set_context("abc", "user", "1.2.3.4")
        SessionContext.clear_context()
        ctx = SessionContext.get_context()
        assert ctx["session_id"] == "SYSTEM"

    @pytest.mark.unit
    def test_partial_set_context(self):
        SessionContext.set_context(user_id="partial_user")
        ctx = SessionContext.get_context()
        assert ctx["user_id"] == "partial_user"
        assert ctx["session_id"] == "SYSTEM"  # Default when not set


# ===========================================================================
# 3. ContextFilter
# ===========================================================================

class TestContextFilter:

    @pytest.mark.unit
    def test_filter_adds_session_id_to_record(self):
        SessionContext.set_context(session_id="filter-test", user_id="u1")
        cf = ContextFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        cf.filter(record)
        assert record.session_id == "filter-test"
        assert record.user_id == "u1"

    @pytest.mark.unit
    def test_filter_adds_action_default(self):
        cf = ContextFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        cf.filter(record)
        assert record.action == "UNKNOWN"

    @pytest.mark.unit
    def test_filter_returns_true(self):
        cf = ContextFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        assert cf.filter(record) is True


# ===========================================================================
# 4. Sensitive data masking
# ===========================================================================

class TestSensitiveDataMasking:

    @pytest.mark.unit
    def test_password_masked(self, audit_logger):
        data = {"username": "admin", "password": "s3cr3t"}
        result = audit_logger.mask_sensitive_data(data)
        assert result["password"] == "***MASKED***"
        assert result["username"] == "admin"

    @pytest.mark.unit
    def test_token_masked(self, audit_logger):
        data = {"api_token": "Bearer abc123"}
        result = audit_logger.mask_sensitive_data(data)
        assert result["api_token"] == "***MASKED***"

    @pytest.mark.unit
    def test_api_key_masked(self, audit_logger):
        data = {"api_key": "key-xyz-789"}
        result = audit_logger.mask_sensitive_data(data)
        assert result["api_key"] == "***MASKED***"

    @pytest.mark.unit
    def test_nested_dict_masked(self, audit_logger):
        data = {"config": {"password": "inner_secret", "host": "localhost"}}
        result = audit_logger.mask_sensitive_data(data)
        assert result["config"]["password"] == "***MASKED***"
        assert result["config"]["host"] == "localhost"

    @pytest.mark.unit
    def test_non_sensitive_fields_unchanged(self, audit_logger):
        data = {"equipment_id": "PUMP-001", "value": 78.5, "unit": "celsius"}
        result = audit_logger.mask_sensitive_data(data)
        assert result == data

    @pytest.mark.unit
    def test_list_masking(self, audit_logger):
        data = [{"password": "abc"}, {"username": "xyz"}]
        result = audit_logger.mask_sensitive_data(data)
        assert result[0]["password"] == "***MASKED***"
        assert result[1]["username"] == "xyz"

    @pytest.mark.unit
    def test_scalar_value_returned_unchanged(self, audit_logger):
        assert audit_logger.mask_sensitive_data("plain string") == "plain string"
        assert audit_logger.mask_sensitive_data(42) == 42


# ===========================================================================
# 5. log_* method smoke tests (no I/O, just ensure no exceptions)
# ===========================================================================

class TestLoggingMethods:

    @pytest.mark.unit
    def test_log_system_does_not_raise(self, audit_logger):
        audit_logger.log_system("System event test", action="TEST")

    @pytest.mark.unit
    def test_log_authentication_success(self, audit_logger):
        audit_logger.log_authentication(
            user_id="operator1", action="LOGIN", success=True
        )

    @pytest.mark.unit
    def test_log_authentication_failure(self, audit_logger):
        audit_logger.log_authentication(
            user_id="baduser", action="LOGIN", success=False
        )

    @pytest.mark.unit
    def test_log_database_operation_does_not_raise(self, audit_logger):
        audit_logger.log_database_operation(
            table="personal_mantenimiento",
            operation="create",
            record_id=1,
            details={"nombre": "Test"},
            execution_time=0.05,
        )

    @pytest.mark.unit
    def test_log_prediction_does_not_raise(self, audit_logger):
        audit_logger.log_prediction(
            input_params={"temperature": 75, "pressure": 25},
            output_probability=0.35,
            confidence=0.88,
            model_type="RandomForest",
        )

    @pytest.mark.unit
    def test_log_file_operation_does_not_raise(self, audit_logger):
        audit_logger.log_file_operation(
            operation="upload",
            filename="sensor_data.xlsx",
            size=204800,
            user_id="admin",
            file_type="xlsx",
        )

    @pytest.mark.unit
    def test_log_error_with_exception_does_not_raise(self, audit_logger):
        try:
            raise ValueError("Test error")
        except ValueError as e:
            audit_logger.log_error(e, context="unit_test")

    @pytest.mark.unit
    def test_log_error_captures_exception_type(self, audit_logger):
        """log_error should add exception_type to the log record kwargs."""
        logged_calls = []

        original_log = audit_logger._log

        def capturing_log(category, level, message, action="UNKNOWN", **kwargs):
            logged_calls.append(kwargs)

        audit_logger._log = capturing_log
        try:
            try:
                raise RuntimeError("Sample")
            except RuntimeError as e:
                audit_logger.log_error(e, context="test_context", stack_trace=False)
        finally:
            audit_logger._log = original_log

        assert len(logged_calls) == 1
        assert logged_calls[0].get("exception_type") == "RuntimeError"

    @pytest.mark.unit
    def test_log_model_training_does_not_raise(self, audit_logger):
        audit_logger.log_model_training(
            model_type="RandomForest",
            status="completed",
            accuracy=0.92,
            duration=4.5,
        )

    @pytest.mark.unit
    def test_log_data_validation_does_not_raise(self, audit_logger):
        audit_logger.log_data_validation(
            filename="upload.csv",
            status="passed",
            rows_processed=500,
        )

    @pytest.mark.unit
    def test_log_cache_operation_does_not_raise(self, audit_logger):
        audit_logger.log_cache_operation(
            operation="hit", cache_key="validate_excel_structure:abc123", hit=True
        )

    @pytest.mark.unit
    def test_log_security_event_does_not_raise(self, audit_logger):
        audit_logger.log_security_event(
            event_type="unauthorized_access",
            severity="WARNING",
            details={"user": "attacker", "endpoint": "/admin"},
        )


# ===========================================================================
# 6. Level selection logic
# ===========================================================================

class TestLevelSelection:

    @pytest.mark.unit
    def test_authentication_success_uses_info_level(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            audit_logger.log_authentication("user1", "LOGIN", success=True)
            call_args = mock_log.call_args[0]
            assert call_args[1] == "INFO"

    @pytest.mark.unit
    def test_authentication_failure_uses_warning_level(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            audit_logger.log_authentication("user1", "LOGIN", success=False)
            call_args = mock_log.call_args[0]
            assert call_args[1] == "WARNING"

    @pytest.mark.unit
    def test_model_training_completed_uses_info_level(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            audit_logger.log_model_training("RF", "completed")
            call_args = mock_log.call_args[0]
            assert call_args[1] == "INFO"

    @pytest.mark.unit
    def test_model_training_failed_uses_warning_level(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            audit_logger.log_model_training("RF", "failed")
            call_args = mock_log.call_args[0]
            assert call_args[1] == "WARNING"

    @pytest.mark.unit
    def test_data_validation_passed_uses_info_level(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            audit_logger.log_data_validation("file.csv", "passed")
            call_args = mock_log.call_args[0]
            assert call_args[1] == "INFO"

    @pytest.mark.unit
    def test_data_validation_failed_uses_warning_level(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            audit_logger.log_data_validation("file.csv", "failed",
                                              errors=["missing_column"])
            call_args = mock_log.call_args[0]
            assert call_args[1] == "WARNING"


# ===========================================================================
# 7. log_operation context manager
# ===========================================================================

class TestLogOperationContextManager:

    @pytest.mark.unit
    def test_successful_operation_logs_start_and_complete(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            with audit_logger.log_operation("test_operation"):
                pass
            assert mock_log.call_count == 2
            # First call should be "Starting"
            first_msg = mock_log.call_args_list[0][0][2]
            assert "Starting" in first_msg
            # Second call should be "Completed"
            second_msg = mock_log.call_args_list[1][0][2]
            assert "Completed" in second_msg

    @pytest.mark.unit
    def test_failed_operation_logs_error(self, audit_logger):
        with patch.object(audit_logger, "_log") as mock_log:
            with pytest.raises(ValueError):
                with audit_logger.log_operation("failing_op"):
                    raise ValueError("intentional")
            # Should log start + failure
            assert mock_log.call_count == 2
            last_msg = mock_log.call_args_list[-1][0][2]
            assert "Failed" in last_msg or "failed" in last_msg.lower()


# ===========================================================================
# 8. Quick-access convenience functions
# ===========================================================================

class TestConvenienceFunctions:

    @pytest.mark.unit
    def test_log_system_function(self, audit_logger):
        """Module-level log_system convenience function should not raise."""
        log_system("Module-level system event")

    @pytest.mark.unit
    def test_log_database_function(self, audit_logger):
        log_database("personal_mantenimiento", "read")

    @pytest.mark.unit
    def test_log_error_function(self, audit_logger):
        try:
            raise KeyError("test_key")
        except KeyError as e:
            module_log_error(e, context="convenience_function_test")

    @pytest.mark.unit
    def test_log_prediction_function(self, audit_logger):
        module_log_prediction(
            input_params={"temp": 80}, output_probability=0.55
        )

    @pytest.mark.unit
    def test_log_file_operation_function(self, audit_logger):
        module_log_file_operation("download", "report.xlsx")
