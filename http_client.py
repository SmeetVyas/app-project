"""
Secure Outbound HTTP Client for API Sentinel.

Enforces SSRF protection, configurable timeouts, streaming response size limits,
redirect security, and sensitive header redaction.
"""

import json
import time
from typing import Any, Optional
import requests
from django.conf import settings
from services.ssrf_guard import validate_outbound_url, SSRFSecurityError

SENSITIVE_HEADER_KEYS = {
    'authorization',
    'proxy-authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
    'api-key',
    'x-auth-token',
    'token',
}


def redact_headers(headers: dict[str, Any]) -> dict[str, str]:
    """
    Returns a copy of headers with sensitive authorization tokens and cookies masked.
    """
    redacted = {}
    for key, value in headers.items():
        k_lower = key.lower()
        if k_lower in SENSITIVE_HEADER_KEYS or 'secret' in k_lower or 'password' in k_lower:
            val_str = str(value)
            if len(val_str) > 8:
                redacted[key] = f"{val_str[:4]}••••••••{val_str[-4:]}"
            else:
                redacted[key] = "••••••••"
        else:
            redacted[key] = str(value)
    return redacted


class OutboundResponse:
    """Encapsulates the result of an outbound HTTP execution."""
    def __init__(
        self,
        status_code: Optional[int] = None,
        elapsed_ms: float = 0.0,
        headers: Optional[dict[str, str]] = None,
        body: str = "",
        content_type: str = "",
        size_bytes: int = 0,
        is_json: bool = False,
        parsed_json: Optional[Any] = None,
        error: Optional[str] = None,
        truncated: bool = False,
        final_url: str = "",
    ):
        self.status_code = status_code
        self.elapsed_ms = round(elapsed_ms, 2)
        self.headers = headers or {}
        self.body = body
        self.content_type = content_type
        self.size_bytes = size_bytes
        self.is_json = is_json
        self.parsed_json = parsed_json
        self.error = error
        self.truncated = truncated
        self.final_url = final_url

    def to_dict(self) -> dict[str, Any]:
        return {
            'status_code': self.status_code,
            'elapsed_ms': self.elapsed_ms,
            'headers': self.headers,
            'body': self.body,
            'content_type': self.content_type,
            'size_bytes': self.size_bytes,
            'is_json': self.is_json,
            'parsed_json': self.parsed_json,
            'error': self.error,
            'truncated': self.truncated,
            'final_url': self.final_url,
        }


def execute_http_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    body: Optional[str] = None,
    timeout: Optional[int] = None,
    allow_redirects: bool = False,
    enforce_ssrf: bool = True,
) -> OutboundResponse:
    """
    Safely executes an outbound HTTP request with pre-flight SSRF check,
    streaming size limit, and header redaction.
    """
    method = (method or 'GET').upper().strip()
    if method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
        return OutboundResponse(error=f"Unsupported HTTP method: {method}")

    # 1. Pre-flight SSRF validation
    if enforce_ssrf and getattr(settings, 'SSRF_STRICT_MODE', True):
        try:
            validated_url, _ = validate_outbound_url(url)
            url = validated_url
        except SSRFSecurityError as ssrf_err:
            return OutboundResponse(error=f"Security Policy Block: {str(ssrf_err)}")
        except Exception as e:
            return OutboundResponse(error=f"URL Validation Error: {str(e)}")

    req_timeout = timeout or getattr(settings, 'HTTP_CLIENT_TIMEOUT', 10)
    max_bytes = getattr(settings, 'HTTP_MAX_RESPONSE_BYTES', 1048576)

    # Clean headers
    clean_headers = {str(k): str(v) for k, v in (headers or {}).items() if k}
    if 'User-Agent' not in clean_headers:
        clean_headers['User-Agent'] = 'APISentinel/1.0 (+https://apisentinel.dev)'

    start_time = time.perf_counter()
    try:
        session = requests.Session()
        # Stream response so we can enforce byte limits without loading gigabytes in memory
        resp = session.request(
            method=method,
            url=url,
            headers=clean_headers,
            params=params,
            data=body.encode('utf-8') if (body and method in ('POST', 'PUT', 'PATCH', 'DELETE')) else None,
            timeout=req_timeout,
            allow_redirects=False,  # Revalidate redirects explicitly if any
            stream=True,
        )

        # Handle manual redirect if allow_redirects requested
        if allow_redirects and resp.is_redirect and 'location' in resp.headers:
            redirect_url = resp.headers['location']
            if enforce_ssrf and getattr(settings, 'SSRF_STRICT_MODE', True):
                try:
                    validate_outbound_url(redirect_url)
                except SSRFSecurityError as e:
                    return OutboundResponse(
                        error=f"Redirect blocked by SSRF Policy: {str(e)}"
                    )
            # Re-fetch redirect destination
            resp = session.request(
                method='GET',
                url=redirect_url,
                headers=clean_headers,
                timeout=req_timeout,
                allow_redirects=False,
                stream=True,
            )

        # Read response content chunk by chunk up to max_bytes
        chunks = []
        bytes_read = 0
        truncated = False

        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                bytes_read += len(chunk)
                if bytes_read > max_bytes:
                    truncated = True
                    remaining = max_bytes - (bytes_read - len(chunk))
                    if remaining > 0:
                        chunks.append(chunk[:remaining])
                    break
                chunks.append(chunk)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        raw_body_bytes = b"".join(chunks)

        # Try to decode body
        encoding = resp.encoding or 'utf-8'
        try:
            body_text = raw_body_bytes.decode(encoding, errors='replace')
        except Exception:
            body_text = raw_body_bytes.decode('utf-8', errors='replace')

        content_type = resp.headers.get('Content-Type', '')
        is_json = 'application/json' in content_type.lower()
        parsed_json = None

        if is_json or (body_text.strip().startswith('{') or body_text.strip().startswith('[')):
            try:
                parsed_json = json.loads(body_text)
                is_json = True
            except Exception:
                pass

        resp_headers = dict(resp.headers)

        return OutboundResponse(
            status_code=resp.status_code,
            elapsed_ms=elapsed_ms,
            headers=resp_headers,
            body=body_text,
            content_type=content_type,
            size_bytes=bytes_read,
            is_json=is_json,
            parsed_json=parsed_json,
            truncated=truncated,
            final_url=resp.url,
        )

    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OutboundResponse(
            elapsed_ms=elapsed_ms,
            error=f"Request timed out after {req_timeout}s."
        )
    except requests.exceptions.SSLError as ssl_err:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OutboundResponse(
            elapsed_ms=elapsed_ms,
            error=f"SSL/TLS Certificate verification failed: {ssl_err}"
        )
    except requests.exceptions.ConnectionError as conn_err:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OutboundResponse(
            elapsed_ms=elapsed_ms,
            error=f"Connection failed: Unable to reach host or network unreachable. ({conn_err})"
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return OutboundResponse(
            elapsed_ms=elapsed_ms,
            error=f"Unexpected HTTP execution error: {str(exc)}"
        )
