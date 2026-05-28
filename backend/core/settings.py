"""
core/settings.py
================
Central configuration loader for PetroFlow.

Replaces hard-coded values in modules/config.py with environment-variable
driven settings.  Uses python-dotenv to load .env on startup.

Security compliance:
  - ISO/IEC 27001 A.9.4 (information access restriction)
  - OWASP ASVS 2.10 (service authentication secrets)
  - Zero hard-coded secrets: every sensitive value is mandatory env var
    in production (APP_ENV=production) and fails fast with a clear error.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Load .env before any other import accesses os.environ
try:
    from dotenv import load_dotenv
    # Walk up from this file to find .env at project root
    _project_root = Path(__file__).resolve().parent.parent
    _env_path = _project_root / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    # python-dotenv not installed — acceptable in pure-container deployments
    # where env vars are injected by the orchestrator (ECS task def, Cloud Run)
    pass

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _require(key: str) -> str:
    """
    Return env var value.  In production (APP_ENV=production) the process
    exits with exit code 1 if the variable is missing or empty.
    In development a warning is emitted instead.
    """
    value = os.environ.get(key, "").strip()
    if not value:
        env = os.environ.get("APP_ENV", "development")
        if env == "production":
            print(
                f"[PetroFlow] FATAL: Required environment variable '{key}' "
                f"is not set. Refusing to start in production mode.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            logger.warning(
                "Environment variable '%s' is not set (acceptable in development).", key
            )
    return value


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_bool(key: str, default: bool = False) -> bool:
    return _get(key, str(default)).lower() in ("1", "true", "yes", "on")


def _get_int(key: str, default: int = 0) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default


# --------------------------------------------------------------------------- #
# Application                                                                  #
# --------------------------------------------------------------------------- #
APP_ENV: str = _get("APP_ENV", "development")
APP_VERSION: str = _get("APP_VERSION", "1.0.0")
IS_PRODUCTION: bool = APP_ENV == "production"

# Mandatory in production — used for session signing and CSRF tokens
SECRET_KEY: str = _require("SECRET_KEY") if IS_PRODUCTION else _get(
    "SECRET_KEY", "dev-insecure-key-do-not-use-in-prod"
)

# --------------------------------------------------------------------------- #
# Database — local SQLite                                                      #
# --------------------------------------------------------------------------- #
DATABASE_PATH: str = _get("DATABASE_PATH", "petroflow.db")
STORAGE_BASE_DIR: Path = Path(_get("STORAGE_BASE_DIR", "storage"))

# --------------------------------------------------------------------------- #
# Supabase — cloud PostgreSQL + auth (production only)                        #
# --------------------------------------------------------------------------- #
SUPABASE_URL: Optional[str] = _get("SUPABASE_URL") or None
SUPABASE_ANON_KEY: Optional[str] = _get("SUPABASE_ANON_KEY") or None

# service_role key: NEVER expose to frontend — server-side only
_SUPABASE_SERVICE_KEY: Optional[str] = _get("SUPABASE_SERVICE_ROLE_KEY") or None

SUPABASE_JWT_SECRET: Optional[str] = _get("SUPABASE_JWT_SECRET") or None
SUPABASE_DATABASE_URL: Optional[str] = _get("SUPABASE_DATABASE_URL") or None

# Multi-tenant isolation — used by RLS policies
COMPANY_ID: Optional[str] = _get("COMPANY_ID") or None

# In production, Supabase vars are mandatory
if IS_PRODUCTION:
    for _var, _val in [
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY),
        ("SUPABASE_SERVICE_ROLE_KEY", _SUPABASE_SERVICE_KEY),
        ("SUPABASE_JWT_SECRET", SUPABASE_JWT_SECRET),
        ("COMPANY_ID", COMPANY_ID),
    ]:
        if not _val:
            print(
                f"[PetroFlow] FATAL: '{_var}' is required in production.",
                file=sys.stderr,
            )
            sys.exit(1)

# Expose service key only through a controlled accessor — prevents
# accidental logging or serialisation of the raw string.
def get_supabase_service_key() -> Optional[str]:
    """Return the Supabase service-role key.  Call only in server-side code."""
    return _SUPABASE_SERVICE_KEY


# --------------------------------------------------------------------------- #
# MQTT                                                                         #
# --------------------------------------------------------------------------- #
MQTT_BROKER_HOST: str = _get("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT: int = _get_int("MQTT_BROKER_PORT", 1883)
MQTT_USERNAME: Optional[str] = _get("MQTT_USERNAME") or None
MQTT_PASSWORD: Optional[str] = _get("MQTT_PASSWORD") or None
MQTT_USE_TLS: bool = _get_bool("MQTT_USE_TLS", False)
MQTT_TLS_VERSION: str = _get("MQTT_TLS_VERSION", "TLSv1.3")
MQTT_CA_CERT_PATH: Optional[str] = _get("MQTT_CA_CERT_PATH") or None
MQTT_CLIENT_CERT_PATH: Optional[str] = _get("MQTT_CLIENT_CERT_PATH") or None
MQTT_CLIENT_KEY_PATH: Optional[str] = _get("MQTT_CLIENT_KEY_PATH") or None

# --------------------------------------------------------------------------- #
# Logging                                                                      #
# --------------------------------------------------------------------------- #
LOG_LEVEL: str = _get("LOG_LEVEL", "INFO")
LOG_DIR: Path = Path(_get("LOG_DIR", "logs"))
LOG_FILE: str = _get("LOG_FILE", "petroflow.log")
STRUCTURED_LOGGING: bool = _get_bool("STRUCTURED_LOGGING", True)
ASYNC_LOGGING: bool = _get_bool("ASYNC_LOGGING", True)
AUDIT_LOG_RETENTION_DAYS: int = _get_int("AUDIT_LOG_RETENTION_DAYS", 365)

# --------------------------------------------------------------------------- #
# Security controls                                                            #
# --------------------------------------------------------------------------- #
MAX_FILE_SIZE_MB: int = _get_int("MAX_FILE_SIZE_MB", 50)
ALLOWED_FILE_EXTENSIONS: list[str] = [
    ext.strip().lower()
    for ext in _get("ALLOWED_FILE_EXTENSIONS", "xlsx,csv,gltf,glb").split(",")
    if ext.strip()
]
RATE_LIMIT_PER_MINUTE: int = _get_int("RATE_LIMIT_PER_MINUTE", 60)
CORS_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in _get("CORS_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
CSP_POLICY: str = _get(
    "CSP_POLICY",
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
)

# --------------------------------------------------------------------------- #
# Application constants (non-sensitive)                                        #
# --------------------------------------------------------------------------- #
DEFAULT_SAFETY_FACTOR: int = 20
OPTIMAL_RPM: int = 2500
RISK_LOW_THRESHOLD: int = 30
RISK_HIGH_THRESHOLD: int = 70

# ML normalisation
TEMP_MAX: int = 150
PRESSURE_MAX: int = 50
VIBRATION_MAX: int = 10
HOURS_MAX: int = 20000
RPM_MAX: int = 5000
