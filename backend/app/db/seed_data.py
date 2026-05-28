"""
Database Seed Data Script
Populate database with sample data for development and testing
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
import random

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.equipment import Equipment, EquipmentType, EquipmentStatus
from app.models.simulation import Simulation, SimulationType
from app.models.telemetry import TelemetryData
from app.models.analysis import AnalysisResult, AnalysisType, AnalysisSeverity

logger = logging.getLogger(__name__)


def load_equipment_config() -> dict:
    """Load equipment configuration from JSON file"""
    try:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "equipment_config.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load equipment config: {e}")
        return {}


def seed_users(db: Session) -> list[User]:
    """
    Create sample users with different roles
    
    Args:
        db: Database session
        
    Returns:
        List of created users
    """
    users_data = [
        {
            "email": "admin@petroflow.com",
            "username": "admin",
            "password": "admin123",
            "full_name": "System Administrator",
            "role": UserRole.ADMIN,
            "company": "PetroFlow",
            "department": "IT",
        },
        {
            "email": "engineer@petroflow.com",
            "username": "engineer",
            "password": "engineer123",
            "full_name": "John Engineer",
            "role": UserRole.ENGINEER,
            "company": "PetroFlow",
            "department": "Engineering",
        },
        {
            "email": "operator@petroflow.com",
            "username": "operator",
            "password": "operator123",
            "full_name": "Jane Operator",
            "role": UserRole.OPERATOR,
            "company": "PetroFlow",
            "department": "Operations",
        },
        {
            "email": "viewer@petroflow.com",
            "username": "viewer",
            "password": "viewer123",
            "full_name": "Bob Viewer",
            "role": UserRole.VIEWER,
            "company": "PetroFlow",
            "department": "Management",
        },
    ]
    
    created_users = []
    
    for user_data in users_data:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            logger.info(f"User {user_data['email']} already exists, skipping")
            created_users.append(existing_user)
            continue
        
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=user_data["full_name"],
            role=user_data["role"],
            is_active=True,
            is_verified=True,
            company=user_data["company"],
            department=user_data["department"],
        )
        
        db.add(user)
        created_users.append(user)
        logger.info(f"Created user: {user.email}")
    
    db.commit()
    return created_users


def seed_equipment(db: Session, owner: User) -> list[Equipment]:
    """
    Create sample equipment from configuration
    
    Args:
        db: Database session
        owner: User who owns the equipment
        
    Returns:
        List of created equipment
    """
    equipment_data = [
        {
            "tag": "P-101",
            "name": "Main Feed Pump",
            "equipment_type": EquipmentType.PUMP,
            "status": EquipmentStatus.OPERATIONAL,
            "location": "Process Unit 1",
            "facility": "Main Plant",
            "unit": "Feed System",
            "manufacturer": "Sulzer",
            "model": "CPT-100",
            "serial_number": "SN-2023-001",
            "specifications": {
                "type": "Centrifugal",
                "stages": 3,
                "impeller_diameter_mm": 250,
                "casing_material": "316 Stainless Steel"
            },
            "operating_parameters": {
                "flow_rate_m3h": 150,
                "head_m": 80,
                "speed_rpm": 2950,
                "temperature_c": 60
            },
            "rated_capacity": 150.0,
            "rated_power_kw": 45.0,
            "efficiency": 0.78,
            "is_critical": True,
        },
        {
            "tag": "C-201",
            "name": "Gas Compressor",
            "equipment_type": EquipmentType.COMPRESSOR,
            "status": EquipmentStatus.OPERATIONAL,
            "location": "Compression Station",
            "facility": "Main Plant",
            "unit": "Gas Processing",
            "manufacturer": "Atlas Copco",
            "model": "GA-250",
            "serial_number": "SN-2023-002",
            "specifications": {
                "type": "Rotary Screw",
                "stages": 2,
                "compression_ratio": 8.5,
                "cooling": "Air Cooled"
            },
            "operating_parameters": {
                "suction_pressure_bar": 1.5,
                "discharge_pressure_bar": 12.0,
                "flow_rate_m3h": 1200,
                "temperature_c": 85
            },
            "rated_capacity": 1200.0,
            "rated_power_kw": 250.0,
            "efficiency": 0.85,
            "is_critical": True,
        },
        {
            "tag": "T-301",
            "name": "Steam Turbine",
            "equipment_type": EquipmentType.TURBINE,
            "status": EquipmentStatus.OPERATIONAL,
            "location": "Power Generation",
            "facility": "Main Plant",
            "unit": "Utilities",
            "manufacturer": "Siemens",
            "model": "SST-600",
            "serial_number": "SN-2023-003",
            "specifications": {
                "type": "Condensing",
                "stages": 5,
                "blade_material": "Inconel 718",
                "governor_type": "Electronic"
            },
            "operating_parameters": {
                "inlet_pressure_bar": 42.0,
                "inlet_temperature_c": 450,
                "speed_rpm": 5000,
                "power_output_kw": 5000
            },
            "rated_capacity": 5000.0,
            "rated_power_kw": 5000.0,
            "efficiency": 0.82,
            "is_critical": True,
        },
        {
            "tag": "E-401",
            "name": "Shell & Tube Heat Exchanger",
            "equipment_type": EquipmentType.HEAT_EXCHANGER,
            "status": EquipmentStatus.OPERATIONAL,
            "location": "Process Unit 2",
            "facility": "Main Plant",
            "unit": "Heat Recovery",
            "manufacturer": "Alfa Laval",
            "model": "AlfaNova-52",
            "serial_number": "SN-2023-004",
            "specifications": {
                "type": "Shell and Tube",
                "surface_area_m2": 52.0,
                "tube_material": "316L Stainless Steel",
                "shell_material": "Carbon Steel"
            },
            "operating_parameters": {
                "hot_side_inlet_temp_c": 120,
                "hot_side_outlet_temp_c": 60,
                "cold_side_inlet_temp_c": 30,
                "cold_side_outlet_temp_c": 90,
                "flow_rate_m3h": 80
            },
            "rated_capacity": 80.0,
            "rated_power_kw": 0.0,
            "efficiency": 0.88,
            "is_critical": False,
        },
        {
            "tag": "V-501",
            "name": "Control Valve",
            "equipment_type": EquipmentType.VALVE,
            "status": EquipmentStatus.OPERATIONAL,
            "location": "Process Unit 1",
            "facility": "Main Plant",
            "unit": "Flow Control",
            "manufacturer": "Fisher",
            "model": "ED-3000",
            "serial_number": "SN-2023-005",
            "specifications": {
                "type": "Globe Control",
                "size_inches": 4,
                "cv": 120,
                "actuator": "Pneumatic"
            },
            "operating_parameters": {
                "inlet_pressure_bar": 15.0,
                "outlet_pressure_bar": 8.0,
                "flow_rate_m3h": 100,
                "position_percent": 65
            },
            "rated_capacity": 150.0,
            "rated_power_kw": 0.0,
            "efficiency": 0.95,
            "is_critical": False,
        },
    ]
    
    created_equipment = []
    
    for eq_data in equipment_data:
        # Check if equipment already exists
        existing_eq = db.query(Equipment).filter(Equipment.tag == eq_data["tag"]).first()
        if existing_eq:
            logger.info(f"Equipment {eq_data['tag']} already exists, skipping")
            created_equipment.append(existing_eq)
            continue
        
        equipment = Equipment(
            owner_id=owner.id,
            installation_date=datetime.now() - timedelta(days=random.randint(365, 1825)),
            commissioning_date=datetime.now() - timedelta(days=random.randint(300, 1800)),
            last_maintenance_date=datetime.now() - timedelta(days=random.randint(30, 180)),
            next_maintenance_date=datetime.now() + timedelta(days=random.randint(30, 180)),
            operating_hours=random.uniform(5000, 50000),
            start_count=random.randint(100, 5000),
            **eq_data
        )
        
        db.add(equipment)
        created_equipment.append(equipment)
        logger.info(f"Created equipment: {equipment.tag}")
    
    db.commit()
    return created_equipment


def seed_simulations(db: Session, equipment_list: list[Equipment], owner: User) -> list[Simulation]:
    """
    Create sample simulations
    
    Args:
        db: Database session
        equipment_list: List of equipment to create simulations for
        owner: User who owns the simulations
        
    Returns:
        List of created simulations
    """
    simulations = []
    
    for equipment in equipment_list[:3]:  # Create simulations for first 3 equipment
        simulation = Simulation(
            name=f"{equipment.name} - Dynamic Analysis",
            description=f"Dynamic simulation for {equipment.tag}",
            simulation_type=SimulationType.DYNAMIC,
            configuration={
                "time_step": 0.01,
                "duration": 100.0,
                "solver": "RK45",
                "tolerance": 1e-6
            },
            initial_conditions={
                "pressure": 10.0,
                "temperature": 25.0,
                "flow_rate": 100.0
            },
            boundary_conditions={
                "inlet_pressure": 15.0,
                "outlet_pressure": 5.0
            },
            solver_settings={
                "max_iterations": 1000,
                "convergence_criteria": 1e-6
            },
            equipment_id=equipment.id,
            owner_id=owner.id,
            is_template=False,
            is_active=True
        )
        
        db.add(simulation)
        simulations.append(simulation)
        logger.info(f"Created simulation for equipment: {equipment.tag}")
    
    db.commit()
    return simulations


def seed_telemetry(db: Session, equipment_list: list[Equipment]) -> list[TelemetryData]:
    """
    Create sample telemetry data
    
    Args:
        db: Database session
        equipment_list: List of equipment to create telemetry for
        
    Returns:
        List of created telemetry records
    """
    telemetry_records = []
    base_time = datetime.now() - timedelta(hours=24)
    
    for equipment in equipment_list:
        # Create 100 telemetry records for each equipment (last 24 hours)
        for i in range(100):
            timestamp = base_time + timedelta(minutes=i * 14.4)  # Every ~14 minutes
            
            telemetry = TelemetryData(
                equipment_id=equipment.id,
                timestamp=timestamp,
                temperature_c=random.uniform(50, 90) if equipment.equipment_type in [EquipmentType.PUMP, EquipmentType.COMPRESSOR] else random.uniform(20, 40),
                pressure_pa=random.uniform(100000, 1500000),
                flow_rate_m3_s=random.uniform(0.01, 0.1),
                vibration_mm_s=random.uniform(0.5, 5.0) if equipment.equipment_type in [EquipmentType.PUMP, EquipmentType.COMPRESSOR, EquipmentType.TURBINE] else None,
                speed_rpm=random.uniform(2800, 3000) if equipment.equipment_type in [EquipmentType.PUMP, EquipmentType.COMPRESSOR, EquipmentType.TURBINE] else None,
                power_kw=random.uniform(equipment.rated_power_kw * 0.7, equipment.rated_power_kw * 0.95) if equipment.rated_power_kw else None,
                current_a=random.uniform(50, 200) if equipment.rated_power_kw else None,
                voltage_v=random.uniform(380, 420) if equipment.rated_power_kw else None,
                sensor_data={
                    "bearing_temp_c": random.uniform(40, 70),
                    "oil_pressure_bar": random.uniform(2, 5),
                    "seal_condition": "good"
                },
                quality_score=random.uniform(0.85, 1.0),
                is_valid=1,
                source="MQTT",
                device_id=f"sensor-{equipment.tag}"
            )
            
            telemetry_records.append(telemetry)
    
    db.bulk_save_objects(telemetry_records)
    db.commit()
    logger.info(f"Created {len(telemetry_records)} telemetry records")
    return telemetry_records


def seed_analysis(db: Session, equipment_list: list[Equipment], owner: User) -> list[AnalysisResult]:
    """
    Create sample analysis results
    
    Args:
        db: Database session
        equipment_list: List of equipment to create analysis for
        owner: User who owns the analysis
        
    Returns:
        List of created analysis results
    """
    analysis_results = []
    
    for equipment in equipment_list:
        # Create vibration analysis
        vibration_analysis = AnalysisResult(
            analysis_type=AnalysisType.VIBRATION,
            name=f"Vibration Analysis - {equipment.tag}",
            description=f"Automated vibration analysis for {equipment.name}",
            equipment_id=equipment.id,
            results={
                "overall_vibration_mm_s": random.uniform(1.5, 4.5),
                "peak_frequency_hz": random.uniform(50, 150),
                "harmonics": [50, 100, 150],
                "bearing_condition": "acceptable"
            },
            metrics={
                "rms_velocity": random.uniform(2.0, 4.0),
                "peak_acceleration": random.uniform(5.0, 15.0),
                "crest_factor": random.uniform(3.0, 5.0)
            },
            recommendations=[
                "Continue monitoring",
                "Schedule inspection in 30 days"
            ],
            severity=random.choice([AnalysisSeverity.NORMAL, AnalysisSeverity.WARNING]),
            confidence_score=random.uniform(0.85, 0.98),
            fault_detected=random.choice([True, False]),
            fault_mode="Bearing wear" if random.random() > 0.7 else None,
            analysis_start_time=datetime.now() - timedelta(hours=1),
            analysis_end_time=datetime.now(),
            execution_time_seconds=random.uniform(5.0, 30.0),
            algorithm_version="1.0.0",
            owner_id=owner.id,
            requires_action=random.choice([True, False])
        )
        
        db.add(vibration_analysis)
        analysis_results.append(vibration_analysis)
        logger.info(f"Created vibration analysis for equipment: {equipment.tag}")
    
    db.commit()
    return analysis_results


def seed_all(db: Session) -> dict:
    """
    Seed all data
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with counts of created records
    """
    logger.info("Starting database seeding...")
    
    try:
        # Seed users
        users = seed_users(db)
        admin_user = next((u for u in users if u.role == UserRole.ADMIN), users[0])
        
        # Seed equipment
        equipment = seed_equipment(db, admin_user)
        
        # Seed simulations
        simulations = seed_simulations(db, equipment, admin_user)
        
        # Seed telemetry
        telemetry = seed_telemetry(db, equipment)
        
        # Seed analysis
        analysis = seed_analysis(db, equipment, admin_user)
        
        result = {
            "users": len(users),
            "equipment": len(equipment),
            "simulations": len(simulations),
            "telemetry": len(telemetry),
            "analysis": len(analysis)
        }
        
        logger.info(f"Database seeding completed: {result}")
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
        raise


if __name__ == "__main__":
    # For standalone execution
    from app.database import SessionLocal
    
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    
    try:
        result = seed_all(db)
        print(f"Seeding completed: {result}")
    finally:
        db.close()