"""
Unit tests for Outbound HTTP Client with mocked requests.
"""

from unittest.mock import patch, MagicMock
from services.http_client import execute_http_request, redact_headers
import requests


class TestHttpClient:
    def test_header_redaction(self):
        headers = {
            "Authorization": "Bearer secret_jwt_token_12345",
            "X-API-Key": "my_secret_api_key_4567",
            "Content-Type": "application/json",
        }
        redacted = redact_headers(headers)
        assert "Bear" in redacted["Authorization"] and "2345" in redacted["Authorization"]
        assert "••••" in redacted["Authorization"]
        assert "my_s" in redacted["X-API-Key"] and "4567" in redacted["X-API-Key"]
        assert "••••" in redacted["X-API-Key"]
        assert redacted["Content-Type"] == "application/json"

    @patch('services.http_client.validate_outbound_url')
    @patch('requests.Session.request')
    def test_successful_request_execution(self, mock_request, mock_validate):
        mock_validate.return_value = ("https://api.example.com/v1", ["93.184.216.34"])

        # Create mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'Content-Type': 'application/json'}
        mock_resp.encoding = 'utf-8'
        mock_resp.url = "https://api.example.com/v1"
        mock_resp.is_redirect = False
        mock_resp.iter_content.return_value = [b'{"success": true}']
        mock_request.return_value = mock_resp

        outbound = execute_http_request(
            url="https://api.example.com/v1",
            method="GET",
        )

        assert outbound.status_code == 200
        assert outbound.is_json
        assert outbound.parsed_json == {"success": True}
        assert outbound.error is None

    @patch('services.http_client.validate_outbound_url')
    @patch('requests.Session.request')
    def test_timeout_handling(self, mock_request, mock_validate):
        mock_validate.return_value = ("https://api.example.com/slow", ["93.184.216.34"])
        mock_request.side_effect = requests.exceptions.Timeout("Connection timed out")

        outbound = execute_http_request(
            url="https://api.example.com/slow",
            method="GET",
            timeout=5,
        )

        assert outbound.status_code is None
        assert "timed out after 5s" in outbound.error

    @patch('services.http_client.validate_outbound_url')
    @patch('requests.Session.request')
    def test_connection_failure_handling(self, mock_request, mock_validate):
        mock_validate.return_value = ("https://unreachable.example.com", ["93.184.216.34"])
        mock_request.side_effect = requests.exceptions.ConnectionError("Failed to establish a new connection")

        outbound = execute_http_request(
            url="https://unreachable.example.com",
            method="GET",
        )

        assert outbound.status_code is None
        assert "Connection failed" in outbound.error
