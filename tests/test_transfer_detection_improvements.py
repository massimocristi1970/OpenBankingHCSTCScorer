"""
Comprehensive test suite for transfer detection improvements.

Tests the multi-signal transfer detection system that fixes:
1. TRANSFER_OUT transactions miscategorized as expenses
2. TRANSFER_IN + CASH_ADVANCES/LOANS should be income > loans
3. Low-confidence PLAID transfers fallback to keyword patterns
4. Legitimate expenses with TRANSFER category but no other signals

This addresses the issue where transactions like:
"To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331"
were being miscategorized as expenses instead of transfers.
"""

import unittest
from openbanking_engine.categorisation.engine import TransactionCategorizer


class TestTransferDetectionImprovements(unittest.TestCase):
    """Test cases for multi-signal transfer detection improvements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_revolut_transfer_to_person_with_sort_code(self):
        """Test Revolut transfer with all signals: To Mr [Name], Sent from Revolut, SortCodeAccountNumber."""
        # This is the exact example from the issue
        result = self.categorizer.categorize_transaction(
            description="To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331",
            amount=7.16,  # Positive = debit/TRANSFER_OUT
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.match_method, "multi_signal")
        self.assertGreaterEqual(result.confidence, 0.70)
        # Should detect multiple signals
        self.assertIn("PLAID_TRANSFER", result.description)
        self.assertIn("TO_PERSON_NAME", result.description)
        self.assertIn("SENT_FROM_APP", result.description)
        self.assertIn("SORT_CODE", result.description)
    
    def test_revolut_transfer_out_150_pounds(self):
        """Test Revolut transfer OUT for £150."""
        result = self.categorizer.categorize_transaction(
            description="To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331",
            amount=150.0,
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_revolut_transfer_out_70_pounds(self):
        """Test Revolut transfer OUT for £70."""
        result = self.categorizer.categorize_transaction(
            description="To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331",
            amount=70.0,
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_monzo_transfer_sent_from_monzo(self):
        """Test Monzo transfer with 'Sent from Monzo' pattern."""
        result = self.categorizer.categorize_transaction(
            description="To Mrs Jane Smith - Sent from Monzo",
            amount=100.0,
            merchant_name="Monzo",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
        # Should have high confidence with multiple signals
        self.assertGreaterEqual(result.confidence, 0.70)
    
    def test_wise_international_transfer(self):
        """Test Wise international transfer."""
        result = self.categorizer.categorize_transaction(
            description="To Ms Sarah Jones - Sent from Wise",
            amount=250.0,
            merchant_name="Wise",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_starling_transfer(self):
        """Test Starling Bank transfer."""
        result = self.categorizer.categorize_transaction(
            description="To Mr John Doe - Sent from Starling",
            amount=75.0,
            merchant_name="Starling",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_transfer_in_with_cash_advances_loans(self):
        """Test TRANSFER_IN + CASH_ADVANCES should be income > loans with weight=0.0."""
        result = self.categorizer.categorize_transaction(
            description="LOAN DISBURSEMENT FROM HCSTC LENDER",
            amount=-500.0,  # Negative = credit/TRANSFER_IN
            plaid_category="TRANSFER_IN_CASH_ADVANCES_AND_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
        self.assertGreaterEqual(result.confidence, 0.90)
    
    def test_transfer_in_with_advances(self):
        """Test TRANSFER_IN with ADVANCES in detailed category."""
        result = self.categorizer.categorize_transaction(
            description="CASH ADVANCE",
            amount=-300.0,
            plaid_category="TRANSFER_IN_ADVANCES",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_transfer_in_with_loans(self):
        """Test TRANSFER_IN with LOANS in detailed category."""
        result = self.categorizer.categorize_transaction(
            description="PERSONAL LOAN DISBURSEMENT",
            amount=-1000.0,
            plaid_category="TRANSFER_IN_LOANS",
            plaid_category_primary="TRANSFER_IN"
        )
        
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "loans")
        self.assertEqual(result.weight, 0.0)
    
    def test_low_confidence_plaid_transfer_with_keywords(self):
        """Test low-confidence PLAID transfer (score 30-69) falls back to keywords."""
        # Only PLAID signal (30 points), but also has keyword "INTERNAL TRANSFER"
        result = self.categorizer.categorize_transaction(
            description="INTERNAL TRANSFER TO SAVINGS",
            amount=200.0,
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
        # Should use keyword method since score is 30+15=45 (low confidence)
        self.assertIn("keyword", result.match_method.lower())
    
    def test_low_confidence_plaid_transfer_without_keywords(self):
        """Test low-confidence PLAID transfer without keywords should NOT be categorized as transfer."""
        # Only PLAID signal (30 points), no other signals, no keywords
        result = self.categorizer.categorize_transaction(
            description="TESCO STORES",
            amount=50.0,
            plaid_category="TRANSFER_OUT",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        # Should NOT be categorized as transfer (score < 70, no keywords)
        # Should fallback to expense categorization
        self.assertNotEqual(result.category, "transfer")
    
    def test_legitimate_expense_with_transfer_category_no_signals(self):
        """Test that legitimate expenses with TRANSFER category but no other signals are categorized as expense."""
        # This tests the case where PLAID might mis-tag something as TRANSFER
        # but there are no other supporting signals
        result = self.categorizer.categorize_transaction(
            description="AMAZON PURCHASE",
            amount=29.99,
            plaid_category="TRANSFER_OUT",  # Incorrectly tagged by PLAID
            plaid_category_primary="TRANSFER_OUT"
        )
        
        # Should NOT be categorized as transfer (only 30 points, no keywords)
        # Should be categorized as expense
        self.assertIn(result.category, ["expense", "essential", "positive"])
    
    def test_transfer_out_positive_amount_detection(self):
        """Test that TRANSFER_OUT (positive amounts) are correctly detected."""
        result = self.categorizer.categorize_transaction(
            description="To Ms Emma Wilson - Sent from Revolut - SortCodeAccountNumber: 12345678901234",
            amount=300.0,  # Positive = debit
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_transfer_with_sort_code_pattern(self):
        """Test detection of 'Sort Code' pattern (with space)."""
        result = self.categorizer.categorize_transaction(
            description="To Mr James Brown - Sort Code: 12-34-56 Account: 12345678",
            amount=150.0,
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertIn("SORT_CODE", result.description)
    
    def test_transfer_to_mrs_pattern(self):
        """Test 'To Mrs [Name]' pattern detection."""
        result = self.categorizer.categorize_transaction(
            description="To Mrs Elizabeth Taylor - Sent from Monzo",
            amount=100.0,
            merchant_name="Monzo",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertIn("TO_PERSON_NAME", result.description)
    
    def test_transfer_to_ms_pattern(self):
        """Test 'To Ms [Name]' pattern detection."""
        result = self.categorizer.categorize_transaction(
            description="To Ms Rachel Green - Sent from Wise",
            amount=75.0,
            merchant_name="Wise",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertIn("TO_PERSON_NAME", result.description)
    
    def test_transfer_to_dr_pattern(self):
        """Test 'To Dr [Name]' pattern detection."""
        result = self.categorizer.categorize_transaction(
            description="To Dr Gregory House - Sent from Revolut",
            amount=200.0,
            merchant_name="Revolut",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertIn("TO_PERSON_NAME", result.description)
    
    def test_chase_transfer(self):
        """Test Chase Bank transfer."""
        result = self.categorizer.categorize_transaction(
            description="To Mr Robert Davis",
            amount=500.0,
            merchant_name="Chase",
            plaid_category="TRANSFER_OUT_ACCOUNT_TRANSFER",
            plaid_category_primary="TRANSFER_OUT"
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        # Should detect fintech app signal
        self.assertIn("FINTECH_APP", result.description)
    
    def test_own_account_keyword_transfer(self):
        """Test keyword-based transfer detection without PLAID."""
        result = self.categorizer.categorize_transaction(
            description="TRANSFER TO OWN ACCOUNT",
            amount=1000.0
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
        self.assertEqual(result.weight, 0.0)
    
    def test_internal_transfer_keyword(self):
        """Test 'INTERNAL TRANSFER' keyword detection."""
        result = self.categorizer.categorize_transaction(
            description="INTERNAL TRANSFER FROM CURRENT TO SAVINGS",
            amount=500.0
        )
        
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.weight, 0.0)
    
    def test_check_transfer_signals_method(self):
        """Test the _check_transfer_signals() method directly."""
        # Test high confidence case (all signals)
        score, signals = self.categorizer._check_transfer_signals(
            description="To Mr John Smith - Sent from Revolut - SortCodeAccountNumber: 12345678901234",
            plaid_category_primary="TRANSFER_OUT",
            plaid_category_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            merchant_name="Revolut"
        )
        
        # Should have high score with multiple signals
        self.assertGreaterEqual(score, 70)
        self.assertIn("PLAID_TRANSFER", signals)
        self.assertIn("TO_PERSON_NAME", signals)
        self.assertIn("SENT_FROM_APP", signals)
        self.assertIn("SORT_CODE", signals)
    
    def test_check_transfer_signals_low_confidence(self):
        """Test low confidence transfer signal detection."""
        score, signals = self.categorizer._check_transfer_signals(
            description="SOME TRANSACTION",
            plaid_category_primary="TRANSFER_OUT",
            plaid_category_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            merchant_name=None
        )
        
        # Only PLAID signal, score should be 30
        self.assertEqual(score, 30)
        self.assertEqual(len(signals), 1)
        self.assertIn("PLAID_TRANSFER", signals)
    
    def test_check_transfer_signals_no_plaid(self):
        """Test transfer detection without PLAID but with strong keywords."""
        score, signals = self.categorizer._check_transfer_signals(
            description="INTERNAL TRANSFER TO SAVINGS",
            plaid_category_primary=None,
            plaid_category_detailed=None,
            merchant_name=None
        )
        
        # Only keyword signal, score should be 15
        self.assertEqual(score, 15)
        self.assertIn("TRANSFER_KEYWORDS", signals)


class TestBatchTransferDetection(unittest.TestCase):
    """Test batch processing with improved transfer detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_batch_with_multiple_transfer_types(self):
        """Test batch processing with various transfer types."""
        transactions = [
            {
                "name": "To Mr Vishant Khanna - Sent from Revolut - SortCodeAccountNumber: 60837132003331",
                "amount": 7.16,
                "date": "2025-05-18",
                "merchant_name": "Revolut",
                "personal_finance_category": {
                    "primary": "TRANSFER_OUT",
                    "detailed": "TRANSFER_OUT_ACCOUNT_TRANSFER"
                }
            },
            {
                "name": "LOAN DISBURSEMENT",
                "amount": -500.0,
                "date": "2025-05-15",
                "personal_finance_category": {
                    "primary": "TRANSFER_IN",
                    "detailed": "TRANSFER_IN_CASH_ADVANCES_AND_LOANS"
                }
            },
            {
                "name": "TESCO STORES",
                "amount": 45.50,
                "date": "2025-05-17",
                "merchant_name": "Tesco"
            }
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # First should be transfer
        self.assertEqual(results[0][1].category, "transfer")
        self.assertEqual(results[0][1].subcategory, "internal")
        
        # Second should be income > loans
        self.assertEqual(results[1][1].category, "income")
        self.assertEqual(results[1][1].subcategory, "loans")
        self.assertEqual(results[1][1].weight, 0.0)
        
        # Third should be expense (grocery)
        self.assertIn(results[2][1].category, ["essential", "expense"])


if __name__ == "__main__":
    unittest.main()
