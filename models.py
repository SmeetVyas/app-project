"""
Testing Engine Models for API Sentinel.

Models representing Test Suites, Test Cases, Assertions, Test Runs, and Individual Results.
"""

from django.db import models
from django.contrib.auth.models import User
from core.models import Project
from endpoints.models import Endpoint
from services.assertion_engine import ASSERTION_TYPE_CHOICES


class TestSuite(models.Model):
    """
    A collection of reusable test cases grouped for regression testing and continuous QA.
    """
    __test__ = False
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_suites')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['project', 'name']
        unique_together = ('project', 'name')

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    def get_latest_run(self):
        """Returns the most recent TestRun executed for this suite."""
        return self.runs.order_by('-started_at').first()

    def get_pass_rate(self):
        """Calculates suite pass rate based on historical runs."""
        runs = self.runs.all()
        total = runs.count()
        if total == 0:
            return 0.0
        passed = runs.filter(status='PASSED').count()
        return round((passed / total) * 100, 1)


class TestCase(models.Model):
    """
    A specific test scenario bound to an Endpoint with custom assertions.
    """
    __test__ = False
    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='test_cases')
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name='test_cases')
    name = models.CharField(max_length=150)
    order = models.PositiveIntegerField(default=0)
    custom_body_override = models.TextField(blank=True, default='', help_text="Overrides the endpoint's default body if provided")
    custom_headers_override = models.JSONField(default=dict, blank=True, help_text="Header overrides for this specific case")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['suite', 'order', 'id']

    def __str__(self):
        return f"{self.suite.name} -> {self.name}"


class Assertion(models.Model):
    """
    An assertion rule belonging to a TestCase.
    Evaluated by services.assertion_engine.
    """
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='assertions')
    assertion_type = models.CharField(max_length=40, choices=ASSERTION_TYPE_CHOICES)
    target_property = models.CharField(max_length=200, blank=True, default='', help_text="Dot-path or header key, e.g. 'data.user.id'")
    expected_value = models.TextField(help_text="Expected literal value, number, type name, or regex")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.get_assertion_type_display()} [{self.target_property} = {self.expected_value}]"


class TestRun(models.Model):
    """
    Execution instance of a TestSuite or an ad-hoc batch run.
    Stores aggregated outcome, timing, and environmental details.
    """
    __test__ = False
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('ERROR', 'Error'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_runs')
    suite = models.ForeignKey(TestSuite, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs')
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_tests = models.PositiveIntegerField(default=0)
    passed_tests = models.PositiveIntegerField(default=0)
    failed_tests = models.PositiveIntegerField(default=0)
    total_duration_ms = models.FloatField(default=0.0)
    environment_label = models.CharField(max_length=50, default='Production/Staging')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Run #{self.id} [{self.status}] - {self.project.name} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def pass_percentage(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return round((self.passed_tests / self.total_tests) * 100, 1)

    @property
    def is_successful(self) -> bool:
        return self.status == 'PASSED'


class TestResult(models.Model):
    """
    Detailed outcome of an individual TestCase within a TestRun.
    Contains complete response status, latency, headers, body snippet, and assertion comparisons.
    """
    __test__ = False
    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='results')
    test_case = models.ForeignKey(TestCase, on_delete=models.SET_NULL, null=True, blank=True)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=150)
    passed = models.BooleanField(default=False)
    status_code = models.IntegerField(null=True, blank=True)
    elapsed_ms = models.FloatField(default=0.0)
    response_headers = models.JSONField(default=dict, blank=True)
    response_body_preview = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    
    # List of assertion outcomes: [{"assertion_type": "...", "passed": true/false, ...}]
    assertion_details = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        outcome = "PASS" if self.passed else "FAIL"
        return f"[{outcome}] {self.name} ({self.elapsed_ms}ms)"
