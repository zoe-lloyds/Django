from django.test import TestCase
from unittest.mock import patch, MagicMock
import os
from your_app_name.views import trigger_ingestion  # Replace with your actual app name
from django.conf import settings
from django.http import HttpRequest

class IngestionTriggerTestCase(TestCase):

    @patch('your_app_name.views.load_kube_config')  # Mock load_kube_config function
    @patch('os.getenv')
    def test_trigger_ingestion_with_default_kubeconfig(self, mock_getenv, mock_load_kube_config):
        # Setup: Make sure no RTL_ENV environment variable is set
        mock_getenv.return_value = None
        request = HttpRequest()

        # Test: Call the function
        response = trigger_ingestion(request)

        # Assertions
        mock_load_kube_config.assert_called_once()  # Ensure kube config was loaded
        self.assertEqual(response.status_code, 200)  # Check if the function returned a 200 response
        
    @patch('your_app_name.views.load_kube_config')
    @patch('os.getenv')
    def test_trigger_ingestion_with_custom_kubeconfig(self, mock_getenv, mock_load_kube_config):
        # Setup: Simulate RTL_ENV environment variable set to 'bld'
        mock_getenv.side_effect = lambda x: 'bld' if x == 'RTL_ENV' else None
        request = HttpRequest()

        # Test: Call the function
        response = trigger_ingestion(request)

        # Assertions
        mock_load_kube_config.assert_not_called()  # Ensure kube config was NOT loaded
        self.assertEqual(response.status_code, 200)  # Check if the function returned a 200 response

    @patch('your_app_name.views.load_kube_config')
    @patch('os.getenv')
    def test_trigger_ingestion_with_kubeconfig_env_var(self, mock_getenv, mock_load_kube_config):
        # Setup: Simulate the KUBECONFIG environment variable is set
        mock_getenv.side_effect = lambda x: '/path/to/custom/kubeconfig' if x == 'KUBECONFIG' else None
        request = HttpRequest()

        # Test: Call the function
        response = trigger_ingestion(request)

        # Assertions
        mock_load_kube_config.assert_called_once()  # Ensure kube config was loaded
        self.assertEqual(response.status_code, 200)  # Check if the function returned a 200 response
