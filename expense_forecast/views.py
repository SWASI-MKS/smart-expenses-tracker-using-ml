from django.shortcuts import render
import numpy as np
import pandas as pd
from django.utils.timezone import now
from expenses.models import Expense
from django.contrib import messages
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from django.contrib.auth.decorators import login_required
import os
from django.conf import settings
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')


def get_simple_moving_average(data, periods=3):
    """Calculate Simple Moving Average fallback"""
    if len(data) >= periods:
        avg = data.tail(periods).mean()
    else:
        avg = data.mean()
    return round(float(avg), 2)


def get_linear_regression_forecast(data, steps=30):
    """Calculate Linear Regression trend as fallback"""
    if len(data) < 2:
        return [round(float(data.mean()), 2)] * steps
    
    # Create simple linear trend
    x = np.arange(len(data))
    y = data.values
    
    # Simple linear regression
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    intercept = coeffs[1]
    
    # Generate forecast
    future_x = np.arange(len(data), len(data) + steps)
    forecast = slope * future_x + intercept
    
    # Ensure no negative values
    forecast = [max(0, round(float(v), 2)) for v in forecast]
    return forecast


@login_required(login_url='/authentication/login')
def forecast(request):
    # Handle database errors gracefully
    try:
        # Fetch expenses sorted by date (ascending for time series)
        expenses = Expense.objects.filter(owner=request.user).order_by('date')
        expense_count = len(expenses)
    except Exception as e:
        # Database schema mismatch - show error message
        messages.error(request, "Database error: Please run migrations to update the database schema. Error: " + str(e))
        return render(request, 'expense_forecast/index.html')

    # Check minimum data length for ARIMA (need at least 12 points)
    MIN_DATA_POINTS = 12
    
    if expense_count < MIN_DATA_POINTS:
        messages.error(request, f"Not enough expenses to make a forecast. Please add at least {MIN_DATA_POINTS} expenses.")
        return render(request, 'expense_forecast/index.html')

    try:
        # Create DataFrame with all expenses
        expense_data = []
        for expense in expenses:
            expense_data.append({
                'Date': expense.date, 
                'Expenses': float(expense.amount), 
                'Category': expense.category
            })
        
        data = pd.DataFrame(expense_data)
        
        # Ensure data is sorted by date
        data = data.sort_values('Date')
        
        # Aggregate expenses by date (sum all expenses for each day)
        daily_expenses = data.groupby('Date')['Expenses'].sum().reset_index()
        daily_expenses.columns = ['Date', 'Expenses']
        
        # Get total expenses for category ratio calculation
        total_expenses = daily_expenses['Expenses'].sum()
        
        # Calculate category ratios (for projected category forecasts)
        category_totals = data.groupby('Category')['Expenses'].sum().to_dict()
        category_ratios = {str(k): round(float(v) / total_expenses, 4) if total_expenses > 0 else 0 for k, v in category_totals.items()}
        
        # Set index for time series
        daily_expenses.set_index('Date', inplace=True)
        daily_expenses = daily_expenses.sort_index()
        
        # Ensure we have enough data points after processing
        if len(daily_expenses) < MIN_DATA_POINTS:
            messages.error(request, f"Not enough expense data points after processing. Please add more expenses.")
            return render(request, 'expense_forecast/index.html')
        
        # ===== Handle outliers using IQR method =====
        try:
            Q1 = daily_expenses['Expenses'].quantile(0.25)
            Q3 = daily_expenses['Expenses'].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Cap outliers instead of removing them
            daily_expenses['Expenses_Capped'] = daily_expenses['Expenses'].clip(lower=max(0, lower_bound), upper=upper_bound)
            data_for_forecast = daily_expenses['Expenses_Capped']
        except Exception:
            # If outlier handling fails, use original data
            data_for_forecast = daily_expenses['Expenses']
        
        # ===== ARIMA with proper try/except and fallback =====
        forecast_values = None
        arima_failed = False
        
        try:
            # Try ARIMA with error handling
            from statsmodels.tsa.arima.model import ARIMA
            model = ARIMA(data_for_forecast, order=(5, 1, 0))
            model_fit = model.fit()
            
            forecast_steps = 30
            current_date = now().date()
            next_day = current_date + timedelta(days=1)
            forecast_index = pd.date_range(start=next_day, periods=forecast_steps, freq='D')
            
            # Get forecast and convert to list
            forecast_values_series = model_fit.forecast(steps=forecast_steps)
            forecast_values = [max(0, round(float(x), 2)) for x in forecast_values_series.tolist()]
            
        except Exception as e:
            # ARIMA failed - will use fallback
            arima_failed = True
            print(f"ARIMA failed, using fallback: {e}")
        
        # ===== Fallback if ARIMA failed =====
        if arima_failed or forecast_values is None:
            # Use Linear Regression as primary fallback
            forecast_values = get_linear_regression_forecast(data_for_forecast, 30)
            
            current_date = now().date()
            next_day = current_date + timedelta(days=1)
            forecast_index = pd.date_range(start=next_day, periods=30, freq='D')
        
        # Calculate total forecasted expenses
        total_forecasted_expenses = round(sum(forecast_values), 2)
        
        # ===== Calculate projected category forecasts =====
        # Use category ratios to project future spending
        projected_category_forecasts = {}
        for category, ratio in category_ratios.items():
            projected_amount = round(total_forecasted_expenses * ratio, 2)
            projected_category_forecasts[category] = projected_amount
        
        # Create forecast data list for template
        forecast_data_list = []
        for i in range(len(forecast_index)):
            forecast_data_list.append({
                'Date': forecast_index[i].strftime('%Y-%m-%d'),
                'Forecasted_Expenses': forecast_values[i]
            })
        
        # ===== FIX Plot dimension mismatch =====
        try:
            # Create static/img directory if it doesn't exist
            static_dir = os.path.join(settings.BASE_DIR, 'static')
            img_dir = os.path.join(static_dir, 'img')
            os.makedirs(img_dir, exist_ok=True)
            
            # Prepare data for plotting
            hist_dates = daily_expenses.index[-15:] if len(daily_expenses) > 15 else daily_expenses.index
            hist_values = daily_expenses['Expenses'].loc[hist_dates].values
            
            # Trim forecast to match historical data length for visualization
            fore_dates = forecast_index[:15]
            fore_values = forecast_values[:15]
            
            # Ensure arrays have same length for the visualization
            min_len = min(len(hist_dates), len(fore_dates))
            
            # Create plot
            plt.figure(figsize=(12, 6))
            
            # Plot historical data
            plt.plot(hist_dates[:min_len], hist_values[:min_len], 'b-o', 
                     label='Historical', linewidth=2, markersize=4)
            
            # Plot forecast
            plt.plot(fore_dates[:min_len], fore_values[:min_len], 'r--s', 
                     label='Forecast', linewidth=2, markersize=4)
            
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Expenses ($)', fontsize=12)
            plt.title(f'30-Day Expense Forecast - {request.user.username}', fontsize=14)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot
            plot_path = os.path.join(img_dir, 'forecast_plot.png')
            plt.savefig(plot_path, dpi=100, bbox_inches='tight')
            plt.close()
            
        except Exception:
            # Silently handle plot errors - don't show to user
            pass
        
        # Context for template
        context = {
            'forecast_data': forecast_data_list,
            'total_forecasted_expenses': total_forecasted_expenses,
            'category_forecasts': projected_category_forecasts,  # Now shows projected values
        }
        
        return render(request, 'expense_forecast/index.html', context)
        
    except Exception as e:
        print(f"Error calculating predictions: {e}")
        # Catch-all for any unexpected errors
        context = {
            'forecast_data': [],
            'total_forecasted_expenses': 0,
            'category_forecasts': {},
        }
        return render(request, 'expense_forecast/index.html', context)
