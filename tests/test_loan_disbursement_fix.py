"""
Test suite for loan disbursement categorization fix.

Tests that PLAID LOAN_PAYMENTS categories for credit transactions (loan disbursements)
are correctly categorized as income/loans with weight=0.0, preventing them from
inflating effective monthly income in scoring.

Addresses the issue where 46+ transactions with PLAID category LOAN_PAYMENTS
were being recategorized as income/salary or income/other.
"""

import unittest
from transaction_categorizer import TransactionCategorizer


class TestLoanDisbursementCategorization(unittest.TestCase):
    """Test cases for loan disbursement categorization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_visa_direct_payment_barclays(self):
        """
        VISA DIRECT PAYMENT Barclays Cashback - loan repayment credit
        Should be income/loans (weight=0.0), not income/salary
        """
        result = self.categorizer.categorize_transaction(
            description="VISA DIRECT PAYMENT Barclays Cashback",
            amount=-150.00,  # Negative = credit (money IN)
            plaid_category="LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
        self.assertFalse(result.is_stable)
        self.assertEqual(result.match_method, "plaid")
        self.assertGreaterEqual(result.confidence, 0.9)
    
    def test_mr_lender_disbursement(self):
        """
        MR LENDER loan disbursements should be income/loans (weight=0.0)
        """
        test_cases = [
            "MR LENDER 05MAY24",
            "MR LENDER ML65609059",
            "MRLENDER PAYMENT"
        ]
        
        for description in test_cases:
            with self.subTest(description=description):
                result = self.categorizer.categorize_transaction(
                    description=description,
                    amount=-300.00,
                    plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
                    plaid_category_primary="LOAN_PAYMENTS"
                )
                
                self.assertEqual(result.category, "income")
                self.assertEqual(result.subcategory, "loans")
                self.assertEqual(result.weight, 0.0)
    
    def test_klarna_refund(self):
        """
        KLARNA REFUND should be income/loans (weight=0.0), not income/other
        """
        result = self.categorizer.categorize_transaction(
            description="KLARNA REFUND",
            amount=-50.00,
            plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_hsbc_loan_reversal(self):
        """
        REVERSAL OF HSBC PLC LOANS should be income/loans, not income/salary
        """
        result = self.categorizer.categorize_transaction(
            description="REVERSAL OF HSBC PLC LOANS",
            amount=-100.00,
            plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_zopa_personal_loan(self):
        """
        ZOPA BANK LIMITED PERSONAL LOAN should be income/loans, not income/salary
        """
        result = self.categorizer.categorize_transaction(
            description="ZOPA BANK LIMITED PERSONAL LOAN",
            amount=-500.00,
            plaid_category="LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_various_loan_providers(self):
        """
        Test various loan providers mentioned in the issue
        """
        loan_providers = [
            ("LENDABLE LOAN DISBURSEMENT", -400.00),
            ("TOTALSA PAYMENT", -200.00),
            ("AQUA CARD REFUND", -75.00),
            ("HSBC LOANS REVERSAL", -150.00),
        ]
        
        for description, amount in loan_providers:
            with self.subTest(description=description):
                result = self.categorizer.categorize_transaction(
                    description=description,
                    amount=amount,
                    plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
                    plaid_category_primary="LOAN_PAYMENTS"
                )
                
                self.assertEqual(result.category, "income")
                self.assertEqual(result.subcategory, "loans")
                self.assertEqual(result.weight, 0.0)
                self.assertFalse(result.is_stable)
    
    def test_plaid_loan_payments_always_respected(self):
        """
        PLAID LOAN_PAYMENTS category should ALWAYS be respected,
        even with strong income keywords
        """
        test_cases = [
            "SALARY LOAN REFUND",  # Contains "SALARY"
            "PAYMENT FROM LENDER",  # Contains "PAYMENT"
            "WAGES LOAN REVERSAL",  # Contains "WAGES"
        ]
        
        for description in test_cases:
            with self.subTest(description=description):
                result = self.categorizer.categorize_transaction(
                    description=description,
                    amount=-200.00,
                    plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
                    plaid_category_primary="LOAN_PAYMENTS"
                )
                
                # Should be loans, NOT salary, even with salary keywords
                self.assertEqual(result.category, "income")
                self.assertEqual(result.subcategory, "loans")
                self.assertEqual(result.weight, 0.0)
    
    def test_loan_payments_expense_still_debt(self):
        """
        Verify that loan PAYMENTS (debits/expenses) are still categorized as debt
        This test ensures we didn't break existing functionality for expense transactions
        """
        result = self.categorizer.categorize_transaction(
            description="MR LENDER PAYMENT",
            amount=150.00,  # Positive = debit (expense/payment OUT)
            plaid_category="LOAN_PAYMENTS_CREDIT_CARD_PAYMENT",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        # Expense loan payments should still be debt, not income
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "hcstc_payday")
    
    def test_batch_categorization_respects_loan_payments(self):
        """
        Test that batch categorization also respects PLAID LOAN_PAYMENTS
        """
        transactions = [
            {
                "description": "VISA DIRECT PAYMENT",
                "amount": -150.00,
                "personal_finance_category": {
                    "primary": "LOAN_PAYMENTS",
                    "detailed": "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT"
                }
            },
            {
                "description": "MR LENDER 05MAY24",
                "amount": -300.00,
                "personal_finance_category": {
                    "primary": "LOAN_PAYMENTS",
                    "detailed": "LOAN_PAYMENTS_OTHER_PAYMENT"
                }
            },
            {
                "description": "ZOPA BANK LIMITED PERSONAL LOAN",
                "amount": -500.00,
                "personal_finance_category": {
                    "primary": "LOAN_PAYMENTS",
                    "detailed": "LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # All should be categorized as income/loans with weight=0.0
        for tx, result in results:
            with self.subTest(description=tx["description"]):
                self.assertEqual(result.category, "income")
                self.assertEqual(result.subcategory, "loans")
                self.assertEqual(result.weight, 0.0)
                self.assertFalse(result.is_stable)
    
    def test_weight_zero_prevents_income_inflation(self):
        """
        Verify that weight=0.0 means these transactions won't inflate income calculations
        """
        loan_disbursements = [
            ("VISA DIRECT PAYMENT", -150.00),
            ("MR LENDER LOAN", -300.00),
            ("ZOPA PERSONAL LOAN", -500.00),
        ]
        
        total_weighted_income = 0.0
        
        for description, amount in loan_disbursements:
            result = self.categorizer.categorize_transaction(
                description=description,
                amount=amount,
                plaid_category="LOAN_PAYMENTS_OTHER_PAYMENT",
                plaid_category_primary="LOAN_PAYMENTS"
            )
            
            # Calculate weighted income (negative amount * weight)
            weighted_amount = abs(amount) * result.weight
            total_weighted_income += weighted_amount
        
        # Total weighted income should be 0.0 (none of these count as real income)
        self.assertEqual(total_weighted_income, 0.0,
                        "Loan disbursements should not contribute to weighted income")
    
    def test_without_plaid_category_uses_keyword_matching(self):
        """
        Test that without PLAID category, keyword matching still works
        """
        result = self.categorizer.categorize_transaction(
            description="LOAN DISBURSEMENT FROM BANK",
            amount=-400.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        
        # Should match keyword patterns for loans
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)


if __name__ == '__main__':
    unittest.main()
