"""
Declarative Assertion Engine for API Sentinel.

Safely evaluates HTTP responses against configured criteria without using eval(), exec(),
or shell execution. Compares status codes, latency, headers, body text, and JSON structures.
"""

import json
import re
from typing import Any, Optional
from services.http_client import OutboundResponse

# Assertion Type Constants
ASSERTION_STATUS_EQUALS = 'STATUS_EQUALS'
ASSERTION_STATUS_IN = 'STATUS_IN'
ASSERTION_MAX_LATENCY_MS = 'MAX_LATENCY_MS'
ASSERTION_CONTENT_TYPE_CONTAINS = 'CONTENT_TYPE_CONTAINS'
ASSERTION_JSON_PROP_EXISTS = 'JSON_PROP_EXISTS'
ASSERTION_JSON_VALUE_EQUALS = 'JSON_VALUE_EQUALS'
ASSERTION_JSON_VALUE_TYPE = 'JSON_VALUE_TYPE'
ASSERTION_BODY_CONTAINS = 'BODY_CONTAINS'
ASSERTION_BODY_REGEX = 'BODY_REGEX'
ASSERTION_HEADER_EXISTS = 'HEADER_EXISTS'
ASSERTION_HEADER_EQUALS = 'HEADER_EQUALS'

ASSERTION_TYPE_CHOICES = [
    (ASSERTION_STATUS_EQUALS, 'Status Code Equals'),
    (ASSERTION_STATUS_IN, 'Status Code In List (e.g. 200, 201)'),
    (ASSERTION_MAX_LATENCY_MS, 'Maximum Response Time (ms)'),
    (ASSERTION_CONTENT_TYPE_CONTAINS, 'Content-Type Contains'),
    (ASSERTION_JSON_PROP_EXISTS, 'JSON Property Exists (dot-path)'),
    (ASSERTION_JSON_VALUE_EQUALS, 'JSON Value Equals (path & value)'),
    (ASSERTION_JSON_VALUE_TYPE, 'JSON Value Type (string, number, boolean, array, object)'),
    (ASSERTION_BODY_CONTAINS, 'Response Body Contains Text'),
    (ASSERTION_BODY_REGEX, 'Response Body Matches Regex'),
    (ASSERTION_HEADER_EXISTS, 'Header Exists'),
    (ASSERTION_HEADER_EQUALS, 'Header Value Equals'),
]


def extract_json_path(data: Any, path: str) -> tuple[bool, Any]:
    """
    Safely resolves dot/bracket-notation paths in nested dictionaries and lists.
    Examples:
      'user.id' -> data['user']['id']
      'items[0].title' or 'items.0.title' -> data['items'][0]['title']
    Returns:
      (found: bool, value: Any)
    """
    if data is None or not path:
        return False, None

    # Normalize tokens: replace [0] with .0
    normalized_path = re.sub(r'\[(\d+)\]', r'.\1', path.strip())
    tokens = [t.strip() for t in normalized_path.split('.') if t.strip()]

    current = data
    for token in tokens:
        if isinstance(current, dict):
            if token in current:
                current = current[token]
            else:
                return False, None
        elif isinstance(current, list):
            try:
                idx = int(token)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return False, None
            except ValueError:
                return False, None
        else:
            return False, None

    return True, current


def parse_typed_value(expected_str: str) -> Any:
    """
    Attempts to parse expected string representation into JSON types (int, float, bool, None, str).
    """
    if expected_str is None:
        return None
    cleaned = expected_str.strip()
    if cleaned.lower() == 'true':
        return True
    if cleaned.lower() == 'false':
        return False
    if cleaned.lower() in ('null', 'none'):
        return None
    # Try integer
    try:
        return int(cleaned)
    except ValueError:
        pass
    # Try float
    try:
        return float(cleaned)
    except ValueError:
        pass
    # Try JSON array/object if quoted
    if (cleaned.startswith('{') and cleaned.endswith('}')) or (cleaned.startswith('[') and cleaned.endswith(']')):
        try:
            return json.loads(cleaned)
        except Exception:
            pass
    return cleaned


class AssertionResult:
    """Detailed outcome of an assertion evaluation."""
    def __init__(
        self,
        assertion_type: str,
        passed: bool,
        expected_value: str,
        actual_value: str,
        target_property: str = "",
        message: str = "",
    ):
        self.assertion_type = assertion_type
        self.passed = passed
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.target_property = target_property
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            'assertion_type': self.assertion_type,
            'passed': self.passed,
            'expected_value': self.expected_value,
            'actual_value': self.actual_value,
            'target_property': self.target_property,
            'message': self.message,
        }


def evaluate_assertion(
    assertion_type: str,
    target_property: str,
    expected_value: str,
    response: OutboundResponse
) -> AssertionResult:
    """
    Evaluates a single assertion rule against an OutboundResponse.
    No arbitrary code execution (no eval, exec, or ast.literal_eval of untrusted code).
    """
    target = (target_property or '').strip()
    expected = (expected_value or '').strip()

    # If the response had a top-level error (e.g. timeout, connection error)
    if response.error and assertion_type != ASSERTION_BODY_CONTAINS:
        return AssertionResult(
            assertion_type=assertion_type,
            passed=False,
            expected_value=expected,
            actual_value=f"Execution Failed: {response.error}",
            target_property=target,
            message=f"Request failed before assertions could be met: {response.error}"
        )

    # 1. STATUS_CODE_EQUALS
    if assertion_type == ASSERTION_STATUS_EQUALS:
        try:
            exp_code = int(expected)
        except ValueError:
            return AssertionResult(
                assertion_type, False, expected, str(response.status_code), target,
                f"Configured expected status '{expected}' is not a valid integer."
            )
        passed = (response.status_code == exp_code)
        msg = f"Status code matched {exp_code}" if passed else f"Expected status {exp_code}, received {response.status_code}"
        return AssertionResult(assertion_type, passed, str(exp_code), str(response.status_code), target, msg)

    # 2. STATUS_CODE_IN
    if assertion_type == ASSERTION_STATUS_IN:
        candidates = []
        for part in expected.replace(',', ' ').split():
            try:
                candidates.append(int(part))
            except ValueError:
                pass
        passed = (response.status_code in candidates)
        msg = f"Status {response.status_code} is in allowed list" if passed else f"Status {response.status_code} not in {candidates}"
        return AssertionResult(assertion_type, passed, str(candidates), str(response.status_code), target, msg)

    # 3. MAX_LATENCY_MS
    if assertion_type == ASSERTION_MAX_LATENCY_MS:
        try:
            max_ms = float(expected)
        except ValueError:
            return AssertionResult(
                assertion_type, False, expected, f"{response.elapsed_ms}ms", target,
                f"Configured max latency '{expected}' is not a valid number."
            )
        passed = (response.elapsed_ms <= max_ms)
        msg = f"Response time {response.elapsed_ms:.1f}ms <= {max_ms:.1f}ms threshold" if passed else f"Response time {response.elapsed_ms:.1f}ms exceeded {max_ms:.1f}ms"
        return AssertionResult(assertion_type, passed, f"<={max_ms}ms", f"{response.elapsed_ms:.1f}ms", target, msg)

    # 4. CONTENT_TYPE_CONTAINS
    if assertion_type == ASSERTION_CONTENT_TYPE_CONTAINS:
        actual_ct = response.content_type or ""
        passed = (expected.lower() in actual_ct.lower())
        msg = f"Content-Type contains '{expected}'" if passed else f"Expected Content-Type to contain '{expected}', got '{actual_ct}'"
        return AssertionResult(assertion_type, passed, expected, actual_ct, target, msg)

    # 5. JSON_PROP_EXISTS
    if assertion_type == ASSERTION_JSON_PROP_EXISTS:
        if not response.is_json or response.parsed_json is None:
            return AssertionResult(
                assertion_type, False, f"Key '{target}' exists", "Response is not JSON", target,
                "Cannot check JSON property: response is not valid JSON."
            )
        found, val = extract_json_path(response.parsed_json, target)
        msg = f"JSON property '{target}' exists" if found else f"Property '{target}' not found in JSON response"
        return AssertionResult(
            assertion_type, found, f"Property '{target}' exists",
            f"Found: {repr(val)[:60]}" if found else "Missing", target, msg
        )

    # 6. JSON_VALUE_EQUALS
    if assertion_type == ASSERTION_JSON_VALUE_EQUALS:
        if not response.is_json or response.parsed_json is None:
            return AssertionResult(
                assertion_type, False, expected, "Response is not JSON", target,
                "Cannot check JSON value: response is not valid JSON."
            )
        found, actual_val = extract_json_path(response.parsed_json, target)
        if not found:
            return AssertionResult(
                assertion_type, False, expected, f"Property '{target}' not found", target,
                f"Target property '{target}' does not exist in response JSON."
            )
        typed_expected = parse_typed_value(expected)
        # Compare either as typed or string
        passed = (actual_val == typed_expected) or (str(actual_val) == expected)
        msg = f"Property '{target}' equals expected value" if passed else f"Expected '{target}' to be {typed_expected!r}, got {actual_val!r}"
        return AssertionResult(assertion_type, passed, str(typed_expected), str(actual_val), target, msg)

    # 7. JSON_VALUE_TYPE
    if assertion_type == ASSERTION_JSON_VALUE_TYPE:
        if not response.is_json or response.parsed_json is None:
            return AssertionResult(
                assertion_type, False, expected, "Response is not JSON", target,
                "Cannot check JSON type: response is not valid JSON."
            )
        found, actual_val = extract_json_path(response.parsed_json, target)
        if not found:
            return AssertionResult(
                assertion_type, False, expected, f"Property '{target}' not found", target,
                f"Target property '{target}' does not exist."
            )
        
        type_mapping = {
            'string': str,
            'str': str,
            'number': (int, float),
            'int': int,
            'integer': int,
            'float': float,
            'boolean': bool,
            'bool': bool,
            'array': list,
            'list': list,
            'object': dict,
            'dict': dict,
            'null': type(None),
        }
        target_type = type_mapping.get(expected.lower())
        if target_type is None:
            return AssertionResult(
                assertion_type, False, expected, type(actual_val).__name__, target,
                f"Unknown expected type '{expected}'."
            )
        passed = isinstance(actual_val, target_type)
        actual_type_name = type(actual_val).__name__
        msg = f"Property '{target}' is type '{actual_type_name}'" if passed else f"Expected type '{expected}', got '{actual_type_name}'"
        return AssertionResult(assertion_type, passed, expected, actual_type_name, target, msg)

    # 8. BODY_CONTAINS
    if assertion_type == ASSERTION_BODY_CONTAINS:
        passed = (expected in (response.body or ''))
        msg = f"Body contains '{expected}'" if passed else f"Substring '{expected}' not found in response body"
        return AssertionResult(assertion_type, passed, expected, "Substring present" if passed else "Substring absent", target, msg)

    # 9. BODY_REGEX
    if assertion_type == ASSERTION_BODY_REGEX:
        try:
            pattern = re.compile(expected)
            match = pattern.search(response.body or '')
            passed = (match is not None)
            msg = f"Body matches regex pattern '{expected}'" if passed else f"Regex '{expected}' found no matches"
            actual = match.group(0)[:60] if match else "No match"
            return AssertionResult(assertion_type, passed, expected, actual, target, msg)
        except re.error as re_err:
            return AssertionResult(assertion_type, False, expected, f"Invalid regex: {re_err}", target, f"Regex syntax error: {re_err}")

    # 10. HEADER_EXISTS
    if assertion_type == ASSERTION_HEADER_EXISTS:
        normalized_headers = {k.lower(): v for k, v in response.headers.items()}
        passed = (target.lower() in normalized_headers)
        msg = f"Header '{target}' exists" if passed else f"Header '{target}' missing from response"
        return AssertionResult(assertion_type, passed, f"Header '{target}' exists", "Present" if passed else "Missing", target, msg)

    # 11. HEADER_EQUALS
    if assertion_type == ASSERTION_HEADER_EQUALS:
        normalized_headers = {k.lower(): v for k, v in response.headers.items()}
        actual_header_val = normalized_headers.get(target.lower())
        passed = (actual_header_val == expected)
        msg = f"Header '{target}' matched expected value" if passed else f"Header '{target}' expected '{expected}', got '{actual_header_val}'"
        return AssertionResult(assertion_type, passed, expected, str(actual_header_val), target, msg)

    return AssertionResult(assertion_type, False, expected, "Unknown rule", target, f"Unsupported assertion type: {assertion_type}")
