from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # ============ MAIN DASHBOARD ============
    path('', views.index, name="dashboard"),  # Main expenses list
    path('overview/', views.overview, name="overview"),  # Original dashboard
    
    # ============ FINANCIAL INTELLIGENCE ============
    path('financial-intelligence/', views.financial_intelligence, name="financial_intelligence"),
    path('api/financial-intelligence/', views.financial_intelligence_api, name="financial_intelligence_api"),
    
    # ============ STATS ============
    path('stats/', views.stats, name="stats"),
    
    # ============ CRUD OPERATIONS ============
    path('add-expense/', views.add_expense, name="add-expenses"),
    path('edit-expense/<int:id>/', views.expense_edit, name="expense-edit"),
    path('expense-delete/<int:id>/', views.delete_expense, name="expense-delete"),
    
    # ============ UTILITIES ============
    path('search-expenses/', csrf_exempt(views.search_expenses), name="search_expenses"),
    path('expense_category_summary/', views.expense_category_summary, name="expense_category_summary"),
    path('ocr-extract/', views.ocr_extract, name='ocr-extract'),
    path('predict-category/', views.predict_category, name='predict-category'),
    path('set-daily-expense-limit/', views.set_expense_limit, name="set-daily-expense-limit"),
]

# Also keep the same name alias for backward compatibility
# This allows both {% url 'expenses' %} and {% url 'dashboard' %} to work


# ================= SUGGESTIONS PAGE =================
urlpatterns += [
    path('suggestions/', views.suggestions, name="suggestions"),
]
