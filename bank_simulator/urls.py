from django.urls import path
from . import views

urlpatterns = [
    path('add-card/', views.add_card, name='add-card'),
    path('', views.bank_dashboard, name='bank-dashboard'),
    path('card-swipe/', views.card_swipe, name='card-swipe'),
    # PHASE 5: CSV Import
    path('csv-import/', views.csv_import, name='csv-import'),
    # PHASE 6: Alerts
    path('alerts/', views.alerts, name='alerts'),
    path('alerts/mark-read/', views.mark_alert_as_read, name='mark-alert-read'),
    path('alerts/mark-all-read/', views.mark_all_alerts_read, name='mark-all-alerts-read'),
    
    # NEW BANKING PAGES
    path('send-money/', views.send_money, name='send-money'),
    path('confirm-transfer/<int:transfer_id>/', views.confirm_transfer, name='confirm-transfer'),
    path('process-transfer/<int:transfer_id>/', views.process_transfer, name='process-transfer'),
    path('transfer-success/<int:transfer_id>/', views.transfer_success, name='transfer-success'),
    path('transfer-failed/<int:transfer_id>/', views.transfer_failed, name='transfer-failed'),
    
    # NEW PAGES
    path('transactions/', views.transaction_history, name='transaction-history'),
    path('cards/', views.cards_view, name='cards-view'),
    path('card/<int:card_id>/transactions/', views.card_transactions_view, name='card-transactions'),
    path('analytics/', views.analytics_view, name='analytics-view'),
    path('merchants/', views.merchants_view, name='merchants-view'),
    path('beneficiaries/', views.beneficiaries_view, name='beneficiaries'),
    path('beneficiaries/delete/', views.delete_beneficiary, name='delete-beneficiary'),
    
    # Bank Transaction Integration APIs
    path('sync/', views.sync_bank_api, name='sync-bank-api'),
    path('sync-all/', views.sync_all_users_api, name='sync-all-users-api'),
    path('auto-sync/', views.auto_sync_api, name='auto-sync-api'),
    path('update-balance/', views.update_balance_api, name='update-balance-api'),
    path('monthly-summary/', views.monthly_summary_api, name='monthly-summary-api'),
    path('dashboard-analytics/', views.dashboard_analytics_api, name='dashboard-analytics-api'),
    path('transaction-history/', views.transaction_history_api, name='transaction-history-api'),
    path('net-worth/', views.net_worth_api, name='net-worth-api'),
    path('category-totals/', views.category_totals_api, name='category-totals-api'),
]
