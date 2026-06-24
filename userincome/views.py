from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta


from django.shortcuts import render, redirect,HttpResponseRedirect
from .models import Source, UserIncome
from django.core.paginator import Paginator
from userpreferences.models import UserPreference
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse
import datetime
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from .models import UserIncome
from expenses.models import Expense
from django.db.models import Sum
import csv
import openpyxl
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa


from .models import UserIncome
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from datetime import datetime
# Create your views here.

@login_required(login_url='/authentication/login')

def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        income = UserIncome.objects.filter(
            amount__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            date__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            description__icontains=search_str, owner=request.user) | UserIncome.objects.filter(
            source__icontains=search_str, owner=request.user)
        data = income.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    categories = Source.objects.filter(owner=request.user)
    income = UserIncome.objects.filter(owner=request.user)

    sort_order = request.GET.get('sort')

    if sort_order == 'amount_asc':
        income = income.order_by('amount')
    elif sort_order == 'amount_desc':
        income = income.order_by('-amount')
    elif sort_order == 'date_asc':
        income = income.order_by('date')
    elif sort_order == 'date_desc':
        income = income.order_by('-date')

    paginator = Paginator(income, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    try:
        currency = UserPreference.objects.get(user=request.user).currency
    except:
        currency=None
    total = page_obj.paginator.num_pages
    context = {
        'income': income,
        'page_obj': page_obj,
        'currency': currency,
        'total': total,
        'sort_order': sort_order,
    }
    return render(request, 'income/index.html', context)


@login_required(login_url='/authentication/login')
def add_income(request):
    sources = Source.objects.filter(owner=request.user)
    if(len(sources)==0):
        messages.info(request,"you need to add income sources first in order to add income")
        return HttpResponseRedirect('/account/')
    context = {
        'sources': sources,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'income/add_income.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']
        date_str = request.POST.get('income_date')
        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/add_income.html', context)
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'income/add_income.html', context)

        try:
            # Convert the date string to a datetime object and validate the date
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.now().date()

            if date > today:
                messages.error(request, 'Date cannot be in the future')
                return render(request, 'income/add_income.html', context)
                # return redirect('add-income', context)

            UserIncome.objects.create(owner=request.user, amount=amount, date=date,
                                      source=source, description=description)
            messages.success(request, 'Income saved successfully')

            return redirect('overview')
        except ValueError:
            messages.error(request, 'Invalid date format')
            return render(request, 'income/add_income.html', context)
            # return redirect('add-income', context)

        # UserIncome.objects.create(owner=request.user, amount=amount, date=date,
        #                           source=source, description=description)
        # messages.success(request, 'Record saved successfully')

        # return redirect('income')


@login_required(login_url='/authentication/login')
def income_edit(request, id):
    income = UserIncome.objects.get(pk=id)
    sources = Source.objects.all()
    context = {
        'income': income,
        'values': income,
        'sources': sources
    }
    if request.method == 'GET':
        return render(request, 'income/edit_income.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        date_str = request.POST.get('income_date')

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'income/edit_income.html', context)
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'income/edit_income.html', context)

        try:
            # Convert the date string to a datetime object and validate the date
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.now().date()

          
            if date > today:
                messages.error(request, 'Date cannot be in the future')
                return render(request, 'income/edit_income.html', context)
                # return redirect('edit_income', context)

            income.amount = amount
            income. date = date
            income.source = source
            income.description = description
            income.save()
            messages.success(request, 'Income saved successfully')

            return redirect('income')
        except ValueError:
            messages.error(request, 'Invalid date format')
            return render(request, 'income/edit_income.html', context)
        # income.amount = amount
        # income. date = date
        # income.source = source
        # income.description = description

        # income.save()
        # messages.success(request, 'Record updated  successfully')

        # return redirect('income')

@login_required(login_url='/authentication/login')
def delete_income(request, id):
    income = UserIncome.objects.get(pk=id)
    income.delete()
    messages.success(request, 'record removed')
    return redirect('income')


@login_required(login_url='/authentication/login')
def income_summary(request):
    # Import FinancialService for centralized calculations
    from services.financial_service import FinancialService
    from userincome.prediction_service import IncomePredictionService
    
    user = request.user  # Get the logged-in user
    
    # Get currency symbol for the user
    from userpreferences.currency_service import CurrencyService
    currency_symbol = CurrencyService.get_currency_symbol(user)

    today = timezone.now().date()
    one_week_ago = today - timedelta(days=7)
    first_day_of_month = today.replace(day=1)
    first_day_of_year = today.replace(month=1, day=1)

    # Query the database to get daily, weekly, monthly, and yearly income for the logged-in user
    daily_income = user.userincome_set.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0
    weekly_income = user.userincome_set.filter(date__gte=one_week_ago).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_income = user.userincome_set.filter(date__month=today.month, date__year=today.year).aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_income = user.userincome_set.filter(date__year=today.year).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Total Lifetime Income
    total_income = user.userincome_set.all().aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get centralized financial totals using FinancialService (ALWAYS recalculate from DB)
    financial_totals = FinancialService.calculate_net_worth(user)
    monthly_summary = FinancialService.calculate_monthly_summary(user)
    
    # Calculate average monthly income
    from django.db.models import Avg, Count
    monthly_avg = user.userincome_set.filter(date__year=today.year).annotate(
        month=ExtractMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).aggregate(Avg('total'))['total__avg'] or 0
    
    # Get highest income month (this year)
    monthly_data = user.userincome_set.filter(
        date__year=today.year
    ).annotate(
        month=ExtractMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    highest_month_amount = monthly_data[0]['total'] if monthly_data else 0
    
    # Calculate income count
    income_count = user.userincome_set.count()
    
    # ================= NEW: INCOME BY SOURCE (for pie chart) =================
    source_data = user.userincome_set.values('source').annotate(total=Sum('amount')).order_by('-total')
    sources = [item['source'] for item in source_data]
    source_amounts = [float(item['total']) for item in source_data]
    
    # ================= NEW: HIGHEST INCOME SOURCE =================
    highest_source = None
    if source_data:
        top_source = source_data[0]
        highest_source = {
            'name': top_source['source'],
            'amount': float(top_source['total']),
            'percentage': round((top_source['total'] / total_income * 100) if total_income > 0 else 0, 1)
        }
    
    # ================= NEW: SOURCE BREAKDOWN TABLE =================
    source_breakdown_table = []
    for item in source_data:
        source_breakdown_table.append({
            'name': item['source'],
            'amount': float(item['total']),
            'percentage': round((item['total'] / total_income * 100) if total_income > 0 else 0, 1)
        })
    
    # ================= NEW: MONTHLY INCOME TREND (Last 6 months) =================
    import calendar
    monthly_income_list = []
    
    for i in range(5, -1, -1):  # Last 6 months
        current_month = today.month
        current_year = today.year
        
        target_month = current_month - i
        target_year = current_year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        first_day = date(target_year, target_month, 1)
        last_day = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])
        
        month_income = user.userincome_set.filter(
            date__gte=first_day,
            date__lte=last_day
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        monthly_income_list.append({
            'month': first_day.strftime('%b %Y'),
            'month_short': first_day.strftime('%b'),
            'year': target_year,
            'month_num': target_month,
            'amount': float(month_income)
        })
    
    # Remove duplicates if any
    seen = set()
    unique_monthly_income = []
    for item in monthly_income_list:
        key = (item['year'], item['month_num'])
        if key not in seen:
            seen.add(key)
            unique_monthly_income.append(item)
    
    monthly_income_list = unique_monthly_income
    
    # ================= NEW: AVERAGE MONTHLY INCOME (Last 6 months) =================
    six_months_ago = today - timedelta(days=180)
    last_6_month_income = user.userincome_set.filter(date__gte=six_months_ago)
    total_last_6_months = last_6_month_income.aggregate(Sum('amount'))['amount__sum'] or 0
    average_monthly_income = round(total_last_6_months / 6, 2)
    
    # ================= NEW: RECENT INCOME (Last 10) =================
    recent_income_query = user.userincome_set.order_by('-date', '-id')[:10]
    
    recent_income = []
    for income in recent_income_query:
        recent_income.append({
            'id': income.id,
            'amount': income.amount,
            'date': income.date,
            'source': income.source,
            'description': income.description,
        })
    
    # For JSON - convert date to string
    recent_income_json_list = []
    for income in recent_income_query:
        recent_income_json_list.append({
            'id': income.id,
            'amount': float(income.amount),
            'date': income.date.strftime('%Y-%m-%d'),
            'source': income.source,
            'description': income.description,
        })
    
    import json
    recent_income_json = json.dumps(recent_income_json_list)
    sources_json = json.dumps(sources)
    source_amounts_json = json.dumps(source_amounts)
    monthly_income_json = json.dumps(monthly_income_list)
    source_breakdown_json = json.dumps(source_breakdown_table)
    
    # Calculate progress percentage
    from expenses.models import ExpenseLimit
    try:
        expense_limit = ExpenseLimit.objects.filter(owner=user).first()
        monthly_budget = expense_limit.daily_expense_limit * 30 if expense_limit else 50000
    except:
        monthly_budget = 50000
    
    monthly_progress = (monthly_income / monthly_budget * 100) if monthly_budget > 0 else 0

    context = {
        'daily_income': daily_income,
        'weekly_income': weekly_income,
        'monthly_income': monthly_income,
        'yearly_income': yearly_income,
        'total_income': total_income,
        'currency_symbol': currency_symbol,
        'monthly_budget': monthly_budget,
        'monthly_progress': min(monthly_progress, 100),
        # Analytics
        'monthly_avg': monthly_avg,
        'highest_month_amount': highest_month_amount,
        'income_count': income_count,
        # Legacy context names for compatibility
        'daily_earnings': daily_income,
        'weekly_earnings': weekly_income,
        'monthly_earnings': monthly_income,
        'yearly_earnings': yearly_income,
        # NEW CONTEXT VARIABLES
        'has_income': income_count > 0,
        'sources': sources,
        'source_amounts': source_amounts,
        'sources_json': sources_json,
        'source_amounts_json': source_amounts_json,
        'highest_source': highest_source,
        'source_breakdown_table': source_breakdown_table,
        'source_breakdown_json': source_breakdown_json,
        'monthly_income_list': monthly_income_list,
        'monthly_income_json': monthly_income_json,
        'average_monthly_income': average_monthly_income,
        'recent_income': recent_income,
        'recent_income_json': recent_income_json,
        # Centralized Financial Totals from FinancialService (always from DB, never cached)
        'total_expenses': financial_totals.get('total_expenses', 0),
        'card_spending': financial_totals.get('card_spending', 0),
        'bank_balance': financial_totals.get('bank_balance', 0),
        'net_worth': financial_totals.get('net_worth', 0),
        'monthly_expenses': monthly_summary.get('expenses', {}).get('total', 0),
        'monthly_card_spending': monthly_summary.get('card_spending', {}).get('total', 0),
        
        # Next Month Income Prediction
        'next_month_income_prediction': IncomePredictionService.predict_next_month(user),
    }
    return render(request, 'income/dashboard.html', context)

# @login_required(login_url='/authentication/login')
# def income_summary(request):
#     today = timezone.now()

#     # Calculate the date for one week ago
#     one_week_ago = today - timedelta(days=7)

#     # Calculate the first day of the current month
#     first_day_of_month = today.replace(day=1)
#     first_day_of_year = today.replace(month=1, day=1)

#     # Query the database to get daily, weekly, and monthly income
#     daily_income = UserIncome.objects.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0
#     weekly_income = UserIncome.objects.filter(date__range=[one_week_ago, today]).aggregate(Sum('amount'))['amount__sum'] or 0
#     monthly_income = UserIncome.objects.filter(date__month=today.month).aggregate(Sum('amount'))['amount__sum'] or 0
#     yearly_income = UserIncome.objects.filter(date__year=today.year).aggregate(Sum('amount'))['amount__sum'] or 0
#     context = {
#         'daily_income': daily_income,
#         'weekly_income': weekly_income,
#         'monthly_income': monthly_income,
#         'yearly_income': yearly_income,
#         # You can add more context data here if needed
#     }
#     return render(request,'income/dashboard.html',context)




from datetime import datetime

@login_required(login_url='/authentication/login')
def monthly_income_data(request):
    """Get monthly income data for the last 6 months with income only"""
    from datetime import datetime, timedelta
    from django.db.models.functions import ExtractMonth
    
    today = datetime.now().date()
    
    # Calculate 6 months ago
    six_months_ago = today - timedelta(days=180)
    
    # Get monthly income data for the last 6 months
    monthly_data = (
        UserIncome.objects
        .filter(date__gte=six_months_ago, owner=request.user)
        .annotate(month=ExtractMonth('date'), year=ExtractMonth('date'))
        .values('month', 'year')
        .annotate(total_income=Sum('amount'))
        .order_by('year', 'month')
    )
    
    # Build month names and data
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Get unique months with data
    result_data = []
    for item in monthly_data:
        month_index = item['month'] - 1
        result_data.append({
            'month': month_names[month_index],
            'total': float(item['total_income'])
        })
    
    # If no data, provide sample months
    if not result_data:
        for i in range(5, -1, -1):
            month_date = today - timedelta(days=i*30)
            result_data.append({
                'month': month_names[month_date.month - 1],
                'total': 0
            })
    
    return JsonResponse({'monthly_income_data': result_data})







@login_required(login_url='/authentication/login')
def get_monthly_income(request):
    today = date.today()
    first_day_of_year = today.replace(month=1, day=1)
    last_day_of_year = today.replace(month=12, day=31)

    # Create a list to hold income data for all 12 months
    monthly_data = [0] * 12

    # Retrieve and fill in the actual monthly income data
    income_data = UserIncome.objects.filter(
        date__range=(first_day_of_year, last_day_of_year),
        owner=request.user
    ).values('date', 'amount')

    for entry in income_data:
        month = entry['date'].month - 1  # Convert month (1-12) to index (0-11)
        monthly_data[month] = entry['amount']

    return JsonResponse({'monthly_data': monthly_data})





def render_to_pdf(template_path, context_dict):
    template = get_template(template_path)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="expense_report.pdf"'
        return response
    return HttpResponse("Error rendering PDF", status=400)


def export_pdf(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    incomes = UserIncome.objects.filter(date__range=[start_date, end_date])
    expenses = Expense.objects.filter(date__range=[start_date, end_date])
    
    total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    savings = total_income - total_expense
    
    context = {
        'incomes': incomes,
        'expenses': expenses,
        'total_income': total_income,
        'total_expense': total_expense,
        'savings': savings,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    pdf = render_to_pdf('income/pdf_template.html', context)
    return pdf

@login_required(login_url='/authentication/login')
def report(request):
    report_generated=False
    return render(request, 'income/report.html',{'report_generated':report_generated})

def generate_report(request):
    if request.method == "POST":
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        user = request.user
        report_generated=True

        if start_date > end_date:
            messages.error(request, "Start date cannot be greater than end date.")
            return redirect('report')

        # incomes = UserIncome.objects.filter(date__range=[start_date, end_date])
        # expenses = Expense.objects.filter(date__range=[start_date, end_date])

        incomes = UserIncome.objects.filter(owner=user, date__range=[start_date, end_date])
        expenses = Expense.objects.filter(owner=user, date__range=[start_date, end_date])

        total_income = incomes.aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

        savings = total_income - total_expense
        
        context = {
            'incomes': incomes,
            'expenses': expenses,
            'total_income': total_income,
            'total_expense': total_expense,
            'savings': savings,
            'start_date': start_date,
            'end_date': end_date,
            'report_generated':report_generated
        }

        return render(request, 'income/report.html', context)
    else:
        
        return render(request, 'income/report.html')

def export_csv(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    incomes = UserIncome.objects.filter(date__range=[start_date, end_date])
    expenses = Expense.objects.filter(date__range=[start_date, end_date])
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.csv'
    
    writer = csv.writer(response)
    
    # Label the income section
    writer.writerow(['Income'])
    writer.writerow(['Date', 'Source', 'Amount'])
    
    income_total = 0
    for income in incomes:
        writer.writerow([income.date, income.source, income.amount])
        income_total += income.amount
    
    # Display the total income
    writer.writerow(['', f'Total Income: {income_total}'])

    # Label the expense section
    writer.writerow(['Expenses'])
    writer.writerow(['Date', 'Category', 'Amount'])
    
    expense_total = 0
    for expense in expenses:
        writer.writerow([expense.date, expense.category, expense.amount])
        expense_total += expense.amount
    
    # Add an empty line
    writer.writerow([])
    
    # Display the total expense
    writer.writerow(['', f'Total Expenses: {expense_total}'])
    
    return response

def export_xlsx(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    incomes = UserIncome.objects.filter(date__range=[start_date, end_date])
    expenses = Expense.objects.filter(date__range=[start_date, end_date])
    
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.xlsx"'
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Label the income section
    ws.append(['Income'])
    ws.append(['Date', 'Source', 'Amount'])
    
    income_total = 0
    for income in incomes:
        ws.append([income.date, income.source, income.amount])
        income_total += income.amount
    
    # Display the total income
    ws.append(['', f'Total Income: {income_total}'])

    # Label the expense section
    ws.append(['Expenses'])
    ws.append(['Date', 'Category', 'Amount'])
    
    expense_total = 0
    for expense in expenses:
        ws.append([expense.date, expense.category, expense.amount])
        expense_total += expense.amount
    
    # Add an empty line
    ws.append([])
    
    # Display the total expense
    ws.append(['', f'Total Expenses: {expense_total}'])
    
    wb.save(response)
    return response
