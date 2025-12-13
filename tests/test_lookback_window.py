"""
Test for income/expense lookback window functionality.
Validates that income/expense calculations use recent transactions while risk metrics use full history.
"""

import unittest
from datetime import datetime, timedelta
from openbanking_engine.scoring.feature_builder import MetricsCalculator
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestLookbackWindow(unittest.TestCase):
    """Test lookback window functionality for income/expense vs risk metrics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_3_month_lookback_filters_old_transactions(self):
        """Test that 3-month lookback only uses last 3 months for income/expense."""
        # Transactions spanning 7 months (Nov 2024 - May 2025)
        # But most recent income is in last 3 months (March-May 2025)
        transactions = [
            # Old income from November 2024 (should be excluded)
            {"date": "2024-11-01", "amount": -1000, "name": "OLD SALARY", "description": "OLD SALARY"},
            {"date": "2024-11-15", "amount": 100, "name": "OLD EXPENSE", "description": "OLD EXPENSE"},
            
            # Recent income from March-May 2025 (should be included)
            {"date": "2025-03-01", "amount": -1533.24, "name": "FULLER SMITH SALARY", "description": "FULLER SMITH SALARY"},
            {"date": "2025-03-15", "amount": 50, "name": "GROCERIES", "description": "GROCERIES"},
            {"date": "2025-04-01", "amount": -1533.24, "name": "FULLER SMITH SALARY", "description": "FULLER SMITH SALARY"},
            {"date": "2025-04-20", "amount": 75, "name": "TRANSPORT", "description": "TRANSPORT"},
            {"date": "2025-05-01", "amount": -1533.25, "name": "FULLER SMITH SALARY", "description": "FULLER SMITH SALARY"},
            {"date": "2025-05-25", "amount": 100, "name": "UTILITIES", "description": "UTILITIES"},
        ]
        
        # Categorize all transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with 3-month lookback
        calculator = MetricsCalculator(lookback_months=3, transactions=transactions)
        
        # Calculate metrics with categorized transactions
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        income_metrics = metrics["income"]
        
        # Expected: Only last 3 months (March-May) = 4599.73 total / 3 months = ~1533.24/month
        expected_monthly = 1533.24
        
        self.assertAlmostEqual(
            income_metrics.monthly_income,
            expected_monthly,
            places=1,
            msg=f"Monthly income should be ~{expected_monthly} (from last 3 months only), "
                f"not diluted by old November transaction"
        )
        
        print(f"\n✓ Lookback window test passed:")
        print(f"  Total income (last 3 months): £{income_metrics.total_income:.2f}")
        print(f"  Monthly income: £{income_metrics.monthly_income:.2f}")
        print(f"  Expected: £{expected_monthly:.2f}")
    
    def test_risk_metrics_use_full_history(self):
        """Test that risk metrics (HCSTC, gambling, etc.) use full transaction history."""
        # Transactions with HCSTC from 6 months ago and recent income
        transactions = [
            # Old HCSTC activity (6 months ago) - should be detected
            {"date": "2024-11-01", "amount": 100, "name": "LENDING STREAM", "description": "LENDING STREAM"},
            {"date": "2024-12-01", "amount": 100, "name": "MR LENDER", "description": "MR LENDER"},
            
            # Recent income (last 3 months)
            {"date": "2025-03-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-04-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-05-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
        ]
        
        # Categorize all transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with 3-month lookback
        calculator = MetricsCalculator(lookback_months=3, transactions=transactions)
        
        # Calculate metrics
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        debt_metrics = metrics["debt"]
        
        # Should detect HCSTC lenders from full history (even though they're older than 3 months)
        self.assertGreater(
            debt_metrics.active_hcstc_count,
            0,
            "Should detect HCSTC lenders from full transaction history, not just last 3 months"
        )
        
        print(f"\n✓ Risk metrics full history test passed:")
        print(f"  HCSTC lenders detected: {debt_metrics.active_hcstc_count}")
        print(f"  (from full history including old transactions)")
    
    def test_configurable_lookback_period(self):
        """Test that lookback period is configurable."""
        transactions = [
            # Older transactions (4-6 months ago) with lower salary
            {"date": "2024-11-20", "amount": -1000, "name": "ACME LTD SALARY", "description": "ACME LTD SALARY"},
            {"date": "2024-12-20", "amount": -1000, "name": "ACME LTD SALARY", "description": "ACME LTD SALARY"},
            {"date": "2025-01-20", "amount": -1000, "name": "ACME LTD SALARY", "description": "ACME LTD SALARY"},
            # Recent 3 months with higher salary
            {"date": "2025-03-20", "amount": -2000, "name": "NEW COMPANY SALARY", "description": "NEW COMPANY SALARY"},
            {"date": "2025-04-20", "amount": -2000, "name": "NEW COMPANY SALARY", "description": "NEW COMPANY SALARY"},
            {"date": "2025-05-20", "amount": -2000, "name": "NEW COMPANY SALARY", "description": "NEW COMPANY SALARY"},
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Test with 3-month lookback (should include Mar, Apr, May = £6000 / 3 = £2000/month)
        calculator_3m = MetricsCalculator(lookback_months=3, transactions=transactions)
        metrics_3m = calculator_3m.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        # Test with 6-month lookback (should include all 6 transactions)
        calculator_6m = MetricsCalculator(lookback_months=6, transactions=transactions)
        metrics_6m = calculator_6m.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        # 3-month lookback should only include recent higher salary (£6000 / 3 = £2000/month)
        self.assertAlmostEqual(metrics_3m["income"].monthly_income, 2000, places=0,
                              msg=f"3-month lookback should give £2000/month, got £{metrics_3m['income'].monthly_income:.2f}")
        
        # 6-month lookback: Note that 6 months (180 days) from May 20 = Nov 21,
        # so excludes Nov 20 transaction. Includes 5 transactions (Dec, Jan, Mar, Apr, May)
        # £8000 / 6 months = £1333.33/month
        # This demonstrates that a longer lookback smooths out income variations
        self.assertLess(metrics_6m["income"].monthly_income, metrics_3m["income"].monthly_income,
                       "6-month lookback should show lower average due to older lower-paying job")
        
        print(f"\n✓ Configurable lookback test passed:")
        print(f"  3-month monthly income: £{metrics_3m['income'].monthly_income:.2f}")
        print(f"  6-month monthly income: £{metrics_6m['income'].monthly_income:.2f}")
    
    def test_record_832117_scenario(self):
        """
        Test the real-world Record_832117 scenario from problem statement.
        
        Expected:
        - Actual salary (March-May 2025): £4,599.73
        - Expected monthly income: ~£1,533 (£4,599.73 ÷ 3)
        - Old calculation (wrong): £615.87 (diluted by 7+ months span)
        """
        transactions = [
            # Old transactions from November 2024 (should not dilute income calculation)
            {"date": "2024-11-10", "amount": 50, "name": "GAMBLING", "description": "GAMBLING"},
            {"date": "2024-11-15", "amount": 100, "name": "LENDING STREAM", "description": "LENDING STREAM"},
            
            # Recent salary from Fuller Smith & Turner (March-May 2025)
            # Using SALARY keyword to ensure proper categorization
            {"date": "2025-03-15", "amount": -1533.24, "name": "SALARY FULLER SMITH TURNER", "description": "SALARY FULLER SMITH TURNER"},
            {"date": "2025-03-20", "amount": 200, "name": "RENT", "description": "RENT"},
            {"date": "2025-04-15", "amount": -1533.24, "name": "SALARY FULLER SMITH TURNER", "description": "SALARY FULLER SMITH TURNER"},
            {"date": "2025-04-25", "amount": 150, "name": "UTILITIES", "description": "UTILITIES"},
            {"date": "2025-05-15", "amount": -1533.25, "name": "SALARY FULLER SMITH TURNER", "description": "SALARY FULLER SMITH TURNER"},
            {"date": "2025-05-20", "amount": 100, "name": "GROCERIES", "description": "GROCERIES"},
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with 3-month lookback (default)
        calculator = MetricsCalculator(lookback_months=3, transactions=transactions)
        
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            categorized_transactions=categorized
        )
        
        income_metrics = metrics["income"]
        risk_metrics = metrics["risk"]
        debt_metrics = metrics["debt"]
        
        # Verify monthly income is correct (~£1,533, NOT £615.87)
        expected_monthly_income = 1533.24
        self.assertAlmostEqual(
            income_metrics.monthly_income,
            expected_monthly_income,
            places=0,
            msg=f"Monthly income should be ~£{expected_monthly_income} from last 3 months"
        )
        
        # Verify risk metrics still detect old HCSTC activity
        self.assertGreater(
            debt_metrics.active_hcstc_count,
            0,
            "Should detect HCSTC lender (Lending Stream) from full history"
        )
        
        print(f"\n✓ Record_832117 scenario validated:")
        print(f"  Total salary (March-May): £{income_metrics.total_income:.2f}")
        print(f"  Monthly income: £{income_metrics.monthly_income:.2f}")
        print(f"  Expected: £{expected_monthly_income:.2f}")
        print(f"  HCSTC lenders detected: {debt_metrics.active_hcstc_count} (from full history)")
        print(f"  Old calculation would have been: ~£615.87 (FIXED ✓)")


if __name__ == "__main__":
    unittest.main()
