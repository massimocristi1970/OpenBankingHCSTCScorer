"""
Demonstration test showing how the fix resolves the inflated income issue.
This test demonstrates the problem described in the issue and validates the fix.
"""

import unittest
from transaction_categorizer import TransactionCategorizer


class TestIncomeCalculationFix(unittest.TestCase):
    """Test demonstrating the income calculation fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_scenario_before_fix_would_inflate_income(self):
        """
        Test scenario from the problem statement:
        Customer with £28,000/year salary (£2,333/month) was showing £17,647/month
        due to internal transfers being counted as income.
        
        This test shows that after the fix, transfers are correctly excluded.
        """
        # Example transactions from a month
        transactions = [
            # Legitimate salary - should count
            {
                "name": "FP-EMPLOYER COMPANY LTD SALARY",
                "amount": -2333,  # £2,333 salary
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            # Internal transfer 1 - should NOT count
            {
                "name": "209074 40964700 MOBILE-CHANNEL FT",
                "amount": -5000,
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
            # Internal transfer 2 - should NOT count
            {
                "name": "FROM SAVINGS ACCOUNT",
                "amount": -10000,
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
            # Internal transfer 3 - should NOT count
            {
                "name": "INTERNAL TRANSFER",
                "amount": -314,
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
        ]
        
        # Categorize all transactions
        results = self.categorizer.categorize_transactions(transactions)
        
        # Calculate weighted income
        total_income = 0.0
        salary_income = 0.0
        transfer_count = 0
        
        for txn, match in results:
            amount = abs(txn.get("amount", 0))
            
            if match.category == "income":
                weighted_amount = amount * match.weight
                total_income += weighted_amount
                if match.subcategory == "salary":
                    salary_income += weighted_amount
            elif match.category == "transfer":
                transfer_count += 1
        
        # Verify that only the salary is counted
        self.assertEqual(salary_income, 2333, "Only salary should be counted as income")
        self.assertEqual(total_income, 2333, "Total income should only be the salary")
        self.assertEqual(transfer_count, 3, "All three transfers should be identified")
        
        # The original issue would have counted all 4 transactions as income:
        # £2,333 + £5,000 + £10,000 + £314 = £17,647
        # But now we correctly only count £2,333
        
        print(f"\n✓ Monthly income correctly calculated as £{total_income:.0f}")
        print(f"  (vs. £17,647 before fix - a {((17647/2333)-1)*100:.0f}% inflation)")
        print(f"✓ {transfer_count} transfers correctly excluded from income")
    
    def test_mixed_income_sources_with_transfers(self):
        """Test that multiple income sources are correctly counted while excluding transfers."""
        transactions = [
            # Salary
            {
                "name": "EMPLOYER PAYMENT",
                "amount": -2333,
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_WAGES"
                }
            },
            # Benefits
            {
                "name": "DWP UNIVERSAL CREDIT",
                "amount": -500,
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_GOVERNMENT_BENEFITS"
                }
            },
            # Transfer (should NOT count)
            {
                "name": "TRANSFER FROM SAVINGS",
                "amount": -3000,
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
            # Gig economy (100% weight)
            {
                "name": "UBER",
                "amount": -200,
                "personal_finance_category": {
                    "primary": "INCOME",
                    "detailed": "INCOME_OTHER"
                }
            },
        ]
        
        results = self.categorizer.categorize_transactions(transactions)
        
        total_weighted_income = 0.0
        for txn, match in results:
            amount = abs(txn.get("amount", 0))
            if match.category == "income":
                total_weighted_income += amount * match.weight
        
        # Expected: £2,333 + £500 + (£200 * 1.0) = £3,033
        expected_income = 2333 + 500 + (200 * 1.0)
        
        self.assertAlmostEqual(total_weighted_income, expected_income, places=2)
        print(f"\n✓ Mixed income sources correctly calculated: £{total_weighted_income:.2f}")
        print(f"  Salary: £2,333 (100%), Benefits: £500 (100%), Gig: £200 (100% of £200)")
        print(f"  Transfer: £3,000 excluded ✓")
    
    def test_transfer_without_plaid_category_uses_keyword_match(self):
        """Test that transfers without Plaid category are still caught by keyword matching."""
        result = self.categorizer.categorize_transaction(
            description="OWN ACCOUNT TRANSFER",
            amount=-1000
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "keyword")
        print("\n✓ Keyword-based transfer detection still works for legacy data")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
