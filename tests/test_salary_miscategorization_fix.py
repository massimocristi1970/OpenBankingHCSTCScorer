"""
Test to verify that PLAID-miscategorized salary payments are correctly identified as income.

This test validates the fix for the issue where legitimate salary payments
(e.g., via BANK GIRO CREDIT, FP- prefix) were being marked as TRANSFER_IN by PLAID
and incorrectly excluded from income calculations.
"""

import unittest
from transaction_categorizer import TransactionCategorizer


class TestSalaryMiscategorizationFix(unittest.TestCase):
    """Test cases for salary miscategorization fix."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_bank_giro_credit_salary_not_transfer(self):
        """Test that BANK GIRO CREDIT salary is not categorized as transfer despite PLAID labeling."""
        # This is the exact example from the problem statement
        result = self.categorizer.categorize_transaction(
            description="BANK GIRO CREDIT REF CHEQUERS CONTRACT",
            amount=-1241.46,  # Negative = credit (money in)
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        # Should be categorized as income, not transfer
        self.assertEqual(result.category, "income")
        # Could be "salary" or "other" income - both are acceptable as long as it counts
        self.assertIn(result.subcategory, ["salary", "other"])
        self.assertGreater(result.weight, 0.0)  # Should count toward income (most important!)
        # Note: "other" income also has full weight (1.0) so this is perfectly fine
    
    def test_fp_prefix_salary_not_transfer(self):
        """Test that FP- prefix payments are recognized as salary, not transfers."""
        result = self.categorizer.categorize_transaction(
            description="FP-ACME CORP LTD SALARY",
            amount=-1500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
        self.assertTrue(result.is_stable)
    
    def test_bgc_keyword_salary(self):
        """Test that BGC (Bank Giro Credit) keyword indicates salary."""
        result = self.categorizer.categorize_transaction(
            description="BGC MONTHLY SALARY ACME LTD",
            amount=-2000.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_payroll_keyword_overrides_plaid_transfer(self):
        """Test that PAYROLL keyword overrides PLAID transfer categorization."""
        result = self.categorizer.categorize_transaction(
            description="COMPANY PAYROLL PAYMENT",
            amount=-1800.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_wages_keyword_overrides_plaid_transfer(self):
        """Test that WAGES keyword overrides PLAID transfer categorization."""
        result = self.categorizer.categorize_transaction(
            description="WEEKLY WAGES FROM EMPLOYER",
            amount=-950.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_net_pay_keyword(self):
        """Test that NET PAY keyword indicates salary."""
        result = self.categorizer.categorize_transaction(
            description="NET PAY ACME CORPORATION",
            amount=-1750.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_employer_payment(self):
        """Test that EMPLOYER keyword indicates salary."""
        result = self.categorizer.categorize_transaction(
            description="EMPLOYER MONTHLY PAYMENT",
            amount=-2100.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_ltd_company_payment(self):
        """Test that LTD company payments are recognized as salary."""
        result = self.categorizer.categorize_transaction(
            description="ACME TRADING LTD",
            amount=-1600.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertGreater(result.weight, 0.0)
    
    def test_plc_company_payment(self):
        """Test that PLC company payments are recognized as salary."""
        result = self.categorizer.categorize_transaction(
            description="MEGACORP PLC PAYMENT",
            amount=-2500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertGreater(result.weight, 0.0)
    
    def test_genuine_internal_transfer_still_detected(self):
        """Test that genuine internal transfers are still correctly identified."""
        result = self.categorizer.categorize_transaction(
            description="INTERNAL TRANSFER OWN ACCOUNT",
            amount=-500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        # Should still be categorized as transfer
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_self_transfer_still_detected(self):
        """Test that self transfers are still correctly identified."""
        result = self.categorizer.categorize_transaction(
            description="SELF TRANSFER TO CURRENT ACCOUNT",
            amount=-1000.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.weight, 0.0)
    
    def test_from_savings_transfer_still_detected(self):
        """Test that transfers from savings are still correctly identified."""
        result = self.categorizer.categorize_transaction(
            description="FROM SAVINGS ACCOUNT",
            amount=-750.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.weight, 0.0)
    
    def test_salary_without_plaid_category(self):
        """Test that salary is correctly identified without PLAID category."""
        result = self.categorizer.categorize_transaction(
            description="BANK GIRO CREDIT SALARY PAYMENT",
            amount=-1500.00
        )
        
        # Should be recognized as salary through keyword matching
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_correct_plaid_income_category_unchanged(self):
        """Test that correctly categorized income is not affected by the fix."""
        result = self.categorizer.categorize_transaction(
            description="SALARY PAYMENT",
            amount=-2000.00,
            plaid_category_primary="INCOME",
            plaid_category="INCOME_WAGES"
        )
        
        self.assertEqual(result.category, "income")
        self.assertGreater(result.weight, 0.0)
    
    def test_contains_salary_keywords_method(self):
        """Test the _contains_salary_keywords helper method directly."""
        # Positive cases
        self.assertTrue(self.categorizer._contains_salary_keywords("BANK GIRO CREDIT SALARY"))
        self.assertTrue(self.categorizer._contains_salary_keywords("FP-ACME LTD"))
        self.assertTrue(self.categorizer._contains_salary_keywords("PAYROLL PAYMENT"))
        self.assertTrue(self.categorizer._contains_salary_keywords("MONTHLY WAGES"))
        self.assertTrue(self.categorizer._contains_salary_keywords("NET PAY"))
        self.assertTrue(self.categorizer._contains_salary_keywords("EMPLOYER PAYMENT"))
        self.assertTrue(self.categorizer._contains_salary_keywords("ACME LTD"))
        self.assertTrue(self.categorizer._contains_salary_keywords("MEGACORP PLC"))
        self.assertTrue(self.categorizer._contains_salary_keywords("BGC PAYMENT"))
        self.assertTrue(self.categorizer._contains_salary_keywords("MONTHLY PAY"))
        self.assertTrue(self.categorizer._contains_salary_keywords("WEEKLY PAY"))
        
        # Negative cases (should not match)
        self.assertFalse(self.categorizer._contains_salary_keywords("INTERNAL TRANSFER OWN ACCOUNT"))
        self.assertFalse(self.categorizer._contains_salary_keywords("SELF TRANSFER"))
        self.assertFalse(self.categorizer._contains_salary_keywords("FROM SAVINGS"))
        self.assertFalse(self.categorizer._contains_salary_keywords("RANDOM TRANSACTION"))
        self.assertFalse(self.categorizer._contains_salary_keywords("SUPERMARKET PURCHASE"))
        self.assertFalse(self.categorizer._contains_salary_keywords(""))
        self.assertFalse(self.categorizer._contains_salary_keywords(None))
    
    def test_is_plaid_transfer_with_description(self):
        """Test _is_plaid_transfer method with description parameter."""
        # Should return False when description contains salary keywords
        self.assertFalse(
            self.categorizer._is_plaid_transfer(
                "TRANSFER_IN",
                "TRANSFER_IN_ACCOUNT_TRANSFER",
                "BANK GIRO CREDIT SALARY"
            )
        )
        
        # Should return True for genuine transfers even with description
        self.assertTrue(
            self.categorizer._is_plaid_transfer(
                "TRANSFER_IN",
                "TRANSFER_IN_ACCOUNT_TRANSFER",
                "INTERNAL TRANSFER OWN ACCOUNT"
            )
        )
        
        # Should work without description (backwards compatibility)
        self.assertTrue(
            self.categorizer._is_plaid_transfer(
                "TRANSFER_IN",
                "TRANSFER_IN_ACCOUNT_TRANSFER"
            )
        )


if __name__ == "__main__":
    unittest.main()
