"""
Phase 1 Example Script - Complete Workflow
Demonstrates how to use Phase 1 modules for historical data integration
and formation-specific model retraining.

Usage: python -c "from scripts.phase1_example import main; main()"
Or: streamlit run scripts/phase1_example.py
"""

import logging
from pathlib import Path

from core.historical_data_connector import (
    HistoricalDataConnector,
    DataSourceConfig,
    DataSourceType,
    HistoricalDataRecord
)
from core.formation_specific_models import (
    FormationType,
    WellContext,
    get_formation_model_generator
)
from core.well_context_analyzer import OilWellContextAnalyzer, get_well_analyzer
from core.retraining_pipeline import get_retraining_pipeline
from core.audit_logging_service import get_audit_logger
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

audit_logger = get_audit_logger()


def example_connect_postgresql():
    """Example: Connect to PostgreSQL operator database."""
    logger.info("Example 1: PostgreSQL Connection")
    
    connector = HistoricalDataConnector()
    
    config = DataSourceConfig(
        source_type=DataSourceType.POSTGRESQL,
        host="production.database.example.com",
        port=5432,
        database="operator_history",
        username="petro_reader",
        password="secure_password",
        table_name="equipment_telemetry",
        timeout_seconds=30,
        max_retries=3
    )
    
    if connector.register_data_source("operator_pg", config):
        logger.info("Successfully registered PostgreSQL source")
        
        records, metadata = connector.fetch_historical_data(
            source_name="operator_pg",
            filters={"equipment_type": "pump"},
            limit=5000
        )
        
        logger.info(f"Fetched {len(records)} records from operator database")
        if records:
            first_record = records[0]
            logger.info(f"Sample record: {first_record.equipment_id} - "
                       f"Temp: {first_record.discharge_temperature}°C, "
                       f"Failure: {first_record.failure_occurred}")
    
    else:
        logger.warning("Could not register PostgreSQL source - using CSV fallback")


def example_load_csv_historical_data():
    """Example: Load historical data from CSV file."""
    logger.info("Example 2: CSV Historical Data Loading")
    
    connector = HistoricalDataConnector()
    
    csv_path = "data/operator_historical_data.csv"
    if Path(csv_path).exists():
        config = DataSourceConfig(
            source_type=DataSourceType.CSV,
            file_path=csv_path
        )
        
        if connector.register_data_source("historical_csv", config):
            logger.info(f"Successfully registered CSV source: {csv_path}")
            
            records, metadata = connector.fetch_historical_data(
                source_name="historical_csv",
                limit=1000
            )
            
            logger.info(f"Loaded {len(records)} records from CSV")
            logger.info(f"Metadata: {metadata}")
        
    else:
        logger.warning(f"CSV file not found: {csv_path}")


def example_well_risk_assessment():
    """Example: Perform comprehensive well risk assessment."""
    logger.info("Example 3: Well Risk Assessment")
    
    analyzer = get_well_analyzer()
    
    well_scenarios = [
        {
            "name": "Shallow Low-Temp Sandstone Well",
            "depth": 1200,
            "bht": 45,
            "viscosity": 15,
            "api": 32,
            "formation": "sandstone"
        },
        {
            "name": "Deep High-Temp Limestone Well",
            "depth": 3800,
            "bht": 140,
            "viscosity": 85,
            "api": 22,
            "formation": "limestone"
        },
        {
            "name": "Ultra-Deep Shale Well",
            "depth": 5500,
            "bht": 180,
            "viscosity": 200,
            "api": 18,
            "formation": "shale"
        }
    ]
    
    for scenario in well_scenarios:
        logger.info(f"\n--- {scenario['name']} ---")
        
        assessment = analyzer.assess_well_risk(
            depth_meters=scenario["depth"],
            bottom_hole_temp=scenario["bht"],
            oil_viscosity_cst=scenario["viscosity"],
            api_gravity=scenario["api"],
            formation_type=scenario["formation"],
            water_cut_percent=50
        )
        
        logger.info(f"Well Type: {assessment.well_type.value}")
        logger.info(f"Overall Risk: {assessment.overall_risk_score:.1%}")
        logger.info(f"Monitoring Interval: {assessment.recommended_monitoring_interval_hours}h")
        
        for param in assessment.critical_parameters[:2]:
            logger.info(f"  Critical: {param}")
        
        for rec in assessment.maintenance_recommendations[:2]:
            logger.info(f"  Recommendation: {rec}")


def example_formation_model_training():
    """Example: Train formation-specific models."""
    logger.info("Example 4: Formation-Specific Model Training")
    
    generator = get_formation_model_generator()
    
    well = WellContext(
        formation_type=FormationType.LIMESTONE,
        well_depth_meters=3500,
        bottom_hole_temperature_celsius=120,
        oil_viscosity_cst=85,
        api_gravity=22,
        producing_zone_pressure_bar=200,
        water_cut_percent=55,
        gas_oil_ratio=120
    )
    
    scenarios = [
        ("pump", "Electric"),
        ("pump", "Diesel"),
        ("compressor", "Electric"),
        ("compressor", "Gas")
    ]
    
    for equipment_type, power_source in scenarios:
        logger.info(f"\nTraining: {equipment_type.capitalize()} - {power_source}")
        
        try:
            model, scaler, accuracy, features = generator.train_formation_model(
                well_context=well,
                equipment_type=equipment_type,
                power_source=power_source
            )
            
            logger.info(f"  Accuracy: {accuracy:.1%}")
            logger.info(f"  Features: {len(features)}")
            
        except Exception as e:
            logger.error(f"  Error: {str(e)}")


def example_retraining_pipeline():
    """Example: Complete retraining pipeline with historical data."""
    logger.info("Example 5: Continuous Model Retraining Pipeline")
    
    pipeline = get_retraining_pipeline()
    
    well = WellContext(
        formation_type=FormationType.SANDSTONE,
        well_depth_meters=2500,
        bottom_hole_temperature_celsius=95,
        oil_viscosity_cst=45,
        api_gravity=28
    )
    
    synthetic_training_data_df = None
    historical_records = []
    
    try:
        synthetic_df = generator.generate_pump_training_data(
            well,
            n_samples=800,
            power_source="Electric"
        )
        
        training_df, features = pipeline.prepare_training_data(
            historical_records=historical_records,
            well_context=well,
            equipment_type="pump",
            power_source="Electric",
            synthetic_ratio=0.3
        )
        
        logger.info(f"Training data prepared: {len(training_df)} samples, {len(features)} features")
        
        model, scaler, version_info, report = pipeline.train_model(
            training_df=training_df,
            feature_names=features,
            formation_type="Sandstone",
            equipment_type="pump",
            power_source="Electric"
        )
        
        logger.info(f"Model Version: {version_info.version_id}")
        logger.info(f"Accuracy: {version_info.accuracy:.1%}")
        logger.info(f"Precision: {version_info.precision:.1%}")
        logger.info(f"Recall: {version_info.recall:.1%}")
        logger.info(f"F1 Score: {version_info.f1_score_value:.1%}")
        
        logger.info(f"\nRetraining Report:")
        logger.info(f"  Total Samples: {report.total_samples}")
        logger.info(f"  Historical: {report.historical_samples_used}")
        logger.info(f"  Synthetic: {report.synthetic_samples_used}")
        logger.info(f"  Accuracy Improvement: {report.accuracy_improvement:+.2%}")
        
        logger.info(f"\nRecommendations:")
        for rec in report.recommendations:
            logger.info(f"  - {rec}")
        
        audit_logger.log_system(
            f"Example retraining completed: Accuracy={version_info.accuracy:.1%}",
            action="EXAMPLE_RETRAINING"
        )
        
    except Exception as e:
        logger.error(f"Error in retraining pipeline: {str(e)}")


def example_model_versioning():
    """Example: List and retrieve model versions."""
    logger.info("Example 6: Model Versioning & Retrieval")
    
    pipeline = get_retraining_pipeline()
    
    logger.info("Available model versions:")
    versions = pipeline.list_model_versions()
    
    if versions:
        for v in versions[:5]:
            logger.info(f"  {v.version_id}")
            logger.info(f"    Formation: {v.formation_type}")
            logger.info(f"    Equipment: {v.equipment_type}")
            logger.info(f"    Power: {v.power_source}")
            logger.info(f"    Accuracy: {v.accuracy:.1%}")
            logger.info(f"    Date: {v.creation_date}")
        
        if len(versions) > 5:
            logger.info(f"  ... and {len(versions) - 5} more")
    else:
        logger.info("  No models found yet")


def main():
    """Run all examples."""
    logger.info("=" * 70)
    logger.info("Phase 1 - Historical Data Integration Examples")
    logger.info("=" * 70)
    
    try:
        example_connect_postgresql()
        logger.info("\n" + "=" * 70)
        
        example_load_csv_historical_data()
        logger.info("\n" + "=" * 70)
        
        example_well_risk_assessment()
        logger.info("\n" + "=" * 70)
        
        example_formation_model_training()
        logger.info("\n" + "=" * 70)
        
        example_retraining_pipeline()
        logger.info("\n" + "=" * 70)
        
        example_model_versioning()
        logger.info("\n" + "=" * 70)
        
        logger.info("\nAll examples completed successfully!")
        audit_logger.log_system("Phase 1 examples completed", action="EXAMPLE_COMPLETE")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
