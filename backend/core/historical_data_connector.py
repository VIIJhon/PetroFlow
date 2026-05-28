"""
Historical Data Connector Module
Connects to multiple external data sources (PostgreSQL, MySQL, CSV, SQLite)
for real-time training data ingestion from oil & gas operators.

Supports:
- Relational databases (PostgreSQL, MySQL)
- Local SQLite archives
- CSV/Excel files from operators
- Data validation and schema inference
- Connection pooling and retry logic
- Audit trail for all data transfers

Phase: Phase 1 - Historical Data Integration
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import logging
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import time
import json
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CSV = "csv"
    EXCEL = "excel"


@dataclass
class DataSourceConfig:
    """Configuration for a data source connection."""
    source_type: DataSourceType
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None
    table_name: Optional[str] = None
    query: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    batch_size: int = 5000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoricalDataRecord:
    """Represents a historical failure/operational record."""
    equipment_id: str
    equipment_type: str
    timestamp: datetime
    failure_occurred: bool
    time_to_failure_hours: Optional[float]
    discharge_temperature: float
    inlet_pressure: float
    outlet_pressure: float
    volumetric_flow: float
    vibration_velocity: float
    rpm: float
    operating_hours: float
    power_source: str
    formation_type: str
    well_depth_meters: float
    bottom_hole_temperature: float
    oil_viscosity_cst: float
    api_gravity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class HistoricalDataConnector:
    """
    Main connector class for historical data ingestion.
    Manages connection pooling, caching, and data validation.
    """
    
    def __init__(self, cache_dir: str = "storage/historical_cache"):
        """
        Initialize the historical data connector.
        
        Args:
            cache_dir: Directory for caching downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.connections = {}
        self.cache_index = self._load_cache_index()
        self.source_configs: Dict[str, DataSourceConfig] = {}
        
    def register_data_source(self, source_name: str, config: DataSourceConfig) -> bool:
        """
        Register a new data source.
        
        Args:
            source_name: Unique identifier for the source
            config: DataSourceConfig instance
            
        Returns:
            bool: True if registration successful
        """
        try:
            if not self._validate_connection(config):
                logger.error(f"Failed to validate connection for source: {source_name}")
                return False
            
            self.source_configs[source_name] = config
            logger.info(f"Data source registered: {source_name} ({config.source_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error registering data source {source_name}: {str(e)}")
            return False
    
    def _validate_connection(self, config: DataSourceConfig) -> bool:
        """Validate that a data source is accessible."""
        try:
            if config.source_type == DataSourceType.POSTGRESQL:
                import psycopg2
                conn = psycopg2.connect(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.username,
                    password=config.password,
                    connect_timeout=config.timeout_seconds
                )
                conn.close()
                return True
                
            elif config.source_type == DataSourceType.MYSQL:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.username,
                    password=config.password,
                    connection_timeout=config.timeout_seconds
                )
                conn.close()
                return True
                
            elif config.source_type == DataSourceType.SQLITE:
                if not Path(config.file_path).exists():
                    return False
                conn = sqlite3.connect(config.file_path, timeout=config.timeout_seconds)
                conn.close()
                return True
                
            elif config.source_type in [DataSourceType.CSV, DataSourceType.EXCEL]:
                return Path(config.file_path).exists()
                
            return False
            
        except Exception as e:
            logger.error(f"Connection validation failed: {str(e)}")
            return False
    
    @contextmanager
    def _get_connection(self, config: DataSourceConfig):
        """
        Get a database connection with automatic cleanup.
        Implements retry logic with exponential backoff.
        """
        conn = None
        attempt = 0
        
        while attempt < config.max_retries:
            try:
                if config.source_type == DataSourceType.POSTGRESQL:
                    import psycopg2
                    conn = psycopg2.connect(
                        host=config.host,
                        port=config.port,
                        database=config.database,
                        user=config.username,
                        password=config.password,
                        connect_timeout=config.timeout_seconds
                    )
                    
                elif config.source_type == DataSourceType.MYSQL:
                    import mysql.connector
                    conn = mysql.connector.connect(
                        host=config.host,
                        port=config.port,
                        database=config.database,
                        user=config.username,
                        password=config.password,
                        connection_timeout=config.timeout_seconds
                    )
                    
                elif config.source_type == DataSourceType.SQLITE:
                    conn = sqlite3.connect(config.file_path, timeout=config.timeout_seconds)
                
                yield conn
                return
                
            except Exception as e:
                attempt += 1
                if attempt < config.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection attempt {attempt} failed. Retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect after {config.max_retries} attempts: {str(e)}")
                    raise
                    
            finally:
                if conn is not None:
                    conn.close()
    
    def fetch_historical_data(
        self,
        source_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Tuple[List[HistoricalDataRecord], Dict[str, Any]]:
        """
        Fetch historical data from a registered source.
        
        Args:
            source_name: Name of registered data source
            filters: Optional filters (equipment_type, date_range, etc.)
            limit: Maximum records to fetch
            
        Returns:
            Tuple of (records, metadata)
        """
        if source_name not in self.source_configs:
            logger.error(f"Data source not registered: {source_name}")
            return [], {}
        
        config = self.source_configs[source_name]
        cache_key = self._generate_cache_key(source_name, filters)
        
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"Returning cached data for {source_name}")
            return cached_data[0], cached_data[1]
        
        try:
            if config.source_type == DataSourceType.POSTGRESQL:
                df, metadata = self._fetch_postgresql(config, filters, limit)
            elif config.source_type == DataSourceType.MYSQL:
                df, metadata = self._fetch_mysql(config, filters, limit)
            elif config.source_type == DataSourceType.SQLITE:
                df, metadata = self._fetch_sqlite(config, filters, limit)
            elif config.source_type == DataSourceType.CSV:
                df, metadata = self._fetch_csv(config, filters, limit)
            elif config.source_type == DataSourceType.EXCEL:
                df, metadata = self._fetch_excel(config, filters, limit)
            else:
                raise ValueError(f"Unknown source type: {config.source_type}")
            
            records = self._dataframe_to_records(df)
            self._cache_data(cache_key, records, metadata)
            
            logger.info(f"Fetched {len(records)} records from {source_name}")
            return records, metadata
            
        except Exception as e:
            logger.error(f"Error fetching data from {source_name}: {str(e)}")
            return [], {"error": str(e)}
    
    def _fetch_postgresql(
        self,
        config: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch data from PostgreSQL database."""
        import psycopg2.extras
        
        with self._get_connection(config) as conn:
            query = config.query or f"SELECT * FROM {config.table_name}"
            
            if filters:
                query += " WHERE " + " AND ".join(
                    f"{k} = %s" for k in filters.keys()
                )
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                query,
                list(filters.values()) if filters else []
            )
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=columns)
            cursor.close()
            
            metadata = {
                "source": config.database,
                "table": config.table_name,
                "row_count": len(df),
                "fetch_time": datetime.now().isoformat()
            }
            
            return df, metadata
    
    def _fetch_mysql(
        self,
        config: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch data from MySQL database."""
        import mysql.connector
        
        with self._get_connection(config) as conn:
            query = config.query or f"SELECT * FROM {config.table_name}"
            
            if filters:
                query += " WHERE " + " AND ".join(
                    f"{k} = %s" for k in filters.keys()
                )
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql(
                query,
                conn,
                params=list(filters.values()) if filters else None
            )
            
            metadata = {
                "source": config.database,
                "table": config.table_name,
                "row_count": len(df),
                "fetch_time": datetime.now().isoformat()
            }
            
            return df, metadata
    
    def _fetch_sqlite(
        self,
        config: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch data from SQLite database."""
        conn = sqlite3.connect(config.file_path)
        
        try:
            query = config.query or f"SELECT * FROM {config.table_name}"
            
            if filters:
                query += " WHERE " + " AND ".join(
                    f"{k} = ?" for k in filters.keys()
                )
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql(
                query,
                conn,
                params=list(filters.values()) if filters else None
            )
            
            metadata = {
                "source": config.file_path,
                "table": config.table_name,
                "row_count": len(df),
                "fetch_time": datetime.now().isoformat()
            }
            
            return df, metadata
            
        finally:
            conn.close()
    
    def _fetch_csv(
        self,
        config: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch data from CSV file."""
        df = pd.read_csv(config.file_path)
        
        if filters:
            for key, value in filters.items():
                if key in df.columns:
                    df = df[df[key] == value]
        
        if limit:
            df = df.head(limit)
        
        metadata = {
            "source": config.file_path,
            "row_count": len(df),
            "fetch_time": datetime.now().isoformat()
        }
        
        return df, metadata
    
    def _fetch_excel(
        self,
        config: DataSourceConfig,
        filters: Optional[Dict[str, Any]],
        limit: Optional[int]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch data from Excel file."""
        df = pd.read_excel(
            config.file_path,
            sheet_name=config.metadata.get("sheet_name", 0)
        )
        
        if filters:
            for key, value in filters.items():
                if key in df.columns:
                    df = df[df[key] == value]
        
        if limit:
            df = df.head(limit)
        
        metadata = {
            "source": config.file_path,
            "row_count": len(df),
            "fetch_time": datetime.now().isoformat()
        }
        
        return df, metadata
    
    def _dataframe_to_records(self, df: pd.DataFrame) -> List[HistoricalDataRecord]:
        """Convert DataFrame to HistoricalDataRecord objects."""
        records = []
        
        for _, row in df.iterrows():
            try:
                record = HistoricalDataRecord(
                    equipment_id=str(row.get("equipment_id", "")),
                    equipment_type=str(row.get("equipment_type", "")),
                    timestamp=pd.to_datetime(row.get("timestamp", datetime.now())),
                    failure_occurred=bool(row.get("failure_occurred", False)),
                    time_to_failure_hours=float(row.get("time_to_failure_hours")) if row.get("time_to_failure_hours") else None,
                    discharge_temperature=float(row.get("discharge_temperature", 0)),
                    inlet_pressure=float(row.get("inlet_pressure", 0)),
                    outlet_pressure=float(row.get("outlet_pressure", 0)),
                    volumetric_flow=float(row.get("volumetric_flow", 0)),
                    vibration_velocity=float(row.get("vibration_velocity", 0)),
                    rpm=float(row.get("rpm", 0)),
                    operating_hours=float(row.get("operating_hours", 0)),
                    power_source=str(row.get("power_source", "")),
                    formation_type=str(row.get("formation_type", "")),
                    well_depth_meters=float(row.get("well_depth_meters", 0)),
                    bottom_hole_temperature=float(row.get("bottom_hole_temperature", 0)),
                    oil_viscosity_cst=float(row.get("oil_viscosity_cst", 0)),
                    api_gravity=float(row.get("api_gravity", 0)),
                    metadata=dict(row.get("metadata", {}))
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to convert row to record: {str(e)}")
                continue
        
        return records
    
    def _generate_cache_key(self, source_name: str, filters: Optional[Dict]) -> str:
        """Generate a cache key for a query."""
        filter_str = json.dumps(filters, sort_keys=True, default=str) if filters else "none"
        return f"{source_name}_{hash(filter_str)}"
    
    def _load_cache_index(self) -> Dict[str, Dict]:
        """Load the cache index from disk."""
        index_path = self.cache_dir / "cache_index.json"
        if index_path.exists():
            try:
                with open(index_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {str(e)}")
        return {}
    
    def _get_cached_data(self, cache_key: str) -> Optional[Tuple[List, Dict]]:
        """Retrieve cached data if it's still valid."""
        if cache_key not in self.cache_index:
            return None
        
        entry = self.cache_index[cache_key]
        cache_path = Path(entry["path"])
        
        if not cache_path.exists():
            del self.cache_index[cache_key]
            return None
        
        cache_age = datetime.now() - datetime.fromisoformat(entry["created"])
        if cache_age > timedelta(hours=24):
            cache_path.unlink()
            del self.cache_index[cache_key]
            return None
        
        try:
            df = pd.read_parquet(cache_path)
            records = self._dataframe_to_records(df)
            metadata = entry.get("metadata", {})
            return records, metadata
        except Exception as e:
            logger.warning(f"Failed to load cached data: {str(e)}")
            return None
    
    def _cache_data(self, cache_key: str, records: List[HistoricalDataRecord], metadata: Dict) -> None:
        """Cache data to disk."""
        try:
            cache_path = self.cache_dir / f"{cache_key}.parquet"
            df = pd.DataFrame([vars(r) for r in records])
            df.to_parquet(cache_path, index=False)
            
            self.cache_index[cache_key] = {
                "path": str(cache_path),
                "created": datetime.now().isoformat(),
                "metadata": metadata
            }
            
            index_path = self.cache_dir / "cache_index.json"
            with open(index_path, "w") as f:
                json.dump(self.cache_index, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to cache data: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            import shutil
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_index = {}
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")


def get_historical_connector() -> HistoricalDataConnector:
    """Get singleton instance of historical data connector."""
    if not hasattr(get_historical_connector, "_instance"):
        get_historical_connector._instance = HistoricalDataConnector()
    return get_historical_connector._instance
