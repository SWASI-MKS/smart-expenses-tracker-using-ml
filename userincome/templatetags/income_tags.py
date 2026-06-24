from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Source color mapping
SOURCE_COLORS = {
    'Salary': '#10b981',        # Green
    'Freelance': '#8b5cf6',      # Purple
    'Investment': '#f59e0b',     # Orange
    'Business': '#3b82f6',       # Blue
    'Rent': '#ec4899',           # Pink
    'Gift': '#f97316',           # Orange
    'Refund': '#14b8a6',         # Teal
    'Bank Transfer': '#6366f1',   # Indigo
    'Interest': '#a855f7',        # Purple
    'Dividend': '#06b6d4',        # Cyan
    'Bonus': '#d946ef',           # Magenta
    'Commission': '#f43f5e',      # Rose
    'Other': '#6b7280',           # Gray
}

@register.filter
def source_pill(source):
    """Return HTML for a source pill with correct color"""
    if not source:
        return ''
    
    color = SOURCE_COLORS.get(source, '#6b7280')
    
    return mark_safe(
        f'<span class="source-pill" style="background-color: {color};">'
        f'{source}</span>'
    )

@register.filter
def source_color(source):
    """Return just the color for a source"""
    return SOURCE_COLORS.get(source, '#6b7280')