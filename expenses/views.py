from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Expense, ExpenseLimit
from userincome.models import UserIncome
from userpreferences.models import Notification
from .forms import ExpenseForm
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
import datetime
from datetime import timedelta, date
import json


def create_notification(user, title, message, notification_type='info', event_type=None):
    """Helper function to create a notification"""
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type,
        event_type=event_type,
    )


# ================= OVERVIEW (Original Dashboard) =================
@login_required(login_url='/authentication/login')
def overview(request):
    # Import DashboardService inside function to avoid any import issues
    from services.dashboard_service import DashboardService
    from services.financial_service import FinancialService
    
    # Get the period parameter from request (default: month)
    period = request.GET.get('period', 'month')
    
    # Validate period
    valid_periods = ['week', 'month', 'quarter', 'year']
    if period not in valid_periods:
        period = 'month'
    
    # Get expenses for the logged-in user
    expenses = Expense.objects.filter(owner=request.user).order_by('-date')
    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get expense count and total for display
    expense_count = expenses.count()
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Debug logging
    print("Expenses:", expense_count)
    print("Total Expenses:", total_expenses)
    print("Period:", period)
    
    # Get dashboard analytics using DashboardService with period parameter
    dashboard_data = DashboardService.get_dashboard_data(request.user, period=period)
    
    # Get currency symbol for the user
    from userpreferences.currency_service import CurrencyService
    currency_symbol = CurrencyService.get_currency_symbol(request.user)
    
    # Print debug info for goals
    from goals.models import Goal
    user_goals = Goal.objects.filter(owner=request.user)
    print("Goals count:", user_goals.count())
    
    # Get centralized financial totals using FinancialService (ALWAYS recalculate from DB)
    financial_totals = FinancialService.calculate_net_worth(request.user)
    monthly_summary = FinancialService.calculate_monthly_summary(request.user)
    
    context = {
        "expenses": expenses,
        "page_obj": page_obj,
        "expense_count": expense_count,
        "total_expenses": total_expenses,
        "current_period": period,  # Pass period to template
        
        # Dashboard analytics from DashboardService
        "financial_health": dashboard_data.get("financial_health"),
        "spending_vs_income": dashboard_data.get("spending_vs_income"),
        "budget_utilization": dashboard_data.get("budget_utilization"),
        "category_breakdown": dashboard_data.get("category_breakdown"),
        "trend_data": dashboard_data.get("trend_data"),
        "trend_data_json": json.dumps(dashboard_data.get("trend_data", {
            'daily': [],
            'moving_avg_7': []
        })),
        "ai_insights": dashboard_data.get("ai_insights"),
        "savings_goals": dashboard_data.get("savings_goals"),
        "activity_timeline": dashboard_data.get("activity_timeline"),
        "predictions": dashboard_data.get("predictions"),
        
        # NEW: Advanced AI Insights
        "advanced_ai_insights": dashboard_data.get("advanced_ai_insights"),
        
        # Currency
        "currency_symbol": currency_symbol,
        
        # Centralized Financial Totals from FinancialService (always from DB, never cached)
        "total_income": financial_totals.get('total_income', 0),
        "total_expenses_calculated": financial_totals.get('total_expenses', 0),
        "card_spending": financial_totals.get('card_spending', 0),
        "bank_balance": financial_totals.get('bank_balance', 0),
        "net_worth": financial_totals.get('net_worth', 0),
        "monthly_income": monthly_summary.get('income', {}).get('total', 0),
        "monthly_expenses": monthly_summary.get('expenses', {}).get('total', 0),
        "monthly_card_spending": monthly_summary.get('card_spending', {}).get('total', 0),
    }
    
    # Check if this is the financial intelligence page
    if request.GET.get('view') == 'intelligence':
        return render(request, 'expenses/financial_intelligence.html', context)
    else:
        return render(request, 'expenses/overview.html', context)


# ================= FINANCIAL INTELLIGENCE DASHBOARD (NEW) =================
@login_required(login_url='/authentication/login')
def financial_intelligence(request):
    """
    Financial Intelligence Dashboard - Main page
    """
    from services.dashboard_service import DashboardService
    from userpreferences.currency_service import CurrencyService
    
    # Get period from request (default: month)
    period = request.GET.get('period', 'month')
    valid_periods = ['week', 'month', 'quarter', 'year']
    if period not in valid_periods:
        period = 'month'
    
    # Get currency symbol
    currency_symbol = CurrencyService.get_currency_symbol(request.user)
    
    # Get dashboard data
    dashboard_data = DashboardService.get_dashboard_data(request.user, period=period)
    
    # Calculate date range text for display
    today = timezone.now().date()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
        date_range_text = f"{start_date.strftime('%b %d')} - {today.strftime('%b %d, %Y')}"
    elif period == 'month':
        start_date = today.replace(day=1)
        date_range_text = start_date.strftime('%B %Y')
    elif period == 'quarter':
        quarter = (today.month - 1) // 3 + 1
        date_range_text = f"Q{quarter} {today.year}"
    else:  # year
        date_range_text = str(today.year)
    
    # Prepare trend data JSON
    trend_data = dashboard_data.get("trend_data", {
        'daily': [],
        'moving_avg_7': []
    })
    
    # Ensure daily items have labels
    if trend_data.get('daily'):
        for item in trend_data['daily']:
            if 'label' not in item and 'date' in item:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(item['date'], '%Y-%m-%d')
                    item['label'] = date_obj.strftime('%b %d')
                except:
                    item['label'] = item['date']
    
    # Prepare context
    context = {
        # Page info
        "page_title": "Financial Intelligence Dashboard",
        "current_period": period,
        "date_range_text": date_range_text,
        "currency_symbol": currency_symbol,
        
        # Core metrics
        "financial_health": dashboard_data.get("financial_health", {
            'score': 0,
            'explanation': 'No data available',
            'income_score': 0,
            'budget_score': 0,
            'savings_score': 0,
            'volatility_score': 0
        }),
        
        "spending_vs_income": dashboard_data.get("spending_vs_income", {
            'income': {'current': 0, 'change': 0},
            'expenses': {'current': 0, 'change': 0},
            'savings': {'current': 0, 'change': 0}
        }),
        
        "budget_utilization": dashboard_data.get("budget_utilization", {}),
        "category_breakdown": dashboard_data.get("category_breakdown", {}),
        "ai_insights": dashboard_data.get("ai_insights", {}),
        "savings_goals": dashboard_data.get("savings_goals", {'has_goals': False, 'goals': []}),
        "activity_timeline": dashboard_data.get("activity_timeline", {}),
        "predictions": dashboard_data.get("predictions", {}),
        
        # Chart data (JSON serialized)
        "trend_data_json": json.dumps(trend_data),
    }
    
    return render(request, 'expenses/financial_intelligence.html', context)
# ================= STATS =================
@login_required(login_url='/authentication/login')
def stats(request):
    from .models import Expense
    from .prediction_service import PredictionService
    import json
    
    # Get currency symbol for the user
    from userpreferences.currency_service import CurrencyService
    currency_symbol = CurrencyService.get_currency_symbol(request.user)
    
    expenses = Expense.objects.filter(owner=request.user)
    
    # Calculate total expenses
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get expenses by category
    category_data = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    
    # Check if user has expenses
    has_expenses = expenses.exists()
    
    # Prepare data for chart - convert to list
    categories = [item['category'] for item in category_data]
    amounts = [float(item['total']) for item in category_data]
    
    # Get monthly expenses
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_expenses = expenses.filter(date__month=current_month, date__year=current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # ================= NEW: RECENT EXPENSES (Last 10) =================
    # Use values() but keep date as date object for template rendering
    # We'll create two versions: one for template, one for JSON
    recent_expenses_query = expenses.order_by('-date', '-id')[:10]
    
    # For template - keep date as date object
    recent_expenses = []
    for expense in recent_expenses_query:
        recent_expenses.append({
            'id': expense.id,
            'amount': expense.amount,
            'date': expense.date,  # Keep as date object for template
            'category': expense.category,
            'description': expense.description,
        })
    
    # For JSON - convert date to string
    recent_expenses_json_list = []
    for expense in recent_expenses_query:
        recent_expenses_json_list.append({
            'id': expense.id,
            'amount': float(expense.amount),
            'date': expense.date.strftime('%Y-%m-%d'),  # String for JSON
            'category': expense.category,
            'description': expense.description,
        })
    
    recent_expenses_json = json.dumps(recent_expenses_json_list)
    
    # ================= NEW: MONTHLY EXPENSES TREND (Last 6 months) =================
    monthly_expenses_list = []
    today = timezone.now().date()
    
    # Use proper month calculation to avoid duplicates
    import calendar
    for i in range(5, -1, -1):  # Last 6 months
        # Calculate the first day of the month i months ago
        current_month = today.month
        current_year = today.year
        
        # Calculate target month and year
        target_month = current_month - i
        target_year = current_year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        # Get first and last day of target month
        first_day = date(target_year, target_month, 1)
        last_day = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])
        
        # Get expenses for this month
        month_expenses = expenses.filter(
            date__gte=first_day,
            date__lte=last_day
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        monthly_expenses_list.append({
            'month': first_day.strftime('%b %Y'),
            'month_short': first_day.strftime('%b'),
            'year': target_year,
            'month_num': target_month,
            'amount': float(month_expenses)
        })
    
    # Remove duplicates if any (by month)
    seen = set()
    unique_monthly_expenses = []
    for item in monthly_expenses_list:
        key = (item['year'], item['month_num'])
        if key not in seen:
            seen.add(key)
            unique_monthly_expenses.append(item)
    
    monthly_expenses_list = unique_monthly_expenses
    
    # ================= NEW: HIGHEST EXPENSE CATEGORY =================
    highest_category = None
    if category_data:
        top_category = category_data[0]
        highest_category = {
            'name': top_category['category'],
            'amount': float(top_category['total']),
            'percentage': round((top_category['total'] / total_expenses * 100) if total_expenses > 0 else 0, 1)
        }
    
    # ================= NEW: AVERAGE MONTHLY SPENDING (Last 6 months) =================
    # Calculate from actual expenses in the last 6 months only
    six_months_ago = today - timedelta(days=180)
    last_6_month_expenses = expenses.filter(date__gte=six_months_ago)
    total_last_6_months = last_6_month_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    average_monthly_spending = round(total_last_6_months / 6, 2)
    
    # ================= NEW: CATEGORY BREAKDOWN TABLE =================
    category_breakdown_table = []
    for item in category_data:
        category_breakdown_table.append({
            'name': item['category'],
            'amount': float(item['total']),
            'percentage': round((item['total'] / total_expenses * 100) if total_expenses > 0 else 0, 1)
        })
    
    # Monthly expenses JSON for chart
    monthly_expenses_json = json.dumps(monthly_expenses_list)
    category_breakdown_json = json.dumps(category_breakdown_table)
    
    # Debug output
    print("=" * 50)
    print("STATS DEBUG:")
    print(f"User: {request.user}")
    print(f"Total expenses: {total_expenses}")
    print(f"Has expenses: {has_expenses}")
    print(f"Categories: {categories}")
    print(f"Amounts: {amounts}")
    print(f"Recent expenses count: {len(recent_expenses)}")
    print(f"Monthly trend: {monthly_expenses_list}")
    print(f"Highest category: {highest_category}")
    print(f"Average monthly: {average_monthly_spending}")
    print("=" * 50)
    
    context = {
        'total_expenses': total_expenses,
        'monthly_expenses': monthly_expenses,
        'category_data': list(category_data),
        'has_expenses': has_expenses,
        'categories_json': json.dumps(categories),
        'amounts_json': json.dumps(amounts),
        
        # NEW CONTEXT VARIABLES
        'currency_symbol': currency_symbol,
        'recent_expenses': recent_expenses,
        'recent_expenses_json': recent_expenses_json,
        'monthly_expenses_list': monthly_expenses_list,
        'monthly_expenses_json': monthly_expenses_json,
        'highest_category': highest_category,
        'average_monthly_spending': average_monthly_spending,
        'category_breakdown_table': category_breakdown_table,
        'category_breakdown_json': category_breakdown_json,
        
        # Next Month Expense Prediction
        'next_month_expense_prediction': PredictionService.get_predictions(request.user),
    }
    return render(request, 'expenses/stats.html', context)


# ================= INDEX (Main Expense List) =================
@login_required(login_url='/authentication/login')
def index(request):
    # Get sort parameter from URL
    sort_param = request.GET.get('sort', 'date_desc')
    
    # Build the base queryset
    expenses = Expense.objects.filter(owner=request.user)
    
    # Apply sorting based on sort parameter
    if sort_param == 'date_asc':
        expenses = expenses.order_by('date', 'id')
    elif sort_param == 'date_desc':
        expenses = expenses.order_by('-date', '-id')
    elif sort_param == 'time_asc':
        expenses = expenses.order_by('date', 'time', 'id')
    elif sort_param == 'time_desc':
        expenses = expenses.order_by('-date', '-time', '-id')
    else:
        # Default: newest first
        expenses = expenses.order_by('-date', '-id')
    
    paginator = Paginator(expenses, 10)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    
    # Get expense limit - use 'owner' not 'user' as per model
    # Wrap in try-except to handle database migration issues
    try:
        expense_limit = ExpenseLimit.objects.filter(owner=request.user).first()
    except Exception:
        expense_limit = None
    
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'expense_limit': expense_limit,
        'current_sort': sort_param,
    }
    return render(request, 'expenses/index.html', context)


# ================= ADD EXPENSE =================
@login_required(login_url='/authentication/login')
def add_expense(request):
    current_time = timezone.now()
    
    if request.method == 'POST':
        # IMPORTANT: Pass request.FILES for receipt upload support
        form = ExpenseForm(request.POST, request.FILES)
        
        # Debug: Print form errors to console
        if not form.is_valid():
            print("=== FORM ERRORS ===")
            print(form.errors)
            print("===================")
        
        if form.is_valid():
            expense = form.save(commit=False)
            expense.owner = request.user
            expense.save()
            
            # Create notification for expense added
            create_notification(
                user=request.user,
                title="Expense Added",
                message=f"Expense of {expense.amount} for {expense.category} has been added successfully.",
                notification_type='success',
                event_type='expense_added'
            )
            
            # Check daily limit after adding expense
            try:
                from userpreferences.currency_service import CurrencyService
                currency_symbol = CurrencyService.get_currency_symbol(request.user)
                
                # Get today's expenses
                today = timezone.now().date()
                today_expenses = Expense.objects.filter(
                    owner=request.user,
                    date__date=today
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                # Get user's daily limit
                expense_limit = ExpenseLimit.objects.filter(owner=request.user).first()
                if expense_limit and expense_limit.daily_expense_limit > 0:
                    if today_expenses > expense_limit.daily_expense_limit:
                        # Create warning notification for limit exceeded
                        create_notification(
                            user=request.user,
                            title="Daily Limit Exceeded",
                            message=f"You've exceeded your daily expense limit of {currency_symbol}{expense_limit.daily_expense_limit}. Today's total: {currency_symbol}{today_expenses}",
                            notification_type='warning',
                            event_type='daily_limit_exceeded'
                        )
                    elif today_expenses >= (expense_limit.daily_expense_limit * 0.8):
                        # Create warning at 80% threshold
                        create_notification(
                            user=request.user,
                            title="Approaching Daily Limit",
                            message=f"You've reached 80% of your daily expense limit. Used: {currency_symbol}{today_expenses}/{currency_symbol}{expense_limit.daily_expense_limit}",
                            notification_type='warning',
                            event_type='daily_limit_80'
                        )
            except Exception as e:
                print(f"Error checking daily limit: {e}")
            
            return redirect('dashboard')
    else:
        form = ExpenseForm()
    
    return render(request, 'expenses/add_expense.html', {
        'form': form,
        'current_time': current_time
        }
    )


# ================= EDIT EXPENSE =================
@login_required(login_url='/authentication/login')
def expense_edit(request, id):
    expense = Expense.objects.get(id=id, owner=request.user)
    
    if request.method == 'POST':
        # IMPORTANT: Pass request.FILES for receipt upload support
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        
        # Debug: Print form errors to console
        if not form.is_valid():
            print("=== FORM ERRORS ===")
            print(form.errors)
            print("===================")
        
        if form.is_valid():
            # Save the form first
            expense = form.save(commit=False)
            
            # If time is not provided in the form, keep the existing time
            # The form will handle the time field automatically if it's included
            
            # Save the expense
            expense.save()
            
            # Create notification for expense updated
            create_notification(
                user=request.user,
                title="Expense Updated",
                message=f"Expense has been updated to {expense.amount} for {expense.category}.",
                notification_type='success',
                event_type='expense_updated'
            )
            
            return redirect('dashboard')
    else:
        form = ExpenseForm(instance=expense)
    
    return render(request, 'expenses/edit-expense.html', {'form': form, 'expense': expense})
# ================= DELETE EXPENSE =================
@login_required(login_url='/authentication/login')
def delete_expense(request, id):
    expense = Expense.objects.get(id=id, owner=request.user)
    
    # Store expense details before deleting for notification
    expense_amount = expense.amount
    expense_category = expense.category
    
    expense.delete()
    
    # Create notification for expense deleted
    create_notification(
        user=request.user,
        title="Expense Deleted",
        message=f"Expense of {expense_amount} for {expense_category} has been deleted.",
        notification_type='info',
        event_type='expense_deleted'
    )
    
    return redirect('dashboard')


# ================= SEARCH EXPENSES =================
@login_required(login_url='/authentication/login')
@csrf_exempt
def search_expenses(request):
    if request.method == 'POST':
        search_text = request.POST.get('search_text', '')
        
        if search_text:
            expenses = Expense.objects.filter(
                owner=request.user,
                description__icontains=search_text
            ) | Expense.objects.filter(
                owner=request.user,
                category__icontains=search_text
            )
        else:
            expenses = Expense.objects.filter(owner=request.user)
        
        # Convert to list for JSON serialization
        expense_list = []
        for expense in expenses:
            expense_list.append({
                'id': expense.id,
                'description': expense.description,
                'amount': str(expense.amount),
                'category': expense.category,
                'date': expense.date.strftime('%Y-%m-%d'),
            })
        
        return JsonResponse(expense_list, safe=False)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ================= EXPENSE CATEGORY SUMMARY =================
@login_required(login_url='/authentication/login')
def expense_category_summary(request):
    expenses = Expense.objects.filter(owner=request.user)
    
    # Group by category and sum amounts
    category_totals = expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Get date range (last 30 days by default)
    end_date = timezone.now()
    start_date = end_date - datetime.timedelta(days=30)
    
    recent_expenses = expenses.filter(date__gte=start_date, date__lte=end_date)
    recent_totals = recent_expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    return JsonResponse({
        'all_time': list(category_totals),
        'last_30_days': list(recent_totals),
    })


# ================= OCR EXTRACT =================
import logging
logger = logging.getLogger(__name__)

@csrf_exempt
def ocr_extract(request):
    """
    API endpoint to scan receipt image and extract expense data.
    
    POST request with image file:
    - Accepts: image/jpeg, image/png, image/jpg
    - Max file size: 5MB
    
    Returns JSON:
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
    logger.info("OCR extract endpoint called")
    logger.info(f"User authenticated: {request.user.is_authenticated}")
    logger.info(f"User: {request.user}")
    
    # Check if user is authenticated - use more robust check
    if not request.user.is_authenticated:
        # Try to get user from session
        from django.contrib.auth import get_user
        try:
            # Check if session auth is working
            if request.session.session_key:
                logger.info(f"Session key: {request.session.session_key}")
        except Exception as e:
            logger.error(f"Session error: {e}")
            
        logger.warning("OCR: User not authenticated")
        return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
    
    from django.conf import settings
    import os
    import uuid
    from .utils.ocr_processor import scan_receipt, check_ocr_available
    
    if request.method != 'POST':
        logger.warning("OCR: Invalid request method")
        return JsonResponse({'error': 'Invalid request method. Use POST.'}, status=400)
    
    # Check if image file is provided
    image_file = request.FILES.get('image')
    if not image_file:
        logger.warning("OCR: No image provided")
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    logger.info(f"OCR: Processing image {image_file.name} ({image_file.size} bytes)")
    
    # Check if OCR libraries are available
    ocr_available, message = check_ocr_available()
    if not ocr_available:
        logger.error(f"OCR not available: {message}")
        return JsonResponse({
            'success': False,
            'error': f'OCR not available: {message}. Please install pytesseract and Tesseract OCR.'
        }, status=500)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
    if image_file.content_type not in allowed_types:
        logger.warning(f"OCR: Invalid file type {image_file.content_type}")
        return JsonResponse({
            'success': False,
            'error': f'Invalid file type. Allowed types: JPG, PNG, JPEG'
        }, status=400)
    
    # Validate file size (5MB max)
    max_size = 5 * 1024 * 1024  # 5MB
    if image_file.size > max_size:
        logger.warning(f"OCR: File too large {image_file.size} bytes")
        return JsonResponse({
            'success': False,
            'error': 'File too large. Maximum size is 5MB.'
        }, status=400)
    
    try:
        # Create media directory for temporary receipts if it doesn't exist
        media_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
        os.makedirs(media_dir, exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(image_file.name)[1]
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_filepath = os.path.join(media_dir, temp_filename)
        
        # Save uploaded file temporarily
        with open(temp_filepath, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)
        
        logger.info(f"OCR: Saved temp file to {temp_filepath}")
        
        # Process with OCR
        result = scan_receipt(temp_filepath)
        
        logger.info(f"OCR Result: {result}")
        
        # Ensure all required fields are present with proper defaults
        response_data = {
            'success': result.get('success', False),
            'amount': result.get('amount') or "",
            'merchant': result.get('merchant') or "",
            'date': result.get('date') or "",
            'category': result.get('category') or "Other",
            'confidence': result.get('confidence') or 0,
            'raw_text': result.get('raw_text') or "",
            'error': result.get('error')
        }
        
        # Add the image path to result (for later saving with expense)
        if result.get('success'):
            response_data['temp_image_path'] = temp_filepath
        
        # Return JSON response
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'OCR processing failed: {str(e)}'
        }, status=500)


# ================= PREDICT CATEGORY =================
@login_required(login_url='/authentication/login')
@csrf_exempt
def predict_category(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '')
            
            # Placeholder for ML-based category prediction
            # In production, you would use a trained model
            # For now, return a simple prediction based on keywords
            keywords = {
                'food': ['restaurant', 'lunch', 'dinner', 'breakfast', 'food', 'cafe', 'coffee'],
                'transport': ['uber', 'lyft', 'taxi', 'bus', 'train', 'metro', 'gas', 'fuel'],
                'shopping': ['amazon', 'walmart', 'target', 'shop', 'store'],
                'utilities': ['electric', 'water', 'internet', 'phone', 'bill'],
            }
            
            description_lower = description.lower()
            for category, words in keywords.items():
                for word in words:
                    if word in description_lower:
                        return JsonResponse({'category': category})
            
            return JsonResponse({'category': 'general'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# ================= SET EXPENSE LIMIT =================
@login_required(login_url='/authentication/login')
def set_expense_limit(request):
    if request.method == 'POST':
        limit_amount = request.POST.get('limit_amount')
        
        if limit_amount:
            try:
                limit, created = ExpenseLimit.objects.get_or_create(
                    owner=request.user,
                    defaults={'daily_expense_limit': limit_amount}
                )
                if not created:
                    limit.daily_expense_limit = limit_amount
                    limit.save()
                    
                    # Create notification for limit updated
                    create_notification(
                        user=request.user,
                        title="Daily Limit Updated",
                        message=f"Your daily expense limit has been updated to {limit_amount}.",
                        notification_type='success',
                        event_type='limit_updated'
                    )
                elif created:
                    # Create notification for new limit set
                    create_notification(
                        user=request.user,
                        title="Daily Limit Set",
                        message=f"Your daily expense limit has been set to {limit_amount}.",
                        notification_type='success',
                        event_type='limit_updated'
                    )
            except Exception:
                pass
            
            return redirect('dashboard')
    
    # Get current limit - use 'owner' not 'user' as per model
    try:
        expense_limit = ExpenseLimit.objects.filter(owner=request.user).first()
    except Exception:
        expense_limit = None
    return render(request, 'expenses/set_limit.html', {'expense_limit': expense_limit})


# ================= FINANCIAL INTELLIGENCE API =================
@login_required(login_url='/authentication/login')
def financial_intelligence_api(request):
    """
    API endpoint for live financial intelligence data.
    Returns JSON data for charts and metrics without page reload.
    """
    from services.dashboard_service import DashboardService
    from userpreferences.currency_service import CurrencyService
    
    # Get period parameter
    period = request.GET.get('period', 'month')
    valid_periods = ['week', 'month', 'quarter', 'year']
    if period not in valid_periods:
        period = 'month'
    
    # Get currency symbol
    currency_symbol = CurrencyService.get_currency_symbol(request.user)
    
    # Calculate date range text
    today = timezone.now().date()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
        date_range_text = f"{start_date.strftime('%b %d')} - {today.strftime('%b %d, %Y')}"
    elif period == 'month':
        start_date = today.replace(day=1)
        date_range_text = start_date.strftime('%B %Y')
    elif period == 'quarter':
        quarter = (today.month - 1) // 3 + 1
        date_range_text = f"Q{quarter} {today.year}"
    else:  # year
        date_range_text = str(today.year)
    
    # Get fresh dashboard data (don't use cache for API)
    dashboard_data = DashboardService.get_dashboard_data(request.user, period=period)
    
    # Build response data
    response_data = {
        'success': True,
        'period': period,
        'date_range_text': date_range_text,
        'currency_symbol': currency_symbol,
        
        # Financial Health
        'financial_health': dashboard_data.get('financial_health', {}),
        
        # Spending vs Income
        'spending_vs_income': dashboard_data.get('spending_vs_income', {}),
        
        # Budget Utilization
        'budget_utilization': dashboard_data.get('budget_utilization', {}),
        
        # Category Breakdown
        'category_breakdown': dashboard_data.get('category_breakdown', {}),
        
        # Trend Data
        'trend_data': dashboard_data.get('trend_data', {}),
        
        # AI Insights
        'ai_insights': dashboard_data.get('ai_insights', {}),
        
        # Savings Goals
        'savings_goals': dashboard_data.get('savings_goals', {}),
        
        # Activity Timeline
        'activity_timeline': dashboard_data.get('activity_timeline', {}),
        
        # Predictions
        'predictions': dashboard_data.get('predictions', {}),
    }
    
    return JsonResponse(response_data)


# ================= SUGGESTIONS PAGE (V2 - Enhanced) =================
@login_required(login_url='/authentication/login')
def suggestions(request):
    """
    Financial Suggestions Page V2 - Enhanced Intelligent Financial Advisor
    Provides personalized recommendations including health score, spending patterns, projections.
    """
    # Try to use V2 engine first, fall back to V1 if needed
    try:
        from services.suggestions_engine_v2 import SuggestionsEngineV2 as Engine
    except ImportError:
        from services.suggestions_engine import SuggestionsEngine as Engine
    
    from userpreferences.currency_service import CurrencyService
    
    # Get currency symbol
    currency_symbol = CurrencyService.get_currency_symbol(request.user)
    
    # Get comprehensive analysis from the suggestions engine
    analysis = Engine.get_comprehensive_analysis(request.user)
    
    # Prepare context for template
    context = {
        'page_title': 'Financial Suggestions',
        'currency_symbol': currency_symbol,
        
        # Budget Overview
        'budget': analysis['budget'],
        
        # NEW: Health Score
        'health_score': analysis.get('health_score', {}),
        
        # NEW: Spending Patterns
        'spending_patterns': analysis.get('spending_patterns', {}),
        
        # NEW: Savings Rate
        'savings_rate': analysis.get('savings_rate', {}),
        
        # NEW: Projections
        'projections': analysis.get('projections', {}),
        
        # NEW: Card Analysis
        'card_analysis': analysis.get('card_analysis', {}),
        
        # NEW: Net Worth
        'net_worth': analysis.get('net_worth', {}),
        
        # Debts
        'debts': analysis['debts'],
        'debt_predictions': analysis['debt_predictions'],
        
        # Goals
        'goals': analysis['goals'],
        'goal_predictions': analysis['goal_predictions'],
        
        # Allocation
        'allocation': analysis['allocation'],
        
        # Strategy Comparison
        'strategy_comparison': analysis.get('strategy_comparison'),
        
        # Financial Guidance
        'guidance': analysis['guidance'],
        
        # Summary
        'summary': analysis['summary'],
        
        # Check if user has data
        'has_debts': len(analysis['debts']) > 0,
        'has_goals': len(analysis['goals']) > 0,
        'has_budget': analysis['budget']['remaining_budget'] > 0,
    }
    
    return render(request, 'suggestions/index.html', context)
