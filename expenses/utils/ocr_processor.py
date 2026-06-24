"""
OCR Receipt Processor for Expense Tracker
==========================================
Provides complete OCR functionality to scan receipts and extract expense data.

Features:
- Tesseract OCR integration
- Image preprocessing with OpenCV
- Intelligent data extraction (amount, date, merchant)
- Category auto-classification
- Confidence scoring
- Comprehensive error handling
"""

import os
import re
import logging
import numpy as np
from datetime import datetime
from django.conf import settings

# Configure logging
LOG_DIR = os.path.join(settings.BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'ocr_logs.txt')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================
# TESSERACT CONFIGURATION
# =====================================================

def configure_tesseract():
    """
    Configure Tesseract OCR executable path.
    Returns True if successful, False otherwise.
    """
    try:
        import pytesseract
        # Windows example path - adjust for your system
        # Users need to install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract configured successfully: {tesseract_path}")
            return True
        else:
            # Try to find tesseract in PATH
            logger.warning("Tesseract not found at default location. Checking PATH...")
            pytesseract.pytesseract.tesseract_cmd = 'tesseract'
            return True
    except Exception as e:
        logger.error(f"Failed to configure Tesseract: {e}")
        return False


def check_ocr_available():
    """
    Check if OCR libraries are available.
    Returns tuple: (available: bool, message: str)
    """
    try:
        import pytesseract
    except ImportError as e:
        return False, f"Missing pytesseract: {str(e)}"
    
    try:
        import cv2
    except ImportError as e:
        return False, f"Missing opencv-python: {str(e)}"
    
    try:
        import numpy as np
    except ImportError as e:
        return False, f"Missing numpy: {str(e)}"
    
    # Try to configure Tesseract
    configure_tesseract()
    return True, "OCR libraries available"


# =====================================================
# IMAGE PREPROCESSING
# =====================================================

def preprocess_image(image_path):
    """
    Preprocess image for better OCR accuracy.
    
    Steps:
    1. Load image
    2. Resize if too large
    3. Convert to grayscale
    4. Apply Gaussian blur to reduce noise
    5. Apply thresholding for better text contrast
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Processed image ready for OCR, or None if failed
    """
    try:
        import cv2
        
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to read image: {image_path}")
            return None
        
        # Resize large images for performance (max 2000px)
        height, width = image.shape[:2]
        max_dimension = 2000
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            logger.info(f"Image resized for OCR processing")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply Otsu's thresholding for better text contrast
        # This automatically finds the optimal threshold value
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Apply morphological operations to enhance text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        logger.info("Image preprocessing completed")
        return thresh
        
    except Exception as e:
        logger.error(f"Error in image preprocessing: {e}")
        return None


# =====================================================
# OCR TEXT EXTRACTION
# =====================================================

def extract_text_from_image(processed_image):
    """
    Extract text from preprocessed image using Tesseract OCR.
    
    Args:
        processed_image: Preprocessed image from preprocess_image()
        
    Returns:
        Tuple: (extracted_text: str, confidence: float)
    """
    try:
        import pytesseract
        
        # Configure Tesseract
        configure_tesseract()
        
        # Extract text
        text = pytesseract.image_to_string(processed_image)
        
        # Get confidence score
        # pytesseract returns data with confidence values
        data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        logger.info(f"OCR extracted text with confidence: {avg_confidence:.1f}%")
        return text, avg_confidence
        
    except Exception as e:
        logger.error(f"Error in OCR text extraction: {e}")
        return "", 0.0


# =====================================================
# INTELLIGENT DATA EXTRACTION
# =====================================================

def extract_amount(text):
    """
    Extract amount from OCR text using regex patterns.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Float amount or None if not found
    """
    # Common amount patterns
    patterns = [
        r'(?:total|amount|sum|rs\.?|₹)\s*:?\s*([\d,]+\.?\d*)',  # total: 250.00
        r'(?:₹|rs\.?)\s*([\d,]+\.?\d*)',  # ₹250 or rs250
        r'([\d,]+\.\d{2})\s*(?:/-)?',  # 250.00/-
        r'\b(\d+\.\d{2})\b',  # Any decimal with 2 places
        r'\b(\d+)\b',  # Any integer (fallback)
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Clean the number (remove commas)
            amount_str = match.replace(',', '').strip()
            try:
                amount = float(amount_str)
                # Reasonable amount range (1 to 100000)
                if 1 <= amount <= 100000:
                    amounts.append(amount)
            except ValueError:
                continue
    
    # Return the largest amount (usually the total)
    return max(amounts) if amounts else None


def extract_date(text):
    """
    Extract date from OCR text using regex patterns.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Date string in YYYY-MM-DD format or None if not found
    """
    # Common date patterns
    patterns = [
        r'(\d{2})[/\-.](\d{2})[/\-.](\d{4})',  # DD-MM-YYYY or DD/MM/YYYY
        r'(\d{4})[/\-.](\d{2})[/\-.](\d{2})',  # YYYY-MM-DD
        r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})',  # Short year
        r'(?:date|dated)\s*:?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})',  # Date: 10-03-2026
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                if len(match) == 3:
                    # Determine format based on position
                    part1, part2, part3 = match
                    
                    # Try DD-MM-YYYY format
                    if len(part3) == 4:
                        day, month, year = int(part1), int(part2), int(part3)
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            return f"{year:04d}-{month:02d}-{day:02d}"
                    
                    # Try YYYY-MM-DD format
                    if len(part1) == 4:
                        year, month, day = int(part1), int(part2), int(part3)
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            return f"{year:04d}-{month:02d}-{day:02d}"
                            
            except (ValueError, IndexError):
                continue
    
    return None


def extract_merchant(text):
    """
    Extract merchant name from OCR text.
    Usually the first prominent line of text.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Merchant name or None if not found
    """
    lines = text.strip().split('\n')
    
    # Clean and filter lines
    meaningful_lines = []
    for line in lines:
        # Remove empty lines and very short lines
        line = line.strip()
        if len(line) >= 3:
            # Skip lines that are mostly numbers or special chars
            alpha_count = sum(c.isalpha() for c in line)
            if alpha_count / len(line) > 0.3:  # At least 30% letters
                meaningful_lines.append(line)
    
    # Return first meaningful line as merchant name
    if meaningful_lines:
        return meaningful_lines[0]
    
    return None


# =====================================================
# CATEGORY AUTO CLASSIFICATION
# =====================================================

CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "restaurant", "cafe", "dinner", "lunch", "breakfast", "food", "meal",
        "groceries", "coffee", "tea", "snack", "pizza", "burger", "sushi",
        "dining", "eat", "bakery", "food delivery", "zomato", "swiggy",
        "mcdonald's", "kfc", "starbucks", "domino's", "pizza hut", "subway",
        "burger king", "wendy's", "chipotle", "panera", "dunkin",
        "restaurant", "hotel", "kitchen", "dhabba", "mess", "canteen",
        "biryani", "dosa", "idli", "vada", "sambar", "chai", "juice",
        "ice cream", "dessert", "cake", "pastry", "chocolate", "snacks"
    ],
    "Transportation": [
        "uber", "ola", "taxi", "bus", "metro", "train", "flight", "fuel",
        "petrol", "diesel", "gas", "parking", "toll", "auto", "rickshaw",
        "cab", "ride", "transport", "commute", "travel", "airport", "railway",
        "indigo", "air india", "spicejet", "rapido", "zoomcar", "drivezy",
        "petrol", "diesel", "fuel", "filling station", "gas station"
    ],
    "Shopping": [
        "shopping", "amazon", "flipkart", "myntra", "clothes", "dress",
        "shirt", "shoes", "electronics", "phone", "laptop", "gadget",
        "book", "stationery", "mall", "market", "purchase", "buy", "order",
        "ajio", "nykaa", "flipkart", "amazon", "myntra", "meesho",
        "shop", "store", "retail", "market", "supermarket", "department"
    ],
    "Entertainment": [
        "movie", "cinema", "theatre", "concert", "show", "game", "sports",
        "netflix", "prime video", "disney+", "hotstar", "youtube premium",
        "music", "spotify", "apple music", "party", "event", "fun",
        "pvr", "inox", "carnival", "imax", "bookmyshow", "ticket"
    ],
    "Bills & Utilities": [
        "electricity", "water", "gas", "internet", "wifi", "mobile", "phone bill",
        "rent", "emi", "loan", "insurance", "subscription", "netflix", "prime",
        "bsnl", "airtel", "jio", "vi", "vodafone", "act", "spectra",
        "bill", "payment", "utility", "maintenance", "society charges"
    ],
    "Healthcare": [
        "pharmacy", "medical", "hospital", "clinic", "doctor", "apollo",
        "fortis", "max", "manipal", "medicare", "wellness", "diagnostics",
        "pathology", "lab", "test", "medicine", "drug", "pharmeasy", "netmeds",
        "1mg", "practo", "health", "hospital", "clinic", "pharmacy"
    ],
    "Education": [
        "school", "college", "university", "tuition", "coaching", "course",
        "books", "stationery", "uniform", "fees", "exam", "test", "workshop",
        "byju's", "vedantu", "unacademy", "coursera", "udemy", "skillshare",
        "education", "learning", "training", "certification"
    ],
    "Travel": [
        "hotel", "resort", "booking", "airbnb", "oyo", "make my trip", "goibibo",
        "cleartrip", "yatra", "expedia", "booking.com", "agoda", "trivago",
        "flight", "train", "bus", "travel", "tour", "package", "holiday",
        "vacation", "trip", "sightseeing", "stay", "accommodation"
    ]
}


def classify_category(text):
    """
    Automatically classify expense category based on OCR text.
    
    Args:
        text: Raw OCR text
        
    Returns:
        Category name string
    """
    text_lower = text.lower()
    
    # Count keyword matches for each category
    category_scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 1
        category_scores[category] = score
    
    # Return category with highest score
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])
        if best_category[1] > 0:
            return best_category[0]
    
    return "Other"


# =====================================================
# MAIN OCR PROCESSING FUNCTION
# =====================================================

def process_receipt_image(image_path):
    """
    Main function to process receipt image and extract expense data.
    
    Args:
        image_path: Path to the receipt image file
        
    Returns:
        Dictionary with extracted data:
        {
            "success": bool,
            "amount": float or None,
            "merchant": str or None,
            "date": str or None,
            "category": str,
            "confidence": float,
            "raw_text": str,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "amount": None,
        "merchant": None,
        "date": None,
        "category": "Other",
        "confidence": 0.0,
        "raw_text": "",
        "error": None
    }
    
    # Check if image file exists
    if not os.path.exists(image_path):
        result["error"] = "Image file not found"
        logger.error(f"OCR Error: {result['error']}")
        return result
    
    # Check if OCR libraries are available
    ocr_available, message = check_ocr_available()
    if not ocr_available:
        result["error"] = f"OCR not available: {message}"
        logger.error(f"OCR Error: {result['error']}")
        return result
    
    try:
        # Step 1: Preprocess image
        logger.info(f"Processing receipt: {image_path}")
        processed_image = preprocess_image(image_path)
        
        if processed_image is None:
            result["error"] = "Failed to preprocess image"
            logger.error("OCR Error: Image preprocessing failed")
            return result
        
        # Step 2: Extract text with OCR
        raw_text, confidence = extract_text_from_image(processed_image)
        
        if not raw_text or len(raw_text.strip()) < 10:
            result["error"] = "No text detected in image"
            result["confidence"] = confidence
            logger.warning("OCR Warning: No meaningful text extracted")
            return result
        
        result["raw_text"] = raw_text
        result["confidence"] = confidence
        result["success"] = True
        
        # Step 3: Extract structured data
        result["amount"] = extract_amount(raw_text)
        result["date"] = extract_date(raw_text)
        result["merchant"] = extract_merchant(raw_text)
        result["category"] = classify_category(raw_text)
        
        # Log the extraction results
        logger.info(f"OCR Results:")
        logger.info(f"  - Amount: {result['amount']}")
        logger.info(f"  - Merchant: {result['merchant']}")
        logger.info(f"  - Date: {result['date']}")
        logger.info(f"  - Category: {result['category']}")
        logger.info(f"  - Confidence: {result['confidence']:.1f}%")
        
        # Log raw text for debugging
        logger.info(f"Raw OCR Text:\n{raw_text[:500]}...")
        
        return result
        
    except Exception as e:
        result["error"] = f"OCR processing failed: {str(e)}"
        logger.error(f"OCR Error: {result['error']}", exc_info=True)
        return result


# =====================================================
# API-FRIENDLY FUNCTION
# =====================================================

def scan_receipt(file_path):
    """
    Simplified API function for scanning receipts.
    
    Args:
        file_path: Path to the receipt image
        
    Returns:
        Dictionary with standardized response:
        {
            "success": bool,
            "amount": float,
            "merchant": string,
            "date": string,
            "category": string,
            "confidence": float,
            "raw_text": string,
            "error": string or None
        }
    """
    result = process_receipt_image(file_path)
    
    # Format date for API response
    if result.get("date"):
        try:
            # Ensure date is in YYYY-MM-DD format
            date_obj = datetime.strptime(result["date"], "%Y-%m-%d")
            result["date"] = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            result["date"] = None
    
    # Ensure amount is float
    if result.get("amount"):
        try:
            result["amount"] = float(result["amount"])
        except (ValueError, TypeError):
            result["amount"] = None
    
    return result

