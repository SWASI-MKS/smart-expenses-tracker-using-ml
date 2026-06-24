"""
CurrencyService - Enterprise-Level Currency Management

This service provides a unified, cached approach to:
- Fetch user currency preferences
- Format amounts with currency symbols
- Handle fallback defaults
- Support future exchange rate conversions

Architecture:
- Uses functools.lru_cache for in-memory caching (per-process)
- For multi-process/multi-server deployments, consider Redis caching
- Designed to be extendable for future exchange rate API integration
"""

import logging
from functools import lru_cache
from typing import Optional, Union, Dict, Any
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.core.cache import cache

from .models import UserPreference
from .currency_symbols import (
    get_currency_symbol, 
    DEFAULT_CURRENCY, 
    DEFAULT_SYMBOL,
    CURRENCY_SYMBOLS
)

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    Enterprise-level currency service with caching.
    
    Features:
    - In-memory caching to avoid repeated DB queries
    - Thread-safe operations
    - Extendable for future exchange rate support
    - Graceful fallback to default currency
    
    Usage:
        # Get user currency
        currency = CurrencyService.get_user_currency(user)
        
        # Format amount
        formatted = CurrencyService.format_amount(1234.56, user)
        
        # Get currency symbol
        symbol = CurrencyService.get_currency_symbol(user)
    """
    
    # Cache key prefixes
    CACHE_KEY_PREFIX = 'user_currency_'
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours
    
    # Exchange rate storage (for future use)
    _exchange_rates: Dict[str, float] = {}
    
    @classmethod
    def _get_cache_key(cls, user_id: int) -> str:
        """Generate cache key for user currency preference."""
        return f"{cls.CACHE_KEY_PREFIX}{user_id}"
    
    @classmethod
    def get_user_currency(cls, user: Union[User, int], use_cache: bool = True) -> str:
        """
        Get the user's preferred currency code.
        
        Args:
            user: User instance or user ID
            use_cache: Whether to use cached value (default: True)
        
        Returns:
            Currency code string (e.g., 'USD', 'EUR', 'INR')
        """
        # Handle both User object and user_id
        if isinstance(user, User):
            user_id = user.id
        else:
            user_id = int(user)
        
        cache_key = cls._get_cache_key(user_id)
        
        # Try cache first
        if use_cache:
            cached_currency = cache.get(cache_key)
            if cached_currency:
                # Validate cached value is still a valid currency code
                if cached_currency.upper() in CURRENCY_SYMBOLS:
                    return cached_currency
                # If cached value is old format, invalidate and fetch fresh
                cache.delete(cache_key)
        
        # Fetch from database
        try:
            preference = UserPreference.objects.only('currency').get(user_id=user_id)
            currency = preference.currency if preference.currency else DEFAULT_CURRENCY
            
            # Handle backward compatibility - strip old format like "AED - United Arab Emirates Dirham"
            if ' - ' in currency:
                # Old format detected, extract just the currency code
                currency = currency.split(' - ')[0].strip()
                # Update the preference with the correct format
                preference.currency = currency
                preference.save(update_fields=['currency'])
                logger.info(f"Fixed old currency format for user {user_id}: now using {currency}")
            
            # Validate currency code
            if currency.upper() not in CURRENCY_SYMBOLS:
                logger.warning(f"Invalid currency code '{currency}' for user {user_id}, using default")
                currency = DEFAULT_CURRENCY
                
        except UserPreference.DoesNotExist:
            currency = DEFAULT_CURRENCY
            logger.debug(f"No preference found for user {user_id}, using default: {DEFAULT_CURRENCY}")
        except Exception as e:
            logger.error(f"Error fetching currency for user {user_id}: {e}")
            currency = DEFAULT_CURRENCY
        
        # Cache the result
        cache.set(cache_key, currency, cls.CACHE_TIMEOUT)
        
        return currency
    
    @classmethod
    def get_currency_symbol(cls, user: Union[User, int]) -> str:
        """
        Get the currency symbol for a user's preferred currency.
        
        Args:
            user: User instance or user ID
        
        Returns:
            Currency symbol (e.g., '$', '€', '₹')
        """
        currency_code = cls.get_user_currency(user)
        return get_currency_symbol(currency_code)
    
    @classmethod
    def format_amount(
        cls, 
        amount: Union[float, int, Decimal], 
        user: Union[User, int],
        include_symbol: bool = True,
        decimal_places: int = 2
    ) -> str:
        """
        Format an amount with the user's preferred currency symbol.
        
        Args:
            amount: The numeric amount to format
            user: User instance or user ID
            include_symbol: Whether to include currency symbol (default: True)
            decimal_places: Number of decimal places (default: 2)
        
        Returns:
            Formatted string (e.g., '$1,234.56' or '1,234.56')
        """
        # Convert to Decimal for precise rounding
        if isinstance(amount, (float, int)):
            decimal_amount = Decimal(str(amount))
        else:
            decimal_amount = Decimal(str(amount))
        
        # Round to specified decimal places
        quantize_str = '0.' + '0' * decimal_places
        rounded_amount = decimal_amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        
        # Format with thousand separators
        formatted_number = f"{rounded_amount:,.{decimal_places}f}"
        
        if not include_symbol:
            return formatted_number
        
        symbol = cls.get_currency_symbol(user)
        return f"{symbol}{formatted_number}"
    
    @classmethod
    def format_amount_with_code(
        cls,
        amount: Union[float, int, Decimal],
        user: Union[User, int],
        decimal_places: int = 2
    ) -> str:
        """
        Format an amount with currency code (e.g., 'USD 1,234.56').
        
        Args:
            amount: The numeric amount to format
            user: User instance or user ID
            decimal_places: Number of decimal places
        
        Returns:
            Formatted string (e.g., 'USD 1,234.56')
        """
        currency_code = cls.get_user_currency(user)
        
        # Convert and round
        if isinstance(amount, (float, int)):
            decimal_amount = Decimal(str(amount))
        else:
            decimal_amount = Decimal(str(amount))
        
        quantize_str = '0.' + '0' * decimal_places
        rounded_amount = decimal_amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        
        formatted_number = f"{rounded_amount:,.{decimal_places}f}"
        
        return f"{currency_code} {formatted_number}"
    
    @classmethod
    def invalidate_user_cache(cls, user_id: int) -> None:
        """
        Invalidate cached currency preference for a user.
        
        Call this when user updates their currency preference.
        
        Args:
            user_id: The user's ID
        """
        cache_key = cls._get_cache_key(user_id)
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for user {user_id}")
    
    @classmethod
    def get_currency_info(cls, user: Union[User, int]) -> Dict[str, Any]:
        """
        Get complete currency information for a user.
        
        Args:
            user: User instance or user ID
        
        Returns:
            Dictionary with currency code, symbol, and name
        """
        currency_code = cls.get_user_currency(user)
        symbol = get_currency_symbol(currency_code)
        
        return {
            'code': currency_code,
            'symbol': symbol,
            'name': cls._get_currency_name(currency_code)
        }
    
    @classmethod
    def _get_currency_name(cls, currency_code: str) -> str:
        """
        Get the name of a currency code.
        
        Note: This uses a simplified mapping. For production,
        consider loading from currencies.json or a database.
        """
        # This would ideally be loaded from currencies.json
        # For now, return the code as name for unsupported currencies
        currency_names = {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound',
            'JPY': 'Japanese Yen',
            'INR': 'Indian Rupee',
            'CAD': 'Canadian Dollar',
            'AUD': 'Australian Dollar',
            'CHF': 'Swiss Franc',
            'CNY': 'Chinese Yuan',
            'AED': 'UAE Dirham',
            'SAR': 'Saudi Riyal',
            'SGD': 'Singapore Dollar',
            'MYR': 'Malaysian Ringgit',
            'PHP': 'Philippine Peso',
            'THB': 'Thai Baht',
            'KRW': 'South Korean Won',
            'NGN': 'Nigerian Naira',
            'ZAR': 'South African Rand',
            'BRL': 'Brazilian Real',
            'MXN': 'Mexican Peso',
        }
        return currency_names.get(currency_code.upper(), currency_code)
    
    # =====================================================
    # Exchange Rate Support (Future Enhancement)
    # =====================================================
    
    @classmethod
    def set_exchange_rate(cls, from_currency: str, to_currency: str, rate: float) -> None:
        """
        Set exchange rate between two currencies.
        
        This is a placeholder for future exchange rate API integration.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate: Exchange rate
        """
        key = f"{from_currency.upper()}_{to_currency.upper()}"
        cls._exchange_rates[key] = rate
    
    @classmethod
    def get_exchange_rate(cls, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Get exchange rate between two currencies.
        
        Returns None if rate is not available.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
        
        Returns:
            Exchange rate or None
        """
        key = f"{from_currency.upper()}_{to_currency.upper()}"
        return cls._exchange_rates.get(key)
    
    @classmethod
    def convert_amount(
        cls,
        amount: Union[float, Decimal],
        from_currency: str,
        to_currency: str
    ) -> Optional[Decimal]:
        """
        Convert amount from one currency to another.
        
        Requires exchange rate to be set first.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
        
        Returns:
            Converted amount or None if rate not available
        """
        if from_currency.upper() == to_currency.upper():
            return Decimal(str(amount))
        
        rate = cls.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            return None
        
        return Decimal(str(amount)) * Decimal(str(rate))


# Decorator function for cached user currency (alternative approach)
def get_user_currency_cached(user: Union[User, int]) -> str:
    """
    Convenience function to get user currency with caching.
    
    Usage:
        currency = get_user_currency_cached(request.user)
    """
    return CurrencyService.get_user_currency(user)


def format_currency(amount: Union[float, int], user: Union[User, int]) -> str:
    """
    Convenience function to format amount with currency.
    
    Usage:
        formatted = format_currency(expense.amount, request.user)
    """
    return CurrencyService.format_amount(amount, user)
