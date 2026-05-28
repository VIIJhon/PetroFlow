"""
Unit Tests for ERP Integrations
================================

Comprehensive test suite for SAP PM and Oracle EAM integrations.

Test Coverage:
- SAP PM connector functionality
- Oracle EAM connector functionality
- Mock API responses
- Error handling scenarios
- Data synchronization
- Authentication mechanisms

Author: Bob
Version: 1.0.0
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

# Import modules to test
try:
    from core.sap_pm_connector import (
        SAPPMConnector,
        SAPConnectionError,
        SAPAuthenticationError,
        SAPAPIError,
        SAPDataValidationError,
        WorkOrderStatus,
        NotificationPriority,
        SAPAuthType
    )
    SAP_PM_AVAILABLE = True
except ImportError:
    SAP_PM_AVAILABLE = False

try:
    from core.oracle_eam_connector import (
        OracleEAMConnector,
        OracleConnectionError,
        OracleAuthenticationError,
        OracleAPIError,
        OracleDataValidationError,
        AssetStatus,
        WorkRequestStatus,
        WorkRequestPriority,
        OracleAuthType
    )
    ORACLE_EAM_AVAILABLE = True
except ImportError:
    ORACLE_EAM_AVAILABLE = False


# ============================================================================
# SAP PM CONNECTOR TESTS
# ============================================================================

@unittest.skipIf(not SAP_PM_AVAILABLE, "SAP PM connector not available")
class TestSAPPMConnector(unittest.TestCase):
    """Test SAP PM connector with mocked connections."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'host': 'sap-test.example.com',
            'client': '100',
            'user': 'test_user',
            'password': 'test_password',
            'sysnr': '00',
            'rest_api_url': 'https://sap-test.example.com/sap/opu/odata/sap'
        }
    
    @patch('core.sap_pm_connector.requests.Session')
    def test_initialization(self, mock_session):
        """Test SAP connector initialization."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        connector = SAPPMConnector(self.config, use_rfc=False)
        
        self.assertIsNotNone(connector)
        self.assertEqual(connector.config['host'], 'sap-test.example.com')
        self.assertFalse(connector.use_rfc)
    
    def test_config_validation(self):
        """Test configuration validation."""
        invalid_config = {'host': 'sap-test.example.com'}
        
        with self.assertRaises(SAPDataValidationError):
            SAPPMConnector(invalid_config, use_rfc=False)
    
    @patch('core.sap_pm_connector.requests.Session')
    def test_sync_equipment_data(self, mock_session):
        """Test equipment data synchronization."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'd': {'Equipment': '10000001', 'EquipmentName': 'Test Equipment'}
        }
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        connector = SAPPMConnector(self.config, use_rfc=False)
        connector.session = mock_session_instance
        
        result = connector.sync_equipment_data(['10000001', '10000002'])
        
        self.assertIn('success_count', result)
        self.assertIn('error_count', result)


# ============================================================================
# ORACLE EAM CONNECTOR TESTS
# ============================================================================

@unittest.skipIf(not ORACLE_EAM_AVAILABLE, "Oracle EAM connector not available")
class TestOracleEAMConnector(unittest.TestCase):
    """Test Oracle EAM connector with mocked connections."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'base_url': 'https://oracle-test.example.com',
            'username': 'test_user',
            'password': 'test_password',
            'organization_id': 'TEST_ORG'
        }
    
    @patch('core.oracle_eam_connector.requests.Session')
    def test_initialization(self, mock_session):
        """Test Oracle connector initialization."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        connector = OracleEAMConnector(self.config)
        
        self.assertIsNotNone(connector)
        self.assertEqual(connector.base_url, 'https://oracle-test.example.com')
    
    def test_config_validation(self):
        """Test configuration validation."""
        invalid_config = {'base_url': 'https://oracle-test.example.com'}
        
        with self.assertRaises(OracleDataValidationError):
            OracleEAMConnector(invalid_config)
    
    @patch('core.oracle_eam_connector.requests.Session')
    def test_get_asset(self, mock_session):
        """Test asset retrieval. Refactored by Jhon Villegas"""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{
                'AssetId': '1001',
                'AssetNumber': 'PUMP-001',
                'Description': 'Test Pump',
                'AssetStatus': 'ACTIVE'
            }]
        }
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        connector = OracleEAMConnector(self.config)
        connector.session = mock_session_instance
        
        result = connector.get_asset('PUMP-001')
        
        self.assertEqual(result['AssetNumber'], 'PUMP-001')
        self.assertEqual(result['Description'], 'Test Pump')
    
    @patch('core.oracle_eam_connector.requests.Session')
    def test_create_work_request(self, mock_session):
        """Test work request creation. Refactored by Jhon Villegas"""
        mock_session_instance = MagicMock()
        
        # Mock connection test response
        mock_connect_response = MagicMock()
        mock_connect_response.status_code = 200
        mock_session_instance.get.return_value = mock_connect_response
        
        # Mock get_asset response
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'items': [{'AssetId': '1001', 'AssetNumber': 'PUMP-001'}]
        }
        
        # Mock create work request response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            'WorkRequestId': '2001',
            'WorkRequestNumber': 'WR-12345',
            'Status': 'DRAFT'
        }
        
        mock_session_instance.request.side_effect = [mock_get_response, mock_post_response]
        mock_session.return_value = mock_session_instance
        
        connector = OracleEAMConnector(self.config)
        connector.session = mock_session_instance
        
        result = connector.create_work_request(
            asset_number='PUMP-001',
            description='Test maintenance',
            priority=WorkRequestPriority.HIGH
        )
        
        self.assertIn('WorkRequestNumber', result)
    
    @patch('core.oracle_eam_connector.requests.Session')
    def test_sync_assets(self, mock_session):
        """Test asset synchronization. Refactored by Jhon Villegas"""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{'AssetNumber': 'PUMP-001', 'Description': 'Test'}]
        }
        mock_session_instance.get.return_value = mock_response
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        connector = OracleEAMConnector(self.config)
        connector.session = mock_session_instance
        
        result = connector.sync_assets(['PUMP-001', 'PUMP-002'])
        
        self.assertIn('success_count', result)
        self.assertIn('error_count', result)
    
    @patch('core.oracle_eam_connector.requests.Session')
    def test_health_check(self, mock_session):
        """Test health check."""
        mock_session_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        connector = OracleEAMConnector(self.config)
        connector.session = mock_session_instance
        
        health = connector.get_health_status()
        
        self.assertIn('status', health)
        self.assertIn('timestamp', health)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@unittest.skipIf(not (SAP_PM_AVAILABLE and ORACLE_EAM_AVAILABLE), 
                 "Both connectors required")
class TestERPIntegration(unittest.TestCase):
    """Test integration scenarios between ERP systems."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sap_config = {
            'host': 'sap-test.example.com',
            'client': '100',
            'user': 'test_user',
            'password': 'test_password',
            'sysnr': '00',
            'rest_api_url': 'https://sap-test.example.com/sap/opu/odata/sap'
        }
        
        self.oracle_config = {
            'base_url': 'https://oracle-test.example.com',
            'username': 'test_user',
            'password': 'test_password',
            'organization_id': 'TEST_ORG'
        }
    
    @patch('core.sap_pm_connector.requests.Session')
    @patch('core.oracle_eam_connector.requests.Session')
    def test_cross_system_sync(self, mock_oracle_session, mock_sap_session):
        """Test synchronization between SAP and Oracle."""
        # Mock SAP session
        mock_sap_instance = MagicMock()
        mock_sap_response = MagicMock()
        mock_sap_response.status_code = 200
        mock_sap_response.json.return_value = {
            'd': {'Equipment': '10000001', 'EquipmentName': 'Test Equipment'}
        }
        mock_sap_instance.get.return_value = mock_sap_response
        mock_sap_session.return_value = mock_sap_instance
        
        # Mock Oracle session
        mock_oracle_instance = MagicMock()
        mock_oracle_response = MagicMock()
        mock_oracle_response.status_code = 200
        mock_oracle_response.json.return_value = {
            'items': [{'AssetNumber': 'PUMP-001', 'Description': 'Test'}]
        }
        mock_oracle_instance.get.return_value = mock_oracle_response
        mock_oracle_instance.request.return_value = mock_oracle_response
        mock_oracle_session.return_value = mock_oracle_instance
        
        # Create connectors
        sap_connector = SAPPMConnector(self.sap_config, use_rfc=False)
        sap_connector.session = mock_sap_instance
        
        oracle_connector = OracleEAMConnector(self.oracle_config)
        oracle_connector.session = mock_oracle_instance
        
        # Test sync
        sap_equipment = sap_connector.get_equipment('10000001')
        oracle_asset = oracle_connector.get_asset('PUMP-001')
        
        self.assertIsNotNone(sap_equipment)
        self.assertIsNotNone(oracle_asset)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()