"""
Test Runner Service for API Sentinel.

Orchestrates test executions: prepares requests, fetches active credentials, executes
outbound HTTP calls safely, evaluates all assertions, and persists TestRun and TestResult records.
"""

import time
from typing import Optional
from django.utils import timezone
from endpoints.models import Endpoint
from testing_engine.models import TestSuite, TestCase, TestRun, TestResult
from services.http_client import execute_http_request
from services.assertion_engine import evaluate_assertion


def run_single_test_case(test_case: TestCase, test_run: TestRun) -> TestResult:
    """
    Executes an individual TestCase, evaluates its assertions, and creates a TestResult.
    """
    endpoint = test_case.endpoint
    
    # 1. Prepare request headers and parameters
    headers = endpoint.get_headers()
    if test_case.custom_headers_override:
        headers.update(test_case.custom_headers_override)

    params = dict(endpoint.query_params_json or {})
    body = test_case.custom_body_override if test_case.custom_body_override else endpoint.body

    # 2. Execute request safely
    outbound_resp = execute_http_request(
        url=endpoint.url,
        method=endpoint.method,
        headers=headers,
        params=params,
        body=body,
        timeout=endpoint.timeout_seconds,
        allow_redirects=False,
    )

    # 3. Evaluate assertions
    assertion_results = []
    all_assertions_passed = True
    error_message = outbound_resp.error or ""

    active_assertions = list(test_case.assertions.filter(is_active=True))

    # If no custom assertions were defined, default to checking expected_status_code
    if not active_assertions:
        from services.assertion_engine import ASSERTION_STATUS_EQUALS
        res = evaluate_assertion(
            assertion_type=ASSERTION_STATUS_EQUALS,
            target_property="",
            expected_value=str(endpoint.expected_status_code),
            response=outbound_resp
        )
        assertion_results.append(res.to_dict())
        if not res.passed:
            all_assertions_passed = False
            if not error_message:
                error_message = res.message
    else:
        for assertion in active_assertions:
            res = evaluate_assertion(
                assertion_type=assertion.assertion_type,
                target_property=assertion.target_property,
                expected_value=assertion.expected_value,
                response=outbound_resp
            )
            assertion_results.append(res.to_dict())
            if not res.passed:
                all_assertions_passed = False
                if not error_message:
                    error_message = res.message

    # Final pass determination
    overall_passed = all_assertions_passed and (not outbound_resp.error)

    # Sanitize and truncate body preview for persistence
    body_snippet = outbound_resp.body[:4000] if outbound_resp.body else ""

    result = TestResult.objects.create(
        test_run=test_run,
        test_case=test_case,
        endpoint=endpoint,
        name=test_case.name,
        passed=overall_passed,
        status_code=outbound_resp.status_code,
        elapsed_ms=outbound_resp.elapsed_ms,
        response_headers=dict(outbound_resp.headers),
        response_body_preview=body_snippet,
        error_message=error_message,
        assertion_details=assertion_results,
    )
    return result


def execute_test_suite(suite: TestSuite, triggered_by=None, environment_label: str = "Default") -> TestRun:
    """
    Executes all active test cases in a TestSuite in order, recording run metrics.
    """
    test_run = TestRun.objects.create(
        project=suite.project,
        suite=suite,
        triggered_by=triggered_by,
        status='RUNNING',
        environment_label=environment_label,
    )

    cases = suite.test_cases.filter(is_active=True).order_by('order', 'id')
    total_tests = cases.count()
    passed_count = 0
    failed_count = 0
    total_duration = 0.0

    start_wall_time = time.perf_counter()

    for case in cases:
        result = run_single_test_case(case, test_run)
        total_duration += result.elapsed_ms
        if result.passed:
            passed_count += 1
        else:
            failed_count += 1

    overall_duration = (time.perf_counter() - start_wall_time) * 1000.0

    # Determine run status
    if total_tests == 0:
        status = 'PASSED'
    elif failed_count == 0:
        status = 'PASSED'
    else:
        status = 'FAILED'

    test_run.status = status
    test_run.total_tests = total_tests
    test_run.passed_tests = passed_count
    test_run.failed_tests = failed_count
    test_run.total_duration_ms = round(overall_duration, 2)
    test_run.completed_at = timezone.now()
    test_run.save()

    return test_run


def execute_adhoc_endpoint_test(endpoint: Endpoint, user=None) -> tuple[TestRun, TestResult]:
    """
    Executes a quick ad-hoc test directly on an Endpoint without requiring a pre-existing Suite.
    """
    test_run = TestRun.objects.create(
        project=endpoint.project,
        suite=None,
        triggered_by=user,
        status='RUNNING',
        environment_label='Ad-hoc Test',
    )

    # Create dummy or temporary execution
    headers = endpoint.get_headers()
    params = dict(endpoint.query_params_json or {})
    
    outbound_resp = execute_http_request(
        url=endpoint.url,
        method=endpoint.method,
        headers=headers,
        params=params,
        body=endpoint.body,
        timeout=endpoint.timeout_seconds,
    )

    from services.assertion_engine import ASSERTION_STATUS_EQUALS
    res = evaluate_assertion(
        assertion_type=ASSERTION_STATUS_EQUALS,
        target_property="",
        expected_value=str(endpoint.expected_status_code),
        response=outbound_resp
    )

    passed = res.passed and (not outbound_resp.error)
    error_msg = outbound_resp.error or (res.message if not res.passed else "")

    result = TestResult.objects.create(
        test_run=test_run,
        test_case=None,
        endpoint=endpoint,
        name=f"Direct Test: {endpoint.name}",
        passed=passed,
        status_code=outbound_resp.status_code,
        elapsed_ms=outbound_resp.elapsed_ms,
        response_headers=dict(outbound_resp.headers),
        response_body_preview=(outbound_resp.body or "")[:4000],
        error_message=error_msg,
        assertion_details=[res.to_dict()],
    )

    test_run.status = 'PASSED' if passed else 'FAILED'
    test_run.total_tests = 1
    test_run.passed_tests = 1 if passed else 0
    test_run.failed_tests = 0 if passed else 1
    test_run.total_duration_ms = outbound_resp.elapsed_ms
    test_run.completed_at = timezone.now()
    test_run.save()

    return test_run, result
