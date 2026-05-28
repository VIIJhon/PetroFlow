"""
Telemetry Processor Module
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

High-performance telemetry processing with advanced validation, anomaly detection,
and integration with safety envelope validators.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import hashlib
import json

import numpy as np
import pandas as pd
from scipy import stats

from .safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint,
    SafetyEnvelopeResult,
    ValidationSeverity
)
from .optimizer import OperationalOptimizer, OptimizationConfig
from .standards import EquipmentType, UnitSystem

logger = logging.getLogger(__name__)


@dataclass
class TelemetryPoint:
    """Single telemetry data point."""
    equipment_id: str
    timestamp: datetime
    parameters: Dict[str, float]
    units: Dict[str, str]
    quality: float = 1.0  # 0.0 to 1.0
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    equipment_id: str
    parameter: str
    timestamp: datetime
    value: float
    expected_value: float
    deviation: float
    z_score: float
    severity: str  # "low", "medium", "high", "critical"
    confidence: float  # 0.0 to 1.0


@dataclass
class TelemetryAggregation:
    """Aggregated telemetry data."""
    equipment_id: str
    parameter: str
    start_time: datetime
    end_time: datetime
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    percentile_99: float


@dataclass
class ProcessingStats:
    """Statistics for telemetry processing."""
    total_points_processed: int = 0
    valid_points: int = 0
    invalid_points: int = 0
    anomalies_detected: int = 0
    processing_time_ms: float = 0.0
    throughput_points_per_sec: float = 0.0


class CircularBuffer:
    """
    Circular buffer for storing recent telemetry data.
    Efficient memory usage with O(1) append and access.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize circular buffer.
        
        Args:
            maxsize: Maximum number of items to store
        """
        self.buffer = deque(maxlen=maxsize)
        self.maxsize = maxsize
    
    def append(self, item: Any):
        """Add item to buffer."""
        self.buffer.append(item)
    
    def get_recent(self, n: int) -> List[Any]:
        """Get n most recent items."""
        return list(self.buffer)[-n:] if n < len(self.buffer) else list(self.buffer)
    
    def get_all(self) -> List[Any]:
        """Get all items in buffer."""
        return list(self.buffer)
    
    def clear(self):
        """Clear buffer."""
        self.buffer.clear()
    
    def __len__(self) -> int:
        return len(self.buffer)


class TelemetryProcessor:
    """
    High-performance telemetry processor with advanced validation and anomaly detection.
    
    Features:
    - Real-time telemetry processing
    - Batch processing with vectorization
    - Anomaly detection using statistical methods
    - Integration with SafetyEnvelopeValidator
    - Temporal aggregation
    - Unit normalization
    - Data enrichment
    - Circular buffer for historical data
    """
    
    def __init__(
        self,
        safety_validator: SafetyEnvelopeValidator,
        optimizer: Optional[OperationalOptimizer] = None,
        buffer_size: int = 10000,
        anomaly_threshold: float = 3.0,
        enable_logging: bool = True
    ):
        """
        Initialize telemetry processor.
        
        Args:
            safety_validator: Safety envelope validator instance
            optimizer: Optional operational optimizer instance
            buffer_size: Size of circular buffer for historical data
            anomaly_threshold: Z-score threshold for anomaly detection
            enable_logging: Enable structured logging
        """
        self.safety_validator = safety_validator
        self.optimizer = optimizer
        self.buffer_size = buffer_size
        self.anomaly_threshold = anomaly_threshold
        self.enable_logging = enable_logging
        self.logger = logging.getLogger(f"{__name__}.TelemetryProcessor")
        
        # Circular buffers per equipment
        self.buffers: Dict[str, CircularBuffer] = {}
        
        # Processing statistics
        self.stats = ProcessingStats()
        
        # Unit conversion factors (to SI)
        self.unit_conversions = self._initialize_unit_conversions()
        
        self.logger.info(
            "TelemetryProcessor initialized",
            extra={
                "buffer_size": buffer_size,
                "anomaly_threshold": anomaly_threshold,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _initialize_unit_conversions(self) -> Dict[str, Dict[str, float]]:
        """Initialize unit conversion factors."""
        return {
            "pressure": {
                "Pa": 1.0,
                "kPa": 1000.0,
                "MPa": 1e6,
                "bar": 1e5,
                "psi": 6894.76,
                "atm": 101325.0
            },
            "temperature": {
                "K": 1.0,
                "C": 1.0,  # Special handling needed
                "F": 1.0   # Special handling needed
            },
            "flow": {
                "m3/s": 1.0,
                "m3/h": 1/3600,
                "L/s": 0.001,
                "L/min": 1/60000,
                "gpm": 6.30902e-5,
                "bbl/d": 1.84013e-6
            },
            "power": {
                "W": 1.0,
                "kW": 1000.0,
                "MW": 1e6,
                "hp": 745.7
            },
            "speed": {
                "rpm": 1.0,
                "rad/s": 9.5493
            }
        }
    
    def process_telemetry_point(
        self,
        telemetry_point: TelemetryPoint,
        validate_safety: bool = True,
        detect_anomalies: bool = True
    ) -> Tuple[bool, Optional[SafetyEnvelopeResult], List[AnomalyDetection]]:
        """
        Process a single telemetry point.
        
        Args:
            telemetry_point: Telemetry point to process
            validate_safety: Whether to validate against safety envelope
            detect_anomalies: Whether to detect anomalies
            
        Returns:
            Tuple of (is_valid, safety_result, anomalies)
        """
        start_time = datetime.utcnow()
        
        try:
            # Normalize units
            normalized_point = self.normalize_units(telemetry_point)
            
            # Validate data quality
            if normalized_point.quality < 0.5:
                self.stats.invalid_points += 1
                return False, None, []
            
            # Store in buffer
            self._store_in_buffer(normalized_point)
            
            # Validate safety envelope
            safety_result = None
            if validate_safety:
                safety_result = self._validate_safety(normalized_point)
            
            # Detect anomalies
            anomalies = []
            if detect_anomalies:
                anomalies = self._detect_point_anomalies(normalized_point)
                self.stats.anomalies_detected += len(anomalies)
            
            # Update statistics
            self.stats.total_points_processed += 1
            self.stats.valid_points += 1
            
            # Calculate processing time
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats.processing_time_ms += duration_ms
            
            return True, safety_result, anomalies
            
        except Exception as e:
            self.logger.error(
                f"Failed to process telemetry point: {e}",
                extra={
                    "equipment_id": telemetry_point.equipment_id,
                    "error": str(e)
                }
            )
            self.stats.invalid_points += 1
            return False, None, []
    
    def process_telemetry_batch(
        self,
        telemetry_points: List[TelemetryPoint],
        validate_safety: bool = True,
        detect_anomalies: bool = True
    ) -> Tuple[List[bool], List[Optional[SafetyEnvelopeResult]], List[List[AnomalyDetection]]]:
        """
        Process batch of telemetry points with vectorization.
        
        Args:
            telemetry_points: List of telemetry points
            validate_safety: Whether to validate against safety envelope
            detect_anomalies: Whether to detect anomalies
            
        Returns:
            Tuple of (validity_list, safety_results, anomalies_list)
        """
        start_time = datetime.utcnow()
        
        validity_list = []
        safety_results = []
        anomalies_list = []
        
        # Group by equipment for efficient processing
        equipment_groups = self._group_by_equipment(telemetry_points)
        
        for equipment_id, points in equipment_groups.items():
            # Convert to DataFrame for vectorized operations
            df = self._points_to_dataframe(points)
            
            # Normalize units (vectorized)
            df = self._normalize_dataframe_units(df)
            
            # Process each point
            for idx, point in enumerate(points):
                is_valid = df.iloc[idx]['quality'] >= 0.5
                
                safety_result = None
                if is_valid and validate_safety:
                    safety_result = self._validate_safety(point)
                
                anomalies = []
                if is_valid and detect_anomalies:
                    anomalies = self._detect_point_anomalies(point)
                
                validity_list.append(is_valid)
                safety_results.append(safety_result)
                anomalies_list.append(anomalies)
                
                if is_valid:
                    self.stats.valid_points += 1
                    self._store_in_buffer(point)
                else:
                    self.stats.invalid_points += 1
        
        # Update statistics
        self.stats.total_points_processed += len(telemetry_points)
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.stats.processing_time_ms += duration_ms
        self.stats.throughput_points_per_sec = len(telemetry_points) / (duration_ms / 1000)
        
        return validity_list, safety_results, anomalies_list
    
    def aggregate_telemetry(
        self,
        equipment_id: str,
        parameter: str,
        start_time: datetime,
        end_time: datetime,
        window_size: Optional[timedelta] = None
    ) -> List[TelemetryAggregation]:
        """
        Aggregate telemetry data over time windows.
        
        Args:
            equipment_id: Equipment identifier
            parameter: Parameter to aggregate
            start_time: Start of time range
            end_time: End of time range
            window_size: Size of aggregation window (None = single aggregation)
            
        Returns:
            List of aggregated telemetry data
        """
        # Get data from buffer
        buffer = self.buffers.get(equipment_id)
        if not buffer:
            return []
        
        points = buffer.get_all()
        
        # Filter by time range and parameter
        filtered_points = [
            p for p in points
            if start_time <= p.timestamp <= end_time and parameter in p.parameters
        ]
        
        if not filtered_points:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'timestamp': p.timestamp,
                'value': p.parameters[parameter]
            }
            for p in filtered_points
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Aggregate
        if window_size:
            # Multiple windows
            aggregations = []
            current_time = start_time
            
            while current_time < end_time:
                window_end = min(current_time + window_size, end_time)
                window_data = df[current_time:window_end]['value']
                
                if len(window_data) > 0:
                    agg = self._calculate_aggregation(
                        equipment_id, parameter, current_time, window_end, window_data
                    )
                    aggregations.append(agg)
                
                current_time = window_end
            
            return aggregations
        else:
            # Single aggregation
            return [self._calculate_aggregation(
                equipment_id, parameter, start_time, end_time, df['value']
            )]
    
    def _calculate_aggregation(
        self,
        equipment_id: str,
        parameter: str,
        start_time: datetime,
        end_time: datetime,
        data: pd.Series
    ) -> TelemetryAggregation:
        """Calculate aggregation statistics."""
        return TelemetryAggregation(
            equipment_id=equipment_id,
            parameter=parameter,
            start_time=start_time,
            end_time=end_time,
            count=len(data),
            mean=float(data.mean()),
            median=float(data.median()),
            std=float(data.std()),
            min=float(data.min()),
            max=float(data.max()),
            percentile_25=float(data.quantile(0.25)),
            percentile_75=float(data.quantile(0.75)),
            percentile_95=float(data.quantile(0.95)),
            percentile_99=float(data.quantile(0.99))
        )
    
    def detect_anomalies(
        self,
        equipment_id: str,
        parameter: str,
        window_size: int = 100,
        threshold: Optional[float] = None
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies in telemetry data using statistical methods.
        
        Args:
            equipment_id: Equipment identifier
            parameter: Parameter to analyze
            window_size: Size of rolling window for statistics
            threshold: Z-score threshold (None = use default)
            
        Returns:
            List of detected anomalies
        """
        threshold = threshold or self.anomaly_threshold
        
        # Get data from buffer
        buffer = self.buffers.get(equipment_id)
        if not buffer or len(buffer) < window_size:
            return []
        
        points = buffer.get_all()
        
        # Filter by parameter
        filtered_points = [p for p in points if parameter in p.parameters]
        if len(filtered_points) < window_size:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'timestamp': p.timestamp,
                'value': p.parameters[parameter]
            }
            for p in filtered_points
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Calculate rolling statistics
        rolling_mean = df['value'].rolling(window=window_size, min_periods=1).mean()
        rolling_std = df['value'].rolling(window=window_size, min_periods=1).std()
        
        # Calculate z-scores
        z_scores = np.abs((df['value'] - rolling_mean) / rolling_std)
        
        # Detect anomalies
        anomalies = []
        anomaly_mask = z_scores > threshold
        
        for idx in df[anomaly_mask].index:
            z_score = z_scores[idx]
            value = df.loc[idx, 'value']
            expected = rolling_mean[idx]
            
            # Determine severity based on z-score
            if z_score > 5.0:
                severity = "critical"
            elif z_score > 4.0:
                severity = "high"
            elif z_score > 3.5:
                severity = "medium"
            else:
                severity = "low"
            
            anomaly = AnomalyDetection(
                equipment_id=equipment_id,
                parameter=parameter,
                timestamp=idx.to_pydatetime(),
                value=float(value),
                expected_value=float(expected),
                deviation=float(value - expected),
                z_score=float(z_score),
                severity=severity,
                confidence=min(float(z_score / 5.0), 1.0)
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def normalize_units(self, telemetry_point: TelemetryPoint) -> TelemetryPoint:
        """
        Normalize units to standard SI units.
        
        Args:
            telemetry_point: Telemetry point with original units
            
        Returns:
            Telemetry point with normalized units
        """
        normalized_params = {}
        normalized_units = {}
        
        for param, value in telemetry_point.parameters.items():
            unit = telemetry_point.units.get(param, "")
            
            # Determine parameter type
            param_type = self._get_parameter_type(param)
            
            if param_type and param_type in self.unit_conversions:
                # Convert to SI
                if param_type == "temperature":
                    normalized_value, normalized_unit = self._convert_temperature(value, unit)
                else:
                    conversion_factor = self.unit_conversions[param_type].get(unit, 1.0)
                    normalized_value = value * conversion_factor
                    normalized_unit = self._get_si_unit(param_type)
            else:
                # No conversion needed
                normalized_value = value
                normalized_unit = unit
            
            normalized_params[param] = normalized_value
            normalized_units[param] = normalized_unit
        
        return TelemetryPoint(
            equipment_id=telemetry_point.equipment_id,
            timestamp=telemetry_point.timestamp,
            parameters=normalized_params,
            units=normalized_units,
            quality=telemetry_point.quality,
            source=telemetry_point.source,
            metadata=telemetry_point.metadata
        )
    
    def _convert_temperature(self, value: float, unit: str) -> Tuple[float, str]:
        """Convert temperature to Kelvin."""
        if unit == "C":
            return value + 273.15, "K"
        elif unit == "F":
            return (value - 32) * 5/9 + 273.15, "K"
        else:
            return value, "K"
    
    def _get_si_unit(self, param_type: str) -> str:
        """Get SI unit for parameter type."""
        si_units = {
            "pressure": "Pa",
            "temperature": "K",
            "flow": "m3/s",
            "power": "W",
            "speed": "rpm"
        }
        return si_units.get(param_type, "")
    
    def _get_parameter_type(self, parameter: str) -> Optional[str]:
        """Determine parameter type from name."""
        param_lower = parameter.lower()
        
        if any(x in param_lower for x in ["pressure", "press"]):
            return "pressure"
        elif any(x in param_lower for x in ["temperature", "temp"]):
            return "temperature"
        elif any(x in param_lower for x in ["flow", "rate"]):
            return "flow"
        elif any(x in param_lower for x in ["power", "watt"]):
            return "power"
        elif any(x in param_lower for x in ["speed", "rpm"]):
            return "speed"
        
        return None
    
    def enrich_telemetry(
        self,
        telemetry_point: TelemetryPoint,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> TelemetryPoint:
        """
        Enrich telemetry data with additional context.
        
        Args:
            telemetry_point: Original telemetry point
            additional_context: Additional context to add
            
        Returns:
            Enriched telemetry point
        """
        enriched_metadata = telemetry_point.metadata.copy()
        
        # Add processing timestamp
        enriched_metadata['processed_at'] = datetime.utcnow().isoformat()
        
        # Add data quality metrics
        enriched_metadata['quality_score'] = telemetry_point.quality
        
        # Add additional context
        if additional_context:
            enriched_metadata.update(additional_context)
        
        return TelemetryPoint(
            equipment_id=telemetry_point.equipment_id,
            timestamp=telemetry_point.timestamp,
            parameters=telemetry_point.parameters,
            units=telemetry_point.units,
            quality=telemetry_point.quality,
            source=telemetry_point.source,
            metadata=enriched_metadata
        )
    
    def validate_telemetry_stream(
        self,
        telemetry_points: List[TelemetryPoint],
        max_gap_seconds: float = 60.0,
        min_quality: float = 0.5
    ) -> Tuple[bool, List[str]]:
        """
        Validate a stream of telemetry data.
        
        Args:
            telemetry_points: List of telemetry points
            max_gap_seconds: Maximum allowed gap between points
            min_quality: Minimum quality threshold
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        if not telemetry_points:
            return False, ["Empty telemetry stream"]
        
        # Sort by timestamp
        sorted_points = sorted(telemetry_points, key=lambda p: p.timestamp)
        
        # Check for gaps
        for i in range(1, len(sorted_points)):
            gap = (sorted_points[i].timestamp - sorted_points[i-1].timestamp).total_seconds()
            if gap > max_gap_seconds:
                issues.append(f"Gap of {gap:.1f}s detected between points")
        
        # Check quality
        low_quality_count = sum(1 for p in telemetry_points if p.quality < min_quality)
        if low_quality_count > 0:
            issues.append(f"{low_quality_count} points below quality threshold")
        
        # Check for duplicate timestamps
        timestamps = [p.timestamp for p in telemetry_points]
        if len(timestamps) != len(set(timestamps)):
            issues.append("Duplicate timestamps detected")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _validate_safety(self, telemetry_point: TelemetryPoint) -> Optional[SafetyEnvelopeResult]:
        """Validate telemetry point against safety envelope."""
        try:
            # Determine equipment type (simplified - should be from metadata)
            equipment_type = EquipmentType.PUMP  # Default
            
            operating_point = OperatingPoint(
                equipment_id=telemetry_point.equipment_id,
                equipment_type=equipment_type,
                timestamp=telemetry_point.timestamp,
                parameters=telemetry_point.parameters,
                units=telemetry_point.units,
                metadata=telemetry_point.metadata
            )
            
            return self.safety_validator.validate_operating_point(operating_point)
        except Exception as e:
            self.logger.error(f"Safety validation failed: {e}")
            return None
    
    def _detect_point_anomalies(self, telemetry_point: TelemetryPoint) -> List[AnomalyDetection]:
        """Detect anomalies for a single point."""
        anomalies = []
        
        for parameter in telemetry_point.parameters:
            param_anomalies = self.detect_anomalies(
                telemetry_point.equipment_id,
                parameter,
                window_size=min(100, len(self.buffers.get(telemetry_point.equipment_id, [])))
            )
            anomalies.extend(param_anomalies)
        
        return anomalies
    
    def _store_in_buffer(self, telemetry_point: TelemetryPoint):
        """Store telemetry point in circular buffer."""
        if telemetry_point.equipment_id not in self.buffers:
            self.buffers[telemetry_point.equipment_id] = CircularBuffer(self.buffer_size)
        
        self.buffers[telemetry_point.equipment_id].append(telemetry_point)
    
    def _group_by_equipment(
        self,
        telemetry_points: List[TelemetryPoint]
    ) -> Dict[str, List[TelemetryPoint]]:
        """Group telemetry points by equipment ID."""
        groups = {}
        for point in telemetry_points:
            if point.equipment_id not in groups:
                groups[point.equipment_id] = []
            groups[point.equipment_id].append(point)
        return groups
    
    def _points_to_dataframe(self, points: List[TelemetryPoint]) -> pd.DataFrame:
        """Convert telemetry points to DataFrame."""
        data = []
        for point in points:
            row = {
                'equipment_id': point.equipment_id,
                'timestamp': point.timestamp,
                'quality': point.quality,
                'source': point.source
            }
            row.update(point.parameters)
            data.append(row)
        
        return pd.DataFrame(data)
    
    def _normalize_dataframe_units(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize units in DataFrame (vectorized)."""
        # Simplified - full implementation would handle all parameters
        return df
    
    def get_processing_stats(self) -> ProcessingStats:
        """Get processing statistics."""
        return self.stats
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = ProcessingStats()
    
    def clear_buffer(self, equipment_id: Optional[str] = None):
        """
        Clear telemetry buffer.
        
        Args:
            equipment_id: Specific equipment ID (None = clear all)
        """
        if equipment_id:
            if equipment_id in self.buffers:
                self.buffers[equipment_id].clear()
        else:
            for buffer in self.buffers.values():
                buffer.clear()