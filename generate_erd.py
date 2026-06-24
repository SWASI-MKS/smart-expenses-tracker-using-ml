#!/usr/bin/env python
"""
Database ER Diagram Generator
=============================
This script generates an Entity-Relationship (ER) diagram from Django models.
It uses Graphviz to create a visual representation of the database.

Usage:
    python generate_erd.py

Requirements:
    pip install graphviz django-extensions
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expensetracker.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

# Import all models
from django.apps import apps
from django.contrib.auth.models import User, Group
from django.db import models

# Try to import all app models
try:
    from expenses.models import Expense, Category, ExpenseLimit
except:
    pass

try:
    from userincome.models import Income, IncomeCategory
except:
    pass

try:
    from userpreferences.models import UserPreference, Notification
except:
    pass

try:
    from goals.models import Goal, Transaction
except:
    pass

try:
    from bank_simulator.models import BankAccount, Card, CardTransaction
except:
    pass

try:
    from userprofile.models import UserProfile
except:
    pass


def generate_erd_graphviz():
    """
    Generate ER diagram using Graphviz.
    Creates a .dot file that can be converted to image.
    """
    # Get all models
    all_models = []
    for model in apps.get_models():
        all_models.append(model)
    
    # Create DOT file content
    dot_content = '''database_diagram.dot
```
dot
digraph database_schema {
    rankdir=LR;
    node [shape=box, style=filled, fontname="Arial"];
    edge [fontname="Arial"];
    
    # Page settings
    page="11,17";
    splines=true;
    overlap=false;
    pad=0.5;
    
    # Graph styling
    bgcolor="#f5f5f5";
    node [fillcolor="#e3f2fd", color="#1565c0", penwidth=2];
    edge [color="#424242", penwidth=1.5];
    
    # Legend node
    Legend [label=<
        <table border="0" cellborder="1" cellspacing="5" cellpadding="10">
            <tr><td bgcolor="#ffcc80" colspan="2"><b>ExpenseTracker DB Schema</b></td></tr>
            <tr><td>● Foreign Key</td><td>→</td></tr>
            <tr><td>■ Model</td><td>Box</td></tr>
        </table>
