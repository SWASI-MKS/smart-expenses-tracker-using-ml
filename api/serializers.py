
"""
DRF Serializers with Currency Support

These serializers automatically format amounts using the user's preferred currency.
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from expenses.models import Expense
from userincome.models import UserIncome
from userpreferences.models import UserPreference
from userpreferences.currency_service import CurrencyService


class CurrencyFormattingMixin:
    """
    Mixin that provides currency formatting for serializer fields.
    
    Usage:
        class MySerializer(CurrencyFormattingMixin, serializers.ModelSerializer):
            amount_formatted = serializers.SerializerMethodField()
            
            def get_amount_formatted(self, obj):
                return self.format_currency(obj.amount, self.context.get('request'))
    """
    
    def format_currency(self, amount, request):
        """Format amount with user's currency."""
        if not request or not hasattr(request, 'user'):
            return f"${amount:,.2f}"
        
        user = request.user
        if not user.is_authenticated:
            return f"${amount:,.2f}"
        
        try:
            return CurrencyService.format_amount(amount, user)
        except Exception:
            return f"${amount:,.2f}"
    
    def get_currency_info(self, request):
        """Get user's currency info."""
        if not request or not hasattr(request, 'user'):
            return {'code': 'USD', 'symbol': '$', 'name': 'US Dollar'}
        
        user = request.user
        if not user.is_authenticated:
            return {'code': 'USD', 'symbol': '$', 'name': 'US Dollar'}
        
        try:
            return CurrencyService.get_currency_info(user)
        except Exception:
            return {'code': 'USD', 'symbol': '$', 'name': 'US Dollar'}


class ExpenseSerializer(CurrencyFormattingMixin, serializers.ModelSerializer):
    """
    Serializer for Expense model with currency formatting.
    
    Includes both raw amount and formatted amount.
    """
    # Formatted amount field
    amount_formatted = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = Expense
        fields = [
            'id', 'amount', 'amount_formatted', 'currency_code', 'currency_symbol',
            'date', 'description', 'category', 'owner'
        ]
        read_only_fields = ['id', 'owner']
    
    def get_amount_formatted(self, obj):
        request = self.context.get('request')
        return self.format_currency(obj.amount, request)
    
    def get_currency_code(self, obj):
        request = self.context.get('request')
        info = self.get_currency_info(request)
        return info.get('code', 'USD')
    
    def get_currency_symbol(self, obj):
        request = self.context.get('request')
        info = self.get_currency_info(request)
        return info.get('symbol', '$')


class UserIncomeSerializer(CurrencyFormattingMixin, serializers.ModelSerializer):
    """
    Serializer for UserIncome model with currency formatting.
    """
    amount_formatted = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = UserIncome
        fields = [
            'id', 'amount', 'amount_formatted', 'currency_code', 'currency_symbol',
            'date', 'description', 'source', 'owner'
        ]
        read_only_fields = ['id', 'owner']
    
    def get_amount_formatted(self, obj):
        request = self.context.get('request')
        return self.format_currency(obj.amount, request)
    
    def get_currency_code(self, obj):
        request = self.context.get('request')
        info = self.get_currency_info(request)
        return info.get('code', 'USD')
    
    def get_currency_symbol(self, obj):
        request = self.context.get('request')
        info = self.get_currency_info(request)
        return info.get('symbol', '$')


class ExpenseListSerializer(serializers.ModelSerializer):
    """
    Simplified expense serializer for list views.
    """
    amount_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Expense
        fields = ['id', 'amount', 'amount_formatted', 'date', 'category', 'description']
    
    def get_amount_formatted(self, obj):
        request = self.context.get('request')
        return self.format_currency(obj.amount, request)


class IncomeListSerializer(serializers.ModelSerializer):
    """
    Simplified income serializer for list views.
    """
    amount_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = UserIncome
        fields = ['id', 'amount', 'amount_formatted', 'date', 'source', 'description']
    
    def get_amount_formatted(self, obj):
        request = self.context.get('request')
        return self.format_currency(obj.amount, request)


class YourDataSerializer(serializers.Serializer):
    """Legacy serializer - kept for backward compatibility."""
    description = serializers.CharField()
    category = serializers.CharField()


class CurrencyPreferenceSerializer(serializers.Serializer):
    """
    Serializer for getting/setting user currency preference.
    """
    currency = serializers.ChoiceField(
        choices=[
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('INR', 'Indian Rupee'),
            ('JPY', 'Japanese Yen'),
            ('CAD', 'Canadian Dollar'),
            ('AUD', 'Australian Dollar'),
            ('CHF', 'Swiss Franc'),
            ('CNY', 'Chinese Yuan'),
            ('AED', 'UAE Dirham'),
            ('SAR', 'Saudi Riyal'),
            ('SGD', 'Singapore Dollar'),
            ('MYR', 'Malaysian Ringgit'),
            ('PHP', 'Philippine Peso'),
            ('THB', 'Thai Baht'),
            ('KRW', 'South Korean Won'),
            ('NGN', 'Nigerian Naira'),
            ('ZAR', 'South African Rand'),
            ('BRL', 'Brazilian Real'),
            ('MXN', 'Mexican Peso'),
        ]
    )


class DashboardSummarySerializer(serializers.Serializer):
    """
    Serializer for dashboard summary with currency formatting.
    """
    total_expenses = serializers.FloatField()
    total_expenses_formatted = serializers.CharField()
    total_income = serializers.FloatField()
    total_income_formatted = serializers.CharField()
    balance = serializers.FloatField()
    balance_formatted = serializers.CharField()
    currency_code = serializers.CharField()
    currency_symbol = serializers.CharField()
    expense_count = serializers.IntegerField()
    income_count = serializers.IntegerField()
