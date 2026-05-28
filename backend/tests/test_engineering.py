"""
Unit tests for PetroFlow Advanced Engineering v2.0 solvers and API endpoints.
Verifies the physics and mathematical soundness of Beggs & Brill, Darcy-Weisbach,
Vogel IPR, Centrifugal Pump intersections, and high-frequency Fourier Transform (FFT) spectra.
Authored by PetroFlow Engineering Team
"""

import pytest
import math
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token

from core.hydraulic_engine import HydraulicEngine
from core.pump_engine import PumpEngine
from core.nodal_engine import NodalEngine
from core.fft_engine import FFTEngine


# -------------------------------------------------------------
# Test Database & Fixtures Setup (Self-Contained)
# -------------------------------------------------------------

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_engineering.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role=UserRole.ENGINEER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers."""
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


# -------------------------------------------------------------
# 1. Physics Engines Unit Tests
# -------------------------------------------------------------

def test_colebrook_white_solver():
    """Verifies that the Colebrook-White explicit Swamee-Jain solver calculates realistic friction factors."""
    # Laminar flow (Re = 1000) -> f = 64/Re = 0.064
    f_lam = HydraulicEngine.solve_colebrook_white(1000.0, 0.001)
    assert pytest.approx(f_lam, rel=1e-5) == 0.064
    
    # Turbulent flow (Re = 100,000, e/D = 0.0001) -> f approx 0.018
    f_turb = HydraulicEngine.solve_colebrook_white(100000.0, 0.0001)
    assert 0.015 < f_turb < 0.022


def test_single_phase_pressure_drop():
    """Verifies Darcy-Weisbach friction loss and static lift head loss."""
    res = HydraulicEngine.calculate_single_phase_pressure_drop(
        length_m=100.0,
        diameter_m=0.1,
        roughness_m=0.00005,
        flow_rate_m3s=0.02,  # ~2.55 m/s velocity
        density_kg_m3=1000.0, # water
        viscosity_pa_s=0.001,
        inclination_deg=0.0
    )
    assert res["reynolds"] > 10000.0
    assert res["velocity_m_s"] > 2.0
    assert res["friction_loss_pa"] > 0.0
    assert res["gravity_loss_pa"] == 0.0  # horizontal
    assert res["regime"] == "Turbulent"


def test_beggs_brill_multiphase():
    """Verifies that the Beggs & Brill correlation calculates a reasonable liquid holdup and pressure gradient."""
    res = HydraulicEngine.calculate_beggs_brill(
        length_m=1000.0,
        diameter_m=0.1524,  # 6 inches
        roughness_m=0.000045,
        liquid_rate_m3s=0.03,
        gas_rate_m3s=0.002,
        density_liquid_kg_m3=900.0,
        density_gas_kg_m3=1.2,
        viscosity_liquid_pa_s=0.015,  # 15 cP
        viscosity_gas_pa_s=0.000018,
        inclination_deg=2.0  # inclined uphill
    )
    assert 0.0 < res["liquid_holdup"] <= 1.0
    assert res["no_slip_holdup"] < res["liquid_holdup"]  # hold-up correction
    assert res["mixture_density_kg_m3"] > 10.0
    assert res["total_loss_pa"] > 0.0


def test_pump_operating_point():
    """Verifies Centrifugal Pump intersection and NPSH calculation."""
    # Solver
    q_op, h_op, converged = PumpEngine.calculate_operating_point(
        shut_off_head_m=120.0,
        pump_resistance_coeff=0.0004,
        static_lift_m=30.0,
        system_friction_coeff=0.0002
    )
    assert converged is True
    # H0 - A * Q^2 = dZ + C * Q^2
    # 120 - 0.0004 * Q^2 = 30 + 0.0002 * Q^2
    # 90 = 0.0006 * Q^2 -> Q^2 = 150000 -> Q = 387.3 m3/h
    assert pytest.approx(q_op, rel=1e-3) == 387.298
    assert pytest.approx(h_op, rel=1e-3) == 59.999
    
    # NPSHa
    npsha = PumpEngine.calculate_npsha(
        suction_pressure_abs_pa=180000.0,
        vapor_pressure_pa=30000.0,
        fluid_density_kg_m3=850.0,
        suction_loss_m=0.4
    )
    # (180k - 30k) / (850 * 9.80665) - 0.4 = 150k / 8335.65 - 0.4 = 17.99 - 0.4 = 17.59m
    assert 17.0 < npsha < 18.0


def test_multi_pump_curves():
    """Verifies heterogeneous pump layouts (Series/Parallel, Centrifugal and PD) operating point solutions."""
    # Arreglo 1: Dos centrífugas idénticas en Serie
    pumps_series = [
        {"id": "pump_a", "name": "Bomba A", "type": "centrifugal", "active": True, "shut_off_head_m": 120.0, "pump_resistance_coeff": 0.0004, "speed_pct": 100.0},
        {"id": "pump_b", "name": "Bomba B", "type": "centrifugal", "active": True, "shut_off_head_m": 120.0, "pump_resistance_coeff": 0.0004, "speed_pct": 100.0}
    ]
    res_series = PumpEngine.solve_multi_pump_curves(
        configuration="series",
        pumps=pumps_series,
        static_lift_m=30.0,
        system_friction_coeff=0.0002
    )
    assert res_series["converged"] is True
    # Combined shut-off = 240m, combined A = 0.0008
    # 240 - 0.0008*Q^2 = 30 + 0.0002*Q^2 -> 210 = 0.001*Q^2 -> Q^2 = 210000 -> Q = 458.25 m3/h
    assert pytest.approx(res_series["operating_flow_m3h"], rel=1e-3) == 458.257
    
    # Arreglo 2: Centrífuga y Desplazamiento Positivo en Serie
    pumps_mix_series = [
        {"id": "pump_a", "name": "Bomba A", "type": "centrifugal", "active": True, "shut_off_head_m": 120.0, "pump_resistance_coeff": 0.0004, "speed_pct": 100.0},
        {"id": "pump_pd", "name": "Bomba PD", "type": "positive_displacement", "active": True, "pd_flow_rate_m3h": 150.0, "relief_pressure_m": 200.0, "speed_pct": 100.0}
    ]
    res_mix = PumpEngine.solve_multi_pump_curves(
        configuration="series",
        pumps=pumps_mix_series,
        static_lift_m=30.0,
        system_friction_coeff=0.0002
    )
    # Caudal debe estar forzado a 150 m3/h
    assert pytest.approx(res_mix["operating_flow_m3h"]) == 150.0
    assert res_mix["psv_active"] is False


def test_nodal_analysis_vogel():
    """Verifies Vogel two-phase reservoir performance inflow intersects system lifting curves under flowing conditions."""
    res = NodalEngine.solve_nodal_intersection(
        reservoir_pressure_psi=3200.0,
        productivity_index_j=3.0,
        bubble_point_pressure_psi=1800.0,
        wellhead_pressure_psi=120.0,
        well_depth_ft=4500.0,  # shallower depth ensures well flows naturally
        water_cut_percent=30.0,
        gas_oil_ratio=200.0,
        oil_api=28.0,
        fluid_viscosity_cst=45.0
    )
    assert res["converged"] is True
    assert res["operating_flow_rate_bpd"] > 10.0
    assert res["operating_flowing_pressure_psi"] < 3200.0


def test_vibration_fft():
    """Verifies synthetic dynamic defects signal generator and real FFT spectrum calculations."""
    res = FFTEngine.generate_vibration_signal(
        rpm=3000.0,  # 50 Hz rotation
        vibration_level=2.5,
        defect_type="desalineacion",
        sampling_rate=1000,
        duration_seconds=1.0
    )
    assert len(res["time_series"]["time"]) == 400
    assert len(res["fft_spectrum"]["frequencies"]) == 501  # N/2 + 1 for N=1000
    # Must identify misalignment peaks near 100 Hz (2x) and 150 Hz (3x)
    peaks_hz = [p["frequency_hz"] for p in res["spectral_peaks"]]
    # check 2x RPM (100 Hz) presence
    has_2x = any(abs(hz - 100.0) < 5.0 for hz in peaks_hz)
    assert has_2x is True


# -------------------------------------------------------------
# 2. REST API Integration Tests
# -------------------------------------------------------------

def test_api_coupled_piping(client, auth_headers):
    """Verifies coupled piping simulation API endpoints."""
    payload = {
        "inlet_pressure_psi": 280.0,
        "length_m": 1500.0,
        "diameter_in": 6.0,
        "fluid_type": "crude_32",
        "viscosity_cp": 8.0,
        "valve_opening_pct": 50.0,
        "valve_wear_pct": 10.0,
        "pipe_material": "cs"
    }
    response = client.post("/api/v2/engineering/coupled-piping", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "reynolds" in data
    assert "friction_factor" in data
    assert "velocity_m_s" in data
    assert "profile" in data
    assert len(data["profile"]["pressures_psi"]) == 7


def test_api_pump_operating_point(client, auth_headers):
    """Verifies pump operating intersection API endpoints."""
    payload = {
        "shut_off_head_m": 130.0,
        "pump_resistance_coeff": 0.0003,
        "static_lift_m": 25.0,
        "system_friction_coeff": 0.0001,
        "npshr_m": 3.0,
        "suction_pressure_pa": 160000.0,
        "vapor_pressure_pa": 35000.0,
        "density_kg_m3": 850.0
    }
    response = client.post("/api/v2/engineering/pump-operating-point", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["converged"] is True
    assert "operating_flow_m3h" in data
    assert "operating_head_m" in data
    assert "cavitation" in data


def test_api_multi_pump_operating_point(client, auth_headers):
    """Verifies multi-pump series/parallel layout API endpoint."""
    payload = {
        "configuration": "parallel",
        "pumps": [
            {
                "id": "pump_1",
                "name": "Bomba A",
                "type": "centrifugal",
                "active": True,
                "shut_off_head_m": 120.0,
                "pump_resistance_coeff": 0.0004,
                "pd_flow_rate_m3h": 0.0,
                "relief_pressure_m": 0.0,
                "speed_pct": 100.0
            },
            {
                "id": "pump_2",
                "name": "Bomba B",
                "type": "centrifugal",
                "active": True,
                "shut_off_head_m": 120.0,
                "pump_resistance_coeff": 0.0004,
                "pd_flow_rate_m3h": 0.0,
                "relief_pressure_m": 0.0,
                "speed_pct": 100.0
            }
        ],
        "static_lift_m": 30.0,
        "system_friction_coeff": 0.0002,
        "npshr_m": 3.0,
        "suction_pressure_pa": 150000.0,
        "vapor_pressure_pa": 40000.0,
        "density_kg_m3": 850.0
    }
    response = client.post("/api/v2/engineering/multi-pump-operating-point", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["converged"] is True
    assert "operating_flow_m3h" in data
    assert "operating_head_m" in data
    assert "curve_data" in data
    assert "individual_curves" in data["curve_data"]


def test_api_nodal_analysis(client, auth_headers):
    """Verifies oil well nodal curves API endpoints."""
    payload = {
        "reservoir_pressure_psi": 3000.0,
        "productivity_index_j": 2.5,
        "bubble_point_pressure_psi": 1500.0,
        "wellhead_pressure_psi": 100.0,
        "well_depth_ft": 4000.0,  # ensure natural flow for intersection convergence
        "water_cut_percent": 20.0,
        "gas_oil_ratio": 150.0,
        "oil_api": 30.0,
        "oil_viscosity_cst": 15.0
    }
    response = client.post("/api/v2/engineering/nodal-analysis", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["converged"] is True
    assert "operating_flow_rate_bpd" in data
    assert "curve_data" in data


def test_api_vibration_fft(client, auth_headers):
    """Verifies dynamic signal generation and Fourier Transform API endpoints."""
    payload = {
        "rpm": 1800.0,
        "vibration_level": 3.2,
        "defect_type": "desbalance"
    }
    response = client.post("/api/v2/engineering/vibration-fft", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "fft_spectrum" in data
    assert "spectral_peaks" in data
    assert data["defect_type"] == "desbalance"
