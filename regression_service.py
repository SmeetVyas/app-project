"""
Regression Testing & Performance Comparison Service for API Sentinel.

Compares two Test Runs (Baseline vs Comparison) to identify:
1. Newly failing tests (Functional Regressions)
2. Resolved tests (Fixes / Improvements)
3. Significant latency spikes (Performance Regressions)
4. Overall suite health delta.
"""

from typing import Any
from testing_engine.models import TestRun


def compare_test_runs(
    baseline_run: TestRun,
    comparison_run: TestRun,
    latency_threshold_percent: float = 25.0,
    min_latency_diff_ms: float = 50.0,
) -> dict[str, Any]:
    """
    Compares two test runs and flags functional and performance regressions.
    """
    baseline_results = {r.name: r for r in baseline_run.results.all()}
    comparison_results = {r.name: r for r in comparison_run.results.all()}

    all_test_names = sorted(list(set(baseline_results.keys()) | set(comparison_results.keys())))

    diffs = []
    functional_regressions = []
    functional_fixes = []
    performance_regressions = []
    performance_improvements = []

    for name in all_test_names:
        base_res = baseline_results.get(name)
        comp_res = comparison_results.get(name)

        if not base_res:
            diffs.append({
                'name': name,
                'status': 'NEW_TEST',
                'description': 'Added in comparison run',
                'baseline_passed': None,
                'comparison_passed': comp_res.passed,
                'baseline_latency': None,
                'comparison_latency': comp_res.elapsed_ms,
                'latency_diff_ms': None,
                'latency_change_pct': None,
                'comp_error': comp_res.error_message,
            })
            continue

        if not comp_res:
            diffs.append({
                'name': name,
                'status': 'REMOVED_TEST',
                'description': 'Removed from comparison run',
                'baseline_passed': base_res.passed,
                'comparison_passed': None,
                'baseline_latency': base_res.elapsed_ms,
                'comparison_latency': None,
                'latency_diff_ms': None,
                'latency_change_pct': None,
                'comp_error': None,
            })
            continue

        # Both runs have this test
        base_passed = base_res.passed
        comp_passed = comp_res.passed
        base_lat = base_res.elapsed_ms
        comp_lat = comp_res.elapsed_ms
        lat_diff = round(comp_lat - base_lat, 2)
        lat_pct = round(((comp_lat - base_lat) / base_lat * 100), 1) if base_lat > 0 else 0.0

        # Outcome evaluation
        if base_passed and not comp_passed:
            status = 'FUNCTIONAL_REGRESSION'
            functional_regressions.append(name)
            desc = f"Regressed: Previously passed, now failing ({comp_res.error_message or 'Assertion failed'})"
        elif not base_passed and comp_passed:
            status = 'FUNCTIONAL_FIX'
            functional_fixes.append(name)
            desc = "Fixed: Previously failed, now passing!"
        elif not base_passed and not comp_passed:
            status = 'PERSISTENT_FAILURE'
            desc = "Still failing across both runs"
        else:
            status = 'CONSISTENT_PASS'
            desc = "Passed in both runs"

        # Check performance regression
        is_perf_regression = False
        is_perf_improvement = False
        if lat_diff > min_latency_diff_ms and lat_pct >= latency_threshold_percent:
            is_perf_regression = True
            performance_regressions.append({
                'name': name,
                'increase_ms': lat_diff,
                'increase_pct': lat_pct,
            })
        elif lat_diff < -min_latency_diff_ms and lat_pct <= -latency_threshold_percent:
            is_perf_improvement = True
            performance_improvements.append({
                'name': name,
                'decrease_ms': abs(lat_diff),
                'decrease_pct': abs(lat_pct),
            })

        diffs.append({
            'name': name,
            'status': status,
            'description': desc,
            'baseline_passed': base_passed,
            'comparison_passed': comp_passed,
            'baseline_latency': base_lat,
            'comparison_latency': comp_lat,
            'latency_diff_ms': lat_diff,
            'latency_change_pct': lat_pct,
            'is_perf_regression': is_perf_regression,
            'is_perf_improvement': is_perf_improvement,
            'comp_error': comp_res.error_message,
        })

    # Aggregated run metrics
    base_duration = baseline_run.total_duration_ms
    comp_duration = comparison_run.total_duration_ms
    duration_delta_ms = round(comp_duration - base_duration, 2)
    duration_delta_pct = round(((comp_duration - base_duration) / base_duration * 100), 1) if base_duration > 0 else 0.0

    pass_rate_delta = round(comparison_run.pass_percentage - baseline_run.pass_percentage, 1)

    return {
        'baseline_run': baseline_run,
        'comparison_run': comparison_run,
        'diffs': diffs,
        'functional_regressions': functional_regressions,
        'functional_fixes': functional_fixes,
        'performance_regressions': performance_regressions,
        'performance_improvements': performance_improvements,
        'duration_delta_ms': duration_delta_ms,
        'duration_delta_pct': duration_delta_pct,
        'pass_rate_delta': pass_rate_delta,
        'has_regressions': bool(functional_regressions or performance_regressions),
    }
