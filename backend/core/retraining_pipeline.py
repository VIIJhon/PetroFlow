"""
Retraining Pipeline Module
Integrates historical data with formation-specific models for continuous learning.
Implements data validation, feature engineering, and model versioning.

Phase: Phase 1 - Continuous Model Improvement
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import json
import pickle

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import confusion_matrix, classification_report

from .historical_data_connector import HistoricalDataRecord, HistoricalDataConnector
from .formation_specific_models import FormationType, WellContext
from .audit_logging_service import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()


@dataclass
class ModelVersion:
    """Represents a versioned model snapshot."""
    version_id: str
    creation_date: str
    formation_type: str
    equipment_type: str
    power_source: str
    training_samples: int
    accuracy: float
    precision: float
    recall: float
    f1_score_value: float
    model_path: str
    scaler_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrainingReport:
    """Report of a retraining session."""
    timestamp: str
    formation_type: str
    equipment_type: str
    power_source: str
    historical_samples_used: int
    synthetic_samples_used: int
    total_samples: int
    train_test_split: float
    previous_accuracy: float
    new_accuracy: float
    accuracy_improvement: float
    precision: float
    recall: float
    f1_score_value: float
    confusion_matrix_data: List[List[int]]
    recommendations: List[str]


class RetrainingPipeline:
    """
    Manages continuous model retraining with historical data.
    Combines real operational data with formation-specific synthetic generation.
    """
    
    def __init__(self, model_storage_dir: str = "storage/models/versioned"):
        """
        Initialize the retraining pipeline.
        
        Args:
            model_storage_dir: Directory for storing model versions
        """
        self.storage_dir = Path(model_storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.model_registry = self._load_model_registry()
        self.connector = HistoricalDataConnector()
        
    def _load_model_registry(self) -> Dict[str, List[ModelVersion]]:
        """Load model version registry from disk."""
        registry_path = self.storage_dir / "registry.json"
        if registry_path.exists():
            try:
                with open(registry_path, "r") as f:
                    registry_data = json.load(f)
                    return {
                        key: [self._deserialize_model_version(v) for v in versions]
                        for key, versions in registry_data.items()
                    }
            except Exception as e:
                logger.warning(f"Failed to load model registry: {str(e)}")
        return {}
    
    def _deserialize_model_version(self, data: Dict) -> ModelVersion:
        """Deserialize ModelVersion from JSON."""
        return ModelVersion(
            version_id=data["version_id"],
            creation_date=data["creation_date"],
            formation_type=data["formation_type"],
            equipment_type=data["equipment_type"],
            power_source=data["power_source"],
            training_samples=data["training_samples"],
            accuracy=data["accuracy"],
            precision=data["precision"],
            recall=data["recall"],
            f1_score_value=data["f1_score"],
            model_path=data["model_path"],
            scaler_path=data["scaler_path"],
            metadata=data.get("metadata", {})
        )
    
    def _save_model_registry(self) -> None:
        """Save model version registry to disk."""
        try:
            registry_path = self.storage_dir / "registry.json"
            registry_data = {}
            
            for key, versions in self.model_registry.items():
                registry_data[key] = [
                    {
                        "version_id": v.version_id,
                        "creation_date": v.creation_date,
                        "formation_type": v.formation_type,
                        "equipment_type": v.equipment_type,
                        "power_source": v.power_source,
                        "training_samples": v.training_samples,
                        "accuracy": v.accuracy,
                        "precision": v.precision,
                        "recall": v.recall,
                        "f1_score": v.f1_score_value,
                        "model_path": v.model_path,
                        "scaler_path": v.scaler_path,
                        "metadata": v.metadata,
                    }
                    for v in versions
                ]
            
            with open(registry_path, "w") as f:
                json.dump(registry_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save model registry: {str(e)}")
    
    def prepare_training_data(
        self,
        historical_records: List[HistoricalDataRecord],
        well_context: WellContext,
        equipment_type: str,
        power_source: str,
        synthetic_ratio: float = 0.3
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Prepare training data combining historical and synthetic data.
        
        Args:
            historical_records: Real operational data from database
            well_context: Well context for synthetic data generation
            equipment_type: 'pump' or 'compressor'
            power_source: 'Electric', 'Diesel', 'Steam', 'Gas'
            synthetic_ratio: Ratio of synthetic to total data (0-1)
            
        Returns:
            Tuple of (combined_dataframe, feature_names)
        """
        from .formation_specific_models import get_formation_model_generator
        
        logger.info(f"Preparing training data: {equipment_type} - {power_source}")
        
        historical_df = self._convert_records_to_dataframe(
            historical_records,
            equipment_type,
            power_source
        )
        
        n_historical = len(historical_df)
        logger.info(f"Historical records available: {n_historical}")
        
        if n_historical == 0:
            logger.warning("No historical records found, using synthetic data only")
            generator = get_formation_model_generator()
            if equipment_type == "pump":
                synthetic_df = generator.generate_pump_training_data(
                    well_context,
                    n_samples=800,
                    power_source=power_source
                )
            else:
                synthetic_df = generator.generate_compressor_training_data(
                    well_context,
                    n_samples=800,
                    power_source=power_source
                )
            return synthetic_df, list(synthetic_df.columns[:-2])
        
        n_synthetic = int(n_historical * synthetic_ratio / (1 - synthetic_ratio))
        logger.info(f"Generating {n_synthetic} synthetic records for augmentation")
        
        generator = get_formation_model_generator()
        if equipment_type == "pump":
            synthetic_df = generator.generate_pump_training_data(
                well_context,
                n_samples=n_synthetic,
                power_source=power_source
            )
        else:
            synthetic_df = generator.generate_compressor_training_data(
                well_context,
                n_samples=n_synthetic,
                power_source=power_source
            )
        
        combined_df = pd.concat(
            [historical_df, synthetic_df],
            ignore_index=True,
            sort=False
        )
        
        combined_df = combined_df.fillna(combined_df.mean(numeric_only=True))
        
        feature_cols = [col for col in combined_df.columns 
                       if col not in ['failure_category', 'failure_score']]
        
        logger.info(
            f"Training data prepared: {len(combined_df)} records "
            f"({n_historical} historical, {n_synthetic} synthetic)"
        )
        
        return combined_df, feature_cols
    
    def _convert_records_to_dataframe(
        self,
        records: List[HistoricalDataRecord],
        equipment_type: str,
        power_source: str
    ) -> pd.DataFrame:
        """Convert HistoricalDataRecord objects to DataFrame for training."""
        data = []
        
        for record in records:
            try:
                row = {
                    'discharge_temperature': record.discharge_temperature,
                    'inlet_pressure': record.inlet_pressure,
                    'outlet_pressure': record.outlet_pressure,
                    'volumetric_flow': record.volumetric_flow,
                    'vibration_velocity': record.vibration_velocity,
                    'rpm': record.rpm,
                    'failure_category': 2 if record.failure_occurred else 0,
                }
                
                if power_source == "Electric":
                    row.update({
                        'motor_efficiency': record.metadata.get('motor_efficiency', 90),
                        'winding_temperature': record.metadata.get('winding_temperature', 65),
                        'phase_current': record.metadata.get('phase_current', 15),
                        'power_factor': record.metadata.get('power_factor', 0.92),
                    })
                elif power_source == "Diesel":
                    row.update({
                        'fuel_consumption': record.metadata.get('fuel_consumption', 30),
                        'engine_oil_temperature': record.metadata.get('engine_oil_temperature', 80),
                        'engine_oil_pressure': record.metadata.get('engine_oil_pressure', 3.0),
                        'exhaust_temperature': record.metadata.get('exhaust_temperature', 450),
                    })
                elif power_source == "Steam":
                    row.update({
                        'inlet_steam_pressure': record.metadata.get('inlet_steam_pressure', 8),
                        'steam_temperature': record.metadata.get('steam_temperature', 250),
                        'condensate_temperature': record.metadata.get('condensate_temperature', 70),
                        'throttle_valve_position': record.metadata.get('throttle_valve_position', 50),
                    })
                elif power_source == "Gas":
                    row.update({
                        'air_fuel_ratio': record.metadata.get('air_fuel_ratio', 14.7),
                        'intake_temperature': record.metadata.get('intake_temperature', 35),
                        'knock_index': record.metadata.get('knock_index', 50),
                        'turbine_inlet_temperature': record.metadata.get('turbine_inlet_temperature', 650),
                    })
                
                row['failure_score'] = self._calculate_failure_score(row)
                data.append(row)
                
            except Exception as e:
                logger.warning(f"Failed to convert record: {str(e)}")
                continue
        
        return pd.DataFrame(data)
    
    def _calculate_failure_score(self, row: Dict) -> float:
        """Estimate failure score from operational parameters."""
        scores = []
        
        if row['discharge_temperature'] > 100:
            scores.append(min(1.0, (row['discharge_temperature'] - 100) / 50))
        
        if row['vibration_velocity'] > 5:
            scores.append(min(1.0, (row['vibration_velocity'] - 5) / 5))
        
        if 'motor_efficiency' in row and row['motor_efficiency'] < 85:
            scores.append((90 - row['motor_efficiency']) / 10 * 0.5)
        
        if 'winding_temperature' in row and row['winding_temperature'] > 100:
            scores.append(min(0.5, (row['winding_temperature'] - 100) / 30))
        
        if 'fuel_consumption' in row and row['fuel_consumption'] > 40:
            scores.append(min(0.4, (row['fuel_consumption'] - 40) / 20))
        
        if 'knock_index' in row and row['knock_index'] > 60:
            scores.append(min(0.5, (row['knock_index'] - 60) / 40))
        
        return min(100.0, np.mean(scores) * 100) if scores else 0.0
    
    def train_model(
        self,
        training_df: pd.DataFrame,
        feature_names: List[str],
        formation_type: str,
        equipment_type: str,
        power_source: str,
        test_size: float = 0.2
    ) -> Tuple[CalibratedClassifierCV, StandardScaler, ModelVersion, RetrainingReport]:
        """
        Train a new model with improved features.
        
        Args:
            training_df: Combined training data
            feature_names: List of feature column names
            formation_type: Type of formation
            equipment_type: 'pump' or 'compressor'
            power_source: Power source type
            test_size: Train/test split ratio
            
        Returns:
            Tuple of (model, scaler, model_version, report)
        """
        logger.info(f"Training model: {formation_type} - {equipment_type} - {power_source}")
        
        start_time = datetime.now()
        
        X = training_df[feature_names]
        y = training_df['failure_category']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y
        )
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        base_model = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=7,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
            n_iter_no_change=15,
            validation_fraction=0.1
        )
        
        model = CalibratedClassifierCV(base_model, cv=5, method='sigmoid')
        model.fit(X_train_scaled, y_train)
        
        y_pred = model.predict(X_test_scaled)
        y_pred_proba = model.predict_proba(X_test_scaled)
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        cm = confusion_matrix(y_test, y_pred)
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        version_id = self._generate_version_id(formation_type, equipment_type, power_source)
        model_version = self._save_model_version(
            version_id,
            model,
            scaler,
            formation_type,
            equipment_type,
            power_source,
            len(training_df),
            accuracy,
            precision,
            recall,
            f1
        )
        
        previous_accuracy = self._get_previous_model_accuracy(
            formation_type,
            equipment_type,
            power_source
        )
        
        recommendations = self._generate_retraining_recommendations(
            accuracy,
            precision,
            recall,
            previous_accuracy,
            len(training_df)
        )
        
        report = RetrainingReport(
            timestamp=datetime.now().isoformat(),
            formation_type=formation_type,
            equipment_type=equipment_type,
            power_source=power_source,
            historical_samples_used=len(training_df),
            synthetic_samples_used=0,
            total_samples=len(training_df),
            train_test_split=1 - test_size,
            previous_accuracy=previous_accuracy,
            new_accuracy=accuracy,
            accuracy_improvement=accuracy - previous_accuracy,
            precision=precision,
            recall=recall,
            f1_score_value=f1,
            confusion_matrix_data=cm.tolist(),
            recommendations=recommendations
        )
        
        audit_logger.log_system(
            f"Model retrained: {formation_type} - {equipment_type} - {power_source} "
            f"(Accuracy: {accuracy:.2%}, Training time: {training_time:.2f}s)",
            action="MODEL_RETRAINED"
        )
        
        logger.info(
            f"Model training complete: Accuracy={accuracy:.2%}, "
            f"Precision={precision:.2%}, Recall={recall:.2%}, F1={f1:.2%}"
        )
        
        return model, scaler, model_version, report
    
    def _generate_version_id(self, formation: str, equipment: str, power: str) -> str:
        """Generate unique version ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{formation}_{equipment}_{power}_{timestamp}"
    
    def _save_model_version(
        self,
        version_id: str,
        model: CalibratedClassifierCV,
        scaler: StandardScaler,
        formation_type: str,
        equipment_type: str,
        power_source: str,
        training_samples: int,
        accuracy: float,
        precision: float,
        recall: float,
        f1_score_value: float
    ) -> ModelVersion:
        """Save model version to disk."""
        try:
            version_dir = self.storage_dir / version_id
            version_dir.mkdir(parents=True, exist_ok=True)
            
            model_path = str(version_dir / "model.pkl")
            scaler_path = str(version_dir / "scaler.pkl")
            
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            
            model_version = ModelVersion(
                version_id=version_id,
                creation_date=datetime.now().isoformat(),
                formation_type=formation_type,
                equipment_type=equipment_type,
                power_source=power_source,
                training_samples=training_samples,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score_value=f1_score_value,
                model_path=model_path,
                scaler_path=scaler_path,
            )
            
            registry_key = f"{formation_type}_{equipment_type}_{power_source}"
            if registry_key not in self.model_registry:
                self.model_registry[registry_key] = []
            
            self.model_registry[registry_key].append(model_version)
            self._save_model_registry()
            
            logger.info(f"Model version saved: {version_id}")
            return model_version
            
        except Exception as e:
            logger.error(f"Failed to save model version: {str(e)}")
            raise
    
    def _get_previous_model_accuracy(
        self,
        formation_type: str,
        equipment_type: str,
        power_source: str
    ) -> float:
        """Get accuracy of previous model version if it exists."""
        registry_key = f"{formation_type}_{equipment_type}_{power_source}"
        if registry_key in self.model_registry and len(self.model_registry[registry_key]) > 0:
            return self.model_registry[registry_key][-1].accuracy
        return 0.0
    
    def _generate_retraining_recommendations(
        self,
        accuracy: float,
        precision: float,
        recall: float,
        previous_accuracy: float,
        sample_count: int
    ) -> List[str]:
        """Generate recommendations based on training metrics."""
        recommendations = []
        
        if sample_count < 500:
            recommendations.append(
                "Collect more historical data - current sample size is below 500"
            )
        
        if accuracy < 0.80:
            recommendations.append(
                "Accuracy below 80% - consider feature engineering or hyperparameter tuning"
            )
        
        if precision < 0.75:
            recommendations.append(
                "Precision is low - model generates false positives frequently"
            )
        
        if recall < 0.70:
            recommendations.append(
                "Recall is low - model may miss actual failures"
            )
        
        if accuracy - previous_accuracy < -0.05:
            recommendations.append(
                "Model accuracy degraded - check for data distribution shift"
            )
        
        if accuracy - previous_accuracy > 0.05:
            recommendations.append(
                "Significant accuracy improvement - consider deploying this version"
            )
        
        if not recommendations:
            recommendations.append("Model performance is satisfactory - continue monitoring")
        
        return recommendations
    
    def get_model_version(
        self,
        formation_type: str,
        equipment_type: str,
        power_source: str,
        version_id: Optional[str] = None
    ) -> Optional[Tuple[CalibratedClassifierCV, StandardScaler, ModelVersion]]:
        """
        Retrieve a specific model version or the latest version.
        
        Args:
            formation_type: Formation type
            equipment_type: Equipment type
            power_source: Power source
            version_id: Specific version ID, or None for latest
            
        Returns:
            Tuple of (model, scaler, version_info) or None if not found
        """
        registry_key = f"{formation_type}_{equipment_type}_{power_source}"
        
        if registry_key not in self.model_registry:
            logger.warning(f"No models found for {registry_key}")
            return None
        
        versions = self.model_registry[registry_key]
        if not versions:
            return None
        
        if version_id:
            version = next((v for v in versions if v.version_id == version_id), None)
        else:
            version = versions[-1]
        
        if not version:
            return None
        
        try:
            with open(version.model_path, 'rb') as f:
                model = pickle.load(f)
            
            with open(version.scaler_path, 'rb') as f:
                scaler = pickle.load(f)
            
            return model, scaler, version
            
        except Exception as e:
            logger.error(f"Failed to load model version {version_id}: {str(e)}")
            return None
    
    def list_model_versions(
        self,
        formation_type: Optional[str] = None,
        equipment_type: Optional[str] = None,
        power_source: Optional[str] = None
    ) -> List[ModelVersion]:
        """List available model versions with optional filtering."""
        results = []
        
        for registry_key, versions in self.model_registry.items():
            for version in versions:
                if (
                    (formation_type is None or version.formation_type == formation_type) and
                    (equipment_type is None or version.equipment_type == equipment_type) and
                    (power_source is None or version.power_source == power_source)
                ):
                    results.append(version)
        
        return sorted(results, key=lambda v: v.creation_date, reverse=True)


def get_retraining_pipeline() -> RetrainingPipeline:
    """Get singleton instance of retraining pipeline."""
    if not hasattr(get_retraining_pipeline, "_instance"):
        get_retraining_pipeline._instance = RetrainingPipeline()
    return get_retraining_pipeline._instance
