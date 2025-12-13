"""
Test to validate that expense weighting is correctly handled in category summary.

This test demonstrates the bug fix for underreported expenses due to incorrect
application of income weighting to expense transactions.
"""

import unittest
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestExpenseWeightingFix(unittest.TestCase):
    """Test that expense totals are calculated without applying income weights."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_expenses_use_full_amount_not_weighted(self):
        """
        Test that expenses are counted at full value, not weighted like income.
        
        This validates the fix for the critical bug where expenses were being
        incorrectly weighted, causing massive underreporting (£91.70 vs £1971.70).
        """
        transactions = [
            # Groceries expense - should count full £50
            {
                "name": "TESCO STORES 5321",
                "amount": 50.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            },
            # Utilities expense - should count full £120
            {
                "name": "BRITISH GAS",
                "amount": 120.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "GENERAL_SERVICES",
                    "detailed": "GENERAL_SERVICES_OTHER_GENERAL_SERVICES"
                }
            },
            # Transport expense - should count full £80
            {
                "name": "SHELL FUEL",
                "amount": 80.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "TRANSPORTATION",
                    "detailed": "TRANSPORTATION_GAS"
                }
            },
            # Uncertain income - should be weighted at 0.5
            {
                "name": "FREELANCE PAYMENT",
                "amount": -200.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_OTHER_INCOME"
                }
            },
            # Salary income - should be weighted at 1.0
            {
                "name": "EMPLOYER LTD SALARY",
                "amount": -2000.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
        ]
        
        # Categorize transactions
        categorized = self.categorizer.categorize_transactions(transactions)
        
        # Get category summary
        summary = self.categorizer.get_category_summary(categorized)
        
        # Validate expenses are counted at full value
        groceries_total = summary["essential"]["groceries"]["total"]
        utilities_total = summary["essential"]["utilities"]["total"]
        transport_total = summary["essential"]["transport"]["total"]
        
        # These should be EXACTLY the transaction amounts (no weighting)
        self.assertEqual(groceries_total, 50.00, 
                        "Groceries should be counted at full £50, not weighted")
        self.assertEqual(utilities_total, 120.00,
                        "Utilities should be counted at full £120, not weighted")
        self.assertEqual(transport_total, 80.00,
                        "Transport should be counted at full £80, not weighted")
        
        # Total expenses should be full amounts
        total_expenses = groceries_total + utilities_total + transport_total
        self.assertEqual(total_expenses, 250.00,
                        "Total expenses should be £250 without any weighting")
        
        # Validate income IS weighted correctly
        # Uncertain income: £200 * 0.5 = £100
        # Salary: £2000 * 1.0 = £2000
        # Total weighted income should be £2100
        total_income = (summary["income"]["other"]["total"] + 
                       summary["income"]["salary"]["total"])
        
        # Uncertain income should be weighted
        other_income = summary["income"]["other"]["total"]
        self.assertAlmostEqual(other_income, 100.00, places=2,
                              msg="Uncertain income should be weighted at 0.5: £200 * 0.5 = £100")
        
        # Salary should be full weight
        salary_income = summary["income"]["salary"]["total"]
        self.assertEqual(salary_income, 2000.00,
                        "Salary should be at full weight: £2000 * 1.0 = £2000")
        
        print(f"\n✓ Expenses correctly counted at full value: £{total_expenses:.2f}")
        print(f"  - Groceries: £{groceries_total:.2f} (not weighted)")
        print(f"  - Utilities: £{utilities_total:.2f} (not weighted)")
        print(f"  - Transport: £{transport_total:.2f} (not weighted)")
        print(f"✓ Income correctly weighted: £{total_income:.2f}")
        print(f"  - Uncertain income: £{other_income:.2f} (£200 * 0.5)")
        print(f"  - Salary: £{salary_income:.2f} (£2000 * 1.0)")
    
    def test_debt_payments_use_full_amount(self):
        """Test that debt payments are counted at full value."""
        transactions = [
            # Other loan payment - should count full £150
            {
                "name": "WONGA PAYMENT",
                "amount": 150.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "LOAN_PAYMENTS",
                    "detailed": "LOAN_PAYMENTS_OTHER_PAYMENT"
                }
            },
            # Credit card payment - should count full £300
            {
                "name": "BARCLAYCARD PAYMENT",
                "amount": 300.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "LOAN_PAYMENTS",
                    "detailed": "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT"
                }
            },
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        summary = self.categorizer.get_category_summary(categorized)
        
        # Debt payments should be at full value
        loan_total = summary["debt"]["other_loans"]["total"]
        cc_total = summary["debt"]["credit_cards"]["total"]
        
        self.assertEqual(loan_total, 150.00,
                        "Loan payment should be counted at full £150")
        self.assertEqual(cc_total, 300.00,
                        "Credit card payment should be counted at full £300")
        
        print(f"\n✓ Debt payments correctly counted at full value:")
        print(f"  - Other Loans: £{loan_total:.2f} (not weighted)")
        print(f"  - Credit Card: £{cc_total:.2f} (not weighted)")
    
    def test_risk_indicators_use_full_amount(self):
        """Test that risk indicators (gambling, bank charges) are counted at full value."""
        transactions = [
            # Gambling - should count full £50
            {
                "name": "BETFAIR SPORTS",
                "amount": 50.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "ENTERTAINMENT",
                    "detailed": "ENTERTAINMENT_CASINOS_AND_GAMBLING"
                }
            },
            # Bank charge - should count full £25
            {
                "name": "UNPAID DIRECT DEBIT FEE",
                "amount": 25.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "BANK_FEES",
                    "detailed": "BANK_FEES_OVERDRAFT_FEES"
                }
            },
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        summary = self.categorizer.get_category_summary(categorized)
        
        # Risk indicators should be at full value
        gambling_total = summary["risk"]["gambling"]["total"]
        bank_charges_total = summary["risk"]["bank_charges"]["total"]
        
        self.assertEqual(gambling_total, 50.00,
                        "Gambling should be counted at full £50")
        self.assertEqual(bank_charges_total, 25.00,
                        "Bank charge should be counted at full £25")
        
        print(f"\n✓ Risk indicators correctly counted at full value:")
        print(f"  - Gambling: £{gambling_total:.2f} (not weighted)")
        print(f"  - Bank Charges: £{bank_charges_total:.2f} (not weighted)")
    
    def test_scenario_from_problem_statement(self):
        """
        Test the scenario from the problem statement:
        Monthly expenses should be £1971.70, not £91.70.
        
        This simulates the underreporting bug where expenses were incorrectly
        weighted at 30% of their actual value (default weight for unknown expenses).
        """
        # Create a representative set of monthly expenses
        transactions = [
            {"name": "TESCO", "amount": 200.00, "date": "2024-01-15",
             "personal_finance_category": {"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_GROCERIES"}},
            {"name": "SAINSBURYS", "amount": 150.00, "date": "2024-01-18",
             "personal_finance_category": {"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_GROCERIES"}},
            {"name": "ASDA", "amount": 180.00, "date": "2024-01-22",
             "personal_finance_category": {"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_GROCERIES"}},
            {"name": "BRITISH GAS", "amount": 120.00, "date": "2024-01-10",
             "personal_finance_category": {"primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_UTILITIES"}},
            {"name": "THAMES WATER", "amount": 45.00, "date": "2024-01-12",
             "personal_finance_category": {"primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_UTILITIES"}},
            {"name": "EE MOBILE", "amount": 35.00, "date": "2024-01-05",
             "personal_finance_category": {"primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_PHONE"}},
            {"name": "SKY BROADBAND", "amount": 45.00, "date": "2024-01-05",
             "personal_finance_category": {"primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_INTERNET"}},
            {"name": "LANDLORD RENT", "amount": 850.00, "date": "2024-01-01",
             "personal_finance_category": {"primary": "RENT_AND_UTILITIES", "detailed": "RENT_AND_UTILITIES_RENT"}},
            {"name": "COUNCIL TAX", "amount": 110.00, "date": "2024-01-01",
             "personal_finance_category": {"primary": "GENERAL_SERVICES", "detailed": "GENERAL_SERVICES_GOVERNMENT_SERVICES"}},
            {"name": "SHELL FUEL", "amount": 80.00, "date": "2024-01-14",
             "personal_finance_category": {"primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_GAS"}},
            {"name": "TFL TRAVEL", "amount": 156.70, "date": "2024-01-28",
             "personal_finance_category": {"primary": "TRANSPORTATION", "detailed": "TRANSPORTATION_PUBLIC"}},
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        summary = self.categorizer.get_category_summary(categorized)
        
        # Calculate total expenses
        total_expenses = 0.0
        total_expenses += summary["essential"]["groceries"]["total"]
        total_expenses += summary["essential"]["utilities"]["total"]
        total_expenses += summary["essential"]["communications"]["total"]
        total_expenses += summary["essential"]["rent"]["total"]
        total_expenses += summary["essential"]["council_tax"]["total"]
        total_expenses += summary["essential"]["transport"]["total"]
        
        # Expected total from transactions
        expected_total = sum(txn["amount"] for txn in transactions)
        
        # Should be close to expected (allowing for rounding)
        self.assertAlmostEqual(total_expenses, expected_total, places=2,
                              msg=f"Total expenses should be £{expected_total:.2f}, not underreported")
        
        # The bug would have caused expenses to be ~30% of actual
        # (if default weight was 0.3 for unknown transactions)
        incorrect_total = expected_total * 0.3
        
        print(f"\n✓ Monthly expenses correctly calculated: £{total_expenses:.2f}")
        print(f"  (vs. £{incorrect_total:.2f} with the bug - {((expected_total/incorrect_total - 1) * 100):.0f}% underreporting)")
        print(f"✓ Fix prevents underreporting of expenses for affordability assessment")


if __name__ == '__main__':
    unittest.main()
