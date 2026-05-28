"""
IoT and Telemetry API Endpoints
Handles IoT device management and telemetry data
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.models.user import User, UserRole
from app.models.equipment import Equipment
from app.models.telemetry import TelemetryData
from app.core.equipment_engine import EquipmentEngine
from core.mqtt_telemetry_client import MQTTTelemetryClient
from core.alarm_manager import get_alarm_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/devices", response_model=dict)
async def list_devices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all IoT devices that require active monitoring.
    Authored by Jhon Villegas
    """
    try:
        query = db.query(Equipment).filter(Equipment.requires_monitoring == True)
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER]:
            query = query.filter(Equipment.owner_id == current_user.id)
        
        devices = query.offset(skip).limit(limit).all()
        total = query.count()
        
        return {
            "devices": [d.to_dict() for d in devices],
            "total": total
        }
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/devices", response_model=dict)
async def register_device(
    device_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register new IoT device and force monitoring flag.
    Authored by Jhon Villegas
    """
    try:
        # Force active monitoring for IoT registered devices
        device_data["requires_monitoring"] = True
        engine = EquipmentEngine(db)
        new_device = engine.create_equipment(device_data, current_user.id)
        return {
            "device_id": new_device["id"],
            "status": "registered",
            "device": new_device
        }
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/devices/{device_id}/telemetry", response_model=dict)
async def get_device_telemetry(
    device_id: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical telemetry data for a specific device.
    Authored by Jhon Villegas
    """
    try:
        equipment = db.query(Equipment).filter(Equipment.id == device_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device/Equipment not found"
            )
            
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER] and equipment.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this device's telemetry"
            )
            
        query = db.query(TelemetryData).filter(TelemetryData.equipment_id == device_id)
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(TelemetryData.timestamp >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_time must be in ISO format"
                )
                
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(TelemetryData.timestamp <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_time must be in ISO format"
                )
                
        telemetry = query.order_by(TelemetryData.timestamp.desc()).all()
        return {
            "device_id": device_id,
            "telemetry": [t.to_dict() for t in telemetry]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/telemetry", response_model=dict)
async def publish_telemetry(
    telemetry_data: dict,
    db: Session = Depends(get_db)
):
    """
    Publish telemetry data from sensors, store in DB, and propagate via MQTT.
    Authored by Jhon Villegas
    """
    try:
        equipment_id = telemetry_data.get("equipment_id")
        if not equipment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="equipment_id is required in telemetry data"
            )
            
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated equipment not found"
            )
            
        # Parse timestamp
        ts_str = telemetry_data.get("timestamp")
        if ts_str:
            try:
                timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()
            
        # Create and persist telemetry data
        db_telemetry = TelemetryData(
            equipment_id=equipment_id,
            timestamp=timestamp,
            temperature_c=telemetry_data.get("temperature_c"),
            pressure_pa=telemetry_data.get("pressure_pa"),
            flow_rate_m3_s=telemetry_data.get("flow_rate_m3_s"),
            vibration_mm_s=telemetry_data.get("vibration_mm_s"),
            speed_rpm=telemetry_data.get("speed_rpm"),
            power_kw=telemetry_data.get("power_kw"),
            sensor_data=telemetry_data.get("sensor_data", {}),
            quality_score=telemetry_data.get("quality_score", 1.0),
            is_valid=int(telemetry_data.get("is_valid", True)),
            source=telemetry_data.get("source", "API"),
            device_id=telemetry_data.get("device_id")
        )
        
        db.add(db_telemetry)
        db.commit()
        db.refresh(db_telemetry)
        
        # Try to publish via MQTT
        try:
            mqtt_client = MQTTTelemetryClient()
            if mqtt_client.enabled and mqtt_client.connected:
                topic = f"petroflow/api/equipment/{equipment_id}/telemetry"
                mqtt_client.publish(topic, db_telemetry.to_dict())
        except Exception as mqtt_err:
            logger.warning(f"Failed to publish telemetry to MQTT: {mqtt_err}")
            
        # Run alarm manager evaluation
        try:
            alarm_mgr = get_alarm_manager()
            # Map telemetry fields to alarm parameters
            readings = {}
            if db_telemetry.temperature_c is not None:
                readings["discharge_temperature"] = db_telemetry.temperature_c
                readings["steam_temperature"] = db_telemetry.temperature_c
                readings["exhaust_temperature"] = db_telemetry.temperature_c
            if db_telemetry.pressure_pa is not None:
                # Convert Pa to Bar for alarm setpoints
                pressure_bar = db_telemetry.pressure_pa / 100000.0
                readings["inlet_pressure"] = pressure_bar
            if db_telemetry.flow_rate_m3_s is not None:
                # Flow rate
                readings["volumetric_flow"] = db_telemetry.flow_rate_m3_s
            if db_telemetry.vibration_mm_s is not None:
                readings["vibration"] = db_telemetry.vibration_mm_s
                readings["radial_vibration"] = db_telemetry.vibration_mm_s
                readings["axial_vibration"] = db_telemetry.vibration_mm_s
            if db_telemetry.speed_rpm is not None:
                readings["synchronous_speed"] = db_telemetry.speed_rpm
                
            alarm_mgr.evaluate(
                equipment_id=equipment.tag,
                equipment_type=equipment.equipment_type.value,
                readings=readings
            )
        except Exception as alarm_err:
            logger.error(f"Error evaluating alarms for telemetry: {alarm_err}")
            
        return {
            "status": "published",
            "telemetry_id": db_telemetry.id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/alarms", response_model=dict)
async def get_alarms(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get active or historical alarms, with RBAC protection.
    Authored by Jhon Villegas
    """
    try:
        alarm_mgr = get_alarm_manager()
        if active_only:
            alarms = alarm_mgr.get_active_alarms()
        else:
            alarms = alarm_mgr.get_all_alarms()
            
        # RBAC filtering: non-admin/engineers only see alarms for their owned equipment
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER]:
            user_equipments = db.query(Equipment).filter(Equipment.owner_id == current_user.id).all()
            user_tags = {eq.tag for eq in user_equipments}
            alarms = [a for a in alarms if a.equipment_id in user_tags]
            
        return {
            "alarms": [a.to_dict() for a in alarms],
            "total": len(alarms)
        }
    except Exception as e:
        logger.error(f"Error getting alarms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/alarms/{alarm_id}/acknowledge", response_model=dict)
async def acknowledge_alarm(
    alarm_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(UserRole.OPERATOR))
):
    """
    Acknowledge an alarm to confirm awareness (Operator role required).
    Authored by Jhon Villegas
    """
    try:
        alarm_mgr = get_alarm_manager()
        alarm = alarm_mgr._alarms.get(alarm_id)
        if not alarm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alarm not found"
            )
            
        # RBAC: non-admin/engineers can only acknowledge their owned equipment alarms
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER]:
            equipment = db.query(Equipment).filter(Equipment.tag == alarm.equipment_id).first()
            if not equipment or equipment.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to acknowledge alarms for this equipment"
                )
                
        success = alarm_mgr.acknowledge(alarm_id, current_user.username)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alarm already acknowledged or cleared"
            )
            
        return {
            "status": "acknowledged",
            "alarm_id": alarm_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alarm: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/alarms/{alarm_id}/shelve", response_model=dict)
async def shelve_alarm(
    alarm_id: str,
    reason_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(UserRole.ENGINEER))
):
    """
    Temporarily suppress/shelve an active alarm (Engineer role required).
    Authored by Jhon Villegas
    """
    try:
        reason = reason_data.get("reason")
        duration_hours = reason_data.get("duration_hours", 8.0)
        
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reason is mandatory for shelving an alarm (ISA-18.2 compliant)"
            )
            
        alarm_mgr = get_alarm_manager()
        alarm = alarm_mgr._alarms.get(alarm_id)
        if not alarm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alarm not found"
            )
            
        # RBAC: non-admin/engineers can only shelve their owned equipment alarms
        if current_user.role not in [UserRole.ADMIN, UserRole.ENGINEER]:
            equipment = db.query(Equipment).filter(Equipment.tag == alarm.equipment_id).first()
            if not equipment or equipment.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to shelve alarms for this equipment"
                )
                
        success = alarm_mgr.shelve(
            alarm_id=alarm_id,
            operator=current_user.username,
            reason=reason,
            duration_hours=duration_hours
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alarm could not be shelved"
            )
            
        return {
            "status": "shelved",
            "alarm_id": alarm_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error shelving alarm: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )