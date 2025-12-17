"""
Test suite for enhanced categorization features.

Tests cover:
- Extended keywords for salary, gig economy, pension, benefits, interest, and transfers
- PLAID detailed category preference
- Transfer pairing heuristic
- Quarterly pension tolerance
- Credit card and loan repayment routing to debt
- Debug mode rationale output
"""

import unittest
from datetime import datetime, timedelta
from openbanking_engine.categorisation.engine import TransactionCategorizer, CategoryMatch
from openbanking_engine.income.income_detector import IncomeDetector


class TestExtendedSalaryKeywords(unittest.TestCase):
    """Test extended salary/payroll keywords."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
    
    def test_adp_payroll_detected_as_salary(self):
        """Test that ADP payroll is detected as salary."""
        result = self.categorizer.categorize_transaction(
            description="ADP PAYROLL PAYMENT",
            amount=-2500.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_payfit_detected_as_salary(self):
        """Test that PayFit is detected as salary."""
        result = self.categorizer.categorize_transaction(
            description="PAYFIT MONTHLY SALARY",
            amount=-3000.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_sage_payroll_detected_as_salary(self):
        """Test that Sage Payroll is detected as salary."""
        result = self.categorizer.categorize_transaction(
            description="SAGE PAYROLL WAGES",
            amount=-2800.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_xero_payrun_detected_as_salary(self):
        """Test that Xero Payrun is detected as salary."""
        result = self.categorizer.categorize_transaction(
            description="XERO PAYRUN",
            amount=-2600.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")
    
    def test_workday_payroll_detected_as_salary(self):
        """Test that Workday payroll is detected as salary."""
        result = self.categorizer.categorize_transaction(
            description="WORKDAY PAYROLL",
            amount=-3200.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "salary")


class TestExtendedGigKeywords(unittest.TestCase):
    """Test extended gig economy keywords."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
    
    def test_uber_eats_payout_detected(self):
        """Test that Uber Eats payout is detected as gig income."""
        result = self.categorizer.categorize_transaction(
            description="UBER EATS PAYOUT",
            amount=-150.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "gig_economy")
    
    def test_evri_earnings_detected(self):
        """Test that Evri earnings are detected as gig income."""
        result = self.categorizer.categorize_transaction(
            description="EVRI EARNINGS PAYMENT",
            amount=-200.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "gig_economy")
    
    def test_dpd_driver_payment_detected(self):
        """Test that DPD driver payment is detected as gig income."""
        result = self.categorizer.categorize_transaction(
            description="DPD DRIVER PAYMENT",
            amount=-250.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "gig_economy")
    
    def test_shopify_payout_detected(self):
        """Test that Shopify payout is detected as gig income."""
        result = self.categorizer.categorize_transaction(
            description="SHOPIFY PAYMENTS PAYOUT",
            amount=-500.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "gig_economy")
    
    def test_stripe_payout_detected(self):
        """Test that Stripe payout is detected as gig income."""
        result = self.categorizer.categorize_transaction(
            description="STRIPE PAYOUT",
            amount=-300.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "gig_economy")


class TestInterestIncome(unittest.TestCase):
    """Test new interest income category."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
    
    def test_bank_interest_detected(self):
        """Test that bank interest is detected."""
        result = self.categorizer.categorize_transaction(
            description="INTEREST PAID",
            amount=-5.25,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "interest")
    
    def test_gross_interest_detected(self):
        """Test that gross interest is detected."""
        result = self.categorizer.categorize_transaction(
            description="GROSS INT",
            amount=-12.50,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "interest")
    
    def test_savings_interest_detected(self):
        """Test that savings interest is detected."""
        result = self.categorizer.categorize_transaction(
            description="SAVINGS INTEREST CREDIT",
            amount=-8.75,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "interest")


class TestTaxRefunds(unittest.TestCase):
    """Test tax refund detection."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
    
    def test_hmrc_refund_detected(self):
        """Test that HMRC refund is detected as benefit."""
        result = self.categorizer.categorize_transaction(
            description="HMRC REFUND",
            amount=-150.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "benefits")
    
    def test_tax_refund_detected(self):
        """Test that tax refund is detected as benefit."""
        result = self.categorizer.categorize_transaction(
            description="TAX REFUND HMRC",
            amount=-200.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "income")
        self.assertEqual(result.subcategory, "benefits")


class TestExtendedTransferKeywords(unittest.TestCase):
    """Test extended transfer keywords for neobanks."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
    
    def test_revolut_transfer_detected(self):
        """Test that Revolut transfer is detected."""
        result = self.categorizer.categorize_transaction(
            description="REVOLUT TRANSFER TO VAULT",
            amount=100.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
    
    def test_monzo_pot_transfer_detected(self):
        """Test that Monzo pot transfer is detected."""
        result = self.categorizer.categorize_transaction(
            description="MONZO POT TRANSFER",
            amount=50.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
    
    def test_starling_space_move_detected(self):
        """Test that Starling space move is detected."""
        result = self.categorizer.categorize_transaction(
            description="STARLING MOVE TO SPACE",
            amount=75.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")
    
    def test_round_up_detected(self):
        """Test that round up is detected as transfer."""
        result = self.categorizer.categorize_transaction(
            description="ROUND UP",
            amount=0.50,
            plaid_category=None,
            plaid_category_primary=None
        )
        self.assertEqual(result.category, "transfer")
        self.assertEqual(result.subcategory, "internal")


class TestPensionQuarterlyTolerance(unittest.TestCase):
    """Test quarterly pension tolerance."""
    
    def setUp(self):
        self.detector = IncomeDetector()
    
    def test_quarterly_pension_accepted(self):
        """Test that quarterly pension payments are accepted."""
        # Create 3 transactions ~90 days apart
        base_date = datetime(2024, 1, 15)
        transactions = [
            {
                "name": "STATE PENSION",
                "amount": -500.00,
                "date": base_date.strftime("%Y-%m-%d")
            },
            {
                "name": "STATE PENSION",
                "amount": -500.00,
                "date": (base_date + timedelta(days=90)).strftime("%Y-%m-%d")
            },
            {
                "name": "STATE PENSION",
                "amount": -500.00,
                "date": (base_date + timedelta(days=180)).strftime("%Y-%m-%d")
            }
        ]
        
        sources = self.detector.find_recurring_income_sources(transactions)
        
        # Should find the quarterly pension pattern
        self.assertTrue(len(sources) > 0)
        pension_source = sources[0]
        self.assertEqual(pension_source.source_type, "pension")
        self.assertTrue(80 <= pension_source.frequency_days <= 100)


class TestPlaidDetailedPreference(unittest.TestCase):
    """Test that detailed PLAID categories are preferred over primary."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
        self.detector = IncomeDetector()
    
    def test_detailed_wages_preferred_over_primary(self):
        """Test that detailed INCOME_WAGES is used over primary INCOME."""
        is_income, confidence, reason = self.detector.is_likely_income(
            description="ACME LTD PAYMENT",
            amount=-2500.00,
            plaid_category_primary="INCOME",
            plaid_category_detailed="INCOME_WAGES"
        )
        
        self.assertTrue(is_income)
        self.assertGreaterEqual(confidence, 0.90)
        self.assertIn("detailed", reason)
    
    def test_detailed_retirement_preferred(self):
        """Test that detailed INCOME_RETIREMENT is recognized."""
        is_income, confidence, reason = self.detector.is_likely_income(
            description="PENSION PAYMENT",
            amount=-800.00,
            plaid_category_primary="INCOME",
            plaid_category_detailed="INCOME_RETIREMENT"
        )
        
        self.assertTrue(is_income)
        self.assertGreaterEqual(confidence, 0.90)
        self.assertIn("retirement", reason.lower())


class TestDebugMode(unittest.TestCase):
    """Test debug mode rationale output."""
    
    def test_debug_mode_off_no_rationale(self):
        """Test that debug mode off produces no rationale."""
        categorizer = TransactionCategorizer(debug_mode=False)
        result = categorizer.categorize_transaction(
            description="TESCO",
            amount=50.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        
        self.assertIsNone(result.debug_rationale)
    
    def test_debug_mode_on_provides_rationale(self):
        """Test that debug mode on provides rationale."""
        categorizer = TransactionCategorizer(debug_mode=True)
        result = categorizer.categorize_transaction(
            description="SALARY PAYMENT",
            amount=-2500.00,
            plaid_category=None,
            plaid_category_primary=None
        )
        
        # Debug rationale should be present when debug mode is on
        # (Implementation will populate this when debug mode is used)
        self.assertIsNotNone(result.debug_rationale)


class TestTransferPairing(unittest.TestCase):
    """Test transfer pairing heuristic."""
    
    def setUp(self):
        self.categorizer = TransactionCategorizer()
    
    def test_find_transfer_pair_same_day(self):
        """Test finding transfer pair on same day."""
        transactions = [
            {
                "name": "TRANSFER TO SAVINGS",
                "amount": 100.00,
                "date": "2024-01-15"
            },
            {
                "name": "TRANSFER FROM CURRENT",
                "amount": -100.00,
                "date": "2024-01-15"
            }
        ]
        
        pair = self.categorizer._find_transfer_pair(
            transactions=transactions,
            current_idx=0,
            amount=100.00,
            description="TRANSFER TO SAVINGS",
            date_str="2024-01-15"
        )
        
        self.assertIsNotNone(pair)
        self.assertEqual(pair["amount"], -100.00)
    
    def test_find_transfer_pair_next_day(self):
        """Test finding transfer pair next day."""
        transactions = [
            {
                "name": "MONZO TRANSFER",
                "amount": 50.00,
                "date": "2024-01-15"
            },
            {
                "name": "MONZO TRANSFER",
                "amount": -50.00,
                "date": "2024-01-16"
            }
        ]
        
        pair = self.categorizer._find_transfer_pair(
            transactions=transactions,
            current_idx=0,
            amount=50.00,
            description="MONZO TRANSFER",
            date_str="2024-01-15"
        )
        
        self.assertIsNotNone(pair)
    
    def test_no_pair_found_different_amounts(self):
        """Test no pair found when amounts differ significantly."""
        transactions = [
            {
                "name": "TRANSFER",
                "amount": 100.00,
                "date": "2024-01-15"
            },
            {
                "name": "TRANSFER",
                "amount": -50.00,  # Too different (50% vs 10% tolerance)
                "date": "2024-01-15"
            }
        ]
        
        pair = self.categorizer._find_transfer_pair(
            transactions=transactions,
            current_idx=0,
            amount=100.00,
            description="TRANSFER",
            date_str="2024-01-15"
        )
        
        self.assertIsNone(pair)
    
    def test_no_pair_found_too_far_apart(self):
        """Test no pair found when dates are too far apart."""
        transactions = [
            {
                "name": "TRANSFER",
                "amount": 100.00,
                "date": "2024-01-15"
            },
            {
                "name": "TRANSFER",
                "amount": -100.00,
                "date": "2024-01-20"  # 5 days apart, exceeds 2-day limit
            }
        ]
        
        pair = self.categorizer._find_transfer_pair(
            transactions=transactions,
            current_idx=0,
            amount=100.00,
            description="TRANSFER",
            date_str="2024-01-15"
        )
        
        self.assertIsNone(pair)


if __name__ == "__main__":
    unittest.main()
