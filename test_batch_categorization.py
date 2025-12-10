"""
Test suite for batch transaction categorization.

Tests the new batch categorization methods that optimize recurring pattern
detection by analyzing all transactions at once rather than individually.
"""

import unittest
from datetime import datetime, timedelta
from transaction_categorizer import TransactionCategorizer
from income_detector import IncomeDetector


class TestBatchAnalysis(unittest.TestCase):
    """Test cases for batch analysis in IncomeDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = IncomeDetector()
    
    def test_analyze_batch_caches_patterns(self):
        """Test that analyze_batch caches recurring patterns."""
        # Create recurring salary pattern
        transactions = [
            {"name": "ACME LTD SALARY", "amount": -2000, "date": "2024-01-25"},
            {"name": "ACME LTD SALARY", "amount": -2000, "date": "2024-02-25"},
            {"name": "ACME LTD SALARY", "amount": -2000, "date": "2024-03-25"},
        ]
        
        # Analyze batch
        self.detector.analyze_batch(transactions)
        
        # Cache should be valid and contain patterns
        self.assertTrue(self.detector._cache_valid)
        self.assertEqual(len(self.detector._cached_recurring_sources), 1)
        
        # Pattern should have all 3 transactions
        source = self.detector._cached_recurring_sources[0]
        self.assertEqual(source.occurrence_count, 3)
        self.assertEqual(len(source.transaction_indices), 3)
    
    def test_clear_batch_cache(self):
        """Test that clear_batch_cache resets the cache."""
        transactions = [
            {"name": "SALARY", "amount": -2000, "date": "2024-01-25"},
            {"name": "SALARY", "amount": -2000, "date": "2024-02-25"},
        ]
        
        self.detector.analyze_batch(transactions)
        self.assertTrue(self.detector._cache_valid)
        
        # Clear cache
        self.detector.clear_batch_cache()
        
        # Cache should be invalid and empty
        self.assertFalse(self.detector._cache_valid)
        self.assertEqual(len(self.detector._cached_recurring_sources), 0)
    
    def test_is_likely_income_from_batch_uses_cache(self):
        """Test that is_likely_income_from_batch uses cached patterns."""
        # Use neutral descriptions to test recurring pattern detection
        # Avoid keywords like "SALARY", "MONTHLY PAY", "LTD", etc.
        transactions = [
            {"name": "AUTOMATED CREDIT REF 12345", "amount": -1500, "date": "2024-01-25"},
            {"name": "AUTOMATED CREDIT REF 23456", "amount": -1500, "date": "2024-02-25"},
            {"name": "AUTOMATED CREDIT REF 34567", "amount": -1500, "date": "2024-03-25"},
            {"name": "TESCO", "amount": 50, "date": "2024-01-26"},  # Not income
        ]
        
        # Analyze batch
        self.detector.analyze_batch(transactions)
        
        # Check first transaction (part of recurring pattern)
        is_income, confidence, reason = self.detector.is_likely_income_from_batch(
            description="AUTOMATED CREDIT REF 12345",
            amount=-1500,
            transaction_index=0
        )
        
        self.assertTrue(is_income)
        self.assertGreaterEqual(confidence, 0.70)
        self.assertIn("recurring", reason)
        
        # Check transaction that's not part of pattern
        is_income, confidence, reason = self.detector.is_likely_income_from_batch(
            description="TESCO",
            amount=50,
            transaction_index=3
        )
        
        self.assertFalse(is_income)
    
    def test_batch_analysis_with_no_recurring_patterns(self):
        """Test batch analysis when no recurring patterns exist."""
        transactions = [
            {"name": "RANDOM 1", "amount": -100, "date": "2024-01-01"},
            {"name": "RANDOM 2", "amount": -200, "date": "2024-01-05"},
            {"name": "RANDOM 3", "amount": -300, "date": "2024-01-22"},
        ]
        
        self.detector.analyze_batch(transactions)
        
        # Should have empty cache but still be valid
        self.assertTrue(self.detector._cache_valid)
        self.assertEqual(len(self.detector._cached_recurring_sources), 0)
        
        # Categorization should still work (fall back to keyword matching)
        is_income, confidence, reason = self.detector.is_likely_income_from_batch(
            description="SALARY PAYMENT",
            amount=-1000,
            transaction_index=0
        )
        
        self.assertTrue(is_income)
        self.assertIn("payroll", reason)


class TestBatchCategorization(unittest.TestCase):
    """Test cases for batch categorization in TransactionCategorizer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_categorize_transactions_batch_detects_recurring_salary(self):
        """Test that batch categorization detects recurring salary."""
        transactions = [
            {"name": "EMPLOYER LTD", "amount": -2500, "date": "2024-01-25"},
            {"name": "EMPLOYER LTD", "amount": -2500, "date": "2024-02-25"},
            {"name": "EMPLOYER LTD", "amount": -2500, "date": "2024-03-25"},
            {"name": "TESCO GROCERIES", "amount": 45.50, "date": "2024-01-26"},
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # Should have 4 results
        self.assertEqual(len(results), 4)
        
        # First 3 should be income (salary)
        for i in range(3):
            txn, match = results[i]
            self.assertEqual(match.category, "income")
            self.assertIn(match.subcategory, ["salary", "other"])
            self.assertGreater(match.weight, 0.0)
            # Check match method indicates batch processing
            self.assertTrue(
                "batch" in match.match_method or "recurring" in match.match_method
            )
        
        # Last one should be expense
        txn, match = results[3]
        self.assertEqual(match.category, "essential")
    
    def test_batch_vs_single_categorization_consistency(self):
        """Test that batch and single categorization produce consistent results."""
        transactions = [
            {"name": "SALARY PAYMENT", "amount": -2000, "date": "2024-01-25"},
            {"name": "DWP UNIVERSAL CREDIT", "amount": -800, "date": "2024-01-10"},
            {"name": "TESCO", "amount": 50, "date": "2024-01-26"},
            {"name": "TRANSFER FROM SAVINGS", "amount": -500, "date": "2024-01-15"},
        ]
        
        # Batch categorization
        batch_results = self.categorizer.categorize_transactions_batch(transactions)
        
        # Single categorization
        single_results = self.categorizer.categorize_transactions(transactions)
        
        # Both should have same number of results
        self.assertEqual(len(batch_results), len(single_results))
        
        # Categories should match (though match_method may differ)
        for i, (batch_txn, batch_match) in enumerate(batch_results):
            single_txn, single_match = single_results[i]
            
            with self.subTest(txn_index=i):
                self.assertEqual(batch_match.category, single_match.category)
                self.assertEqual(batch_match.subcategory, single_match.subcategory)
                self.assertEqual(batch_match.weight, single_match.weight)
    
    def test_batch_categorization_clears_cache(self):
        """Test that batch categorization clears cache after processing."""
        transactions = [
            {"name": "SALARY", "amount": -2000, "date": "2024-01-25"},
            {"name": "SALARY", "amount": -2000, "date": "2024-02-25"},
        ]
        
        # Run batch categorization
        self.categorizer.categorize_transactions_batch(transactions)
        
        # Cache should be cleared
        self.assertFalse(self.categorizer.income_detector._cache_valid)
        self.assertEqual(len(self.categorizer.income_detector._cached_recurring_sources), 0)
    
    def test_batch_categorization_with_mixed_transactions(self):
        """Test batch categorization with various transaction types."""
        transactions = [
            # Recurring salary
            {"name": "ACME CORP", "amount": -2000, "date": "2024-01-25"},
            {"name": "ACME CORP", "amount": -2000, "date": "2024-02-25"},
            # Benefits
            {"name": "DWP UC", "amount": -500, "date": "2024-01-10"},
            # Expenses
            {"name": "RENT PAYMENT", "amount": 800, "date": "2024-01-01"},
            {"name": "GROCERIES", "amount": 100, "date": "2024-01-15"},
            # Transfer
            {"name": "FROM SAVINGS", "amount": -1000, "date": "2024-01-20"},
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        self.assertEqual(len(results), 6)
        
        # Check first two (recurring salary)
        for i in range(2):
            txn, match = results[i]
            self.assertEqual(match.category, "income")
            self.assertGreater(match.weight, 0.0)
        
        # Check benefits
        txn, match = results[2]
        self.assertEqual(match.category, "income")
        self.assertEqual(match.subcategory, "benefits")
        
        # Check expenses
        txn, match = results[3]
        self.assertEqual(match.category, "essential")
        
        # Check transfer
        txn, match = results[5]
        self.assertEqual(match.category, "transfer")
        self.assertEqual(match.weight, 0.0)
    
    def test_batch_categorization_empty_list(self):
        """Test batch categorization with empty transaction list."""
        transactions = []
        results = self.categorizer.categorize_transactions_batch(transactions)
        self.assertEqual(len(results), 0)
    
    def test_batch_categorization_single_transaction(self):
        """Test batch categorization with single transaction."""
        transactions = [
            {"name": "SALARY", "amount": -2000, "date": "2024-01-25"},
        ]
        
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        self.assertEqual(len(results), 1)
        txn, match = results[0]
        self.assertEqual(match.category, "income")


class TestBatchPerformance(unittest.TestCase):
    """Test cases for batch categorization performance characteristics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.categorizer = TransactionCategorizer()
    
    def test_large_batch_with_multiple_recurring_sources(self):
        """Test batch categorization with large transaction list."""
        transactions = []
        base_date = datetime(2024, 1, 1)
        
        # Add 3 months of weekly salary (12 transactions)
        for i in range(12):
            date = base_date + timedelta(days=7*i)
            transactions.append({
                "name": "EMPLOYER SALARY",
                "amount": -1500,
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Add 3 months of monthly benefits (3 transactions)
        for i in range(3):
            date = base_date + timedelta(days=30*i)
            transactions.append({
                "name": "DWP UNIVERSAL CREDIT",
                "amount": -500,
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Add random expenses (20 transactions)
        for i in range(20):
            date = base_date + timedelta(days=3*i)
            transactions.append({
                "name": f"EXPENSE {i}",
                "amount": 50 + (i * 10),
                "date": date.strftime("%Y-%m-%d")
            })
        
        # Should categorize all 35 transactions
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        self.assertEqual(len(results), 35)
        
        # Count income transactions
        income_count = sum(1 for _, match in results if match.category == "income")
        
        # Should detect salary + benefits (15 income transactions)
        self.assertGreaterEqual(income_count, 15)
    
    def test_batch_handles_malformed_transactions(self):
        """Test that batch categorization handles malformed data gracefully."""
        transactions = [
            {"name": "VALID SALARY", "amount": -2000, "date": "2024-01-25"},
            {"name": "", "amount": 0, "date": ""},  # Empty data
            {"name": "MISSING AMOUNT", "date": "2024-01-26"},  # Missing amount
            {"amount": -1000, "date": "2024-01-27"},  # Missing name
        ]
        
        # Should not crash
        results = self.categorizer.categorize_transactions_batch(transactions)
        
        # Should have results for all transactions
        self.assertEqual(len(results), 4)
        
        # First transaction should be categorized as income
        txn, match = results[0]
        self.assertEqual(match.category, "income")


if __name__ == "__main__":
    unittest.main(verbosity=2)
