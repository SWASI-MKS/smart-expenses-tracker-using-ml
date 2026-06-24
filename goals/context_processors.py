"""
Django Context Processor for Goals Summary

This context processor automatically injects goal summary information 
into every template context, showing goals data across all pages.

Usage:
    {{ goal_summary.total_saved }}     - Total amount saved across all goals
    {{ goal_summary.total_target }}    - Total target amount across all goals
    {{ goal_summary.active_goals }}    - Number of active goals
    {{ goal_summary.completed_goals }} - Number of completed goals
    {{ goal_summary.progress }}         - Overall progress percentage
"""

import logging
from typing import Dict, Any

from django.contrib.auth.models import User

from .models import Goal

logger = logging.getLogger(__name__)


def goals_summary_processor(request) -> Dict[str, Any]:
    """
    Django context processor to inject goal summary information globally.
    
    This runs on every request and provides:
    - goal_summary: Dict with total saved, target, counts, and progress
    
    Args:
        request: Django HttpRequest object
    
    Returns:
        Dictionary to be merged into template context
    """
    # Initialize default values
    context = {
        'goal_summary': {
            'total_saved': 0,
            'total_target': 0,
            'active_goals': 0,
            'completed_goals': 0,
            'overdue_goals': 0,
            'progress': 0,
            'has_goals': False,
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
        # Get all non-archived goals for the user
        goals = Goal.objects.filter(
            owner=request.user
        ).exclude(status=Goal.STATUS_ARCHIVED)
        
        # Calculate totals
        total_saved = sum(goal.current_saved_amount for goal in goals)
        total_target = sum(goal.amount_to_save for goal in goals)
        
        # Count by status
        active_goals = goals.filter(status=Goal.STATUS_ACTIVE).count()
        completed_goals = goals.filter(status=Goal.STATUS_COMPLETED).count()
        overdue_goals = goals.filter(status=Goal.STATUS_OVERDUE).count()
        
        # Calculate overall progress
        progress = 0
        if total_target > 0:
            progress = (total_saved / total_target) * 100
        
        context['goal_summary'] = {
            'total_saved': total_saved,
            'total_target': total_target,
            'active_goals': active_goals,
            'completed_goals': completed_goals,
            'overdue_goals': overdue_goals,
            'progress': round(progress, 1),
            'has_goals': goals.exists(),
        }
        
    except Exception as e:
        # Log error but don't break the page
        logger.error(f"Error in goals context processor: {e}")
    
    return context

