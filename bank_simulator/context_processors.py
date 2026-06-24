"""
Django Context Processor for Bank Balance Summary

This context processor automatically injects bank balance information 
into every template context, showing bank data across all pages.

Usage:
    {{ bank_summary.balance }}        - Current bank balance
    {{ bank_summary.has_account }}   - Whether user has a bank account
"""

import logging
from typing import Dict, Any

from django.contrib.auth.models import User

from .models import BankAccount

logger = logging.getLogger(__name__)


def bank_summary_processor(request) -> Dict[str, Any]:
    """
    Django context processor to inject bank summary information globally.
    
    This runs on every request and provides:
    - bank_summary: Dict with balance and account info
    
    Args:
        request: Django HttpRequest object
    
    Returns:
        Dictionary to be merged into template context
    """
    # Initialize default values
    context = {
        'bank_summary': {
            'balance': 0,
            'has_account': False,
            'account_number': '',
        }
    }
    
    # Check if user is authenticated
    if not hasattr(request, 'user'):
        return context
    
    if not hasattr(request.user, 'is_authenticated'):
        return context
    
    if not request.user.is_authenticated:
        return context
    
    try:
        # Get bank account for the user
        account = BankAccount.objects.filter(user=request.user).first()
        
        if account:
            context['bank_summary'] = {
                'balance': account.balance,
                'has_account': True,
                'account_number': account.account_number,
            }
        
    except Exception as e:
        # Log error but don't break the page
        logger.error(f"Error in bank context processor: {e}")
    
    return context

