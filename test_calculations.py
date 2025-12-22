import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime
from openbanking_engine.categorisation. engine import TransactionCategorizer
from openbanking_engine. scoring.feature_builder import MetricsCalculator

# Load the CSV
df = pd.read_csv("categorization_results_1766415540531.csv")

# Convert dates properly
df['parsed_date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')

# Find the actual latest date
latest_date = df['parsed_date'].max()
print(f"Latest transaction date: {latest_date. strftime('%Y-%m-%d')}")

# Get last 3 complete months (excluding the partial month)
latest_month = (latest_date.year, latest_date.month)
print(f"Latest month (partial, excluded): {latest_month[0]}-{latest_month[1]: 02d}")

# Calculate the 3 complete months before
months_to_include = []
year, month = latest_month
for i in range(1, 4):  # Go back 3 months
    month -= 1
    if month == 0:
        month = 12
        year -= 1
    months_to_include.append((year, month))

months_to_include.reverse()
print(f"Expected 3 complete months: {[f'{y}-{m:02d}' for y, m in months_to_include]}")

# Filter transactions to these months
df['year_month'] = df['parsed_date'].apply(lambda x: (x.year, x.month))
filtered_df = df[df['year_month'].isin(months_to_include)]

print(f"\nFiltered to {len(filtered_df)} transactions in those 3 months")

# INCOME - Only the specified subcategories
income_filter = (
    (filtered_df['category'] == 'income') &
    filtered_df['subcategory'].isin(['salary', 'account_transfer', 'other', 'gig_economy'])
)
income_df = filtered_df[income_filter]

print(f"\n{'='*60}")
print("INCOME BREAKDOWN (Last 3 Complete Months)")
print(f"{'='*60}")

for subcat in ['salary', 'account_transfer', 'other', 'gig_economy']:
    subcat_df = income_df[income_df['subcategory'] == subcat]
    if len(subcat_df) > 0:
        total = -subcat_df['amount'].sum()  # Negative because income is negative in banking
        count = len(subcat_df)
        print(f"income/{subcat}: £{total:,.2f} ({count} txns)")

total_income = -income_df['amount'].sum()
monthly_income = total_income / 3
print(f"\nTotal Income (3 months): £{total_income:,.2f}")
print(f"Monthly Income (÷3): £{monthly_income:,.2f}")

# EXPENSES - Only the specified category/subcategory combinations
expense_filters = [
    ('expense', 'other'),
    ('expense', 'discretionary'),
    ('expense', 'account_transfer'),
    ('expense', 'gambling'),
    ('expense', 'food_dining'),
    ('debt', 'hcstc_payday'),
    ('debt', 'bnpl'),
    ('debt', 'credit_cards'),
    ('debt', 'other_loans'),
    ('essential', 'groceries'),
]

expense_dfs = []
for cat, subcat in expense_filters:
    mask = (filtered_df['category'] == cat) & (filtered_df['subcategory'] == subcat)
    expense_dfs.append(filtered_df[mask])

expense_df = pd.concat(expense_dfs, ignore_index=True)

print(f"\n{'='*60}")
print("EXPENSE BREAKDOWN (Last 3 Complete Months)")
print(f"{'='*60}")

for cat, subcat in expense_filters:
    subcat_df = expense_df[(expense_df['category'] == cat) & (expense_df['subcategory'] == subcat)]
    if len(subcat_df) > 0:
        total = subcat_df['amount']. sum()  # Positive for expenses
        count = len(subcat_df)
        print(f"{cat}/{subcat}:£{total:,.2f} ({count} txns)")

total_expenses = expense_df['amount'].sum()
monthly_expenses = total_expenses / 3
print(f"\nTotal Expenses (3 months): £{total_expenses:,.2f}")
print(f"Monthly Expenses (÷3): £{monthly_expenses:,.2f}")

print(f"\n{'='*60}")
print(f"EXPECTED RESULTS")
print(f"{'='*60}")
print(f"Monthly Income:£{monthly_income:,.2f}")
print(f"Monthly Expenses:£{monthly_expenses:,.2f}")
print(f"Monthly Disposable:£{monthly_income - monthly_expenses:,.2f}")
print(f"{'='*60}\n")
