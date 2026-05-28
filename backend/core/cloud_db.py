"""
Cloud Database Module
Handles Supabase integration for cloud persistence of simulation results.
The supabase SDK import is lazy so the application works even when the package
is not installed in the current environment.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_SUPABASE_AVAILABLE = False
try:
    from supabase import create_client, Client  # type: ignore
    _SUPABASE_AVAILABLE = True
except ImportError:
    logger.warning(
        "supabase-py package not installed. Cloud DB features will be disabled. "
        "Install with: pip install supabase"
    )


def _get_supabase_config():
    """Return (SUPABASE_URL, SUPABASE_ANON_KEY) from settings, or (None, None)."""
    try:
        from core.settings import SUPABASE_URL, SUPABASE_ANON_KEY
        return SUPABASE_URL, SUPABASE_ANON_KEY
    except Exception:
        return None, None


def get_authenticated_client(access_token: str):
    """
    Creates a Supabase client authenticated as the calling user.
    Row-Level Security (RLS) policies are enforced natively via the JWT.

    Returns None if the supabase SDK is not available.
    """
    if not _SUPABASE_AVAILABLE:
        logger.warning("Supabase SDK not available. Cannot create authenticated client.")
        return None

    url, key = _get_supabase_config()
    if not url or not key:
        raise ValueError("Supabase configuration missing in environment (.env).")

    supabase = create_client(url, key)
    supabase.postgrest.auth(access_token)
    return supabase


def save_simulation_result(
    access_token: str,
    equipment_id: str,
    sim_vib: float,
    sim_temp: float,
    sim_rpm: float,
    baseline_health: float,
    simulated_health: float,
    is_stressed: bool,
):
    """
    Save a What-If simulation result to the Supabase cloud database.

    Returns the inserted row data on success, or None on failure / when the
    Supabase SDK is not available.
    """
    if not _SUPABASE_AVAILABLE:
        logger.warning("Cloud save skipped: supabase-py not installed.")
        return None

    try:
        client = get_authenticated_client(access_token)
        if client is None:
            return None

        data = {
            "equipment_id": equipment_id,
            "estado": "what_if_simulation",
            "descripcion": (
                f"What-If simulation — equipment: {equipment_id}, "
                f"vib={sim_vib:.2f} mm/s, temp={sim_temp:.1f} C, rpm={sim_rpm:.0f}. "
                f"Stressed={is_stressed}. "
                f"Baseline health={baseline_health:.1f}%, simulated={simulated_health:.1f}%."
            ),
            "fecha": datetime.now().isoformat(),
        }

        response = client.table("reportes_intervencion").insert(data).execute()
        logger.info(f"Simulation result saved for equipment {equipment_id}.")
        return response.data

    except Exception as e:
        logger.error(f"Failed to save simulation result to Cloud DB: {e}")
        return None

