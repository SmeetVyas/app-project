"""
Pytest configuration and shared fixtures for API Sentinel tests.
"""

import pytest
from django.contrib.auth.models import User
from core.models import Project
from endpoints.models import Endpoint, SecureCredential
from testing_engine.models import TestSuite, TestCase, Assertion, TestRun, TestResult


@pytest.fixture
def test_user(db):
    """Creates a primary test user."""
    return User.objects.create_user(
        username="test_dev",
        email="test_dev@apisentinel.local",
        password="ValidPassword123!"
    )


@pytest.fixture
def other_user(db):
    """Creates a second user to test tenant isolation and permission boundaries."""
    return User.objects.create_user(
        username="other_dev",
        email="other_dev@apisentinel.local",
        password="ValidPassword123!"
    )


@pytest.fixture
def sample_project(db, test_user):
    """Creates a sample project owned by test_user."""
    return Project.objects.create(
        owner=test_user,
        name="Payment Gateway API",
        description="Core billing microservices"
    )


@pytest.fixture
def sample_endpoint(db, sample_project):
    """Creates a sample endpoint."""
    return Endpoint.objects.create(
        project=sample_project,
        name="Charge Credit Card",
        url="https://api.stripe.com/v1/charges",
        method="POST",
        headers_json={"Accept": "application/json"},
        query_params_json={},
        body='{"amount": 2000, "currency": "usd"}',
        expected_status_code=200,
        timeout_seconds=5,
    )


@pytest.fixture
def sample_suite(db, sample_project, sample_endpoint):
    """Creates a sample test suite with test cases and assertions."""
    suite = TestSuite.objects.create(
        project=sample_project,
        name="Billing Smoke Suite",
        description="Verifies charge creation and refund flow"
    )
    tc = TestCase.objects.create(
        suite=suite,
        endpoint=sample_endpoint,
        name="Verify Successful Charge Status",
        order=1,
    )
    from services.assertion_engine import ASSERTION_STATUS_EQUALS, ASSERTION_MAX_LATENCY_MS
    Assertion.objects.create(test_case=tc, assertion_type=ASSERTION_STATUS_EQUALS, expected_value="200")
    Assertion.objects.create(test_case=tc, assertion_type=ASSERTION_MAX_LATENCY_MS, expected_value="1000")
    return suite
