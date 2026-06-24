from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def replace(value, old_new):
    """
    Replace occurrences of a substring with another string.
    Usage: {{ value|replace:"old,new" }} or {{ value|replace:"_"," " }}
    
    If two arguments are passed (old, new), it replaces old with new.
    If one argument is passed, it replaces that string with empty string.
    """
    if not value:
        return value
    
    # Handle the case where old_new is a tuple (multiple args in Django)
    if isinstance(old_new, tuple):
        if len(old_new) >= 2:
            old = old_new[0]
            new = old_new[1]
            return value.replace(old, new)
        elif len(old_new) == 1:
            return value.replace(old_new[0], '')
        return value
    
    # Handle single string argument with comma separator
    if ',' in old_new:
        args = old_new.split(',')
        if len(args) >= 2:
            old = args[0]
            new = args[1]
            return value.replace(old, new)
        elif len(args) == 1:
            return value.replace(args[0], '')
    
    # Simple case: replace old_new with empty string
    return value.replace(old_new, '')

# Income source colors (distinct colors for income sources)
INCOME_SOURCE_COLORS = {
    'Salary': '#10B981',           # Emerald Green
    'Freelance': '#8B5CF6',        # Purple
    'Rental Income': '#F59E0B',     # Amber
    'Investments': '#3B82F6',      # Blue
    'Business': '#EC4899',         # Pink
    'Royalties': '#14B8A6',        # Teal
    'Dividends': '#6366F1',        # Indigo
    'Interest': '#84CC16',         # Lime
    'Gifts': '#F97316',            # Orange
    'Refunds': '#06B6D4',          # Cyan
    'Other Income': '#6B7280',     # Gray
}

# Category color mapping (defined directly in the template tag)
CATEGORY_COLORS = {
    # Income Sources (distinct colors for income)
    'Salary': '#10B981',           # Emerald Green
    'Freelance': '#8B5CF6',        # Purple
    'Rental Income': '#F59E0B',     # Amber
    'Investments': '#3B82F6',      # Blue
    'Business': '#EC4899',         # Pink
    'Royalties': '#14B8A6',        # Teal
    'Dividends': '#6366F1',        # Indigo
    'Interest': '#84CC16',         # Lime
    'Gifts': '#F97316',            # Orange
    'Refunds': '#06B6D4',          # Cyan
    'Other Income': '#6B7280',     # Gray
    
    # Expense categories
    # Core categories
    'Food & Dining': '#FF6B6B',      # Coral Red
    'Food': '#FF6B6B',               # Short name
    'Transportation': '#4ECDC4',      # Turquoise
    'Transport': '#4ECDC4',          # Short name
    'Shopping': '#FFD93D',            # Golden Yellow
    'Entertainment': '#9B59B6',       # Purple
    'Bills & Utilities': '#3498DB',   # Blue
    'Bills': '#3498DB',              # Short name
    'Healthcare': '#E67E22',           # Orange
    'Health': '#E67E22',             # Short name
    'Education': '#2ECC71',            # Green
    'Travel': '#1ABC9C',               # Teal
    
    # Additional categories
    'Housing': '#E74C3C',               # Red
    'Groceries': '#F39C12',              # Orange
    'EMI & Loans': '#8E44AD',            # Purple
    'Insurance': '#2980B9',               # Dark Blue
    'Investments Expense': '#27AE60',              # Dark Green
    'Utilities': '#7F8C8D',                 # Gray
    'Subscriptions': '#C0392B',             # Dark Red
    'Personal Care': '#884EA0',             # Light Purple
    'Gifts & Donations': '#A569BD',         # Lavender
    'Taxes': '#515A5A',                      # Dark Gray
    'Savings': '#229954',                     # Forest Green
    
    # Default
    'Other': '#95A5A6',                       # Gray
}

DEFAULT_COLOR = '#95A5A6'

@register.filter
def income_source_color(source):
    """
    Return the hex color for an income source.
    Usage: <div style="background-color: {{ income.source|income_source_color }};">
    """
    return INCOME_SOURCE_COLORS.get(source, DEFAULT_COLOR)

@register.filter
def category_badge(category):
    """
    Return HTML for a category badge with correct color.
    Usage: {{ expense.category|category_badge }}
    """
    if not category:
        return ''
    
    color = CATEGORY_COLORS.get(category, DEFAULT_COLOR)
    
    # Create a badge with inline styles for consistent appearance
    badge_html = (
        f'<span class="category-badge" style="'
        f'background-color: {color}; '
        f'color: white; '
        f'padding: 4px 12px; '
        f'border-radius: 20px; '
        f'font-size: 0.85rem; '
        f'font-weight: 500; '
        f'display: inline-block; '
        f'min-width: 100px; '
        f'text-align: center; '
        f'box-shadow: 0 2px 4px rgba(0,0,0,0.1);'
        f'">{category}</span>'
    )
    
    return mark_safe(badge_html)


@register.filter
def category_color(category):
    """
    Return just the hex color for a category.
    Usage: <div style="background-color: {{ expense.category|category_color }};">
    """
    return CATEGORY_COLORS.get(category, DEFAULT_COLOR)


@register.filter
def category_css_class(category):
    """
    Return CSS class name for a category.
    Usage: <span class="category-{{ expense.category|category_css_class }}">
    """
    css_map = {
        'Food & Dining': 'food-dining',
        'Food': 'food-dining',
        'Transportation': 'transportation',
        'Transport': 'transportation',
        'Shopping': 'shopping',
        'Entertainment': 'entertainment',
        'Bills & Utilities': 'bills-utilities',
        'Bills': 'bills-utilities',
        'Healthcare': 'healthcare',
        'Health': 'healthcare',
        'Education': 'education',
        'Travel': 'travel',
        'Housing': 'housing',
        'Groceries': 'groceries',
        'EMI & Loans': 'emi-loans',
        'Insurance': 'insurance',
        'Investments': 'investments',
        'Salary': 'salary',
        'Freelance': 'freelance',
        'Rental Income': 'rental-income',
        'Utilities': 'utilities',
        'Subscriptions': 'subscriptions',
        'Personal Care': 'personal-care',
        'Gifts & Donations': 'gifts-donations',
        'Taxes': 'taxes',
        'Savings': 'savings',
        'Other': 'other',
    }
    return css_map.get(category, 'other')


@register.simple_tag
def category_colors_json():
    """
    Return category colors as JSON for JavaScript.
    Usage: var colors = JSON.parse('{% category_colors_json %}');
    """
    return mark_safe(json.dumps(CATEGORY_COLORS))


@register.inclusion_tag('expenses/partials/category_legend.html')
def category_legend():
    """
    Render a legend of all categories with their colors.
    Usage: {% category_legend %}
    """
    return {
        'categories': sorted(CATEGORY_COLORS.items()),
    }


@register.filter
def category_icon(category):
    """
    Return a Font Awesome icon for the category.
    Usage: <i class="{{ expense.category|category_icon }}"></i>
    """
    icon_map = {
        'Food & Dining': 'fas fa-utensils',
        'Food': 'fas fa-utensils',
        'Transportation': 'fas fa-car',
        'Transport': 'fas fa-car',
        'Shopping': 'fas fa-shopping-cart',
        'Entertainment': 'fas fa-film',
        'Bills & Utilities': 'fas fa-file-invoice',
        'Bills': 'fas fa-file-invoice',
        'Healthcare': 'fas fa-hospital',
        'Health': 'fas fa-hospital',
        'Education': 'fas fa-graduation-cap',
        'Travel': 'fas fa-plane',
        'Housing': 'fas fa-home',
        'Groceries': 'fas fa-shopping-basket',
        'EMI & Loans': 'fas fa-hand-holding-usd',
        'Insurance': 'fas fa-shield-alt',
        'Investments': 'fas fa-chart-line',
        'Salary': 'fas fa-money-bill-wave',
        'Freelance': 'fas fa-laptop-code',
        'Rental Income': 'fas fa-key',
        'Utilities': 'fas fa-bolt',
        'Subscriptions': 'fas fa-calendar-check',
        'Personal Care': 'fas fa-smile',
        'Gifts & Donations': 'fas fa-gift',
        'Taxes': 'fas fa-calculator',
        'Savings': 'fas fa-piggy-bank',
        'Other': 'fas fa-tag',
    }
    return icon_map.get(category, 'fas fa-tag')