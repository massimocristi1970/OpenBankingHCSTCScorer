"""
Test for debt metrics time basis consistency.
Validates that debt metrics use the same time period (lookback_months) as expenses.
"""

import unittest
from datetime import datetime, timedelta
from openbanking_engine.scoring.feature_builder import MetricsCalculator
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestDebtTimeBasis(unittest.TestCase):
    """Test debt metrics time basis alignment with expenses."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_debt_concentrated_in_recent_period(self):
        """
        Test Example 1 from problem statement: Debt concentrated in recent period.
        
        Scenario:
        - 12 months of transaction data
        - £1,800 in credit card payments (all in last 3 complete months)
        - Current (WRONG): £1,800 / 12 = £150/month (understated by 4x!)
        - Should be: £1,800 / 3 = £600/month
        
        Note: Latest transaction is in June, so last 3 COMPLETE months are Mar, Apr, May.
        """
        transactions = [
            # Old months (9 months ago - no debt)
            {"date": "2024-06-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-07-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-08-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-09-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-10-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-11-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-12-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-01-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-02-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            
            # Last 3 COMPLETE months with concentrated debt (£600/month)
            {"date": "2025-03-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-03-15", "amount": 600, "name": "BARCLAYCARD", "description": "CREDIT CARD PAYMENT"},
            
            {"date": "2025-04-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-04-15", "amount": 600, "name": "BARCLAYCARD", "description": "CREDIT CARD PAYMENT"},
            
            {"date": "2025-05-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-05-15", "amount": 600, "name": "BARCLAYCARD", "description": "CREDIT CARD PAYMENT"},
            
            # Current (partial) month - June (will be excluded from calculation)
            {"date": "2025-06-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-06-05", "amount": 50, "name": "GROCERIES", "description": "GROCERIES"},
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
        
        # Expected: £1,800 total in last 3 months / 3 = £600/month
        expected_monthly_debt = 600.0
        
        self.assertAlmostEqual(
            debt_metrics.monthly_credit_card_payments,
            expected_monthly_debt,
            places=0,
            msg=f"Monthly credit card payments should be £{expected_monthly_debt} (£1,800 / 3 months), "
                f"not £150 (£1,800 / 12 months)"
        )
        
        print(f"\n✓ Concentrated debt test passed:")
        print(f"  Monthly credit card payment: £{debt_metrics.monthly_credit_card_payments:.2f}")
        print(f"  Expected: £{expected_monthly_debt:.2f}")
        print(f"  Old calculation (WRONG): £150.00")
    
    def test_debt_and_expenses_use_same_time_basis(self):
        """
        Test that debt and expenses are both calculated over the same lookback period.
        
        This ensures affordability calculations are consistent.
        """
        transactions = [
            # Old months (6 months ago)
            {"date": "2024-11-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-11-15", "amount": 200, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2024-11-20", "amount": 100, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            {"date": "2024-12-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-12-15", "amount": 200, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2024-12-20", "amount": 100, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            {"date": "2025-01-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-01-15", "amount": 200, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-01-20", "amount": 100, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            # Recent 3 complete months (different pattern)
            {"date": "2025-03-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-03-15", "amount": 300, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-03-20", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            {"date": "2025-04-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-04-15", "amount": 300, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-04-20", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            {"date": "2025-05-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-05-15", "amount": 300, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-05-20", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            # Current partial month (June - will be excluded)
            {"date": "2025-06-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-06-05", "amount": 50, "name": "UTILITIES", "description": "UTILITIES"},
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
        
        expense_metrics = metrics["expenses"]
        debt_metrics = metrics["debt"]
        
        # Both should be based on last 3 months
        # Groceries: £900 / 3 = £300/month
        expected_groceries = 300.0
        # Credit card: £600 / 3 = £200/month
        expected_credit_card = 200.0
        
        self.assertAlmostEqual(
            expense_metrics.monthly_groceries,
            expected_groceries,
            places=0,
            msg=f"Groceries should be £{expected_groceries}/month from last 3 months"
        )
        
        self.assertAlmostEqual(
            debt_metrics.monthly_credit_card_payments,
            expected_credit_card,
            places=0,
            msg=f"Credit card should be £{expected_credit_card}/month from last 3 months"
        )
        
        print(f"\n✓ Consistent time basis test passed:")
        print(f"  Monthly groceries: £{expense_metrics.monthly_groceries:.2f} (from last 3 months)")
        print(f"  Monthly credit card: £{debt_metrics.monthly_credit_card_payments:.2f} (from last 3 months)")
        print(f"  Both use same lookback period ✓")
    
    def test_multiple_debt_types_same_period(self):
        """Test that all debt types use the same lookback period."""
        transactions = [
            # Old debt (12 months ago) - should be excluded
            {"date": "2024-06-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2024-06-15", "amount": 500, "name": "WONGA", "description": "HCSTC PAYDAY"},
            {"date": "2024-06-20", "amount": 100, "name": "KLARNA", "description": "BNPL"},
            
            # Recent 3 months with different debt
            {"date": "2025-03-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-03-10", "amount": 150, "name": "WONGA", "description": "HCSTC PAYDAY"},
            {"date": "2025-03-15", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            {"date": "2025-03-20", "amount": 50, "name": "KLARNA", "description": "BNPL"},
            
            {"date": "2025-04-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-04-10", "amount": 150, "name": "WONGA", "description": "HCSTC PAYDAY"},
            {"date": "2025-04-15", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            {"date": "2025-04-20", "amount": 50, "name": "KLARNA", "description": "BNPL"},
            
            {"date": "2025-05-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-05-10", "amount": 150, "name": "WONGA", "description": "HCSTC PAYDAY"},
            {"date": "2025-05-15", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            {"date": "2025-05-20", "amount": 50, "name": "KLARNA", "description": "BNPL"},
            
            # Current partial month (June - will be excluded)
            {"date": "2025-06-01", "amount": -2000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-06-05", "amount": 100, "name": "GROCERIES", "description": "GROCERIES"},
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
        
        # All debt should be from last 3 months only
        # HCSTC: £450 / 3 = £150/month
        expected_hcstc = 150.0
        # Credit card: £600 / 3 = £200/month
        expected_credit_card = 200.0
        # BNPL: £150 / 3 = £50/month
        expected_bnpl = 50.0
        # Total debt: £400/month
        expected_total = 400.0
        
        self.assertAlmostEqual(
            debt_metrics.monthly_hcstc_payments,
            expected_hcstc,
            places=0,
            msg=f"HCSTC should be £{expected_hcstc}/month from last 3 months"
        )
        
        self.assertAlmostEqual(
            debt_metrics.monthly_credit_card_payments,
            expected_credit_card,
            places=0,
            msg=f"Credit card should be £{expected_credit_card}/month from last 3 months"
        )
        
        self.assertAlmostEqual(
            debt_metrics.monthly_bnpl_payments,
            expected_bnpl,
            places=0,
            msg=f"BNPL should be £{expected_bnpl}/month from last 3 months"
        )
        
        self.assertAlmostEqual(
            debt_metrics.total_debt_commitments,
            expected_total,
            places=0,
            msg=f"Total debt should be £{expected_total}/month from last 3 months"
        )
        
        print(f"\n✓ Multiple debt types test passed:")
        print(f"  Monthly HCSTC: £{debt_metrics.monthly_hcstc_payments:.2f}")
        print(f"  Monthly credit card: £{debt_metrics.monthly_credit_card_payments:.2f}")
        print(f"  Monthly BNPL: £{debt_metrics.monthly_bnpl_payments:.2f}")
        print(f"  Total monthly debt: £{debt_metrics.total_debt_commitments:.2f}")
    
    def test_affordability_calculation_consistency(self):
        """
        Test that affordability calculations are consistent when using same time basis.
        
        Monthly disposable = Monthly income - Monthly expenses - Monthly debt
        All components must use the same lookback period.
        """
        transactions = [
            # Recent 3 months only for simplicity
            {"date": "2025-03-01", "amount": -3000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-03-10", "amount": 800, "name": "LANDLORD PAYMENT", "description": "RENT PAYMENT"},
            {"date": "2025-03-15", "amount": 300, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-03-20", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            {"date": "2025-04-01", "amount": -3000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-04-10", "amount": 800, "name": "LANDLORD PAYMENT", "description": "RENT PAYMENT"},
            {"date": "2025-04-15", "amount": 300, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-04-20", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            {"date": "2025-05-01", "amount": -3000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-05-10", "amount": 800, "name": "LANDLORD PAYMENT", "description": "RENT PAYMENT"},
            {"date": "2025-05-15", "amount": 300, "name": "TESCO", "description": "GROCERIES"},
            {"date": "2025-05-20", "amount": 200, "name": "BARCLAYCARD", "description": "CREDIT CARD"},
            
            # Current partial month (June - will be excluded)
            {"date": "2025-06-01", "amount": -3000, "name": "SALARY", "description": "SALARY"},
            {"date": "2025-06-05", "amount": 50, "name": "UTILITIES", "description": "UTILITIES"},
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
        
        income_metrics = metrics["income"]
        expense_metrics = metrics["expenses"]
        debt_metrics = metrics["debt"]
        affordability_metrics = metrics["affordability"]
        
        # Verify all monthly figures are based on same 3-month period
        # Monthly income: £9,000 / 3 = £3,000
        self.assertAlmostEqual(income_metrics.monthly_income, 3000, places=0)
        
        # Monthly rent: £2,400 / 3 = £800
        self.assertAlmostEqual(expense_metrics.monthly_housing, 800, places=0)
        
        # Monthly groceries: £900 / 3 = £300
        self.assertAlmostEqual(expense_metrics.monthly_groceries, 300, places=0)
        
        # Monthly credit card: £600 / 3 = £200
        self.assertAlmostEqual(debt_metrics.monthly_credit_card_payments, 200, places=0)
        
        # Total monthly spend (rent + groceries) = £1,100
        expected_total_spend = 1100
        self.assertAlmostEqual(expense_metrics.monthly_total_spend, expected_total_spend, places=0)
        
        # Monthly disposable calculation includes expense buffer (10% shock)
        # Buffered expenses = 1100 * 1.1 = 1210
        # Monthly disposable = £3,000 - £1,210 - £200 = £1,590
        expected_disposable = 1590
        self.assertAlmostEqual(
            affordability_metrics.monthly_disposable,
            expected_disposable,
            places=0,
            msg="Monthly disposable should be income - buffered_expenses - debt"
        )
        
        print(f"\n✓ Affordability consistency test passed:")
        print(f"  Monthly income: £{income_metrics.monthly_income:.2f}")
        print(f"  Monthly expenses: £{expense_metrics.monthly_total_spend:.2f}")
        print(f"  Monthly debt: £{debt_metrics.total_debt_commitments:.2f}")
        print(f"  Monthly disposable: £{affordability_metrics.monthly_disposable:.2f}")
        print(f"  Expected disposable: £{expected_disposable:.2f}")


if __name__ == "__main__":
    unittest.main()
