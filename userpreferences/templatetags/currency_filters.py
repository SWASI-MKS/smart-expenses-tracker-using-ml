"""
Custom Django Template Filters for Currency Formatting

Usage in templates:
    {{ amount|currency:user }}
    {{ amount|currency_symbol:user }}
    {{ amount|currency_with_code:user }}

These filters use CurrencyService internally - no hardcoded symbols.
"""

import logging
from typing import Union, Optional

from django import template
from django.contrib.auth.models import User

from ..currency_service import CurrencyService
from ..currency_symbols import DEFAULT_SYMBOL

register = template.Library()

logger = logging.getLogger(__name__)


@register.filter
def currency(amount: Union[float, int, str], user: Optional[User] = None) -> str:
    """
    Format an amount with the user's currency symbol.
    
    Usage in templates:
        {{ expense.amount|currency:user }}
        {{ income.amount|currency:request.user }}
        {{ total|currency:user }}
    
    Args:
        amount: The numeric amount to format
        user: User instance (must be authenticated)
    
    Returns:
        Formatted string with currency symbol (e.g., '$1,234.56')
    
    Example:
        {{ 1234.56|currency:user }} -> '$1,234.56'
    """
    # Handle invalid input
    if amount is None:
        return f"{DEFAULT_SYMBOL}0.00"
    
    try:
        # Convert to float if string
        if isinstance(amount, str):
            amount = float(amount.replace(',', ''))
        else:
            amount = float(amount)
    except (ValueError, TypeError):
        return f"{DEFAULT_SYMBOL}0.00"
    
    # Handle no user provided - use default formatting
    if user is None or not hasattr(user, 'id'):
        return f"{DEFAULT_SYMBOL}{amount:,.2f}"
    
    # Check if user is authenticated
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return f"{DEFAULT_SYMBOL}{amount:,.2f}"
    
    try:
        return CurrencyService.format_amount(amount, user)
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        return f"{DEFAULT_SYMBOL}{amount:,.2f}"


@register.filter
def currency_symbol(user: Optional[User] = None) -> str:
    """
    Get the currency symbol for a user.
    
    Usage in templates:
        {{ user|currency_symbol }}
        {{ request.user|currency_symbol }}
    
    Args:
        user: User instance
    
    Returns:
        Currency symbol (e.g., '$', '€', '₹')
    """
    if user is None or not hasattr(user, 'id'):
        return DEFAULT_SYMBOL
    
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return DEFAULT_SYMBOL
    
    try:
        return CurrencyService.get_currency_symbol(user)
    except Exception as e:
        logger.error(f"Error getting currency symbol: {e}")
        return DEFAULT_SYMBOL


@register.filter
def currency_with_code(amount: Union[float, int, str], user: Optional[User] = None) -> str:
    """
    Format an amount with currency code.
    
    Usage in templates:
        {{ expense.amount|currency_with_code:user }}
    
    Args:
        amount: The numeric amount to format
        user: User instance
    
    Returns:
        Formatted string with currency code (e.g., 'USD 1,234.56')
    """
    if amount is None:
        return "USD 0.00"
    
    try:
        if isinstance(amount, str):
            amount = float(amount.replace(',', ''))
        else:
            amount = float(amount)
    except (ValueError, TypeError):
        return "USD 0.00"
    
    if user is None or not hasattr(user, 'id'):
        return f"USD {amount:,.2f}"
    
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return f"USD {amount:,.2f}"
    
    try:
        return CurrencyService.format_amount_with_code(amount, user)
    except Exception as e:
        logger.error(f"Error formatting currency with code: {e}")
        return f"USD {amount:,.2f}"


@register.filter
def currency_code(user: Optional[User] = None) -> str:
    """
    Get the currency code for a user.
    
    Usage in templates:
        {{ user|currency_code }}
    
    Args:
        user: User instance
    
    Returns:
        Currency code (e.g., 'USD', 'EUR', 'INR')
    """
    if user is None or not hasattr(user, 'id'):
        return 'USD'
    
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return 'USD'
    
    try:
        return CurrencyService.get_user_currency(user)
    except Exception as e:
        logger.error(f"Error getting currency code: {e}")
        return 'USD'


# =====================================================
# Simple filters that don't require user context
# =====================================================

@register.filter
def symbol_from_code(code: str) -> str:
    """
    Get symbol from currency code.
    
    Usage in templates:
        {{ "USD"|symbol_from_code }} -> '$'
        {{ currency_code|symbol_from_code }} -> '€'
    
    Args:
        code: Currency code string
    
    Returns:
        Currency symbol
    """
    if not code:
        return DEFAULT_SYMBOL
    
    from ..currency_symbols import get_currency_symbol
    return get_currency_symbol(str(code).upper())


@register.filter
def dict_key(dictionary, key):
    """
    Get value from dictionary by key.
    
    Usage in templates:
        {{ currencies_dict|dict_key:'USD' }}
    
    Args:
        dictionary: The dictionary to access
        key: The key to look up
    
    Returns:
        The value at the key, or empty string if not found
    """
    if dictionary is None:
        return ''
    return dictionary.get(str(key), dictionary.get(key, ''))


@register.simple_tag
def format_currency_tag(amount: Union[float, int], user: User) -> str:
    """
    Django template tag for currency formatting.
    
    Usage:
        {% format_currency_tag expense.amount user %}
    
    More flexible than filters when you need to pass multiple arguments.
    """
    if amount is None:
        return f"{DEFAULT_SYMBOL}0.00"
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return f"{DEFAULT_SYMBOL}0.00"
    
    if user is None or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return f"{DEFAULT_SYMBOL}{amount:,.2f}"
    
    try:
        return CurrencyService.format_amount(amount, user)
    except Exception:
        return f"{DEFAULT_SYMBOL}{amount:,.2f}"
