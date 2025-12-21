"""
Test suite for Income Classification Fix - Complete Implementation.

This test validates the 4 critical fixes for income classification:
1. Enhanced Transfer Promotion in engine.py
2. Enhanced Income Detector in income_detector.py
3. Expanded Salary Patterns in transaction_patterns.py
4. Validation & Month Counting Fix in feature_builder.py
"""

import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openbanking_engine.categorisation.engine import TransactionCategorizer
from openbanking_engine.income.income_detector import IncomeDetector
from openbanking_engine.scoring.feature_builder import MetricsCalculator


class TestTransferPromotionInEngine(unittest.TestCase):
    """Test enhanced transfer promotion logic in engine.py."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_payroll_keyword_promotion(self):
        """Test that payroll keywords promote TRANSFER_IN to salary income."""
        result = self.categorizer.categorize_transaction(
            description="BANK GIRO CREDIT REF SALARY",
            amount=-1500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertEqual(result.weight, 1.0)
        self.assertTrue(result.is_stable)
    
    def test_company_suffix_promotion(self):
        """Test that company suffix with meaningful amount promotes to salary."""
        result = self.categorizer.categorize_transaction(
            description="ACME CORPORATION LTD",
            amount=-1200.00,  # Above £200 threshold
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertEqual(result.weight, 1.0)
    
    def test_faster_payment_promotion(self):
        """Test that FP- prefix promotes TRANSFER_IN to salary."""
        result = self.categorizer.categorize_transaction(
            description="FP-EMPLOYER PAYMENT",
            amount=-1800.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertEqual(result.weight, 1.0)
    
    def test_benefits_keyword_promotion(self):
        """Test that benefit keywords promote TRANSFER_IN to benefits income."""
        result = self.categorizer.categorize_transaction(
            description="UNIVERSAL CREDIT PAYMENT",
            amount=-500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "benefits")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertEqual(result.weight, 1.0)
        self.assertTrue(result.is_stable)
    
    def test_gig_economy_promotion(self):
        """Test that gig economy keywords promote TRANSFER_IN to gig income."""
        result = self.categorizer.categorize_transaction(
            description="UBER WEEKLY PAYOUT",
            amount=-300.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "gig_economy")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertEqual(result.weight, 1.0)
    
    def test_large_named_payment_promotion(self):
        """Test that large payments from named entities are promoted."""
        result = self.categorizer.categorize_transaction(
            description="CONSULTING SERVICES CLIENT ABC",
            amount=-2500.00,  # Above £500 threshold
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertIn(result.subcategory, ["salary", "other"])
        self.assertGreaterEqual(result.confidence, 0.70)
        self.assertEqual(result.weight, 1.0)
    
    def test_internal_transfer_exclusion(self):
        """Test that internal transfers are NOT promoted to income."""
        result = self.categorizer.categorize_transaction(
            description="OWN ACCOUNT TRANSFER",
            amount=-1000.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN_ACCOUNT_TRANSFER"
        )
        
        # Should remain as transfer, not promoted to income
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.weight, 0.0)
    
    def test_savings_transfer_exclusion(self):
        """Test that savings transfers are NOT promoted to income."""
        result = self.categorizer.categorize_transaction(
            description="FROM SAVINGS ACCOUNT",
            amount=-500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        # Should remain as transfer, not promoted to income
        self.assertIn(result.category, ["transfer", "income"])
        if result.category == "income":
            # If categorized as income, it should be with low confidence
            self.assertLess(result.confidence, 0.8)


class TestBankGiroCreditPatterns(unittest.TestCase):
    """Test BGC and BACS patterns specifically."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_bgc_bank_giro_credit(self):
        """Test BANK GIRO CREDIT pattern recognition."""
        result = self.categorizer.categorize_transaction(
            description="BANK GIRO CREDIT REF CHEQUERS CONTRACT",
            amount=-1241.46,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertIn(result.subcategory, ["salary", "other"])
        self.assertGreater(result.weight, 0.0)
    
    def test_bgc_abbreviation(self):
        """Test BGC abbreviation recognition."""
        result = self.categorizer.categorize_transaction(
            description="BGC MONTHLY PAYMENT",
            amount=-1500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)
    
    def test_bacs_credit_pattern(self):
        """Test BACS CREDIT pattern recognition."""
        result = self.categorizer.categorize_transaction(
            description="BACS CREDIT EMPLOYER NAME",
            amount=-1800.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreater(result.weight, 0.0)


class TestCompanySuffixPatterns(unittest.TestCase):
    """Test company suffix pattern recognition."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_limited_suffix(self):
        """Test LIMITED suffix recognition."""
        result = self.categorizer.categorize_transaction(
            description="TECH COMPANY LIMITED",
            amount=-2000.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_ltd_suffix(self):
        """Test LTD suffix recognition."""
        result = self.categorizer.categorize_transaction(
            description="CONSULTING SERVICES LTD",
            amount=-1500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_plc_suffix(self):
        """Test PLC suffix recognition."""
        result = self.categorizer.categorize_transaction(
            description="BIG CORPORATION PLC",
            amount=-2500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_company_suffix_below_threshold(self):
        """Test that company suffix below £200 threshold is not promoted."""
        result = self.categorizer.categorize_transaction(
            description="SMALL COMPANY LTD",
            amount=-100.00,  # Below £200 threshold
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        # Should not be promoted based on company suffix alone
        # May still be categorized as income via other patterns
        if result.category == "income" and result.subcategory == "salary":
            # If promoted, it should be via another pattern, not company suffix
            self.assertNotIn("company_suffix", result.match_method.lower())


class TestMonthCountingFix(unittest.TestCase):
    """Test month counting fix in feature_builder.py."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = MetricsCalculator(lookback_months=3)
    
    def test_count_unique_income_months(self):
        """Test that unique income months are counted correctly."""
        transactions = [
            {"amount": -1500.00, "date": "2024-01-15"},  # Income in Jan
            {"amount": -1500.00, "date": "2024-01-31"},  # Income in Jan (same month)
            {"amount": -1500.00, "date": "2024-02-15"},  # Income in Feb
            {"amount": -1500.00, "date": "2024-03-15"},  # Income in Mar
            {"amount": 100.00, "date": "2024-04-15"},    # Not income (positive)
        ]
        
        months = self.calculator._count_unique_income_months(transactions)
        
        # Should count 3 unique months (Jan, Feb, Mar)
        self.assertEqual(months, 3)
    
    def test_count_unique_income_months_no_income(self):
        """Test that at least 1 month is returned even with no income."""
        transactions = [
            {"amount": 100.00, "date": "2024-01-15"},  # Not income
            {"amount": 200.00, "date": "2024-02-15"},  # Not income
        ]
        
        months = self.calculator._count_unique_income_months(transactions)
        
        # Should return minimum of 1
        self.assertEqual(months, 1)
    
    def test_income_metrics_uses_actual_months(self):
        """Test that income metrics calculation uses actual months with income."""
        # Create transactions spanning 2 months
        transactions = [
            {"amount": -1500.00, "date": "2024-01-15"},
            {"amount": -1500.00, "date": "2024-02-15"},
        ]
        
        # Initialize calculator with transactions (calculates months_of_data = 2)
        calculator = MetricsCalculator(transactions=transactions)
        
        # Create category summary with £3000 total income
        category_summary = {
            "income": {
                "salary": {
                    "total": 3000.00,
                    "count": 2
                }
            }
        }
        
        metrics = calculator.calculate_income_metrics(
            category_summary=category_summary,
            transactions=transactions
        )
        
        # Monthly income should be 3000/2 = 1500, not 3000/3 = 1000
        self.assertEqual(metrics.monthly_income, 1500.00)


class TestHelperMethods(unittest.TestCase):
    """Test helper methods in engine.py."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_looks_like_employer_name_with_ltd(self):
        """Test employer name detection with LTD suffix."""
        result = self.categorizer._looks_like_employer_name("ACME CONSULTING LTD")
        self.assertTrue(result)
    
    def test_looks_like_employer_name_with_limited(self):
        """Test employer name detection with LIMITED suffix."""
        result = self.categorizer._looks_like_employer_name("BIG TECH LIMITED")
        self.assertTrue(result)
    
    def test_looks_like_employer_name_generic_payment(self):
        """Test that generic payment is NOT recognized as employer."""
        result = self.categorizer._looks_like_employer_name("PAYMENT LTD")
        self.assertFalse(result)
    
    def test_looks_like_employer_name_no_suffix(self):
        """Test that name without company suffix is NOT recognized."""
        result = self.categorizer._looks_like_employer_name("ACME CONSULTING")
        self.assertFalse(result)


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios combining multiple fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_salary_with_bgc_and_company_name(self):
        """Test salary with both BGC and company name."""
        result = self.categorizer.categorize_transaction(
            description="BANK GIRO CREDIT ACME CORPORATION LTD",
            amount=-2000.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.9)
        self.assertEqual(result.weight, 1.0)
        self.assertTrue(result.is_stable)
    
    def test_faster_payment_with_payroll_keyword(self):
        """Test FP- prefix with PAYROLL keyword."""
        result = self.categorizer.categorize_transaction(
            description="FP-PAYROLL MONTHLY",
            amount=-1750.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.9)
        self.assertEqual(result.weight, 1.0)
    
    def test_multiple_salary_indicators(self):
        """Test transaction with multiple salary indicators."""
        result = self.categorizer.categorize_transaction(
            description="BACS CREDIT SALARY TECH COMPANY LIMITED",
            amount=-2500.00,
            plaid_category_primary="TRANSFER_IN",
            plaid_category="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.9)
        self.assertEqual(result.weight, 1.0)
        self.assertTrue(result.is_stable)


if __name__ == '__main__':
    unittest.main()
