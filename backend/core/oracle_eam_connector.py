"""
PetroFlow Oracle EAM Integration Module
========================================

Oracle Enterprise Asset Management (EAM) integration for comprehensive asset lifecycle management.

Features:
- Oracle EAM REST API integration
- Asset management synchronization
- Work request creation and updates
- Maintenance schedule integration
- Inventory management interface
- Preventive maintenance program management
- Asset hierarchy and location tracking
- Authentication with Oracle Cloud credentials
- Comprehensive error handling and retry logic
- Audit logging integration

Supported Oracle EAM Modules:
- Asset Management
- Work Management
- Preventive Maintenance
- Inventory Management
- Procurement Integration

Author: Bob
Version: 1.0.0
"""

import logging
import time
import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import base64

# Import audit logging
try:
    from core.audit_logging_service import AuditLogger, SessionContext
    AUDIT_LOGGING_AVAILABLE = True
except ImportError:
    AUDIT_LOGGING_AVAILABLE = False
    AuditLogger = None
    SessionContext = None

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class OracleAuthType(Enum):
    """Oracle authentication types."""
    BASIC = "basic"
    OAUTH2 = "oauth2"
    TOKEN = "token"


class AssetStatus(Enum):
    """Oracle EAM asset status codes."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    IN_SERVICE = "IN_SERVICE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    RETIRED = "RETIRED"


class WorkRequestStatus(Enum):
    """Oracle EAM work request status codes."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class WorkRequestPriority(Enum):
    """Oracle EAM work request priority levels."""
    CRITICAL = "1"
    HIGH = "2"
    MEDIUM = "3"
    LOW = "4"


# Oracle EAM REST API Endpoints
ORACLE_EAM_ENDPOINTS = {
    'ASSETS': '/fscmRestApi/resources/11.13.18.05/assets',
    'WORK_REQUESTS': '/fscmRestApi/resources/11.13.18.05/workRequests',
    'WORK_ORDERS': '/fscmRestApi/resources/11.13.18.05/workOrders',
    'MAINTENANCE_SCHEDULES': '/fscmRestApi/resources/11.13.18.05/maintenanceSchedules',
    'INVENTORY_ITEMS': '/fscmRestApi/resources/11.13.18.05/inventoryItems',
    'ASSET_GROUPS': '/fscmRestApi/resources/11.13.18.05/assetGroups',
    'LOCATIONS': '/fscmRestApi/resources/11.13.18.05/locations'
}


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class OracleConnectionError(Exception):
    """Raised when Oracle connection fails."""
    pass


class OracleAuthenticationError(Exception):
    """Raised when Oracle authentication fails."""
    pass


class OracleAPIError(Exception):
    """Raised when Oracle API call fails."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict] = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class OracleDataValidationError(Exception):
    """Raised when Oracle data validation fails."""
    pass


# ============================================================================
# ORACLE EAM CONNECTOR CLASS
# ============================================================================

class OracleEAMConnector:
    """
    Oracle Enterprise Asset Management Integration Connector
    
    Provides comprehensive integration with Oracle EAM Cloud:
    - Asset lifecycle management
    - Work request and work order management
    - Preventive maintenance scheduling
    - Inventory and spare parts management
    - Asset hierarchy and location tracking
    
    Uses Oracle Cloud REST APIs with OAuth2 or Basic authentication.
    
    Attributes:
        config: Oracle connection configuration
        auth_type: Authentication type
        session: HTTP session for REST API
        base_url: Oracle Cloud base URL
        audit_logger: Audit logging instance
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        auth_type: OracleAuthType = OracleAuthType.BASIC,
        connection_pool_size: int = 10,
        timeout: int = 30
    ):
        """
        Initialize Oracle EAM Connector.
        
        Args:
            config: Configuration dictionary with Oracle connection details
            auth_type: Authentication type to use
            connection_pool_size: HTTP connection pool size
            timeout: Request timeout in seconds
            
        Example:
            >>> config = {
            ...     'base_url': 'https://your-instance.oraclecloud.com',
            ...     'username': 'eam_user',
            ...     'password': 'password',
            ...     'organization_id': 'ORG123'
            ... }
            >>> connector = OracleEAMConnector(config)
        """
        self.config = config
        self.auth_type = auth_type
        self.session = None
        self.base_url = config.get('base_url', '').rstrip('/')
        self.timeout = timeout
        self._connection_pool_size = connection_pool_size
        
        # Initialize audit logger
        if AUDIT_LOGGING_AVAILABLE:
            self.audit_logger = AuditLogger()
        else:
            self.audit_logger = None
        
        # Validate configuration
        self._validate_config()
        
        # Initialize session
        self._init_session()
        
        logger.info(f"Oracle EAM Connector initialized (auth: {auth_type.value})")
    
    def _validate_config(self):
        """Validate Oracle configuration."""
        required_fields = ['base_url', 'username', 'password']
        
        missing = [field for field in required_fields if field not in self.config]
        if missing:
            raise OracleDataValidationError(f"Missing required configuration fields: {missing}")
        
        if not self.base_url:
            raise OracleDataValidationError("base_url cannot be empty")
    
    def _init_session(self):
        """Initialize REST API session with retry logic."""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "PATCH", "DELETE"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self._connection_pool_size,
            pool_maxsize=self._connection_pool_size
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set authentication
        if self.auth_type == OracleAuthType.BASIC:
            self._setup_basic_auth()
        elif self.auth_type == OracleAuthType.OAUTH2:
            self._setup_oauth2()
        elif self.auth_type == OracleAuthType.TOKEN:
            self._setup_token_auth()
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test connection
        self._test_connection()
        
        logger.info("Oracle EAM REST API session initialized successfully")
    
    def _setup_basic_auth(self):
        """Setup Basic authentication."""
        username = self.config['username']
        password = self.config['password']
        
        # Create Basic Auth header
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        self.session.headers.update({
            'Authorization': f'Basic {encoded_credentials}'
        })
        
        logger.info("Basic authentication configured")
    
    def _setup_oauth2(self):
        """Setup OAuth2 authentication."""
        if 'oauth_token_url' not in self.config:
            raise OracleAuthenticationError("OAuth2 token URL not configured")
        
        try:
            # Request OAuth2 token
            token_response = requests.post(
                self.config['oauth_token_url'],
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.config.get('client_id'),
                    'client_secret': self.config.get('client_secret'),
                    'scope': self.config.get('scope', 'eam:all')
                },
                timeout=10
            )
            token_response.raise_for_status()
            
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                raise OracleAuthenticationError("No access token received")
            
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}'
            })
            
            # Store token expiry for refresh
            self._token_expiry = time.time() + token_data.get('expires_in', 3600)
            
            logger.info("OAuth2 authentication configured successfully")
            
        except Exception as e:
            raise OracleAuthenticationError(f"OAuth2 setup failed: {e}")
    
    def _setup_token_auth(self):
        """Setup token-based authentication."""
        if 'api_token' not in self.config:
            raise OracleAuthenticationError("API token not configured")
        
        self.session.headers.update({
            'Authorization': f'Bearer {self.config["api_token"]}'
        })
        
        logger.info("Token authentication configured")
    
    def _test_connection(self):
        """Test Oracle EAM connection."""
        try:
            # Try to access a simple endpoint
            url = f"{self.base_url}{ORACLE_EAM_ENDPOINTS['ASSETS']}"
            response = self.session.get(
                url,
                params={'limit': 1},
                timeout=self.timeout
            )
            
            if response.status_code in [200, 401, 403]:
                # Connection successful (even if auth fails, we reached the server)
                if response.status_code == 401:
                    raise OracleAuthenticationError("Authentication failed")
                elif response.status_code == 403:
                    logger.warning("Connection successful but access forbidden - check permissions")
                else:
                    logger.info("Oracle EAM connection test successful")
                    
                    if self.audit_logger:
                        self.audit_logger.log_data_access(
                            action="ORACLE_EAM_CONNECTION_TEST",
                            resource="ORACLE_EAM",
                            message="Connection test successful",
                            details={"base_url": self.base_url}
                        )
            else:
                raise OracleConnectionError(f"Connection test failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise OracleConnectionError(f"Connection test failed: {e}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Oracle EAM API.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            json_data: JSON data
            
        Returns:
            Response data as dictionary
            
        Raises:
            OracleAPIError: If request fails
        """
        try:
            url = f"{self.base_url}{endpoint}"
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                timeout=self.timeout
            )
            
            # Handle different status codes
            if response.status_code == 401:
                raise OracleAuthenticationError("Authentication failed - token may have expired")
            elif response.status_code == 403:
                raise OracleAPIError("Access forbidden - insufficient permissions")
            elif response.status_code == 404:
                raise OracleAPIError("Resource not found")
            elif response.status_code >= 400:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_json.get('title', error_detail))
                except:
                    pass
                raise OracleAPIError(f"API request failed: {error_detail}", error_code=str(response.status_code))
            
            # Parse response
            if response.status_code == 204:  # No content
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Oracle EAM API request failed: {e}")
            raise OracleAPIError(f"API request failed: {e}")
    
    # ========================================================================
    # ASSET MANAGEMENT
    # ========================================================================
    
    def get_asset(self, asset_number: str) -> Dict[str, Any]:
        """
        Get asset details from Oracle EAM.
        
        Args:
            asset_number: Asset number/identifier
            
        Returns:
            Dictionary with asset details
            
        Raises:
            OracleAPIError: If retrieval fails
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> asset = connector.get_asset('PUMP-001')
            >>> print(f"Status: {asset['AssetStatus']}")
        """
        try:
            logger.info(f"Retrieving asset: {asset_number}")
            
            # Search for asset by number
            params = {
                'q': f"AssetNumber='{asset_number}'",
                'limit': 1
            }
            
            result = self._make_request(
                'GET',
                ORACLE_EAM_ENDPOINTS['ASSETS'],
                params=params
            )
            
            items = result.get('items', [])
            if not items:
                raise OracleAPIError(f"Asset not found: {asset_number}")
            
            asset_data = items[0]
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="ORACLE_EAM_ASSET_GET",
                    resource="ORACLE_EAM_ASSET",
                    message=f"Retrieved asset {asset_number}",
                    details={"asset_number": asset_number}
                )
            
            return asset_data
            
        except Exception as e:
            logger.error(f"Failed to get asset {asset_number}: {e}")
            raise OracleAPIError(f"Asset retrieval failed: {e}")
    
    def create_asset(
        self,
        asset_number: str,
        description: str,
        asset_group: str,
        organization_id: Optional[str] = None,
        location: Optional[str] = None,
        parent_asset: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new asset in Oracle EAM.
        
        Args:
            asset_number: Unique asset number
            description: Asset description
            asset_group: Asset group/category
            organization_id: Organization ID
            location: Asset location
            parent_asset: Parent asset number (for hierarchy)
            **kwargs: Additional asset attributes
            
        Returns:
            Dictionary with created asset details
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> asset = connector.create_asset(
            ...     asset_number='PUMP-002',
            ...     description='Centrifugal Pump',
            ...     asset_group='PUMPS',
            ...     location='PLANT-A'
            ... )
        """
        try:
            logger.info(f"Creating asset: {asset_number}")
            
            asset_data = {
                'AssetNumber': asset_number,
                'Description': description,
                'AssetGroup': asset_group,
                'AssetStatus': AssetStatus.ACTIVE.value,
                'OrganizationId': organization_id or self.config.get('organization_id'),
                'Location': location or '',
                'ParentAssetNumber': parent_asset or ''
            }
            
            # Add additional attributes
            asset_data.update(kwargs)
            
            result = self._make_request(
                'POST',
                ORACLE_EAM_ENDPOINTS['ASSETS'],
                json_data=asset_data
            )
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="ORACLE_EAM_ASSET_CREATE",
                    resource="ORACLE_EAM_ASSET",
                    message=f"Created asset {asset_number}",
                    details={
                        "asset_number": asset_number,
                        "asset_group": asset_group
                    }
                )
            
            logger.info(f"Asset created successfully: {asset_number}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create asset: {e}")
            raise OracleAPIError(f"Asset creation failed: {e}")
    
    def update_asset_status(
        self,
        asset_number: str,
        status: AssetStatus,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Update asset status.
        
        Args:
            asset_number: Asset number
            status: New asset status
            notes: Status change notes
            
        Returns:
            Dictionary with update result
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> result = connector.update_asset_status(
            ...     'PUMP-001',
            ...     AssetStatus.UNDER_MAINTENANCE,
            ...     'Scheduled maintenance'
            ... )
        """
        try:
            logger.info(f"Updating asset {asset_number} status to {status.value}")
            
            # Get asset to find its ID
            asset = self.get_asset(asset_number)
            asset_id = asset.get('AssetId')
            
            if not asset_id:
                raise OracleAPIError(f"Asset ID not found for {asset_number}")
            
            # Update asset
            update_data = {
                'AssetStatus': status.value,
                'StatusNotes': notes
            }
            
            result = self._make_request(
                'PATCH',
                f"{ORACLE_EAM_ENDPOINTS['ASSETS']}/{asset_id}",
                json_data=update_data
            )
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="ORACLE_EAM_ASSET_UPDATE",
                    resource="ORACLE_EAM_ASSET",
                    message=f"Updated asset {asset_number} status",
                    details={
                        "asset_number": asset_number,
                        "new_status": status.value,
                        "notes": notes
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update asset status: {e}")
            raise OracleAPIError(f"Asset status update failed: {e}")
    
    def sync_assets(self, asset_numbers: List[str]) -> Dict[str, Any]:
        """
        Synchronize multiple assets.
        
        Args:
            asset_numbers: List of asset numbers to sync
            
        Returns:
            Dictionary with sync results
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> result = connector.sync_assets(['PUMP-001', 'PUMP-002'])
            >>> print(f"Synced: {result['success_count']}")
        """
        results = {
            'success_count': 0,
            'error_count': 0,
            'assets': [],
            'errors': []
        }
        
        for asset_number in asset_numbers:
            try:
                asset_data = self.get_asset(asset_number)
                results['assets'].append(asset_data)
                results['success_count'] += 1
            except Exception as e:
                results['errors'].append({
                    'asset_number': asset_number,
                    'error': str(e)
                })
                results['error_count'] += 1
        
        logger.info(f"Asset sync completed: {results['success_count']} success, {results['error_count']} errors")
        return results
    
    # ========================================================================
    # WORK REQUEST MANAGEMENT
    # ========================================================================
    
    def create_work_request(
        self,
        asset_number: str,
        description: str,
        priority: WorkRequestPriority = WorkRequestPriority.MEDIUM,
        requested_start_date: Optional[datetime] = None,
        requested_end_date: Optional[datetime] = None,
        work_type: str = "CORRECTIVE",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a work request in Oracle EAM.
        
        Args:
            asset_number: Asset number
            description: Work request description
            priority: Priority level
            requested_start_date: Requested start date
            requested_end_date: Requested end date
            work_type: Type of work (CORRECTIVE, PREVENTIVE, etc.)
            **kwargs: Additional work request fields
            
        Returns:
            Dictionary with work request details
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> wr = connector.create_work_request(
            ...     asset_number='PUMP-001',
            ...     description='Bearing replacement required',
            ...     priority=WorkRequestPriority.HIGH
            ... )
        """
        try:
            logger.info(f"Creating work request for asset: {asset_number}")
            
            # Get asset details
            asset = self.get_asset(asset_number)
            
            wr_data = {
                'AssetNumber': asset_number,
                'AssetId': asset.get('AssetId'),
                'Description': description,
                'Priority': priority.value,
                'WorkType': work_type,
                'Status': WorkRequestStatus.DRAFT.value,
                'OrganizationId': self.config.get('organization_id'),
                'RequestedStartDate': requested_start_date.isoformat() if requested_start_date else None,
                'RequestedEndDate': requested_end_date.isoformat() if requested_end_date else None
            }
            
            # Add additional fields
            wr_data.update(kwargs)
            
            # Remove None values
            wr_data = {k: v for k, v in wr_data.items() if v is not None}
            
            result = self._make_request(
                'POST',
                ORACLE_EAM_ENDPOINTS['WORK_REQUESTS'],
                json_data=wr_data
            )
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="ORACLE_EAM_WORK_REQUEST_CREATE",
                    resource="ORACLE_EAM_WORK_REQUEST",
                    message=f"Created work request for asset {asset_number}",
                    details={
                        "asset_number": asset_number,
                        "priority": priority.value,
                        "work_type": work_type
                    }
                )
            
            logger.info(f"Work request created successfully: {result.get('WorkRequestNumber')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create work request: {e}")
            raise OracleAPIError(f"Work request creation failed: {e}")
    
    def get_work_request(self, work_request_number: str) -> Dict[str, Any]:
        """
        Get work request details.
        
        Args:
            work_request_number: Work request number
            
        Returns:
            Dictionary with work request details
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> wr = connector.get_work_request('WR-12345')
            >>> print(f"Status: {wr['Status']}")
        """
        try:
            logger.info(f"Retrieving work request: {work_request_number}")
            
            params = {
                'q': f"WorkRequestNumber='{work_request_number}'",
                'limit': 1
            }
            
            result = self._make_request(
                'GET',
                ORACLE_EAM_ENDPOINTS['WORK_REQUESTS'],
                params=params
            )
            
            items = result.get('items', [])
            if not items:
                raise OracleAPIError(f"Work request not found: {work_request_number}")
            
            return items[0]
            
        except Exception as e:
            logger.error(f"Failed to get work request: {e}")
            raise OracleAPIError(f"Work request retrieval failed: {e}")
    
    def update_work_request_status(
        self,
        work_request_number: str,
        status: WorkRequestStatus,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Update work request status.
        
        Args:
            work_request_number: Work request number
            status: New status
            notes: Status change notes
            
        Returns:
            Dictionary with update result
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> result = connector.update_work_request_status(
            ...     'WR-12345',
            ...     WorkRequestStatus.APPROVED
            ... )
        """
        try:
            logger.info(f"Updating work request {work_request_number} status to {status.value}")
            
            # Get work request to find its ID
            wr = self.get_work_request(work_request_number)
            wr_id = wr.get('WorkRequestId')
            
            if not wr_id:
                raise OracleAPIError(f"Work request ID not found for {work_request_number}")
            
            update_data = {
                'Status': status.value,
                'StatusNotes': notes
            }
            
            result = self._make_request(
                'PATCH',
                f"{ORACLE_EAM_ENDPOINTS['WORK_REQUESTS']}/{wr_id}",
                json_data=update_data
            )
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="ORACLE_EAM_WORK_REQUEST_UPDATE",
                    resource="ORACLE_EAM_WORK_REQUEST",
                    message=f"Updated work request {work_request_number} status",
                    details={
                        "work_request_number": work_request_number,
                        "new_status": status.value,
                        "notes": notes
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update work request status: {e}")
            raise OracleAPIError(f"Work request status update failed: {e}")
    
    # ========================================================================
    # MAINTENANCE SCHEDULE MANAGEMENT
    # ========================================================================
    
    def get_maintenance_schedules(
        self,
        asset_number: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get maintenance schedules.
        
        Args:
            asset_number: Filter by asset number (optional)
            active_only: Return only active schedules
            
        Returns:
            List of maintenance schedule dictionaries
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> schedules = connector.get_maintenance_schedules('PUMP-001')
            >>> for schedule in schedules:
            ...     print(f"Schedule: {schedule['ScheduleName']}")
        """
        try:
            logger.info(f"Retrieving maintenance schedules for asset: {asset_number or 'all'}")
            
            params = {}
            if asset_number:
                params['q'] = f"AssetNumber='{asset_number}'"
            if active_only:
                status_filter = "Status='ACTIVE'"
                params['q'] = f"{params.get('q', '')} and {status_filter}" if params.get('q') else status_filter
            
            result = self._make_request(
                'GET',
                ORACLE_EAM_ENDPOINTS['MAINTENANCE_SCHEDULES'],
                params=params
            )
            
            return result.get('items', [])
            
        except Exception as e:
            logger.error(f"Failed to get maintenance schedules: {e}")
            raise OracleAPIError(f"Maintenance schedule retrieval failed: {e}")
    
    # ========================================================================
    # INVENTORY MANAGEMENT
    # ========================================================================
    
    def get_inventory_item(self, item_number: str) -> Dict[str, Any]:
        """
        Get inventory item details.
        
        Args:
            item_number: Inventory item number
            
        Returns:
            Dictionary with item details
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> item = connector.get_inventory_item('BEARING-001')
            >>> print(f"Quantity: {item['OnHandQuantity']}")
        """
        try:
            logger.info(f"Retrieving inventory item: {item_number}")
            
            params = {
                'q': f"ItemNumber='{item_number}'",
                'limit': 1
            }
            
            result = self._make_request(
                'GET',
                ORACLE_EAM_ENDPOINTS['INVENTORY_ITEMS'],
                params=params
            )
            
            items = result.get('items', [])
            if not items:
                raise OracleAPIError(f"Inventory item not found: {item_number}")
            
            return items[0]
            
        except Exception as e:
            logger.error(f"Failed to get inventory item: {e}")
            raise OracleAPIError(f"Inventory item retrieval failed: {e}")
    
    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Oracle EAM connection.
        
        Returns:
            Dictionary with connection test results
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> result = connector.test_connection()
            >>> print(f"Connected: {result['connected']}")
        """
        result = {
            'connected': False,
            'authenticated': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Try to access assets endpoint
            url = f"{self.base_url}{ORACLE_EAM_ENDPOINTS['ASSETS']}"
            response = self.session.get(url, params={'limit': 1}, timeout=10)
            
            if response.status_code == 200:
                result['connected'] = True
                result['authenticated'] = True
            elif response.status_code == 401:
                result['connected'] = True
                result['authenticated'] = False
                result['error'] = 'Authentication failed'
            elif response.status_code == 403:
                result['connected'] = True
                result['authenticated'] = True
                result['warning'] = 'Access forbidden - check permissions'
            else:
                result['error'] = f'Unexpected status code: {response.status_code}'
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get connector health status.
        
        Returns:
            Dictionary with health information
            
        Example:
            >>> connector = OracleEAMConnector(config)
            >>> health = connector.get_health_status()
            >>> print(f"Status: {health['status']}")
        """
        health = {
            'status': 'unknown',
            'base_url': self.base_url,
            'auth_type': self.auth_type.value,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            test_result = self.test_connection()
            
            if test_result['connected'] and test_result['authenticated']:
                health['status'] = 'healthy'
            elif test_result['connected']:
                health['status'] = 'degraded'
                health['reason'] = 'Authentication issue'
            else:
                health['status'] = 'unhealthy'
                health['reason'] = test_result.get('error', 'Connection failed')
            
            health.update(test_result)
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
        
        return health
    
    def close(self):
        """Close Oracle EAM connections."""
        try:
            if self.session:
                self.session.close()
                logger.info("Oracle EAM session closed")
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="ORACLE_EAM_CONNECTION_CLOSE",
                    resource="ORACLE_EAM",
                    message="Connection closed",
                    details={"status": "closed"}
                )
            
        except Exception as e:
            logger.error(f"Error closing Oracle EAM connections: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_oracle_connector(config_path: Optional[str] = None, **kwargs) -> OracleEAMConnector:
    """
    Factory function to create Oracle EAM connector.
    
    Args:
        config_path: Path to JSON configuration file
        **kwargs: Configuration parameters
        
    Returns:
        OracleEAMConnector instance
        
    Example:
        >>> connector = create_oracle_connector(config_path='config/oracle_eam_config.json')
    """
    if config_path:
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = kwargs
    
    return OracleEAMConnector(config)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example configuration
    config = {
        'base_url': 'https://your-instance.oraclecloud.com',
        'username': 'eam_user',
        'password': 'password',
        'organization_id': 'ORG123'
    }
    
    # Create connector
    with OracleEAMConnector(config) as connector:
        # Test connection
        test_result = connector.test_connection()
        print(f"Connection test: {test_result}")
        
        # Get asset
        try:
            asset = connector.get_asset('PUMP-001')
            print(f"Asset: {asset.get('Description')}")
        except OracleAPIError as e:
            print(f"Error: {e}")
        
        # Create work request
        try:
            wr = connector.create_work_request(
                asset_number='PUMP-001',
                description='Scheduled maintenance',
                priority=WorkRequestPriority.MEDIUM
            )
            print(f"Created work request: {wr.get('WorkRequestNumber')}")
        except OracleAPIError as e:
            print(f"Error: {e}")
        
        # Get health status
        health = connector.get_health_status()
        print(f"Health: {health['status']}")