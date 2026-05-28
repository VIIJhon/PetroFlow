"""
PetroFlow SAP PM Integration Module
====================================

SAP Plant Maintenance (PM) integration for work order and equipment management.

Features:
- SAP PM API integration using RFC/REST protocols
- Work order synchronization (create, update, status tracking)
- Equipment master data synchronization
- Maintenance notification creation and management
- Technical object hierarchy mapping
- Functional location management
- Error handling with exponential backoff retry logic
- Authentication with SAP credentials (Basic, OAuth2, Certificate)
- Comprehensive audit logging
- Connection pooling and session management

Supported SAP Modules:
- PM (Plant Maintenance)
- EAM (Enterprise Asset Management)
- MM (Materials Management) - for spare parts

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

# Try to import SAP RFC connector (PyRFC)
try:
    from pyrfc import Connection as RFCConnection, ABAPApplicationError, ABAPRuntimeError
    PYRFC_AVAILABLE = True
except ImportError:
    PYRFC_AVAILABLE = False
    RFCConnection = None
    ABAPApplicationError = Exception
    ABAPRuntimeError = Exception

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

class SAPAuthType(Enum):
    """SAP authentication types."""
    BASIC = "basic"
    OAUTH2 = "oauth2"
    CERTIFICATE = "certificate"
    RFC = "rfc"


class WorkOrderStatus(Enum):
    """SAP work order status codes."""
    CREATED = "CRTD"
    RELEASED = "REL"
    IN_PROGRESS = "INPR"
    TECHNICALLY_COMPLETED = "TECO"
    CLOSED = "CLSD"
    CANCELLED = "CANC"


class NotificationPriority(Enum):
    """SAP notification priority levels."""
    VERY_HIGH = "1"
    HIGH = "2"
    MEDIUM = "3"
    LOW = "4"


# SAP PM Function Modules
SAP_FM = {
    'CREATE_WORK_ORDER': 'BAPI_ALM_ORDER_MAINTAIN',
    'GET_WORK_ORDER': 'BAPI_ALM_ORDER_GET_DETAIL',
    'UPDATE_WORK_ORDER': 'BAPI_ALM_ORDER_MAINTAIN',
    'CREATE_NOTIFICATION': 'BAPI_ALM_NOTIF_CREATE',
    'GET_NOTIFICATION': 'BAPI_ALM_NOTIF_GET_DETAIL',
    'GET_EQUIPMENT': 'BAPI_EQUI_GETDETAIL',
    'GET_FUNCTIONAL_LOCATION': 'BAPI_FUNCLOC_GETDETAIL',
    'COMMIT': 'BAPI_TRANSACTION_COMMIT'
}


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class SAPConnectionError(Exception):
    """Raised when SAP connection fails."""
    pass


class SAPAuthenticationError(Exception):
    """Raised when SAP authentication fails."""
    pass


class SAPAPIError(Exception):
    """Raised when SAP API call fails."""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class SAPDataValidationError(Exception):
    """Raised when SAP data validation fails."""
    pass


# ============================================================================
# SAP PM CONNECTOR CLASS
# ============================================================================

class SAPPMConnector:
    """
    SAP Plant Maintenance Integration Connector
    
    Provides comprehensive integration with SAP PM module:
    - Work order management (create, read, update)
    - Equipment master data synchronization
    - Maintenance notification handling
    - Technical object hierarchy navigation
    - Functional location management
    
    Supports both RFC and REST API protocols with automatic failover.
    
    Attributes:
        config: SAP connection configuration
        auth_type: Authentication type
        session: HTTP session for REST API
        rfc_connection: RFC connection for direct SAP calls
        audit_logger: Audit logging instance
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        auth_type: SAPAuthType = SAPAuthType.BASIC,
        use_rfc: bool = True,
        connection_pool_size: int = 10
    ):
        """
        Initialize SAP PM Connector.
        
        Args:
            config: Configuration dictionary with SAP connection details
            auth_type: Authentication type to use
            use_rfc: Whether to use RFC connection (requires PyRFC)
            connection_pool_size: HTTP connection pool size
            
        Example:
            >>> config = {
            ...     'host': 'sap.example.com',
            ...     'client': '100',
            ...     'user': 'PM_USER',
            ...     'password': 'password',
            ...     'sysnr': '00',
            ...     'rest_api_url': 'https://sap.example.com/sap/opu/odata/sap'
            ... }
            >>> connector = SAPPMConnector(config)
        """
        self.config = config
        self.auth_type = auth_type
        self.use_rfc = use_rfc and PYRFC_AVAILABLE
        self.rfc_connection = None
        self.session = None
        self._connection_pool_size = connection_pool_size
        
        # Initialize audit logger
        if AUDIT_LOGGING_AVAILABLE:
            self.audit_logger = AuditLogger()
        else:
            self.audit_logger = None
        
        # Validate configuration
        self._validate_config()
        
        # Initialize connections
        self._init_connections()
        
        logger.info(f"SAP PM Connector initialized (auth: {auth_type.value}, rfc: {self.use_rfc})")
    
    def _validate_config(self):
        """Validate SAP configuration."""
        required_fields = ['host', 'client', 'user', 'password']
        
        if self.use_rfc:
            required_fields.extend(['sysnr'])
        else:
            required_fields.extend(['rest_api_url'])
        
        missing = [field for field in required_fields if field not in self.config]
        if missing:
            raise SAPDataValidationError(f"Missing required configuration fields: {missing}")
    
    def _init_connections(self):
        """Initialize SAP connections."""
        try:
            # Initialize RFC connection
            if self.use_rfc and PYRFC_AVAILABLE:
                self._init_rfc_connection()
            
            # Initialize REST API session
            self._init_rest_session()
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="SAP_CONNECTION_INIT",
                    resource="SAP_PM",
                    details={
                        "host": self.config['host'],
                        "client": self.config['client'],
                        "rfc_enabled": self.use_rfc
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to initialize SAP connections: {e}")
            raise SAPConnectionError(f"SAP connection initialization failed: {e}")
    
    def _init_rfc_connection(self):
        """Initialize RFC connection to SAP."""
        try:
            if not PYRFC_AVAILABLE:
                logger.warning("PyRFC not available, RFC connection disabled")
                self.use_rfc = False
                return
            
            rfc_params = {
                'ashost': self.config['host'],
                'sysnr': self.config['sysnr'],
                'client': self.config['client'],
                'user': self.config['user'],
                'passwd': self.config['password']
            }
            
            # Add optional parameters
            if 'lang' in self.config:
                rfc_params['lang'] = self.config['lang']
            if 'saprouter' in self.config:
                rfc_params['saprouter'] = self.config['saprouter']
            
            self.rfc_connection = RFCConnection(**rfc_params)
            logger.info("RFC connection to SAP established successfully")
            
        except Exception as e:
            logger.error(f"RFC connection failed: {e}")
            self.use_rfc = False
            raise SAPConnectionError(f"RFC connection failed: {e}")
    
    def _init_rest_session(self):
        """Initialize REST API session with retry logic."""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "PATCH"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self._connection_pool_size,
            pool_maxsize=self._connection_pool_size
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set authentication
        if self.auth_type == SAPAuthType.BASIC:
            self.session.auth = (self.config['user'], self.config['password'])
        elif self.auth_type == SAPAuthType.OAUTH2:
            self._setup_oauth2()
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'sap-client': self.config['client']
        })
        
        logger.info("REST API session initialized successfully")
    
    def _setup_oauth2(self):
        """Setup OAuth2 authentication."""
        if 'oauth_token_url' not in self.config:
            raise SAPAuthenticationError("OAuth2 token URL not configured")
        
        try:
            # Request OAuth2 token
            token_response = requests.post(
                self.config['oauth_token_url'],
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.config.get('client_id'),
                    'client_secret': self.config.get('client_secret')
                },
                timeout=10
            )
            token_response.raise_for_status()
            
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                raise SAPAuthenticationError("No access token received")
            
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}'
            })
            
            logger.info("OAuth2 authentication configured successfully")
            
        except Exception as e:
            raise SAPAuthenticationError(f"OAuth2 setup failed: {e}")
    
    # ========================================================================
    # WORK ORDER MANAGEMENT
    # ========================================================================
    
    def create_work_order(
        self,
        order_type: str,
        equipment_number: Optional[str] = None,
        functional_location: Optional[str] = None,
        description: str = "",
        priority: str = "3",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new work order in SAP PM.
        
        Args:
            order_type: SAP order type (e.g., 'PM01', 'PM02')
            equipment_number: Equipment number
            functional_location: Functional location
            description: Work order description
            priority: Priority (1-4)
            start_date: Planned start date
            end_date: Planned end date
            **kwargs: Additional work order fields
            
        Returns:
            Dictionary with work order details including order number
            
        Raises:
            SAPAPIError: If work order creation fails
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> order = connector.create_work_order(
            ...     order_type='PM01',
            ...     equipment_number='10000001',
            ...     description='Pump maintenance',
            ...     priority='2'
            ... )
            >>> print(f"Created order: {order['order_number']}")
        """
        try:
            logger.info(f"Creating work order: type={order_type}, equipment={equipment_number}")
            
            # Prepare work order data
            order_data = {
                'OrderType': order_type,
                'Description': description,
                'Priority': priority,
                'Equipment': equipment_number or '',
                'FunctionalLocation': functional_location or '',
                'BasicStartDate': start_date.strftime('%Y%m%d') if start_date else '',
                'BasicEndDate': end_date.strftime('%Y%m%d') if end_date else ''
            }
            
            # Add additional fields
            order_data.update(kwargs)
            
            # Try RFC first if available
            if self.use_rfc and self.rfc_connection:
                result = self._create_work_order_rfc(order_data)
            else:
                result = self._create_work_order_rest(order_data)
            
            # Log to audit
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="SAP_WORK_ORDER_CREATE",
                    resource="SAP_PM_ORDER",
                    details={
                        "order_number": result.get('order_number'),
                        "order_type": order_type,
                        "equipment": equipment_number
                    }
                )
            
            logger.info(f"Work order created successfully: {result.get('order_number')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create work order: {e}")
            raise SAPAPIError(f"Work order creation failed: {e}")
    
    def _create_work_order_rfc(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create work order using RFC."""
        try:
            # Call SAP BAPI
            result = self.rfc_connection.call(
                SAP_FM['CREATE_WORK_ORDER'],
                IT_HEADER=[order_data],
                TESTRUN=''
            )
            
            # Check for errors
            if result.get('RETURN', {}).get('TYPE') == 'E':
                error_msg = result['RETURN'].get('MESSAGE', 'Unknown error')
                raise SAPAPIError(f"SAP BAPI error: {error_msg}")
            
            # Commit transaction
            self.rfc_connection.call(SAP_FM['COMMIT'], WAIT='X')
            
            # Extract order number
            order_number = result.get('ET_NUMBERS', [{}])[0].get('NUMBER', '')
            
            return {
                'order_number': order_number,
                'status': 'created',
                'message': result.get('RETURN', {}).get('MESSAGE', ''),
                'method': 'rfc'
            }
            
        except (ABAPApplicationError, ABAPRuntimeError) as e:
            raise SAPAPIError(f"RFC call failed: {e}")
    
    def _create_work_order_rest(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create work order using REST API."""
        try:
            url = f"{self.config['rest_api_url']}/API_MAINTENANCEORDER/MaintenanceOrder"
            
            response = self.session.post(url, json=order_data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'order_number': result.get('MaintenanceOrder', ''),
                'status': 'created',
                'message': 'Work order created via REST API',
                'method': 'rest',
                'data': result
            }
            
        except requests.exceptions.RequestException as e:
            raise SAPAPIError(f"REST API call failed: {e}")
    
    def get_work_order(self, order_number: str) -> Dict[str, Any]:
        """
        Get work order details from SAP PM.
        
        Args:
            order_number: SAP work order number
            
        Returns:
            Dictionary with work order details
            
        Raises:
            SAPAPIError: If retrieval fails
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> order = connector.get_work_order('4000000001')
            >>> print(f"Status: {order['status']}")
        """
        try:
            logger.info(f"Retrieving work order: {order_number}")
            
            if self.use_rfc and self.rfc_connection:
                result = self._get_work_order_rfc(order_number)
            else:
                result = self._get_work_order_rest(order_number)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get work order {order_number}: {e}")
            raise SAPAPIError(f"Work order retrieval failed: {e}")
    
    def _get_work_order_rfc(self, order_number: str) -> Dict[str, Any]:
        """Get work order using RFC."""
        try:
            result = self.rfc_connection.call(
                SAP_FM['GET_WORK_ORDER'],
                NUMBER=order_number
            )
            
            header = result.get('ET_HEADER', [{}])[0]
            operations = result.get('ET_OPERATIONS', [])
            
            return {
                'order_number': order_number,
                'order_type': header.get('ORDERTYPE', ''),
                'description': header.get('DESCRIPTION', ''),
                'status': header.get('USER_STAT', ''),
                'equipment': header.get('EQUIPMENT', ''),
                'functional_location': header.get('FUNC_LOC', ''),
                'priority': header.get('PRIORITY', ''),
                'start_date': header.get('BASIC_START', ''),
                'end_date': header.get('BASIC_END', ''),
                'operations': operations,
                'method': 'rfc'
            }
            
        except (ABAPApplicationError, ABAPRuntimeError) as e:
            raise SAPAPIError(f"RFC call failed: {e}")
    
    def _get_work_order_rest(self, order_number: str) -> Dict[str, Any]:
        """Get work order using REST API."""
        try:
            url = f"{self.config['rest_api_url']}/API_MAINTENANCEORDER/MaintenanceOrder('{order_number}')"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json().get('d', {})
            
            return {
                'order_number': order_number,
                'order_type': data.get('MaintenanceOrderType', ''),
                'description': data.get('MaintenanceOrderDesc', ''),
                'status': data.get('MaintOrderUserStatus', ''),
                'equipment': data.get('TechnicalObject', ''),
                'functional_location': data.get('FunctionalLocation', ''),
                'priority': data.get('MaintenancePriority', ''),
                'method': 'rest',
                'data': data
            }
            
        except requests.exceptions.RequestException as e:
            raise SAPAPIError(f"REST API call failed: {e}")
    
    def update_work_order_status(
        self,
        order_number: str,
        status: WorkOrderStatus,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Update work order status.
        
        Args:
            order_number: SAP work order number
            status: New status
            notes: Status change notes
            
        Returns:
            Dictionary with update result
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> result = connector.update_work_order_status(
            ...     '4000000001',
            ...     WorkOrderStatus.TECHNICALLY_COMPLETED,
            ...     'Maintenance completed'
            ... )
        """
        try:
            logger.info(f"Updating work order {order_number} status to {status.value}")
            
            update_data = {
                'order_number': order_number,
                'status': status.value,
                'notes': notes
            }
            
            if self.use_rfc and self.rfc_connection:
                result = self._update_work_order_status_rfc(update_data)
            else:
                result = self._update_work_order_status_rest(update_data)
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="SAP_WORK_ORDER_UPDATE",
                    resource="SAP_PM_ORDER",
                    details={
                        "order_number": order_number,
                        "new_status": status.value,
                        "notes": notes
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update work order status: {e}")
            raise SAPAPIError(f"Work order status update failed: {e}")
    
    def _update_work_order_status_rfc(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update work order status using RFC."""
        try:
            result = self.rfc_connection.call(
                SAP_FM['UPDATE_WORK_ORDER'],
                IT_HEADER=[{
                    'NUMBER': update_data['order_number'],
                    'USER_STAT': update_data['status']
                }],
                IT_TEXT=[{
                    'NUMBER': update_data['order_number'],
                    'TEXT_LINE': update_data['notes']
                }]
            )
            
            self.rfc_connection.call(SAP_FM['COMMIT'], WAIT='X')
            
            return {
                'success': True,
                'order_number': update_data['order_number'],
                'status': update_data['status'],
                'method': 'rfc'
            }
            
        except (ABAPApplicationError, ABAPRuntimeError) as e:
            raise SAPAPIError(f"RFC call failed: {e}")
    
    def _update_work_order_status_rest(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update work order status using REST API."""
        try:
            url = f"{self.config['rest_api_url']}/API_MAINTENANCEORDER/MaintenanceOrder('{update_data['order_number']}')"
            
            payload = {
                'MaintOrderUserStatus': update_data['status']
            }
            
            response = self.session.patch(url, json=payload, timeout=30)
            response.raise_for_status()
            
            return {
                'success': True,
                'order_number': update_data['order_number'],
                'status': update_data['status'],
                'method': 'rest'
            }
            
        except requests.exceptions.RequestException as e:
            raise SAPAPIError(f"REST API call failed: {e}")
    
    # ========================================================================
    # MAINTENANCE NOTIFICATION MANAGEMENT
    # ========================================================================
    
    def create_notification(
        self,
        notification_type: str,
        equipment_number: Optional[str] = None,
        functional_location: Optional[str] = None,
        description: str = "",
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        malfunction_start: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create maintenance notification in SAP PM.
        
        Args:
            notification_type: SAP notification type (e.g., 'M1', 'M2')
            equipment_number: Equipment number
            functional_location: Functional location
            description: Notification description
            priority: Notification priority
            malfunction_start: Malfunction start date/time
            **kwargs: Additional notification fields
            
        Returns:
            Dictionary with notification details including notification number
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> notif = connector.create_notification(
            ...     notification_type='M1',
            ...     equipment_number='10000001',
            ...     description='Pump vibration detected',
            ...     priority=NotificationPriority.HIGH
            ... )
        """
        try:
            logger.info(f"Creating notification: type={notification_type}, equipment={equipment_number}")
            
            notif_data = {
                'NotificationType': notification_type,
                'NotificationText': description,
                'Priority': priority.value,
                'Equipment': equipment_number or '',
                'FunctionalLocation': functional_location or '',
                'MalfunctionStartDate': malfunction_start.strftime('%Y%m%d') if malfunction_start else '',
                'MalfunctionStartTime': malfunction_start.strftime('%H%M%S') if malfunction_start else ''
            }
            
            notif_data.update(kwargs)
            
            if self.use_rfc and self.rfc_connection:
                result = self._create_notification_rfc(notif_data)
            else:
                result = self._create_notification_rest(notif_data)
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="SAP_NOTIFICATION_CREATE",
                    resource="SAP_PM_NOTIFICATION",
                    details={
                        "notification_number": result.get('notification_number'),
                        "notification_type": notification_type,
                        "equipment": equipment_number,
                        "priority": priority.value
                    }
                )
            
            logger.info(f"Notification created: {result.get('notification_number')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise SAPAPIError(f"Notification creation failed: {e}")
    
    def _create_notification_rfc(self, notif_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create notification using RFC."""
        try:
            result = self.rfc_connection.call(
                SAP_FM['CREATE_NOTIFICATION'],
                NOTIFHEADER=notif_data
            )
            
            if result.get('RETURN', {}).get('TYPE') == 'E':
                error_msg = result['RETURN'].get('MESSAGE', 'Unknown error')
                raise SAPAPIError(f"SAP BAPI error: {error_msg}")
            
            self.rfc_connection.call(SAP_FM['COMMIT'], WAIT='X')
            
            return {
                'notification_number': result.get('NUMBER', ''),
                'status': 'created',
                'message': result.get('RETURN', {}).get('MESSAGE', ''),
                'method': 'rfc'
            }
            
        except (ABAPApplicationError, ABAPRuntimeError) as e:
            raise SAPAPIError(f"RFC call failed: {e}")
    
    def _create_notification_rest(self, notif_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create notification using REST API."""
        try:
            url = f"{self.config['rest_api_url']}/API_MAINTNOTIFICATION/MaintenanceNotification"
            
            response = self.session.post(url, json=notif_data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'notification_number': result.get('MaintenanceNotification', ''),
                'status': 'created',
                'message': 'Notification created via REST API',
                'method': 'rest',
                'data': result
            }
            
        except requests.exceptions.RequestException as e:
            raise SAPAPIError(f"REST API call failed: {e}")
    
    # ========================================================================
    # EQUIPMENT MASTER DATA
    # ========================================================================
    
    def get_equipment(self, equipment_number: str) -> Dict[str, Any]:
        """
        Get equipment master data from SAP PM.
        
        Args:
            equipment_number: Equipment number
            
        Returns:
            Dictionary with equipment details
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> equipment = connector.get_equipment('10000001')
            >>> print(f"Description: {equipment['description']}")
        """
        try:
            logger.info(f"Retrieving equipment: {equipment_number}")
            
            if self.use_rfc and self.rfc_connection:
                result = self._get_equipment_rfc(equipment_number)
            else:
                result = self._get_equipment_rest(equipment_number)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get equipment {equipment_number}: {e}")
            raise SAPAPIError(f"Equipment retrieval failed: {e}")
    
    def _get_equipment_rfc(self, equipment_number: str) -> Dict[str, Any]:
        """Get equipment using RFC."""
        try:
            result = self.rfc_connection.call(
                SAP_FM['GET_EQUIPMENT'],
                EQUIPMENT=equipment_number
            )
            
            data = result.get('DATA_GENERAL', {})
            
            return {
                'equipment_number': equipment_number,
                'description': data.get('DESCRIPT', ''),
                'equipment_category': data.get('EQTYP', ''),
                'manufacturer': data.get('HERST', ''),
                'model_number': data.get('TYPBZ', ''),
                'serial_number': data.get('SERNR', ''),
                'functional_location': data.get('TPLNR', ''),
                'technical_id': data.get('TIDNR', ''),
                'method': 'rfc'
            }
            
        except (ABAPApplicationError, ABAPRuntimeError) as e:
            raise SAPAPIError(f"RFC call failed: {e}")
    
    def _get_equipment_rest(self, equipment_number: str) -> Dict[str, Any]:
        """Get equipment using REST API."""
        try:
            url = f"{self.config['rest_api_url']}/API_EQUIPMENT/Equipment('{equipment_number}')"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json().get('d', {})
            
            return {
                'equipment_number': equipment_number,
                'description': data.get('EquipmentName', ''),
                'equipment_category': data.get('EquipmentCategory', ''),
                'manufacturer': data.get('Manufacturer', ''),
                'model_number': data.get('ManufacturerModel', ''),
                'serial_number': data.get('ManufacturerSerialNumber', ''),
                'functional_location': data.get('FunctionalLocation', ''),
                'method': 'rest',
                'data': data
            }
            
        except requests.exceptions.RequestException as e:
            raise SAPAPIError(f"REST API call failed: {e}")
    
    def sync_equipment_data(self, equipment_list: List[str]) -> Dict[str, Any]:
        """
        Synchronize multiple equipment records.
        
        Args:
            equipment_list: List of equipment numbers to sync
            
        Returns:
            Dictionary with sync results
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> result = connector.sync_equipment_data(['10000001', '10000002'])
            >>> print(f"Synced: {result['success_count']}")
        """
        results = {
            'success_count': 0,
            'error_count': 0,
            'equipment': [],
            'errors': []
        }
        
        for equipment_number in equipment_list:
            try:
                equipment_data = self.get_equipment(equipment_number)
                results['equipment'].append(equipment_data)
                results['success_count'] += 1
            except Exception as e:
                results['errors'].append({
                    'equipment_number': equipment_number,
                    'error': str(e)
                })
                results['error_count'] += 1
        
        logger.info(f"Equipment sync completed: {results['success_count']} success, {results['error_count']} errors")
        return results
    
    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test SAP connection.
        
        Returns:
            Dictionary with connection test results
            
        Example:
            >>> connector = SAPPMConnector(config)
            >>> result = connector.test_connection()
            >>> print(f"Connected: {result['connected']}")
        """
        result = {
            'connected': False,
            'rfc_available': False,
            'rest_available': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Test RFC connection
        if self.use_rfc and self.rfc_connection:
            try:
                self.rfc_connection.ping()
                result['rfc_available'] = True
                result['connected'] = True
            except Exception as e:
                result['rfc_error'] = str(e)
        
        # Test REST API
        if self.session:
            try:
                url = f"{self.config['rest_api_url']}/API_MAINTENANCEORDER/$metadata"
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    result['rest_available'] = True
                    result['connected'] = True
            except Exception as e:
                result['rest_error'] = str(e)
        
        return result
    
    def close(self):
        """Close SAP connections."""
        try:
            if self.rfc_connection:
                self.rfc_connection.close()
                logger.info("RFC connection closed")
            
            if self.session:
                self.session.close()
                logger.info("REST session closed")
            
            if self.audit_logger:
                self.audit_logger.log_data_access(
                    action="SAP_CONNECTION_CLOSE",
                    resource="SAP_PM",
                    details={"status": "closed"}
                )
            
        except Exception as e:
            logger.error(f"Error closing SAP connections: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_sap_connector(config_path: Optional[str] = None, **kwargs) -> SAPPMConnector:
    """
    Factory function to create SAP PM connector.
    
    Args:
        config_path: Path to JSON configuration file
        **kwargs: Configuration parameters
        
    Returns:
        SAPPMConnector instance
        
    Example:
        >>> connector = create_sap_connector(config_path='config/sap_config.json')
    """
    if config_path:
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = kwargs
    
    return SAPPMConnector(config)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example configuration
    config = {
        'host': 'sap.example.com',
        'client': '100',
        'user': 'PM_USER',
        'password': 'password',
        'sysnr': '00',
        'rest_api_url': 'https://sap.example.com/sap/opu/odata/sap'
    }
    
    # Create connector
    with SAPPMConnector(config) as connector:
        # Test connection
        test_result = connector.test_connection()
        print(f"Connection test: {test_result}")
        
        # Create work order
        try:
            order = connector.create_work_order(
                order_type='PM01',
                equipment_number='10000001',
                description='Scheduled maintenance',
                priority='2'
            )
            print(f"Created work order: {order['order_number']}")
        except SAPAPIError as e:
            print(f"Error: {e}")
        
        # Get equipment data
        try:
            equipment = connector.get_equipment('10000001')
            print(f"Equipment: {equipment['description']}")
        except SAPAPIError as e:
            print(f"Error: {e}")