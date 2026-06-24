"""
Django Context Processor for Global Currency Injection

This context processor automatically injects currency information 
into every template context, eliminating the need to pass currency 
manually in each view.

Usage:
    {{ current_currency }}     - Currency code (e.g., 'USD')
    {{ current_symbol }}       - Currency symbol (e.g., '$')
    {{ currency_info }}        - Dict with code, symbol, name
"""

import logging
from typing import Dict, Any

from django.contrib.auth.models import User

from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


def currency_processor(request) -> Dict[str, Any]:
    """
    Django context processor to inject currency information globally.
    
    This runs on every request and provides:
    - current_currency: The user's currency code
    - current_symbol: The user's currency symbol
    - currency_info: Full currency information dict
    
    Args:
        request: Django HttpRequest object
    
    Returns:
        Dictionary to be merged into template context
    """
    # Initialize default values
    context = {
        'current_currency': 'USD',
        'current_symbol': '$',
        'currency_info': {
            'code': 'USD',
            'symbol': '$',
            'name': 'US Dollar'
        }
    }
    
    # Check if user is authenticated
    if not hasattr(request, 'user'):
        return context
    
    if not request.user.is_authenticated:
        return context
    
    try:
        # Get currency info using CurrencyService (with caching)
        currency_info = CurrencyService.get_currency_info(request.user)
        
        context['current_currency'] = currency_info['code']
        context['current_symbol'] = currency_info['symbol']
        context['currency_info'] = currency_info
        
    except Exception as e:
        # Log error but don't break the page
        logger.error(f"Error in currency context processor: {e}")
    
    return context


# Alternative: Simple processor that only adds currency when user is authenticated
def currency_context(request: Any) -> Dict[str, Any]:
    """
    Simplified context processor - adds currency only for authenticated users.
    
    This is more efficient as it skips processing for anonymous users.
    Provides both 'current_symbol' and 'currency_symbol' for template compatibility.
    """
    # Return empty dict for anonymous users - they'll use defaults
    if not hasattr(request, 'user') or not hasattr(request.user, 'is_authenticated'):
        return {}
    
    if not request.user.is_authenticated:
        return {}
    
    # Prevent issues with lazy users
    try:
        currency_info = CurrencyService.get_currency_info(request.user)
        return {
            'current_currency': currency_info['code'],
            'current_symbol': currency_info['symbol'],
            'currency_symbol': currency_info['symbol'],  # Alias for compatibility
            'currency_info': currency_info,
        }
    except Exception:
        return {}
