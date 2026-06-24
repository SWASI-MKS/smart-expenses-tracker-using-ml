"""
Bank Simulator Service Layer
Advanced business logic for bank transactions, categorization, and analytics.
"""
import hashlib
import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple

from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from .models import (
    Card,
    CardTransaction,
    BankAccount,
    BankTransaction,
    Alert
)


# =====================================================
# CATEGORY DETECTION (Using keyword matching - No ML)
# =====================================================

# Category keywords (consistent with expense tracker)
# Expanded with task-specific keywords for auto-categorization
CATEGORY_KEYWORDS = {
    "Food & Dining": [
        # Core food keywords
        "restaurant", "cafe", "dinner", "lunch", "breakfast", "food", "meal",
        "groceries", "coffee", "tea", "snack", "pizza", "burger", "sushi",
        "zomato", "swiggy", "mcdonald", "kfc", "starbucks", "domino",
        "bakery", "dining", "eat", "mess", "canteen", "food delivery",
        "pizza hut", "subway", "burger king", "wendy", "chipotle", "dunkin",
        "barista", "chaayos", "chai point", "dosa", "idli", "vada", "biryani",
        # Task-specific food keywords
        "swiggy", "zomato", "foodpanda", "uber eats", "doorDash",
        "restaurant", "diner", "eatery", "kitchen", "tiffin", "mess",
        "grocery", "supermarket", "big basket", "grofers", "zepto"
    ],
    "Transportation": [
        # Core transport keywords
        "uber", "ola", "taxi", "bus", "metro", "train", "flight", "fuel",
        "petrol", "diesel", "gas", "parking", "toll", "auto", "rickshaw",
        "cab", "ride", "transport", "commute", "travel", "airport", "railway",
        "rapido", "zoomcar", "drivezy",
        # Task-specific transport keywords
        "uber", "ola", "lyft", "grab", "taxi", "cab", "car rental",
        "fuel", "petrol", "diesel", "gas station", "IOC", "HP", "BPCL",
        "metro", "subway", "bus", "train", "railway", "flight", "airline",
        "parking", "toll", "fastag", "auto", "rickshaw", "e-rickshaw"
    ],
    "Shopping": [
        # Core shopping keywords
        "amazon", "flipkart", "myntra", "clothes", "dress", "shirt", "shoes",
        "electronics", "phone", "laptop", "gadget", "book", "stationery",
        "mall", "market", "purchase", "buy", "order", "shopping",
        "ajio", "nykaa", "purplle", "tatacliq", "croma", "big bazaar", "d mart",
        # Task-specific shopping keywords
        "amazon", "flipkart", "myntra", "snapdeal", "ebay", "walmart",
        "shopping", "purchase", "buy", "order", "clothing", "fashion",
        "electronics", "mobile", "laptop", "computer", "gadget", "accessories",
        "mall", "market", "store", "shop", "retail", "brand"
    ],
    "Entertainment": [
        # Core entertainment keywords
        "movie", "cinema", "theatre", "concert", "show", "game", "sports",
        "netflix", "prime", "disney", "hotstar", "youtube", "spotify",
        "music", "party", "event", "pvr", "inox", "bookmyshow",
        # Task-specific entertainment keywords
        "netflix", "amazon prime", "disney plus", "hotstar", "hulu",
        "spotify", "apple music", "youtube", "gaana", "jio saavn",
        "movie", "cinema", "theatre", "concert", "show", "event",
        "game", "gaming", "playstation", "xbox", "steam", "epic",
        "netflix", "spotify", "movies", "gaming", "entertainment"
    ],
    "Bills & Utilities": [
        # Core bills keywords
        "electricity", "water", "gas", "internet", "wifi", "mobile", "phone bill",
        "rent", "emi", "loan", "insurance", "subscription", "utility",
        "maintenance", "society", "bsnl", "airtel", "jio", "tata sky",
        # Task-specific bills keywords
        "electricity", "electricity bill", "power", "MSEB", "BSES",
        "water bill", "water supply", "gas connection", "PNG", "LPG",
        "internet", "wifi", "broadband", "Jio Fiber", "Airtel Xstream",
        "mobile", "recharge", "prepaid", "postpaid", "jio", "airtel", "vi", "bsnl",
        "rent", "house rent", "office rent", "maintenance", "society",
        "insurance", "life insurance", "health insurance", "car insurance",
        "loan", "emi", "home loan", "car loan", "personal loan"
    ],
    "Healthcare": [
        # Core healthcare keywords
        "pharmacy", "medical", "hospital", "clinic", "doctor", "apollo",
        "medicine", "drug", "test", "lab", "diagnostic", "health", "wellness",
        "fortis", "max", "manipal", "pharmeasy", "netmeds", "1mg", "practo",
        # Task-specific healthcare keywords
        "hospital", "clinic", "doctor", "medical", "health", "healthcare",
        "pharmacy", "medicine", "drug", "tablet", "syrup", "prescription",
        "lab", "test", "diagnosis", "diagnostic", "pathology", "MRI", "CT scan",
        "dental", "dentist", "eye", "optical", "eyecare",
        "insurance", "health insurance", "mediclaim",
        "pharmeasy", "netmeds", "1mg", "apollo pharmacy", "medicine"
    ],
    "Education": [
        # Core education keywords
        "school", "college", "university", "tuition", "coaching", "course",
        "books", "stationery", "fees", "exam", "training", "byju", "vedantu",
        "unacademy", "coursera", "udemy", "aakash", "fiitjee", "allen",
        # Additional education keywords
        "school fees", "college fees", "tuition", "coaching", "class",
        "course", "training", "certification", "online course",
        "books", "textbook", "notebook", "stationery", "pen", "pencil",
        "exam", "test", "quiz", "assignment", "project",
        "byju", "vedantu", "unacademy", "coursera", "udemy", "skillshare",
        "library", "membership", "subscription"
    ],
    "Travel": [
        # Core travel keywords
        "hotel", "resort", "airbnb", "oyo", "booking", "goibibo", "cleartrip",
        "flight", "train", "bus", "travel", "tour", "package", "holiday",
        "vacation", "trip", "sightseeing",
        # Additional travel keywords
        "hotel", "resort", "homestay", "lodge", "airbnb", "oyo", "oyo rooms",
        "booking", "goibibo", "cleartrip", "makemytrip", "trivago",
        "flight", "airline", "air ticket", "train", "railway", "bus",
        "travel", "tour", "package", "holiday", "vacation", "trip",
        "visa", "passport", "travel insurance", "foreign exchange"
    ],
}


def categorize_transaction(description: str) -> str:
    """
    Categorize a transaction based on description using keyword matching.
    Returns category name or 'Other' if no match.
    
    The function checks for keywords in this priority order:
    1. Food & Dining
    2. Transportation
    3. Shopping
    4. Entertainment
    5. Bills & Utilities
    6. Healthcare
    7. Education
    8. Travel
    
    This ensures more specific categories are matched first.
    """
    if not description:
        return "Other"

    description_lower = description.lower().strip()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in description_lower:
                return category

    return "Other"


def extract_merchant_name(description: str) -> str:
    """
    Extract merchant name from transaction description.
    """
    if not description:
        return ""

    description_lower = description.lower()

    # Check for known merchants
    known_merchants = [
        "zomato", "swiggy", "mcdonald", "kfc", "starbucks", "domino",
        "uber", "ola", "amazon", "flipkart", "myntra", "netflix",
        "spotify", "airtel", "jio", "bsnl"
    ]

    for merchant in known_merchants:
        if merchant in description_lower:
            return merchant.title()

    # Return first word as fallback
    if description:
        words = description.split()
        if words:
            return words[0].title()

    return ""


def generate_transaction_hash(card_id: int, amount: Decimal, description: str, created_at: datetime) -> str:
    """
    Generate a unique hash for duplicate prevention.
    """
    hash_string = f"{card_id}-{amount}-{description}-{created_at.isoformat()}"
    return hashlib.sha256(hash_string.encode()).hexdigest()


# =====================================================
# RECURRING TRANSACTION DETECTION
# =====================================================

def detect_recurring(card: Card, merchant: str, amount: Decimal) -> bool:
    """
    Detect if a transaction is likely recurring.
    """
    if not merchant or not amount:
        return False

    similar_tx = CardTransaction.objects.filter(
        card=card,
        merchant_name__iexact=merchant
    ).order_by('-created_at')[:3]

    if similar_tx.count() < 2:
        return False

    amounts = [tx.amount for tx in similar_tx]
    avg_amount = sum(amounts) / len(amounts)

    if avg_amount > 0:
        variance = abs(amount - avg_amount) / avg_amount
        if variance <= 0.10:
            return True

    return False


# =====================================================
# CREDIT UTILIZATION
# =====================================================

def calculate_utilization(card: Card) -> Decimal:
    """
    Calculate credit utilization percentage for a card.
    """
    if not card.credit_limit or card.credit_limit <= 0:
        return Decimal('0.00')

    total_spent = CardTransaction.objects.filter(
        card=card,
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    utilization = (total_spent / card.credit_limit) * 100
    return round(utilization, 2)


def get_all_cards_utilization(user) -> List[Dict]:
    """
    Get utilization for all user's cards.
    """
    cards = Card.objects.filter(user=user, is_active=True)
    result = []

    for card in cards:
        utilization = calculate_utilization(card)
        result.append({
            'card': card,
            'utilization': utilization,
            'credit_limit': card.credit_limit,
            'total_spent': card.card_transactions.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
        })

    return result


# =====================================================
# MONTHLY SUMMARY
# =====================================================

def generate_monthly_summary(user, year=None, month=None) -> Dict:
    """
    Generate monthly spending summary for a user.
    """
    if year is None:
        year = timezone.now().year
    if month is None:
        month = timezone.now().month

    card_tx = CardTransaction.objects.filter(
        user=user,
        created_at__year=year,
        created_at__month=month
    )

    bank_tx = BankTransaction.objects.filter(
        user=user,
        created_at__year=year,
        created_at__month=month
    )

    card_debit = card_tx.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Handle both uppercase and lowercase transaction types
    bank_debit = bank_tx.filter(
        Q(transaction_type='DEBIT') | Q(transaction_type='debit')
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    bank_credit = bank_tx.filter(
        Q(transaction_type='CREDIT') | Q(transaction_type='credit')
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    category_breakdown = card_tx.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')

    return {
        'year': year,
        'month': month,
        'card_transactions': card_tx.count(),
        'card_debit': card_debit,
        'bank_debit': bank_debit,
        'bank_credit': bank_credit,
        'total_debit': card_debit + bank_debit,
        'total_credit': bank_credit,
        'category_breakdown': list(category_breakdown),
    }


# =====================================================
# SPENDING INSIGHTS
# =====================================================

def generate_spending_insights(user) -> Dict:
    """
    Generate spending insights and analytics.
    """
    current_month = timezone.now().month
    current_year = timezone.now().year

    last_month_date = timezone.now() - timedelta(days=30)
    last_month = last_month_date.month
    last_month_year = last_month_date.year

    current_spending = CardTransaction.objects.filter(
        user=user,
        created_at__year=current_year,
        created_at__month=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    last_spending = CardTransaction.objects.filter(
        user=user,
        created_at__year=last_month_year,
        created_at__month=last_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    if last_spending > 0:
        spending_change = ((current_spending - last_spending) / last_spending) * 100
    else:
        spending_change = 0

    top_merchants = CardTransaction.objects.filter(
        user=user
    ).values('merchant_name').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')[:5]

    top_categories = CardTransaction.objects.filter(
        user=user,
        category__isnull=False
    ).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]

    avg_transaction = CardTransaction.objects.filter(
        user=user
    ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')

    return {
        'current_month_spending': current_spending,
        'last_month_spending': last_spending,
        'spending_change_percent': round(spending_change, 2),
        'top_merchants': list(top_merchants),
        'top_categories': list(top_categories),
        'average_transaction': round(avg_transaction, 2),
    }


# =====================================================
# LARGE TRANSACTION DETECTION
# =====================================================

LARGE_TRANSACTION_THRESHOLD = Decimal('10000.00')


def detect_large_transaction(transaction: CardTransaction) -> bool:
    """
    Detect if a transaction is unusually large.
    """
    if not transaction:
        return False

    if transaction.amount >= LARGE_TRANSACTION_THRESHOLD:
        return True

    avg_amount = CardTransaction.objects.filter(
        user=transaction.user
    ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')

    if avg_amount > 0 and transaction.amount >= avg_amount * 3:
        return True

    return False


# =====================================================
# CSV IMPORT
# =====================================================

def parse_csv_transactions(csv_content: str, card: Card) -> Tuple[List[Dict], List[str]]:
    """
    Parse CSV content and return list of transactions and errors.
    Expected CSV format: date,description,amount
    """
    transactions = []
    errors = []

    try:
        content = csv_content.encode('utf-8')
    except:
        content = csv_content.encode('latin-1')

    reader = csv.DictReader(io.StringIO(content.decode('utf-8', errors='ignore')))

    for row_num, row in enumerate(reader, start=1):
        try:
            date_str = row.get('date', row.get('Date', '')).strip()
            description = row.get('description', row.get('Description', '')).strip()
            amount_str = row.get('amount', row.get('Amount', '')).strip()

            if not description or not amount_str:
                errors.append(f"Row {row_num}: Missing description or amount")
                continue

            amount_str = amount_str.replace('₹', '').replace(',', '').strip()
            try:
                amount = Decimal(amount_str)
            except:
                errors.append(f"Row {row_num}: Invalid amount '{amount_str}'")
                continue

            tx_date = timezone.now()
            if date_str:
                for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        tx_date = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue

            category = categorize_transaction(description)
            merchant = extract_merchant_name(description)
            tx_hash = generate_transaction_hash(card.id, amount, description, tx_date)

            if CardTransaction.objects.filter(transaction_hash=tx_hash).exists():
                errors.append(f"Row {row_num}: Duplicate transaction skipped")
                continue

            transactions.append({
                'date': tx_date,
                'description': description,
                'amount': amount,
                'category': category,
                'merchant_name': merchant,
                'transaction_hash': tx_hash,
            })

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    return transactions, errors


# =====================================================
# ALERTS
# =====================================================

def create_alert(user, alert_type: str, title: str, message: str):
    """
    Create an alert for the user.
    """
    Alert.objects.create(
        user=user,
        alert_type=alert_type,
        title=title,
        message=message
    )


def check_and_create_alerts(user):
    """
    Check various conditions and create alerts if needed.
    """
    cards = Card.objects.filter(user=user, is_active=True)

    for card in cards:
        if card.credit_limit and card.credit_limit > 0:
            utilization = calculate_utilization(card)
            if utilization >= 80:
                exists = Alert.objects.filter(
                    user=user,
                    alert_type='CREDIT_LIMIT',
                    is_read=False,
                    created_at__date=timezone.now().date()
                ).exists()

                if not exists:
                    create_alert(
                        user=user,
                        alert_type='CREDIT_LIMIT',
                        title='Credit Limit Warning',
                        message=f'{card.card_name} has reached {utilization}% of credit limit'
                    )

    recurring_tx = CardTransaction.objects.filter(
        user=user,
        is_recurring=True
    ).values('merchant_name').annotate(
        count=Count('id'),
        total=Sum('amount')
    )

    for tx in recurring_tx:
        if tx['count'] >= 2:
            exists = Alert.objects.filter(
                user=user,
                alert_type='RECURRING_RENEWAL',
                is_read=False,
                created_at__date=timezone.now().date()
            ).exists()

            if not exists:
                create_alert(
                    user=user,
                    alert_type='RECURRING_RENEWAL',
                    title='Recurring Payment Detected',
                    message=f'Subscription to {tx["merchant_name"]} detected ({tx["count"]} times)'
                )


def get_unread_alerts(user) -> List[Alert]:
    """
    Get all unread alerts for a user.
    """
    return Alert.objects.filter(user=user, is_read=False).order_by('-created_at')


def mark_alert_read(alert_id: int, user):
    """
    Mark an alert as read.
    """
    try:
        alert = Alert.objects.get(id=alert_id, user=user)
        alert.is_read = True
        alert.save()
        return True
    except Alert.DoesNotExist:
        return False


# =====================================================
# NET WORTH CALCULATION
# =====================================================

def calculate_net_worth(user) -> Dict:
    """
    Calculate net worth based on bank and card balances.
    """
    try:
        bank_account = BankAccount.objects.get(user=user)
        total_bank_balance = bank_account.balance
    except BankAccount.DoesNotExist:
        total_bank_balance = Decimal('0.00')

    # Handle both uppercase and lowercase transaction types
    total_card_spent = CardTransaction.objects.filter(
        user=user
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    credit_cards = Card.objects.filter(user=user, card_type='CREDIT')
    total_credit_outstanding = Decimal('0.00')

    for card in credit_cards:
        if card.credit_limit:
            spent = card.card_transactions.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            total_credit_outstanding += spent

    return {
        'total_bank_balance': total_bank_balance,
        'total_card_spent': total_card_spent,
        'total_credit_outstanding': total_credit_outstanding,
        'net_worth': total_bank_balance - total_credit_outstanding,
    }


# =====================================================
# MONEY TRANSFER SERVICES
# =====================================================

import random
import string


def generate_transaction_id() -> str:
    """Generate a unique transaction ID"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"TX{timestamp}{random_suffix}"


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def verify_pin(user, pin: str) -> bool:
    """
    Verify user's bank PIN.
    For simulation, we accept any 4-digit PIN.
    """
    if not pin or len(pin) != 4:
        return False
    # In production, this would check against a hashed PIN
    return pin.isdigit()


def verify_otp(transfer_request, otp: str) -> bool:
    """
    Verify OTP for a transfer request.
    """
    if not otp or len(otp) != 6:
        return False
    return transfer_request.otp_code == otp


def process_transfer(transfer_request) -> Dict:
    """
    Process the actual money transfer.
    Returns dict with success status and message.
    Also creates an expense entry automatically if note/description is provided.
    """
    from .models import BankAccount, BankTransaction
    
    try:
        # Get sender's account
        account = BankAccount.objects.get(user=transfer_request.sender)
        
        # Check sufficient balance
        if account.balance < transfer_request.amount:
            transfer_request.status = 'FAILED'
            transfer_request.failure_reason = 'Insufficient balance'
            transfer_request.save()
            return {
                'success': False,
                'message': 'Insufficient balance'
            }
        
        # Deduct amount from sender's account
        account.balance -= transfer_request.amount
        account.save()
        
        # Update transfer request
        transfer_request.balance_before = account.balance + transfer_request.amount
        transfer_request.balance_after = account.balance
        transfer_request.status = 'SUCCESS'
        transfer_request.processed_at = timezone.now()
        transfer_request.save()
        
        # Create bank transaction record
        receiver_name = transfer_request.beneficiary.name if transfer_request.beneficiary else transfer_request.receiver_name
        BankTransaction.objects.create(
            user=transfer_request.sender,
            amount=transfer_request.amount,
            transaction_type='DEBIT',
            description=f"Transfer to {receiver_name} - {transfer_request.transaction_id}",
            balance_after=account.balance
        )
        
        # Force recalculate and sync the bank account balance from all transactions
        from bank_simulator.signals import update_bank_account_balance_from_transactions
        update_bank_account_balance_from_transactions(transfer_request.sender)
        
        # =====================================================
        # AUTO-CREATE EXPENSE FROM TRANSFER
        # =====================================================
        # If there's a note or description, auto-categorize and create expense
        transfer_description = transfer_request.note or f"Transfer to {receiver_name}"
        
        # Import expense models
        try:
            from expenses.models import Expense
            
            # Get category from the transfer note/description using categorize_transaction
            category = categorize_transaction(transfer_description)
            
            # Create expense entry automatically
            expense = Expense.objects.create(
                owner=transfer_request.sender,
                amount=float(transfer_request.amount),
                description=transfer_description,
                category=category,
                date=timezone.now().date(),
                time=timezone.now().time().strftime('%H:%M'),
                payment_method='BANK',
                notes=f"Auto-synced from Transfer {transfer_request.transaction_id}"
            )
            print(f"Auto-created expense: {transfer_description} - {category}")
            
            # Update the transfer with linked expense ID
            transfer_request.linked_expense_id = expense.id
            transfer_request.save(update_fields=['linked_expense_id'])
            
        except ImportError as e:
            # expenses app not available, skip
            print(f"ImportError creating auto-expense: {e}")
        except Exception as e:
            # Log error but don't fail the transfer
            print(f"Error creating auto-expense: {e}")
            pass
        
        return {
            'success': True,
            'message': 'Transfer successful'
        }
        
    except BankAccount.DoesNotExist:
        transfer_request.status = 'FAILED'
        transfer_request.failure_reason = 'Bank account not found'
        transfer_request.save()
        return {
            'success': False,
            'message': 'Bank account not found'
        }
    except Exception as e:
        transfer_request.status = 'FAILED'
        transfer_request.failure_reason = str(e)
        transfer_request.save()
        return {
            'success': False,
            'message': f'Transfer failed: {str(e)}'
        }


def get_transfer_receipt(transfer_request) -> Dict:
    """
    Generate a receipt for the transfer.
    """
    return {
        'transaction_id': transfer_request.transaction_id,
        'sender': transfer_request.sender.username,
        'receiver': transfer_request.beneficiary.name if transfer_request.beneficiary else transfer_request.receiver_name,
        'amount': float(transfer_request.amount),
        'note': transfer_request.note,
        'status': transfer_request.status,
        'balance_before': float(transfer_request.balance_before),
        'balance_after': float(transfer_request.balance_after),
        'created_at': transfer_request.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'processed_at': transfer_request.processed_at.strftime('%Y-%m-%d %H:%M:%S') if transfer_request.processed_at else None,
    }
