"""
Unit tests for SSRF Guard and IP address validation.
"""

import pytest
from services.ssrf_guard import is_ip_allowed, validate_outbound_url, SSRFSecurityError


class TestSSRFGuard:
    def test_blocks_loopback_ipv4(self):
        allowed, reason = is_ip_allowed("127.0.0.1")
        assert not allowed
        assert "Loopback" in reason

    def test_blocks_loopback_alias(self):
        allowed, reason = is_ip_allowed("127.0.1.1")
        assert not allowed

    def test_blocks_private_class_a(self):
        allowed, reason = is_ip_allowed("10.0.5.21")
        assert not allowed
        assert "Private" in reason

    def test_blocks_private_class_b(self):
        allowed, reason = is_ip_allowed("172.16.0.1")
        assert not allowed

    def test_blocks_private_class_c(self):
        allowed, reason = is_ip_allowed("192.168.1.100")
        assert not allowed

    def test_blocks_aws_gcp_cloud_metadata(self):
        allowed, reason = is_ip_allowed("169.254.169.254")
        assert not allowed
        assert "metadata" in reason.lower()

    def test_blocks_alibaba_cloud_metadata(self):
        allowed, reason = is_ip_allowed("100.100.100.200")
        assert not allowed

    def test_blocks_ipv6_loopback(self):
        allowed, reason = is_ip_allowed("::1")
        assert not allowed

    def test_allows_public_ip(self):
        allowed, reason = is_ip_allowed("8.8.8.8")
        assert allowed
        assert "allowed" in reason.lower()

    def test_validate_outbound_url_rejects_file_scheme(self):
        with pytest.raises(SSRFSecurityError) as exc_info:
            validate_outbound_url("file:///etc/passwd")
        assert "Only HTTP and HTTPS" in str(exc_info.value)

    def test_validate_outbound_url_rejects_ftp_scheme(self):
        with pytest.raises(SSRFSecurityError) as exc_info:
            validate_outbound_url("ftp://ftp.example.com/data")
        assert "Only HTTP and HTTPS" in str(exc_info.value)

    def test_validate_outbound_url_rejects_localhost_hostname(self):
        with pytest.raises(SSRFSecurityError) as exc_info:
            validate_outbound_url("http://localhost:8000/internal")
        assert "restricted internal or metadata" in str(exc_info.value)

    def test_validate_outbound_url_rejects_internal_domain_suffix(self):
        with pytest.raises(SSRFSecurityError) as exc_info:
            validate_outbound_url("http://database.corp/admin")
        assert "restricted internal suffix" in str(exc_info.value)

    def test_validate_outbound_url_rejects_metadata_host(self):
        with pytest.raises(SSRFSecurityError) as exc_info:
            validate_outbound_url("http://metadata.google.internal/computeMetadata/v1/")
        assert "restricted internal or metadata" in str(exc_info.value)

    def test_validate_outbound_url_rejects_direct_private_ip(self):
        with pytest.raises(SSRFSecurityError) as exc_info:
            validate_outbound_url("http://192.168.1.1/admin")
        assert "Private/Internal network address prohibited" in str(exc_info.value)
