from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Goal

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'start_date', 'end_date', 'amount_to_save']
    
    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        if end_date:
            if end_date <= timezone.now().date():
                raise ValidationError("End date must be in the future.")
        return end_date


class AddAmountForm(forms.Form):
    additional_amount = forms.DecimalField(
        label='Additional Amount to Save',
        min_value=0,
        max_value=9999999,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'class': 'form-control',
            'placeholder': 'Enter amount'
        })
    )


class ExtendDeadlineForm(forms.Form):
    """Form for extending goal deadline"""
    end_date = forms.DateField(
        label='New End Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        if end_date:
            today = timezone.now().date()
            if end_date <= today:
                raise ValidationError("New end date must be in the future.")
        return end_date
