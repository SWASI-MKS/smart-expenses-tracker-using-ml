from django.urls import path
from . import views

urlpatterns = [
    path('', views.debt_list, name='debt-list'),
    path('dashboard/', views.debt_dashboard, name='debt-dashboard'),
    path('add/', views.add_debt, name='add-debt'),
    path('<int:debt_id>/', views.debt_detail, name='debt-detail'),
    path('<int:debt_id>/edit/', views.edit_debt, name='edit-debt'),
    path('<int:debt_id>/delete/', views.delete_debt, name='delete-debt'),
    path('<int:debt_id>/record-emi/', views.record_emi, name='record-emi'),
]
