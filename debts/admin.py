from django.contrib import admin
from .models import Debt, EMIPayment


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ['loan_name', 'owner', 'loan_type', 'principal_amount', 'emi_amount', 'status', 'next_emi_date']
    list_filter = ['status', 'loan_type']
    search_fields = ['loan_name', 'lender_name', 'account_number']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('owner', 'loan_name', 'loan_type', 'status')
        }),
        ('Loan Details', {
            'fields': ('principal_amount', 'interest_rate', 'loan_term_months', 'emi_amount')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'next_emi_date')
        }),
        ('Additional Info', {
            'fields': ('lender_name', 'account_number', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EMIPayment)
class EMIPaymentAdmin(admin.ModelAdmin):
    list_display = ['debt', 'due_date', 'amount', 'is_paid', 'paid_date']
    list_filter = ['is_paid', 'due_date']
    search_fields = ['debt__loan_name']
    date_hierarchy = 'due_date'
