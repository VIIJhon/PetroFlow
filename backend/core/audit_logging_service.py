"""
PetroFlow Audit Logging System
Professional logging infrastructure for traceability and security compliance.

Fase 8 — Field Testing & SIEM Integration:
  - Structured JSON output when STRUCTURED_LOGGING=true (Splunk/ELK compatible)
  - Jackknife resampling calculations logged with full reproducibility data
  - Critical alerts logged with ISO 8601 timestamps and company_id for RLS audit
  - log_data_access alias added for MQTT telemetry ingestion path
  - log_security alias added for alert message compatibility
"""

import logging
import logging.handlers
import json
import os
import uuid
import hashlib
import threading
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Read structured logging flag from environment at module load time
_STRUCTURED = os.environ.get("STRUCTURED_LOGGING", "true").lower() in ("1", "true", "yes")
_APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
_COMPANY_ID  = os.environ.get("COMPANY_ID", "")


class _JsonFormatter(logging.Formatter):
    """
    Emit each log record as a single-line JSON object.

    Schema (Splunk/ELK Common Schema compliant):
      @timestamp   ISO 8601 UTC with milliseconds
      level        DEBUG | INFO | WARNING | ERROR | CRITICAL
      logger       Python logger name
      action       PetroFlow action code (JACKKNIFE_CALC, CRITICAL_ALERT, etc.)
      session_id   Thread-local session token
      user_id      Authenticated operator ID
      company_id   Tenant identifier (matches Supabase RLS company_id)
      app_version  Deployed application version
      message      Human-readable description
    """

    _RESERVED = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process",
    })

    def format(self, record: logging.LogRecord) -> str:
        event: dict = {
            "@timestamp":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level":       record.levelname,
            "logger":      record.name,
            "module":      record.module,
            "action":      getattr(record, "action", "UNKNOWN"),
            "session_id":  getattr(record, "session_id", "SYSTEM"),
            "user_id":     getattr(record, "user_id", "SYSTEM"),
            "company_id":  _COMPANY_ID,
            "app_version": _APP_VERSION,
            "message":     record.getMessage(),
        }
        # Merge caller-supplied extra fields (skip stdlib internals)
        for key, val in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_") and key not in event:
                try:
                    json.dumps(val)
                    event[key] = val
                except (TypeError, ValueError):
                    event[key] = str(val)

        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)

        return json.dumps(event, ensure_ascii=False, default=str)


class SessionContext:
    """Thread-local storage for session context."""
    _thread_local = threading.local()
    
    @classmethod
    def set_context(cls, session_id: str = None, user_id: str = None, ip_address: str = None):
        """Set session context for current thread."""
        cls._thread_local.session_id = session_id or "SYSTEM"
        cls._thread_local.user_id = user_id or "SYSTEM"
        cls._thread_local.ip_address = ip_address or "127.0.0.1"
    
    @classmethod
    def get_context(cls) -> Dict[str, str]:
        """Get session context for current thread."""
        return {
            'session_id': getattr(cls._thread_local, 'session_id', 'SYSTEM'),
            'user_id': getattr(cls._thread_local, 'user_id', 'SYSTEM'),
            'ip_address': getattr(cls._thread_local, 'ip_address', '127.0.0.1')
        }
    
    @classmethod
    def clear_context(cls):
        """Clear session context."""
        cls._thread_local.session_id = "SYSTEM"
        cls._thread_local.user_id = "SYSTEM"
        cls._thread_local.ip_address = "127.0.0.1"


class ContextFilter(logging.Filter):
    """Add session context to log records."""
    
    def filter(self, record):
        context = SessionContext.get_context()
        record.session_id = context['session_id']
        record.user_id = context['user_id']
        record.ip_address = context['ip_address']
        record.action = getattr(record, 'action', 'UNKNOWN')
        return True


class AuditLogger:
    """
    Centralized audit logging system with multi-level logging,
    automatic rotation, and security features.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the audit logger."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.config = self._load_config()
        self.log_dir = Path(self.config.get('log_directory', 'logs'))
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize loggers for each category
        self.loggers = {}
        self._setup_loggers()
        
        # Initialize session
        SessionContext.set_context()
        
        # Log system startup
        self.log_system("Audit logging system initialized", action="SYSTEM_INIT")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from JSON file."""
        config_path = Path('config/logging_config.json')
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load logging config: {e}")
        
        # Return default configuration
        return {
            'log_level': 'INFO',
            'log_directory': 'logs',
            'max_file_size_mb': 10,
            'backup_count': 5,
            'enable_console_output': True,
            'enable_file_output': True,
            'categories': {
                'system_audit': {'enabled': True, 'file': 'system_audit.log', 'level': 'INFO'},
                'authentication': {'enabled': True, 'file': 'authentication.log', 'level': 'INFO'},
                'database': {'enabled': True, 'file': 'database.log', 'level': 'INFO'},
                'predictions': {'enabled': True, 'file': 'predictions.log', 'level': 'INFO'},
                'file_operations': {'enabled': True, 'file': 'file_operations.log', 'level': 'INFO'},
                'errors': {'enabled': True, 'file': 'errors.log', 'level': 'ERROR'},
                'security': {'enabled': True, 'file': 'security.log', 'level': 'WARNING'}
            }
        }
    
    def _setup_loggers(self):
        """Setup loggers for each category."""
        categories = self.config.get('categories', {})
        
        for category, settings in categories.items():
            if not settings.get('enabled', True):
                continue
            
            logger = logging.getLogger(f'petroflow.{category}')
            logger.setLevel(getattr(logging, settings.get('level', 'INFO')))
            logger.handlers.clear()
            logger.propagate = False
            
            # Add context filter
            logger.addFilter(ContextFilter())
            
            # File handler with rotation
            if self.config.get('enable_file_output', True):
                log_file = self.log_dir / settings['file']
                max_bytes = self.config.get('max_file_size_mb', 10) * 1024 * 1024
                backup_count = self.config.get('backup_count', 5)
                
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setFormatter(self._get_formatter())
                logger.addHandler(file_handler)
            
            # Console handler
            if self.config.get('enable_console_output', True):
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(self._get_formatter())
                logger.addHandler(console_handler)
            
            self.loggers[category] = logger
    
    def _get_formatter(self) -> logging.Formatter:
        """
        Return a log formatter.

        When STRUCTURED_LOGGING=true  → JSON format (Splunk/ELK/SIEM).
        When STRUCTURED_LOGGING=false → human-readable text (development).
        """
        if _STRUCTURED:
            return _JsonFormatter()
        log_format = self.config.get(
            'log_format',
            '[%(asctime)s] [%(levelname)s] [SESSION:%(session_id)s] '
            '[USER:%(user_id)s] [MODULE:%(module)s] [ACTION:%(action)s] %(message)s'
        )
        date_format = self.config.get('date_format', '%Y-%m-%dT%H:%M:%S')
        return logging.Formatter(log_format, datefmt=date_format)
    
    def _get_logger(self, category: str) -> logging.Logger:
        """Get logger for specific category."""
        return self.loggers.get(category, self.loggers.get('system_audit'))
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """Mask sensitive data in logs."""
        if isinstance(data, dict):
            masked = {}
            sensitive_fields = self.config.get('sensitive_fields', [
                'password', 'token', 'secret', 'api_key', 'credit_card', 'ssn'
            ])
            
            for key, value in data.items():
                if any(field in key.lower() for field in sensitive_fields):
                    masked[key] = '***MASKED***'
                elif isinstance(value, (dict, list)):
                    masked[key] = self._mask_sensitive_data(value)
                else:
                    masked[key] = value
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data
    
    def _log(self, category: str, level: str, message: str, action: str = "UNKNOWN", **kwargs):
        """Internal logging method."""
        try:
            logger = self._get_logger(category)
            log_method = getattr(logger, level.lower(), logger.info)
            
            # Add action to extra
            extra = {'action': action}
            
            # Mask sensitive data in kwargs
            masked_kwargs = self._mask_sensitive_data(kwargs)
            
            # Format message with kwargs
            if masked_kwargs:
                message = f"{message} | Details: {json.dumps(masked_kwargs, default=str)}"
            
            log_method(message, extra=extra)
        except Exception as e:
            # Fallback to console if logging fails
            print(f"Logging error: {e} | Original message: {message}")
    
    # Public logging methods
    
    def log_system(self, message: str, action: str = "SYSTEM", level: str = "INFO", **kwargs):
        """Log system-level operations."""
        self._log('system_audit', level, message, action, **kwargs)
    
    def log_authentication(self, user_id: str, action: str, success: bool, ip_address: str = None, **kwargs):
        """Log authentication events."""
        level = "INFO" if success else "WARNING"
        status = "SUCCESS" if success else "FAILED"
        message = f"Authentication {action} {status} for user: {user_id}"
        
        if ip_address:
            kwargs['ip_address'] = ip_address
        
        self._log('authentication', level, message, f"AUTH_{action.upper()}", **kwargs)
    
    def log_database_operation(self, table: str, operation: str, record_id: Any = None, 
                              details: Dict = None, execution_time: float = None):
        """Log database CRUD operations."""
        message = f"Database {operation.upper()} on table '{table}'"
        
        if record_id is not None:
            message += f" | Record ID: {record_id}"
        
        kwargs = {}
        if details:
            kwargs['details'] = details
        if execution_time:
            kwargs['execution_time_ms'] = round(execution_time * 1000, 2)
        
        self._log('database', 'INFO', message, f"DB_{operation.upper()}", **kwargs)
    
    def log_prediction(self, input_params: Dict, output_probability: float, 
                      confidence: float = None, model_type: str = None, **kwargs):
        """Log ML predictions and calculations."""
        message = f"Prediction generated: Probability={output_probability:.4f}"
        
        if model_type:
            message += f" | Model: {model_type}"
        
        prediction_category = kwargs.pop('category', kwargs.pop('category_name', kwargs.pop('prediction_category', None)))
        if prediction_category:
            kwargs['prediction_category'] = prediction_category

        kwargs.update({
            'input_params': input_params,
            'output_probability': output_probability,
            'confidence': confidence
        })
        
        # Log critical failures with higher severity
        level = "WARNING" if output_probability > 0.7 else "INFO"
        
        self._log('predictions', level, message, "PREDICTION", **kwargs)
    
    def log_file_operation(self, operation: str, filename: str, size: int = None, 
                          user_id: str = None, file_type: str = None, **kwargs):
        """Log file uploads/downloads."""
        message = f"File {operation.upper()}: {filename}"
        
        if size:
            kwargs['size_bytes'] = size
            kwargs['size_mb'] = round(size / (1024 * 1024), 2)
        if file_type:
            kwargs['file_type'] = file_type
        if user_id:
            kwargs['user_id'] = user_id
        
        self._log('file_operations', 'INFO', message, f"FILE_{operation.upper()}", **kwargs)
    
    def log_error(self, exception: Exception, context: str = None, 
                 stack_trace: bool = True, **kwargs):
        """Log errors and exceptions."""
        message = f"Error in {context or 'unknown context'}: {str(exception)}"
        
        if stack_trace:
            kwargs['stack_trace'] = traceback.format_exc()
        
        kwargs['exception_type'] = type(exception).__name__
        
        self._log('errors', 'ERROR', message, "ERROR", **kwargs)
    
    # ---- Aliases for compatibility with MQTT and alert modules ---------------

    def log_data_access(self, message: str = "", action: str = "DATA_ACCESS", **kwargs) -> None:
        """
        Log data access events (used by MQTT telemetry ingestion path).
        Authored by Jhon Villegas
        """
        if not message:
            message = f"Data access event: {action}"
        self._log('system_audit', 'INFO', message, action, **kwargs)

    def log_security(self, message: str, action: str = "SECURITY_EVENT", **kwargs) -> None:
        """Log security / alert events (used by MQTT alert handler)."""
        details = kwargs.pop('details', {})
        if isinstance(details, dict):
            kwargs.update(details)
        self._log('security', 'WARNING', message, action, **kwargs)

    def log_system_event(self, action: str, details: Dict[str, Any], level: str = "INFO"):
        """
        Log system-level events with specific details.
        Added for compatibility with Redis rate limiter and telemetry modules.
        Authored by Jhon Villegas
        """
        message = f"System event: {action}"
        kwargs = dict(details) if details else {}
        if "action" in kwargs:
            kwargs["target_action"] = kwargs.pop("action")
        self.log_system(message, action=action, level=level, **kwargs)

    def log_security_event(self, event_type: str = "SECURITY", severity: str = "WARNING", details: Dict = None, **kwargs):
        """
        Log security-related events.
        Authored by Jhon Villegas
        """
        action = kwargs.pop('action', event_type)
        if details is None:
            details = {}
        message = f"Security event: {action}"
        
        full_kwargs = {}
        full_kwargs.update(details)
        full_kwargs.update(kwargs)
        
        # Prevent conflict with the 'action' argument of self._log
        if "action" in full_kwargs:
            full_kwargs["target_action"] = full_kwargs.pop("action")
        
        self._log('security', severity.upper(), message, f"SECURITY_{action.upper()}", **full_kwargs)
    
    def log_jackknife(self, equipment_id: str, equipment_type: str,
                      n_samples: int, mean_estimate: float, std_error: float,
                      ci_lower: float, ci_upper: float, ci_level: float = 0.95,
                      execution_time: float = None, **kwargs) -> None:
        """
        Log a Jackknife resampling calculation with full reproducibility data.

        Every Jackknife run is logged as a discrete, auditable event so that
        field engineers can reproduce any prediction from the log alone.

        Args:
            equipment_id:   Tag / serial number of the equipment.
            equipment_type: 'pump' | 'compressor' | 'turbine'
            n_samples:      Number of leave-one-out resamples.
            mean_estimate:  Jackknife mean failure probability.
            std_error:      Jackknife standard error.
            ci_lower:       Confidence interval lower bound.
            ci_upper:       Confidence interval upper bound.
            ci_level:       Confidence level (default 0.95 = 95%).
            execution_time: Wall-clock seconds for the computation.
        """
        message = (
            f"Jackknife resampling: {equipment_type}/{equipment_id} "
            f"mean={mean_estimate:.4f} SE={std_error:.4f} "
            f"CI{int(ci_level*100)}=[{ci_lower:.4f},{ci_upper:.4f}]"
        )
        level = "WARNING" if mean_estimate > 0.70 else "INFO"
        kwargs.update({
            'equipment_id':   equipment_id,
            'equipment_type': equipment_type,
            'n_samples':      n_samples,
            'mean_estimate':  round(mean_estimate, 6),
            'std_error':      round(std_error, 6),
            'ci_lower':       round(ci_lower, 6),
            'ci_upper':       round(ci_upper, 6),
            'ci_level':       ci_level,
        })
        if execution_time is not None:
            kwargs['execution_time_ms'] = round(execution_time * 1000, 2)
        self._log('predictions', level, message, 'JACKKNIFE_CALC', **kwargs)

    def log_critical_alert(self, equipment_id: str, alert_type: str,
                           failure_probability: float, recommended_action: str,
                           operator_id: str = None, **kwargs) -> None:
        """
        Log a critical maintenance alert for field-testing audit trail.

        Critical alerts (failure probability > 70%) are written to BOTH
        the predictions log and the security log to ensure SIEM pickup.

        Args:
            equipment_id:          Equipment tag.
            alert_type:            Category of predicted failure.
            failure_probability:   Float [0, 1].
            recommended_action:    Prescribed maintenance action.
            operator_id:           ID of the on-call operator (optional).
        """
        message = (
            f"CRITICAL ALERT: {equipment_id} | {alert_type} "
            f"P={failure_probability:.1%} | Action: {recommended_action}"
        )
        kwargs.update({
            'equipment_id':         equipment_id,
            'alert_type':           alert_type,
            'failure_probability':  round(failure_probability, 4),
            'recommended_action':   recommended_action,
            'company_id':           _COMPANY_ID,
        })
        if operator_id:
            kwargs['operator_id'] = operator_id

        # Write to predictions log
        self._log('predictions', 'ERROR', message, 'CRITICAL_ALERT', **kwargs)
        # Duplicate to security log for SIEM alert correlation
        self._log('security', 'ERROR', message, 'CRITICAL_ALERT', **kwargs)

    def log_calculation(self, calc_type: str, input_data: Dict, result: Any,
                        execution_time: float = None, **kwargs):
        """Log statistical calculations (legacy compatibility wrapper)."""
        message = f"Calculation: {calc_type}"
        
        kwargs.update({
            'calculation_type': calc_type,
            'input_data': input_data,
            'result': result
        })
        
        if execution_time:
            kwargs['execution_time_ms'] = round(execution_time * 1000, 2)
        
        self._log('predictions', 'INFO', message, f"CALC_{calc_type.upper()}", **kwargs)
    
    def log_model_training(self, model_type: str, status: str, accuracy: float = None, 
                          duration: float = None, **kwargs):
        """Log ML model training events."""
        message = f"Model training {status}: {model_type}"
        
        if accuracy:
            kwargs['accuracy'] = accuracy
        if duration:
            kwargs['duration_seconds'] = round(duration, 2)
        
        level = "INFO" if status == "completed" else "WARNING"
        
        self._log('predictions', level, message, f"TRAIN_{status.upper()}", **kwargs)
    
    def log_data_validation(self, filename: str, status: str, rows_processed: int = None,
                           errors: list = None, **kwargs):
        """Log data validation results."""
        message = f"Data validation {status}: {filename}"
        
        if rows_processed:
            kwargs['rows_processed'] = rows_processed
        if errors:
            kwargs['validation_errors'] = errors
            kwargs['error_count'] = len(errors)
        
        level = "INFO" if status == "passed" else "WARNING"
        
        self._log('file_operations', level, message, f"VALIDATE_{status.upper()}", **kwargs)
    
    def log_cache_operation(self, operation: str, cache_key: str, hit: bool = None, **kwargs):
        """Log cache operations."""
        message = f"Cache {operation}: {cache_key}"
        
        if hit is not None:
            kwargs['cache_hit'] = hit
            message += f" | {'HIT' if hit else 'MISS'}"
        
        self._log('system_audit', 'DEBUG', message, f"CACHE_{operation.upper()}", **kwargs)
    
    @contextmanager
    def log_operation(self, operation_name: str, category: str = 'system_audit', **kwargs):
        """Context manager for logging operations with timing."""
        start_time = datetime.utcnow()
        operation_id = str(uuid.uuid4())[:8]
        
        self._log(category, 'INFO', f"Starting operation: {operation_name}", 
                 f"START_{operation_name.upper()}", operation_id=operation_id, **kwargs)
        
        try:
            yield
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._log(category, 'INFO', f"Completed operation: {operation_name}", 
                     f"COMPLETE_{operation_name.upper()}", 
                     operation_id=operation_id, duration_seconds=round(duration, 3))
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._log(category, 'ERROR', f"Failed operation: {operation_name} - {str(e)}", 
                     f"FAILED_{operation_name.upper()}", 
                     operation_id=operation_id, duration_seconds=round(duration, 3),
                     error=str(e))
            raise
    
    def get_session_context(self) -> Dict[str, str]:
        """Get current session context."""
        return SessionContext.get_context()
    
    def set_session_context(self, session_id: str = None, user_id: str = None, 
                           ip_address: str = None):
        """Set session context."""
        SessionContext.set_context(session_id, user_id, ip_address)
        self.log_system(f"Session context updated", action="SESSION_UPDATE",
                       session_id=session_id, user_id=user_id)
    
    def mask_sensitive_data(self, data: Any) -> Any:
        """Public method to mask sensitive data."""
        return self._mask_sensitive_data(data)
    
    def cleanup_old_logs(self, days: int = None):
        """Clean up log files older than specified days."""
        if days is None:
            days = self.config.get('retention_days', 90)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        try:
            for log_file in self.log_dir.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_count += 1
            
            self.log_system(f"Cleaned up {cleaned_count} old log files", 
                          action="LOG_CLEANUP", days=days, files_removed=cleaned_count)
        except Exception as e:
            self.log_error(e, context="log_cleanup")


# Global instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions for quick access
def log_system(message: str, **kwargs):
    """Quick access to system logging."""
    get_audit_logger().log_system(message, **kwargs)

def log_database(table: str, operation: str, **kwargs):
    """Quick access to database logging."""
    get_audit_logger().log_database_operation(table, operation, **kwargs)

def log_error(exception: Exception, context: str = None, **kwargs):
    """Quick access to error logging."""
    get_audit_logger().log_error(exception, context, **kwargs)

def log_prediction(input_params: Dict, output_probability: float, **kwargs):
    """Quick access to prediction logging."""
    get_audit_logger().log_prediction(input_params, output_probability, **kwargs)

def log_file_operation(operation: str, filename: str, **kwargs):
    """Quick access to file operation logging."""
    get_audit_logger().log_file_operation(operation, filename, **kwargs)

