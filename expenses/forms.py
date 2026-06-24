from django import forms
from .models import Expense, ExpenseLimit, Category


class ExpenseForm(forms.ModelForm):
    """Form for creating and editing expenses."""
    
    # Category as ChoiceField to match the template's select dropdown
    category = forms.ChoiceField(
        choices=[('', 'Select a category')] + [
            ('Food & Dining', 'Food & Dining'),
            ('Transportation', 'Transportation'),
            ('Shopping', 'Shopping'),
            ('Entertainment', 'Entertainment'),
            ('Bills & Utilities', 'Bills & Utilities'),
            ('Healthcare', 'Healthcare'),
            ('Education', 'Education'),
            ('Travel', 'Travel'),
            ('Other', 'Other'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select w-100'
        })
    )
    
    class Meta:
        model = Expense
        fields = [
            'amount', 'date', 'description', 'category',
            'tags', 'receipt', 'is_recurring', 'recurring_frequency',
            'payment_method', 'notes','time'
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter expense description'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tags separated by commas'
            }),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'recurring_frequency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
            'receipt': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class'):
                continue
            field.widget.attrs['class'] = 'form-control'


class ExpenseLimitForm(forms.ModelForm):
    """Form for setting expense limits."""
    
    class Meta:
        model = ExpenseLimit
        fields = ['daily_expense_limit', 'monthly_expense_limit']
        widgets = {
            'daily_expense_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter daily expense limit',
                'min': '0'
            }),
            'monthly_expense_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter monthly expense limit',
                'min': '0'
            }),
        }


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories."""
    
    class Meta:
        model = Category
        fields = ['name', 'icon', 'color', 'budget_limit', 'is_global']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter icon class (e.g., fas fa-car)'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control'
            }),
            'budget_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter monthly budget limit',
                'min': '0',
                'step': '0.01'
            }),
            'is_global': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
