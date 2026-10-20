"""
Tests for CSV and PDF Report Generation and ownership security.
"""

import pytest
from testing_engine.models import TestRun, TestResult
from services.pdf_generator import generate_test_run_pdf


@pytest.mark.django_db
class TestReports:
    def test_pdf_report_generation(self, sample_project, sample_suite, test_user):
        run = TestRun.objects.create(
            project=sample_project,
            suite=sample_suite,
            triggered_by=test_user,
            status='PASSED',
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            total_duration_ms=130.5,
        )
        TestResult.objects.create(
            test_run=run,
            name="Verify Payment Token",
            passed=True,
            status_code=200,
            elapsed_ms=130.5,
        )

        pdf_bytes = generate_test_run_pdf(run)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        # Check standard PDF file header
        assert pdf_bytes.startswith(b'%PDF-')

    def test_csv_export_endpoint(self, client, test_user, sample_project, sample_suite):
        client.force_login(test_user)
        run = TestRun.objects.create(
            project=sample_project,
            suite=sample_suite,
            triggered_by=test_user,
            status='PASSED',
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            total_duration_ms=150.0,
        )
        TestResult.objects.create(
            test_run=run,
            name="Health Check",
            passed=True,
            status_code=200,
            elapsed_ms=150.0,
        )

        resp = client.get(f'/analytics/reports/run/{run.id}/csv/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv'
        assert b"API Sentinel" in resp.content
        assert b"Health Check" in resp.content

    def test_report_ownership_protection(self, client, other_user, sample_project, test_user):
        # Run belongs to test_user
        run = TestRun.objects.create(
            project=sample_project,
            triggered_by=test_user,
            status='PASSED'
        )

        # other_user attempts to download test_user's CSV and PDF reports
        client.force_login(other_user)
        resp_csv = client.get(f'/analytics/reports/run/{run.id}/csv/')
        assert resp_csv.status_code == 404

        resp_pdf = client.get(f'/analytics/reports/run/{run.id}/pdf/')
        assert resp_pdf.status_code == 404
