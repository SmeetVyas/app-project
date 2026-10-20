"""
Unit tests for the Declarative Assertion Engine.
"""

from services.http_client import OutboundResponse
from services.assertion_engine import (
    evaluate_assertion,
    extract_json_path,
    ASSERTION_STATUS_EQUALS,
    ASSERTION_STATUS_IN,
    ASSERTION_MAX_LATENCY_MS,
    ASSERTION_CONTENT_TYPE_CONTAINS,
    ASSERTION_JSON_PROP_EXISTS,
    ASSERTION_JSON_VALUE_EQUALS,
    ASSERTION_JSON_VALUE_TYPE,
    ASSERTION_BODY_CONTAINS,
    ASSERTION_BODY_REGEX,
    ASSERTION_HEADER_EXISTS,
    ASSERTION_HEADER_EQUALS,
)


class TestAssertionEngine:
    def test_json_path_extraction(self):
        data = {
            "user": {
                "id": 42,
                "profile": {"name": "Alice"}
            },
            "items": [
                {"sku": "ABC", "qty": 5},
                {"sku": "XYZ", "qty": 10}
            ]
        }

        found, val = extract_json_path(data, "user.id")
        assert found and val == 42

        found, val = extract_json_path(data, "user.profile.name")
        assert found and val == "Alice"

        found, val = extract_json_path(data, "items[0].sku")
        assert found and val == "ABC"

        found, val = extract_json_path(data, "items.1.qty")
        assert found and val == 10

        found, val = extract_json_path(data, "user.non_existent")
        assert not found

    def test_status_code_equals(self):
        resp = OutboundResponse(status_code=200, elapsed_ms=85.0)
        res = evaluate_assertion(ASSERTION_STATUS_EQUALS, "", "200", resp)
        assert res.passed

        res_fail = evaluate_assertion(ASSERTION_STATUS_EQUALS, "", "201", resp)
        assert not res_fail.passed

    def test_status_code_in_list(self):
        resp = OutboundResponse(status_code=204, elapsed_ms=50.0)
        res = evaluate_assertion(ASSERTION_STATUS_IN, "", "200, 201, 204", resp)
        assert res.passed

        res_fail = evaluate_assertion(ASSERTION_STATUS_IN, "", "200 400", resp)
        assert not res_fail.passed

    def test_max_latency(self):
        resp = OutboundResponse(status_code=200, elapsed_ms=150.0)
        assert evaluate_assertion(ASSERTION_MAX_LATENCY_MS, "", "300", resp).passed
        assert not evaluate_assertion(ASSERTION_MAX_LATENCY_MS, "", "100", resp).passed

    def test_content_type_contains(self):
        resp = OutboundResponse(status_code=200, content_type="application/json; charset=utf-8")
        assert evaluate_assertion(ASSERTION_CONTENT_TYPE_CONTAINS, "", "application/json", resp).passed
        assert not evaluate_assertion(ASSERTION_CONTENT_TYPE_CONTAINS, "", "text/html", resp).passed

    def test_json_property_exists(self):
        resp = OutboundResponse(
            status_code=200,
            is_json=True,
            parsed_json={"data": {"token": "xyz"}}
        )
        assert evaluate_assertion(ASSERTION_JSON_PROP_EXISTS, "data.token", "exists", resp).passed
        assert not evaluate_assertion(ASSERTION_JSON_PROP_EXISTS, "data.missing", "exists", resp).passed

    def test_json_value_equals(self):
        resp = OutboundResponse(
            status_code=200,
            is_json=True,
            parsed_json={"status": "success", "count": 10, "active": True}
        )
        assert evaluate_assertion(ASSERTION_JSON_VALUE_EQUALS, "status", "success", resp).passed
        assert evaluate_assertion(ASSERTION_JSON_VALUE_EQUALS, "count", "10", resp).passed
        assert evaluate_assertion(ASSERTION_JSON_VALUE_EQUALS, "active", "true", resp).passed
        assert not evaluate_assertion(ASSERTION_JSON_VALUE_EQUALS, "count", "99", resp).passed

    def test_json_value_type(self):
        resp = OutboundResponse(
            status_code=200,
            is_json=True,
            parsed_json={"id": 12, "name": "Bob", "tags": ["admin", "staff"]}
        )
        assert evaluate_assertion(ASSERTION_JSON_VALUE_TYPE, "id", "number", resp).passed
        assert evaluate_assertion(ASSERTION_JSON_VALUE_TYPE, "name", "string", resp).passed
        assert evaluate_assertion(ASSERTION_JSON_VALUE_TYPE, "tags", "array", resp).passed

    def test_body_contains_and_regex(self):
        resp = OutboundResponse(status_code=200, body="Error Code 409: Duplicate Transaction")
        assert evaluate_assertion(ASSERTION_BODY_CONTAINS, "", "Duplicate Transaction", resp).passed
        assert evaluate_assertion(ASSERTION_BODY_REGEX, "", r"Error Code \d{3}", resp).passed

    def test_headers_assertions(self):
        resp = OutboundResponse(status_code=200, headers={"X-RateLimit-Remaining": "50"})
        assert evaluate_assertion(ASSERTION_HEADER_EXISTS, "X-RateLimit-Remaining", "", resp).passed
        assert evaluate_assertion(ASSERTION_HEADER_EQUALS, "X-RateLimit-Remaining", "50", resp).passed
        assert not evaluate_assertion(ASSERTION_HEADER_EQUALS, "X-RateLimit-Remaining", "100", resp).passed
