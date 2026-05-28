"""
Unit tests for Fault Tree Analysis (FTA) FTAEngine.
"""

import pytest
from core.fta_engine import FTAEngine

def test_fta_and_gate():
    # AND gate: P(A AND B) = P(A) * P(B)
    nodes = {
        "top": {
            "id": "top",
            "name": "AND Gate",
            "type": "AND",
            "children": ["child_1", "child_2"]
        },
        "child_1": {
            "id": "child_1",
            "name": "Child 1",
            "type": "BASIC",
            "probability": 0.2
        },
        "child_2": {
            "id": "child_2",
            "name": "Child 2",
            "type": "BASIC",
            "probability": 0.3
        }
    }
    res = FTAEngine.solve_tree(nodes, "top")
    assert abs(res["top_event_probability"] - 0.06) < 1e-6
    assert "critical_path" in res

def test_fta_or_gate():
    # OR gate: P(A OR B) = 1 - (1 - P(A)) * (1 - P(B))
    nodes = {
        "top": {
            "id": "top",
            "name": "OR Gate",
            "type": "OR",
            "children": ["child_1", "child_2"]
        },
        "child_1": {
            "id": "child_1",
            "name": "Child 1",
            "type": "BASIC",
            "probability": 0.2
        },
        "child_2": {
            "id": "child_2",
            "name": "Child 2",
            "type": "BASIC",
            "probability": 0.3
        }
    }
    res = FTAEngine.solve_tree(nodes, "top")
    # P = 1 - 0.8 * 0.7 = 1 - 0.56 = 0.44
    assert abs(res["top_event_probability"] - 0.44) < 1e-6
