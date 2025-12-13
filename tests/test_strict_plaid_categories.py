"""
Test suite for strict PLAID detailed categories that must ALWAYS be respected.

Tests that specific PLAID detailed categories (TRANSFER_IN_ACCOUNT_TRANSFER,
TRANSFER_OUT_ACCOUNT_TRANSFER, TRANSFER_IN_CASH_ADVANCES_AND_LOANS) are 
NEVER overridden by keyword matching or behavioral detection.

Addresses the issue where:
1. TRANSFER_IN_ACCOUNT_TRANSFER was being miscategorized as income/salary or income/other
2. TRANSFER_OUT_ACCOUNT_TRANSFER was being miscategorized as expense/other
3. TRANSFER_IN_CASH_ADVANCES_AND_LOANS needs to be categorized as income/loans with weight=0.0
"""

import unittest
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestStrictPlaidCategories(unittest.TestCase):
    """Test cases for strict PLAID detailed categories."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    # ====================================================================
    # TRANSFER_IN_ACCOUNT_TRANSFER Tests
    # ====================================================================
    
    def test_transfer_in_account_transfer_with_payment_from_keyword(self):
        """
        TRANSFER_IN_ACCOUNT_TRANSFER should be transfer > internal,
        even with "Payment from" keyword that would normally match salary.
        
        Real example:
        "Payment from Vishant Khanna - vgghhg" with TRANSFER_IN_ACCOUNT_TRANSFER
        was being categorized as income/salary due to keyword matching.
        """
        result = self.categorizer.categorize_transaction(
            description="Payment from Vishant Khanna - vgghhg",
            amount=-20,  # Negative = credit (money in)
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "plaid_strict")
        self.assertGreaterEqual(result.confidence, 0.98)
        self.assertFalse(result.is_stable)
    
    def test_transfer_in_account_transfer_with_mr_prefix(self):
        """
        TRANSFER_IN_ACCOUNT_TRANSFER should be transfer > internal,
        even with complex description.
        
        Real example:
        "MR VISHANT KHANNA - From POCKET CHANGE PIONEERS LTD - TiPJAR tipjar.tips/4YHJST"
        with TRANSFER_IN_ACCOUNT_TRANSFER was being categorized as income/other.
        """
        result = self.categorizer.categorize_transaction(
            description="MR VISHANT KHANNA - From POCKET CHANGE PIONEERS LTD - TiPJAR tipjar.tips/4YHJST - IBAN: GB29REVO00997044058991",
            amount=-73.56,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "plaid_strict")
    
    def test_transfer_in_account_transfer_simple(self):
        """
        TRANSFER_IN_ACCOUNT_TRANSFER with simple description.
        """
        result = self.categorizer.categorize_transaction(
            description="209074 40964700 MOBILE-CHANNEL FT",
            amount=-2000,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    # ====================================================================
    # TRANSFER_OUT_ACCOUNT_TRANSFER Tests
    # ====================================================================
    
    def test_transfer_out_account_transfer_to_person(self):
        """
        TRANSFER_OUT_ACCOUNT_TRANSFER should be transfer > external,
        not expense/other.
        
        Real example:
        "To Mr Vishant Khanna - Sent from Revolut" with TRANSFER_OUT_ACCOUNT_TRANSFER
        was being categorized as expense/other.
        """
        result = self.categorizer.categorize_transaction(
            description="To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331",
            amount=7.16,  # Positive = debit (money out)
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "external")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "plaid_strict")
        self.assertGreaterEqual(result.confidence, 0.98)
    
    def test_transfer_out_account_transfer_larger_amount(self):
        """
        TRANSFER_OUT_ACCOUNT_TRANSFER with larger amount.
        """
        result = self.categorizer.categorize_transaction(
            description="To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331",
            amount=150,
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "external")
        self.assertEqual(result.weight, 0.0)
    
    # ====================================================================
    # TRANSFER_IN_CASH_ADVANCES_AND_LOANS Tests
    # ====================================================================
    
    def test_transfer_in_cash_advances_and_loans(self):
        """
        TRANSFER_IN_CASH_ADVANCES_AND_LOANS should be income > loans
        with weight=0.0 (not counted as real income).
        """
        result = self.categorizer.categorize_transaction(
            description="LOAN DISBURSEMENT",
            amount=-500.0,
            plaid_category="TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "plaid_strict")
        self.assertGreaterEqual(result.confidence, 0.98)
        self.assertFalse(result.is_stable)
    
    def test_cash_advance_from_credit_card(self):
        """
        Cash advance should be categorized as income > loans with weight=0.0.
        """
        result = self.categorizer.categorize_transaction(
            description="CASH ADVANCE - CREDIT CARD",
            amount=-200.0,
            plaid_category="TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    # ====================================================================
    # Test that keywords do NOT override strict categories
    # ====================================================================
    
    def test_keyword_does_not_override_transfer_in_account_transfer(self):
        """
        Even with strong salary keywords, TRANSFER_IN_ACCOUNT_TRANSFER
        must remain transfer > internal.
        """
        result = self.categorizer.categorize_transaction(
            description="SALARY PAYMENT FROM EMPLOYER LIMITED",
            amount=-3000,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertNotEqual(result.category, "income")
        self.assertEqual(result.weight, 0.0)
    
    def test_keyword_does_not_override_transfer_out_account_transfer(self):
        """
        Even with grocery/shopping keywords, TRANSFER_OUT_ACCOUNT_TRANSFER
        must remain transfer > external.
        """
        result = self.categorizer.categorize_transaction(
            description="TESCO GROCERIES",
            amount=50,
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "external")
        self.assertNotEqual(result.category, "essential")
        self.assertEqual(result.weight, 0.0)
    
    # ====================================================================
    # Test batch processing with strict categories
    # ====================================================================
    
    def test_batch_processing_transfer_in_account_transfer(self):
        """
        Batch processing should respect TRANSFER_IN_ACCOUNT_TRANSFER.
        """
        transactions = [
            {
                "name": "Payment from Vishant Khanna - vgghhg",
                "amount": -20,
                "date": "2025-05-01",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
            {
                "name": "Payment from Vishant Khanna - vgghhg",
                "amount": -40,
                "date": "2025-04-27",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions(transactions)
        
        self.assertEqual(len(results), 2)
        for txn, match in results:
            self.assertEqual(match.category, "transfer")
            self.assertEqual(match.subcategory, "internal")
            self.assertEqual(match.weight, 0.0)
    
    def test_batch_processing_transfer_out_account_transfer(self):
        """
        Batch processing should respect TRANSFER_OUT_ACCOUNT_TRANSFER.
        """
        transactions = [
            {
                "name": "To Mr Vishant Khanna - Sent from Revolut",
                "amount": 7.16,
                "date": "2025-05-18",
                "merchant_name": "Revolut",
                "personal_finance_category": {
                    "primary": "TRANSFER_OUT",
                    "detailed": "TRANSFER_OUT_ACCOUNT_TRANSFER"
                }
            },
            {
                "name": "To Mr Vishant Khanna - Sent from Revolut",
                "amount": 150,
                "date": "2025-05-18",
                "merchant_name": "Revolut",
                "personal_finance_category": {
                    "primary": "TRANSFER_OUT",
                    "detailed": "TRANSFER_OUT_ACCOUNT_TRANSFER"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions(transactions)
        
        self.assertEqual(len(results), 2)
        for txn, match in results:
            self.assertEqual(match.category, "transfer")
            self.assertEqual(match.subcategory, "external")
            self.assertEqual(match.weight, 0.0)
    
    # ====================================================================
    # Test category summary with transfer subcategories
    # ====================================================================
    
    def test_category_summary_tracks_transfer_subcategories(self):
        """
        get_category_summary should track internal vs external transfers separately.
        """
        transactions = [
            {
                "name": "Payment from John",
                "amount": -100,
                "date": "2025-05-01",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
            {
                "name": "To Jane",
                "amount": 50,
                "date": "2025-05-02",
                "personal_finance_category": {
                    "primary": "TRANSFER_OUT",
                    "detailed": "TRANSFER_OUT_ACCOUNT_TRANSFER"
                }
            },
            {
                "name": "Another Payment from John",
                "amount": -75,
                "date": "2025-05-03",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            }
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        summary = self.categorizer.get_category_summary(categorized)
        
        # Check that transfer has subcategories
        self.assertIn("transfer", summary)
        self.assertIn("internal", summary["transfer"])
        self.assertIn("external", summary["transfer"])
        
        # Check internal transfers (2 transactions, total 175)
        self.assertEqual(summary["transfer"]["internal"]["count"], 2)
        self.assertEqual(summary["transfer"]["internal"]["total"], 175.0)
        
        # Check external transfers (1 transaction, total 50)
        self.assertEqual(summary["transfer"]["external"]["count"], 1)
        self.assertEqual(summary["transfer"]["external"]["total"], 50.0)
    
    def test_category_summary_mixed_categories(self):
        """
        Test that summary correctly handles mixed categories including strict PLAID categories.
        """
        transactions = [
            {
                "name": "Payment from Vishant Khanna",
                "amount": -20,
                "date": "2025-05-01",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_ACCOUNT_TRANSFER"
                }
            },
            {
                "name": "TESCO",
                "amount": 45.50,
                "date": "2025-05-02",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            },
            {
                "name": "LOAN DISBURSEMENT",
                "amount": -500,
                "date": "2025-05-03",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_CASH_ADVANCES_AND_LOANS"
                }
            }
        ]
        
        categorized = self.categorizer.categorize_transactions(transactions)
        summary = self.categorizer.get_category_summary(categorized)
        
        # Check transfer > internal
        self.assertEqual(summary["transfer"]["internal"]["count"], 1)
        self.assertEqual(summary["transfer"]["internal"]["total"], 20.0)
        
        # Check income > loans (weight=0.0, so total should be 0)
        self.assertEqual(summary["income"]["loans"]["count"], 1)
        self.assertEqual(summary["income"]["loans"]["total"], 0.0)  # weight=0.0
        
        # Check essential > groceries
        self.assertEqual(summary["essential"]["groceries"]["count"], 1)
        self.assertEqual(summary["essential"]["groceries"]["total"], 45.50)


class TestStrictPlaidCategoriesPrecedence(unittest.TestCase):
    """Test that strict PLAID categories take precedence over all other logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_strict_category_overrides_plaid_primary(self):
        """
        Detailed category TRANSFER_IN_ACCOUNT_TRANSFER should override
        primary category INCOME_WAGES.
        """
        result = self.categorizer.categorize_transaction(
            description="MONTHLY SALARY",
            amount=-3000,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="INCOME_WAGES"  # Should be ignored
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
    
    def test_strict_category_checked_before_known_expense_services(self):
        """
        Strict categories should be checked even before known expense service checks.
        """
        result = self.categorizer.categorize_transaction(
            description="PAYPAL PAYMENT",  # Would normally trigger expense service check
            amount=-100,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
    
    def test_case_insensitive_matching(self):
        """
        Test that detailed category matching is case-insensitive.
        """
        test_cases = [
            "TRANSFER_IN_ACCOUNT_TRANSFER",
            "transfer_in_account_transfer",
            "Transfer_In_Account_Transfer",
        ]
        
        for detailed_cat in test_cases:
            with self.subTest(detailed_category=detailed_cat):
                result = self.categorizer.categorize_transaction(
                    description="Test transaction",
                    amount=-100,
                    plaid_category=detailed_cat
                )
                
                self.assertEqual(result.category, "transfer")
                self.assertEqual(result.subcategory, "internal")


if __name__ == "__main__":
    unittest.main()
