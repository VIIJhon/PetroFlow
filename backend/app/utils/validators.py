"""
Custom Validators
Pydantic validators and validation utilities for the application
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import validator


# Regular expressions for validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
TAG_REGEX = re.compile(r'^[A-Z0-9-]{3,20}$')
PHONE_REGEX = re.compile(r'^\+?1?\d{9,15}$')


def validate_email(email: str) -> bool:
    """Validate email format"""
    return bool(EMAIL_REGEX.match(email))


def validate_username(username: str) -> bool:
    """Validate username format"""
    return bool(USERNAME_REGEX.match(username))


def validate_equipment_tag(tag: str) -> bool:
    """Validate equipment tag format (uppercase alphanumeric with hyphens)"""
    return bool(TAG_REGEX.match(tag))


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    return bool(PHONE_REGEX.match(phone))


def validate_password_strength(password: str) -> tuple[bool, List[str]]:
    """
    Validate password strength.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        issues.append("Password should contain at least one special character")
    
    return len(issues) == 0, issues


def validate_date_range(start_date: datetime, end_date: datetime, max_days: int = 365) -> tuple[bool, Optional[str]]:
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
        max_days: Maximum allowed days in range
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if start_date > end_date:
        return False, "Start date must be before end date"
    
    if end_date > datetime.now():
        return False, "End date cannot be in the future"
    
    delta = end_date - start_date
    if delta.days > max_days:
        return False, f"Date range cannot exceed {max_days} days"
    
    return True, None


def validate_numeric_range(value: float, min_val: float, max_val: float, field_name: str = "Value") -> tuple[bool, Optional[str]]:
    """
    Validate numeric value is within range.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value < min_val:
        return False, f"{field_name} must be at least {min_val}"
    
    if value > max_val:
        return False, f"{field_name} must not exceed {max_val}"
    
    return True, None


def validate_sensor_value(sensor_type: str, value: float, unit: str) -> tuple[bool, Optional[str]]:
    """
    Validate sensor value based on type and unit.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    validations = {
        "temperature": {
            "celsius": (-273.15, 1000),
            "fahrenheit": (-459.67, 1832),
            "kelvin": (0, 1273.15)
        },
        "pressure": {
            "bar": (0, 1000),
            "psi": (0, 15000),
            "pa": (0, 100000000)
        },
        "vibration": {
            "mm/s": (0, 100),
            "in/s": (0, 4),
            "g": (0, 50)
        },
        "flow": {
            "m3/h": (0, 10000),
            "l/min": (0, 100000),
            "gpm": (0, 50000)
        },
        "speed": {
            "rpm": (0, 50000),
            "rad/s": (0, 5000)
        }
    }
    
    sensor_type_lower = sensor_type.lower()
    unit_lower = unit.lower()
    
    if sensor_type_lower not in validations:
        return True, None  # Unknown sensor type, skip validation
    
    if unit_lower not in validations[sensor_type_lower]:
        return False, f"Invalid unit '{unit}' for sensor type '{sensor_type}'"
    
    min_val, max_val = validations[sensor_type_lower][unit_lower]
    return validate_numeric_range(value, min_val, max_val, f"{sensor_type} value")


def validate_equipment_parameters(equipment_type: str, parameters: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate equipment parameters based on equipment type.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    required_params = {
        "pump": ["rated_flow", "rated_head", "rated_power"],
        "compressor": ["rated_capacity", "discharge_pressure", "rated_power"],
        "turbine": ["rated_power", "rated_speed"],
        "heat_exchanger": ["heat_transfer_area", "design_pressure"],
        "valve": ["cv_value", "design_pressure"],
        "separator": ["design_pressure", "design_temperature", "capacity"],
        "vessel": ["design_pressure", "design_temperature", "volume"]
    }
    
    if equipment_type.lower() in required_params:
        for param in required_params[equipment_type.lower()]:
            if param not in parameters:
                issues.append(f"Missing required parameter: {param}")
    
    # Validate numeric parameters are positive
    for key, value in parameters.items():
        if isinstance(value, (int, float)) and value < 0:
            issues.append(f"Parameter '{key}' must be non-negative")
    
    return len(issues) == 0, issues


def validate_simulation_parameters(simulation_type: str, parameters: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate simulation parameters based on simulation type.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    required_params = {
        "steady_state": ["operating_point"],
        "transient": ["initial_conditions", "simulation_time"],
        "what_if": ["vibration", "temperature", "rpm"],
        "optimization": ["objective", "constraints"]
    }
    
    if simulation_type in required_params:
        for param in required_params[simulation_type]:
            if param not in parameters:
                issues.append(f"Missing required parameter for {simulation_type}: {param}")
    
    # Validate what-if parameters
    if simulation_type == "what_if":
        if "vibration" in parameters:
            is_valid, error = validate_numeric_range(parameters["vibration"], 0, 100, "Vibration")
            if not is_valid:
                issues.append(error)
        
        if "temperature" in parameters:
            is_valid, error = validate_numeric_range(parameters["temperature"], -50, 500, "Temperature")
            if not is_valid:
                issues.append(error)
        
        if "rpm" in parameters:
            is_valid, error = validate_numeric_range(parameters["rpm"], 0, 50000, "RPM")
            if not is_valid:
                issues.append(error)
    
    return len(issues) == 0, issues


def validate_file_size(file_size: int, max_size_mb: int = 10) -> tuple[bool, Optional[str]]:
    """
    Validate file size.
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum allowed size in MB
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        return False, f"File size exceeds maximum allowed size of {max_size_mb}MB"
    
    return True, None


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> tuple[bool, Optional[str]]:
    """
    Validate file extension.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    if extension not in [ext.lower() for ext in allowed_extensions]:
        return False, f"File extension must be one of: {', '.join(allowed_extensions)}"
    
    return True, None


def validate_json_structure(data: Dict[str, Any], required_keys: List[str]) -> tuple[bool, List[str]]:
    """
    Validate JSON structure has required keys.
    
    Returns:
        Tuple of (is_valid, list_of_missing_keys)
    """
    missing_keys = [key for key in required_keys if key not in data]
    return len(missing_keys) == 0, missing_keys


def validate_time_interval(interval: str) -> tuple[bool, Optional[str]]:
    """
    Validate time interval format (e.g., '1h', '30m', '7d').
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    pattern = re.compile(r'^(\d+)([smhd])$')
    match = pattern.match(interval)
    
    if not match:
        return False, "Invalid time interval format. Use format like '1h', '30m', '7d'"
    
    value, unit = match.groups()
    value = int(value)
    
    if value <= 0:
        return False, "Time interval value must be positive"
    
    # Check reasonable limits
    limits = {'s': 86400, 'm': 1440, 'h': 168, 'd': 365}  # max seconds, minutes, hours, days
    if value > limits[unit]:
        return False, f"Time interval too large. Maximum for '{unit}' is {limits[unit]}"
    
    return True, None


def sanitize_string(text: str, max_length: int = 255) -> str:
    """
    Sanitize string input by removing potentially harmful characters.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Trim to max length
    text = text[:max_length]
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_coordinates(latitude: float, longitude: float) -> tuple[bool, Optional[str]]:
    """
    Validate geographic coordinates.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not -90 <= latitude <= 90:
        return False, "Latitude must be between -90 and 90"
    
    if not -180 <= longitude <= 180:
        return False, "Longitude must be between -180 and 180"
    
    return True, None