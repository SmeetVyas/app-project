"""
Tests for Project ownership, isolation, and metrics calculation.
"""

import pytest
from core.models import Project


@pytest.mark.django_db
class TestProjects:
    def test_project_creation(self, test_user):
        project = Project.objects.create(
            owner=test_user,
            name="Search Service API",
            description="Algolia and Elasticsearch proxies"
        )
        assert project.slug == "search-service-api"
        assert project.owner == test_user

    def test_tenant_isolation(self, client, test_user, other_user, sample_project):
        # Client logged in as other_user
        client.force_login(other_user)

        # Attempt to access test_user's project detail
        resp = client.get(f'/projects/{sample_project.id}/')
        assert resp.status_code == 404

        # Attempt to edit test_user's project
        resp = client.post(f'/projects/{sample_project.id}/edit/', {'name': 'Hacked Name'})
        assert resp.status_code == 404

        # Verify unchanged
        sample_project.refresh_from_db()
        assert sample_project.name == "Payment Gateway API"

    def test_project_stats_calculation(self, sample_project, sample_endpoint, test_user):
        from testing_engine.models import TestRun
        
        # Initially empty stats
        stats = sample_project.get_stats()
        assert stats['endpoints_count'] == 1
        assert stats['total_runs'] == 0
        assert stats['pass_rate'] == 0.0

        # Create 1 passed run, 1 failed run
        TestRun.objects.create(project=sample_project, status='PASSED', total_duration_ms=100.0)
        TestRun.objects.create(project=sample_project, status='FAILED', total_duration_ms=200.0)

        stats = sample_project.get_stats()
        assert stats['total_runs'] == 2
        assert stats['passed_runs'] == 1
        assert stats['failed_runs'] == 1
        assert stats['pass_rate'] == 50.0
        assert stats['avg_latency'] == 150.0
