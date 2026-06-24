"""
Expenses utilities package
"""

from .ocr_processor import scan_receipt, check_ocr_available

# Don't try to import from itself - this causes circular import
# Instead, we'll define the function here or import it from a different module

# If the function is defined in this package (in another file like utils.py),
# import it directly from that file
try:
    from .utils import predict_category_from_text
except ImportError:
    # If utils.py doesn't exist, define a simple version here
    def predict_category_from_text(text):
        """Simple category prediction based on keywords"""
        if not text:
            return "Other"
        
        text = text.lower()
        categories = {
            "Food & Dining": ["food", "restaurant", "lunch", "dinner", "breakfast", "cafe", "coffee"],
            "Transportation": ["uber", "taxi", "bus", "train", "gas", "fuel"],
            "Shopping": ["amazon", "walmart", "shop", "store", "mall"],
            "Entertainment": ["movie", "netflix", "concert", "game"],
            "Bills & Utilities": ["electric", "water", "internet", "phone", "bill"],
            "Healthcare": ["doctor", "hospital", "medicine", "pharmacy"],
            "Education": ["school", "college", "course", "book"],
            "Travel": ["hotel", "flight", "airbnb", "trip"]
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return "Other"


# ================= CATEGORY COLORS FOR UI CONSISTENCY =================

CATEGORY_COLORS = {
    # Core categories from your app
    'Food & Dining': '#FF6B6B',      # Coral Red
    'Transportation': '#4ECDC4',      # Turquoise
    'Shopping': '#FFD93D',            # Golden Yellow
    'Entertainment': '#9B59B6',       # Purple
    'Bills & Utilities': '#3498DB',   # Blue
    'Healthcare': '#E67E22',           # Orange
    'Education': '#2ECC71',            # Green
    'Travel': '#1ABC9C',               # Teal
    
    # Additional common categories
    'Housing': '#E74C3C',               # Red
    'Groceries': '#F39C12',              # Orange
    'EMI & Loans': '#8E44AD',            # Purple
    'Insurance': '#2980B9',               # Dark Blue
    'Investments': '#27AE60',              # Dark Green
    'Salary': '#2C3E50',                   # Dark Gray
    'Freelance': '#16A085',                 # Dark Teal
    'Rental Income': '#D35400',             # Dark Orange
    'Utilities': '#7F8C8D',                 # Gray
    'Subscriptions': '#C0392B',             # Dark Red
    'Personal Care': '#884EA0',             # Light Purple
    'Gifts & Donations': '#A569BD',         # Lavender
    'Taxes': '#515A5A',                      # Dark Gray
    'Savings': '#229954',                     # Forest Green
    
    # Default for unmapped categories
    'Other': '#95A5A6',                       # Gray
}

CATEGORY_CSS_SUFFIXES = {
    'Food & Dining': 'food-dining',
    'Transportation': 'transportation',
    'Shopping': 'shopping',
    'Entertainment': 'entertainment',
    'Bills & Utilities': 'bills-utilities',
    'Healthcare': 'healthcare',
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


def get_category_color(category):
    """Return color for a category"""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS['Other'])


def get_category_css_class(category):
    """Return CSS class for a category"""
    return CATEGORY_CSS_SUFFIXES.get(category, 'other')


# Update __all__ to include the new functions
__all__ = [
    'scan_receipt', 
    'check_ocr_available', 
    'predict_category_from_text',
    'CATEGORY_COLORS',
    'CATEGORY_CSS_SUFFIXES',
    'get_category_color',
    'get_category_css_class',
]