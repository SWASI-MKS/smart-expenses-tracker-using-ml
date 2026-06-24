# Category detection using keyword matching
# No ML, no training, no external dependencies beyond standard library

# Category dataset with keywords (identical to frontend defaultCategoryDataset)
CATEGORY_DATASET = {
    "Food & Dining": {
        "keywords": [
            "restaurant", "cafe", "dinner", "lunch", "breakfast", "food", "meal",
            "groceries", "coffee", "tea", "snack", "pizza", "burger", "sushi",
            "dining", "eat", "bakery", "food delivery", "zomato", "swiggy",
            "mcdonald's", "kfc", "starbucks", "domino's", "pizza hut", "subway",
            "burger king", "wendy's", "chipotle", "panera", "dunkin", "dunkin donuts",
            "costa", "barista", "ccd", "cafe coffee day", "food court", "mess", "canteen",
            "pizza", "burger", "sandwich", "noodles", "rice", "curry", "biryani",
            "dosa", "idli", "vada", "sambar", "chai", "coffee", "juice", "soda",
            "ice cream", "dessert", "cake", "pastry", "chocolate", "snacks",
            "breakfast", "lunch", "dinner", "brunch", "supper", "meal",
            "kfc", "mcd", "subway", "pizzahut", "dominos", "burger king",
            "starbucks", "ccd", "barista", "chaayos", "chai point"
        ],
    },
    "Transportation": {
        "keywords": [
            "uber", "ola", "taxi", "bus", "metro", "train", "flight", "fuel",
            "petrol", "diesel", "gas", "parking", "toll", "auto", "rickshaw",
            "cab", "ride", "transport", "commute", "travel", "airport", "railway",
            "indigo", "air india", "spicejet", "goair", "vistara", "ola money",
            "uber cash", "rapido", "zoomcar", "drivezy", "metro card", "bus pass",
            "uber", "ola", "rapido", "auto", "taxi", "cab", "ride",
            "bus", "train", "metro", "flight", "airplane", "airport",
            "petrol", "diesel", "gas", "fuel", "filling", "station",
            "parking", "toll", "ticket", "pass", "commute", "travel"
        ],
    },
    "Shopping": {
        "keywords": [
            "shopping", "amazon", "flipkart", "myntra", "clothes", "dress",
            "shirt", "shoes", "electronics", "phone", "laptop", "gadget",
            "book", "stationery", "mall", "market", "purchase", "buy", "order",
            "ajio", "nykaa", "purplle", "tatacliq", "reliance digital", "croma",
            "vijay sales", "poorvika", "sangeetha", "big bazaar", "d mart", "more",
            "spencer's", "reliance fresh", "easyday", "star bazaar", "hypermarket",
            "saravana stores", "saravana selvarathnam", "pothys",
            "chennnai silks", "nalli silks", "rmkv", "the chennai shopping mall",
            "clothes", "shoes", "accessories", "electronics", "appliances",
            "furniture", "home decor", "kitchen", "grocery", "supermarket",
            "mall", "market", "store", "shop", "retail", "purchase", "buy"
        ],
    },
    "Entertainment": {
        "keywords": [
            "movie", "cinema", "theatre", "concert", "show", "game", "sports",
            "netflix", "prime video", "disney+", "hotstar", "youtube premium",
            "music", "spotify", "apple music", "party", "event", "fun", "entertainment",
            "pvr", "inox", "carnival", "imax", "bookmyshow", "planetarium", "museum",
            "zoo", "aquarium", "amusement park", "water park", "adventure", "outing",
            "movie", "cinema", "theater", "concert", "show", "game", "sports",
            "netflix", "prime", "disney", "hotstar", "youtube", "streaming",
            "music", "spotify", "apple music", "party", "event", "outing",
            "pvr", "inox", "imax", "bookmyshow", "ticket", "entry", "fee"
        ],
    },
    "Bills & Utilities": {
        "keywords": [
            "electricity", "water", "gas", "internet", "wifi", "mobile", "phone bill",
            "rent", "emi", "loan", "insurance", "subscription", "netflix", "prime",
            "disney+", "hotstar", "utility", "maintenance", "society charges",
            "bsnl", "airtel", "jio", "vi", "vodafone idea", "act", "spectra", "tata sky",
            "dish tv", "airtel dth", "jio fiber", "gas cylinder", "indane", "bharat gas",
            "electricity", "water", "gas", "internet", "wifi", "phone", "bill",
            "rent", "emi", "loan", "insurance", "subscription", "utility",
            "maintenance", "society", "charge", "payment", "dues", "fees"
        ],
    },
    "Healthcare": {
        "keywords": [
            "pharmacy", "medical", "hospital", "clinic", "doctor", "apollo",
            "fortis", "max", "manipal", "medicare", "wellness", "diagnostics",
            "pathology", "lab", "test", "medicine", "drug", "pharmeasy", "netmeds",
            "1mg", "practo", "lybrate", "healthkart", "medlife", "covid", "vaccine",
            "pharmacy", "medical", "hospital", "clinic", "doctor", "appointment",
            "medicine", "drug", "prescription", "test", "lab", "diagnostic",
            "health", "wellness", "checkup", "dental", "eye", "vision"
        ],
    },
    "Education": {
        "keywords": [
            "school", "college", "university", "tuition", "coaching", "course",
            "books", "stationery", "uniform", "fees", "exam", "test", "workshop",
            "seminar", "conference", "training", "certification", "byju's", "vedantu",
            "unacademy", "coursera", "udemy", "skillshare", "edx", "khan academy",
            "extramarks", "toppr", "aakash", "fiitjee", "allen", "resonance",
            "school", "college", "university", "tuition", "coaching", "course",
            "books", "stationery", "uniform", "fees", "exam", "test", "education",
            "learning", "training", "certification", "workshop", "seminar"
        ],
    },
    "Travel": {
        "keywords": [
            "hotel", "resort", "booking", "airbnb", "oyo", "make my trip", "goibibo",
            "cleartrip", "yatra", "expedia", "booking.com", "agoda", "trivago",
            "flight", "train", "bus", "travel", "tour", "package", "holiday",
            "vacation", "trip", "sightseeing", "guide", "tourist", "passport", "visa",
            "hotel", "resort", "booking", "airbnb", "oyo", "stay", "accommodation",
            "flight", "train", "bus", "travel", "tour", "package", "holiday",
            "vacation", "trip", "sightseeing", "tourist", "passport", "visa"
        ],
    },
    "Other": {
        "keywords": [],
    }
}

# =====================================================
# CATEGORY COLOR MAPPING
# =====================================================
# Consistent color mapping for expense categories
# Used by: Pie charts, tables, badges, lists
# Format: category_name -> hex_color
CATEGORY_COLORS = {
    "Food & Dining": "#FF6384",      # Red/Pink - appetizing
    "Food": "#FF6384",               # Map database short name too
    "Transportation": "#36A2EB",     # Blue - trust/transport
    "Transport": "#36A2EB",          # Map database short name too
    "Shopping": "#FFCE56",            # Yellow - attention/retail
    "Entertainment": "#4BC0C0",       # Teal - fun/leisure
    "Bills & Utilities": "#9966FF",  # Purple - utilities
    "Bills": "#9966FF",              # Map database short name too
    "Healthcare": "#FF9F40",          # Orange - health/medical
    "Health": "#FF9F40",             # Map database short name too
    "Education": "#C9CBCF",           # Gray - learning
    "Travel": "#7C4DFF",              # Deep Purple - travel
    "Other": "#6c757d",               # Dark Gray - default
}

# CSS class suffix mapping (for creating CSS classes from category names)
# Converts "Food & Dining" -> "food-dining"
CATEGORY_CSS_SUFFIXES = {
    "Food & Dining": "food-dining",
    "Food": "food-dining",
    "Transportation": "transportation",
    "Transport": "transportation",
    "Shopping": "shopping",
    "Entertainment": "entertainment",
    "Bills & Utilities": "bills-utilities",
    "Bills": "bills-utilities",
    "Healthcare": "healthcare",
    "Health": "healthcare",
    "Education": "education",
    "Travel": "travel",
    "Other": "other",
}


def get_category_color(category_name):
    """
    Get the color for a given category name.
    
    Args:
        category_name: The name of the expense category
        
    Returns:
        Hex color string (e.g., '#FF6384')
    """
    return CATEGORY_COLORS.get(category_name, CATEGORY_COLORS.get("Other", "#6c757d"))


def get_category_css_class(category_name):
    """
    Get the CSS class suffix for a given category name.
    
    Args:
        category_name: The name of the expense category
        
    Returns:
        CSS class suffix string (e.g., 'food-dining')
    """
    return CATEGORY_CSS_SUFFIXES.get(category_name, "other")


def detect_category_from_keywords(description):
    """
    Detect category from expense description using keyword matching.
    This function uses only keyword matching - no ML, no training.

    Args:
        description: The expense description string

    Returns:
        Category name string. Defaults to "Other" if no match found.
    """
    # Handle empty or invalid input
    if not description or not isinstance(description, str):
        return "Other"

    # Convert to lowercase for case-insensitive matching
    description_lower = description.lower().strip()

    if not description_lower:
        return "Other"

    # Loop through all categories and check for keyword matches
    for category_name, category_data in CATEGORY_DATASET.items():
        keywords = category_data.get("keywords", [])

        for keyword in keywords:
            # Use string includes() for matching
            # Convert keyword to lowercase for case-insensitive comparison
            if keyword.lower() in description_lower:
                return category_name

    # No match found - return "Other"
    return "Other"


# Keep the original function name for backward compatibility with views
# but now it uses keyword-based detection instead of ML
def predict_category_from_text(description):
    """
    Predict category using keyword-based detection.
    Returns the predicted category or 'Other' if no match found.

    This function is kept for backward compatibility with existing code.
    """
    return detect_category_from_keywords(description)

"""
Enhanced OCR processor for receipt scanning with quality detection
"""
import os
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def check_ocr_available():
    """Check if OCR dependencies are available."""
    # In production, check for pytesseract/tesseract
    # For now, return True with mock mode
    logger.info("OCR available (mock mode with quality simulation)")
    return True, "OCR available (mock mode with quality simulation)"

def analyze_image_quality(image_path):
    """
    Simulate image quality analysis.
    Returns quality score (0-100) and issues list.
    """
    # Simulate different quality factors
    quality_factors = {
        'resolution': random.randint(30, 100),
        'contrast': random.randint(40, 100),
        'brightness': random.randint(40, 100),
        'sharpness': random.randint(30, 100),
        'noise_level': random.randint(0, 70),
        'skew_angle': random.uniform(0, 5)
    }
    
    # Calculate overall quality score
    base_score = sum(quality_factors.values()) / len(quality_factors)
    
    # Adjust based on filename (simulate different scenarios)
    filename = os.path.basename(image_path).lower()
    
    issues = []
    
    # Simulate quality issues based on filename or random
    if 'blurry' in filename or random.random() < 0.2:
        quality_factors['sharpness'] = random.randint(10, 40)
        issues.append("Image is blurry")
    
    if 'dark' in filename or random.random() < 0.15:
        quality_factors['brightness'] = random.randint(10, 30)
        issues.append("Image is too dark")
    
    if 'glare' in filename or random.random() < 0.1:
        quality_factors['contrast'] = random.randint(20, 50)
        issues.append("Image has glare or reflection")
    
    if 'skewed' in filename or random.random() < 0.15:
        quality_factors['skew_angle'] = random.uniform(8, 25)
        issues.append(f"Image is skewed ({quality_factors['skew_angle']:.1f} degrees)")
    
    if 'lowres' in filename or random.random() < 0.2:
        quality_factors['resolution'] = random.randint(15, 40)
        issues.append("Image resolution is too low")
    
    # Recalculate score with adjusted factors
    final_score = sum(quality_factors.values()) / len(quality_factors)
    
    # Determine quality rating
    if final_score >= 80:
        quality_rating = "Excellent"
    elif final_score >= 60:
        quality_rating = "Good"
    elif final_score >= 40:
        quality_rating = "Fair"
    elif final_score >= 20:
        quality_rating = "Poor"
    else:
        quality_rating = "Unusable"
    
    return {
        'score': round(final_score, 1),
        'rating': quality_rating,
        'issues': issues,
        'factors': quality_factors
    }

def simulate_ocr_extraction(quality_info):
    """
    Simulate OCR text extraction based on image quality.
    Higher quality = more accurate and complete extraction.
    """
    quality_score = quality_info['score']
    
    # Determine success and confidence based on quality
    if quality_score < 20:
        # Unusable image
        return {
            'success': False,
            'error': 'Image quality too low for OCR. Please upload a clearer image.',
            'confidence': 0
        }
    elif quality_score < 40:
        # Poor quality - partial/maybe success
        success = random.random() < 0.3  # 30% chance of success
        if not success:
            return {
                'success': False,
                'error': 'Failed to extract text due to poor image quality',
                'confidence': 0
            }
        confidence = random.uniform(30, 50)
    elif quality_score < 60:
        # Fair quality
        confidence = random.uniform(50, 70)
    elif quality_score < 80:
        # Good quality
        confidence = random.uniform(70, 90)
    else:
        # Excellent quality
        confidence = random.uniform(90, 99)
    
    # Determine which fields can be extracted based on quality
    merchants = ["Walmart", "Target", "Starbucks", "Amazon", "Uber", "McDonald's", "Shell", "Netflix", "CVS", "Walgreens"]
    categories = {
        "Walmart": "Shopping",
        "Target": "Shopping",
        "Starbucks": "Food & Dining",
        "Amazon": "Shopping",
        "Uber": "Transportation",
        "McDonald's": "Food & Dining",
        "Shell": "Transportation",
        "Netflix": "Entertainment",
        "CVS": "Healthcare",
        "Walgreens": "Healthcare"
    }
    
    # Simulate extraction based on confidence
    amount = round(random.uniform(5.0, 150.0), 2) if confidence > 40 else None
    merchant = random.choice(merchants) if confidence > 50 else None
    category = categories.get(merchant, "Other") if merchant else None
    
    # Date extraction - more reliable with good quality
    if confidence > 60:
        date = (datetime.now() - timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d')
    else:
        date = None
    
    # Generate raw text based on quality
    if confidence > 70:
        raw_text = f"{merchant}\n{datetime.now().strftime('%Y-%m-%d')}\nItems: ...\nSubtotal: ${amount*0.85:.2f}\nTax: ${amount*0.15:.2f}\nTotal: ${amount}\nThank you!"
    elif confidence > 40:
        raw_text = f"{merchant if merchant else 'STORE'}\nTotal: ${amount if amount else 'XX.XX'}\n..."
    else:
        raw_text = "Unable to extract text clearly"
    
    # Add warnings based on quality
    warnings = []
    if quality_score < 50:
        warnings.append("Low confidence extraction - please verify all fields")
    if quality_info['issues']:
        warnings.extend(quality_info['issues'])
    
    return {
        'success': True,
        'amount': amount,
        'merchant': merchant,
        'date': date,
        'category': category,
        'confidence': round(confidence, 1),
        'raw_text': raw_text,
        'quality': quality_info,
        'warnings': warnings,
        'error': None
    }

def scan_receipt(image_path):
    """
    Process receipt image with quality detection and simulated OCR.
    """
    logger.info(f"OCR processing started for: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return {
            'success': False,
            'amount': None,
            'merchant': None,
            'date': None,
            'category': 'Other',
            'confidence': 0.0,
            'raw_text': '',
            'quality': None,
            'warnings': ['Image file not found'],
            'error': 'Image file not found'
        }
    
    try:
        # Simulate processing time based on file size (smaller delay)
        file_size = os.path.getsize(image_path)
        processing_time = min(0.5, file_size / (10 * 1024 * 1024))  # Max 0.5 seconds
        import time
        time.sleep(processing_time)
        
        # Analyze image quality
        quality_info = analyze_image_quality(image_path)
        logger.info(f"Image quality analysis: {quality_info['rating']} (score: {quality_info['score']})")
        
        # Simulate OCR extraction based on quality
        result = simulate_ocr_extraction(quality_info)
        
        # Add file info
        result['file_name'] = os.path.basename(image_path)
        result['file_size'] = file_size
        
        logger.info(f"OCR result: success={result.get('success')}, confidence={result.get('confidence')}")
        return result
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'amount': None,
            'merchant': None,
            'date': None,
            'category': 'Other',
            'confidence': 0.0,
            'raw_text': '',
            'quality': None,
            'warnings': [str(e)],
            'error': f'OCR processing failed: {str(e)}'
        }