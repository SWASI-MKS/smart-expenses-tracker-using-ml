from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Debt, EMIPayment
from .forms import DebtForm, EMIPaymentForm


@login_required
def debt_list(request):
    """Display all debts for the user."""
    debts = Debt.objects.filter(owner=request.user)
    
    # Calculate totals
    total_debt = sum(float(d.principal_amount) for d in debts)
    total_remaining = sum(float(d.remaining_balance) for d in debts)
    total_emi_monthly = sum(float(d.emi_amount) for d in debts.filter(status=Debt.STATUS_ACTIVE))
    
    context = {
        'debts': debts,
        'total_debt': round(total_debt, 2),
        'total_remaining': round(total_remaining, 2),
        'total_emi_monthly': round(total_emi_monthly, 2),
    }
    return render(request, 'debts/list.html', context)


@login_required
def debt_detail(request, debt_id):
    """Display debt details with amortization schedule."""
    debt = get_object_or_404(Debt, id=debt_id, owner=request.user)
    emi_payments = debt.emi_payments.all().order_by('due_date')
    
    # Calculate summary
    total_paid = debt.total_amount_paid
    remaining = debt.remaining_balance
    progress = debt.progress_percentage
    
    context = {
        'debt': debt,
        'emi_payments': emi_payments,
        'total_paid': total_paid,
        'remaining': remaining,
        'progress': round(progress, 1),
        'schedule': debt.calculate_amortization_schedule()[:12],  # First year only
    }
    return render(request, 'debts/detail.html', context)


@login_required
def add_debt(request):
    """Add a new debt record."""
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            debt.owner = request.user
            
            # Calculate EMI
            calculated_emi = form.cleaned_data.get('calculated_emi')
            if calculated_emi:
                debt.emi_amount = Decimal(str(calculated_emi))
            
            # Calculate end date
            debt.end_date = debt.start_date + timedelta(days=30 * debt.loan_term_months)
            debt.next_emi_date = debt.end_date  # Will be updated
            
            debt.save()
            
            # Generate EMI schedule
            _generate_emi_schedule(debt)
            
            messages.success(request, 'Debt added successfully!')
            return redirect('debt-list')
    else:
        form = DebtForm()
    
    return render(request, 'debts/add.html', {'form': form})


@login_required
def edit_debt(request, debt_id):
    """Edit an existing debt record."""
    debt = get_object_or_404(Debt, id=debt_id, owner=request.user)
    
    if request.method == 'POST':
        form = DebtForm(request.POST, instance=debt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Debt updated successfully!')
            return redirect('debt-detail', debt_id=debt.id)
    else:
        form = DebtForm(instance=debt)
    
    return render(request, 'debts/edit.html', {'form': form, 'debt': debt})


@login_required
def delete_debt(request, debt_id):
    """Delete a debt record."""
    debt = get_object_or_404(Debt, id=debt_id, owner=request.user)
    
    if request.method == 'POST':
        debt.delete()
        messages.success(request, 'Debt deleted successfully!')
        return redirect('debt-list')
    
    return render(request, 'debts/delete.html', {'debt': debt})


@login_required
def record_emi(request, debt_id):
    """Record an EMI payment."""
    debt = get_object_or_404(Debt, id=debt_id, owner=request.user)
    
    if request.method == 'POST':
        form = EMIPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.debt = debt
            
            # Calculate principal and interest portions
            balance = float(debt.remaining_balance)
            rate = float(debt.interest_rate) / 100 / 12
            interest = balance * rate
            principal = float(payment.amount) - interest
            
            payment.principal_portion = Decimal(str(round(principal, 2)))
            payment.interest_portion = Decimal(str(round(interest, 2)))
            payment.balance_after = Decimal(str(max(0, balance - principal)))
            
            payment.save()
            
            # Update debt status if fully paid
            if payment.balance_after <= 0:
                debt.status = Debt.STATUS_PAID_OFF
                debt.save()
            else:
                # Update next EMI date
                debt.next_emi_date = debt.next_emi_date + timedelta(days=30)
                debt.save()
            
            messages.success(request, 'EMI payment recorded successfully!')
            return redirect('debt-detail', debt_id=debt.id)
    else:
        # Pre-fill with next expected EMI
        initial = {
            'due_date': debt.next_emi_date,
            'amount': debt.emi_amount,
        }
        form = EMIPaymentForm(initial=initial)
    
    return render(request, 'debts/record_emi.html', {'form': form, 'debt': debt})


@login_required
def debt_dashboard(request):
    """Debt overview dashboard."""
    debts = Debt.objects.filter(owner=request.user)
    active_debts = debts.filter(status=Debt.STATUS_ACTIVE)
    
    # Get upcoming EMI payments
    upcoming_emis = EMIPayment.objects.filter(
        debt__in=active_debts,
        is_paid=False,
        due_date__lte=timezone.now().date() + timedelta(days=30)
    ).order_by('due_date')[:5]
    
    # Calculate totals
    total_remaining = sum(float(d.remaining_balance) for d in active_debts)
    total_monthly_emi = sum(float(d.emi_amount) for d in active_debts)
    overdue_count = sum(1 for e in upcoming_emis if e.is_overdue)
    
    context = {
        'debts': active_debts,
        'upcoming_emis': upcoming_emis,
        'total_remaining': round(total_remaining, 2),
        'total_monthly_emi': round(total_monthly_emi, 2),
        'overdue_count': overdue_count,
        'total_active_debts': active_debts.count(),
    }
    return render(request, 'debts/dashboard.html', context)


def _generate_emi_schedule(debt):
    """Generate EMI payment schedule for a debt."""
    schedule = debt.calculate_amortization_schedule()
    
    for item in schedule:
        EMIPayment.objects.create(
            debt=debt,
            due_date=debt.start_date + timedelta(days=30 * item['month']),
            amount=Decimal(str(item['emi'])),
            principal_portion=Decimal(str(item['principal'])),
            interest_portion=Decimal(str(item['interest'])),
            balance_after=Decimal(str(item['balance']))
        )
