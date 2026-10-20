from django.contrib import admin
from testing_engine.models import TestSuite, TestCase, Assertion, TestRun, TestResult


class AssertionInline(admin.TabularInline):
    model = Assertion
    extra = 1


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'suite', 'endpoint', 'order', 'is_active')
    list_filter = ('suite', 'is_active')
    search_fields = ('name', 'endpoint__name')
    inlines = [AssertionInline]


@admin.register(TestSuite)
class TestSuiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at')
    list_filter = ('project',)
    search_fields = ('name', 'project__name')


class TestResultInline(admin.TabularInline):
    model = TestResult
    extra = 0
    readonly_fields = ('name', 'passed', 'status_code', 'elapsed_ms', 'error_message')


@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'suite', 'status', 'total_tests', 'passed_tests', 'failed_tests', 'total_duration_ms', 'started_at')
    list_filter = ('status', 'project')
    search_fields = ('suite__name', 'project__name')
    inlines = [TestResultInline]


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('name', 'test_run', 'passed', 'status_code', 'elapsed_ms', 'created_at')
    list_filter = ('passed', 'created_at')
