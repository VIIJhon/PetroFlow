"""
Unit tests for Decline Curve Analysis (DCA) DeclineEngine.
"""

import pytest
from core.decline_engine import DeclineEngine

def test_decline_exponential():
    res = DeclineEngine.run_decline_projection(qi=1000.0, di_annual_pct=20.0, b=0.0, months=12)
    assert res["model_type"] == "Exponencial"
    assert len(res["rates_bpd"]) == 13
    assert res["rates_bpd"][0] == 1000.0
    assert res["rates_bpd"][-1] < 1000.0
    assert res["eur_bbl"] > 0

def test_decline_harmonic():
    res = DeclineEngine.run_decline_projection(qi=1000.0, di_annual_pct=20.0, b=1.0, months=12)
    assert res["model_type"] == "Armonica"
    assert len(res["rates_bpd"]) == 13
    assert res["rates_bpd"][0] == 1000.0
    assert res["rates_bpd"][-1] < 1000.0
    assert res["eur_bbl"] > 0

def test_decline_hyperbolic():
    res = DeclineEngine.run_decline_projection(qi=1000.0, di_annual_pct=20.0, b=0.5, months=12)
    assert res["model_type"] == "Hiperbolica"
    assert len(res["rates_bpd"]) == 13
    assert res["rates_bpd"][0] == 1000.0
    assert res["rates_bpd"][-1] < 1000.0
    assert res["eur_bbl"] > 0
