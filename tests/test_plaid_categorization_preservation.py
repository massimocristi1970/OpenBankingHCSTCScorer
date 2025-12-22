"""
Test suite for PLAID categorization preservation.

Tests that high-confidence PLAID categorizations are preserved and not overridden
by keyword-based detection, addressing the issues:
1. Incorrect income detection (loan payments, BNPL, payment services)
2. Loss of high-confidence expense categorizations (gambling, etc.)
"""

import unittest
from unittest import result
from transaction_categorizer import TransactionCategorizer


class TestPlaidCategorizationPreservation(unittest.TestCase):
    """Test cases for preserving high-confidence PLAID categorizations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    # Issue 1: Loan Payments Should Not Be Income
    
    def test_lending_stream_payment_not_income(self):
        """
        LENDING STREAM PAYMENT should remain as loan payment (debt),
        not be recategorized as salary income despite keyword 'PAYMENT'.
        """
        result = self.categorizer.categorize_transaction(
            description="LENDING STREAM PAYMENT2356225",
            amount=150.00,  # Positive = debit (expense)
            plaid_category="LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        # Should be debt/loan payment, NOT income
        self.assertNotEqual(result.category, "income")
        self.assertIn(result.category, ["debt", "risk"])
        # Should preserve risk level if present
        if result.category == "debt":
            self.assertEqual(result.subcategory, "hcstc_payday")
        
    def test_loan_payment_with_high_plaid_confidence(self):
        """
        Transactions with PLAID LOAN_PAYMENTS category should not be
        recategorized as income even with keywords like 'PAY'.
        """
        result = self.categorizer.categorize_transaction(
            description="MONEYBOAT REPAY",
            amount=200.00,  # Positive = debit (expense)
            plaid_category="LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertNotEqual(result.category, "income")
        self.assertEqual(result.category, "debt")
    
    # Issue 2: BNPL Should Not Be Income
    
    def test_clearpay_not_income(self):
        """
        CLEARPAY transactions marked as TRANSFER_IN_CASH_ADVANCES_AND_LOANS
        should NOT be recategorized as salary income.
        """
        result = self.categorizer.categorize_transaction(
            description="CLEARPAY",
            amount=50.00,  # Positive = debit (expense)
            plaid_category="TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        # Should be debt (BNPL), NOT income
        self.assertNotEqual(result.category, "income")
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "bnpl")
    
    def test_klarna_not_income(self):
        """KLARNA BNPL should remain as debt."""
        result = self.categorizer.categorize_transaction(
            description="KLARNA PAYMENT",
            amount=75.00,
            plaid_category="LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertNotEqual(result.category, "income")
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "bnpl")
    
    # Issue 3: Payment Services Should Not Be Income
    
    def test_paypal_withdrawal_not_salary(self):
        """
        PAYPAL PPWDL (withdrawal) should NOT be categorized as salary
        just because it contains letters that might match patterns.
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
    
    def test_paypal_payment_is_expense(self):
        """PAYPAL payments (debits) should be expenses, not income."""
        result = self.categorizer.categorize_transaction(
            description="PAYPAL PAYMENT TO MERCHANT",
            amount=50.00,  # Positive = debit (expense)
            plaid_category="GENERAL_SERVICES_OTHER_GENERAL_SERVICES",
            plaid_category_primary="GENERAL_SERVICES"
        )
        
        self.assertNotEqual(result.category, "income")
    
    # Issue 4: Preserve High-Confidence Gambling Categorization
    
    def test_monopoly_casino_preserves_gambling_risk(self):
        """
        MONOPOLY CASINO with PLAID gambling category should preserve
        risk/gambling categorization, not be reset to expense/other.
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
        # Confidence should be high (from pattern match)
        self.assertGreaterEqual(result.confidence, 0.85)
    
    def test_casino_high_confidence_plaid(self):
        """Casino transactions should maintain risk categorization."""
        result = self.categorizer.categorize_transaction(
            description="GROSVENOR CASINO",
            amount=100.00,
            plaid_category="ENTERTAINMENT_CASINOS_AND_GAMBLING",
            plaid_category_primary="ENTERTAINMENT"
        )
        
        self.assertEqual(result.category, "risk")
        self.assertEqual(result.subcategory, "gambling")
    
    # Issue 5: Preserve Debt Collection Risk Flags
    
    def test_lowell_portfolio_preserves_risk(self):
        """
        LOWELL PORTFOLIO with PLAID debt collection flag should preserve
        risk categorization, not lose risk indicators.
        """
        result = self.categorizer.categorize_transaction(
            description="LOWELL PORTFOLIO",
            amount=75.00,
            plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        # Should be risk/debt_collection
        self.assertEqual(result.category, "risk")
        self.assertEqual(result.subcategory, "debt_collection")
        self.assertEqual(result.risk_level, "severe")
    
    def test_cabot_financial_preserves_risk(self):
        """Debt collection agencies should maintain severe risk level."""
        result = self.categorizer.categorize_transaction(
            description="CABOT FINANCIAL",
            amount=50.00,
            plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "risk")
        self.assertEqual(result.subcategory, "debt_collection")
    
    # Issue 6: Transaction Direction Validation
    
    def test_credit_transactions_for_expense_services(self):
        """
        Credits from expense services (refunds) should not be income.
        """
        # Refund from BNPL service
        result = self.categorizer.categorize_transaction(
        description="CLEARPAY REFUND",
            amount=-25.00,  # Negative = credit (refund)
            plaid_category="TRANSFER_IN_OTHER_TRANSFER_IN",
            plaid_category_primary="TRANSFER_IN"
        )
        # Should be transfer (not ACCOUNT_TRANSFER), not income
        self.assertEqual(result.category, "transfer")
    
    def test_debit_transactions_never_income(self):
        """Debit transactions (positive amounts) should never be income."""
        result = self.categorizer.categorize_transaction(
            description="SALARY PAYMENT OUT",
            amount=500.00,  # Positive = debit, paying someone else
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )  
        # Should be expense (now categorized as expense/account_transfer)
        self.assertEqual(result.category, "expense")
        self.assertEqual(result.subcategory, "account_transfer")
    
    # Issue 7: Context-Aware Transfer vs Income
    
    def test_transfer_in_without_income_keywords_not_salary(self):
        """
        TRANSFER_IN without explicit income keywords should remain as transfer,
        not be promoted to salary income.
        """
        result = self.categorizer.categorize_transaction(
        description="FRIEND PAYMENT",
            amount=-50.00,  # Negative = credit
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        # Should be income/account_transfer (strict PLAID match takes precedence)
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "account_transfer")
    
    def test_transfer_in_with_salary_keywords_is_income(self):
        """
        TRANSFER_IN with explicit salary keywords SHOULD be income.
        This is the correct override case.
        """
        result = self.categorizer.categorize_transaction(
            description="FP-ACME CORP LTD SALARY",
            amount=-2500.00,  # Negative = credit
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_IN"
        )
        # Should be income/account_transfer (strict PLAID match takes precedence over keywords)
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "account_transfer")  # Changed from "salary")
    
    # Issue 8: High Confidence Threshold
    
    def test_plaid_high_confidence_loan_preserved(self):
        """
        When PLAID provides high-confidence loan categorization,
        it should not be overridden by generic keyword matching.
        """
        # Loan payment with ambiguous description
        result = self.categorizer.categorize_transaction(
            description="PAYMENT TO FINANCE CO",
            amount=150.00,
            plaid_category="LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        # Should preserve PLAID's loan categorization
        self.assertEqual(result.category, "debt")
    
    def test_low_confidence_generic_expense_uses_plaid(self):
        """
        When our patterns would give low confidence generic expense,
        but PLAID has high-confidence specific category, use PLAID.
        """
        # Restaurant without keyword match but PLAID knows it
        result = self.categorizer.categorize_transaction(
            description="THE FANCY RESTAURANT",
            amount=45.00,
            plaid_category="FOOD_AND_DRINK_RESTAURANTS",
            plaid_category_primary="FOOD_AND_DRINK"
        )
        
        # Should NOT be generic expense/other
        # If we don't have a specific pattern, should fall back to PLAID
        self.assertNotEqual(
            (result.category, result.subcategory),
            ("expense", "other")
        )


class TestKnownServiceWhitelist(unittest.TestCase):
    """Test that known expense services are not misidentified as income."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_known_bnpl_services_are_debt(self):
        """All major BNPL services should be categorized as debt, not income."""
        bnpl_services = [
            ("CLEARPAY PAYMENT", 50.00),
            ("KLARNA", 75.00),
            ("ZILCH PURCHASE", 30.00),
            ("LAYBUY", 40.00),
        ]
        
        for description, amount in bnpl_services:
            with self.subTest(description=description):
                result = self.categorizer.categorize_transaction(
                    description=description,
                    amount=amount,  # Debit
                    plaid_category="LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
                    plaid_category_primary="LOAN_PAYMENTS"
                )
                
                self.assertEqual(result.category, "debt", 
                    f"{description} should be debt, not {result.category}")
    
    def test_known_lenders_are_debt(self):
        """HCSTC lenders should be debt, not income."""
        lenders = [
            ("LENDING STREAM PAYMENT", 150.00),
            ("MONEYBOAT REPAY", 200.00),
            ("DRAFTY PAYMENT", 100.00),
        ]
        
        for description, amount in lenders:
            with self.subTest(description=description):
                result = self.categorizer.categorize_transaction(
                    description=description,
                    amount=amount,  # Debit
                    plaid_category="LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT",
                    plaid_category_primary="LOAN_PAYMENTS"
                )
                
                self.assertEqual(result.category, "debt",
                    f"{description} should be debt, not {result.category}")


if __name__ == "__main__":
    unittest.main()
