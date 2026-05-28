"""
core/security.py
================
Input sanitization and validation layer for PetroFlow.

Compliance:
  - OWASP ASVS 5.2 (Sanitization and Sandboxing)
  - OWASP Top 10 A03:2021 (Injection)
  - OWASP Top 10 A07:2021 (Identification and Authentication Failures)

All public-facing data entry points must pass through this module before
reaching the database layer or ML pipeline.
"""

import re
import html
import logging
from pathlib import Path
from typing import Any, Union

from .settings import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# SQL Injection patterns (defence-in-depth — SQLAlchemy ORM is primary guard) #
# --------------------------------------------------------------------------- #
_SQL_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"('|--|;|/\*|\*/|xp_|EXEC\s|EXECUTE\s|INSERT\s|UPDATE\s|"
               r"DELETE\s|DROP\s|ALTER\s|CREATE\s|UNION\s|SELECT\s)", re.IGNORECASE),
]

# --------------------------------------------------------------------------- #
# XSS patterns                                                                 #
# --------------------------------------------------------------------------- #
_XSS_PATTERNS: list[re.Pattern] = [
    re.compile(r"<[^>]*>"),                               # any HTML tag
    re.compile(r"javascript\s*:", re.IGNORECASE),         # JS URI
    re.compile(r"on\w+\s*=", re.IGNORECASE),              # event handlers
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),   # data URIs
]

# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

class ValidationError(ValueError):
    """Raised when user input fails security validation."""


def sanitize_text(
    value: str,
    field_name: str = "field",
    max_length: int = 1000,
    allow_html: bool = False,
) -> str:
    """
    Sanitize a free-text string against SQL injection and XSS.

    Args:
        value:      Raw input string from user.
        field_name: Name used in error messages.
        max_length: Maximum allowed character count.
        allow_html: If False (default), HTML entities are escaped.

    Returns:
        Cleaned string safe for storage and display.

    Raises:
        ValidationError: If the value contains injection patterns.
    """
    if not isinstance(value, str):
        value = str(value)

    # Strip leading/trailing whitespace
    value = value.strip()

    # Length guard
    if len(value) > max_length:
        raise ValidationError(
            f"'{field_name}' exceeds maximum length of {max_length} characters."
        )

    # SQL injection detection
    for pattern in _SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            logger.warning(
                "SQL injection pattern detected in field '%s': %.50r",
                field_name, value,
            )
            raise ValidationError(
                f"'{field_name}' contains disallowed characters or keywords."
            )

    # XSS detection / mitigation
    for pattern in _XSS_PATTERNS:
        if pattern.search(value):
            if allow_html:
                # Escape rather than reject when HTML is expected (e.g. notes)
                value = html.escape(value)
                break
            logger.warning(
                "XSS pattern detected in field '%s': %.50r", field_name, value
            )
            raise ValidationError(
                f"'{field_name}' contains disallowed HTML or script content."
            )

    return value


def sanitize_dict(
    data: dict[str, Any],
    text_fields: list[str] | None = None,
    max_length: int = 500,
) -> dict[str, Any]:
    """
    Sanitize every string field in a dictionary.

    Args:
        data:         Input dictionary (e.g. form submission).
        text_fields:  Keys to sanitize; if None, all string values are processed.
        max_length:   Per-field maximum length.

    Returns:
        New dictionary with sanitized values.
    """
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            if text_fields is None or key in text_fields:
                clean[key] = sanitize_text(value, field_name=key, max_length=max_length)
            else:
                clean[key] = value
        else:
            clean[key] = value
    return clean


def validate_file_upload(
    filename: str,
    file_size_bytes: int,
    content_bytes: bytes | None = None,
) -> None:
    """
    Validate an uploaded file against security policy.

    Checks:
      1. Extension is in the allowlist (no path traversal).
      2. File size is within configured limit.
      3. Basic magic-byte check for Excel and CSV (when content provided).

    Args:
        filename:       Original filename from the upload.
        file_size_bytes: Size in bytes.
        content_bytes:  Optional raw bytes for magic-byte validation.

    Raises:
        ValidationError: On policy violation.
    """
    # --- Path traversal prevention -------------------------------------------
    safe_name = Path(filename).name  # strips directory components
    if safe_name != filename:
        raise ValidationError(
            "Filename contains path traversal characters."
        )

    # --- Extension allowlist --------------------------------------------------
    extension = Path(safe_name).suffix.lstrip(".").lower()
    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(
            f"File type '.{extension}' is not permitted. "
            f"Allowed: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )

    # --- Size limit -----------------------------------------------------------
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValidationError(
            f"File size ({file_size_bytes / 1_048_576:.1f} MB) exceeds "
            f"the {MAX_FILE_SIZE_MB} MB limit."
        )

    # --- Magic bytes (OWASP: verify actual content type) ---------------------
    if content_bytes is not None:
        _validate_magic_bytes(extension, content_bytes[:16], filename)


# --------------------------------------------------------------------------- #
# Magic byte signatures                                                         #
# --------------------------------------------------------------------------- #
_MAGIC_BYTES: dict[str, list[bytes]] = {
    # xlsx = PKZIP (Office Open XML)
    "xlsx": [b"PK\x03\x04"],
    # csv = plain text — check no NUL bytes (binary disguised as csv)
    "csv": [],
    # glTF JSON
    "gltf": [b"{"],
    # GLB binary container
    "glb": [b"glTF"],
}


def _validate_magic_bytes(extension: str, header: bytes, filename: str) -> None:
    signatures = _MAGIC_BYTES.get(extension)
    if signatures is None:
        return  # unknown extension already rejected above

    if extension == "csv":
        # CSV has no magic bytes — just reject binary content
        if b"\x00" in header:
            raise ValidationError(
                f"'{filename}' appears to be a binary file, not a CSV."
            )
        return

    if signatures and not any(header.startswith(sig) for sig in signatures):
        raise ValidationError(
            f"'{filename}' content does not match the declared file type "
            f"'.{extension}'."
        )


# --------------------------------------------------------------------------- #
# Numeric / sensor parameter validation                                        #
# --------------------------------------------------------------------------- #

def validate_sensor_parameter(name: str, value: float) -> float:
    """
    Validate a physical sensor reading against known physical bounds.
    Prevents garbage data from entering the ML pipeline.

    Args:
        name:  Parameter name.
        value: Measured value.

    Returns:
        The original value if valid.

    Raises:
        ValidationError: If the value is outside the physical envelope.
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"Parameter '{name}' must be numeric.")

    # Deferred import to avoid circular dependency
    from core.physical_validator import validate_single
    result = validate_single(name, float(value))
    
    if result.blocked:
        raise ValidationError(result.issues[0].message)
        
    return float(value)


def validate_sensor_payload(payload: dict[str, float]) -> dict[str, float]:
    """
    Validate a complete sensor payload dictionary.
    Suitable for use at the MQTT ingestion boundary.

    Args:
        payload: {parameter_name: measured_value}

    Returns:
        Cleaned payload with all values cast to float.

    Raises:
        ValidationError: On the first invalid parameter.
    """
    return {k: validate_sensor_parameter(k, v) for k, v in payload.items()}


# --------------------------------------------------------------------------- #
# Role-Based Access Control (RBAC) - IEC 62443                                 #
# --------------------------------------------------------------------------- #

# IEC 62443 standard roles
VALID_ROLES = {"viewer", "analyst", "engineer", "admin"}

# Permission matrix maps actions to minimum required role
# Precedence: admin > engineer > analyst > viewer
_ROLE_HIERARCHY = {
    "admin": 4,
    "engineer": 3,
    "analyst": 2,
    "viewer": 1,
}

_PERMISSION_MATRIX = {
    "view_dashboard": "viewer",
    "view_alarms": "viewer",
    "acknowledge_alarms": "analyst",
    "shelve_alarms": "engineer",
    "modify_setpoints": "engineer",
    "train_models": "engineer",
    "manage_users": "admin",
    "export_audit_logs": "admin",
}

class AuthorizationError(Exception):
    """Raised when a user attempts an action without sufficient privileges."""
    pass

def check_permission(user_role: str, action: str) -> bool:
    """
    Check if the user's role has permission to perform the action.
    
    Args:
        user_role: Role of the user (e.g., 'viewer', 'engineer')
        action: Action being attempted
        
    Returns:
        bool: True if authorized, False otherwise
    """
    if user_role not in VALID_ROLES:
        logger.warning("Invalid role checked: %s", user_role)
        return False
        
    required_role = _PERMISSION_MATRIX.get(action)
    if not required_role:
        logger.error("Unknown action checked: %s", action)
        return False
        
    user_level = _ROLE_HIERARCHY.get(user_role, 0)
    required_level = _ROLE_HIERARCHY.get(required_role, 99)
    
    if user_level >= required_level:
        return True
        
    logger.warning("Access denied: User with role '%s' attempted '%s'", user_role, action)
    return False

def require_permission(user_role: str, action: str) -> None:
    """
    Enforce permission check, raising AuthorizationError if denied.
    """
    if not check_permission(user_role, action):
        raise AuthorizationError(
            f"Action '{action}' requires at least '{_PERMISSION_MATRIX.get(action)}' privileges."
        )
