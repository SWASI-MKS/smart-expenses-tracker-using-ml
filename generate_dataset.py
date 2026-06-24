import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# Configuration
num_rows = 650
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 6, 30)

# Categories with their base probabilities and amount ranges
categories_config = {
    'Food': {
        'prob': 0.28,
        'amount_range': (50, 800),
        'large_prob': 0.10,  # 10% chance of large transaction
        'large_range': (1500, 3500)  # Restaurant parties, catering
    },
    'Transport': {
        'prob': 0.18,
        'amount_range': (50, 500),
        'large_prob': 0.05,
        'large_range': (2000, 4000)  # Vehicle maintenance, flight tickets
    },
    'Shopping': {
        'prob': 0.15,
        'amount_range': (200, 1500),
        'large_prob': 0.15,
        'large_range': (2000, 5000)  # Electronics, clothes haul
    },
    'Entertainment': {
        'prob': 0.10,
        'amount_range': (100, 1000),
        'large_prob': 0.08,
        'large_range': (2000, 4000)  # Concert tickets, weekend getaways
    },
    'Bills': {
        'prob': 0.12,
        'amount_range': (500, 3000),
        'large_prob': 0.02,
        'large_range': (3500, 5000)  # Large utility bills
    },
    'Health': {
        'prob': 0.08,
        'amount_range': (100, 1200),
        'large_prob': 0.12,
        'large_range': (2500, 5000)  # Medical emergencies
    },
    'Education': {
        'prob': 0.09,
        'amount_range': (200, 1500),
        'large_prob': 0.10,
        'large_range': (3000, 5000)  # Course fees, books
    }
}

# Payment methods and card types
payment_methods = ['Debit Card', 'Credit Card']
card_types = ['Visa', 'Mastercard', 'RuPay']

# Payment method probabilities (more debit cards for small amounts, credit for large)
payment_probs = {
    'Debit Card': 0.6,
    'Credit Card': 0.4
}

# Card type distribution
card_type_probs = {
    'Visa': 0.4,
    'Mastercard': 0.35,
    'RuPay': 0.25
}

# Day of week names
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Generate dates
date_range = pd.date_range(start=start_date, end=end_date, freq='D')
all_dates = []

# Create date distribution with more transactions on weekends
for date in date_range:
    # More transactions on weekends
    if date.weekday() >= 5:  # Saturday, Sunday
        num_transactions = np.random.poisson(8)  # 8 avg on weekends
    else:
        num_transactions = np.random.poisson(5)  # 5 avg on weekdays
    
    for _ in range(num_transactions):
        all_dates.append(date)

# Trim to exact number of rows
if len(all_dates) > num_rows:
    all_dates = random.sample(all_dates, num_rows)
elif len(all_dates) < num_rows:
    # Add more dates if needed
    additional = num_rows - len(all_dates)
    all_dates.extend(random.choices(date_range, k=additional))

random.shuffle(all_dates)

# Generate dataset
data = []

# Track monthly bills
bills_paid = {month: False for month in range(1, 7)}

for date in all_dates[:num_rows]:
    # Select category based on probabilities
    categories = list(categories_config.keys())
    probs = [categories_config[cat]['prob'] for cat in categories]
    probs = [p / sum(probs) for p in probs]  # Normalize
    category = np.random.choice(categories, p=probs)
    
    # Special handling for Bills - ensure monthly occurrence
    if category == 'Bills':
        month = date.month
        if bills_paid.get(month, False):
            # Already paid bills this month, reduce probability
            if random.random() < 0.7:  # 70% chance to override
                # Choose different category
                other_cats = [c for c in categories if c != 'Bills']
                other_probs = [categories_config[c]['prob'] for c in other_cats]
                other_probs = [p / sum(other_probs) for p in other_probs]
                category = np.random.choice(other_cats, p=other_probs)
            else:
                bills_paid[month] = True
        else:
            # Pay bills this month
            bills_paid[month] = True
    
    # Determine if this is a large transaction
    config = categories_config[category]
    is_large = random.random() < config['large_prob']
    
    if is_large:
        amount = round(random.uniform(*config['large_range']), 2)
        # Large transactions more likely on weekends
        if date.weekday() < 5 and random.random() < 0.5:
            # Move to weekend for realistic large purchases
            days_to_add = 5 - date.weekday()
            date += timedelta(days=days_to_add)
    else:
        amount = round(random.uniform(*config['amount_range']), 2)
    
    # Select payment method (Credit Card more likely for large amounts)
    if amount > 2000:
        payment_method = np.random.choice(['Credit Card', 'Debit Card'], p=[0.8, 0.2])
    else:
        payment_method = np.random.choice(payment_methods, p=[0.4, 0.6])
    
    # Select card type
    card_type = np.random.choice(card_types, p=list(card_type_probs.values()))
    
    # Get day of week
    day_of_week = days[date.weekday()]
    
    # Add some realistic patterns
    if category == 'Food' and amount < 100 and date.weekday() < 5:
        # Small food transactions more likely on weekdays (lunch)
        pass
    
    if category == 'Entertainment' and date.weekday() < 5:
        # Entertainment more likely on weekends
        if random.random() < 0.3:  # 30% chance to move to weekend
            days_to_add = 5 - date.weekday()
            date += timedelta(days=days_to_add)
            day_of_week = days[date.weekday()]
    
    if category == 'Shopping' and amount > 2000:
        # Large shopping on weekends or month-end
        if date.day < 25 and random.random() < 0.6:
            # Move to month-end
            date = date.replace(day=28)
            day_of_week = days[date.weekday()]
    
    data.append({
        'date': date.strftime('%Y-%m-%d'),
        'amount': amount,
        'category': category,
        'payment_method': payment_method,
        'card_type': card_type,
        'day_of_week': day_of_week
    })

# Sort by date
data.sort(key=lambda x: x['date'])

# Create DataFrame
df = pd.DataFrame(data)

# Add some anomalies (very large transactions)
anomalies = [
    {'date': '2025-02-14', 'amount': 4500, 'category': 'Shopping', 
     'payment_method': 'Credit Card', 'card_type': 'Mastercard', 
     'day_of_week': 'Friday'},  # Valentine's day splurge
    {'date': '2025-04-01', 'amount': 5000, 'category': 'Education', 
     'payment_method': 'Credit Card', 'card_type': 'Visa', 
     'day_of_week': 'Tuesday'},  # Course fee
    {'date': '2025-05-20', 'amount': 4800, 'category': 'Health', 
     'payment_method': 'Credit Card', 'card_type': 'Visa', 
     'day_of_week': 'Tuesday'},  # Medical emergency
    {'date': '2025-03-15', 'amount': 4200, 'category': 'Entertainment', 
     'payment_method': 'Credit Card', 'card_type': 'Mastercard', 
     'day_of_week': 'Saturday'},  # Concert tickets
    {'date': '2025-06-10', 'amount': 3800, 'category': 'Transport', 
     'payment_method': 'Credit Card', 'card_type': 'RuPay', 
     'day_of_week': 'Tuesday'},  # Flight booking
]

for anomaly in anomalies:
    df = pd.concat([df, pd.DataFrame([anomaly])], ignore_index=True)

# Sort again
df = df.sort_values('date').reset_index(drop=True)

# Final dataset stats
print(f"Generated {len(df)} rows of data")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print("\nCategory distribution:")
print(df['category'].value_counts(normalize=True).round(3))
print("\nAmount statistics:")
print(df['amount'].describe().round(2))
print("\nLarge transactions (>2000):", len(df[df['amount'] > 2000]))

# Save to CSV
df.to_csv('expense_tracker_dataset.csv', index=False)
print("\nDataset saved to 'expense_tracker_dataset.csv'")