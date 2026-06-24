from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count
from django.http import JsonResponse
from decimal import Decimal

from .models import (
    BankAccount,
    BankTransaction,
    Card,
    CardTransaction,
    Alert,
    Beneficiary,
    TransferRequest
)
from .services import (
    categorize_transaction,
    extract_merchant_name,
    generate_transaction_hash,
    calculate_utilization,
    generate_monthly_summary,
    generate_spending_insights,
    get_all_cards_utilization,
    parse_csv_transactions,
    get_unread_alerts,
    mark_alert_read,
    calculate_net_worth,
    generate_transaction_id,
    generate_otp,
    verify_pin,
    verify_otp,
    process_transfer as process_transfer_service,
    get_transfer_receipt,
)


@login_required
def bank_dashboard(request):
    # Import FinancialService for centralized calculations
    from services.financial_service import FinancialService
    
    # Get or create bank account for logged-in user
    account, created = BankAccount.objects.get_or_create(
        user=request.user,
        defaults={
            'account_number': f'ACC{request.user.id}0001',
            'balance': 0.00
        }
    )

    # Fetch cards
    cards = Card.objects.filter(user=request.user)

    # Fetch recent card transactions
    card_transactions = (
        CardTransaction.objects
        .filter(user=request.user)
        .order_by('-created_at')[:10]
    )

    # Card spending analytics
    card_stats = (
        CardTransaction.objects
        .filter(user=request.user)
        .values('card__card_name')
        .annotate(total_spent=Sum('amount'))
    )

    # PHASE 4 & 7: Enhanced data for dashboard
    cards_utilization = get_all_cards_utilization(request.user)
    monthly_summary = generate_monthly_summary(request.user)
    spending_insights = generate_spending_insights(request.user)
    unread_alerts = get_unread_alerts(request.user)[:5]
    net_worth = calculate_net_worth(request.user)

    # Fetch bank transactions and transfers for recent activity
    bank_transactions = BankTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    transfers = TransferRequest.objects.filter(
        sender=request.user
    ).order_by('-created_at')[:10]

    # Top merchants
    top_merchants = (
        CardTransaction.objects
        .filter(user=request.user)
        .exclude(merchant_name='')
        .values('merchant_name')
        .annotate(total=Sum('amount'), count=Sum('amount'))
        .order_by('-total')[:5]
    )

    # Recurring subscriptions
    recurring_transactions = (
        CardTransaction.objects
        .filter(user=request.user, is_recurring=True)
        .values('merchant_name')
        .annotate(
            count=Sum('amount'),
            total=Sum('amount'),
            last_date=Max('created_at')
        )
    )

    # Get centralized financial totals using FinancialService (ALWAYS recalculate from DB)
    financial_totals = FinancialService.calculate_net_worth(request.user)
    monthly_financial = FinancialService.calculate_monthly_summary(request.user)

    # Handle bank debit / credit
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        transaction_type = request.POST.get('transaction_type')
        description = request.POST.get('description')

        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero')
            return redirect('bank-dashboard')

        # CREDIT
        if transaction_type == 'CREDIT':
            account.balance += amount

        # DEBIT
        elif transaction_type == 'DEBIT':
            if account.balance < amount:
                messages.error(request, 'Insufficient balance')
                return redirect('bank-dashboard')
            account.balance -= amount

        account.save()

        # Create bank transaction (triggers signal)
        BankTransaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            balance_after=account.balance
        )

        # Force recalculate and sync the bank account balance from all transactions
        from bank_simulator.signals import update_bank_account_balance_from_transactions
        update_bank_account_balance_from_transactions(request.user)

        messages.success(request, f'{transaction_type} successful')
        return redirect('bank-dashboard')

    return render(request, 'bank_simulator/bank_dashboard.html', {
        'account': account,
        'cards': cards,
        'card_transactions': card_transactions,
        'card_stats': card_stats,
        # PHASE 4 new data
        'cards_utilization': cards_utilization,
        'monthly_summary': monthly_summary,
        'spending_insights': spending_insights,
        'unread_alerts': unread_alerts,
        'net_worth': net_worth,
        'top_merchants': top_merchants,
        'recurring_transactions': recurring_transactions,
        'bank_transactions': bank_transactions,
        'transfers': transfers,
        # Centralized Financial Totals from FinancialService (always from DB, never cached)
        'total_income': financial_totals.get('total_income', 0),
        'total_expenses': financial_totals.get('total_expenses', 0),
        'card_spending': financial_totals.get('card_spending', 0),
        'bank_balance': financial_totals.get('bank_balance', 0),
        'net_worth_calculated': financial_totals.get('net_worth', 0),
        'monthly_income': monthly_financial.get('income', {}).get('total', 0),
        'monthly_expenses': monthly_financial.get('expenses', {}).get('total', 0),
        'monthly_card_spending': monthly_financial.get('card_spending', {}).get('total', 0),
    })


@login_required
@require_POST
def add_card(request):
    Card.objects.create(
        user=request.user,
        card_name=request.POST.get('card_name'),
        card_type=request.POST.get('card_type'),
        last_four_digits=request.POST.get('last_four_digits'),
        limit=request.POST.get('limit') or None,
        # PHASE 1: Enhanced card fields
        bank_name=request.POST.get('bank_name', ''),
        card_brand=request.POST.get('card_brand', 'OTHER'),
        credit_limit=request.POST.get('credit_limit') or None,
        due_date=request.POST.get('due_date') or None,
        is_active=True,
    )

    messages.success(request, "Card added successfully")
    return redirect('bank-dashboard')


@login_required
@require_POST
def card_swipe(request):
    card = Card.objects.get(
        id=request.POST.get('card_id'),
        user=request.user
    )

    amount = Decimal(request.POST.get('amount'))
    description = request.POST.get('description')

    # Auto-categorize and extract merchant
    category = categorize_transaction(description)
    merchant = extract_merchant_name(description)
    tx_hash = generate_transaction_hash(card.id, amount, description, timezone.now())

    CardTransaction.objects.create(
        card=card,
        user=request.user,
        amount=amount,
        description=description,
        category=category,
        merchant_name=merchant,
        transaction_hash=tx_hash,
        source_type='SIMULATED',
    )

    messages.success(
        request,
        f"Card payment done using {card.card_name}"
    )
    return redirect('bank-dashboard')


# PHASE 5: CSV Import
@login_required
def csv_import(request):
    """Handle CSV import for card transactions."""
    if request.method == 'GET':
        cards = Card.objects.filter(user=request.user)
        return render(request, 'bank_simulator/csv_import.html', {
            'cards': cards
        })

    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        csv_file = request.FILES.get('csv_file')

        if not card_id or not csv_file:
            messages.error(request, 'Please select a card and upload a CSV file')
            return redirect('csv-import')

        try:
            card = Card.objects.get(id=card_id, user=request.user)
        except Card.DoesNotExist:
            messages.error(request, 'Invalid card selected')
            return redirect('csv-import')

        # Read CSV content
        try:
            csv_content = csv_file.read().decode('utf-8')
        except UnicodeDecodeError:
            csv_content = csv_file.read().decode('latin-1')

        # Parse CSV
        transactions, errors = parse_csv_transactions(csv_content, card)

        # Create transactions
        created_count = 0
        for tx_data in transactions:
            CardTransaction.objects.create(
                card=card,
                user=request.user,
                amount=tx_data['amount'],
                description=tx_data['description'],
                category=tx_data['category'],
                merchant_name=tx_data['merchant_name'],
                transaction_hash=tx_data['transaction_hash'],
                source_type='CSV_IMPORT',
            )
            created_count += 1

        # Show results
        if created_count > 0:
            messages.success(request, f'Successfully imported {created_count} transactions')
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                messages.warning(request, error)

        return redirect('bank-dashboard')


# PHASE 6: Alerts Management
@login_required
def alerts(request):
    """Show all alerts for the user."""
    alerts = Alert.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'bank_simulator/alerts.html', {
        'alerts': alerts
    })


@login_required
@require_POST
def mark_alert_as_read(request):
    """Mark an alert as read."""
    alert_id = request.POST.get('alert_id')
    if mark_alert_read(alert_id, request.user):
        messages.success(request, 'Alert marked as read')
    else:
        messages.error(request, 'Alert not found')
    return redirect('alerts')


@login_required
@require_POST
def mark_all_alerts_read(request):
    """Mark all alerts as read."""
    Alert.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All alerts marked as read')
    return redirect('alerts')


# Import timezone for transaction hash
from django.utils import timezone
from django.db.models import Max

# Import integration functions
from .integration import (
    sync_all_bank_transactions,
    auto_sync_new_transactions,
    update_bank_account_balance,
    get_combined_monthly_summary,
    get_dashboard_analytics,
    get_combined_transaction_history,
    get_monthly_income_summary,
    get_monthly_expense_summary,
    calculate_total_net_worth,
    get_category_totals,
)


# =====================================================
# API Views for Bank Transaction Integration
# =====================================================

@login_required
def sync_bank_api(request):
    """
    API endpoint to sync bank transactions with expenses/income.
    Call this after inserting transactions via phpMyAdmin.
    """
    if request.method == 'POST':
        results = sync_all_bank_transactions(user=request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Sync complete: {results['synced']} transactions synced",
                'results': results
            })
        
        messages.success(request, f"Sync complete: {results['synced']} transactions synced")
        return redirect('bank-dashboard')
    
    return JsonResponse({'error': 'POST request required'}, status=400)


@login_required
def sync_all_users_api(request):
    """
    API endpoint to sync all users' bank transactions.
    Admin only.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    if request.method == 'POST':
        results = sync_all_bank_transactions()
        
        return JsonResponse({
            'success': True,
            'message': f"Sync complete: {results['synced']} transactions synced",
            'results': results
        })
    
    return JsonResponse({'error': 'POST request required'}, status=400)


@login_required
def auto_sync_api(request):
    """
    API endpoint for auto-sync (check and sync new transactions).
    Can be called periodically via JavaScript or cron.
    """
    if request.method == 'POST' or request.method == 'GET':
        results = auto_sync_new_transactions()
        
        return JsonResponse({
            'success': True,
            'results': results
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def update_balance_api(request):
    """
    API endpoint to update bank account balance.
    """
    if request.method == 'POST':
        balance = update_bank_account_balance(request.user)
        
        return JsonResponse({
            'success': True,
            'balance': float(balance),
            'message': f'Bank balance updated to ₹{balance}'
        })
    
    return JsonResponse({'error': 'POST request required'}, status=400)


@login_required
def monthly_summary_api(request):
    """
    API endpoint to get monthly summary data.
    """
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year:
        year = int(year)
    if month:
        month = int(month)
    
    summary = get_combined_monthly_summary(request.user, year, month)
    
    return JsonResponse({
        'success': True,
        'summary': summary
    })


@login_required
def dashboard_analytics_api(request):
    """
    API endpoint to get dashboard analytics.
    """
    period = request.GET.get('period', 'month')
    
    analytics = get_dashboard_analytics(request.user, period)
    
    return JsonResponse({
        'success': True,
        'analytics': analytics
    })


@login_required
def transaction_history_api(request):
    """
    API endpoint to get combined transaction history.
    """
    limit = request.GET.get('limit', 50)
    try:
        limit = int(limit)
    except ValueError:
        limit = 50
    
    history = get_combined_transaction_history(request.user, limit)
    
    # Convert datetime to string for JSON serialization
    for item in history:
        item['date'] = item['date'].isoformat() if item['date'] else None
    
    return JsonResponse({
        'success': True,
        'transactions': history
    })


@login_required
def net_worth_api(request):
    """
    API endpoint to get net worth calculation.
    """
    net_worth = calculate_total_net_worth(request.user)
    
    return JsonResponse({
        'success': True,
        'net_worth': net_worth
    })


@login_required
def category_totals_api(request):
    """
    API endpoint to get category totals.
    """
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year:
        year = int(year)
    if month:
        month = int(month)
    
    totals = get_category_totals(request.user, year, month)
    
    return JsonResponse({
        'success': True,
        'categories': totals
    })


# =====================================================
# NEW BANKING PAGES VIEWS
# =====================================================

@login_required
def send_money(request):
    """Send Money - Step 1: Select recipient and enter amount"""
    # Get user's bank account
    try:
        account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        account = BankAccount.objects.create(
            user=request.user,
            account_number=f'ACC{request.user.id}0001',
            balance=0.00
        )
    
    # Get saved beneficiaries
    beneficiaries = Beneficiary.objects.filter(user=request.user, is_active=True)
    
    # Handle form submission
    if request.method == 'POST':
        beneficiary_id = request.POST.get('beneficiary_id')
        amount = request.POST.get('amount')
        note = request.POST.get('note', '')
        
        # Check if adding new beneficiary
        if request.POST.get('add_beneficiary'):
            name = request.POST.get('new_name')
            account_number = request.POST.get('new_account')
            upi_id = request.POST.get('new_upi')
            phone = request.POST.get('new_phone')
            
            beneficiary = Beneficiary.objects.create(
                user=request.user,
                name=name,
                account_number=account_number,
                upi_id=upi_id,
                phone=phone,
                is_verified=True
            )
            messages.success(request, f'Beneficiary {name} added successfully')
            return redirect('send-money')
        
        if not beneficiary_id or not amount:
            messages.error(request, 'Please select a beneficiary and enter amount')
            return redirect('send-money')
        
        try:
            beneficiary = Beneficiary.objects.get(id=beneficiary_id, user=request.user)
        except Beneficiary.DoesNotExist:
            messages.error(request, 'Invalid beneficiary')
            return redirect('send-money')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero')
                return redirect('send-money')
        except:
            messages.error(request, 'Invalid amount')
            return redirect('send-money')
        
        # Check sufficient balance
        if account.balance < amount:
            messages.error(request, 'Insufficient balance')
            return redirect('send-money')
        
        # Create transfer request and redirect to confirmation
        transfer = TransferRequest.objects.create(
            transaction_id=generate_transaction_id(),
            sender=request.user,
            beneficiary=beneficiary,
            amount=amount,
            note=note,
            transfer_type='BENEFICIARY',
            balance_before=account.balance,
            status='PENDING'
        )
        
        return redirect('confirm-transfer', transfer_id=transfer.id)
    
    return render(request, 'bank_simulator/send_money.html', {
        'account': account,
        'beneficiaries': beneficiaries,
    })


@login_required
def confirm_transfer(request, transfer_id):
    """Send Money - Step 2: Confirm transfer details"""
    try:
        transfer = TransferRequest.objects.get(id=transfer_id, sender=request.user)
    except TransferRequest.DoesNotExist:
        messages.error(request, 'Transfer not found')
        return redirect('send-money')
    
    if transfer.status != 'PENDING':
        messages.error(request, 'This transfer has already been processed')
        return redirect('bank-dashboard')
    
    # Get account for balance display
    account = BankAccount.objects.get(user=request.user)
    
    if request.method == 'POST':
        # Confirm and proceed to processing
        transfer.status = 'CONFIRMED'
        transfer.save()
        return redirect('process-transfer', transfer_id=transfer.id)
    
    return render(request, 'bank_simulator/confirm_transfer.html', {
        'transfer': transfer,
        'account': account,
    })


@login_required
def process_transfer(request, transfer_id):
    """Send Money - Step 3: PIN verification and processing"""
    try:
        transfer = TransferRequest.objects.get(id=transfer_id, sender=request.user)
    except TransferRequest.DoesNotExist:
        messages.error(request, 'Transfer not found')
        return redirect('send-money')
    
    if request.method == 'POST':
        pin = request.POST.get('pin', '')
        
        # Verify PIN (accept any 4-digit PIN for simulation)
        if not verify_pin(request.user, pin):
            messages.error(request, 'Invalid PIN. Please enter a 4-digit PIN.')
            return redirect('process-transfer', transfer_id=transfer.id)
        
        # Mark as PIN verified
        transfer.pin_verified = True
        transfer.status = 'PROCESSING'
        transfer.save()
        
        # Process the transfer
        result = process_transfer_service(transfer)
        
        if result['success']:
            return redirect('transfer-success', transfer_id=transfer.id)
        else:
            return redirect('transfer-failed', transfer_id=transfer.id)
    
    return render(request, 'bank_simulator/processing.html', {
        'transfer': transfer,
    })


@login_required
def transfer_success(request, transfer_id):
    """Send Money - Step 4: Success page with receipt"""
    try:
        transfer = TransferRequest.objects.get(id=transfer_id, sender=request.user)
    except TransferRequest.DoesNotExist:
        messages.error(request, 'Transfer not found')
        return redirect('bank-dashboard')
    
    receipt = get_transfer_receipt(transfer)
    
    return render(request, 'bank_simulator/transfer_success.html', {
        'transfer': transfer,
        'receipt': receipt,
    })


@login_required
def transfer_failed(request, transfer_id):
    """Send Money - Step 5: Failed page"""
    try:
        transfer = TransferRequest.objects.get(id=transfer_id, sender=request.user)
    except TransferRequest.DoesNotExist:
        messages.error(request, 'Transfer not found')
        return redirect('bank-dashboard')
    
    return render(request, 'bank_simulator/transfer_failed.html', {
        'transfer': transfer,
    })


@login_required
def transaction_history(request):
    """Transaction History Page"""
    # Get user's bank account
    try:
        account = BankAccount.objects.get(user=request.user)
    except BankAccount.DoesNotExist:
        account = None
    
    # Get all bank transactions
    bank_transactions = BankTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]
    
    # Get all transfer requests
    transfers = TransferRequest.objects.filter(
        sender=request.user
    ).order_by('-created_at')[:50]
    
    return render(request, 'bank_simulator/transaction_history.html', {
        'account': account,
        'bank_transactions': bank_transactions,
        'transfers': transfers,
    })


@login_required
def cards_view(request):
    """Cards Management Page"""
    cards = Card.objects.filter(user=request.user)
    cards_utilization = get_all_cards_utilization(request.user)
    
    return render(request, 'bank_simulator/cards.html', {
        'cards': cards,
        'cards_utilization': cards_utilization,
    })


@login_required
def card_transactions_view(request, card_id):
    """Card Transactions Page"""
    try:
        card = Card.objects.get(id=card_id, user=request.user)
    except Card.DoesNotExist:
        messages.error(request, 'Card not found')
        return redirect('cards-view')
    
    transactions = CardTransaction.objects.filter(
        card=card
    ).order_by('-transaction_date')[:50]
    
    return render(request, 'bank_simulator/card_transactions.html', {
        'card': card,
        'transactions': transactions,
    })


@login_required
def analytics_view(request):
    """Spending Analytics Page"""
    monthly_summary = generate_monthly_summary(request.user)
    spending_insights = generate_spending_insights(request.user)
    cards_utilization = get_all_cards_utilization(request.user)
    
    return render(request, 'bank_simulator/analytics.html', {
        'monthly_summary': monthly_summary,
        'spending_insights': spending_insights,
        'cards_utilization': cards_utilization,
    })


@login_required
def merchants_view(request):
    """Merchant Insights Page"""
    # Get merchant spending data
    merchants = CardTransaction.objects.filter(
        user=request.user
    ).exclude(merchant_name='').values(
        'merchant_name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:20]
    
    # Get recurring subscriptions
    recurring = CardTransaction.objects.filter(
        user=request.user,
        is_recurring=True
    ).values('merchant_name').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    return render(request, 'bank_simulator/merchants.html', {
        'merchants': merchants,
        'recurring': recurring,
    })


@login_required
def beneficiaries_view(request):
    """Manage Beneficiaries Page"""
    beneficiaries = Beneficiary.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-created_at')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        account_number = request.POST.get('account_number', '')
        upi_id = request.POST.get('upi_id', '')
        phone = request.POST.get('phone', '')
        
        Beneficiary.objects.create(
            user=request.user,
            name=name,
            account_number=account_number,
            upi_id=upi_id,
            phone=phone,
            is_verified=True
        )
        messages.success(request, f'Beneficiary {name} added successfully')
        return redirect('beneficiaries')
    
    return render(request, 'bank_simulator/beneficiaries.html', {
        'beneficiaries': beneficiaries,
    })


@login_required
@require_POST
def delete_beneficiary(request):
    """Delete a beneficiary"""
    beneficiary_id = request.POST.get('beneficiary_id')
    try:
        beneficiary = Beneficiary.objects.get(id=beneficiary_id, user=request.user)
        beneficiary.is_active = False
        beneficiary.save()
        messages.success(request, 'Beneficiary removed')
    except Beneficiary.DoesNotExist:
        messages.error(request, 'Beneficiary not found')
    
    return redirect('beneficiaries')
