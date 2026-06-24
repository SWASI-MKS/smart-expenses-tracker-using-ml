from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum

from .models import BankTransaction, CardTransaction, Card, TransferRequest, BankAccount
from expenses.models import Expense
from userincome.models import UserIncome
from .services import (
    categorize_transaction,
    extract_merchant_name,
    generate_transaction_hash,
    detect_recurring,
    detect_large_transaction,
    create_alert,
    check_and_create_alerts
)
import logging

logger = logging.getLogger(__name__)


def update_bank_account_balance_from_transactions(user):
    """
    Helper function to recalculate and update BankAccount balance from all transactions.
    This ensures the balance is always in sync with the transaction history.
    Also clears the dashboard cache to ensure fresh data is displayed.
    """
    try:
        # Get or create bank account
        account, created = BankAccount.objects.get_or_create(
            user=user,
            defaults={
                'account_number': f'ACC{user.id}0001',
                'balance': 0.00
            }
        )
        
        # Calculate total credits and debits from all transactions
        credits = BankTransaction.objects.filter(
            user=user,
            transaction_type='CREDIT'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        debits = BankTransaction.objects.filter(
            user=user,
            transaction_type='DEBIT'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate new balance
        new_balance = credits - debits
        
        # Only update if balance has changed
        if account.balance != new_balance:
            account.balance = new_balance
            account.save(update_fields=['balance'])
            logger.info(f"Updated BankAccount balance for user {user.id}: {new_balance}")
        
        # Clear dashboard cache for this user to ensure fresh data
        _clear_dashboard_cache(user)
        
        return new_balance
    except Exception as e:
        logger.error(f"Error updating bank account balance: {str(e)}")
        return 0


def _clear_dashboard_cache(user):
    """
    Clear all dashboard-related cache for a user.
    This ensures that when bank transactions occur, the dashboard shows fresh data.
    """
    try:
        from django.core.cache import cache
        
        # Clear all dashboard cache keys for this user
        cache_keys = [
            f"dashboard_{user.id}_financial_health_month",
            f"dashboard_{user.id}_budget_utilization",
            f"dashboard_{user.id}_spending_vs_income",
            f"dashboard_{user.id}_category_breakdown_1",
            f"dashboard_{user.id}_trend_30",
            f"dashboard_{user.id}_ai_insights",
            f"dashboard_{user.id}_savings_goals",
            f"dashboard_{user.id}_advanced_ai_insights",
            f"dashboard_{user.id}_predictions",
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        logger.info(f"Cleared dashboard cache for user {user.id}")
    except Exception as e:
        logger.error(f"Error clearing dashboard cache: {str(e)}")


@receiver(post_save, sender=TransferRequest)
def handle_transfer_request_status(sender, instance, created, **kwargs):
    """
    Handle TransferRequest status changes - create Expense when transfer is successful.
    This ensures automatic synchronization between bank transfers and expense tracking.
    """
    try:
        # Only process when transfer is successful and wasn't already successful before
        if instance.status == 'SUCCESS' and not created:
            # Check if this is a new success (not an update to already successful)
            # Get the previous state by checking if linked_expense_id was already set
            from django.db.models import F
            
            # Check if expense was already created for this transfer
            existing_expense = Expense.objects.filter(
                owner=instance.sender,
                description__contains=instance.transaction_id,
                payment_method='BANK'
            ).first()
            
            if existing_expense:
                # Expense already exists, just log
                logger.info(f"Expense already exists for transfer {instance.transaction_id}")
                return
            
            # Get receiver name
            receiver_name = instance.beneficiary.name if instance.beneficiary else instance.receiver_name
            
            # Get description from transfer note or create default
            transfer_description = instance.note or f"Transfer to {receiver_name}"
            
            # Auto-detect category based on description
            category = categorize_transaction(transfer_description)
            
            # Extract merchant name if applicable
            merchant_name = extract_merchant_name(transfer_description)
            
            # Create expense record automatically
            expense = Expense.objects.create(
                owner=instance.sender,
                amount=float(instance.amount),
                description=transfer_description,
                category=category,
                date=instance.processed_at.date() if instance.processed_at else timezone.now().date(),
                time=instance.processed_at.time().strftime('%H:%M') if instance.processed_at else timezone.now().time().strftime('%H:%M'),
                payment_method='BANK',
                notes=f"Auto-synced from Transfer {instance.transaction_id}"
            )
            
            logger.info(f"Created Expense {expense.id} from successful Transfer {instance.transaction_id} - Category: {category}")
            
            # UPDATE BANK ACCOUNT BALANCE - This ensures synchronization!
            update_bank_account_balance_from_transactions(instance.sender)
            
            # Create an alert for successful transfer with expense creation
            create_alert(
                user=instance.sender,
                alert_type='LARGE_TRANSACTION',
                title='Transfer Completed with Expense Record',
                message=f'Transfer of ₹{instance.amount} to {receiver_name} completed. Expense recorded in {category}.'
            )
            
    except Exception as e:
        logger.error(f"Error in transfer request signal: {str(e)}")


@receiver(post_save, sender=BankTransaction)
def sync_bank_with_expense_income(sender, instance, created, **kwargs):
    """
    Handle bank transactions - create/update Expense for DEBIT or Income for CREDIT.
    Supports both creation and updates.
    Also updates the BankAccount balance to ensure synchronization.
    """
    try:
        # Normalize transaction type
        tx_type = instance.transaction_type.upper() if instance.transaction_type else ''
        
        # Handle DEBIT → Expense
        if tx_type == 'DEBIT':
            # Check if expense already exists (for updates)
            if instance.linked_expense_id and not created:
                try:
                    expense = Expense.objects.get(id=instance.linked_expense_id)
                    # Update existing expense
                    expense.amount = float(instance.amount)
                    expense.category = instance.category or categorize_transaction(instance.description)
                    expense.description = f"Bank Debit - {instance.description}"
                    expense.date = instance.created_at.date()
                    expense.save()
                    logger.info(f"Updated Expense {expense.id} from Bank Debit {instance.id}")
                    
                    # Recalculate balance after expense update
                    update_bank_account_balance_from_transactions(instance.user)
                    return
                except Expense.DoesNotExist:
                    pass
            
            # Check for duplicates before creating
            if not created:
                return
                
            existing_expense = Expense.objects.filter(
                owner=instance.user,
                amount=float(instance.amount),
                description=instance.description,
                payment_method='BANK'
            ).exists()
            
            if not existing_expense:
                # Auto-categorize if not provided
                category = instance.category or categorize_transaction(instance.description)
                
                expense = Expense.objects.create(
                    owner=instance.user,
                    amount=float(instance.amount),
                    description=f"Bank Debit - {instance.description}",
                    category=category,
                    date=instance.created_at.date(),
                    payment_method='BANK',
                    notes=f"Auto-synced from Bank Transaction #{instance.id}"
                )
                
                # Link back to bank transaction
                instance.linked_expense_id = expense.id
                instance.save(update_fields=['linked_expense_id'])
                logger.info(f"Created Expense {expense.id} from Bank Debit {instance.id}")
                
                # UPDATE BANK ACCOUNT BALANCE - This ensures synchronization!
                update_bank_account_balance_from_transactions(instance.user)
        
        # Handle CREDIT → Income
        elif tx_type == 'CREDIT':
            # Check if income already exists (for updates)
            if instance.linked_income_id and not created:
                try:
                    income = UserIncome.objects.get(id=instance.linked_income_id)
                    # Update existing income
                    income.amount = float(instance.amount)
                    income.source = instance.source or 'Bank Transfer'
                    income.description = f"Bank Credit - {instance.description}"
                    income.date = instance.created_at.date()
                    income.save()
                    logger.info(f"Updated Income {income.id} from Bank Credit {instance.id}")
                    
                    # Recalculate balance after income update
                    update_bank_account_balance_from_transactions(instance.user)
                    return
                except UserIncome.DoesNotExist:
                    pass
            
            # Check for duplicates before creating
            if not created:
                return
                
            existing_income = UserIncome.objects.filter(
                owner=instance.user,
                amount=float(instance.amount),
                description=instance.description,
                payment_method='BANK'
            ).exists()
            
            if not existing_income:
                income = UserIncome.objects.create(
                    owner=instance.user,
                    amount=float(instance.amount),
                    description=f"Bank Credit - {instance.description}",
                    source=instance.source or 'Bank Transfer',
                    date=instance.created_at.date(),
                    payment_method='BANK',
                    is_verified=True,
                    notes=f"Auto-synced from Bank Transaction #{instance.id}"
                )
                
                # Link back to bank transaction
                instance.linked_income_id = income.id
                instance.save(update_fields=['linked_income_id'])
                logger.info(f"Created Income {income.id} from Bank Credit {instance.id}")
                
                # UPDATE BANK ACCOUNT BALANCE - This ensures synchronization!
                update_bank_account_balance_from_transactions(instance.user)
        
        # Check for large transactions and create alerts
        if detect_large_transaction(instance):
            create_alert(
                user=instance.user,
                alert_type='LARGE_TRANSACTION',
                title='Large Bank Transaction Detected',
                message=f'Unusual {"credit" if tx_type == "CREDIT" else "debit"} of ₹{instance.amount}'
            )
            
    except Exception as e:
        logger.error(f"Error in bank transaction signal: {str(e)}")


@receiver(post_delete, sender=BankTransaction)
def delete_linked_expense_income(sender, instance, **kwargs):
    """Delete linked Expense/Income when bank transaction is deleted"""
    try:
        # Delete linked expense for DEBIT
        if instance.transaction_type == 'DEBIT' and instance.linked_expense_id:
            Expense.objects.filter(id=instance.linked_expense_id).delete()
            logger.info(f"Deleted Expense {instance.linked_expense_id} from Bank Deletion")
        
        # Delete linked income for CREDIT
        elif instance.transaction_type == 'CREDIT' and instance.linked_income_id:
            UserIncome.objects.filter(id=instance.linked_income_id).delete()
            logger.info(f"Deleted Income {instance.linked_income_id} from Bank Deletion")
        
        # UPDATE BANK ACCOUNT BALANCE - This ensures synchronization after deletion!
        update_bank_account_balance_from_transactions(instance.user)
    
    except Exception as e:
        logger.error(f"Error deleting linked transaction: {str(e)}")


@receiver(post_save, sender=CardTransaction)
def handle_card_transaction(sender, instance, created, **kwargs):
    """Handle card transactions with enhanced features."""
    try:
        if not created:
            return

        # 1. Auto-categorize transaction if not already set
        if not instance.category:
            instance.category = categorize_transaction(instance.description)

        # 2. Extract merchant name if not already set
        if not instance.merchant_name:
            instance.merchant_name = extract_merchant_name(instance.description)

        # 3. Generate transaction hash for duplicate prevention
        if not instance.transaction_hash:
            instance.transaction_hash = generate_transaction_hash(
                instance.card.id,
                instance.amount,
                instance.description,
                instance.created_at
            )

        # 4. Detect recurring transactions
        if not instance.is_recurring and instance.merchant_name:
            instance.is_recurring = detect_recurring(
                instance.card,
                instance.merchant_name,
                instance.amount
            )

        # 5. Update balance_after (for credit cards)
        if instance.card.card_type == 'CREDIT' and instance.card.credit_limit:
            # For credit cards, balance_after = credit_limit - spent
            from django.db.models import Sum
            total_spent = CardTransaction.objects.filter(
                card=instance.card,
                created_at__lte=instance.created_at
            ).aggregate(total=Sum('amount'))['total'] or 0
            instance.balance_after = instance.card.credit_limit - total_spent

        # Save the updated instance
        instance.save(update_fields=[
            'category',
            'merchant_name',
            'transaction_hash',
            'is_recurring',
            'balance_after'
        ])

        # 6. Create Expense in expense tracker
        expense = Expense.objects.create(
            owner=instance.card.user,
            amount=float(instance.amount),
            description=f"{instance.description} (Card: {instance.card.card_name})",
            category=instance.category or 'Other',
            date=instance.created_at.date(),
            payment_method='CARD',
            notes=f"Card Transaction #{instance.id}"
        )
        
        # Link expense to card transaction (optional - add field if needed)
        # instance.linked_expense_id = expense.id
        # instance.save(update_fields=['linked_expense_id'])
        
        logger.info(f"Created Expense {expense.id} from Card Transaction {instance.id}")

        # 7. Check for large transaction and create alert
        if detect_large_transaction(instance):
            create_alert(
                user=instance.card.user,
                alert_type='LARGE_TRANSACTION',
                title='Large Card Transaction Detected',
                message=f'Unusual transaction of ₹{instance.amount} at {instance.merchant_name or instance.description}'
            )

        # 8. Run overall alert checks
        check_and_create_alerts(instance.card.user)
        
    except Exception as e:
        logger.error(f"Error in card transaction signal: {str(e)}")


@receiver(post_delete, sender=CardTransaction)
def delete_linked_expense_from_card(sender, instance, **kwargs):
    """Delete linked Expense when card transaction is deleted"""
    try:
        # Delete expense created from this card transaction
        Expense.objects.filter(
            owner=instance.card.user,
            amount=float(instance.amount),
            description__contains=instance.description,
            payment_method='CARD',
            date=instance.created_at.date()
        ).delete()
        logger.info(f"Deleted Expense from Card Transaction {instance.id}")
        
    except Exception as e:
        logger.error(f"Error deleting card transaction expense: {str(e)}")