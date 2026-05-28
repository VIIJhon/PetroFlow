"""
PetroFlow Fault Tree Analysis (FTA) & Root Cause Analysis (RCA) Engine
Evaluates asset failure trees recursively using boolean gate logic (AND / OR gates)
and computes importance metrics to identify critical failure modes.
"""

from typing import Dict, Any, List, Optional

class FTANode:
    def __init__(self, node_id: str, name: str, node_type: str, probability: float = 0.0, children: Optional[List[str]] = None):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type.upper()  # 'AND', 'OR', 'BASIC'
        self.probability = probability
        self.children = children or []

class FTAEngine:
    @staticmethod
    def solve_tree(nodes_dict: Dict[str, Dict[str, Any]], top_node_id: str) -> Dict[str, Any]:
        """
        Solves the probability of the top event recursively.
        nodes_dict: Dict of nodes, e.g. {
            "top": {"id": "top", "name": "Falla Bomba", "type": "OR", "children": ["pump_mech", "power_loss"]},
            "pump_mech": {"id": "pump_mech", "name": "Falla Mecánica", "type": "AND", "children": ["bearing_fail", "seal_leak"]},
            "bearing_fail": {"id": "bearing_fail", "name": "Falla Cojinete", "type": "BASIC", "probability": 0.05},
            ...
        }
        """
        memo: Dict[str, float] = {}
        
        def calculate_node_prob(node_id: str) -> float:
            if node_id in memo:
                return memo[node_id]
                
            node = nodes_dict.get(node_id)
            if not node:
                return 0.0
                
            node_type = node.get("type", "BASIC").upper()
            
            if node_type == "BASIC":
                prob = float(node.get("probability", 0.0))
                memo[node_id] = prob
                return prob
                
            children_ids = node.get("children", [])
            if not children_ids:
                memo[node_id] = 0.0
                return 0.0
                
            children_probs = [calculate_node_prob(c_id) for c_id in children_ids]
            
            if node_type == "AND":
                # P(AND) = P1 * P2 * ... * Pn
                prob = 1.0
                for p in children_probs:
                    prob *= p
            elif node_type == "OR":
                # P(OR) = 1 - (1 - P1) * (1 - P2) * ... * (1 - Pn)
                q = 1.0
                for p in children_probs:
                    q *= (1.0 - p)
                prob = 1.0 - q
            else:
                prob = 0.0
                
            memo[node_id] = prob
            return prob
            
        # 1. Calculate overall top event probability
        top_prob = calculate_node_prob(top_node_id)
        
        # 2. Calculate Importance of each Basic Event (Fussell-Vesely or Delta Contribution)
        # Delta = P(top | basic event = 1) - P(top | basic event = 0)
        importance_metrics = []
        basic_event_ids = [n_id for n_id, n in nodes_dict.items() if n.get("type") == "BASIC"]
        
        for b_id in basic_event_ids:
            # Save original probability
            original_prob = float(nodes_dict[b_id].get("probability", 0.0))
            
            # Recalculate with probability = 1
            nodes_dict[b_id]["probability"] = 1.0
            memo.clear()
            prob_high = calculate_node_prob(top_node_id)
            
            # Recalculate with probability = 0
            nodes_dict[b_id]["probability"] = 0.0
            memo.clear()
            prob_low = calculate_node_prob(top_node_id)
            
            # Restore original
            nodes_dict[b_id]["probability"] = original_prob
            
            delta = prob_high - prob_low
            
            # Fussell-Vesely Importance: (P_top - P_top(b=0)) / P_top
            fv_importance = 0.0
            if top_prob > 0:
                fv_importance = (top_prob - prob_low) / top_prob
                
            importance_metrics.append({
                "node_id": b_id,
                "name": nodes_dict[b_id].get("name", b_id),
                "birnbaum_importance": max(0.0, delta),
                "fussell_vesely": max(0.0, fv_importance),
                "original_probability": original_prob
            })
            
        # Restore full solver state
        memo.clear()
        
        # Sort importance metrics by Birnbaum importance descending
        importance_metrics.sort(key=lambda x: x["birnbaum_importance"], reverse=True)
        
        # Mark critical path (basic events with highest importance)
        critical_path = [item["node_id"] for item in importance_metrics if item["birnbaum_importance"] > 0.1]
        if not critical_path and importance_metrics:
            critical_path = [importance_metrics[0]["node_id"]]
            
        # Generate full solved tree output for the frontend
        solved_nodes = {}
        calculate_node_prob(top_node_id) # fill memo
        for n_id, node in nodes_dict.items():
            solved_nodes[n_id] = {
                "id": n_id,
                "name": node.get("name", n_id),
                "type": node.get("type", "BASIC"),
                "children": node.get("children", []),
                "probability": memo.get(n_id, node.get("probability", 0.0))
            }
            
        return {
            "top_event_id": top_node_id,
            "top_event_probability": top_prob,
            "solved_nodes": solved_nodes,
            "importance": importance_metrics,
            "critical_path": critical_path
        }
