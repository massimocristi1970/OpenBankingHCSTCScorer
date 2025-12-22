"""
Test suite demonstrating fixes for the specific issues mentioned in the problem statement.

This file tests the exact examples from the problem statement to verify they are now
correctly categorized.
"""

import unittest
from transaction_categorizer import TransactionCategorizer


class TestIssue1Examples(unittest.TestCase):
    """Test examples from Issue 1: Incorrect Income Detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_lending_stream_payment_not_income(self):
        """
        Example from Issue 1:
        LENDING STREAM PAYMENT2356225 - PLAID: LOAN_PAYMENTS:CREDIT_CARD_PAYMENT
        Should remain as loan payment, NOT be recategorized as salary income.
        """
        result = self.categorizer.categorize_transaction(
            description="LENDING STREAM PAYMENT2356225",
            amount=150.00,  # Positive = debit (expense)
            plaid_category="LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        # Should be debt (HCSTC lender), NOT income
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "hcstc_payday")
        self.assertNotEqual(result.category, "income")
        print(f"✓ LENDING STREAM: {result.category}/{result.subcategory} (confidence: {result.confidence})")
    
    def test_clearpay_not_income(self):
        """
        Example from Issue 1:
        CLEARPAY - PLAID: TRANSFER_IN_CASH_ADVANCES_AND_LOANS
        Should remain as BNPL debt, NOT be recategorized as salary income.
        """
        result = self.categorizer.categorize_transaction(
            description="CLEARPAY",
            amount=50.00,  # Positive = debit (expense)
            plaid_category="TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        # Should be debt (BNPL), NOT income
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "bnpl")
        self.assertNotEqual(result.category, "income")
        print(f"✓ CLEARPAY: {result.category}/{result.subcategory} (confidence: {result.confidence})")
    
    def test_paypal_ppwdl_not_salary(self):
        """
        Example from Issue 1:
        PAYPAL PPWDL - PLAID: TRANSFER_IN_ACCOUNT_TRANSFER
        Should remain as transfer, NOT be recategorized as salary.
        """
        result = self.categorizer.categorize_transaction(
            description="PAYPAL PPWDL",
            amount=-100.00,  # Negative = credit
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        
        # Should be transfer, NOT salary
        self.assertEqual(result.category, "transfer")
        self.assertNotEqual(result.subcategory, "salary")
        print(f"✓ PAYPAL PPWDL: {result.category}/{result.subcategory} (confidence: {result.confidence})")


class TestIssue2Examples(unittest.TestCase):
    """Test examples from Issue 2: Unnecessary Expense Recategorization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_monopoly_casino_preserves_gambling_risk(self):
        """
        Example from Issue 2:
        MONOPOLY CASINO - PLAID: ENTERTAINMENT:CASINOS_AND_GAMBLING (confidence 0.95)
        Should preserve gambling categorization with risk flag, NOT reset to expense/other (0.3).
        """
        result = self.categorizer.categorize_transaction(
            description="MONOPOLY CASINO",
            amount=50.00,  # Positive = debit (expense)
            plaid_category="ENTERTAINMENT_CASINOS_AND_GAMBLING",
            plaid_category_primary="ENTERTAINMENT"
        )
        
        # Should be risk/gambling with high confidence
        self.assertEqual(result.category, "risk")
        self.assertEqual(result.subcategory, "gambling")
        self.assertEqual(result.risk_level, "critical")
        self.assertGreaterEqual(result.confidence, 0.85)
        # Should NOT be expense/other with low confidence
        self.assertNotEqual((result.category, result.subcategory), ("expense", "other"))
        print(f"✓ MONOPOLY CASINO: {result.category}/{result.subcategory} " +
              f"(risk: {result.risk_level}, confidence: {result.confidence})")
    
    def test_lowell_portfolio_preserves_debt_collection(self):
        """
        Example from Issue 2:
        LOWELL PORTFOLIO - PLAID: risk/debt_collection
        Should preserve debt collection risk categorization.
        """
        result = self.categorizer.categorize_transaction(
            description="LOWELL PORTFOLIO",
            amount=75.00,
            plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        # Should be risk/debt_collection with severe risk level
        self.assertEqual(result.category, "risk")
        self.assertEqual(result.subcategory, "debt_collection")
        self.assertEqual(result.risk_level, "severe")
        print(f"✓ LOWELL PORTFOLIO: {result.category}/{result.subcategory} " +
              f"(risk: {result.risk_level}, confidence: {result.confidence})")
    
    def test_restaurant_preserves_plaid_category(self):
        """
        Test that restaurants with PLAID category don't get reset to expense/other.
        """
        result = self.categorizer.categorize_transaction(
            description="THE FANCY RESTAURANT",
            amount=45.00,
            plaid_category="FOOD_AND_DRINK_RESTAURANTS",
            plaid_category_primary="FOOD_AND_DRINK"
        )
        
        # Should use PLAID category, NOT generic expense/other
        self.assertNotEqual((result.category, result.subcategory), ("expense", "other"))
        # Should be food-related
        self.assertIn("food", result.subcategory.lower())
        print(f"✓ RESTAURANT: {result.category}/{result.subcategory} (confidence: {result.confidence})")


class TestProposedSolutionValidation(unittest.TestCase):
    """Test that the proposed solutions from the problem statement are implemented."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_transaction_direction_validation(self):
        """
        Proposed Solution:  Transaction direction validation
        Only consider income if credit amount (negative in PLAID format).
        """
        # Debit (positive) should never be income
        result_debit = self.categorizer.categorize_transaction(
            description="SALARY PAYMENT OUT",
            amount=500.00,  # Positive = debit
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        self.assertEqual(result_debit.category, "expense")  # Now categorized as expense
        self.assertEqual(result_debit. subcategory, "account_transfer")
        
        # Credit (negative) can be income
        result_credit = self.categorizer.categorize_transaction(
            description="SALARY",
            amount=-2500.00,  # Negative = credit
            plaid_category="INCOME_WAGES",
            plaid_category_primary="INCOME"
        )
        self.assertEqual(result_credit.category, "income")
        print("✓ Transaction direction validation works")
    
    def test_known_service_whitelist(self):
        """
        Proposed Solution: Whitelist known expense services
        PayPal, Lending Stream, Clearpay should not trigger income detection.
        """
        services = [
            ("PAYPAL PAYMENT", -50.00, "TRANSFER_IN_ACCOUNT_TRANSFER"),
            ("STRIPE TRANSFER", -100.00, "TRANSFER_IN_ACCOUNT_TRANSFER"),
            ("CLEARPAY REFUND", -25.00, "TRANSFER_IN_OTHER_TRANSFER_IN"),
        ]
        
        for desc, amount, plaid_cat in services:
            result = self.categorizer.categorize_transaction(
                description=desc,
                amount=amount,
                plaid_category=plaid_cat,
                plaid_category_primary="TRANSFER_IN"
            )
            # Should not be salary
            if result.category == "income":
                self.assertNotEqual(result.subcategory, "salary")
            print(f"✓ {desc}: {result.category}/{result.subcategory}")
    
    def test_context_aware_matching(self):
        """
        Proposed Solution: Context-aware matching
        Validate income keywords against PLAID category before overriding.
        """
        # Generic transfer with keyword should stay as transfer
        result1 = self.categorizer.categorize_transaction(
            description="FRIEND PAYMENT",
            amount=-50.00,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        self.assertEqual(result1.category, "transfer")
        
        # Transfer with explicit salary keyword should be income
        result2 = self.categorizer.categorize_transaction(
            description="FP-ACME LTD SALARY",
            amount=-2500.00,
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        self.assertEqual(result2.category, "income")
        self.assertEqual(result2.subcategory, "salary")
        print("✓ Context-aware matching works")
    
    def test_high_confidence_plaid_preservation(self):
        """
        Proposed Solution: Preserve high-confidence PLAID categorizations
        If PLAID confidence >= 0.85, preserve original categorization.
        """
        # Gambling with high PLAID confidence should be preserved
        result = self.categorizer.categorize_transaction(
            description="BET365",
            amount=100.00,
            plaid_category="ENTERTAINMENT_CASINOS_AND_GAMBLING",
            plaid_category_primary="ENTERTAINMENT"
        )
        self.assertEqual(result.category, "risk")
        self.assertEqual(result.subcategory, "gambling")
        self.assertGreaterEqual(result.confidence, 0.85)
        print(f"✓ High confidence PLAID preserved (confidence: {result.confidence})")
    
    def test_risk_category_preservation(self):
        """
        Proposed Solution: Risk category preservation
        Ensure risk flags (critical, severe) are maintained.
        """
        risk_transactions = [
            ("BET365", 50.00, "ENTERTAINMENT_CASINOS_AND_GAMBLING", "gambling", "critical"),
            ("LOWELL", 75.00, "LOAN_PAYMENTS_OTHER_PAYMENT", "debt_collection", "severe"),
        ]
        
        for desc, amount, plaid_cat, expected_sub, expected_risk in risk_transactions:
            result = self.categorizer.categorize_transaction(
                description=desc,
                amount=amount,
                plaid_category=plaid_cat,
                plaid_category_primary="LOAN_PAYMENTS" if "LOAN" in plaid_cat else "ENTERTAINMENT"
            )
            self.assertEqual(result.category, "risk")
            self.assertEqual(result.subcategory, expected_sub)
            self.assertEqual(result.risk_level, expected_risk)
            print(f"✓ {desc}: risk/{expected_sub} (level: {expected_risk})")


if __name__ == "__main__":
    # Run with verbose output to see the results
    unittest.main(verbosity=2)
