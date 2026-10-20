"""
Forms for Test Suites, Test Cases, and Assertions.
"""

import json
from django import forms
from core.models import Project
from endpoints.models import Endpoint
from testing_engine.models import TestSuite, TestCase, Assertion


class TestSuiteForm(forms.ModelForm):
    """Form to create or update a TestSuite."""
    class Meta:
        model = TestSuite
        fields = ['project', 'name', 'description']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Smoke Tests, Auth Flow Suite'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Purpose of this suite'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['project'].queryset = Project.objects.filter(owner=user)


class TestCaseForm(forms.ModelForm):
    """Form to define an individual test scenario."""
    custom_headers_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input font-mono',
            'rows': 2,
            'placeholder': '{\n  "X-Test-Id": "regression-42"\n}'
        }),
        help_text="Optional headers overriding the endpoint's defaults."
    )

    class Meta:
        model = TestCase
        fields = ['suite', 'endpoint', 'name', 'order', 'custom_body_override', 'is_active']
        widgets = {
            'suite': forms.Select(attrs={'class': 'form-select'}),
            'endpoint': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Verify 200 OK on valid credentials'}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'custom_body_override': forms.Textarea(attrs={
                'class': 'form-input font-mono',
                'rows': 3,
                'placeholder': 'Optional body payload override'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, user=None, suite=None, **kwargs):
        super().__init__(*args, **kwargs)
        if suite:
            self.fields['suite'].initial = suite
            self.fields['suite'].queryset = TestSuite.objects.filter(id=suite.id)
            self.fields['endpoint'].queryset = Endpoint.objects.filter(project=suite.project)
        elif user:
            self.fields['suite'].queryset = TestSuite.objects.filter(project__owner=user)
            self.fields['endpoint'].queryset = Endpoint.objects.filter(project__owner=user)

        if self.instance and self.instance.pk and self.instance.custom_headers_override:
            self.fields['custom_headers_text'].initial = json.dumps(self.instance.custom_headers_override, indent=2)

    def clean_custom_headers_text(self):
        text = self.cleaned_data.get('custom_headers_text', '').strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise forms.ValidationError("Headers must be a JSON object.")
            return parsed
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.custom_headers_override = self.cleaned_data.get('custom_headers_text', {})
        if commit:
            instance.save()
        return instance


class AssertionForm(forms.ModelForm):
    """Form to create or edit an Assertion rule."""
    class Meta:
        model = Assertion
        fields = ['assertion_type', 'target_property', 'expected_value', 'is_active']
        widgets = {
            'assertion_type': forms.Select(attrs={'class': 'form-select', 'id': 'assertion_type_select'}),
            'target_property': forms.TextInput(attrs={
                'class': 'form-input font-mono',
                'placeholder': 'e.g. data.status or Content-Type (leave blank for status code)',
                'id': 'target_property_input'
            }),
            'expected_value': forms.TextInput(attrs={
                'class': 'form-input font-mono',
                'placeholder': 'e.g. 200, 500, active, string, or regex',
                'id': 'expected_value_input'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
