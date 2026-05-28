"""
Structured Logger Utility
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Provides structured JSON logging for decisions, validations, optimizations, and anomalies.
Integrates with Python's logging module for consistent log formatting.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log categories for structured logging."""
    DECISION = "decision"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    ANOMALY = "anomaly"
    SIMULATION = "simulation"
    TELEMETRY = "telemetry"
    PERFORMANCE = "performance"
    AUDIT = "audit"


class StructuredLogger:
    """
    Structured logger for Petroflow operations.
    
    Features:
    - JSON-formatted log entries
    - Categorized logging (decision, validation, optimization, anomaly)
    - Contextual metadata
    - Performance metrics
    - Audit trail support
    """
    
    def __init__(
        self,
        name: str,
        enable_console: bool = True,
        enable_file: bool = True,
        log_file: Optional[str] = None
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically module name)
            enable_console: Enable console output
            enable_file: Enable file output
            log_file: Path to log file (None = use default)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Console handler
            if enable_console:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.INFO)
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)
            
            # File handler
            if enable_file:
                file_path = log_file or "logs/structured.log"
                try:
                    file_handler = logging.FileHandler(file_path)
                    file_handler.setLevel(logging.DEBUG)
                    file_formatter = logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                    file_handler.setFormatter(file_formatter)
                    self.logger.addHandler(file_handler)
                except Exception as e:
                    print(f"Warning: Could not create file handler: {e}")
    
    def _create_log_entry(
        self,
        category: LogCategory,
        message: str,
        context: Dict[str, Any],
        level: LogLevel = LogLevel.INFO
    ) -> Dict[str, Any]:
        """
        Create structured log entry.
        
        Args:
            category: Log category
            message: Log message
            context: Contextual data
            level: Log level
            
        Returns:
            Structured log entry as dictionary
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "category": category.value,
            "message": message,
            "context": context
        }
        return entry
    
    def _log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        context: Dict[str, Any]
    ):
        """
        Internal logging method.
        
        Args:
            level: Log level
            category: Log category
            message: Log message
            context: Contextual data
        """
        entry = self._create_log_entry(category, message, context, level)
        json_entry = json.dumps(entry)
        
        # Log at appropriate level
        if level == LogLevel.DEBUG:
            self.logger.debug(json_entry)
        elif level == LogLevel.INFO:
            self.logger.info(json_entry)
        elif level == LogLevel.WARNING:
            self.logger.warning(json_entry)
        elif level == LogLevel.ERROR:
            self.logger.error(json_entry)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(json_entry)
    
    def log_decision(
        self,
        decision_type: str,
        equipment_id: str,
        decision: str,
        rationale: str,
        parameters: Dict[str, Any],
        outcome: Optional[str] = None,
        confidence: Optional[float] = None
    ):
        """
        Log a decision made by the system.
        
        Args:
            decision_type: Type of decision (e.g., "optimization", "safety_action")
            equipment_id: Equipment identifier
            decision: The decision made
            rationale: Reasoning behind the decision
            parameters: Parameters involved in decision
            outcome: Expected or actual outcome
            confidence: Confidence level (0.0 to 1.0)
        """
        context = {
            "decision_type": decision_type,
            "equipment_id": equipment_id,
            "decision": decision,
            "rationale": rationale,
            "parameters": parameters,
            "outcome": outcome,
            "confidence": confidence
        }
        
        self._log(
            LogLevel.INFO,
            LogCategory.DECISION,
            f"Decision: {decision_type} for {equipment_id}",
            context
        )
    
    def log_validation(
        self,
        equipment_id: str,
        validation_type: str,
        status: str,
        parameters_checked: List[str],
        violations: List[str],
        safety_margins: Dict[str, float],
        duration_ms: float
    ):
        """
        Log a validation operation.
        
        Args:
            equipment_id: Equipment identifier
            validation_type: Type of validation (e.g., "safety_envelope")
            status: Validation status (e.g., "OK", "WARNING", "ALARM")
            parameters_checked: List of parameters validated
            violations: List of violations found
            safety_margins: Safety margins for each parameter
            duration_ms: Validation duration in milliseconds
        """
        context = {
            "equipment_id": equipment_id,
            "validation_type": validation_type,
            "status": status,
            "parameters_checked": parameters_checked,
            "violations": violations,
            "safety_margins": safety_margins,
            "duration_ms": duration_ms
        }
        
        level = LogLevel.INFO
        if status in ["ALARM", "CRITICAL"]:
            level = LogLevel.ERROR
        elif status == "WARNING":
            level = LogLevel.WARNING
        
        self._log(
            level,
            LogCategory.VALIDATION,
            f"Validation: {validation_type} for {equipment_id} - {status}",
            context
        )
    
    def log_optimization(
        self,
        equipment_id: str,
        optimization_type: str,
        original_parameters: Dict[str, float],
        optimized_parameters: Dict[str, float],
        efficiency_improvement: float,
        energy_savings: float,
        recommendations: List[str],
        duration_ms: float
    ):
        """
        Log an optimization operation.
        
        Args:
            equipment_id: Equipment identifier
            optimization_type: Type of optimization
            original_parameters: Original operating parameters
            optimized_parameters: Optimized parameters
            efficiency_improvement: Efficiency improvement percentage
            energy_savings: Energy savings (kW)
            recommendations: Optimization recommendations
            duration_ms: Optimization duration in milliseconds
        """
        context = {
            "equipment_id": equipment_id,
            "optimization_type": optimization_type,
            "original_parameters": original_parameters,
            "optimized_parameters": optimized_parameters,
            "efficiency_improvement": efficiency_improvement,
            "energy_savings": energy_savings,
            "recommendations": recommendations,
            "duration_ms": duration_ms
        }
        
        self._log(
            LogLevel.INFO,
            LogCategory.OPTIMIZATION,
            f"Optimization: {optimization_type} for {equipment_id} - {efficiency_improvement:.2f}% improvement",
            context
        )
    
    def log_anomaly(
        self,
        equipment_id: str,
        parameter: str,
        anomaly_type: str,
        severity: str,
        value: float,
        expected_value: float,
        deviation: float,
        z_score: float,
        confidence: float,
        recommended_action: Optional[str] = None
    ):
        """
        Log an anomaly detection.
        
        Args:
            equipment_id: Equipment identifier
            parameter: Parameter with anomaly
            anomaly_type: Type of anomaly (e.g., "statistical", "threshold")
            severity: Severity level (e.g., "low", "medium", "high", "critical")
            value: Actual value
            expected_value: Expected value
            deviation: Deviation from expected
            z_score: Statistical z-score
            confidence: Detection confidence (0.0 to 1.0)
            recommended_action: Recommended action to take
        """
        context = {
            "equipment_id": equipment_id,
            "parameter": parameter,
            "anomaly_type": anomaly_type,
            "severity": severity,
            "value": value,
            "expected_value": expected_value,
            "deviation": deviation,
            "z_score": z_score,
            "confidence": confidence,
            "recommended_action": recommended_action
        }
        
        level = LogLevel.WARNING
        if severity == "critical":
            level = LogLevel.CRITICAL
        elif severity == "high":
            level = LogLevel.ERROR
        
        self._log(
            level,
            LogCategory.ANOMALY,
            f"Anomaly: {parameter} on {equipment_id} - {severity} severity",
            context
        )
    
    def log_simulation(
        self,
        simulation_id: str,
        simulation_type: str,
        equipment_ids: List[str],
        duration_ms: float,
        status: str,
        results_summary: Dict[str, Any],
        errors: Optional[List[str]] = None
    ):
        """
        Log a simulation operation.
        
        Args:
            simulation_id: Simulation identifier
            simulation_type: Type of simulation
            equipment_ids: List of equipment involved
            duration_ms: Simulation duration in milliseconds
            status: Simulation status (e.g., "completed", "failed")
            results_summary: Summary of simulation results
            errors: List of errors encountered
        """
        context = {
            "simulation_id": simulation_id,
            "simulation_type": simulation_type,
            "equipment_ids": equipment_ids,
            "equipment_count": len(equipment_ids),
            "duration_ms": duration_ms,
            "status": status,
            "results_summary": results_summary,
            "errors": errors or []
        }
        
        level = LogLevel.INFO if status == "completed" else LogLevel.ERROR
        
        self._log(
            level,
            LogCategory.SIMULATION,
            f"Simulation: {simulation_type} ({simulation_id}) - {status}",
            context
        )
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        throughput: Optional[float] = None,
        resource_usage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log performance metrics.
        
        Args:
            operation: Operation name
            duration_ms: Operation duration in milliseconds
            throughput: Throughput metric (e.g., points/sec)
            resource_usage: Resource usage metrics
            metadata: Additional metadata
        """
        context = {
            "operation": operation,
            "duration_ms": duration_ms,
            "throughput": throughput,
            "resource_usage": resource_usage or {},
            "metadata": metadata or {}
        }
        
        self._log(
            LogLevel.INFO,
            LogCategory.PERFORMANCE,
            f"Performance: {operation} - {duration_ms:.2f}ms",
            context
        )
    
    def log_audit(
        self,
        user_id: Optional[str],
        action: str,
        resource: str,
        resource_id: str,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        success: bool = True
    ):
        """
        Log an audit trail entry.
        
        Args:
            user_id: User identifier (None for system actions)
            action: Action performed (e.g., "create", "update", "delete")
            resource: Resource type (e.g., "equipment", "simulation")
            resource_id: Resource identifier
            changes: Changes made (before/after)
            ip_address: IP address of requester
            success: Whether action was successful
        """
        context = {
            "user_id": user_id or "system",
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "changes": changes or {},
            "ip_address": ip_address,
            "success": success
        }
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        
        self._log(
            level,
            LogCategory.AUDIT,
            f"Audit: {action} {resource}/{resource_id} by {user_id or 'system'}",
            context
        )
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        stack_trace: Optional[str] = None
    ):
        """
        Log an error with context.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Error context
            stack_trace: Stack trace if available
        """
        error_context = {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            **context
        }
        
        self._log(
            LogLevel.ERROR,
            LogCategory.AUDIT,
            f"Error: {error_type} - {error_message}",
            error_context
        )


# Singleton instance for global access
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "petroflow") -> StructuredLogger:
    """
    Get or create global structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger


# Export main classes
__all__ = [
    "StructuredLogger",
    "LogLevel",
    "LogCategory",
    "get_logger"
]