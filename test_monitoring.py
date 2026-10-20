"""
Tests for Scheduled Monitoring and health check telemetry.
"""

from unittest.mock import patch
import pytest
from monitoring.models import MonitorSchedule, MonitorCheckLog
from services.http_client import OutboundResponse


@pytest.mark.django_db
class TestMonitoring:
    def test_uptime_percentage_calculation(self, sample_endpoint):
        sch = MonitorSchedule.objects.create(
            endpoint=sample_endpoint,
            interval_minutes=15,
            is_active=True,
        )

        # 3 healthy, 1 unhealthy checks
        MonitorCheckLog.objects.create(schedule=sch, status_code=200, elapsed_ms=100.0, is_healthy=True)
        MonitorCheckLog.objects.create(schedule=sch, status_code=200, elapsed_ms=110.0, is_healthy=True)
        MonitorCheckLog.objects.create(schedule=sch, status_code=200, elapsed_ms=95.0, is_healthy=True)
        MonitorCheckLog.objects.create(schedule=sch, status_code=500, elapsed_ms=500.0, is_healthy=False)

        assert sch.uptime_percentage == 75.0

    @patch('monitoring.views.execute_http_request')
    def test_manual_trigger_check(self, mock_http, client, test_user, sample_endpoint):
        client.force_login(test_user)
        sch = MonitorSchedule.objects.create(endpoint=sample_endpoint, is_active=True)

        mock_http.return_value = OutboundResponse(
            status_code=200,
            elapsed_ms=115.0,
        )

        resp = client.post(f'/monitoring/{sch.id}/trigger/')
        assert resp.status_code == 302

        sch.refresh_from_db()
        assert sch.last_checked_at is not None
        assert sch.logs.count() == 1
        assert sch.logs.first().is_healthy
