"""
Comprehensive test suite for transaction categorization fixes.

Tests all three issues:
1. REFUND transactions recognition (already implemented)
2. Credit Card Purchases Miscategorized as Groceries (new fix)
3. Recurring Salary Payments Not Detected (enhancement)

This test file focuses on the new Issue 2 fix and enhanced Issue 3 scenarios.
"""

import unittest
from datetime import datetime, timedelta
from openbanking_engine.categorisation.engine import TransactionCategorizer
from openbanking_engine.income.income_detector import IncomeDetector


class TestCreditCardGroceryFix(unittest.TestCase):
    """Test cases for Issue 2: Credit Card Purchases Miscategorized as Groceries."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_sainsburys_credit_card_payment_is_debt(self):
        """Test that Sainsbury's credit card payment is categorized as debt."""
        # When description includes credit card indicators (SAINSBURYS BANK)
        result = self.categorizer.categorize_transaction(
            description="SAINSBURYS BANK",
            amount=45.50,
            merchant_name="SAINSBURYS BANK",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        # Should be debt > credit_cards, not groceries
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "credit_cards")
    
    def test_sainsburys_debit_card_is_groceries(self):
        """Test that Sainsbury's debit card purchase is categorized as groceries."""
        # When description is just the store name (debit card purchase)
        result = self.categorizer.categorize_transaction(
            description="SAINSBURYS",
            amount=45.50,
            merchant_name="SAINSBURYS",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        # Should be essential > groceries
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
    
    def test_ms_catalogue_payment_is_debt(self):
        """Test that M&S catalogue payment is categorized as debt."""
        result = self.categorizer.categorize_transaction(
            description="MARKS & SPENCER CATALOGUE",
            amount=75.00,
            merchant_name="M&S",
            plaid_category="FOOD_AND_DRINK"
        )
        
        # Should be debt > catalogue
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "catalogue")
    
    def test_ms_debit_purchase_is_groceries(self):
        """Test that M&S debit purchase is categorized as groceries."""
        result = self.categorizer.categorize_transaction(
            description="MARKS & SPENCER",
            amount=32.50,
            merchant_name="M&S",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        # Should be essential > groceries
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
    
    def test_tesco_bank_credit_card_is_debt(self):
        """Test that Tesco Bank credit card payment is categorized as debt."""
        result = self.categorizer.categorize_transaction(
            description="TESCO BANK CREDIT CARD",
            amount=100.00,
            merchant_name="TESCO BANK",
            plaid_category="FOOD_AND_DRINK"
        )
        
        # Should be debt > credit_cards
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "credit_cards")
    
    def test_tesco_store_purchase_is_groceries(self):
        """Test that Tesco store purchase is categorized as groceries."""
        result = self.categorizer.categorize_transaction(
            description="TESCO STORES",
            amount=65.00,
            merchant_name="TESCO",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        # Should be essential > groceries
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
    
    def test_very_catalogue_with_food_plaid_is_debt(self):
        """Test that VERY catalogue payment is categorized as debt even with FOOD_AND_DRINK."""
        result = self.categorizer.categorize_transaction(
            description="VERY CATALOGUE",
            amount=50.00,
            merchant_name="VERY",
            plaid_category="FOOD_AND_DRINK"
        )
        
        # Should be debt > catalogue, not groceries
        self.assertEqual(result.category, "debt")
        self.assertEqual(result.subcategory, "catalogue")


class TestEnhancedSalaryDetection(unittest.TestCase):
    """Test cases for Issue 3: Enhanced Recurring Salary Detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = IncomeDetector()
        self.categorizer = TransactionCategorizer()
    
    def test_bbc_monthly_tight_variance_detected_as_salary(self):
        """Test that BBC MONTHLY with tight variance is detected as salary."""
        # BBC MONTHLY: 12 payments, £3,370-£3,578 (±4.2%), consistent day-of-month
        base_date = datetime(2024, 1, 15)
        amounts = [3370, 3400, 3450, 3500, 3520, 3540, 3560, 3578, 3550, 3530, 3510, 3490]
        transactions = []
        
        for i, amount in enumerate(amounts):
            # Payments on 15th ±2 days (consistent within ±3 days)
            day_offset = (i % 3) - 1  # -1, 0, 1, -1, 0, 1, ...
            date = base_date.replace(month=((base_date.month + i - 1) % 12) + 1) + timedelta(days=day_offset)
            transactions.append({
                "name": "BBC MONTHLY",
                "amount": -amount,
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Find recurring sources
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should detect as salary with high confidence
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        self.assertEqual(source.source_type, "salary")
        self.assertTrue(source.day_of_month_consistent)
        self.assertGreaterEqual(source.confidence, 0.85)
        print(f"BBC MONTHLY detected with confidence: {source.confidence:.2f}")
    
    def test_acme_corp_behavioral_salary_detection(self):
        """Test that ACME CORP with regular pattern is detected as salary."""
        # ACME CORP: 12 payments, £2,500±3%, consistent day
        base_date = datetime(2024, 1, 25)
        base_amount = 2500.00
        transactions = []
        
        for i in range(12):
            # Vary amount by ±3%
            variance = (i % 5 - 2) * 0.015  # -3%, -1.5%, 0%, 1.5%, 3%
            amount = base_amount * (1 + variance)
            # Payments on 25th ±1 day
            day_offset = (i % 3) - 1
            date = base_date.replace(month=((base_date.month + i - 1) % 12) + 1) + timedelta(days=day_offset)
            transactions.append({
                "name": "ACME CORP",
                "amount": -amount,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        self.assertEqual(source.source_type, "salary")
        self.assertTrue(source.day_of_month_consistent)
        self.assertGreaterEqual(source.confidence, 0.85)
        print(f"ACME CORP detected with confidence: {source.confidence:.2f}")
    
    def test_jl_employee_fortnightly_salary(self):
        """Test that fortnightly payments are detected as salary."""
        # JL EMPLOYEE: 26 payments, £1,200±2%, fortnightly
        base_date = datetime(2024, 1, 15)
        base_amount = 1200.00
        transactions = []
        
        for i in range(26):
            # Vary amount by ±2%
            variance = (i % 3 - 1) * 0.01  # -1%, 0%, 1%
            amount = base_amount * (1 + variance)
            date = base_date + timedelta(days=14 * i)
            transactions.append({
                "name": "JL EMPLOYEE",
                "amount": -amount,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        self.assertEqual(source.source_type, "salary")
        # Fortnightly doesn't have day-of-month consistency in same way
        self.assertGreaterEqual(source.confidence, 0.80)
        print(f"JL EMPLOYEE fortnightly detected with confidence: {source.confidence:.2f}")
    
    def test_unknown_employer_behavioral_detection(self):
        """Test that ANY employer with regular pattern is detected as salary."""
        # XYZ COMPANY: 12 payments, £3,000, consistent pattern
        base_date = datetime(2024, 1, 20)
        transactions = []
        
        for i in range(12):
            date = base_date.replace(month=((base_date.month + i - 1) % 12) + 1)
            transactions.append({
                "name": "XYZ COMPANY",
                "amount": -3000.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should detect even without salary keywords
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        self.assertEqual(source.source_type, "salary")
        self.assertGreaterEqual(source.confidence, 0.85)
    
    def test_high_variance_not_detected_as_salary(self):
        """Test that high variance payments are not detected as salary."""
        # Irregular payments with >5% variance
        base_date = datetime(2024, 1, 15)
        amounts = [2000, 2500, 3000, 2200, 2800]  # High variance
        transactions = []
        
        for i, amount in enumerate(amounts):
            date = base_date + timedelta(days=30 * i)
            transactions.append({
                "name": "VARIABLE PAY",
                "amount": -amount,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should NOT detect as salary due to high variance
        # May detect as unknown or not detect at all
        if len(recurring_sources) > 0:
            source = recurring_sources[0]
            self.assertNotEqual(source.source_type, "salary")
    
    def test_min_occurrences_three_enforced(self):
        """Test that minimum 3 occurrences is required for salary classification."""
        # Only 2 occurrences
        base_date = datetime(2024, 1, 15)
        transactions = []
        
        for i in range(2):
            date = base_date + timedelta(days=30 * i)
            transactions.append({
                "name": "EMPLOYER PAY",
                "amount": -2500.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should NOT detect with only 2 occurrences
        self.assertEqual(len(recurring_sources), 0)


class TestBatchProcessingWithFixes(unittest.TestCase):
    """Test that batch processing preserves all fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_batch_credit_card_vs_grocery_detection(self):
        """Test that batch processing correctly distinguishes credit card vs grocery."""
        transactions = [
            {
                "name": "SAINSBURYS",
                "amount": 45.50,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            },
            {
                "name": "SAINSBURYS BANK",
                "amount": 100.00,
                "date": "2024-01-16",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # First should be groceries
        txn1, match1 = results[0]
        self.assertEqual(match1.category, "essential")
        self.assertEqual(match1.subcategory, "groceries")
        
        # Second should be credit card debt
        txn2, match2 = results[1]
        self.assertEqual(match2.category, "debt")
        self.assertEqual(match2.subcategory, "credit_cards")
    
    def test_batch_recurring_salary_detection(self):
        """Test that batch processing detects recurring salary patterns."""
        # Create 12 months of salary payments
        base_date = datetime(2024, 1, 25)
        transactions = []
        
        for i in range(12):
            date = base_date.replace(month=((base_date.month + i - 1) % 12) + 1)
            transactions.append({
                "name": "BBC MONTHLY",
                "amount": -2500.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # All should be categorized as salary
        for txn, match in results:
            self.assertEqual(match.category, "income")
            self.assertEqual(match.subcategory, "salary")
            self.assertGreaterEqual(match.confidence, 0.70)


if __name__ == '__main__':
    unittest.main()
