"""
Test for expense calculation fix.
Validates that expenses are calculated from the last 3 months only, not from the full dataset.

This test addresses the issue where:
- 8 months of expenses (£5915.12 in last 3 months) were being divided by 3 months
- But the category_summary included ALL transactions, not just last 3 months
- Result: Artificially low monthly expenses (e.g., £91.90 instead of £1971.70)

The fix ensures that categorized_transactions are passed to calculate_all_metrics,
which enables proper filtering to last 3 months before calculating monthly averages.
"""

import unittest
from datetime import datetime, timedelta
from openbanking_engine.scoring.feature_builder import MetricsCalculator
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestExpenseCalculationFix(unittest.TestCase):
    """Test expense calculation with lookback window."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_expense_calculation_with_old_transactions(self):
        """
        Test that expenses are calculated from last 3 months only, not full dataset.
        
        Scenario: 8 months of transaction data, but only last 3 months should be used
        for expense calculations.
        """
        # Create transactions spanning 8 months
        # Old expenses (5 months ago) - should NOT be included
        old_expenses = [
            {"date": "2024-09-01", "amount": 500, "name": "OLD GROCERIES", "description": "OLD GROCERIES"},
            {"date": "2024-09-15", "amount": 300, "name": "OLD UTILITIES", "description": "OLD UTILITIES"},
            {"date": "2024-10-01", "amount": 400, "name": "OLD TRANSPORT", "description": "OLD TRANSPORT"},
            {"date": "2024-10-15", "amount": 200, "name": "OLD RENT", "description": "OLD RENT"},
            {"date": "2024-11-01", "amount": 350, "name": "OLD INSURANCE", "description": "OLD INSURANCE"},
        ]
        
        # Recent income (last 3 months) - establishes the lookback period
        recent_income = [
            {"date": "2025-03-15", "amount": -1987.13, "name": "SALARY MARCH", "description": "SALARY", "plaid_category": "INCOME_WAGES"},
            {"date": "2025-04-15", "amount": -1987.13, "name": "SALARY APRIL", "description": "SALARY", "plaid_category": "INCOME_WAGES"},
            {"date": "2025-05-15", "amount": -1987.13, "name": "SALARY MAY", "description": "SALARY", "plaid_category": "INCOME_WAGES"},
        ]
        
        # Recent expenses (last 3 months) - total £5915.12 over 3 months = £1971.71/month
        recent_expenses = []
        for month, month_name in [(3, "MARCH"), (4, "APRIL"), (5, "MAY")]:
            month_str = f"2025-{month:02d}"
            # Each month has same pattern of expenses
            recent_expenses.extend([
                {"date": f"{month_str}-01", "amount": 800, "name": f"RENT {month_name}", "description": "RENT"},
                {"date": f"{month_str}-05", "amount": 250, "name": f"UTILITIES {month_name}", "description": "UTILITIES"},
                {"date": f"{month_str}-10", "amount": 300, "name": f"TESCO {month_name}", "description": "GROCERIES"},
                {"date": f"{month_str}-15", "amount": 150, "name": f"TRANSPORT {month_name}", "description": "TRANSPORT"},
                {"date": f"{month_str}-20", "amount": 100, "name": f"PHONE {month_name}", "description": "COMMUNICATIONS"},
                {"date": f"{month_str}-25", "amount": 371.70 if month < 5 else 371.72, "name": f"OTHER {month_name}", "description": "OTHER"},
            ])
        
        all_transactions = old_expenses + recent_income + recent_expenses
        
        # Categorize all transactions
        categorized = self.categorizer.categorize_transactions(all_transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with 3-month lookback
        calculator = MetricsCalculator(lookback_months=3, transactions=all_transactions)
        
        # Calculate metrics WITH categorized_transactions (correct path)
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=all_transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        expense_metrics = metrics["expenses"]
        income_metrics = metrics["income"]
        
        # Verify income is calculated correctly (should be £1987.13)
        expected_income = 1987.13
        self.assertAlmostEqual(
            income_metrics.monthly_income,
            expected_income,
            places=1,
            msg=f"Monthly income should be £{expected_income:.2f} from last 3 months"
        )
        
        # Verify expenses are calculated from last 3 months only
        # Total in last 3 months: £5915.12
        # Monthly average: £5915.12 / 3 = £1971.71
        expected_monthly_expenses = 1971.71
        
        self.assertAlmostEqual(
            expense_metrics.monthly_essential_total,
            expected_monthly_expenses,
            places=1,
            msg=f"Monthly expenses should be £{expected_monthly_expenses:.2f} from last 3 months, "
                f"not diluted by old transactions"
        )
        
        print(f"\n✓ Expense calculation fix validated:")
        print(f"  Total transactions: {len(all_transactions)}")
        print(f"  Old transactions (excluded): {len(old_expenses)}")
        print(f"  Recent transactions (included): {len(recent_income) + len(recent_expenses)}")
        print(f"  Monthly income: £{income_metrics.monthly_income:.2f} (expected: £{expected_income:.2f})")
        print(f"  Monthly expenses: £{expense_metrics.monthly_essential_total:.2f} (expected: £{expected_monthly_expenses:.2f})")
    
    def test_expense_calculation_without_categorized_transactions(self):
        """
        Test that WITHOUT categorized_transactions parameter, calculation may be incorrect.
        
        This demonstrates the bug that was fixed: when categorized_transactions is not
        passed, the method uses the full category_summary which includes ALL transactions,
        not just the recent ones.
        """
        # Same transactions as above
        old_expenses = [
            {"date": "2024-09-01", "amount": 500, "name": "OLD GROCERIES", "description": "OLD GROCERIES"},
            {"date": "2024-10-01", "amount": 400, "name": "OLD TRANSPORT", "description": "OLD TRANSPORT"},
        ]
        
        recent_income = [
            {"date": "2025-03-15", "amount": -2000, "name": "SALARY", "description": "SALARY", "plaid_category": "INCOME_WAGES"},
            {"date": "2025-04-15", "amount": -2000, "name": "SALARY", "description": "SALARY", "plaid_category": "INCOME_WAGES"},
            {"date": "2025-05-15", "amount": -2000, "name": "SALARY", "description": "SALARY", "plaid_category": "INCOME_WAGES"},
        ]
        
        # Recent expenses: £900/month = £2700 over 3 months
        recent_expenses = [
            {"date": "2025-03-10", "amount": 900, "name": "RENT", "description": "RENT"},
            {"date": "2025-04-10", "amount": 900, "name": "RENT", "description": "RENT"},
            {"date": "2025-05-10", "amount": 900, "name": "RENT", "description": "RENT"},
        ]
        
        all_transactions = old_expenses + recent_income + recent_expenses
        
        # Categorize all transactions
        categorized = self.categorizer.categorize_transactions(all_transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with 3-month lookback
        calculator = MetricsCalculator(lookback_months=3, transactions=all_transactions)
        
        # Calculate metrics WITHOUT categorized_transactions (fallback path - may be incorrect)
        metrics_without = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=all_transactions,
            accounts=[],
            categorized_transactions=None  # Explicitly not passing it
        )
        
        # Calculate metrics WITH categorized_transactions (correct path)
        metrics_with = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=all_transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        # Without categorized_transactions, expenses might include old data
        # With categorized_transactions, expenses should be from last 3 months only
        expenses_without = metrics_without["expenses"].monthly_essential_total
        expenses_with = metrics_with["expenses"].monthly_essential_total
        
        # The version WITH categorized_transactions should use filtered data
        expected_monthly = 900.0
        
        self.assertAlmostEqual(
            expenses_with,
            expected_monthly,
            places=1,
            msg=f"With categorized_transactions: expenses should be £{expected_monthly:.2f}/month"
        )
        
        print(f"\n✓ Categorized transactions parameter test:")
        print(f"  Without categorized_transactions: £{expenses_without:.2f}/month")
        print(f"  With categorized_transactions: £{expenses_with:.2f}/month")
        print(f"  Expected (from last 3 months only): £{expected_monthly:.2f}/month")
    
    def test_record_832117_realistic_scenario(self):
        """
        Test realistic Record_832117 scenario from problem statement.
        
        Expected results:
        - Monthly Income: £1987.13 ✓ (already correct)
        - Monthly Expenses: £1971.70 (currently £91.90 - needs fix)
        - Monthly Disposable: ~£15.43
        """
        # Simulate 8 months of data with most expenses in last 3 months
        transactions = [
            # Very old transactions (Nov 2024) - should not affect calculation
            {"date": "2024-11-01", "amount": 100, "name": "OLD EXPENSE 1", "description": "OLD"},
            {"date": "2024-11-15", "amount": 200, "name": "OLD EXPENSE 2", "description": "OLD"},
            
            # Old income (Dec 2024-Feb 2025) - should not affect income calculation
            {"date": "2024-12-15", "amount": -1000, "name": "OLD JOB SALARY", "description": "OLD JOB"},
            {"date": "2025-01-15", "amount": -1000, "name": "OLD JOB SALARY", "description": "OLD JOB"},
            {"date": "2025-02-15", "amount": -1000, "name": "OLD JOB SALARY", "description": "OLD JOB"},
            
            # Recent income (March-May 2025) - £1987.13/month
            {"date": "2025-03-15", "amount": -1987.13, "name": "FULLER SMITH SALARY", "description": "FULLER SMITH SALARY", "plaid_category": "INCOME_WAGES"},
            {"date": "2025-04-15", "amount": -1987.13, "name": "FULLER SMITH SALARY", "description": "FULLER SMITH SALARY", "plaid_category": "INCOME_WAGES"},
            {"date": "2025-05-15", "amount": -1987.13, "name": "FULLER SMITH SALARY", "description": "FULLER SMITH SALARY", "plaid_category": "INCOME_WAGES"},
            
            # Recent expenses (March-May 2025) - totaling £5915.10 over 3 months
            # March: £1971.70
            {"date": "2025-03-01", "amount": 850, "name": "RENT", "description": "RENT"},
            {"date": "2025-03-05", "amount": 200, "name": "COUNCIL TAX", "description": "COUNCIL TAX"},
            {"date": "2025-03-08", "amount": 150, "name": "UTILITIES", "description": "UTILITIES"},
            {"date": "2025-03-10", "amount": 250, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-03-12", "amount": 120, "name": "TRANSPORT", "description": "TRANSPORT"},
            {"date": "2025-03-15", "amount": 80, "name": "MOBILE", "description": "MOBILE"},
            {"date": "2025-03-18", "amount": 100, "name": "INSURANCE", "description": "INSURANCE"},
            {"date": "2025-03-25", "amount": 221.70, "name": "OTHER", "description": "OTHER"},
            
            # April: £1971.70
            {"date": "2025-04-01", "amount": 850, "name": "RENT", "description": "RENT"},
            {"date": "2025-04-05", "amount": 200, "name": "COUNCIL TAX", "description": "COUNCIL TAX"},
            {"date": "2025-04-08", "amount": 150, "name": "UTILITIES", "description": "UTILITIES"},
            {"date": "2025-04-10", "amount": 250, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-04-12", "amount": 120, "name": "TRANSPORT", "description": "TRANSPORT"},
            {"date": "2025-04-15", "amount": 80, "name": "MOBILE", "description": "MOBILE"},
            {"date": "2025-04-18", "amount": 100, "name": "INSURANCE", "description": "INSURANCE"},
            {"date": "2025-04-25", "amount": 221.70, "name": "OTHER", "description": "OTHER"},
            
            # May: £1971.70
            {"date": "2025-05-01", "amount": 850, "name": "RENT", "description": "RENT"},
            {"date": "2025-05-05", "amount": 200, "name": "COUNCIL TAX", "description": "COUNCIL TAX"},
            {"date": "2025-05-08", "amount": 150, "name": "UTILITIES", "description": "UTILITIES"},
            {"date": "2025-05-10", "amount": 250, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-05-12", "amount": 120, "name": "TRANSPORT", "description": "TRANSPORT"},
            {"date": "2025-05-15", "amount": 80, "name": "MOBILE", "description": "MOBILE"},
            {"date": "2025-05-18", "amount": 100, "name": "INSURANCE", "description": "INSURANCE"},
            {"date": "2025-05-25", "amount": 221.70, "name": "OTHER", "description": "OTHER"},
        ]
        
        # Categorize and calculate
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        calculator = MetricsCalculator(lookback_months=3, transactions=transactions)
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        income = metrics["income"]
        expenses = metrics["expenses"]
        affordability = metrics["affordability"]
        
        # Verify expected results
        expected_income = 1987.13
        expected_expenses = 1971.70
        # Note: disposable uses buffered expenses (1.1x shock buffer)
        expected_disposable = expected_income - (expected_expenses * 1.1)
        
        self.assertAlmostEqual(income.monthly_income, expected_income, places=1,
                              msg=f"Income should be £{expected_income:.2f}")
        
        self.assertAlmostEqual(expenses.monthly_essential_total, expected_expenses, places=1,
                              msg=f"Expenses should be £{expected_expenses:.2f} (NOT £91.90)")
        
        # Disposable income includes 10% expense shock buffer
        self.assertAlmostEqual(affordability.monthly_disposable, expected_disposable, places=1,
                              msg=f"Disposable should be ~£{expected_disposable:.2f} (with 10% expense buffer)")
        
        print(f"\n✓ Record_832117 realistic scenario validated:")
        print(f"  Transaction count: {len(transactions)} (spanning 8 months)")
        print(f"  Monthly Income: £{income.monthly_income:.2f} (expected: £{expected_income:.2f}) ✓")
        print(f"  Monthly Expenses: £{expenses.monthly_essential_total:.2f} (expected: £{expected_expenses:.2f}) ✓")
        print(f"  Monthly Disposable: £{affordability.monthly_disposable:.2f} (expected: ~£{expected_disposable:.2f} with 10% buffer) ✓")
        print(f"  Old broken calculation would have shown expenses: ~£91.90 (FIXED) ✓")


if __name__ == "__main__":
    unittest.main()
