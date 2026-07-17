import json
from django import forms
from apps.core.models import AgentRegistry
from apps.core.input_output_types import APPROVED_INPUT_TYPES, APPROVED_OUTPUT_TYPES


class AgentRegistrationForm(forms.ModelForm):
    input_type = forms.ChoiceField(
        choices=[(t, t) for t in APPROVED_INPUT_TYPES],
        initial='text_with_units',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    output_types = forms.MultipleChoiceField(
        choices=[(t, t) for t in APPROVED_OUTPUT_TYPES],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'})
    )
    subject_areas = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Mathematics, Algebra', 'class': 'form-input'}),
        help_text="Comma-separated list of subject areas."
    )
    age_groups = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 9-12, 13-15', 'class': 'form-input'}),
        help_text="Comma-separated list of age groups."
    )
    capabilities = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. real-time feedback, interactive', 'class': 'form-input'}),
        help_text="Comma-separated list of capabilities."
    )

    class Meta:
        model = AgentRegistry
        fields = ['name', 'input_type', 'output_types', 'subject_areas', 'age_groups', 'capabilities']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. MathMentor AI', 'class': 'form-input'}),
        }

    def clean_comma_separated(self, field_name):
        data = self.cleaned_data.get(field_name, '')
        if not data:
            return []
        return [item.strip() for item in data.split(',') if item.strip()]

    def clean_subject_areas(self):
        return self.clean_comma_separated('subject_areas')

    def clean_age_groups(self):
        return self.clean_comma_separated('age_groups')

    def clean_capabilities(self):
        return self.clean_comma_separated('capabilities')
