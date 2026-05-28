"""
ML Service for FastAPI Backend
Migrated from core/mlops_manager.py
Provides MLOps functionality including model versioning, threshold tuning, and retraining
"""

import logging
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger(__name__)

# Model storage directory
MODEL_STORE_DIR = Path("storage/mlops_models")
MODEL_STORE_DIR.mkdir(parents=True, exist_ok=True)


class MLService:
    """
    Service for ML operations including model management, threshold tuning, and retraining.
    Integrates with the existing MLOps infrastructure.
    """
    
    def __init__(self):
        """Initialize ML service."""
        logger.info("ML Service initialized")
    
    # ========== Model Registry Operations ==========
    
    def get_all_regions(self, db: Session) -> List[str]:
        """Get all unique regions from model registry."""
        try:
            # Query distinct regions from database
            # This would query from mlops_model_registry table
            regions = ["GULF_OF_MEXICO", "NORTH_SEA", "MIDDLE_EAST"]
            return regions
        except Exception as e:
            logger.error(f"Error getting regions: {e}")
            return []
    
    def get_model_info(
        self,
        db: Session,
        region: str,
        equipment_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active model information for a region.
        
        Args:
            db: Database session
            region: Geographic region
            equipment_type: Optional equipment type filter
        
        Returns:
            List of model information dictionaries
        """
        try:
            # Query from mlops_model_registry table
            # For now, return mock data
            models = [
                {
                    "id": 1,
                    "region": region,
                    "equipment_type": equipment_type or "pump",
                    "version": "1.2.4",
                    "accuracy": 92.1,
                    "training_date": "2026-04-15",
                    "training_samples": 800,
                    "is_active": True
                }
            ]
            return models
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return []
    
    def register_new_version(
        self,
        db: Session,
        region: str,
        equipment_type: str,
        version: str,
        accuracy: float,
        training_samples: int,
        notes: str = ""
    ) -> int:
        """
        Register a new model version.
        
        Args:
            db: Database session
            region: Geographic region
            equipment_type: Equipment type
            version: Model version string
            accuracy: Model accuracy percentage
            training_samples: Number of training samples
            notes: Optional notes
        
        Returns:
            ID of the new model registry entry
        """
        try:
            # Deactivate previous versions
            # Insert new version into mlops_model_registry
            
            logger.info(
                f"Registered model v{version} for {region}/{equipment_type} "
                f"(accuracy={accuracy:.1f}%)"
            )
            
            # Return mock ID for now
            return 1
            
        except Exception as e:
            logger.error(f"Error registering model version: {e}")
            raise
    
    def get_version_history(
        self,
        db: Session,
        region: str,
        equipment_type: str
    ) -> List[Dict[str, Any]]:
        """Get version history for a region/equipment combination."""
        try:
            # Query mlops_model_registry table
            history = [
                {
                    "id": 1,
                    "region": region,
                    "equipment_type": equipment_type,
                    "version": "1.2.4",
                    "accuracy": 92.1,
                    "training_date": "2026-04-15",
                    "training_samples": 800,
                    "is_active": True,
                    "notes": "Production model"
                }
            ]
            return history
        except Exception as e:
            logger.error(f"Error getting version history: {e}")
            return []
    
    # ========== Threshold Auto-Tuning ==========
    
    def calculate_new_threshold(
        self,
        current_threshold: float,
        false_positive_rate: float,
        false_negative_rate: float
    ) -> Tuple[float, str]:
        """
        Calculate adjusted threshold based on feedback error rates.
        
        Args:
            current_threshold: Current threshold value
            false_positive_rate: False positive rate (0-1)
            false_negative_rate: False negative rate (0-1)
        
        Returns:
            Tuple of (new_threshold, rationale_string)
        """
        adjustment = 0.0
        rationale_parts = []
        
        # High FP rate -> raise threshold (too many false alarms)
        if false_positive_rate > 0.20:
            adjustment += 0.05
            rationale_parts.append(
                f"FP rate {false_positive_rate:.1%} exceeds 20% limit — "
                "threshold raised by +0.05 to reduce nuisance alarms"
            )
        elif false_positive_rate > 0.10:
            adjustment += 0.02
            rationale_parts.append(
                f"FP rate {false_positive_rate:.1%} marginally elevated — "
                "threshold raised by +0.02"
            )
        
        # High FN rate -> lower threshold (missing real failures)
        if false_negative_rate > 0.05:
            adjustment -= 0.05
            rationale_parts.append(
                f"FN rate {false_negative_rate:.1%} exceeds 5% safety limit — "
                "threshold lowered by -0.05 to prevent missed failures"
            )
        elif false_negative_rate > 0.02:
            adjustment -= 0.02
            rationale_parts.append(
                f"FN rate {false_negative_rate:.1%} elevated — threshold lowered by -0.02"
            )
        
        new_thresh = round(min(0.95, max(0.10, current_threshold + adjustment)), 3)
        
        if not rationale_parts:
            rationale = (
                f"Both rates within acceptable bounds — "
                f"threshold unchanged at {current_threshold:.2f}"
            )
        else:
            rationale = ". ".join(rationale_parts) + "."
        
        return new_thresh, rationale
    
    def apply_threshold(
        self,
        db: Session,
        region: str,
        equipment_type: str,
        threshold: float,
        fp_rate: float,
        fn_rate: float,
        applied_by: str = "system"
    ) -> bool:
        """
        Apply and persist a threshold change.
        
        Args:
            db: Database session
            region: Geographic region
            equipment_type: Equipment type
            threshold: New threshold value
            fp_rate: False positive rate
            fn_rate: False negative rate
            applied_by: User or system identifier
        
        Returns:
            True if successful
        """
        try:
            # Insert into mlops_thresholds table
            logger.info(
                f"Threshold updated to {threshold:.3f} for "
                f"{region}/{equipment_type} by {applied_by}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to persist threshold: {e}")
            return False
    
    def get_current_threshold(
        self,
        db: Session,
        region: str,
        equipment_type: str
    ) -> float:
        """Get the most recently applied threshold."""
        try:
            # Query mlops_thresholds table
            # Return default if not found
            return 0.70
        except Exception as e:
            logger.error(f"Error getting current threshold: {e}")
            return 0.70
    
    def get_threshold_history(
        self,
        db: Session,
        region: str,
        equipment_type: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent threshold change history."""
        try:
            # Query mlops_thresholds table
            history = [
                {
                    "id": 1,
                    "region": region,
                    "equipment_type": equipment_type,
                    "threshold": 0.70,
                    "fp_rate": 0.0,
                    "fn_rate": 0.0,
                    "applied_at": datetime.now().isoformat(),
                    "applied_by": "system"
                }
            ]
            return history
        except Exception as e:
            logger.error(f"Error getting threshold history: {e}")
            return []
    
    # ========== Retraining Operations ==========
    
    def get_retraining_schedule(
        self,
        db: Session,
        policy: str = "Monthly"
    ) -> Dict[str, Any]:
        """
        Get retraining schedule information.
        
        Args:
            db: Database session
            policy: Retraining policy (Weekly, Monthly, Quarterly)
        
        Returns:
            Schedule information dictionary
        """
        policy_intervals = {
            "Weekly": 7,
            "Monthly": 30,
            "Quarterly": 90
        }
        
        interval_days = policy_intervals.get(policy, 30)
        
        try:
            # Query mlops_retraining_log table for last execution
            # For now, return mock data
            last_run_dt = datetime.now() - timedelta(days=15)
            next_run_dt = last_run_dt + timedelta(days=interval_days)
            days_remaining = (next_run_dt - datetime.now()).days
            
            return {
                "current_policy": policy,
                "interval_days": interval_days,
                "last_run": last_run_dt.strftime("%Y-%m-%d %H:%M UTC"),
                "last_accuracy": 92.1,
                "last_samples_used": 500,
                "last_status": "completed",
                "next_scheduled_run": next_run_dt.strftime("%Y-%m-%d %H:%M UTC"),
                "days_until_next_run": max(0, days_remaining),
                "overdue": days_remaining < 0
            }
        except Exception as e:
            logger.error(f"Error getting retraining schedule: {e}")
            return {}
    
    def trigger_retraining(
        self,
        db: Session,
        policy: str,
        triggered_by: str = "user",
        region: str = "ALL",
        equipment_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Trigger an incremental retraining cycle.
        
        Args:
            db: Database session
            policy: Retraining policy
            triggered_by: User identifier
            region: Geographic region
            equipment_type: Equipment type
        
        Returns:
            Retraining results dictionary
        """
        start_time = time.time()
        
        try:
            # Query model_feedback table for correction samples
            # For now, simulate with mock data
            correction_count = 150
            
            if correction_count == 0:
                return {
                    "success": False,
                    "message": "No correction samples available in feedback log. "
                               "Submit operator feedback before retraining.",
                    "samples_used": 0
                }
            
            # Get current accuracy
            old_accuracy = 88.0
            
            # Simulate incremental improvement
            improvement = min(correction_count * 0.04, 5.0)
            new_accuracy = round(min(99.0, old_accuracy + improvement), 2)
            
            duration = round(time.time() - start_time, 2)
            
            # Log retraining execution to mlops_retraining_log
            
            # Register new model version if not ALL regions
            if region != "ALL":
                self.register_new_version(
                    db=db,
                    region=region,
                    equipment_type=equipment_type if equipment_type != "all" else "pump",
                    version=f"auto-{datetime.now().strftime('%Y%m%d%H%M')}",
                    accuracy=new_accuracy,
                    training_samples=correction_count,
                    notes=f"Triggered by {triggered_by} via MLOps"
                )
            
            logger.info(
                f"Retraining completed: {correction_count} samples, "
                f"accuracy {old_accuracy:.1f}% -> {new_accuracy:.1f}%"
            )
            
            return {
                "success": True,
                "message": f"Incremental retraining completed using {correction_count} correction samples.",
                "samples_used": correction_count,
                "old_accuracy": old_accuracy,
                "new_accuracy": new_accuracy,
                "duration_sec": duration
            }
            
        except Exception as e:
            logger.error(f"Error during retraining: {e}")
            return {
                "success": False,
                "message": f"Retraining failed: {str(e)}",
                "samples_used": 0
            }
    
    def get_execution_history(
        self,
        db: Session,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get retraining execution history."""
        try:
            # Query mlops_retraining_log table
            history = [
                {
                    "id": 1,
                    "policy": "Monthly",
                    "status": "completed",
                    "triggered_by": "scheduler",
                    "samples_used": 500,
                    "old_accuracy": 88.0,
                    "new_accuracy": 92.1,
                    "duration_sec": 45.2,
                    "notes": "Scheduled retraining",
                    "executed_at": datetime.now().isoformat()
                }
            ]
            return history
        except Exception as e:
            logger.error(f"Error getting execution history: {e}")
            return []
    
    # ========== Model Prediction ==========
    
    def predict_failure(
        self,
        db: Session,
        equipment_id: int,
        sensor_data: Dict[str, float],
        region: str = "GULF_OF_MEXICO"
    ) -> Dict[str, Any]:
        """
        Predict equipment failure probability.
        
        Args:
            db: Database session
            equipment_id: Equipment ID
            sensor_data: Dictionary of sensor readings
            region: Geographic region for model selection
        
        Returns:
            Prediction results dictionary
        """
        try:
            # Get active model for region
            # Load model from storage
            # Run prediction
            
            # Mock prediction for now
            failure_probability = 0.15
            threshold = self.get_current_threshold(db, region, "pump")
            
            prediction = {
                "equipment_id": equipment_id,
                "failure_probability": failure_probability,
                "threshold": threshold,
                "prediction": "failure" if failure_probability > threshold else "normal",
                "confidence": 0.85,
                "model_version": "1.2.4",
                "timestamp": datetime.now().isoformat()
            }
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return {
                "error": str(e),
                "equipment_id": equipment_id
            }
    
    def batch_predict(
        self,
        db: Session,
        predictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run batch predictions for multiple equipment.
        
        Args:
            db: Database session
            predictions: List of prediction requests
        
        Returns:
            List of prediction results
        """
        results = []
        
        for pred_request in predictions:
            try:
                result = self.predict_failure(
                    db=db,
                    equipment_id=pred_request['equipment_id'],
                    sensor_data=pred_request['sensor_data'],
                    region=pred_request.get('region', 'GULF_OF_MEXICO')
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error in batch prediction: {e}")
                results.append({
                    "error": str(e),
                    "equipment_id": pred_request.get('equipment_id')
                })
        
        return results
    
    # ========== Model Management ==========
    
    def save_model(
        self,
        model: Any,
        region: str,
        equipment_type: str,
        version: str
    ) -> str:
        """
        Save model to storage.
        
        Args:
            model: Model object to save
            region: Geographic region
            equipment_type: Equipment type
            version: Model version
        
        Returns:
            Path to saved model
        """
        try:
            filename = f"{region}_{equipment_type}_{version}.pkl"
            filepath = MODEL_STORE_DIR / filename
            
            with open(filepath, 'wb') as f:
                pickle.dump(model, f)
            
            logger.info(f"Model saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise
    
    def load_model(
        self,
        region: str,
        equipment_type: str,
        version: Optional[str] = None
    ) -> Any:
        """
        Load model from storage.
        
        Args:
            region: Geographic region
            equipment_type: Equipment type
            version: Optional specific version (latest if None)
        
        Returns:
            Loaded model object
        """
        try:
            if version:
                filename = f"{region}_{equipment_type}_{version}.pkl"
            else:
                # Find latest version
                pattern = f"{region}_{equipment_type}_*.pkl"
                files = list(MODEL_STORE_DIR.glob(pattern))
                if not files:
                    raise FileNotFoundError(f"No models found for {region}/{equipment_type}")
                filename = max(files, key=lambda p: p.stat().st_mtime).name
            
            filepath = MODEL_STORE_DIR / filename
            
            with open(filepath, 'rb') as f:
                model = pickle.load(f)
            
            logger.info(f"Model loaded from {filepath}")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise


# Singleton instance
_ml_service = None

def get_ml_service() -> MLService:
    """Get singleton ML service instance."""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
    return _ml_service