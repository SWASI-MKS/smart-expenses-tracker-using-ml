from django.shortcuts import render, redirect, get_object_or_404
from .models import Goal
from .forms import GoalForm, AddAmountForm, ExtendDeadlineForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from services.goal_service import GoalService


def reopen_goal(request, goal_id):
    """Reopen a completed goal by changing its status back to ACTIVE"""
    if request.method == 'POST':
        goal = get_object_or_404(Goal, id=goal_id)
        
        # Only allow reopening if goal is COMPLETED
        if goal.status == 'COMPLETED':
            goal.status = 'ACTIVE'
            goal.is_achieved = False
            goal.save()
            messages.success(request, f'Goal "{goal.name}" has been reopened successfully! You can continue saving towards it.')
        else:
            messages.error(request, 'Only completed goals can be reopened.')
    
    return redirect('list_goals')
def add_goal(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.owner = request.user
            goal.status = Goal.STATUS_ACTIVE
            goal.save()
            messages.success(request, f'Goal "{goal.name}" created successfully!')
            return redirect('list_goals')

    form = GoalForm()
    return render(request, 'goals/add_goals.html', {'form': form})


@login_required(login_url='/authentication/login')
def list_goals(request):
    # Update all goal statuses before displaying
    GoalService.update_all_goals_status(request.user)
    
    # Get goals by status for tabs
    active_goals = Goal.objects.filter(
        owner=request.user,
        status=Goal.STATUS_ACTIVE
    ).order_by('end_date')
    
    completed_goals = Goal.objects.filter(
        owner=request.user,
        status=Goal.STATUS_COMPLETED
    ).order_by('-updated_at')
    
    overdue_goals = Goal.objects.filter(
        owner=request.user,
        status=Goal.STATUS_OVERDUE
    ).order_by('end_date')
    
    archived_goals = Goal.objects.filter(
        owner=request.user,
        status=Goal.STATUS_ARCHIVED
    ).order_by('-updated_at')
    
    # Show all non-archived goals by default
    goals = Goal.objects.filter(
        owner=request.user
    ).exclude(status=Goal.STATUS_ARCHIVED).order_by('-created_at')
    
    add_amount_form = AddAmountForm()
    extend_deadline_form = ExtendDeadlineForm()
    
    return render(request, 'goals/list_goals.html', {
        'goals': goals,
        'active_goals': active_goals,
        'completed_goals': completed_goals,
        'overdue_goals': overdue_goals,
        'archived_goals': archived_goals,
        'add_amount_form': add_amount_form,
        'extend_deadline_form': extend_deadline_form,
    })


@login_required(login_url='/authentication/login')
def add_amount(request, goal_id):
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    
    # Don't allow adding amount to completed or archived goals
    if goal.status in [Goal.STATUS_COMPLETED, Goal.STATUS_ARCHIVED]:
        messages.error(request, f'Cannot add amount to a {goal.status.lower()} goal.')
        return redirect('list_goals')

    if request.method == 'POST':
        form = AddAmountForm(request.POST)
        if form.is_valid():
            additional_amount = form.cleaned_data['additional_amount']
            amount_required = goal.amount_to_save - goal.current_saved_amount

            if additional_amount > amount_required:
                messages.error(request, f'The maximum amount needed to achieve goal is: ₹{amount_required}.')
            else:
                # =====================================================
                # DEDUCT FROM BANK ACCOUNT
                # =====================================================
                from bank_simulator.models import BankAccount, BankTransaction
                from django.utils import timezone
                from decimal import Decimal
                
                # Convert to Decimal for proper comparison
                additional_amount_decimal = Decimal(str(additional_amount))
                
                try:
                    # Get user's bank account
                    bank_account = BankAccount.objects.get(user=request.user)
                    
                    # Convert balance to Decimal for comparison
                    current_balance = Decimal(str(bank_account.balance))
                    
                    # Check if user has sufficient balance
                    if current_balance < additional_amount_decimal:
                        messages.error(request, f'Insufficient bank balance. Your current balance is: ₹{bank_account.balance}')
                        return redirect('list_goals')
                    
                    # Deduct from bank account
                    new_balance = current_balance - additional_amount_decimal
                    bank_account.balance = new_balance
                    bank_account.save()
                    
                    # Create bank transaction record
                    BankTransaction.objects.create(
                        user=request.user,
                        amount=additional_amount_decimal,
                        transaction_type='DEBIT',
                        description=f"Goal Savings: {goal.name}",
                        balance_after=new_balance
                    )
                    
                    # Also create an expense entry for tracking
                    from expenses.models import Expense
                    Expense.objects.create(
                        owner=request.user,
                        amount=float(additional_amount_decimal),
                        description=f"Goal Savings: {goal.name}",
                        category="Other",
                        date=timezone.now().date(),
                        payment_method='BANK'
                    )
                    
                    messages.success(request, f'₹{additional_amount} deducted from bank and added to goal!')
                    
                except BankAccount.DoesNotExist:
                    # If no bank account, just add to goal without deduction
                    messages.warning(request, 'No bank account found. Amount added to goal without bank deduction.')
                except Exception as e:
                    messages.error(request, f'Error: {str(e)}')
                
                # Add amount to goal
                goal.current_saved_amount += additional_amount
                goal.save()

                # Check if goal is now completed
                if goal.current_saved_amount >= goal.amount_to_save:
                    # Update status to completed
                    goal.status = Goal.STATUS_COMPLETED
                    goal.is_achieved = True
                    goal.save(update_fields=['status', 'is_achieved', 'updated_at'])
                    
                    # Send congratulatory email
                    send_congratulatory_email(request.user.email, goal)
                    
                    # Create notification
                    GoalService.notify_goal_completed(goal)
                    
                    messages.success(request, 'Congratulations! You have achieved your goal!')
                else:
                    # Update status (might become overdue if deadline passed)
                    GoalService.update_goal_status(goal)
                    messages.success(request, f'Amount successfully added to goal. Total saved: ₹{goal.current_saved_amount}.')
                    messages.info(request, f'Amount required to reach goal: ₹{amount_required}.')

        return redirect('list_goals')

    return redirect('list_goals')


def send_congratulatory_email(email, goal):
    subject = 'Congratulations on achieving your goal!'
    message = f'Dear User,\n\nCongratulations on achieving your goal "{goal.name}". You have successfully saved {goal.amount_to_save}.\n\nKeep up the good work!\n\nBest regards,\nThe Goal Tracker Team, \nExpenseWise Team'
    send_mail(subject, message, 'hemantshirsath24@gmail.com', [email])


@login_required(login_url='/authentication/login')
def extend_deadline(request, goal_id):
    """Extend the deadline of a goal"""
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    
    # Can't extend completed or archived goals
    if goal.status in [Goal.STATUS_COMPLETED, Goal.STATUS_ARCHIVED]:
        messages.error(request, f'Cannot extend a {goal.status.lower()} goal.')
        return redirect('list_goals')
    
    if request.method == 'POST':
        form = ExtendDeadlineForm(request.POST)
        if form.is_valid():
            new_end_date = form.cleaned_data['end_date']
            try:
                goal.extend_deadline(new_end_date)
                messages.success(request, f'Deadline for "{goal.name}" extended successfully!')
            except ValidationError as e:
                messages.error(request, str(e))
        
        return redirect('list_goals')
    
    return redirect('list_goals')


@login_required(login_url='/authentication/login')
def archive_goal(request, goal_id):
    """Archive a goal"""
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    
    if goal.status != Goal.STATUS_ARCHIVED:
        goal.archive()
        messages.success(request, f'Goal "{goal.name}" has been archived.')
    else:
        messages.info(request, 'Goal is already archived.')
    
    return redirect('list_goals')


@login_required(login_url='/authentication/login')
def unarchive_goal(request, goal_id):
    """Unarchive a goal - restore it to Active status"""
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    
    if goal.status == Goal.STATUS_ARCHIVED:
        # Change status from ARCHIVED to ACTIVE
        goal.status = Goal.STATUS_ACTIVE
        goal.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Goal "{goal.name}" has been restored to Active status.')
    else:
        messages.error(request, 'Only archived goals can be unarchived.')
    
    return redirect('list_goals')


@login_required(login_url='/authentication/login')
def restore_goal(request, goal_id):
    """Restore an archived goal to active status"""
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    
    if goal.status == Goal.STATUS_ARCHIVED:
        # Recalculate status based on current state
        GoalService.update_goal_status(goal)
        messages.success(request, f'Goal "{goal.name}" has been restored.')
    else:
        messages.error(request, 'Can only restore archived goals.')
    
    return redirect('list_goals')


@login_required(login_url='/authentication/login')
def delete_goal(request, goal_id):
    """
    Delete a goal. For archived goals only (soft delete pattern).
    Active goals should be archived first.
    """
    try:
        goal = Goal.objects.get(id=goal_id, owner=request.user)
        
        # If goal is active or completed, archive it instead of deleting
        if goal.status in [Goal.STATUS_ACTIVE, Goal.STATUS_COMPLETED, Goal.STATUS_OVERDUE]:
            goal.archive()
            messages.success(request, f'Goal "{goal.name}" has been archived. You can restore it later if needed.')
        elif goal.status == Goal.STATUS_ARCHIVED:
            # Only allow hard delete for archived goals
            goal.delete()
            messages.success(request, 'Goal permanently deleted.')
        else:
            messages.error(request, 'Invalid goal status.')
            
        return redirect('list_goals')
    except Goal.DoesNotExist:
        messages.error(request, 'Goal not found.')
        return redirect('list_goals')


@login_required(login_url='/authentication/login')
def goal_detail(request, goal_id):
    """Show detailed view of a goal"""
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)
    
    # Update status before showing
    GoalService.update_goal_status(goal)
    
    progress = goal.calculate_progress()
    
    return render(request, 'goals/goal_detail.html', {
        'goal': goal,
        'progress': progress,
    })


@login_required(login_url='/authentication/login')
def refresh_goal_statuses(request):
    """Manually refresh all goal statuses"""
    if request.method == 'POST':
        counts = GoalService.update_all_goals_status(request.user)
        
        # Check for newly overdue goals
        newly_overdue = GoalService.check_and_notify_overdue(request.user)
        
        messages.success(request, 
            f'Statuses updated. Active: {counts["active"]}, Completed: {counts["completed"]}, Overdue: {counts["overdue"]}')
        
        if newly_overdue:
            messages.warning(request, 
                f'{len(newly_overdue)} goal(s) became overdue. Notifications sent.')
    
    return redirect('list_goals')
