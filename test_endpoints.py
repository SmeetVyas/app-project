"""
Tests for Endpoint management, credential protection, and duplication.
"""

import pytest
from endpoints.models import Endpoint, SecureCredential
from endpoints.forms import EndpointForm


@pytest.mark.django_db
class TestEndpoints:
    def test_endpoint_with_credentials(self, sample_project):
        ep = Endpoint.objects.create(
            project=sample_project,
            name="Protected Route",
            url="https://api.example.com/secure",
            method="GET",
        )
        cred = SecureCredential.objects.create(
            endpoint=ep,
            credential_type='BEARER_TOKEN',
            header_name='Authorization'
        )
        cred.set_secret("super_secret_token_12345")
        cred.save()

        # Decrypted retrieval
        assert cred.get_decrypted_secret() == "super_secret_token_12345"
        assert "super_secret_token_12345" not in cred.encrypted_value
        assert "••••" in cred.masked_preview

        # get_headers() includes bearer token
        headers = ep.get_headers()
        assert headers['Authorization'] == "Bearer super_secret_token_12345"

    def test_form_rejects_ssrf_url(self, test_user, sample_project):
        form = EndpointForm(data={
            'project': sample_project.id,
            'name': 'SSRF Target',
            'url': 'http://169.254.169.254/latest/meta-data/',
            'method': 'GET',
            'expected_status_code': 200,
            'timeout_seconds': 10,
        }, user=test_user)

        assert not form.is_valid()
        assert 'url' in form.errors
        assert 'SSRF' in form.errors['url'][0] or 'prohibited' in form.errors['url'][0].lower()

    def test_duplicate_endpoint(self, client, test_user, sample_endpoint):
        client.force_login(test_user)
        resp = client.post(f'/endpoints/{sample_endpoint.id}/duplicate/')
        assert resp.status_code == 302

        copies = Endpoint.objects.filter(name=f"{sample_endpoint.name} (Copy)")
        assert copies.exists()
        copy = copies.first()
        assert copy.url == sample_endpoint.url
        assert copy.method == sample_endpoint.method
