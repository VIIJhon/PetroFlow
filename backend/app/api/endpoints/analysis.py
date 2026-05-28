"""
Analysis API Endpoints
Handles data analysis and reporting
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.equipment import Equipment
from app.models.analysis import AnalysisResult, AnalysisType, AnalysisSeverity
from app.models.telemetry import TelemetryData
from app.core.equipment_engine import EquipmentEngine

# Failure prediction and ML
from core.failure_prediction_engine import (
    train_pump_model,
    train_compressor_model,
    train_turbine_model,
    train_failure_prediction_model,
    predict_pump_failure,
    predict_compressor_failure,
    predict_turbine_failure,
    predict_failure,
    get_risk_level
)

# AI report generator
from core.ai_report_generator import AIReportGenerator

# Oil Well Geological and Context Analyzer
from core.well_context_analyzer import get_well_analyzer

logger = logging.getLogger(__name__)
router = APIRouter()

# Global memory cache for ML models to avoid retraining on every request
_MODELS_CACHE = {}


def get_ml_model(eq_type: str):
    """
    Get trained ML model and scaler from memory cache or train on-demand
    Authored by Jhon Villegas
    """
    if eq_type not in _MODELS_CACHE:
        try:
            if eq_type == "pump":
                _MODELS_CACHE[eq_type] = train_pump_model()
            elif eq_type == "compressor":
                _MODELS_CACHE[eq_type] = train_compressor_model()
            elif eq_type == "turbine":
                _MODELS_CACHE[eq_type] = train_turbine_model()
            else:
                _MODELS_CACHE[eq_type] = train_failure_prediction_model()
        except Exception as e:
            logger.error(f"Error training model for {eq_type}: {e}")
            raise RuntimeError(f"Could not initialize ML model for {eq_type}")
    return _MODELS_CACHE[eq_type]


@router.post("/performance", response_model=dict)
async def analyze_performance(
    analysis_params: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze equipment performance and save result.
    Authored by Jhon Villegas
    """
    try:
        equipment_id = analysis_params.get("equipment_id")
        if not equipment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="equipment_id is required in analysis_params"
            )

        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )

        # RBAC Check: standard users can only analyze their own equipment
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER] and equipment.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this equipment"
            )

        engine = EquipmentEngine(db)
        metrics = engine.get_performance_metrics(equipment.id, current_user.id)

        # Fetch latest telemetry to define severity thresholds
        last_telemetry = db.query(TelemetryData).filter(
            TelemetryData.equipment_id == equipment.id
        ).order_by(TelemetryData.timestamp.desc()).first()

        vibration = last_telemetry.vibration_mm_s if (last_telemetry and last_telemetry.vibration_mm_s is not None) else 1.5
        temp = last_telemetry.temperature_c if (last_telemetry and last_telemetry.temperature_c is not None) else 65.0

        if vibration > 10.0 or temp > 90.0:
            severity = AnalysisSeverity.CRITICAL
        elif vibration > 5.0 or temp > 75.0:
            severity = AnalysisSeverity.WARNING
        else:
            severity = AnalysisSeverity.NORMAL

        recommendations = []
        if severity == AnalysisSeverity.CRITICAL:
            if temp > 90.0:
                recommendations.append("High bearing temperature. Inspect cooling loop and lubrication levels immediately.")
            if vibration > 10.0:
                recommendations.append("Severe vibration detected. Schedule immediate shutdown and check shaft alignment.")
        elif severity == AnalysisSeverity.WARNING:
            if temp > 75.0:
                recommendations.append("Elevated temperature. Monitor cooling efficiency closely.")
            if vibration > 5.0:
                recommendations.append("Moderate vibration. Schedule alignment inspection during next maintenance window.")
        else:
            recommendations.append("Equipment is operating within nominal parameters. Continue routine monitoring.")

        # Save to DB
        db_result = AnalysisResult(
            analysis_type=AnalysisType.PERFORMANCE,
            name=f"Performance Analysis - {equipment.tag}",
            description=f"Automated physical performance evaluation for {equipment.tag}",
            equipment_id=equipment.id,
            results={
                "efficiency": metrics.get("efficiency", 0.85),
                "uptime": metrics.get("uptime", 0.98),
                "maintenance_score": metrics.get("maintenance_score", 0.90),
                "vibration_mm_s": vibration,
                "temperature_c": temp
            },
            metrics=metrics,
            recommendations=recommendations,
            severity=severity,
            confidence_score=0.95,
            owner_id=current_user.id
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)

        return {
            "status": "success",
            "analysis": db_result.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/predictive-maintenance", response_model=dict)
async def predictive_maintenance(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run machine learning predictive maintenance failure prediction and save result.
    Authored by Jhon Villegas
    """
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )

        # RBAC Check: standard users can only analyze their own equipment
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER] and equipment.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this equipment"
            )

        # Retrieve last telemetry
        last_telemetry = db.query(TelemetryData).filter(
            TelemetryData.equipment_id == equipment.id
        ).order_by(TelemetryData.timestamp.desc()).first()

        sensor_data = last_telemetry.sensor_data if (last_telemetry and last_telemetry.sensor_data) else {}
        specs = equipment.specifications or {}

        eq_type = equipment.equipment_type.value

        # Train/load ML model
        model, scaler, accuracy, feature_importance, _, _ = get_ml_model(eq_type)

        # Predict based on equipment type
        if eq_type == "pump":
            discharge_temp = float(last_telemetry.temperature_c if last_telemetry and last_telemetry.temperature_c is not None else specs.get("rated_temp_c", 65.0))
            inlet_pressure = float(sensor_data.get("inlet_pressure") or (last_telemetry.pressure_pa / 100000.0 / 10.0 if last_telemetry and last_telemetry.pressure_pa else 1.5))
            outlet_pressure = float(sensor_data.get("outlet_pressure") or (last_telemetry.pressure_pa / 100000.0 if last_telemetry and last_telemetry.pressure_pa else 20.0))
            volumetric_flow = float(last_telemetry.flow_rate_m3_s * 3600.0 if last_telemetry and last_telemetry.flow_rate_m3_s is not None else specs.get("rated_flow_m3_h", 150.0))
            available_npsh = float(sensor_data.get("available_npsh") or specs.get("npsh_required", 4.0))

            failure_prob, category, category_name, prob_dict = predict_pump_failure(
                model, scaler, discharge_temp, inlet_pressure, outlet_pressure, volumetric_flow, available_npsh
            )
        elif eq_type == "compressor":
            discharge_temp = float(last_telemetry.temperature_c if last_telemetry and last_telemetry.temperature_c is not None else specs.get("rated_temp_c", 85.0))
            compression_ratio = float(sensor_data.get("compression_ratio") or specs.get("compression_ratio", 4.5))
            radial_vibration = float(last_telemetry.vibration_mm_s if last_telemetry and last_telemetry.vibration_mm_s is not None else specs.get("vibration_limit", 1.5))
            axial_vibration = float(sensor_data.get("axial_vibration") or (last_telemetry.vibration_mm_s * 0.8 if last_telemetry and last_telemetry.vibration_mm_s is not None else 1.2))
            relative_humidity = float(sensor_data.get("relative_humidity") or specs.get("relative_humidity", 55.0))

            failure_prob, category, category_name, prob_dict = predict_compressor_failure(
                model, scaler, discharge_temp, compression_ratio, radial_vibration, axial_vibration, relative_humidity
            )
        elif eq_type == "turbine":
            steam_temp = float(last_telemetry.temperature_c if last_telemetry and last_telemetry.temperature_c is not None else specs.get("rated_temp_c", 250.0))
            inlet_pressure = float(last_telemetry.pressure_pa / 100000.0 if last_telemetry and last_telemetry.pressure_pa is not None else specs.get("rated_pressure_bar", 25.0))
            axial_vibration = float(last_telemetry.vibration_mm_s if last_telemetry and last_telemetry.vibration_mm_s is not None else specs.get("vibration_limit", 1.0))
            synchronous_speed = float(last_telemetry.speed_rpm if last_telemetry and last_telemetry.speed_rpm is not None else specs.get("rated_speed_rpm", 3000.0))
            exhaust_temp = float(sensor_data.get("exhaust_temperature") or specs.get("exhaust_temp_c", 120.0))

            failure_prob, category, category_name, prob_dict = predict_turbine_failure(
                model, scaler, steam_temp, inlet_pressure, axial_vibration, synchronous_speed, exhaust_temp
            )
        else:
            # Generic fallback model
            features_dict = {
                'temperature': last_telemetry.temperature_c if last_telemetry else 65.0,
                'pressure': (last_telemetry.pressure_pa / 100000.0) if last_telemetry and last_telemetry.pressure_pa else 15.0,
                'vibration': last_telemetry.vibration_mm_s if last_telemetry else 0.8,
                'operating_hours': float(sensor_data.get("operating_hours", 5000.0)),
                'rpm': last_telemetry.speed_rpm if last_telemetry else 3000.0
            }
            failure_prob, category, category_name, prob_dict = predict_failure(model, scaler, features_dict)

        # Estimate RUL based on failure probability
        rul_hours = (1.0 - (failure_prob / 100.0)) * 10000.0
        rul_hours = max(100.0, rul_hours)  # Lower bound of 100 hours

        risk_level, _ = get_risk_level(failure_prob)
        if risk_level == "Low Risk":
            severity = AnalysisSeverity.NORMAL
        elif risk_level == "Medium Risk":
            severity = AnalysisSeverity.WARNING
        else:
            severity = AnalysisSeverity.CRITICAL

        # Compile recommendations
        recommendations = []
        if severity == AnalysisSeverity.CRITICAL:
            recommendations = [
                "Schedule immediate technical shutdown and inspection.",
                "Verify vibration levels manually with a portable analyzer.",
                "Check lubrication status and dynamic oil contamination levels."
            ]
        elif severity == AnalysisSeverity.WARNING:
            recommendations = [
                "Increase sensor telemetry sampling frequency.",
                "Schedule maintenance inspection within next 48 operating hours.",
                "Review operating parameters to reduce load or speed if possible."
            ]
        else:
            recommendations = [
                "Maintain regular operations.",
                "Continue standard routine inspection schedule."
            ]

        # Fault metadata
        fault_detected = (severity != AnalysisSeverity.NORMAL)
        fault_mode = category_name if fault_detected else None
        root_cause = None
        if fault_detected:
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            root_cause = f"High failure risk driven primarily by key features: {', '.join([f'{k} ({v*100:.1f}%)' for k, v in sorted_features[:2]])}"

        # Save to DB
        db_result = AnalysisResult(
            analysis_type=AnalysisType.PREDICTIVE_MAINTENANCE,
            name=f"Predictive Maintenance - {equipment.tag}",
            description=f"Automated failure prediction for {equipment.tag}",
            equipment_id=equipment.id,
            results={
                "failure_probability": float(failure_prob),
                "risk_level": risk_level,
                "category_name": category_name,
                "probabilities": {k: float(v) for k, v in prob_dict.items()},
                "rul_hours": float(rul_hours)
            },
            metrics={
                "model_accuracy": float(accuracy),
                "rul_hours": float(rul_hours),
                "failure_probability": float(failure_prob)
            },
            recommendations=recommendations,
            severity=severity,
            confidence_score=float(prob_dict.get(category_name, 100.0) / 100.0),
            fault_detected=fault_detected,
            fault_mode=fault_mode,
            root_cause=root_cause,
            owner_id=current_user.id,
            feature_importance={k: float(v) for k, v in feature_importance.items()}
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)

        return {
            "predictions": [db_result.results],
            "recommendations": db_result.recommendations,
            "analysis_id": db_result.id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in predictive maintenance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/reports", response_model=dict)
async def get_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analysis reports paginated. Regular users can only see their own reports.
    Authored by Jhon Villegas
    """
    try:
        query = db.query(AnalysisResult)
        if current_user.role != UserRole.ADMIN:
            query = query.filter(AnalysisResult.owner_id == current_user.id)

        total = query.count()
        reports = query.order_by(AnalysisResult.created_at.desc()).offset(skip).limit(limit).all()

        return {
            "reports": [r.to_dict() for r in reports],
            "total": total
        }
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate-report", response_model=dict)
async def generate_report(
    report_params: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate an AI-powered technical report using AIDiagnosticEngine and AIReportGenerator.
    Authored by Jhon Villegas
    """
    try:
        equipment_id = report_params.get("equipment_id")
        if not equipment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="equipment_id is required in report_params"
            )

        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )

        # RBAC Check: standard users can only generate reports for their own equipment
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER] and equipment.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this equipment"
            )

        # Retrieve last telemetry
        last_telemetry = db.query(TelemetryData).filter(
            TelemetryData.equipment_id == equipment.id
        ).order_by(TelemetryData.timestamp.desc()).first()

        if not last_telemetry:
            sensor_data = {
                "temperature": 65.0,
                "pressure": 15.0,
                "vibration": 1.5,
                "flow_rate": 150.0
            }
        else:
            sensor_data = {
                "temperature": last_telemetry.temperature_c,
                "pressure": last_telemetry.pressure_pa / 100000.0 if last_telemetry.pressure_pa else 0.0,
                "vibration": last_telemetry.vibration_mm_s,
                "flow_rate": last_telemetry.flow_rate_m3_s * 3600.0 if last_telemetry.flow_rate_m3_s else 0.0,
                "speed": last_telemetry.speed_rpm,
                "power": last_telemetry.power_kw
            }
            if last_telemetry.sensor_data:
                sensor_data.update(last_telemetry.sensor_data)

        # Fetch historical telemetry (last 30 points)
        history = db.query(TelemetryData).filter(
            TelemetryData.equipment_id == equipment.id
        ).order_by(TelemetryData.timestamp.desc()).limit(30).all()

        historical_data = []
        for t in reversed(history):
            h_dict = {
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                "temperature": t.temperature_c,
                "pressure": t.pressure_pa / 100000.0 if t.pressure_pa else 0.0,
                "vibration": t.vibration_mm_s,
                "flow_rate": t.flow_rate_m3_s * 3600.0 if t.flow_rate_m3_s else 0.0,
                "speed": t.speed_rpm,
                "power": t.power_kw
            }
            if t.sensor_data:
                h_dict.update(t.sensor_data)
            historical_data.append(h_dict)

        # AI Report Generation
        report_generator = AIReportGenerator()
        report = report_generator.generate_report(
            equipment_id=str(equipment.id),
            equipment_type=equipment.equipment_type.value,
            sensor_data=sensor_data,
            historical_data=historical_data,
            language=report_params.get("language", "en"),
            report_type=report_params.get("report_type", "comprehensive")
        )

        severity = AnalysisSeverity.NORMAL
        if any(s.priority in ["high", "critical"] for s in report.sections):
            severity = AnalysisSeverity.WARNING

        # Persist report in AnalysisResult database
        db_result = AnalysisResult(
            analysis_type=AnalysisType.CAUSAL_DIAGNOSIS,
            name=report.title,
            description=f"AI Causal Diagnosis Report for {equipment.tag}",
            equipment_id=equipment.id,
            results={
                "report_id": report.report_id,
                "executive_summary": report.executive_summary,
                "sections": [
                    {
                        "title": s.title,
                        "content": s.content,
                        "priority": s.priority
                    } for s in report.sections
                ],
                "metadata": report.metadata
            },
            metrics={
                "data_points_analyzed": len(historical_data),
                "report_type": report.metadata.get("report_type")
            },
            recommendations=report.recommendations,
            severity=severity,
            confidence_score=0.90,
            owner_id=current_user.id
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)

        return {
            "report_id": db_result.id,
            "status": "generated",
            "title": report.title,
            "executive_summary": report.executive_summary
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/well-context", response_model=dict)
async def analyze_well_context(
    params: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform a high-fidelity geological and fluid-dynamic risk assessment for an oil well.
    Calculates safety derating factors, expected failure categories, and outputs expert prescriptive measures.
    Authored by Jhon Villegas
    """
    try:
        # Extract variables from input parameters
        depth = float(params.get("depth_meters", 3000.0))
        bottom_hole_temp = float(params.get("bottom_hole_temp", 95.0))
        oil_viscosity = float(params.get("oil_viscosity_cst", 80.0))
        api_gravity = float(params.get("api_gravity", 24.0))
        formation_type = str(params.get("formation_type", "Sandstone"))
        
        gas_oil_ratio = params.get("gas_oil_ratio")
        if gas_oil_ratio is not None and str(gas_oil_ratio).strip() != "":
            gas_oil_ratio = float(gas_oil_ratio)
        else:
            gas_oil_ratio = None
            
        water_cut = params.get("water_cut_percent")
        if water_cut is not None and str(water_cut).strip() != "":
            water_cut = float(water_cut)
        else:
            water_cut = None
            
        subsea = bool(params.get("subsea", False))
        
        # Get singleton well analyzer instance
        analyzer = get_well_analyzer()
        
        # Assess well risks
        assessment = analyzer.assess_well_risk(
            depth_meters=depth,
            bottom_hole_temp=bottom_hole_temp,
            oil_viscosity_cst=oil_viscosity,
            api_gravity=api_gravity,
            formation_type=formation_type,
            gas_oil_ratio=gas_oil_ratio,
            water_cut_percent=water_cut,
            subsea=subsea
        )
        
        # Calculate equipment derating factors based on risk scores
        derating = analyzer.get_equipment_derating_factors(
            equipment_type="pump",  # Default generic rotating pump context
            well_type=assessment.well_type,
            thermal_risk=assessment.thermal_risk,
            depth_risk=assessment.depth_risk,
            viscosity_risk=assessment.viscosity_risk
        )
        
        # Format a premium structured report summary
        text_report = analyzer.format_risk_assessment(assessment)
        
        # Add dynamic predictions & failures description
        primary_modes = analyzer.get_formation_failure_modes(formation_type)
        
        # Render a gorgeous response payload
        results = {
            "status": "success",
            "well_type": assessment.well_type.value,
            "production_profile": assessment.production_profile.value,
            "overall_risk_score": float(assessment.overall_risk_score * 100),
            "thermal_risk": float(assessment.thermal_risk * 100),
            "depth_risk": float(assessment.depth_risk * 100),
            "viscosity_risk": float(assessment.viscosity_risk * 100),
            "formation_risk": float(assessment.formation_risk * 100),
            "recommended_monitoring_interval_hours": int(assessment.recommended_monitoring_interval_hours),
            "critical_parameters": assessment.critical_parameters,
            "maintenance_recommendations": assessment.maintenance_recommendations,
            "derating": {
                "flow_rate_factor": float(derating.get("flow_rate_factor", 1.0)),
                "head_factor": float(derating.get("head_factor", 1.0)),
                "life_expectancy_factor": float(derating.get("life_expectancy_factor", 1.0)),
                "frequency_inspection_factor": float(derating.get("frequency_inspection_factor", 1.0)),
                "thermal_stress_multiplier": float(derating.get("thermal_stress_multiplier", 1.0)),
                "erosion_multiplier": float(derating.get("erosion_multiplier", 1.0))
            },
            "failure_modes": {
                "primary": primary_modes.get("primary", "Desgaste estándar"),
                "secondary": primary_modes.get("secondary", "Monitoreo rutinario"),
                "risk_factor": float(primary_modes.get("risk_factor", 1.0))
            },
            "text_report": text_report,
            "timestamp": datetime.utcnow().isoformat(),
            "signature": "Jhon Villegas - Líder de Ingeniería PetroFlow Suite"
        }
        
        # Ensure we have a valid equipment_id (nullable=False constraint)
        eq_id = params.get("equipment_id")
        if not eq_id:
            first_eq = db.query(Equipment).first()
            if first_eq:
                eq_id = first_eq.id
            else:
                from app.models.equipment import EquipmentType, EquipmentStatus
                dummy_eq = Equipment(
                    tag="WELL-DEFAULT-1",
                    name="Default Geological Well Asset",
                    equipment_type=EquipmentType.PUMP,
                    status=EquipmentStatus.OPERATIONAL,
                    owner_id=current_user.id,
                    is_active=True
                )
                db.add(dummy_eq)
                db.commit()
                db.refresh(dummy_eq)
                eq_id = dummy_eq.id

        # Save to database under AnalysisResult as PERFORMANCE type (mapped as compat or generic)
        db_result = AnalysisResult(
            analysis_type=AnalysisType.PERFORMANCE,  # Map to standard enum to avoid migration issues
            name=f"Well Geological Risk Analysis - Formation: {formation_type}",
            description=f"Geological, fluid-dynamics and operational failure prediction for {formation_type} well.",
            equipment_id=eq_id,
            results=results,
            metrics={
                "overall_risk": float(assessment.overall_risk_score),
                "depth_meters": depth,
                "temperature_c": bottom_hole_temp,
                "viscosity_cst": oil_viscosity
            },
            recommendations=assessment.maintenance_recommendations,
            severity=AnalysisSeverity.CRITICAL if assessment.overall_risk_score > 0.7 else (AnalysisSeverity.WARNING if assessment.overall_risk_score > 0.3 else AnalysisSeverity.NORMAL),
            confidence_score=0.92,
            owner_id=current_user.id
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)
        
        results["analysis_id"] = db_result.id
        return results
        
    except Exception as e:
        logger.error(f"Error in well context analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute well context geological analysis: {str(e)}"
        )