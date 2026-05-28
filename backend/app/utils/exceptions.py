"""
Custom Exception Classes
Defines application-specific exceptions for better error handling
"""

from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class PetroFlowException(Exception):
    """Base exception for PetroFlow application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(PetroFlowException):
    """Exception for database-related errors"""
    pass


class ValidationException(PetroFlowException):
    """Exception for validation errors"""
    pass


class AuthenticationException(PetroFlowException):
    """Exception for authentication errors"""
    pass


class AuthorizationException(PetroFlowException):
    """Exception for authorization errors"""
    pass


class ResourceNotFoundException(PetroFlowException):
    """Exception when a resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: Any):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message, {"resource_type": resource_type, "resource_id": resource_id})


class ResourceAlreadyExistsException(PetroFlowException):
    """Exception when trying to create a resource that already exists"""
    
    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier '{identifier}' already exists"
        super().__init__(message, {"resource_type": resource_type, "identifier": identifier})


class SimulationException(PetroFlowException):
    """Exception for simulation-related errors"""
    pass


class AnalysisException(PetroFlowException):
    """Exception for analysis-related errors"""
    pass


class CalculationException(PetroFlowException):
    """Exception for calculation errors"""
    pass


class MQTTException(PetroFlowException):
    """Exception for MQTT-related errors"""
    pass


class ReportGenerationException(PetroFlowException):
    """Exception for report generation errors"""
    pass


class MLServiceException(PetroFlowException):
    """Exception for ML service errors"""
    pass


class ConfigurationException(PetroFlowException):
    """Exception for configuration errors"""
    pass


class ExternalServiceException(PetroFlowException):
    """Exception for external service integration errors"""
    pass


# HTTP Exception Helpers

def not_found_exception(resource_type: str, resource_id: Any) -> HTTPException:
    """Create HTTP 404 exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource_type} with ID {resource_id} not found"
    )


def bad_request_exception(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create HTTP 400 exception"""
    detail = {"message": message}
    if details:
        detail.update(details)
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail
    )


def unauthorized_exception(message: str = "Not authenticated") -> HTTPException:
    """Create HTTP 401 exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"}
    )


def forbidden_exception(message: str = "Not enough permissions") -> HTTPException:
    """Create HTTP 403 exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )


def conflict_exception(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create HTTP 409 exception"""
    detail = {"message": message}
    if details:
        detail.update(details)
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail
    )


def internal_server_exception(message: str = "Internal server error") -> HTTPException:
    """Create HTTP 500 exception"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )


def service_unavailable_exception(service_name: str) -> HTTPException:
    """Create HTTP 503 exception"""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"{service_name} service is currently unavailable"
    )


def validation_exception(errors: list) -> HTTPException:
    """Create HTTP 422 exception for validation errors"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=errors
    )


# Exception Handler Utilities

def handle_database_error(error: Exception) -> HTTPException:
    """Convert database errors to HTTP exceptions"""
    error_msg = str(error)
    
    if "unique constraint" in error_msg.lower():
        return conflict_exception("Resource already exists")
    elif "foreign key" in error_msg.lower():
        return bad_request_exception("Invalid reference to related resource")
    elif "not found" in error_msg.lower():
        return not_found_exception("Resource", "unknown")
    else:
        return internal_server_exception("Database operation failed")


def handle_service_error(error: Exception, service_name: str) -> HTTPException:
    """Convert service errors to HTTP exceptions"""
    if isinstance(error, PetroFlowException):
        return bad_request_exception(error.message, error.details)
    else:
        return internal_server_exception(f"{service_name} operation failed: {str(error)}")