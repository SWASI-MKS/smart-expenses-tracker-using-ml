# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class BankSimulatorAlert(models.Model):
    id = models.BigAutoField(primary_key=True)
    alert_type = models.CharField(max_length=30)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.IntegerField()
    created_at = models.DateTimeField()
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    is_dismissed = models.IntegerField()
    priority = models.CharField(max_length=10)
    related_bank_transaction = models.ForeignKey('BankSimulatorBanktransaction', models.DO_NOTHING, blank=True, null=True)
    related_card_transaction = models.ForeignKey('BankSimulatorCardtransaction', models.DO_NOTHING, blank=True, null=True)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'bank_simulator_alert'


class BankSimulatorBankaccount(models.Model):
    id = models.BigAutoField(primary_key=True)
    account_number = models.CharField(unique=True, max_length=20)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField()
    user = models.OneToOneField(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bank_simulator_bankaccount'


class BankSimulatorBanktransaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=6)
    description = models.CharField(max_length=255)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField()
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    source = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    linked_income_id = models.IntegerField(blank=True, null=True)
    linked_expense_id = models.IntegerField(blank=True, null=True)
    transaction_hash = models.CharField(max_length=64)

    class Meta:
        managed = False
        db_table = 'bank_simulator_banktransaction'


class BankSimulatorBeneficiary(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=20)
    upi_id = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    is_verified = models.IntegerField()
    is_active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bank_simulator_beneficiary'


class BankSimulatorCard(models.Model):
    id = models.BigAutoField(primary_key=True)
    card_name = models.CharField(max_length=100)
    card_type = models.CharField(max_length=10)
    last_four_digits = models.CharField(max_length=4)
    limit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    bank_name = models.CharField(max_length=100)
    card_brand = models.CharField(max_length=20)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    is_active = models.IntegerField()
    card_number = models.CharField(unique=True, max_length=16, blank=True, null=True)
    created_at = models.DateTimeField()
    cvv = models.CharField(max_length=4)
    expiry_date = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'bank_simulator_card'


class BankSimulatorCardtransaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    card = models.ForeignKey(BankSimulatorCard, models.DO_NOTHING)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    category = models.CharField(max_length=100)
    is_recurring = models.IntegerField()
    merchant_name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20)
    transaction_hash = models.CharField(max_length=64)
    linked_expense_id = models.IntegerField(blank=True, null=True)
    transaction_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'bank_simulator_cardtransaction'


class BankSimulatorTransactionstatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=20)
    status_message = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    transfer = models.ForeignKey('BankSimulatorTransferrequest', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bank_simulator_transactionstatus'


class BankSimulatorTransferrequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    transaction_id = models.CharField(unique=True, max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255)
    transfer_type = models.CharField(max_length=20)
    receiver_account = models.CharField(max_length=20)
    receiver_name = models.CharField(max_length=100)
    receiver_ifsc = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    status_message = models.CharField(max_length=255)
    pin_verified = models.IntegerField()
    otp_verified = models.IntegerField()
    otp_code = models.CharField(max_length=6)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    failure_reason = models.CharField(max_length=255)
    beneficiary = models.ForeignKey(BankSimulatorBeneficiary, models.DO_NOTHING, blank=True, null=True)
    sender = models.ForeignKey(AuthUser, models.DO_NOTHING)
    linked_expense_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bank_simulator_transferrequest'


class DebtsDebt(models.Model):
    id = models.BigAutoField(primary_key=True)
    loan_name = models.CharField(max_length=200)
    loan_type = models.CharField(max_length=20)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    loan_term_months = models.IntegerField()
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    next_emi_date = models.DateField()
    lender_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    notes = models.TextField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'debts_debt'


class DebtsEmipayment(models.Model):
    id = models.BigAutoField(primary_key=True)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_portion = models.DecimalField(max_digits=12, decimal_places=2)
    interest_portion = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.IntegerField()
    paid_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    created_at = models.DateTimeField()
    debt = models.ForeignKey(DebtsDebt, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'debts_emipayment'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class ExpensesCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=266)
    budget_limit = models.FloatField()
    color = models.CharField(max_length=20, blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_global = models.IntegerField()
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'expenses_category'


class ExpensesExpense(models.Model):
    id = models.BigAutoField(primary_key=True)
    amount = models.FloatField()
    date = models.DateField()
    description = models.TextField()
    category = models.CharField(max_length=266)
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)
    is_recurring = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=20)
    receipt = models.CharField(max_length=100, blank=True, null=True)
    recurring_frequency = models.CharField(max_length=20)
    tags = models.JSONField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    time = models.TimeField()

    class Meta:
        managed = False
        db_table = 'expenses_expense'


class ExpensesExpenselimit(models.Model):
    id = models.BigAutoField(primary_key=True)
    daily_expense_limit = models.FloatField()
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING)
    monthly_expense_limit = models.FloatField()

    class Meta:
        managed = False
        db_table = 'expenses_expenselimit'


class GoalsGoal(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    amount_to_save = models.DecimalField(max_digits=10, decimal_places=2)
    current_saved_amount = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING)
    status = models.CharField(max_length=20)
    is_achieved = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'goals_goal'


class UserincomeSource(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=7)
    is_active = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'userincome_source'


class UserincomeUserincome(models.Model):
    id = models.BigAutoField(primary_key=True)
    amount = models.FloatField()
    date = models.DateField()
    description = models.TextField()
    source = models.CharField(max_length=266)
    owner = models.ForeignKey(AuthUser, models.DO_NOTHING)
    is_recurring = models.IntegerField()
    recurring_frequency = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=20)
    is_verified = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'userincome_userincome'


class UserpreferencesNotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.IntegerField()
    created_at = models.DateTimeField()
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    send_email = models.IntegerField()
    type = models.CharField(max_length=20)
    event_hash = models.CharField(max_length=64, blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)
    related_object_id = models.IntegerField(blank=True, null=True)
    related_object_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'userpreferences_notification'


class UserpreferencesUserpreference(models.Model):
    id = models.BigAutoField(primary_key=True)
    currency = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(AuthUser, models.DO_NOTHING)
    daily_summary_enabled = models.IntegerField()
    daily_summary_time = models.TimeField()
    last_summary_sent_at = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'userpreferences_userpreference'


class UserprofileUserprofile(models.Model):
    id = models.BigAutoField(primary_key=True)
    profile_image = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    user = models.OneToOneField(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'userprofile_userprofile'
