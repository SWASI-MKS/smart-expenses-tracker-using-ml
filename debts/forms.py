from django import forms
from .models import Debt, EMIPayment


class DebtForm(forms.ModelForm):
    """Form for creating and editing debt records."""
    
    class Meta:
        model = Debt
        fields = [
            'loan_name', 'loan_type', 'principal_amount', 'interest_rate',
            'loan_term_months', 'start_date', 'lender_name', 'account_number', 'notes'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        principal = cleaned_data.get('principal_amount')
        interest_rate = cleaned_data.get('interest_rate')
        loan_term = cleaned_data.get('loan_term_months')
        
        if principal and interest_rate and loan_term:
            # Calculate and set EMI
            from decimal import Decimal
            import math
            
            P = float(principal)
            r = float(interest_rate) / 100 / 12
            n = loan_term
            
            if r > 0:
                emi = P * r * (math.pow(1 + r, n)) / (math.pow(1 + r, n) - 1)
            else:
                emi = P / n
            
            # Store calculated EMI in cleaned_data for the view to use
            cleaned_data['calculated_emi'] = round(emi, 2)
        
        return cleaned_data


class EMIPaymentForm(forms.ModelForm):
    """Form for recording EMI payments."""
    
    class Meta:
        model = EMIPayment
        fields = ['due_date', 'amount', 'is_paid', 'paid_date', 'notes']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'paid_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
