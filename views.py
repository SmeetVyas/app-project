"""
Views for Test Suites, Test Cases, Assertions, Test Runs, and Regression Analysis.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from core.models import Project
from testing_engine.models import TestSuite, TestCase, Assertion, TestRun, TestResult
from testing_engine.forms import TestSuiteForm, TestCaseForm, AssertionForm
from services.test_runner import execute_test_suite
from services.regression_service import compare_test_runs


@login_required
def suite_list_view(request):
    """Lists all Test Suites owned by the user, filterable by project."""
    user = request.user
    project_id = request.GET.get('project') or request.session.get('active_project_id')
    
    suites = TestSuite.objects.filter(project__owner=user).select_related('project')
    if project_id and project_id != 'all':
        suites = suites.filter(project_id=project_id)

    projects = Project.objects.filter(owner=user)
    return render(request, 'testing/suite_list.html', {
        'suites': suites,
        'projects': projects,
        'selected_project_id': project_id,
    })


@login_required
def suite_create_view(request):
    """Creates a new TestSuite."""
    user = request.user
    initial = {}
    project_id = request.GET.get('project') or request.session.get('active_project_id')
    if project_id:
        try:
            initial['project'] = Project.objects.get(id=project_id, owner=user)
        except Project.DoesNotExist:
            pass

    if request.method == 'POST':
        form = TestSuiteForm(request.POST, user=user)
        if form.is_valid():
            suite = form.save()
            messages.success(request, f"Test suite '{suite.name}' created.")
            return redirect('suite_detail', pk=suite.pk)
    else:
        form = TestSuiteForm(initial=initial, user=user)

    return render(request, 'testing/suite_form.html', {'form': form, 'title': 'Create Test Suite'})


@login_required
def suite_detail_view(request, pk):
    """Detailed view of a Test Suite with its Test Cases, Assertions, and execution history."""
    suite = get_object_or_404(TestSuite, pk=pk, project__owner=request.user)
    cases = suite.test_cases.prefetch_related('assertions', 'endpoint').all()
    runs = suite.runs.order_by('-started_at')[:10]

    return render(request, 'testing/suite_detail.html', {
        'suite': suite,
        'cases': cases,
        'runs': runs,
    })


@login_required
def suite_update_view(request, pk):
    """Updates a TestSuite."""
    suite = get_object_or_404(TestSuite, pk=pk, project__owner=request.user)
    if request.method == 'POST':
        form = TestSuiteForm(request.POST, instance=suite, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Test suite '{suite.name}' updated.")
            return redirect('suite_detail', pk=suite.pk)
    else:
        form = TestSuiteForm(instance=suite, user=request.user)

    return render(request, 'testing/suite_form.html', {'form': form, 'suite': suite, 'title': f'Edit {suite.name}'})


@login_required
def suite_delete_view(request, pk):
    """Deletes a TestSuite."""
    suite = get_object_or_404(TestSuite, pk=pk, project__owner=request.user)
    if request.method == 'POST':
        name = suite.name
        suite.delete()
        messages.success(request, f"Test suite '{name}' deleted.")
        return redirect('suite_list')
    return render(request, 'testing/suite_confirm_delete.html', {'suite': suite})


@login_required
def testcase_create_view(request, suite_id):
    """Creates a TestCase within a specific TestSuite."""
    suite = get_object_or_404(TestSuite, pk=suite_id, project__owner=request.user)
    
    if request.method == 'POST':
        form = TestCaseForm(request.POST, suite=suite)
        if form.is_valid():
            case = form.save(commit=False)
            case.suite = suite
            case.save()
            messages.success(request, f"Test case '{case.name}' added to suite.")
            return redirect('suite_detail', pk=suite.pk)
    else:
        form = TestCaseForm(suite=suite)

    return render(request, 'testing/testcase_form.html', {'form': form, 'suite': suite, 'title': 'Add Test Case'})


@login_required
def testcase_update_view(request, pk):
    """Updates an existing TestCase."""
    case = get_object_or_404(TestCase, pk=pk, suite__project__owner=request.user)
    suite = case.suite

    if request.method == 'POST':
        form = TestCaseForm(request.POST, instance=case, suite=suite)
        if form.is_valid():
            form.save()
            messages.success(request, f"Test case '{case.name}' updated.")
            return redirect('suite_detail', pk=suite.pk)
    else:
        form = TestCaseForm(instance=case, suite=suite)

    return render(request, 'testing/testcase_form.html', {'form': form, 'suite': suite, 'case': case, 'title': f'Edit {case.name}'})


@login_required
def testcase_delete_view(request, pk):
    """Deletes a TestCase."""
    case = get_object_or_404(TestCase, pk=pk, suite__project__owner=request.user)
    suite_id = case.suite_id
    if request.method == 'POST':
        name = case.name
        case.delete()
        messages.success(request, f"Test case '{name}' removed.")
        return redirect('suite_detail', pk=suite_id)
    return render(request, 'testing/testcase_confirm_delete.html', {'case': case})


@login_required
def assertion_create_view(request, case_id):
    """Adds an assertion rule to a TestCase."""
    case = get_object_or_404(TestCase, pk=case_id, suite__project__owner=request.user)
    if request.method == 'POST':
        form = AssertionForm(request.POST)
        if form.is_valid():
            assertion = form.save(commit=False)
            assertion.test_case = case
            assertion.save()
            messages.success(request, "Assertion rule added.")
            return redirect('suite_detail', pk=case.suite_id)
    else:
        form = AssertionForm()

    return render(request, 'testing/assertion_form.html', {'form': form, 'case': case, 'title': f'Add Assertion to {case.name}'})


@login_required
def assertion_delete_view(request, pk):
    """Removes an assertion rule."""
    assertion = get_object_or_404(Assertion, pk=pk, test_case__suite__project__owner=request.user)
    suite_id = assertion.test_case.suite_id
    if request.method == 'POST':
        assertion.delete()
        messages.success(request, "Assertion removed.")
        return redirect('suite_detail', pk=suite_id)
    return redirect('suite_detail', pk=suite_id)


@login_required
def suite_run_view(request, pk):
    """Executes a TestSuite synchronously and redirects to the Run Detail report."""
    suite = get_object_or_404(TestSuite, pk=pk, project__owner=request.user)
    test_run = execute_test_suite(suite, triggered_by=request.user)
    
    if test_run.status == 'PASSED':
        messages.success(request, f"Suite '{suite.name}' executed: All {test_run.passed_tests} tests passed!")
    else:
        messages.error(request, f"Suite '{suite.name}' executed with {test_run.failed_tests} failure(s).")

    return redirect('test_run_detail', pk=test_run.pk)


@login_required
def test_run_detail_view(request, pk):
    """Detailed result of a single TestRun with per-test assertion breakdown."""
    test_run = get_object_or_404(TestRun, pk=pk, project__owner=request.user)
    results = test_run.results.select_related('test_case', 'endpoint').all()

    # Find previous run of the same suite to offer 1-click regression comparison
    previous_run = None
    if test_run.suite:
        previous_run = (
            TestRun.objects.filter(suite=test_run.suite, started_at__lt=test_run.started_at)
            .order_by('-started_at')
            .first()
        )

    return render(request, 'testing/run_detail.html', {
        'test_run': test_run,
        'results': results,
        'previous_run': previous_run,
    })


@login_required
def history_view(request):
    """Global Test Run History with filters for project, suite, status, and outcome."""
    user = request.user
    project_id = request.GET.get('project') or request.session.get('active_project_id')
    suite_id = request.GET.get('suite')
    status_filter = request.GET.get('status')

    runs = TestRun.objects.filter(project__owner=user).select_related('project', 'suite', 'triggered_by')

    if project_id and project_id != 'all':
        runs = runs.filter(project_id=project_id)

    if suite_id and suite_id != 'all':
        runs = runs.filter(suite_id=suite_id)

    if status_filter:
        runs = runs.filter(status=status_filter.upper())

    projects = Project.objects.filter(owner=user)
    suites = TestSuite.objects.filter(project__owner=user)

    return render(request, 'testing/history.html', {
        'runs': runs.order_by('-started_at'),
        'projects': projects,
        'suites': suites,
        'selected_project_id': project_id,
        'selected_suite_id': suite_id,
        'selected_status': status_filter,
    })


@login_required
def rerun_view(request, pk):
    """Reruns a saved TestRun."""
    original_run = get_object_or_404(TestRun, pk=pk, project__owner=request.user)
    if original_run.suite:
        new_run = execute_test_suite(original_run.suite, triggered_by=request.user)
        messages.info(request, f"Reran suite '{original_run.suite.name}'.")
        return redirect('test_run_detail', pk=new_run.pk)
    else:
        messages.warning(request, "This run was an ad-hoc direct test. Please trigger it directly from the endpoint.")
        return redirect('history')


@login_required
def regression_compare_view(request):
    """
    Compares two test runs (Baseline vs Comparison) to identify regressions.
    """
    user = request.user
    base_id = request.GET.get('base')
    comp_id = request.GET.get('comp')

    runs = TestRun.objects.filter(project__owner=user).select_related('project', 'suite').order_by('-started_at')

    comparison_data = None
    baseline_run = None
    comparison_run = None

    if base_id and comp_id:
        baseline_run = get_object_or_404(TestRun, pk=base_id, project__owner=user)
        comparison_run = get_object_or_404(TestRun, pk=comp_id, project__owner=user)
        comparison_data = compare_test_runs(baseline_run, comparison_run)

    return render(request, 'testing/regression_compare.html', {
        'runs': runs,
        'base_id': base_id,
        'comp_id': comp_id,
        'baseline_run': baseline_run,
        'comparison_run': comparison_run,
        'comparison_data': comparison_data,
    })
