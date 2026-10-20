"""
SSRF (Server-Side Request Forgery) Guard.

Provides rigorous URL validation and IP destination checks to prevent outbound requests
to internal networks, loopbacks, link-local addresses, and cloud provider metadata services.
"""

import ipaddress
import socket
from urllib.parse import urlsplit


class SSRFSecurityError(ValueError):
    """Raised when an outbound URL violates SSRF security policies."""
    pass


# Specific restricted hostnames that must always be blocked
RESTRICTED_HOSTNAMES = {
    'localhost',
    'metadata.google.internal',
    'metadata',
    'instance-data',
}

# Restricted domain suffixes
RESTRICTED_DOMAIN_SUFFIXES = (
    '.local',
    '.internal',
    '.lan',
    '.home',
    '.corp',
    '.intranet',
    '.localhost',
)

# Known Cloud Metadata IP addresses
CLOUD_METADATA_IPS = {
    '169.254.169.254', # AWS, GCP, Azure, OpenStack, DigitalOcean
    '100.100.100.200', # Alibaba Cloud
    '192.0.0.192',     # Oracle Cloud
}


def is_ip_allowed(ip_str: str) -> tuple[bool, str]:
    """
    Evaluates whether an IP address string is safe for outbound developer API testing.
    Rejects private, loopback, link-local, reserved, multicast, or cloud metadata IPs.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False, f"Invalid IP address format: {ip_str}"

    if str(ip) in CLOUD_METADATA_IPS:
        return False, f"Prohibited cloud metadata address: {ip_str}"

    if ip.is_loopback:
        return False, f"Loopback address prohibited: {ip_str}"

    if ip.is_private:
        return False, f"Private/Internal network address prohibited: {ip_str}"

    if ip.is_link_local:
        return False, f"Link-local address prohibited: {ip_str}"

    if ip.is_reserved:
        return False, f"Reserved network address prohibited: {ip_str}"

    if ip.is_multicast:
        return False, f"Multicast address prohibited: {ip_str}"

    if ip.is_unspecified:
        return False, f"Unspecified address prohibited: {ip_str}"

    return True, "IP address is allowed"


def validate_outbound_url(url: str, allow_custom_ports: bool = True) -> tuple[str, list[str]]:
    """
    Validates a candidate URL against SSRF rules.
    1. Checks URL scheme (only http and https allowed).
    2. Checks hostname for known local/internal aliases.
    3. Resolves DNS to all candidate IPv4/IPv6 addresses and verifies none are internal/private.
    
    Returns:
        tuple of (sanitized_url, resolved_ips)
    
    Raises:
        SSRFSecurityError if the URL violates security policies.
    """
    if not url or not isinstance(url, str):
        raise SSRFSecurityError("URL must be a non-empty string.")

    cleaned_url = url.strip()
    try:
        parsed = urlsplit(cleaned_url)
    except Exception as e:
        raise SSRFSecurityError(f"Malformed URL: {e}")

    scheme = (parsed.scheme or '').lower()
    if scheme not in ('http', 'https'):
        raise SSRFSecurityError(
            f"Invalid protocol '{scheme}'. Only HTTP and HTTPS endpoints are permitted."
        )

    hostname = (parsed.hostname or '').lower().strip('[]')
    if not hostname:
        raise SSRFSecurityError("URL must include a valid hostname.")

    # Check hostname against restricted lists
    if hostname in RESTRICTED_HOSTNAMES:
        raise SSRFSecurityError(f"Host '{hostname}' is a restricted internal or metadata destination.")

    for suffix in RESTRICTED_DOMAIN_SUFFIXES:
        if hostname.endswith(suffix):
            raise SSRFSecurityError(f"Host '{hostname}' ends with restricted internal suffix '{suffix}'.")

    # If the hostname is already an IP address literal, validate it directly
    try:
        ip = ipaddress.ip_address(hostname)
        allowed, reason = is_ip_allowed(str(ip))
        if not allowed:
            raise SSRFSecurityError(f"SSRF Protection: {reason}")
        return cleaned_url, [str(ip)]
    except ValueError:
        pass  # It's a standard domain name, proceed to DNS resolution

    # Resolve hostname via DNS and check every candidate IP address
    port = parsed.port or (443 if scheme == 'https' else 80)
    resolved_ips: list[str] = []

    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if ip_str not in resolved_ips:
                resolved_ips.append(ip_str)
    except socket.gaierror as e:
        raise SSRFSecurityError(f"DNS Resolution failed for host '{hostname}': {e}")
    except Exception as e:
        raise SSRFSecurityError(f"Network error resolving host '{hostname}': {e}")

    if not resolved_ips:
        raise SSRFSecurityError(f"DNS resolution produced no IP addresses for host '{hostname}'.")

    # Verify every resolved address
    for ip_str in resolved_ips:
        allowed, reason = is_ip_allowed(ip_str)
        if not allowed:
            raise SSRFSecurityError(
                f"SSRF Protection: Host '{hostname}' resolves to restricted IP {ip_str}. ({reason})"
            )

    return cleaned_url, resolved_ips
