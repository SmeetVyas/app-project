"""
Tests for Test Suites, Test Engine execution, and Regression Analysis.
"""

from unittest.mock import patch
import pytest
from testing_engine.models import TestSuite, TestCase, Assertion, TestRun, TestResult
from services.test_runner import execute_test_suite
from services.http_client import OutboundResponse
from services.regression_service import compare_test_runs


@pytest.mark.django_db
class TestTestingEngine:
    @patch('services.test_runner.execute_http_request')
    def test_suite_execution_success(self, mock_http, sample_suite, test_user):
        # Mock successful outbound HTTP response
        mock_http.return_value = OutboundResponse(
            status_code=200,
            elapsed_ms=120.0,
            headers={'Content-Type': 'application/json'},
            body='{"status": "charged"}',
            is_json=True,
            parsed_json={"status": "charged"}
        )

        test_run = execute_test_suite(sample_suite, triggered_by=test_user)

        assert test_run.status == 'PASSED'
        assert test_run.total_tests == 1
        assert test_run.passed_tests == 1
        assert test_run.failed_tests == 0
        assert test_run.pass_percentage == 100.0

        result = test_run.results.first()
        assert result.passed
        assert result.status_code == 200

    @patch('services.test_runner.execute_http_request')
    def test_suite_execution_failure_on_failed_assertion(self, mock_http, sample_suite, test_user):
        # Mock response that fails the expected status 200 (returns 500)
        mock_http.return_value = OutboundResponse(
            status_code=500,
            elapsed_ms=150.0,
            body='{"error": "Internal Error"}',
        )

        test_run = execute_test_suite(sample_suite, triggered_by=test_user)

        assert test_run.status == 'FAILED'
        assert test_run.failed_tests == 1
        assert test_run.passed_tests == 0

        result = test_run.results.first()
        assert not result.passed
        assert "Expected status 200, received 500" in result.error_message

    def test_regression_comparison(self, sample_project, sample_suite, test_user):
        # Run 1: Baseline (All passed)
        run1 = TestRun.objects.create(
            project=sample_project,
            suite=sample_suite,
            triggered_by=test_user,
            status='PASSED',
            total_tests=2,
            passed_tests=2,
            failed_tests=0,
            total_duration_ms=200.0,
        )
        TestResult.objects.create(
            test_run=run1, name="Auth Check", passed=True, elapsed_ms=80.0
        )
        TestResult.objects.create(
            test_run=run1, name="Payment Charge", passed=True, elapsed_ms=120.0
        )

        # Run 2: Comparison (Auth Check regressed to fail, Payment Charge latency spiked)
        run2 = TestRun.objects.create(
            project=sample_project,
            suite=sample_suite,
            triggered_by=test_user,
            status='FAILED',
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            total_duration_ms=500.0,
        )
        TestResult.objects.create(
            test_run=run2, name="Auth Check", passed=False, elapsed_ms=85.0, error_message="Expected 200, got 401"
        )
        TestResult.objects.create(
            test_run=run2, name="Payment Charge", passed=True, elapsed_ms=415.0
        )

        diff_data = compare_test_runs(run1, run2)

        assert diff_data['has_regressions']
        assert "Auth Check" in diff_data['functional_regressions']
        assert len(diff_data['performance_regressions']) == 1
        assert diff_data['performance_regressions'][0]['name'] == "Payment Charge"
        assert diff_data['pass_rate_delta'] == -50.0
