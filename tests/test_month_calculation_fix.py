"""
Test for automatic month calculation from transaction dates.
Validates the fix for issue: Monthly Income and Expense Calculation Based on Actual Data Period.
"""

import unittest
from datetime import datetime
from openbanking_engine.scoring.feature_builder import MetricsCalculator
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestMonthCalculationFix(unittest.TestCase):
    """Test automatic month calculation from transaction data."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_calculate_months_from_3_month_data(self):
        """Test calculation with 3 months of data (March-May 2025)."""
        transactions = [
            {"date": "2025-03-01", "amount": -1000, "description": "Salary"},
            {"date": "2025-03-15", "amount": 100, "description": "Expense"},
            {"date": "2025-04-01", "amount": -1000, "description": "Salary"},
            {"date": "2025-04-20", "amount": 50, "description": "Expense"},
            {"date": "2025-05-01", "amount": -1000, "description": "Salary"},
            {"date": "2025-05-25", "amount": 75, "description": "Expense"},
        ]
        
        calculator = MetricsCalculator(transactions=transactions)
        
        self.assertEqual(calculator.months_of_data, 3, 
                        "Should detect 3 months (March, April, May)")
    
    def test_calculate_months_from_6_month_data(self):
        """Test calculation with 6 months of data."""
        transactions = [
            {"date": "2025-01-15", "amount": -1000, "description": "Salary"},
            {"date": "2025-02-15", "amount": -1000, "description": "Salary"},
            {"date": "2025-03-15", "amount": -1000, "description": "Salary"},
            {"date": "2025-04-15", "amount": -1000, "description": "Salary"},
            {"date": "2025-05-15", "amount": -1000, "description": "Salary"},
            {"date": "2025-06-15", "amount": -1000, "description": "Salary"},
        ]
        
        calculator = MetricsCalculator(transactions=transactions)
        
        self.assertEqual(calculator.months_of_data, 6, 
                        "Should detect 6 months (Jan-Jun)")
    
    def test_calculate_months_from_12_month_data(self):
        """Test calculation with 12 months of data."""
        transactions = []
        for month in range(1, 13):
            transactions.append({
                "date": f"2024-{month:02d}-15",
                "amount": -2000,
                "description": "Salary"
            })
        
        calculator = MetricsCalculator(transactions=transactions)
        
        self.assertEqual(calculator.months_of_data, 12, 
                        "Should detect 12 months (full year)")
    
    def test_calculate_months_partial_months(self):
        """Test that partial months are counted correctly."""
        # From Jan 25 to Feb 5 should be 2 months (Jan and Feb)
        # Note: Both transactions must be income (negative amounts) since month
        # calculation now only considers income transaction dates, not expense dates
        transactions = [
            {"date": "2025-01-25", "amount": -1000, "description": "Salary"},
            {"date": "2025-02-05", "amount": -1000, "description": "Salary"},
        ]
        
        calculator = MetricsCalculator(transactions=transactions)
        
        self.assertEqual(calculator.months_of_data, 2, 
                        "Should count partial months as full months (Jan, Feb)")
    
    def test_manual_override_takes_precedence(self):
        """Test that manual months_of_data override works."""
        transactions = [
            {"date": "2025-03-01", "amount": -1000, "description": "Salary"},
            {"date": "2025-05-31", "amount": 100, "description": "Expense"},
        ]
        
        # Should be 3 months auto-calculated, but we override to 6
        calculator = MetricsCalculator(months_of_data=6, transactions=transactions)
        
        self.assertEqual(calculator.months_of_data, 6, 
                        "Manual override should take precedence")
    
    def test_empty_transactions_defaults_to_3(self):
        """Test that empty transactions default to 3 months."""
        calculator = MetricsCalculator(transactions=[])
        
        self.assertEqual(calculator.months_of_data, 3, 
                        "Empty transactions should default to 3 months")
    
    def test_no_parameters_defaults_to_3(self):
        """Test that no parameters defaults to 3 months (backward compatibility)."""
        calculator = MetricsCalculator()
        
        self.assertEqual(calculator.months_of_data, 3, 
                        "No parameters should default to 3 months")
    
    def test_invalid_dates_skipped(self):
        """Test that invalid dates are skipped gracefully."""
        transactions = [
            {"date": "2025-03-01", "amount": -1000, "description": "Salary"},
            {"date": "invalid", "amount": 100, "description": "Expense"},
            {"date": "", "amount": 50, "description": "Expense"},
            {"date": "2025-05-31", "amount": -1000, "description": "Salary"},
        ]
        
        calculator = MetricsCalculator(transactions=transactions)
        
        # Should still calculate correctly from valid dates (March to May = 3)
        self.assertEqual(calculator.months_of_data, 3, 
                        "Invalid dates should be skipped, valid dates used")
    
    def test_real_world_scenario_fuller_smith_turner(self):
        """
        Test the real-world scenario from the problem statement:
        Fuller Smith & Turner salary: £4,599.73 over 3 months (March-May 2025)
        Expected monthly: £4,599.73 / 3 = £1,533.24
        """
        transactions = [
            # Fuller Smith & Turner salary payments over 3 months
            {
                "date": "2025-03-15",
                "amount": -1533.24,
                "name": "FULLER SMITH & TURNER SALARY",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            {
                "date": "2025-04-15",
                "amount": -1533.24,
                "name": "FULLER SMITH & TURNER SALARY",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            {
                "date": "2025-05-15",
                "amount": -1533.25,
                "name": "FULLER SMITH & TURNER SALARY",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            # Some expenses
            {
                "date": "2025-03-20",
                "amount": 210.0,
                "name": "TESCO",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            },
            {
                "date": "2025-04-20",
                "amount": 220.0,
                "name": "TESCO",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            },
            {
                "date": "2025-05-20",
                "amount": 230.0,
                "name": "TESCO",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            },
        ]
        
        # Categorize transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with automatic month calculation
        calculator = MetricsCalculator(transactions=transactions)
        
        # Verify months calculated correctly
        self.assertEqual(calculator.months_of_data, 3,
                        "Should detect 3 months from March-May data")
        
        # Calculate metrics
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            loan_amount=500,
            loan_term=4
        )
        
        # Verify income calculation
        total_salary = 1533.24 + 1533.24 + 1533.25  # £4,599.73
        expected_monthly = total_salary / 3  # £1,533.24
        
        self.assertAlmostEqual(
            metrics["income"].monthly_stable_income,
            expected_monthly,
            places=2,
            msg=f"Monthly income should be £{expected_monthly:.2f}, not inflated"
        )
        
        # Verify expense calculation
        total_expenses = 210.0 + 220.0 + 230.0  # £660
        expected_monthly_expenses = total_expenses / 3  # £220
        
        self.assertAlmostEqual(
            metrics["expenses"].monthly_groceries,
            expected_monthly_expenses,
            places=2,
            msg=f"Monthly expenses should be £{expected_monthly_expenses:.2f}"
        )
        
        print(f"\n✓ Real-world scenario validated:")
        print(f"  Total salary: £{total_salary:.2f}")
        print(f"  Monthly salary: £{metrics['income'].monthly_stable_income:.2f}")
        print(f"  Expected: £{expected_monthly:.2f}")
        print(f"  Total expenses: £{total_expenses:.2f}")
        print(f"  Monthly expenses: £{metrics['expenses'].monthly_groceries:.2f}")
        print(f"  Expected: £{expected_monthly_expenses:.2f}")
    
    def test_integration_with_metrics_calculator(self):
        """Test that the fix works with MetricsCalculator directly."""
        transactions = [
            {
                "date": "2025-03-15",
                "amount": -2500.0,
                "name": "SALARY FROM ACME LTD",
                "merchant_name": "ACME Ltd",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            {
                "date": "2025-04-15",
                "amount": -2500.0,
                "name": "SALARY FROM ACME LTD",
                "merchant_name": "ACME Ltd",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            {
                "date": "2025-05-15",
                "amount": -2500.0,
                "name": "SALARY FROM ACME LTD",
                "merchant_name": "ACME Ltd",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            {
                "date": "2025-03-20",
                "amount": 850.0,
                "name": "RENT TO LANDLORD",
                "personal_finance_category": {
                    "primary": "RENT_AND_UTILITIES",
                    "detailed": "RENT_AND_UTILITIES_RENT"
                }
            },
            {
                "date": "2025-04-20",
                "amount": 850.0,
                "name": "RENT TO LANDLORD",
                "personal_finance_category": {
                    "primary": "RENT_AND_UTILITIES",
                    "detailed": "RENT_AND_UTILITIES_RENT"
                }
            },
            {
                "date": "2025-05-20",
                "amount": 850.0,
                "name": "RENT TO LANDLORD",
                "personal_finance_category": {
                    "primary": "RENT_AND_UTILITIES",
                    "detailed": "RENT_AND_UTILITIES_RENT"
                }
            },
        ]
        
        # Categorize transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        category_summary = self.categorizer.get_category_summary(categorized)
        
        # Create calculator with automatic month calculation
        calculator = MetricsCalculator(transactions=transactions)
        
        # Calculate metrics
        metrics = calculator.calculate_all_metrics(
            category_summary=category_summary,
            transactions=transactions,
            accounts=[],
            loan_amount=500,
            loan_term=3
        )
        
        # Monthly income should be £2,500 (not inflated)
        self.assertAlmostEqual(
            metrics["income"].monthly_income,
            2500.0,
            places=2,
            msg="Integration test: Monthly income should be £2,500"
        )
        
        # Monthly housing should be £850 (not inflated)
        self.assertAlmostEqual(
            metrics["expenses"].monthly_housing,
            850.0,
            places=2,
            msg="Integration test: Monthly housing should be £850"
        )
        
        print(f"\n✓ Integration test passed:")
        print(f"  Monthly income: £{metrics['income'].monthly_income:.2f}")
        print(f"  Monthly housing: £{metrics['expenses'].monthly_housing:.2f}")
    
    def test_calculate_months_from_income_dates_only(self):
        """Test that month calculation uses income dates, not all transaction dates."""
        transactions = [
            # Old expenses from August 2024
            {"date": "2024-08-01", "amount": 50.0, "description": "Expense"},
            {"date": "2024-11-15", "amount": 100.0, "description": "Expense"},
            
            # Income from March-May 2025 only
            {"date": "2025-03-15", "amount": -1533.24, "description": "Salary"},
            {"date": "2025-04-15", "amount": -1533.24, "description": "Salary"},
            {"date": "2025-05-15", "amount": -1533.25, "description": "Salary"},
            
            # Recent expenses
            {"date": "2025-05-18", "amount": 75.0, "description": "Expense"},
        ]
        
        calculator = MetricsCalculator(transactions=transactions)
        
        # Should calculate 3 months from income dates (March-May)
        # NOT 10 months from all transaction dates (August-May)
        self.assertEqual(calculator.months_of_data, 3,
                        "Should use income dates only, ignoring expense dates")
        
        print(f"\n✓ Income-only month calculation test passed:")
        print(f"  Transaction period: August 2024 - May 2025 (10 months)")
        print(f"  Income period: March 2025 - May 2025 (3 months)")
        print(f"  Months used: {calculator.months_of_data} ✓")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
