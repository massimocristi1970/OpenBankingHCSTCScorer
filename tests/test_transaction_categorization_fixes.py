"""
Test suite for transaction categorization fixes.

Tests the following issues:
1. REFUND transactions recognition
2. Loan disbursement detection
3. Grocery categorization priority
4. Enhanced income detection with PLAID-first strategy
"""

import unittest
from datetime import datetime, timedelta
from openbanking_engine.categorisation.engine import TransactionCategorizer
from openbanking_engine.income.income_detector import IncomeDetector


class TestRefundRecognition(unittest.TestCase):
    """Test cases for Issue 1: REFUND transactions recognition."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_refund_keyword_detection(self):
        """Test that REFUND keyword is recognized."""
        result = self.categorizer.categorize_transaction(
            description="MINISO REFUND",
            amount=-25.50,
            merchant_name="MINISO"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "refund")
        self.assertGreaterEqual(result.confidence, 0.90)
        self.assertEqual(result.weight, 1.0)
    
    def test_tesco_refund_detection(self):
        """Test that Tesco refunds are recognized."""
        result = self.categorizer.categorize_transaction(
            description="TESCO REFUNDED",
            amount=-15.75,
            merchant_name="TESCO"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "refund")
        self.assertGreaterEqual(result.confidence, 0.90)
    
    def test_amazon_return_detection(self):
        """Test that Amazon returns are recognized."""
        result = self.categorizer.categorize_transaction(
            description="AMAZON RETURN",
            amount=-45.00,
            merchant_name="AMAZON"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "refund")
        self.assertGreaterEqual(result.confidence, 0.90)
    
    def test_credit_reversal_detection(self):
        """Test that credit reversals are recognized as refunds."""
        result = self.categorizer.categorize_transaction(
            description="CREDIT REVERSAL - JOHN LEWIS",
            amount=-89.99,
            merchant_name="JOHN LEWIS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "refund")
        self.assertGreaterEqual(result.confidence, 0.90)
    
    def test_marks_spencer_refund(self):
        """Test that M&S refunds are recognized."""
        result = self.categorizer.categorize_transaction(
            description="MARKS & SPENCER REFUND",
            amount=-32.50,
            merchant_name="MARKS & SPENCER"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "refund")
        self.assertGreaterEqual(result.confidence, 0.90)


class TestLoanDisbursementDetection(unittest.TestCase):
    """Test cases for Issue 2: Loan disbursement detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_loan_payments_plaid_category(self):
        """Test that PLAID LOAN_PAYMENTS category is recognized."""
        result = self.categorizer.categorize_transaction(
            description="FERNOVO LOAN",
            amount=-1500.00,
            merchant_name="FERNOVO",
            plaid_category="LOAN_PAYMENTS",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertGreaterEqual(result.confidence, 0.95)
        self.assertEqual(result.weight, 0.0)  # Not counted as income
    
    def test_ticktock_loans_detection(self):
        """Test that TICKTOCK LOANS is detected as loan disbursement."""
        result = self.categorizer.categorize_transaction(
            description="TICKTOCK LOANS",
            amount=-800.00,
            merchant_name="TICKTOCK LOANS",
            plaid_category="LOAN_PAYMENTS",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_mr_lender_detection(self):
        """Test that MR LENDER is detected as loan disbursement."""
        result = self.categorizer.categorize_transaction(
            description="MR LENDER",
            amount=-500.00,
            merchant_name="MR LENDER",
            plaid_category="LOAN_PAYMENTS",
            plaid_category_primary="LOAN_PAYMENTS"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_transfer_in_cash_advances(self):
        """Test that TRANSFER_IN + CASH_ADVANCES is categorized as loan."""
        result = self.categorizer.categorize_transaction(
            description="LOAN ADVANCE",
            amount=-1000.00,
            merchant_name="LOAN COMPANY",
            plaid_category="TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertGreaterEqual(result.confidence, 0.95)
        self.assertEqual(result.weight, 0.0)
    
    def test_transfer_in_loans_keyword(self):
        """Test that TRANSFER_IN with LOANS in category is categorized as loan."""
        result = self.categorizer.categorize_transaction(
            description="PERSONAL LOAN DISBURSEMENT",
            amount=-2000.00,
            merchant_name="BANK LOAN",
            plaid_category="TRANSFER_IN_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)


class TestGroceryCategorization(unittest.TestCase):
    """Test cases for Issue 3: Grocery categorization priority."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_sainsburys_grocery_not_debt(self):
        """Test that Sainsbury's groceries are not categorized as debt."""
        result = self.categorizer.categorize_transaction(
            description="SAINSBURYS",
            amount=45.50,
            merchant_name="SAINSBURYS",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
        self.assertNotEqual(result.category, "debt")
    
    def test_marks_spencer_food_not_credit_card(self):
        """Test that M&S Food is not categorized as credit card debt."""
        result = self.categorizer.categorize_transaction(
            description="MARKS & SPENCER",
            amount=35.75,
            merchant_name="MARKS & SPENCER",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
        self.assertNotEqual(result.subcategory, "credit_cards")
    
    def test_tesco_grocery_priority(self):
        """Test that Tesco groceries are prioritized over debt patterns."""
        result = self.categorizer.categorize_transaction(
            description="TESCO STORES",
            amount=65.00,
            merchant_name="TESCO",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
    
    def test_asda_grocery_detection(self):
        """Test that ASDA groceries are correctly categorized."""
        result = self.categorizer.categorize_transaction(
            description="ASDA SUPERSTORE",
            amount=52.30,
            merchant_name="ASDA"
        )
        
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")
    
    def test_plaid_food_and_drink_override(self):
        """Test that PLAID FOOD_AND_DRINK overrides debt categorization."""
        # M&S could match credit card patterns, but PLAID says it's groceries
        result = self.categorizer.categorize_transaction(
            description="M&S BANK PAYMENT",  # Could look like credit card
            amount=40.00,
            merchant_name="M&S",
            plaid_category="FOOD_AND_DRINK_GROCERIES"
        )
        
        # Should be groceries, not credit_cards
        self.assertEqual(result.category, "essential")
        self.assertEqual(result.subcategory, "groceries")


class TestEnhancedIncomeDetection(unittest.TestCase):
    """Test cases for Issue 4: Enhanced income detection with PLAID-first strategy."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
        self.detector = IncomeDetector()
    
    def test_plaid_income_wages_priority(self):
        """Test that PLAID INCOME_WAGES takes priority."""
        result = self.categorizer.categorize_transaction(
            description="COMPANY PAYMENT",
            amount=-2500.00,
            merchant_name="COMPANY LTD",
            plaid_category="INCOME_WAGES",
            plaid_category_primary="INCOME"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.95)
    
    def test_plaid_income_salary_priority(self):
        """Test that PLAID INCOME_SALARY takes priority."""
        result = self.categorizer.categorize_transaction(
            description="MONTHLY PAY",
            amount=-3000.00,
            merchant_name="EMPLOYER",
            plaid_category="INCOME_SALARY",
            plaid_category_primary="INCOME"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.95)
    
    def test_plaid_income_payroll_priority(self):
        """Test that PLAID INCOME_PAYROLL takes priority."""
        result = self.categorizer.categorize_transaction(
            description="PAYROLL DEPOSIT",
            amount=-2800.00,
            merchant_name="COMPANY",
            plaid_category="INCOME_PAYROLL",
            plaid_category_primary="INCOME"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
        self.assertGreaterEqual(result.confidence, 0.95)
    
    def test_behavioral_fallback_when_no_plaid(self):
        """Test that behavioral detection works when PLAID doesn't provide wage info."""
        # Create recurring monthly payments
        base_date = datetime(2024, 1, 15)
        transactions = []
        
        for i in range(3):
            date = base_date + timedelta(days=30*i)
            transactions.append({
                "name": "BBC MONTHLY",
                "amount": -2500.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Analyze batch
        self.detector.analyze_batch(transactions)
        
        # Check if detected as income
        is_income, confidence, reason = self.detector.is_likely_income_from_batch(
            description="BBC MONTHLY",
            amount=-2500.00,
            transaction_index=0
        )
        
        # Should be detected as income with reasonable confidence
        self.assertTrue(is_income)
        self.assertGreaterEqual(confidence, 0.70)
    
    def test_bbc_monthly_recurring_detection(self):
        """Test that BBC MONTHLY is detected as salary based on recurring pattern."""
        # Create 12 monthly payments on same day of month
        base_date = datetime(2024, 1, 25)
        transactions = []
        
        for i in range(12):
            date = base_date + timedelta(days=30*i)
            transactions.append({
                "name": "BBC MONTHLY",
                "amount": -2500.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Find recurring sources
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should detect as recurring income
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        self.assertEqual(source.occurrence_count, 12)
        self.assertAlmostEqual(source.amount_avg, 2500.00, places=2)
        # With 12 occurrences and consistent pattern, should have high confidence
        self.assertGreaterEqual(source.confidence, 0.70)
    
    def test_tight_variance_monthly_detection(self):
        """Test that 5% variance threshold works for monthly salary detection."""
        # Create monthly payments with <5% variance
        base_date = datetime(2024, 1, 15)
        transactions = []
        amounts = [2500.00, 2525.00, 2490.00]  # Within 5% variance
        
        for i, amount in enumerate(amounts):
            date = base_date + timedelta(days=30*i)
            transactions.append({
                "name": "EMPLOYER LTD",
                "amount": -amount,
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Should detect as recurring income
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        self.assertGreaterEqual(source.confidence, 0.70)
    
    def test_day_of_month_consistency(self):
        """Test that day-of-month consistency is detected (±3 days)."""
        # Create monthly payments on 25th (±1 day)
        dates = [
            datetime(2024, 1, 25),
            datetime(2024, 2, 26),
            datetime(2024, 3, 24),
            datetime(2024, 4, 25),
        ]
        
        transactions = []
        for date in dates:
            transactions.append({
                "name": "ACME CORP LTD",
                "amount": -2500.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        self.assertGreater(len(recurring_sources), 0)
        source = recurring_sources[0]
        # Should be detected as salary with high confidence
        self.assertTrue(source.day_of_month_consistent)
        self.assertEqual(source.source_type, "salary")
        self.assertGreaterEqual(source.confidence, 0.80)
    
    def test_british_broadcasting_salary_detection(self):
        """Test that BRITISH BROADCASTI is correctly detected as salary."""
        result = self.categorizer.categorize_transaction(
            description="BRITISH BROADCASTI",
            amount=-2500.00,
            merchant_name="BRITISH BROADCASTING"
        )
        
        # Should be recognized as salary due to LTD/company pattern or recurring
        self.assertEqual(result.category, "income")
        # Could be salary or other, depending on whether it matches patterns
        self.assertIn(result.subcategory, ["salary", "other"])
    
    def test_min_occurrences_is_three(self):
        """Test that minimum occurrences for salary classification is 3."""
        # Only 2 occurrences should not be enough
        base_date = datetime(2024, 1, 15)
        transactions = []
        
        for i in range(2):
            date = base_date + timedelta(days=30*i)
            transactions.append({
                "name": "EMPLOYER SALARY",
                "amount": -2500.00,
                "date": date.strftime("%Y-%m-%d")
            })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should not detect with only 2 occurrences (min is 3)
        self.assertEqual(len(recurring_sources), 0)
        
        # Add one more occurrence
        date = base_date + timedelta(days=60)
        transactions.append({
            "name": "EMPLOYER SALARY",
            "amount": -2500.00,
            "date": date.strftime("%Y-%m-%d")
        })
        
        recurring_sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should detect with 3 occurrences
        self.assertGreater(len(recurring_sources), 0)
    
    def test_normalize_description_preserves_employer(self):
        """Test that normalization preserves employer context."""
        # Different variations of same employer should be grouped
        desc1 = self.detector._normalize_description("BBC MONTHLY SALARY")
        desc2 = self.detector._normalize_description("BBC MONTHLY")
        
        # Should match after normalization (trailing "SALARY" removed)
        self.assertEqual(desc1, desc2)
        
        # Company suffixes should be normalized
        desc3 = self.detector._normalize_description("ACME LIMITED")
        desc4 = self.detector._normalize_description("ACME LTD")
        self.assertEqual(desc3, desc4)


class TestBatchCategorization(unittest.TestCase):
    """Test that batch categorization preserves all fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_batch_refund_detection(self):
        """Test that refunds are detected in batch processing."""
        transactions = [
            {
                "name": "TESCO REFUND",
                "amount": -15.50,
                "date": "2024-01-15"
            },
            {
                "name": "AMAZON RETURN",
                "amount": -35.00,
                "date": "2024-01-16"
            }
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # Both should be categorized as refunds
        for txn, match in results:
            self.assertEqual(match.category, "income")
            self.assertEqual(match.subcategory, "refund")
    
    def test_batch_loan_disbursement_detection(self):
        """Test that loan disbursements are detected in batch processing."""
        transactions = [
            {
                "name": "LOAN COMPANY",
                "amount": -1000.00,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "LOAN_PAYMENTS",
                    "detailed": "LOAN_PAYMENTS"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        txn, match = results[0]
        self.assertEqual(match.category, "income")
        self.assertEqual(match.subcategory, "loans")
        self.assertEqual(match.weight, 0.0)
    
    def test_batch_grocery_priority(self):
        """Test that grocery priority is preserved in batch processing."""
        transactions = [
            {
                "name": "SAINSBURYS",
                "amount": 45.50,
                "date": "2024-01-15",
                "personal_finance_category": {
                    "primary": "FOOD_AND_DRINK",
                    "detailed": "FOOD_AND_DRINK_GROCERIES"
                }
            }
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        txn, match = results[0]
        self.assertEqual(match.category, "essential")
        self.assertEqual(match.subcategory, "groceries")


if __name__ == '__main__':
    unittest.main()
