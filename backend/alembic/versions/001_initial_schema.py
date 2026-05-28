"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2026-05-19 02:26:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('ADMIN', 'ENGINEER', 'OPERATOR', 'VIEWER', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create equipment table
    op.create_table(
        'equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('equipment_type', sa.Enum('PUMP', 'COMPRESSOR', 'TURBINE', 'HEAT_EXCHANGER', 'VALVE', 'SEPARATOR', 'VESSEL', name='equipmenttype'), nullable=False),
        sa.Column('status', sa.Enum('OPERATIONAL', 'MAINTENANCE', 'SHUTDOWN', 'STANDBY', 'FAULT', name='equipmentstatus'), nullable=False, server_default='OPERATIONAL'),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('facility', sa.String(length=255), nullable=True),
        sa.Column('unit', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('serial_number', sa.String(length=255), nullable=True),
        sa.Column('specifications', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('operating_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('design_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('rated_capacity', sa.Float(), nullable=True),
        sa.Column('rated_power_kw', sa.Float(), nullable=True),
        sa.Column('efficiency', sa.Float(), nullable=True),
        sa.Column('installation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('commissioning_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_maintenance_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_maintenance_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('operating_hours', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('start_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_monitoring', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_equipment_id'), 'equipment', ['id'], unique=False)
    op.create_index(op.f('ix_equipment_tag'), 'equipment', ['tag'], unique=True)
    op.create_index(op.f('ix_equipment_equipment_type'), 'equipment', ['equipment_type'], unique=False)

    # Create simulations table
    op.create_table(
        'simulations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('simulation_type', sa.Enum('DYNAMIC', 'STEADY_STATE', 'TRANSIENT', 'NETWORK', 'THERMAL', 'MULTIPHASE', name='simulationtype'), nullable=False),
        sa.Column('configuration', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('initial_conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('boundary_conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('solver_settings', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('is_template', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulations_id'), 'simulations', ['id'], unique=False)
    op.create_index(op.f('ix_simulations_simulation_type'), 'simulations', ['simulation_type'], unique=False)

    # Create simulation_runs table
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('simulation_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='simulationstatus'), nullable=False, server_default='PENDING'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('input_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('results', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('time_series_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('steps_taken', sa.Integer(), nullable=True),
        sa.Column('convergence_achieved', sa.Boolean(), nullable=True),
        sa.Column('error_estimate', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('warnings', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('solver_used', sa.String(length=100), nullable=True),
        sa.Column('computational_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_runs_id'), 'simulation_runs', ['id'], unique=False)
    op.create_index(op.f('ix_simulation_runs_status'), 'simulation_runs', ['status'], unique=False)

    # Create telemetry_data table
    op.create_table(
        'telemetry_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('pressure_pa', sa.Float(), nullable=True),
        sa.Column('flow_rate_m3_s', sa.Float(), nullable=True),
        sa.Column('vibration_mm_s', sa.Float(), nullable=True),
        sa.Column('speed_rpm', sa.Float(), nullable=True),
        sa.Column('power_kw', sa.Float(), nullable=True),
        sa.Column('current_a', sa.Float(), nullable=True),
        sa.Column('voltage_v', sa.Float(), nullable=True),
        sa.Column('sensor_data', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('is_valid', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_telemetry_data_id'), 'telemetry_data', ['id'], unique=False)
    op.create_index(op.f('ix_telemetry_data_equipment_id'), 'telemetry_data', ['equipment_id'], unique=False)
    op.create_index(op.f('ix_telemetry_data_timestamp'), 'telemetry_data', ['timestamp'], unique=False)
    op.create_index('idx_equipment_timestamp', 'telemetry_data', ['equipment_id', 'timestamp'], unique=False)
    op.create_index('idx_timestamp_valid', 'telemetry_data', ['timestamp', 'is_valid'], unique=False)

    # Create analysis_results table
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_type', sa.Enum('VIBRATION', 'THERMAL', 'SPECTRAL', 'CAUSAL_DIAGNOSIS', 'ANOMALY_DETECTION', 'PERFORMANCE', 'PREDICTIVE_MAINTENANCE', name='analysistype'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('results', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('severity', sa.Enum('NORMAL', 'WARNING', 'CRITICAL', 'EMERGENCY', name='analysisseverity'), nullable=False, server_default='NORMAL'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('fault_detected', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('fault_mode', sa.String(length=255), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('analysis_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('analysis_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time_seconds', sa.Float(), nullable=True),
        sa.Column('algorithm_version', sa.String(length=50), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('feature_importance', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('requires_action', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('action_taken', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_results_id'), 'analysis_results', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_results_analysis_type'), 'analysis_results', ['analysis_type'], unique=False)
    op.create_index(op.f('ix_analysis_results_equipment_id'), 'analysis_results', ['equipment_id'], unique=False)
    op.create_index(op.f('ix_analysis_results_severity'), 'analysis_results', ['severity'], unique=False)
    op.create_index(op.f('ix_analysis_results_fault_detected'), 'analysis_results', ['fault_detected'], unique=False)
    op.create_index(op.f('ix_analysis_results_requires_action'), 'analysis_results', ['requires_action'], unique=False)
    op.create_index(op.f('ix_analysis_results_created_at'), 'analysis_results', ['created_at'], unique=False)
    op.create_index('idx_equipment_type_created', 'analysis_results', ['equipment_id', 'analysis_type', 'created_at'], unique=False)
    op.create_index('idx_severity_fault', 'analysis_results', ['severity', 'fault_detected'], unique=False)
    op.create_index('idx_requires_action', 'analysis_results', ['requires_action', 'action_taken'], unique=False)


def downgrade() -> None:
    # Drop analysis_results table
    op.drop_index('idx_requires_action', table_name='analysis_results')
    op.drop_index('idx_severity_fault', table_name='analysis_results')
    op.drop_index('idx_equipment_type_created', table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_created_at'), table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_requires_action'), table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_fault_detected'), table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_severity'), table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_equipment_id'), table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_analysis_type'), table_name='analysis_results')
    op.drop_index(op.f('ix_analysis_results_id'), table_name='analysis_results')
    op.drop_table('analysis_results')
    
    # Drop telemetry_data table
    op.drop_index('idx_timestamp_valid', table_name='telemetry_data')
    op.drop_index('idx_equipment_timestamp', table_name='telemetry_data')
    op.drop_index(op.f('ix_telemetry_data_timestamp'), table_name='telemetry_data')
    op.drop_index(op.f('ix_telemetry_data_equipment_id'), table_name='telemetry_data')
    op.drop_index(op.f('ix_telemetry_data_id'), table_name='telemetry_data')
    op.drop_table('telemetry_data')
    
    # Drop simulation_runs table
    op.drop_index(op.f('ix_simulation_runs_status'), table_name='simulation_runs')
    op.drop_index(op.f('ix_simulation_runs_id'), table_name='simulation_runs')
    op.drop_table('simulation_runs')
    
    # Drop simulations table
    op.drop_index(op.f('ix_simulations_simulation_type'), table_name='simulations')
    op.drop_index(op.f('ix_simulations_id'), table_name='simulations')
    op.drop_table('simulations')
    
    # Drop equipment table
    op.drop_index(op.f('ix_equipment_equipment_type'), table_name='equipment')
    op.drop_index(op.f('ix_equipment_tag'), table_name='equipment')
    op.drop_index(op.f('ix_equipment_id'), table_name='equipment')
    op.drop_table('equipment')
    
    # Drop users table
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    sa.Enum(name='analysisseverity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='analysistype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='simulationstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='simulationtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='equipmentstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='equipmenttype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)