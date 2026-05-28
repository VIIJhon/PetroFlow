import pytest
import numpy as np

from app.api.endpoints.simulation import (
    OperationOptimizeRequest,
    OperationEnvelopeCheckRequest,
    optimize_operation,
    check_operation_envelope,
    get_operation_envelope,
)
from app.models.user import User, UserRole
from core.operational_optimizer import (
    EfficiencyOptimizer,
    SafetyEnvelopeCalculator,
)


class DummyUser(User):
    pass


@pytest.fixture
def stub_user():
    return User(
        username="tester",
        email="tester@example.com",
        hashed_password="x",
        role=UserRole.ENGINEER,
        is_active=True,
        is_verified=True,
    )


@pytest.mark.parametrize(
    "rpm,valve,expected_flow_ratio",
    [
        (1800, 50.0, 0.25),
        (3600, 100.0, 1.0),
        (900, 25.0, 0.0625),
    ],
)
def test_actual_flow_scales_linearly_with_rpm_and_valve(rpm, valve, expected_flow_ratio):
    rated_rpm = 3600.0
    max_flow = 1200.0

    result = EfficiencyOptimizer._actual_flow(rpm, valve, rated_rpm, max_flow)
    expected = max_flow * (rpm / rated_rpm) * (valve / 100.0)

    assert pytest.approx(expected, rel=1e-6) == result
    assert result == pytest.approx(max_flow * expected_flow_ratio, rel=1e-6)


def test_pump_power_increases_with_rpm_and_decreases_with_valve():
    rated_rpm = 3600.0
    rated_kw = 250.0

    low_power = EfficiencyOptimizer._pump_power(1800, 100.0, rated_rpm, rated_kw)
    high_power = EfficiencyOptimizer._pump_power(3600, 100.0, rated_rpm, rated_kw)
    closed_power = EfficiencyOptimizer._pump_power(3600, 10.0, rated_rpm, rated_kw)

    assert low_power < high_power
    assert closed_power > high_power


def test_optimize_operation_returns_valid_solution_for_pump():
    result = EfficiencyOptimizer.optimize_operation(
        equipment_type="pump",
        current_rpm=1800.0,
        current_valve=50.0,
        target_flow=300.0,
        current_pressure=10.0,
        current_temp=60.0,
    )

    assert result["success"] is True
    assert 10.0 <= result["optimal_rpm"] <= 3600.0
    assert 10.0 <= result["optimal_valve"] <= 100.0
    assert result["power_saved_kw"] >= 0
    assert abs(result["achieved_flow"] - 300.0) <= 30.0
    assert result["within_envelope"] is True


def test_get_envelope_returns_compressor_limits():
    envelope = SafetyEnvelopeCalculator.get_envelope("centrifugal compressor")
    assert envelope["max_pressure_bar"] == 200.0
    assert envelope["min_rpm"] == 3000.0
    assert envelope["max_vibration_mms"] == 2.8


def test_check_operating_point_identifies_unsafe_pressure_and_vibration():
    result = SafetyEnvelopeCalculator.check_operating_point(
        equipment_type="pump",
        pressure_bar=50.0,
        temp_c=75.0,
        rpm=1800.0,
        vibration_mms=5.0,
    )

    assert result["safe"] is False
    assert result["checks"]["pressure"]["ok"] is False
    assert result["checks"]["vibration"]["ok"] is False


@pytest.mark.asyncio
async def test_optimize_endpoint_direct_call(stub_user):
    request = OperationOptimizeRequest(
        equipment_type="pump",
        current_rpm=1800.0,
        current_valve=45.0,
        target_flow_m3h=600.0,
        current_pressure_bar=15.0,
        current_temp_c=55.0,
    )

    response = await optimize_operation(request, db=None, current_user=stub_user)

    assert response["status"] == "success"
    assert "optimization" in response
    assert response["optimization"]["success"] is True


@pytest.mark.asyncio
async def test_check_operation_envelope_endpoint_direct_call(stub_user):
    request = OperationEnvelopeCheckRequest(
        equipment_type="pump",
        pressure_bar=15.0,
        temperature_c=60.0,
        rpm=1800.0,
        vibration_mms=2.2,
    )

    response = await check_operation_envelope(request, db=None, current_user=stub_user)

    assert response["status"] == "success"
    assert response["safety_check"]["safe"] is True


@pytest.mark.asyncio
async def test_get_operation_envelope_endpoint_direct_call(stub_user):
    response = await get_operation_envelope(
        equipment_type="turbine",
        db=None,
        current_user=stub_user,
    )

    assert response["status"] == "success"
    assert response["equipment_type"] == "turbine"
    assert response["envelope"]["max_flow_m3h"] == 80000.0
