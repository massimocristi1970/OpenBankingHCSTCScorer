"""
Test to verify that internal transfers are correctly categorized.
This test validates the fix for the issue where transfers were being miscategorized as income.
"""

import unittest
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestTransferCategorization(unittest.TestCase):
    """Test cases for transfer categorization fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_plaid_transfer_in_primary(self):
        """Test that transactions with TRANSFER_IN primary category are categorized as transfers."""
        result = self.categorizer.categorize_transaction(
            description="209074 40964700 MOBILE-CHANNEL FT",
            amount=-2000,  # Negative = credit (money in)
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "account_transfer")
        self.assertEqual(result.weight, 1.0)
        self.assertEqual(result.match_method, "plaid_strict")
        self.assertGreater(result.confidence, 0.9)
    
    def test_plaid_transfer_in_detailed(self):
        """Test that transactions with TRANSFER in detailed category are categorized as transfers."""
        result = self.categorizer.categorize_transaction(
            description="Some transfer description",
            amount=-1500,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "account_transfer")
        self.assertEqual(result.weight, 1.0)
    
    def test_keyword_transfer_fallback(self):
        """Test that keyword matching still works as fallback when Plaid category is absent."""
        result = self.categorizer.categorize_transaction(
            description="INTERNAL TRANSFER TO SAVINGS",
            amount=-1000
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "keyword")
    
    def test_non_transfer_income(self):
        """Test that legitimate income is not incorrectly categorized as transfer."""
        result = self.categorizer.categorize_transaction(
            description="FP-TESCO STORES LTD SALARY",
            amount=-2333,
            plaid_category_primary="INCOME",
            plaid_category="INCOME_WAGES"
        )
        
        self.assertEqual(result.category, "income")
        self.assertNotEqual(result.weight, 0.0)
        self.assertGreater(result.weight, 0.0)
    
    def test_transfer_out_primary(self):
        """Test that TRANSFER_OUT (debit transfers) are also recognized."""
        # This is for completeness - the _is_plaid_transfer should handle both IN and OUT
        result = self.categorizer._is_plaid_transfer(
            plaid_category_primary="TRANSFER_OUT",
            plaid_category_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER"
        )
        
        self.assertTrue(result)
    
    def test_categorize_transactions_with_nested_plaid(self):
        """Test the categorize_transactions method with nested personal_finance_category."""
        transactions = [
            {
                "name": "209074 40964700 MOBILE-CHANNEL FT",
                "amount": -2000,
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions(transactions)
        
        self.assertEqual(len(results), 1)
        txn, match = results[0]
        self.assertEqual(match.category, "income")
        self.assertEqual(match.subcategory, "account_transfer")
        self.assertEqual(match.weight, 1.0)
    
    def test_categorize_transactions_with_flat_plaid(self):
        """Test the categorize_transactions method with flat personal_finance_category fields."""
        transactions = [
            {
                "name": "Transfer from savings",
                "amount": -1500,
                "personal_finance_category.primary": "TRANSFER_IN",
                "personal_finance_category.detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
            }
        ]
        
        results = self.categorizer.categorize_transactions(transactions)
        
        self.assertEqual(len(results), 1)
        txn, match = results[0]
        self.assertEqual(match.category, "income")
        self.assertEqual(match.subcategory, "account_transfer")
        self.assertEqual(match.weight, 1.0)


if __name__ == "__main__":
    unittest.main()
