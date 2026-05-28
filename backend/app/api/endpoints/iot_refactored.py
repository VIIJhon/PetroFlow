"""
Refactored IoT and Telemetry API Endpoints (Phase 5)
Uses TelemetryProcessor via dependency injection
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.api.deps import (
    get_current_user,
    get_telemetry_processor,
    get_safety_validator
)
from app.models.user import User, UserRole
from app.models.equipment import Equipment
from app.models.telemetry import TelemetryData

# Phase 4 services
from app.core.telemetry import (
    TelemetryProcessor,
    TelemetryPoint,
    AnomalyDetection,
    ProcessingStats
)
from app.core.safety_envelope import SafetyEnvelopeValidator
from app.core.standards import EquipmentType, UnitSystem

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class TelemetryProcessRequest(BaseModel):
    """Request to process single telemetry point."""
    equipment_id: int = Field(..., description="Equipment database ID")
    parameters: Dict[str, float] = Field(..., description="Telemetry parameters")
    units: Dict[str, str] = Field(..., description="Units for each parameter")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    quality: float = Field(default=1.0, ge=0.0, le=1.0, description="Data quality score")
    source: str = Field(default="API", description="Data source identifier")


class BatchTelemetryRequest(BaseModel):
    """Request to process batch of telemetry points."""
    equipment_id: int = Field(..., description="Equipment database ID")
    data_points: List[Dict[str, Any]] = Field(..., description="List of telemetry points")
    unit_system: str = Field(default="SI", description="Unit system")


class TelemetryProcessResponse(BaseModel):
    """Response for telemetry processing."""
    telemetry_id: int
    equipment_id: int
    status: str
    validation_status: str
    anomalies_detected: int
    alarms_triggered: int
    processing_time_ms: float


class BatchProcessingResponse(BaseModel):
    """Response for batch telemetry processing."""
    total_points: int
    processed: int
    failed: int
    anomalies_detected: int
    processing_time_ms: float
    throughput_points_per_sec: float


class AnomalyResponse(BaseModel):
    """Response for anomaly detection."""
    equipment_id: int
    equipment_tag: str
    anomalies: List[Dict[str, Any]]
    time_range: Dict[str, str]


# ============================================================================
# Refactored Endpoints Using Services
# ============================================================================

@router.post("/telemetry/process", response_model=TelemetryProcessResponse)
async def process_telemetry_point(
    request: TelemetryProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    telemetry_processor: TelemetryProcessor = Depends(get_telemetry_processor)
):
    """
    Process single telemetry point using TelemetryProcessor.
    
    Includes validation, anomaly detection, and safety checks.
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Parse timestamp
        if request.timestamp:
            try:
                timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            except ValueError:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        # Create telemetry point
        telemetry_point = TelemetryPoint(
            equipment_id=equipment.tag,
            timestamp=timestamp,
            parameters=request.parameters,
            units=request.units,
            quality=request.quality,
            source=request.source
        )
        
        # Process telemetry using processor
        start_time = datetime.utcnow()
        processed_point, validation_result, anomalies = telemetry_processor.process_telemetry_point(
            telemetry_point=telemetry_point
        )
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Store in database
        db_telemetry = TelemetryData(
            equipment_id=equipment.id,
            timestamp=processed_point.timestamp,
            temperature_c=processed_point.parameters.get("temperature"),
            pressure_pa=processed_point.parameters.get("pressure"),
            flow_rate_m3_s=processed_point.parameters.get("flow_rate"),
            vibration_mm_s=processed_point.parameters.get("vibration"),
            speed_rpm=processed_point.parameters.get("speed"),
            power_kw=processed_point.parameters.get("power"),
            sensor_data=processed_point.parameters,
            quality_score=processed_point.quality,
            is_valid=1 if validation_result and validation_result.overall_status.value == "OK" else 0,
            source=processed_point.source
        )
        db.add(db_telemetry)
        db.commit()
        db.refresh(db_telemetry)
        
        # Count alarms
        alarms_count = len(validation_result.alarms) if validation_result else 0
        
        return TelemetryProcessResponse(
            telemetry_id=db_telemetry.id,
            equipment_id=equipment.id,
            status="processed",
            validation_status=validation_result.overall_status.value if validation_result else "UNKNOWN",
            anomalies_detected=len(anomalies),
            alarms_triggered=alarms_count,
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telemetry processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Telemetry processing failed: {str(e)}"
        )


@router.post("/telemetry/batch", response_model=BatchProcessingResponse)
async def process_batch_telemetry(
    request: BatchTelemetryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    telemetry_processor: TelemetryProcessor = Depends(get_telemetry_processor)
):
    """
    Process batch of telemetry points using TelemetryProcessor.
    
    High-performance batch processing with vectorization.
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Convert data points to TelemetryPoint objects
        telemetry_points = []
        for data_point in request.data_points:
            timestamp = datetime.fromisoformat(
                data_point.get("timestamp", datetime.utcnow().isoformat()).replace('Z', '+00:00')
            )
            
            point = TelemetryPoint(
                equipment_id=equipment.tag,
                timestamp=timestamp,
                parameters=data_point.get("parameters", {}),
                units=data_point.get("units", {}),
                quality=data_point.get("quality", 1.0),
                source=data_point.get("source", "API")
            )
            telemetry_points.append(point)
        
        # Process batch
        start_time = datetime.utcnow()
        stats: ProcessingStats = telemetry_processor.process_batch(
            telemetry_points=telemetry_points
        )
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Store valid points in database (simplified - in production, use bulk insert)
        processed_count = 0
        for point in telemetry_points[:stats.valid_points]:  # Only store valid points
            try:
                db_telemetry = TelemetryData(
                    equipment_id=equipment.id,
                    timestamp=point.timestamp,
                    temperature_c=point.parameters.get("temperature"),
                    pressure_pa=point.parameters.get("pressure"),
                    flow_rate_m3_s=point.parameters.get("flow_rate"),
                    vibration_mm_s=point.parameters.get("vibration"),
                    speed_rpm=point.parameters.get("speed"),
                    power_kw=point.parameters.get("power"),
                    sensor_data=point.parameters,
                    quality_score=point.quality,
                    is_valid=1,
                    source=point.source
                )
                db.add(db_telemetry)
                processed_count += 1
            except Exception as e:
                logger.warning(f"Failed to store telemetry point: {e}")
        
        db.commit()
        
        return BatchProcessingResponse(
            total_points=stats.total_points_processed,
            processed=processed_count,
            failed=stats.invalid_points,
            anomalies_detected=stats.anomalies_detected,
            processing_time_ms=processing_time,
            throughput_points_per_sec=stats.throughput_points_per_sec
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.get("/telemetry/anomalies", response_model=AnomalyResponse)
async def get_telemetry_anomalies(
    equipment_id: int,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    telemetry_processor: TelemetryProcessor = Depends(get_telemetry_processor)
):
    """
    Get detected anomalies for equipment using TelemetryProcessor.
    
    Returns anomalies detected in the specified time window.
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Get recent telemetry from buffer
        recent_points = telemetry_processor.get_recent_telemetry(
            equipment_id=equipment.tag,
            count=1000  # Last 1000 points
        )
        
        # Get anomalies from processor
        anomalies = telemetry_processor.get_anomalies(
            equipment_id=equipment.tag,
            time_window_hours=hours
        )
        
        # Format anomalies for response
        anomalies_list = [
            {
                "parameter": anomaly.parameter,
                "timestamp": anomaly.timestamp.isoformat(),
                "value": anomaly.value,
                "expected_value": anomaly.expected_value,
                "deviation": anomaly.deviation,
                "z_score": anomaly.z_score,
                "severity": anomaly.severity,
                "confidence": anomaly.confidence
            }
            for anomaly in anomalies
        ]
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        return AnomalyResponse(
            equipment_id=equipment.id,
            equipment_tag=equipment.tag,
            anomalies=anomalies_list,
            time_range={
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anomaly retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly retrieval failed: {str(e)}"
        )


@router.get("/telemetry/stats", response_model=Dict[str, Any])
async def get_telemetry_statistics(
    equipment_id: int,
    parameter: str,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    telemetry_processor: TelemetryProcessor = Depends(get_telemetry_processor)
):
    """
    Get statistical aggregation of telemetry data.
    
    Returns mean, median, std, percentiles for specified parameter.
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get aggregation from processor
        aggregation = telemetry_processor.aggregate_telemetry(
            equipment_id=equipment.tag,
            parameter=parameter,
            start_time=start_time,
            end_time=end_time
        )
        
        if not aggregation:
            return {
                "equipment_id": equipment.id,
                "parameter": parameter,
                "message": "No data available for specified time range"
            }
        
        return {
            "equipment_id": equipment.id,
            "equipment_tag": equipment.tag,
            "parameter": parameter,
            "time_range": {
                "start": aggregation.start_time.isoformat(),
                "end": aggregation.end_time.isoformat()
            },
            "statistics": {
                "count": aggregation.count,
                "mean": aggregation.mean,
                "median": aggregation.median,
                "std": aggregation.std,
                "min": aggregation.min,
                "max": aggregation.max,
                "percentile_25": aggregation.percentile_25,
                "percentile_75": aggregation.percentile_75,
                "percentile_95": aggregation.percentile_95,
                "percentile_99": aggregation.percentile_99
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Statistics calculation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statistics calculation failed: {str(e)}"
        )


@router.post("/telemetry/clear-buffer/{equipment_id}", response_model=Dict[str, str])
async def clear_telemetry_buffer(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    telemetry_processor: TelemetryProcessor = Depends(get_telemetry_processor)
):
    """
    Clear telemetry buffer for equipment (admin/engineer only).
    """
    try:
        # Check permissions
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Clear buffer
        telemetry_processor.clear_buffer(equipment_id=equipment.tag)
        
        return {
            "status": "success",
            "message": f"Telemetry buffer cleared for equipment {equipment.tag}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Buffer clear failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Buffer clear failed: {str(e)}"
        )