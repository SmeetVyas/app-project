"""
URL routes for Testing Engine: Suites, Test Cases, Runs, History, and Regressions.
"""

from django.urls import path
from testing_engine import views

urlpatterns = [
    path('suites/', views.suite_list_view, name='suite_list'),
    path('suites/new/', views.suite_create_view, name='suite_create'),
    path('suites/<int:pk>/', views.suite_detail_view, name='suite_detail'),
    path('suites/<int:pk>/edit/', views.suite_update_view, name='suite_update'),
    path('suites/<int:pk>/delete/', views.suite_delete_view, name='suite_delete'),
    path('suites/<int:pk>/run/', views.suite_run_view, name='suite_run'),
    
    path('suites/<int:suite_id>/cases/new/', views.testcase_create_view, name='testcase_create'),
    path('cases/<int:pk>/edit/', views.testcase_update_view, name='testcase_update'),
    path('cases/<int:pk>/delete/', views.testcase_delete_view, name='testcase_delete'),
    path('cases/<int:case_id>/assertions/new/', views.assertion_create_view, name='assertion_create'),
    path('assertions/<int:pk>/delete/', views.assertion_delete_view, name='assertion_delete'),

    path('runs/<int:pk>/', views.test_run_detail_view, name='test_run_detail'),
    path('runs/<int:pk>/rerun/', views.rerun_view, name='test_run_rerun'),
    path('history/', views.history_view, name='history'),
    path('compare/', views.regression_compare_view, name='regression_compare'),
]
