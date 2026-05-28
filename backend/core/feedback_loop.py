"""
Phase 8 Backend: Feedback Loop & Continuous Retraining Pipeline.
Connects operator ground-truth feedback with the ML engine for continuous improvement.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

from core.failure_prediction_engine import retrain_model_with_new_data

class FeedbackManager:
    """Handles logging of operator feedback into the local SQLite database."""
    
    def __init__(self, db_path="petroflow.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    equipment_id TEXT,
                    prediction_prob REAL,
                    actual_outcome TEXT,
                    label TEXT,
                    operator_notes TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")

    def log_feedback(self, equipment_id: str, prediction_prob: float, actual_outcome: str, label: str, notes: str) -> bool:
        """Logs the validation feedback from physical inspections."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_feedback (equipment_id, prediction_prob, actual_outcome, label, operator_notes)
                VALUES (?, ?, ?, ?, ?)
            """, (equipment_id, prediction_prob, actual_outcome, label, notes))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging feedback: {e}")
            return False
            
    def get_feedback_history(self) -> pd.DataFrame:
        """Returns the feedback history as a pandas DataFrame."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM model_feedback ORDER BY timestamp DESC", conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error reading feedback: {e}")
            return pd.DataFrame()


class ContinuousRetrainer:
    """Aggregates feedback data and triggers the ML retraining pipeline."""
    
    def __init__(self):
        self.feedback_manager = FeedbackManager()
        
    def check_retraining_criteria(self, min_samples: int = 10) -> dict:
        """Check if enough new verified feedback exists to warrant retraining."""
        df = self.feedback_manager.get_feedback_history()
        if df.empty:
            return {"ready": False, "reason": "No feedback data available."}
            
        mistakes = df[df['label'].isin(['False Positive', 'False Negative'])]
        
        if len(mistakes) >= min_samples:
            return {"ready": True, "samples_ready": len(df), "mistakes": len(mistakes)}
        else:
            return {"ready": False, "reason": f"Only {len(mistakes)} correction samples available. Minimum {min_samples} required."}
            
    def _generate_synthetic_features_for_feedback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        In a production environment, this method would query the Time-Series Database (TSDB) 
        for the exact sensor telemetry at the given timestamps.
        Here, we synthesize plausible physical parameters corresponding to the operator labels.
        """
        n_samples = len(df)
        np.random.seed(int(datetime.now().timestamp()) % 10000)
        
        features = pd.DataFrame({
            'temperature': np.random.normal(65, 15, n_samples),
            'pressure': np.random.normal(25, 5, n_samples),
            'vibration': np.random.normal(2.5, 1.2, n_samples),
            'operating_hours': np.random.uniform(1000, 45000, n_samples),
            'rpm': np.random.normal(3000, 200, n_samples)
        })
        
        # Adjust features based on operator truth
        # If the operator said it was a failure (True Positive / False Negative), make features extreme
        failure_idx = df['actual_outcome'] == 'Failed/Damaged'
        features.loc[failure_idx, 'temperature'] += np.random.uniform(20, 40, sum(failure_idx))
        features.loc[failure_idx, 'vibration'] += np.random.uniform(3.0, 6.0, sum(failure_idx))
        
        # If operator said healthy (True Negative / False Positive), keep features nominal
        healthy_idx = df['actual_outcome'] == 'Healthy/Normal'
        features.loc[healthy_idx, 'temperature'] = np.clip(features.loc[healthy_idx, 'temperature'], 40, 80)
        features.loc[healthy_idx, 'vibration'] = np.clip(features.loc[healthy_idx, 'vibration'], 0.5, 2.5)
        
        # Map failure category
        features['failure_category'] = np.where(failure_idx, 2, 0)
        
        return features

    def trigger_retraining(self) -> dict:
        """
        Extracts features corresponding to historical feedback,
        injects them into the ML engine, and computes new model weights.
        """
        df = self.feedback_manager.get_feedback_history()
        
        if len(df) == 0:
            return {"success": False, "message": "Cannot retrain. Database is empty."}
            
        # Reconstruct physical features for the ML engine
        new_features_df = self._generate_synthetic_features_for_feedback(df)
        
        try:
            # Call the real failure prediction engine method
            new_model, new_scaler, new_accuracy, feature_imp, _, _, _ = retrain_model_with_new_data(
                new_features_df, model_version='2.1'
            )
            
            return {
                "success": True,
                "message": "Continuous retraining pipeline executed successfully.",
                "new_accuracy": round(new_accuracy * 100, 2),
                "samples_added": len(df),
                "model_payload": {
                    "model": new_model,
                    "scaler": new_scaler,
                    "accuracy": new_accuracy,
                    "feature_importance": feature_imp
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"ML Engine retraining failed: {str(e)}"
            }
